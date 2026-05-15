"""Task 10.1 unit tests: MarketSnapshotStore.

Six tests that must fail with ImportError on the RED run, then pass once
market_snapshot_store.py is implemented.
"""
from __future__ import annotations

import pytest

from pathlib import Path
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore
from scripts.ingest_market_archive import ingest_csv


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_rows(snapshot_date: str, n: int = 3) -> list[dict]:
    return [
        {
            "snapshot_date": snapshot_date,
            "league_settings_hash": "abc123",
            "sleeper_id": f"player_{i}",
            "value": 1000 - i * 100,
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": "WR",
            "trend_30day": 0,
            "source": "ktc_community_csv",
            "inserted_at": "2026-05-14T05:00:00+00:00",
        }
        for i in range(n)
    ]


# ── Test 1: upsert writes rows and is idempotent on conflict ──────────────────

def test_upsert_writes_and_is_idempotent(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    rows = _make_rows("2021-09-08")
    count = store.upsert_snapshots(rows)
    assert count == 3

    # Second upsert same rows → idempotent, still 3 rows total
    count2 = store.upsert_snapshots(rows)
    assert count2 == 3
    result = store.get_snapshot("2021-09-08")
    assert len(result) == 3


# ── Test 2: get_snapshot returns exact date ───────────────────────────────────

def test_get_snapshot_exact_date(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    store.upsert_snapshots(_make_rows("2021-09-08"))
    store.upsert_snapshots(_make_rows("2022-09-07"))

    result = store.get_snapshot("2021-09-08")
    dates = {r["snapshot_date"] for r in result}
    assert dates == {"2021-09-08"}
    assert len(result) == 3


# ── Test 3: get_snapshot falls back to nearest date within ±7 days ───────────

def test_get_snapshot_fallback_within_7_days(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    store.upsert_snapshots(_make_rows("2021-09-08"))

    # Ask for 2021-09-10 (2 days after the stored date)
    result = store.get_snapshot("2021-09-10")
    assert len(result) == 3
    assert result[0]["snapshot_date"] == "2021-09-08"


# ── Test 4: get_snapshot returns [] beyond ±7 days ───────────────────────────

def test_get_snapshot_empty_beyond_7_days(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    store.upsert_snapshots(_make_rows("2021-09-08"))

    # Ask for 2021-09-20 (12 days out — beyond ±7 window)
    result = store.get_snapshot("2021-09-20")
    assert result == []


# ── Test 5: has_snapshot returns correct boolean ──────────────────────────────

def test_has_snapshot_true_and_false(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    store.upsert_snapshots(_make_rows("2021-09-08"))

    assert store.has_snapshot("2021-09-08") is True
    assert store.has_snapshot("2022-09-07") is False


# ── Test 6: get_ranked returns rows sorted by overall_rank ascending ──────────

def test_get_ranked_sorted_by_overall_rank(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    # Insert rows in reverse rank order to ensure sorting is applied
    rows = [
        {
            "snapshot_date": "2021-09-08",
            "league_settings_hash": "abc123",
            "sleeper_id": f"player_{i}",
            "value": i * 100,
            "overall_rank": 4 - i,          # 4, 3, 2, 1
            "position_rank": 4 - i,
            "position": "RB",
            "trend_30day": 0,
            "source": "ktc_community_csv",
            "inserted_at": "2026-05-14T05:00:00+00:00",
        }
        for i in range(4)
    ]
    store.upsert_snapshots(rows)

    ranked = store.get_ranked("2021-09-08", "RB")
    assert len(ranked) == 4
    ranks = [r["overall_rank"] for r in ranked]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1

# ── Ingest Script Tests ───────────────────────────────────────────────────────

def test_ingest_writes_rows_correctly(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    csv_path = tmp_path / "archive.csv"
    csv_path.write_text(
        "sleeper_id,value,overall_rank,position_rank,position\n"
        "123,5000,10,1,QB\n"
        "456,4000,20,5,RB\n"
    )

    stats = ingest_csv(
        csv_path=csv_path,
        source="ktc_community_csv",
        snapshot_date="2022-09-07",
        store=store
    )

    assert stats["rows_read"] == 2
    assert stats["rows_written"] == 2
    assert stats["rows_skipped"] == 0

    snapshot = store.get_snapshot("2022-09-07")
    assert len(snapshot) == 2
    ids = {r["sleeper_id"] for r in snapshot}
    assert ids == {"123", "456"}
    vals = {r["value"] for r in snapshot}
    assert vals == {5000, 4000}


def test_ingest_is_idempotent(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    csv_path = tmp_path / "archive.csv"
    csv_path.write_text(
        "sleeper_id,value,rank\n"
        "123,5000,1\n"
    )

    # Run 1
    ingest_csv(csv_path, "ktc_community_csv", "2022-09-07", store)
    # Run 2
    stats = ingest_csv(csv_path, "ktc_community_csv", "2022-09-07", store)

    assert stats["rows_written"] == 1
    snapshot = store.get_snapshot("2022-09-07")
    assert len(snapshot) == 1


def test_ingest_skips_missing_sleeper_id(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    csv_path = tmp_path / "archive.csv"
    # Row 2 is missing sleeper_id, Row 3 has non-numeric value
    csv_path.write_text(
        "sleeper_id,value\n"
        "123,5000\n"
        ",4000\n"
        "789,not_a_number\n"
    )

    stats = ingest_csv(csv_path, "ktc_community_csv", "2022-09-07", store)

    assert stats["rows_read"] == 3
    assert stats["rows_written"] == 1
    assert stats["rows_skipped"] == 2
    snapshot = store.get_snapshot("2022-09-07")
    assert len(snapshot) == 1
    assert snapshot[0]["sleeper_id"] == "123"


def test_ingest_maps_column_name_variants(tmp_path):
    store = MarketSnapshotStore(db_path=tmp_path / "test.db")
    csv_path = tmp_path / "archive.csv"
    # Non-standard but accepted names: sleeperId, sf_value, pos_rank
    csv_path.write_text(
        "sleeperId,sf_value,overall,pos_rank,pos\n"
        "123,5000,1,1,QB\n"
    )

    stats = ingest_csv(csv_path, "ktc_community_csv", "2022-09-07", store)

    assert stats["rows_written"] == 1
    row = store.get_snapshot("2022-09-07")[0]
    assert row["sleeper_id"] == "123"
    assert row["value"] == 5000
    assert row["overall_rank"] == 1
    assert row["position_rank"] == 1
    assert row["position"] == "QB"
