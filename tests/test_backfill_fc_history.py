"""DG-020 unit tests: FantasyCalc point-in-time history backfill.

The FC API serves per-player daily value history via /trades/historical/{fcId}
(measured 2026-08-28: daily, gap-free, global window start 2025-07-01 — nothing
earlier is served). These tests pin the loader that writes that history into the
MarketSnapshotStore: provenance-tagged, idempotent, and never touching a date the
store already holds (fc_native / dp_archive dates stay exactly as recorded).

Pattern follows tests/test_snapshot_script.py: patch httpx.get, tmp_path stores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.backfill_fc_history import (
    SOURCE_TAG,
    _grid_dates,
    _normalize_series,
    _normalize_universe,
    backfill_fc_history,
)
from scripts.snapshot_fantasycalc import LEAGUE_SETTINGS_HASH
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def universe_payload():
    return [
        {
            "player": {"id": 6170, "name": "Josh Allen", "sleeperId": "4984",
                       "position": "QB"},
            "value": 10400,
        },
        {
            "player": {"id": 9821, "name": "Jahmyr Gibbs", "sleeperId": "9221",
                       "position": "RB"},
            "value": 10133,
        },
        {
            "player": {"id": 280, "name": "No Sleeper ID", "sleeperId": None,
                       "position": "TE"},
            "value": 5000,
        },
    ]


@pytest.fixture
def histories():
    # API shape: bare list of {"date": "MM/DD/YYYY", "value": int}.
    return {
        6170: [
            {"date": "07/01/2025", "value": 10411},
            {"date": "07/02/2025", "value": 10390},
            {"date": "07/03/2025", "value": 10402},
        ],
        9821: [
            {"date": "07/01/2025", "value": 7846},
            {"date": "07/02/2025", "value": 7850},
            {"date": "07/03/2025", "value": 7860},
        ],
    }


def _mock_get(universe_payload, histories):
    """One httpx.get stand-in serving both endpoints, keyed by URL."""

    def _get(url, timeout=None):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        if "/values/current" in url:
            response.json.return_value = universe_payload
            return response
        if "/trades/historical/" in url:
            fc_id = int(url.split("/trades/historical/")[1].split("?")[0])
            if fc_id not in histories:
                raise httpx.HTTPError(f"404 for {fc_id}")
            response.json.return_value = histories[fc_id]
            return response
        raise AssertionError(f"unexpected URL fetched: {url}")

    return _get


# ── Pure helpers ──────────────────────────────────────────────────────────────


def test_normalize_universe_skips_missing_sleeper_id(universe_payload):
    players = _normalize_universe(universe_payload)
    assert [(p["fc_id"], p["sleeper_id"], p["position"]) for p in players] == [
        (6170, "4984", "QB"),
        (9821, "9221", "RB"),
    ]


def test_normalize_series_converts_us_dates_to_iso():
    series = _normalize_series(
        [
            {"date": "07/02/2025", "value": 200},
            {"date": "07/01/2025", "value": 100},
            {"date": "not-a-date", "value": 300},  # malformed → skipped
            {"date": "07/03/2025", "value": "nan"},  # malformed → skipped
        ]
    )
    assert series == {"2025-07-01": 100, "2025-07-02": 200}


def test_grid_dates_daily_weekly_monthly():
    dates = [
        "2025-07-01",  # Tuesday
        "2025-07-07",  # Monday
        "2025-07-14",  # Monday
        "2025-08-01",  # Friday, first of month
    ]
    assert _grid_dates(dates, "daily") == sorted(dates)
    assert _grid_dates(dates, "weekly") == ["2025-07-07", "2025-07-14"]
    assert _grid_dates(dates, "monthly") == ["2025-07-01", "2025-08-01"]
    with pytest.raises(ValueError):
        _grid_dates(dates, "hourly")


# ── Backfill behavior ─────────────────────────────────────────────────────────


def test_backfill_writes_history_rows(tmp_path, universe_payload, histories):
    db_path = tmp_path / "test.db"
    with patch("httpx.get", side_effect=_mock_get(universe_payload, histories)):
        summary = backfill_fc_history(
            db_path=db_path, grid="daily", end_exclusive="2025-08-01"
        )

    assert summary["players_total"] == 2
    assert summary["rows_written"] == 6
    assert summary["dates_written"] == ["2025-07-01", "2025-07-02", "2025-07-03"]

    store = MarketSnapshotStore(db_path=db_path)
    rows = store.get_snapshot("2025-07-01")
    assert {r["sleeper_id"]: r["value"] for r in rows} == {
        "4984": 10411,
        "9221": 7846,
    }
    for r in rows:
        assert r["source"] == SOURCE_TAG
        assert r["league_settings_hash"] == LEAGUE_SETTINGS_HASH
        # dp_archive backfill precedent: no fabricated ranks/trend for
        # point-in-time history — the API serves values only.
        assert r["overall_rank"] is None
        assert r["position_rank"] is None
        assert r["trend_30day"] is None
    positions = {r["sleeper_id"]: r["position"] for r in rows}
    assert positions == {"4984": "QB", "9221": "RB"}


def test_backfill_never_touches_dates_already_in_store(
    tmp_path, universe_payload, histories
):
    # 2025-07-02 already holds forward-capture rows with DIFFERENT values.
    # The backfill must skip that date entirely — no immutability explosion,
    # no overwrite — and still write the other dates.
    db_path = tmp_path / "test.db"
    store = MarketSnapshotStore(db_path=db_path)
    store.append_snapshots(
        [
            {
                "snapshot_date": "2025-07-02",
                "league_settings_hash": LEAGUE_SETTINGS_HASH,
                "sleeper_id": "4984",
                "value": 9999,
                "overall_rank": 1,
                "position_rank": 1,
                "position": "QB",
                "trend_30day": 0,
                "source": "fc_native",
                "inserted_at": "2025-07-02T13:00:00+00:00",
            }
        ]
    )

    with patch("httpx.get", side_effect=_mock_get(universe_payload, histories)):
        summary = backfill_fc_history(
            db_path=db_path, grid="daily", end_exclusive="2025-08-01"
        )

    assert summary["dates_skipped_existing"] == ["2025-07-02"]
    assert summary["dates_written"] == ["2025-07-01", "2025-07-03"]
    preserved = store.get_snapshot("2025-07-02")
    assert len(preserved) == 1
    assert preserved[0]["value"] == 9999
    assert preserved[0]["source"] == "fc_native"


def test_backfill_is_idempotent_on_rerun(tmp_path, universe_payload, histories):
    db_path = tmp_path / "test.db"
    with patch("httpx.get", side_effect=_mock_get(universe_payload, histories)):
        first = backfill_fc_history(
            db_path=db_path, grid="daily", end_exclusive="2025-08-01"
        )
        second = backfill_fc_history(
            db_path=db_path, grid="daily", end_exclusive="2025-08-01"
        )

    assert first["rows_written"] == 6
    assert second["rows_written"] == 0
    assert second["dates_written"] == []
    assert second["dates_skipped_existing"] == [
        "2025-07-01",
        "2025-07-02",
        "2025-07-03",
    ]
    store = MarketSnapshotStore(db_path=db_path)
    assert store.get_coverage()["n_rows"] == 6


def test_backfill_excludes_today_by_default(tmp_path, universe_payload):
    # The forward daily capture (fc_native) owns the current day; writing it
    # from history would make the capture's later append an immutability
    # conflict. Default end_exclusive = today UTC.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_us = datetime.now(timezone.utc).strftime("%m/%d/%Y")
    histories = {
        6170: [{"date": today_us, "value": 10400}],
        9821: [{"date": today_us, "value": 10133}],
    }
    db_path = tmp_path / "test.db"
    with patch("httpx.get", side_effect=_mock_get(universe_payload, histories)):
        summary = backfill_fc_history(db_path=db_path, grid="daily")

    assert summary["rows_written"] == 0
    assert summary["dates_written"] == []
    assert not MarketSnapshotStore(db_path=db_path).has_snapshot(today)


def test_backfill_skips_player_whose_history_fetch_fails(
    tmp_path, universe_payload, histories
):
    del histories[9821]  # Gibbs history 404s → player skipped, others written
    db_path = tmp_path / "test.db"
    with patch("httpx.get", side_effect=_mock_get(universe_payload, histories)):
        summary = backfill_fc_history(
            db_path=db_path, grid="daily", end_exclusive="2025-08-01"
        )

    assert summary["players_no_history"] == 1
    assert summary["rows_written"] == 3
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2025-07-01")
    assert {r["sleeper_id"] for r in rows} == {"4984"}


def test_every_backfill_source_is_known_to_the_backtest_harness():
    """D6 pre-land review find: an fc_history_api row resolving in a future
    fold must not fall through to market_source='unavailable' or wear another
    source's label — silent provenance mislabeling of exactly this backfill."""
    from src.dynasty_genius.eval import backtest_harness as bh

    for source in ("fc_native", "dp_archive", "fc_history_api"):
        assert source in bh._MARKET_SOURCE_MAP, source
        assert bh._MARKET_SOURCE_MAP[source] in bh._MARKET_SOURCE_LABELS, source
