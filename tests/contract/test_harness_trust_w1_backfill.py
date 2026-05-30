"""Harness Trust Completion W1.4 RED: archive backfill + G3 producer wiring."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.dynasty_genius.eval import backtest_harness as bh
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


def _archive(
    *,
    sleeper_id: str = "slp_1",
    value: int = 1000,
    position: str = "QB",
    archive_publish_date: str = "2021-09-08",
    updated_at: str | None = None,
    source: str = "ktc_community_csv",
    overall_rank: int = 1,
    position_rank: int = 1,
) -> dict:
    row = {
        "sleeper_id": sleeper_id,
        "value": value,
        "position": position,
        "archive_publish_date": archive_publish_date,
        "source": source,
        "overall_rank": overall_rank,
        "position_rank": position_rank,
    }
    if updated_at is not None:
        row["updated_at"] = updated_at
    return row


def _market_rows(n: int, position: str = "WR") -> list[dict]:
    return [
        {
            "snapshot_date": "2021-09-08",
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": n - i,
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": position,
            "trend_30day": 0,
            "source": "ktc_community_csv",
            "inserted_at": "2026-05-30T00:00:00+00:00",
        }
        for i in range(n)
    ]


def test_backfill_accepts_in_window_archive_rows(tmp_path: Path) -> None:
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    archive = [
        _archive(sleeper_id="slp_1", archive_publish_date="2021-09-01"),
        _archive(sleeper_id="slp_2", archive_publish_date="2021-09-08"),
        _archive(sleeper_id="slp_3", archive_publish_date="2021-09-15"),
    ]

    stats = backfill_market_archive(
        archive,
        db_path=db_path,
        snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 3
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08", "QB")
    assert {r["sleeper_id"] for r in rows} == {"slp_1", "slp_2", "slp_3"}
    assert {r["source"] for r in rows} == {"ktc_community_csv"}


def test_backfill_rejects_rows_outside_point_in_time_window(tmp_path: Path) -> None:
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    stats = backfill_market_archive(
        [_archive(archive_publish_date="2021-09-16")],
        db_path=db_path,
        snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 0
    assert stats["rows_skipped"] == 1
    assert MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08") == []


def test_backfill_skips_rows_missing_required_fields(tmp_path: Path) -> None:
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    valid = _archive(sleeper_id="slp_valid")
    missing_value = _archive(sleeper_id="slp_missing")
    del missing_value["value"]

    stats = backfill_market_archive(
        [valid, missing_value],
        db_path=db_path,
        snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 1
    assert stats["rows_skipped"] == 1
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08", "QB")
    assert [r["sleeper_id"] for r in rows] == ["slp_valid"]


def test_backfill_rejects_revised_rows_updated_after_capture(tmp_path: Path) -> None:
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    stats = backfill_market_archive(
        [
            _archive(
                archive_publish_date="2021-09-08",
                updated_at="2021-09-09",
            )
        ],
        db_path=db_path,
        snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 0
    assert stats["rows_skipped"] == 1
    assert MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08") == []


def test_compute_market_ndcg_populates_primary_k_bootstrap_outputs() -> None:
    n = 30
    rng = np.random.default_rng(44)

    result = bh._compute_market_ndcg(
        y_pred=rng.random(n),
        player_ids=[f"gsis_{i}" for i in range(n)],
        y_realized=rng.random(n),
        market_rows=_market_rows(n, position="WR"),
        id_map={f"gsis_{i}": f"slp_{i}" for i in range(n)},
        position="WR",
        n_bootstrap=100,
        rng_seed=123,
    )

    assert result["primary_k"] == bh.PRIMARY_NDCG_K["WR"] == 24
    assert result["market_pool_n"] == n
    assert result["ndcg_diff_primary_k"] is not None
    assert result["ndcg_diff_bca_ci95"] is not None
    lo, hi = result["ndcg_diff_bca_ci95"]
    assert lo <= result["ndcg_diff_primary_k"] <= hi
    assert result["caveat"] is None


def test_compute_market_ndcg_pool_below_primary_k_sets_caveat_and_null_bootstrap() -> None:
    n = 15
    rng = np.random.default_rng(45)

    result = bh._compute_market_ndcg(
        y_pred=rng.random(n),
        player_ids=[f"gsis_{i}" for i in range(n)],
        y_realized=rng.random(n),
        market_rows=_market_rows(n, position="WR"),
        id_map={f"gsis_{i}": f"slp_{i}" for i in range(n)},
        position="WR",
        n_bootstrap=100,
        rng_seed=123,
    )

    assert result["primary_k"] == 24
    assert result["market_pool_n"] == n
    assert result["ndcg_diff_primary_k"] is None
    assert result["ndcg_diff_bca_ci95"] is None
    assert result["caveat"] == "pool_below_k"


def test_backfill_skips_rows_with_non_int_value(tmp_path: Path) -> None:
    # Codex W1.4 finding: malformed EXTERNAL archive data (non-int value) must skip,
    # not crash on int() coercion.
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    bad = _archive(sleeper_id="slp_bad", value="not-an-int")  # type: ignore[arg-type]
    good = _archive(sleeper_id="slp_good")

    stats = backfill_market_archive(
        [bad, good], db_path=db_path, snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 1
    assert stats["rows_skipped"] == 1
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08", "QB")
    assert [r["sleeper_id"] for r in rows] == ["slp_good"]


def test_backfill_rejects_non_backfill_source(tmp_path: Path) -> None:
    # Codex W1.4 finding: backfill provenance must be ktc_community_csv / dp_archive
    # only — fc_native is the FORWARD W2a source and must not enter the archive.
    from scripts.backfill_market_archive import backfill_market_archive

    db_path = tmp_path / "archive.db"
    stats = backfill_market_archive(
        [_archive(source="fc_native")], db_path=db_path, snapshot_dates=["2021-09-08"],
    )

    assert stats["rows_written"] == 0
    assert stats["rows_skipped"] == 1
    assert MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08") == []
