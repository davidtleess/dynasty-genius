"""Tests for Phase 16.4 WR college bake-off gate logic."""
import pytest
import numpy as np
from scripts.run_wr_college_bakeoff import (
    evaluate_promotion_gate,
    compute_vif,
    BakeoffGateResult,
)


def test_gate_passes_all_criteria():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.8,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.005,
    )
    assert result.passes is True
    # mae_improvement_pct is rounded to 4 decimal places in the implementation
    assert result.mae_improvement_pct == pytest.approx((3.0 - 2.8) / 3.0 * 100, abs=1e-3)


def test_gate_fails_insufficient_mae_improvement():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.95,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.0,
    )
    assert result.passes is False
    assert "mae_improvement" in result.fail_reasons


def test_gate_fails_insufficient_folds():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=2,
        total_folds=4,
        te_mae_delta=0.0,
    )
    assert result.passes is False
    assert "fold_consistency" in result.fail_reasons


def test_gate_fails_te_regression():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.015,
    )
    assert result.passes is False
    assert "te_regression" in result.fail_reasons


def test_gate_te_delta_threshold():
    # exactly 1% regression: fails
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.01,
    )
    assert result.passes is False

    # just under 1%: passes
    result2 = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.7,
        folds_improved=4,
        total_folds=4,
        te_mae_delta=0.0099,
    )
    assert result2.passes is True


def test_gate_multiple_fail_reasons_accumulated():
    result = evaluate_promotion_gate(
        baseline_mae=3.0,
        candidate_mae=2.99,  # < 3% improvement
        folds_improved=1,    # < 3 folds
        total_folds=4,
        te_mae_delta=0.05,   # > 1% TE regression
    )
    assert result.passes is False
    assert "mae_improvement" in result.fail_reasons
    assert "fold_consistency" in result.fail_reasons
    assert "te_regression" in result.fail_reasons


def test_compute_vif_uncorrelated():
    rng = np.random.default_rng(42)
    X = rng.normal(size=(100, 2))
    vif = compute_vif(X, feature_idx=0)
    assert vif < 3.0


def test_compute_vif_collinear():
    rng = np.random.default_rng(42)
    base = rng.normal(size=100)
    X = np.column_stack([base, base + rng.normal(scale=0.1, size=100)])
    vif = compute_vif(X, feature_idx=0)
    assert vif > 5.0
