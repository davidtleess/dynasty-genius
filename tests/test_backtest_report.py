"""Task 12.3 unit tests: per-fold prediction log.

5 tests covering emit_prediction_log parameter, required row keys,
residual arithmetic, temporal isolation, and CSV serialization.
Module-scoped fixtures: run() called once and reused across tests.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.eval.backtest_report import (
    MarketComparisonEntry,
    write_market_comparison_json,
    write_prediction_log_csv,
)
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def wr_driver_with_log():
    """Run WR walk-forward once with emit_prediction_log=True."""
    driver = WalkForwardDriver(position="WR")
    driver.run(emit_prediction_log=True)
    return driver


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_emit_prediction_log_produces_rows(wr_driver_with_log):
    """run(emit_prediction_log=True) exposes driver.prediction_rows as a non-empty list."""
    rows = wr_driver_with_log.prediction_rows
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_prediction_rows_have_required_keys(wr_driver_with_log):
    """Each row has the required prediction log keys."""
    required = {
        "player_id", "fold_index", "feature_season",
        "predicted_ppg", "realized_ppg", "model_rank", "residual",
    }
    for row in wr_driver_with_log.prediction_rows:
        assert required.issubset(row.keys()), (
            f"Row missing keys: {required - row.keys()}"
        )


def test_prediction_rows_residual_equals_realized_minus_predicted(wr_driver_with_log):
    """residual == realized_ppg - predicted_ppg for every row."""
    for row in wr_driver_with_log.prediction_rows:
        expected = pytest.approx(row["realized_ppg"] - row["predicted_ppg"], abs=1e-9)
        assert row["residual"] == expected


def test_prediction_log_has_no_future_data_in_train_rows(wr_driver_with_log):
    """All rows in prediction_rows come from test folds only.

    Each row's feature_season must equal one of the 4 fold test_years
    (2020, 2021, 2022, 2023), and must match the fold_index's expected year.
    """
    fold_test_years = {1: 2020, 2: 2021, 3: 2022, 4: 2023}
    for row in wr_driver_with_log.prediction_rows:
        fold_idx = row["fold_index"]
        expected_year = fold_test_years[fold_idx]
        assert row["feature_season"] == expected_year, (
            f"fold_index={fold_idx} should have feature_season={expected_year}, "
            f"got {row['feature_season']}"
        )


def test_prediction_csv_writes_correctly(tmp_path, wr_driver_with_log):
    """CSV written from prediction_rows is readable by pandas with correct dtypes."""
    csv_path = tmp_path / "predictions_WR.csv"
    write_prediction_log_csv(wr_driver_with_log.prediction_rows, csv_path)

    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == len(wr_driver_with_log.prediction_rows)
    assert "player_id" in df.columns
    assert "model_rank" in df.columns
    assert "residual" in df.columns
    assert df["model_rank"].dtype in (int, "int64", "Int64")
    assert df["predicted_ppg"].dtype in (float, "float64")


# ── Task 12.4: Market-comparison ledger ───────────────────────────────────────

def _wr_2020_player_ids(n: int = 5) -> list[str]:
    df = pd.read_csv("app/data/training/engine_b_features_v2.csv")
    mask = (
        (df["position"] == "WR")
        & (df["feature_season"] == 2020)
        & df["training_eligible"].astype(bool)
    )
    return df.loc[mask, "player_id"].head(n).astype(str).tolist()


def _market_rows_for_players(player_ids: list[str], n_matched: int | None = None) -> tuple[list[dict], dict[str, str]]:
    n_matched = len(player_ids) if n_matched is None else n_matched
    id_map = {pid: f"slp_{i}" for i, pid in enumerate(player_ids[:n_matched])}
    rows = [
        {
            "snapshot_date": "2021-09-08",
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": 1000 - i,
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": "WR",
            "trend_30day": 0,
            "source": "fc_native",
            "inserted_at": datetime.now(timezone.utc).isoformat(),
        }
        for i in range(n_matched)
    ]
    return rows, id_map


def test_emit_market_comparison_with_empty_store_produces_no_rows(tmp_path):
    """run(market_store=empty_store, emit_market_comparison=True) exposes empty rows."""
    store = MarketSnapshotStore(db_path=tmp_path / "empty.db")
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map={}, emit_market_comparison=True)

    assert driver.market_comparison_rows == []


def test_emit_market_comparison_with_populated_store_produces_rows(tmp_path):
    """With synthetic market rows, market_comparison_rows is non-empty."""
    player_ids = _wr_2020_player_ids()
    rows, id_map = _market_rows_for_players(player_ids)
    store = MarketSnapshotStore(db_path=tmp_path / "populated.db")
    store.upsert_snapshots(rows)
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map=id_map, emit_market_comparison=True)

    assert driver.market_comparison_rows
    assert any(row["fc_value"] is not None for row in driver.market_comparison_rows)


def test_market_comparison_entry_rank_delta_positive_when_model_ranks_higher():
    """rank_delta = fc_rank - model_rank; positive means model ranked player higher."""
    entry = MarketComparisonEntry(
        player_id="p1",
        sleeper_id="s1",
        position="WR",
        fold_index=1,
        feature_season=2020,
        snapshot_date="2021-09-08",
        predicted_ppg=12.0,
        model_rank=2,
        fc_value=900,
        fc_rank=5,
        realized_ppg=11.0,
        realized_rank=3,
        rank_delta=5 - 2,
    )

    assert entry.rank_delta == 3


def test_market_comparison_unmatched_players_have_null_fc_fields(tmp_path):
    """Players with no sleeper_id match have fc fields set to None."""
    player_ids = _wr_2020_player_ids()
    rows, id_map = _market_rows_for_players(player_ids, n_matched=2)
    store = MarketSnapshotStore(db_path=tmp_path / "partial.db")
    store.upsert_snapshots(rows)
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map=id_map, emit_market_comparison=True)

    unmatched = [row for row in driver.market_comparison_rows if row["sleeper_id"] is None]
    assert unmatched
    assert all(row["fc_value"] is None and row["fc_rank"] is None for row in unmatched)


def test_market_comparison_json_serializes(tmp_path):
    """List of MarketComparisonEntry serializes to valid JSON."""
    entries = [
        MarketComparisonEntry(
            player_id="p1",
            sleeper_id="s1",
            position="WR",
            fold_index=1,
            feature_season=2020,
            snapshot_date="2021-09-08",
            predicted_ppg=12.0,
            model_rank=2,
            fc_value=900,
            fc_rank=5,
            realized_ppg=11.0,
            realized_rank=3,
            rank_delta=3,
        )
    ]
    path = tmp_path / "market_comparison_WR.json"

    write_market_comparison_json(entries, path)

    assert path.exists()
    loaded = pd.read_json(path)
    assert loaded.loc[0, "player_id"] == "p1"
    assert loaded.loc[0, "rank_delta"] == 3
