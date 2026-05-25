"""Task 10.4 unit tests: backtest_metrics.py statistical functions.

16 tests covering Kendall τ-b, Spearman ρ, NDCG@k, Precision@k, and HLN-DM.
All tests are pure — no I/O, no model calls, no CSV reads.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats as scipy_stats

from src.dynasty_genius.eval.backtest_artifact import TopKResult
from src.dynasty_genius.eval.backtest_metrics import (
    compute_ece,
    compute_ndcg,
    compute_precision_at_k,
    compute_rank_correlation,
    compute_subgroup_metrics,
    diebold_mariano_hln,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _monotone(n: int) -> tuple[list[float], list[float]]:
    """Perfect positive monotone pair, length n."""
    return list(range(1, n + 1)), list(range(1, n + 1))


def _reversed(n: int) -> tuple[list[float], list[float]]:
    """Perfect negative monotone pair, length n."""
    return list(range(1, n + 1)), list(range(n, 0, -1))


# ── Kendall τ-b ───────────────────────────────────────────────────────────────

def test_kendall_perfect_ranking_returns_1():
    pred, real = _monotone(15)
    tau, _, _, _ = compute_rank_correlation(pred, real)
    assert abs(tau - 1.0) < 1e-10


def test_kendall_reversed_ranking_returns_minus_1():
    pred, real = _reversed(15)
    tau, _, _, _ = compute_rank_correlation(pred, real)
    assert abs(tau - (-1.0)) < 1e-10


def test_kendall_known_result_matches_scipy():
    rng = np.random.default_rng(7)
    pred = rng.random(20).tolist()
    real = rng.random(20).tolist()
    expected = scipy_stats.kendalltau(pred, real, variant="b").statistic
    tau, _, _, _ = compute_rank_correlation(pred, real, n_bootstrap=200, rng_seed=42)
    assert abs(tau - expected) < 1e-10


def test_kendall_bca_ci_brackets_point_estimate():
    rng = np.random.default_rng(99)
    pred = rng.random(30).tolist()
    real = rng.random(30).tolist()
    tau, (ci_lo, ci_hi), _, _ = compute_rank_correlation(pred, real, n_bootstrap=500, rng_seed=42)
    assert ci_lo <= tau <= ci_hi


def test_rank_correlation_returns_nan_when_n_lt_10():
    pred = [1.0, 2.0, 3.0]
    real = [3.0, 1.0, 2.0]
    tau, (ci_lo, ci_hi), rho, (rho_lo, rho_hi) = compute_rank_correlation(pred, real)
    assert math.isnan(tau)
    assert math.isnan(ci_lo) and math.isnan(ci_hi)
    assert math.isnan(rho)
    assert math.isnan(rho_lo) and math.isnan(rho_hi)


# ── Spearman ρ ────────────────────────────────────────────────────────────────

def test_spearman_perfect_ranking_returns_1():
    pred, real = _monotone(15)
    _, _, rho, _ = compute_rank_correlation(pred, real)
    assert abs(rho - 1.0) < 1e-10


def test_spearman_known_result_matches_scipy():
    rng = np.random.default_rng(13)
    pred = rng.random(20).tolist()
    real = rng.random(20).tolist()
    expected = scipy_stats.spearmanr(pred, real).statistic
    _, _, rho, _ = compute_rank_correlation(pred, real, n_bootstrap=200, rng_seed=42)
    assert abs(rho - expected) < 1e-10


def test_spearman_bca_ci_brackets_point_estimate():
    rng = np.random.default_rng(55)
    pred = rng.random(25).tolist()
    real = rng.random(25).tolist()
    _, _, rho, (rho_lo, rho_hi) = compute_rank_correlation(pred, real, n_bootstrap=500, rng_seed=42)
    assert rho_lo <= rho <= rho_hi


# ── NDCG@k ────────────────────────────────────────────────────────────────────

def test_ndcg_perfect_ranking_returns_1():
    # Players sorted by realized PPG; model assigns rank 1 to best, etc.
    realized_ppg = [10.0, 8.0, 6.0, 4.0, 2.0]
    predicted_ranks = [1, 2, 3, 4, 5]
    assert abs(compute_ndcg(predicted_ranks, realized_ppg, k=5) - 1.0) < 1e-10


def test_ndcg_k_larger_than_list_returns_0():
    realized_ppg = [10.0, 8.0, 6.0]
    predicted_ranks = [1, 2, 3]
    assert compute_ndcg(predicted_ranks, realized_ppg, k=10) == 0.0


def test_ndcg_rank_1_error_penalized_more_than_rank_k_error():
    # 6 players; realized PPG = [12, 10, 8, 6, 4, 2], k=6
    realized_ppg = [12.0, 10.0, 8.0, 6.0, 4.0, 2.0]
    perfect = [1, 2, 3, 4, 5, 6]

    # Swap rank 1 and 2 — small positional error at the top
    swap_top = [2, 1, 3, 4, 5, 6]

    # Swap rank 1 and 6 — large positional error: best player sent to bottom slot
    swap_extremes = [6, 2, 3, 4, 5, 1]

    ndcg_perfect = compute_ndcg(perfect, realized_ppg, k=6)
    ndcg_swap_top = compute_ndcg(swap_top, realized_ppg, k=6)
    ndcg_swap_extremes = compute_ndcg(swap_extremes, realized_ppg, k=6)

    assert ndcg_perfect == 1.0
    # A rank-1 swap hurts; swapping rank 1 to rank 6 hurts far more
    assert ndcg_swap_extremes < ndcg_swap_top < ndcg_perfect


# ── Precision@k ───────────────────────────────────────────────────────────────

def test_precision_at_k_hit_rate_formula():
    k = 5
    model_top = {"a", "b", "c", "d", "e"}
    market_top = {"a", "b", "x", "y", "z"}
    realized_top = {"a", "b", "c", "f", "g"}  # model hits a,b,c; market hits a,b

    result = compute_precision_at_k(model_top, market_top, realized_top, k)
    assert isinstance(result, TopKResult)
    assert result.k == k
    assert abs(result.model_hit_rate - 3 / 5) < 1e-10
    assert abs(result.market_hit_rate - 2 / 5) < 1e-10


def test_precision_at_k_wilson_ci_bounds_valid():
    # Model gets all k right; market gets none right → diff = 1.0
    # CI for a 100% hit rate difference should be in [0, 1]
    k = 12
    players = {str(i) for i in range(k)}
    result = compute_precision_at_k(
        model_top_k=players,
        market_top_k=set(),
        realized_top_k=players,
        k=k,
    )
    lo, hi = result.diff_wilson_ci95
    assert lo >= 0.0
    assert hi <= 1.0


def test_precision_at_k_wilson_ci_can_be_negative_when_market_wins():
    k = 12
    players = {str(i) for i in range(k)}
    result = compute_precision_at_k(
        model_top_k=set(),
        market_top_k=players,
        realized_top_k=players,
        k=k,
    )
    lo, hi = result.diff_wilson_ci95
    assert result.model_hit_rate - result.market_hit_rate == -1.0
    assert lo < 0.0
    assert -1.0 <= lo <= hi <= 1.0


# ── HLN-Corrected Diebold-Mariano ─────────────────────────────────────────────

def test_dm_hln_identical_errors_returns_p_near_1():
    # If model and naive make identical errors, DM stat ≈ 0, p ≈ 1.0
    errors = [4.0, 9.0, 1.0, 16.0, 2.25, 0.25, 6.25, 3.0] * 5  # n=40
    stat, p = diebold_mariano_hln(errors, errors)
    assert abs(stat) < 1e-10
    assert abs(p - 1.0) < 1e-10


def test_dm_hln_model_clearly_better_yields_significant_p():
    # Model MSE consistently ~1.0, naive MSE consistently ~5.0 → d_bar ≈ -4.0
    rng = np.random.default_rng(42)
    n = 46
    model_err = (1.0 + rng.normal(0, 0.3, n) ** 2).tolist()
    naive_err = (5.0 + rng.normal(0, 0.3, n) ** 2).tolist()
    _, p = diebold_mariano_hln(model_err, naive_err)
    assert p < 0.10


def test_dm_hln_returns_nan_when_n_lt_4():
    stat, p = diebold_mariano_hln([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert math.isnan(stat)
    assert math.isnan(p)


# ── Phase 12 Task 12.2: Calibration + Subgroup Metrics ───────────────────────

def test_compute_ece_perfect_calibration():
    deciles = [
        (4.0, 4.0, 10),
        (8.0, 8.0, 10),
        (12.0, 12.0, 10),
    ]

    assert compute_ece(deciles) == 0.0


def test_compute_ece_known_case():
    deciles = [
        (10.0, 12.0, 10),  # |diff| = 2.0
        (15.0, 14.0, 10),  # |diff| = 1.0
        (20.0, 23.0, 10),  # |diff| = 3.0
    ]

    assert compute_ece(deciles) == pytest.approx(2.0)


def test_compute_ece_returns_nan_on_empty_input():
    assert math.isnan(compute_ece([]))


def test_compute_subgroup_metrics_returns_all_keys():
    result = compute_subgroup_metrics(
        predicted=[1.0, 2.0, 3.0, 4.0, 5.0],
        realized=[1.2, 1.9, 3.4, 3.8, 5.1],
    )

    assert set(result) == {"kendall_tau", "spearman_rho", "rmse", "n"}
    assert result["n"] == 5
    assert result["rmse"] > 0.0
    assert -1.0 <= result["kendall_tau"] <= 1.0
    assert -1.0 <= result["spearman_rho"] <= 1.0


def test_compute_subgroup_metrics_returns_nones_below_min_n():
    result = compute_subgroup_metrics(
        predicted=[1.0, 2.0, 3.0, 4.0],
        realized=[1.0, 2.0, 3.0, 4.0],
    )

    assert result == {
        "kendall_tau": None,
        "spearman_rho": None,
        "rmse": None,
        "n": 4,
    }
