"""Task 10.3 + 10.5 unit tests: WalkForwardDriver.

Task 10.3 (7 tests): _build_fold_data feature isolation.
Task 10.5 (15 tests): run() contract — BacktestResult shape, fold counts,
    alpha, retrain_mode, metric bounds, market fields all None, no model leak.

All use the real engine_b_features_v2.csv — no mocking needed.

Expected counts verified against the CSV before writing these tests:
  WR: n_train=[294,454,607,754], n_test=[160,153,147,153]
  QB: n_train=[80,123,169,215],  n_test=[43,46,46,49]
  RB: n_train=[191,289,387,483], n_test=[98,98,96,90]
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.backtest_artifact import BacktestResult
from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.models.engine_b_contract import OUTCOME_COLUMN

CSV_PATH = "app/data/training/engine_b_features_v2.csv"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV_PATH)


@pytest.fixture(scope="module")
def driver_wr():
    return WalkForwardDriver(position="WR")


@pytest.fixture(scope="module")
def driver_qb():
    return WalkForwardDriver(position="QB")


# ── Test 1: Train set contains only feature_season < test_year and eligible ───

def test_train_row_count_matches_prior_seasons_only(driver_wr, df):
    X_train, X_test = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    # WR rows with feature_season in {2018, 2019} and training_eligible=True
    assert X_train.shape[0] == 294


# ── Test 2: Test set contains only feature_season == test_year and eligible ───

def test_test_row_count_matches_test_year_only(driver_wr, df):
    X_train, X_test = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    # WR rows with feature_season == 2020 and training_eligible=True
    assert X_test.shape[0] == 160


# ── Test 3: No future-season rows in train (expanding window is clean) ────────

def test_train_excludes_future_seasons(driver_wr, df):
    # Fold 2 test_year=2021: train must NOT include 2021 rows.
    # If 2021 were included, n_train would be 607 (through 2021), not 454.
    X_train, X_test = driver_wr._build_fold_data(df, test_year=2021, position="WR")
    assert X_train.shape[0] == 454   # 2018+2019+2020 WR eligible rows


# ── Test 4: avg_ppg_t1_t2 is absent from X_train and X_test ──────────────────

def test_outcome_column_absent_from_feature_matrices(driver_wr, df):
    X_train, X_test = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    assert OUTCOME_COLUMN not in X_train.columns
    assert OUTCOME_COLUMN not in X_test.columns


# ── Test 5: Scaler is fit on train only ───────────────────────────────────────

def test_scaler_fit_on_train_only(driver_wr, df):
    X_train, X_test = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    # StandardScaler fit on train → X_train columns have mean ≈ 0
    assert abs(X_train["ppg_t"].mean()) < 1e-10
    # X_test was transformed by the train-fit scaler, so its mean is not zero
    # (2020 WR ppg_t distribution differs from 2018-2019)
    assert abs(X_test["ppg_t"].mean()) > 0.01


# ── Test 6: Position filter includes only the requested position ──────────────

def test_position_filter_isolates_position(driver_qb, driver_wr, df):
    X_train_wr, X_test_wr = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    X_train_qb, X_test_qb = driver_qb._build_fold_data(df, test_year=2020, position="QB")
    # Counts must match position-specific expected values (no cross-position rows)
    assert X_train_wr.shape[0] == 294
    assert X_train_qb.shape[0] == 80
    assert X_test_wr.shape[0] == 160
    assert X_test_qb.shape[0] == 43
    # Feature sets differ by position (QB has cpoe etc, WR has yprr etc)
    assert set(X_train_wr.columns) != set(X_train_qb.columns)


# ── Test 7: Imputation uses train fold mean — no nulls survive to X ──────────

def test_no_nulls_in_output_matrices(driver_wr, df):
    # ppg_t_minus_2 has ~38% nulls in the raw WR data — imputation must fill them.
    raw_wr = df[(df["position"] == "WR") & (df["training_eligible"])]
    assert raw_wr["ppg_t_minus_2"].isnull().any(), "precondition: raw data has nulls"

    X_train, X_test = driver_wr._build_fold_data(df, test_year=2020, position="WR")
    assert X_train.isnull().sum().sum() == 0
    assert X_test.isnull().sum().sum() == 0


# ── Task 10.5: WalkForwardDriver.run() contract ───────────────────────────────
#
# RED tests — WalkForwardDriver.run() does not exist yet.
# Module-scoped fixtures: run() is called once per position and reused.


@pytest.fixture(scope="module")
def wr_run():
    driver = WalkForwardDriver(position="WR")
    result = driver.run()
    return driver, result


@pytest.fixture(scope="module")
def qb_run():
    driver = WalkForwardDriver(position="QB")
    result = driver.run()
    return driver, result


@pytest.fixture(scope="module")
def rb_run():
    driver = WalkForwardDriver(position="RB")
    result = driver.run()
    return driver, result


def test_run_returns_backtest_result(wr_run):
    _, result = wr_run
    assert isinstance(result, BacktestResult)


def test_run_produces_exactly_4_folds(wr_run):
    _, result = wr_run
    assert len(result.folds) == 4


def test_run_n_train_increases_each_fold(wr_run):
    _, result = wr_run
    n_trains = [f.n_train for f in result.folds]
    assert n_trains == sorted(n_trains), f"n_train must be strictly increasing: {n_trains}"


def test_run_wr_n_train_per_fold(wr_run):
    _, result = wr_run
    assert [f.n_train for f in result.folds] == [294, 454, 607, 754]


def test_run_wr_n_test_per_fold(wr_run):
    _, result = wr_run
    assert [f.n_test for f in result.folds] == [160, 153, 147, 153]


def test_run_qb_n_test_per_fold(qb_run):
    _, result = qb_run
    assert [f.n_test for f in result.folds] == [43, 46, 46, 49]


def test_run_rb_n_test_per_fold(rb_run):
    _, result = rb_run
    assert [f.n_test for f in result.folds] == [98, 98, 96, 90]


def test_run_fixed_alpha_wr(wr_run):
    _, result = wr_run
    assert result.ridge_alpha == 200.0


def test_run_fixed_alpha_qb(qb_run):
    _, result = qb_run
    assert result.ridge_alpha == 1000.0


def test_run_retrain_mode(wr_run):
    _, result = wr_run
    assert result.retrain_mode == "refit_per_fold_fixed_alpha"


def test_run_fold_kendall_bounded(wr_run):
    _, result = wr_run
    for fold in result.folds:
        assert -1.0 <= fold.kendall_tau <= 1.0, (
            f"fold {fold.fold_index}: kendall_tau={fold.kendall_tau} out of range"
        )


def test_run_fold_spearman_bounded(wr_run):
    _, result = wr_run
    for fold in result.folds:
        assert -1.0 <= fold.spearman_rho <= 1.0, (
            f"fold {fold.fold_index}: spearman_rho={fold.spearman_rho} out of range"
        )


def test_run_fold_rmse_and_mae_positive(wr_run):
    _, result = wr_run
    for fold in result.folds:
        assert fold.rmse > 0.0, f"fold {fold.fold_index}: rmse={fold.rmse}"
        assert fold.mae > 0.0, f"fold {fold.fold_index}: mae={fold.mae}"


def test_run_market_fields_all_none(wr_run):
    _, result = wr_run
    assert result.market_source == "unavailable"
    assert result.market_snapshot_dates is None
    assert result.divergence_validity is None
    for fold in result.folds:
        assert fold.ndcg_at_12_model is None
        assert fold.ndcg_at_12_market is None
        assert fold.ndcg_at_24_model is None
        assert fold.ndcg_at_24_market is None
        assert fold.precision_at_k is None


def test_run_no_fitted_model_state_after_run(wr_run):
    driver, _ = wr_run
    assert not hasattr(driver, "_ridge")
    assert not hasattr(driver, "_fitted_model")
    assert not hasattr(driver, "_fitted_ridge")
