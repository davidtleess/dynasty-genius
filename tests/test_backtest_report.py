"""Task 12.3 unit tests: per-fold prediction log.

5 tests covering emit_prediction_log parameter, required row keys,
residual arithmetic, temporal isolation, and CSV serialization.
Module-scoped fixtures: run() called once and reused across tests.
"""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.eval.backtest_report import write_prediction_log_csv


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
