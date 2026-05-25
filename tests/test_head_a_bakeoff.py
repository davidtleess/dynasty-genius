"""TDD tests for Phase 19 W3 Head A v3 bake-off harness.

Covers: standard scaling, temporal isolation, gate calculations, NDCG@10,
censored-row exclusion, TE safety guard, row alignment, and OOF RMSE.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.run_head_a_bakeoff import (
    _aggregate_folds,
    _build_aligned_fold,
    _filter_available_features,
    _filter_training_rows,
    compute_ndcg_at_k,
    compute_oof_rmse_from_folds,
    evaluate_head_a_gates,
    scale_features,
)

# ── 1. Standard Scaling ───────────────────────────────────────────────────────

def test_scale_features_train_zero_mean_unit_variance():
    """Scaled training features must have zero mean and unit variance per column."""
    X_train = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0]])
    X_test = np.array([[2.5, 25.0]])
    X_train_s, _ = scale_features(X_train, X_test)
    np.testing.assert_allclose(X_train_s.mean(axis=0), [0.0, 0.0], atol=1e-10)
    np.testing.assert_allclose(X_train_s.std(axis=0, ddof=0), [1.0, 1.0], atol=1e-10)


def test_scale_features_test_uses_train_statistics():
    """Test features are scaled using train mean/std, not their own distribution."""
    X_train = np.array([[0.0], [2.0]])   # mean=1.0, std=1.0
    X_test = np.array([[3.0]])           # (3-1)/1 = 2.0 if using train stats
    _, X_test_s = scale_features(X_train, X_test)
    assert X_test_s[0, 0] == pytest.approx(2.0, abs=1e-9)


# ── 2. Temporal Isolation ─────────────────────────────────────────────────────

def test_filter_training_rows_excludes_test_year_and_beyond():
    """Training rows must not include any season >= the test year boundary."""
    rows = [
        {"season": "2016", "censored_incomplete_arc": "0", "best3of4_ppg": "10"},
        {"season": "2017", "censored_incomplete_arc": "0", "best3of4_ppg": "8"},
        {"season": "2018", "censored_incomplete_arc": "0", "best3of4_ppg": "12"},  # future
        {"season": "2019", "censored_incomplete_arc": "0", "best3of4_ppg": "9"},   # future
    ]
    result = _filter_training_rows(rows, train_max_year=2017)
    seasons = {int(r["season"]) for r in result}
    assert seasons == {2016, 2017}
    assert 2018 not in seasons
    assert 2019 not in seasons


def test_filter_training_rows_excludes_censored_incomplete_arc():
    """Rows with censored_incomplete_arc='1' must be dropped from the training set."""
    rows = [
        {"season": "2017", "censored_incomplete_arc": "0", "best3of4_ppg": "10"},
        {"season": "2017", "censored_incomplete_arc": "1", "best3of4_ppg": "11"},  # censored
        {"season": "2016", "censored_incomplete_arc": "1", "best3of4_ppg": "9"},   # censored
    ]
    result = _filter_training_rows(rows, train_max_year=2017)
    assert len(result) == 1
    assert result[0]["censored_incomplete_arc"] == "0"


# ── 3. Gate Calculations ──────────────────────────────────────────────────────

def test_gate_passes_when_exactly_two_of_three_metrics_clear():
    """A candidate passes when exactly 2 of 3 core metrics clear (2-of-3 rule)."""
    result = evaluate_head_a_gates(
        baseline_rmse=3.0,
        candidate_rmse=2.9,           # ≥2% improvement → PASS  (3.33%)
        baseline_spearman=0.60,
        candidate_spearman=0.62,      # improvement → PASS
        baseline_ndcg=0.70,
        candidate_ndcg=0.68,          # regression → FAIL
        te_mae_delta=0.0,
    )
    assert result.passes is True
    assert result.metrics_passed == 2


def test_gate_fails_when_fewer_than_two_metrics_clear():
    """A candidate fails when only 1 of 3 core metrics improves."""
    result = evaluate_head_a_gates(
        baseline_rmse=3.0,
        candidate_rmse=2.99,          # < 2% improvement → FAIL (0.33%)
        baseline_spearman=0.60,
        candidate_spearman=0.58,      # regression → FAIL
        baseline_ndcg=0.70,
        candidate_ndcg=0.72,          # improvement → PASS
        te_mae_delta=0.0,
    )
    assert result.passes is False
    assert result.metrics_passed < 2


def test_te_safety_guard_blocks_promotion_on_te_regression():
    """TE safety guard must override the 2-of-3 pass if TE MAE regresses >1%."""
    result = evaluate_head_a_gates(
        baseline_rmse=3.0,
        candidate_rmse=2.85,          # 5% improvement → PASS
        baseline_spearman=0.60,
        candidate_spearman=0.65,      # improvement → PASS
        baseline_ndcg=0.70,
        candidate_ndcg=0.75,          # improvement → PASS
        te_mae_delta=0.015,           # 1.5% TE regression → safety guard fires
    )
    assert result.passes is False
    assert "te_safety_guard" in result.fail_reasons


# ── 4. NDCG@10 Calculation ────────────────────────────────────────────────────

def test_ndcg_at_k_perfect_ranking_returns_one():
    """Perfect ranking (pred order = true value order) must yield NDCG@10 = 1.0."""
    y_true = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 1.0, 0.5, 0.3, 0.1, 0.0, -1.0])
    y_pred = y_true.copy()
    score = compute_ndcg_at_k(y_true, y_pred, k=10)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_filter_available_features_drops_low_coverage_columns():
    """Features with <50% coverage in the eligible cohort must be dropped."""
    rows = [
        {"position": "WR", "season": "2018", "censored_incomplete_arc": "0",
         "nfl_pick": "5", "wr_dominator_final": "0.40", "ryptpa": None},
        {"position": "WR", "season": "2018", "censored_incomplete_arc": "0",
         "nfl_pick": "15", "wr_dominator_final": "0.30", "ryptpa": None},
        {"position": "WR", "season": "2018", "censored_incomplete_arc": "0",
         "nfl_pick": "30", "wr_dominator_final": "0.25", "ryptpa": None},
    ]
    candidate = ["nfl_pick", "wr_dominator_final", "ryptpa"]
    available = _filter_available_features(rows, candidate, min_coverage_pct=50.0)
    assert "ryptpa" not in available
    assert "nfl_pick" in available
    assert "wr_dominator_final" in available


def test_ndcg_at_k_inverted_ranking_scores_below_one():
    """Inverted ranking (worst predicted as best) must yield NDCG@10 < 1.0."""
    y_true = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 1.0, 0.5, 0.3, 0.1, 0.0])
    y_pred = y_true[::-1].copy()     # reverse order
    score = compute_ndcg_at_k(y_true, y_pred, k=10)
    assert score < 1.0


# ── 5. OOF RMSE (weighted by fold size, not equal-weight fold average) ────────

def test_oof_rmse_weighted_by_fold_size_differs_from_equal_weight_average():
    """Pooled OOF RMSE must reflect fold sizes, not treat each fold equally."""
    # Fold 1: 10 predictions, residual = 2.0 each → fold RMSE = 2.0
    fold1 = [{"y_true": 5.0, "y_pred": 3.0}] * 10
    # Fold 2: 90 predictions, residual = 6.0 each → fold RMSE = 6.0
    fold2 = [{"y_true": 5.0, "y_pred": -1.0}] * 90

    # Equal-weight average: (2.0 + 6.0) / 2 = 4.0
    # True OOF: sqrt((10*4 + 90*36) / 100) = sqrt(3280/100) = sqrt(32.8) ≈ 5.727
    expected_oof = math.sqrt((10 * 4 + 90 * 36) / 100)
    result = compute_oof_rmse_from_folds([fold1, fold2])
    assert result == pytest.approx(expected_oof, abs=1e-6)
    assert result != pytest.approx(4.0, abs=0.1)  # must not be the naive average


# ── 6. NDCG uses direct PPG relevance (repo convention) ──────────────────────

def test_ndcg_uses_direct_ppg_relevance_matching_repo_backtest_metrics():
    """NDCG must use y_true directly as relevance, not 2^y_true - 1 (repo convention)."""
    y_true = np.array([10.0, 8.0, 2.0])
    # Predicted: player 2 ranked first, player 1 second (inverted top-2)
    y_pred = np.array([8.0, 10.0, 2.0])

    # Direct-PPG DCG  = 8/log2(2) + 10/log2(3) + 2/log2(4) ≈ 15.31
    # Direct-PPG IDCG = 10/log2(2) + 8/log2(3) + 2/log2(4) ≈ 16.05
    expected_direct = (
        8.0 / np.log2(2) + 10.0 / np.log2(3) + 2.0 / np.log2(4)
    ) / (
        10.0 / np.log2(2) + 8.0 / np.log2(3) + 2.0 / np.log2(4)
    )
    assert compute_ndcg_at_k(y_true, y_pred, k=3) == pytest.approx(expected_direct, abs=1e-6)


# ── 7. TE safety guard: exact 1% boundary ────────────────────────────────────

def test_te_safety_guard_exactly_one_percent_does_not_block():
    """Exactly 1.0% MAE regression (te_mae_delta=0.01) must NOT block (spec: >1.0%)."""
    result = evaluate_head_a_gates(
        baseline_rmse=3.0,
        candidate_rmse=2.7,
        baseline_spearman=0.60,
        candidate_spearman=0.65,
        baseline_ndcg=0.70,
        candidate_ndcg=0.75,
        te_mae_delta=0.01,  # exactly 1.0% as a fraction — should not trigger
    )
    assert result.te_safety_blocked is False


# ── 8. Row alignment ──────────────────────────────────────────────────────────

def test_aligned_fold_excludes_rows_missing_enriched_features():
    """Aligned fold must exclude test rows where any candidate feature is missing."""
    test_rows = [
        {"nfl_pick": "5",  "final_college_age": "21", "rb_final_dominator": "0.30"},
        {"nfl_pick": "15", "final_college_age": "22", "rb_final_dominator": ""},    # missing
        {"nfl_pick": "25", "final_college_age": "23", "rb_final_dominator": "0.20"},
    ]
    baseline_feats = ["nfl_pick", "final_college_age"]
    candidate_feats = ["nfl_pick", "final_college_age", "rb_final_dominator"]

    _, aligned_test = _build_aligned_fold([], test_rows, baseline_feats, candidate_feats)
    # The row with empty rb_final_dominator must be excluded
    assert len(aligned_test) == 2
    assert all(_to_float(r.get("rb_final_dominator")) is not None for r in aligned_test)


def _to_float(value: object) -> float | None:
    """Local helper matching the script's _to_float for use in test assertions."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _make_fold(
    train_max_year: int,
    test_year: int,
    spearman: float,
    ndcg_at_10: float,
    oof_predictions: list[dict],
) -> dict:
    """Minimal fold-result dict matching the shape returned by _run_aligned_comparison."""
    n = len(oof_predictions)
    rmse = math.sqrt(
        sum((p["y_true"] - p["y_pred"]) ** 2 for p in oof_predictions) / max(n, 1)
    )
    return {
        "train_max_year": train_max_year,
        "test_year": test_year,
        "n_train": 50,
        "n_test": n,
        "rmse": round(rmse, 4),
        "spearman": spearman,
        "ndcg_at_10": ndcg_at_10,
        "best_alpha": None,
        "oof_predictions": oof_predictions,
    }


# ── 9. Fold-level rank aggregation ────────────────────────────────────────────

def test_aggregate_folds_exposes_mean_fold_spearman_and_ndcg():
    """_aggregate_folds must return mean_fold_spearman and mean_fold_ndcg_at_10
    as unweighted means of per-fold values, for use as gate inputs."""
    fold1 = _make_fold(2017, 2018, spearman=0.40, ndcg_at_10=0.70,
                       oof_predictions=[{"y_true": 5.0, "y_pred": 4.0}])
    fold2 = _make_fold(2018, 2019, spearman=0.80, ndcg_at_10=0.90,
                       oof_predictions=[{"y_true": 5.0, "y_pred": 5.5}])
    result = _aggregate_folds([fold1, fold2])
    assert result["mean_fold_spearman"] == pytest.approx(0.60, abs=1e-6)
    assert result["mean_fold_ndcg_at_10"] == pytest.approx(0.80, abs=1e-6)


def test_pooled_oof_spearman_diverges_from_mean_fold_spearman():
    """Pooled OOF Spearman inflates when draft-class PPG ranges differ across folds
    (Simpson's paradox). mean_fold_spearman must reflect within-class quality."""
    # Fold 1: 2-player class, candidate inverts true rank → per-fold Spearman = -1.0
    fold1 = _make_fold(2017, 2018, spearman=-1.0, ndcg_at_10=0.5, oof_predictions=[
        {"y_true": 10.0, "y_pred": 9.0},
        {"y_true": 8.0,  "y_pred": 10.0},
    ])
    # Fold 2: 4-player class, perfect prediction → per-fold Spearman = 1.0
    fold2 = _make_fold(2018, 2019, spearman=1.0, ndcg_at_10=1.0, oof_predictions=[
        {"y_true": 3.0, "y_pred": 3.0},
        {"y_true": 2.0, "y_pred": 2.0},
        {"y_true": 1.0, "y_pred": 1.0},
        {"y_true": 0.0, "y_pred": 0.0},
    ])
    result = _aggregate_folds([fold1, fold2])
    # Mean-fold: (-1.0 + 1.0) / 2 = 0.0
    assert result["mean_fold_spearman"] == pytest.approx(0.0, abs=0.01)
    # Pooled OOF: much higher due to cross-class range inflation (≈ 0.94)
    assert result["oof_spearman"] > 0.5
    # The two must diverge meaningfully
    assert abs(result["mean_fold_spearman"] - result["oof_spearman"]) > 0.4


def test_spearman_gate_correctly_fails_when_mean_fold_spearman_regresses():
    """When mean-fold Spearman is lower for candidate than baseline, the gate must
    fail even if pooled OOF Spearman appears to improve (Codex-identified scenario)."""
    # Per-fold values from Codex review of TE Ridge result:
    # Baseline folds: 0.1469, 0.8667, 0.8333, 0.5333 → mean = 0.5951
    # Candidate folds: 0.3357, 0.7212, 0.7667, 0.5500 → mean = 0.5934
    baseline_folds = [
        _make_fold(2017 + i, 2018 + i, spearman=s, ndcg_at_10=0.70,
                   oof_predictions=[{"y_true": 5.0, "y_pred": 5.0}])
        for i, s in enumerate([0.1469, 0.8667, 0.8333, 0.5333])
    ]
    candidate_folds = [
        _make_fold(2017 + i, 2018 + i, spearman=s, ndcg_at_10=0.75,
                   oof_predictions=[{"y_true": 5.0, "y_pred": 4.8}])
        for i, s in enumerate([0.3357, 0.7212, 0.7667, 0.5500])
    ]
    base_agg = _aggregate_folds(baseline_folds)
    cand_agg = _aggregate_folds(candidate_folds)
    assert cand_agg["mean_fold_spearman"] < base_agg["mean_fold_spearman"]
    gate = evaluate_head_a_gates(
        baseline_rmse=3.0, candidate_rmse=2.7,          # RMSE passes (10%)
        baseline_spearman=base_agg["mean_fold_spearman"],
        candidate_spearman=cand_agg["mean_fold_spearman"],
        baseline_ndcg=0.70, candidate_ndcg=0.75,         # NDCG passes
        te_mae_delta=0.0,
    )
    assert gate.spearman_gate is False
    assert gate.passes is True                            # still 2/3 (RMSE + NDCG)


def test_aggregate_folds_preserves_per_player_oof_predictions():
    """_aggregate_folds must return oof_predictions_all with every per-player
    prediction from all folds, enabling per-player residual OOF logging."""
    fold1 = _make_fold(2017, 2018, spearman=0.5, ndcg_at_10=0.7, oof_predictions=[
        {"y_true": 5.0, "y_pred": 4.0},
        {"y_true": 3.0, "y_pred": 3.5},
    ])
    fold2 = _make_fold(2018, 2019, spearman=0.6, ndcg_at_10=0.8, oof_predictions=[
        {"y_true": 8.0, "y_pred": 7.0},
    ])
    result = _aggregate_folds([fold1, fold2])
    assert "oof_predictions_all" in result
    assert len(result["oof_predictions_all"]) == 3
