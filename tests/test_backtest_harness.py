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
from src.dynasty_genius.eval.backtest_harness import (
    WalkForwardDriver,
    _compute_market_ndcg,
    _market_snapshot_date,
)
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore
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


# ── Task 10.7: Market comparison integration ──────────────────────────────────
#
# RED tests — run() market_store parameter and _compute_market_ndcg do not exist yet.
# empty_store tests use module scope (one fold loop per fixture run).
# _compute_market_ndcg tests are fast pure-function unit tests.


def _make_market_rows(n: int, position: str, snapshot_date: str) -> list[dict]:
    """n synthetic market rows with sleeper_id slp_0..slp_{n-1}."""
    return [
        {
            "snapshot_date": snapshot_date,
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": float(n - i),   # slp_0 = highest value
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": position,
            "trend_30day": 0.0,
            "source": "ktc_community_csv",
            "inserted_at": "2026-01-01T00:00:00Z",
        }
        for i in range(n)
    ]


@pytest.fixture(scope="module")
def empty_store(tmp_path_factory):
    db = tmp_path_factory.mktemp("mkt") / "empty.db"
    return MarketSnapshotStore(db_path=db)


@pytest.fixture(scope="module")
def wr_run_empty_market(empty_store):
    return WalkForwardDriver(position="WR").run(market_store=empty_store, id_map={})


# Test 1: empty store → valid result, no crash
def test_empty_store_returns_valid_backtest_result(wr_run_empty_market):
    assert isinstance(wr_run_empty_market, BacktestResult)


# Test 2: empty store → all market fields remain None
def test_empty_store_market_fields_all_none(wr_run_empty_market):
    result = wr_run_empty_market
    assert result.market_source == "unavailable"
    assert result.market_snapshot_dates is None
    for fold in result.folds:
        assert fold.ndcg_at_12_model is None
        assert fold.ndcg_at_12_market is None
        assert fold.ndcg_at_24_model is None
        assert fold.ndcg_at_24_market is None


# Test 3: pool ≥ 25 → NDCG@12 and @24 both populated and in [0, 1]
def test_compute_market_ndcg_sufficient_pool(tmp_path):
    n = 25
    rows = _make_market_rows(n, "WR", "2021-09-08")
    store = MarketSnapshotStore(db_path=tmp_path / "s25.db")
    store.upsert_snapshots(rows)
    market_rows = store.get_ranked("2021-09-08", "WR")

    rng = np.random.default_rng(7)
    y_pred = rng.random(n)
    y_realized = rng.random(n)
    id_map = {f"gsis_{i}": f"slp_{i}" for i in range(n)}
    player_ids = [f"gsis_{i}" for i in range(n)]

    result = _compute_market_ndcg(
        y_pred=y_pred,
        player_ids=player_ids,
        y_realized=y_realized,
        market_rows=market_rows,
        id_map=id_map,
    )

    for key in ["ndcg_at_12_model", "ndcg_at_12_market", "ndcg_at_24_model", "ndcg_at_24_market"]:
        assert result[key] is not None, f"{key} should be set for pool=25"
        assert 0.0 <= result[key] <= 1.0, f"{key}={result[key]} out of [0, 1]"


# Test 4: pool = 15 → @12 set, @24 None (15 < 24)
def test_compute_market_ndcg_pool_below_24_sets_ndcg12_only(tmp_path):
    n = 15
    rows = _make_market_rows(n, "WR", "2021-09-08")
    store = MarketSnapshotStore(db_path=tmp_path / "s15.db")
    store.upsert_snapshots(rows)
    market_rows = store.get_ranked("2021-09-08", "WR")

    rng = np.random.default_rng(3)
    y_pred = rng.random(n)
    y_realized = rng.random(n)
    id_map = {f"gsis_{i}": f"slp_{i}" for i in range(n)}
    player_ids = [f"gsis_{i}" for i in range(n)]

    result = _compute_market_ndcg(
        y_pred=y_pred,
        player_ids=player_ids,
        y_realized=y_realized,
        market_rows=market_rows,
        id_map=id_map,
    )

    assert result["ndcg_at_12_model"] is not None
    assert result["ndcg_at_12_market"] is not None
    assert result["ndcg_at_24_model"] is None
    assert result["ndcg_at_24_market"] is None


# Test 5: 20 players, 5 without sleeper map → pool=15; unmatched excluded from market only
def test_compute_market_ndcg_excludes_unmatched_gsis(tmp_path):
    n_matched = 15
    n_total = 20
    rows = _make_market_rows(n_matched, "WR", "2021-09-08")
    store = MarketSnapshotStore(db_path=tmp_path / "s_exc.db")
    store.upsert_snapshots(rows)
    market_rows = store.get_ranked("2021-09-08", "WR")

    rng = np.random.default_rng(5)
    y_pred = rng.random(n_total)
    y_realized = rng.random(n_total)
    # Only first 15 gsis IDs have a sleeper mapping — last 5 are unmapped
    id_map = {f"gsis_{i}": f"slp_{i}" for i in range(n_matched)}
    player_ids = [f"gsis_{i}" for i in range(n_total)]

    result = _compute_market_ndcg(
        y_pred=y_pred,
        player_ids=player_ids,
        y_realized=y_realized,
        market_rows=market_rows,
        id_map=id_map,
    )

    # Pool = 15 (n_matched), so @12 is set but @24 is None
    assert result["ndcg_at_12_model"] is not None   # pool=15 ≥ 12
    assert result["ndcg_at_24_model"] is None        # pool=15 < 24


# Test 6: snapshot date formula — Sep 8 of test_year + 1 for all 4 folds
def test_snapshot_date_formula():
    assert _market_snapshot_date(2020) == "2021-09-08"
    assert _market_snapshot_date(2021) == "2022-09-08"
    assert _market_snapshot_date(2022) == "2023-09-08"
    assert _market_snapshot_date(2023) == "2024-09-08"
