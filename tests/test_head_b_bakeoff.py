"""TDD tests for Phase 19 W4 Head B v3 bake-off harness.

RED suite — all tests must fail before scripts/run_head_b_bakeoff.py exists.

Covers: Head B leakage enforcement, residual R² mandatory gate, coefficient
drift (LOOO), within-tier pairwise accuracy, Day 3 sleeper precision, residual
calibration monotonicity, and temporal/censoring isolation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_head_b_bakeoff import (
    LOOO_DRIFT_THRESHOLD_PCT,
    HeadBGateResult,
    compute_coefficient_drift,
    compute_residual_calibration_monotonicity,
    compute_residual_r2,
    compute_top5_day3_sleeper_precision,
    compute_within_tier_pairwise_accuracy,
    evaluate_head_b_mandatory_gate,
    flag_unstable_features,
)
from src.dynasty_genius.models.head_b_contract import check_head_b_feature_leakage


# ── 1. Head B Leakage Guard ───────────────────────────────────────────────────

def test_leakage_check_raises_on_nfl_pick():
    """check_head_b_feature_leakage must raise on the explicit 'nfl_pick' column."""
    with pytest.raises(ValueError, match="prohibited draft-capital"):
        check_head_b_feature_leakage(["final_college_age", "nfl_pick"])


def test_leakage_check_raises_on_derived_pick_pattern():
    """check_head_b_feature_leakage must raise on regex-matched derived columns."""
    for bad_col in ["pick_log", "pick_bucket", "nfl_round_bucket", "draft_capital_index"]:
        with pytest.raises(ValueError):
            check_head_b_feature_leakage([bad_col])


def test_leakage_check_passes_clean_wr_features():
    """Valid Head B WR features must pass check_head_b_feature_leakage without error."""
    clean_features = [
        "final_college_age",
        "wr_dominator_final",
        "wr_breakout_age",
        "wr_market_share_yds",
        "wr_yards_per_reception_career",
        "ryptpa",
    ]
    check_head_b_feature_leakage(clean_features)  # must not raise


# ── 2. Residual R² Mandatory Gate ─────────────────────────────────────────────

def test_compute_residual_r2_perfect_fit_returns_one():
    """Perfect predictions must yield R²=1.0."""
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    r2 = compute_residual_r2(y, y.copy())
    assert r2 == pytest.approx(1.0, abs=1e-9)


def test_compute_residual_r2_mean_model_returns_zero():
    """Predicting the mean for every row must yield R²=0.0."""
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_mean = np.full_like(y, y.mean())
    r2 = compute_residual_r2(y, y_mean)
    assert r2 == pytest.approx(0.0, abs=1e-9)


def test_mandatory_r2_gate_passes_above_zero():
    """evaluate_head_b_mandatory_gate must return True when R²>0."""
    assert evaluate_head_b_mandatory_gate(0.01) is True
    assert evaluate_head_b_mandatory_gate(0.5) is True


def test_mandatory_r2_gate_fails_at_zero():
    """evaluate_head_b_mandatory_gate must return False when R²=0.0."""
    assert evaluate_head_b_mandatory_gate(0.0) is False


def test_mandatory_r2_gate_fails_negative():
    """evaluate_head_b_mandatory_gate must return False when R²<0."""
    assert evaluate_head_b_mandatory_gate(-0.05) is False


# ── 3. Coefficient Drift (LOOO Outlier Sensitivity) ──────────────────────────

def test_coefficient_drift_flags_unstable_feature_above_threshold():
    """A single outlier that drives the entire slope must produce drift >25%.

    4 points with zero slope (y=constant) plus one extreme outlier at high x,
    so the outlier dominates the Ridge coefficient AND has the largest training
    residual (because the model bends to fit the other 4 constant points).
    Removing the outlier collapses the coefficient to near-zero → large drift.
    """
    # 4 constant points (zero slope) + 1 outlier at x=4.5, y=50
    X_train = np.array([[1.0], [2.0], [3.0], [4.0], [4.5]])
    y_train = np.array([5.0, 5.0, 5.0, 5.0, 50.0])

    drift = compute_coefficient_drift(X_train, y_train, alpha=0.01, features=["x1"])
    unstable = flag_unstable_features(drift)
    assert "x1" in unstable, (
        f"Expected 'x1' flagged as unstable (drift={drift.get('x1'):.1f}%), "
        f"threshold={LOOO_DRIFT_THRESHOLD_PCT}%"
    )


def test_coefficient_drift_clears_stable_feature_below_threshold():
    """Perfectly linear data must produce drift <25% (no dominant outlier)."""
    X_train = np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0]])
    y_train = np.array([2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0])

    drift = compute_coefficient_drift(X_train, y_train, alpha=1.0, features=["x1"])
    unstable = flag_unstable_features(drift)
    assert "x1" not in unstable, (
        f"Expected 'x1' stable (drift={drift.get('x1'):.1f}%), "
        f"threshold={LOOO_DRIFT_THRESHOLD_PCT}%"
    )


# ── 4. Within-Tier Pairwise Accuracy ─────────────────────────────────────────

def test_within_tier_pairwise_accuracy_perfect_case():
    """When all same-tier pairs are correctly ordered, accuracy must be 1.0."""
    # 4 players drafted within 10 picks of each other, model ranks in same order as truth
    y_true = np.array([10.0, 8.0, 5.0, 2.0])
    y_pred = np.array([9.0, 7.0, 4.0, 1.0])  # same relative order
    nfl_picks = np.array([5.0, 10.0, 12.0, 14.0])  # all within 10 picks of each other

    acc = compute_within_tier_pairwise_accuracy(y_true, y_pred, nfl_picks, tier_window=10)
    assert acc == pytest.approx(1.0, abs=1e-9)


def test_within_tier_pairwise_accuracy_fully_inverted_case():
    """When all same-tier pairs are inverted, accuracy must be 0.0."""
    y_true = np.array([10.0, 8.0, 5.0, 2.0])
    y_pred = np.array([1.0, 2.0, 3.0, 4.0])  # fully inverted order
    nfl_picks = np.array([5.0, 8.0, 10.0, 13.0])  # all within 10 picks

    acc = compute_within_tier_pairwise_accuracy(y_true, y_pred, nfl_picks, tier_window=10)
    assert acc == pytest.approx(0.0, abs=1e-9)


def test_within_tier_pairwise_accuracy_no_tier_pairs_returns_zero():
    """When no players are within the tier window, return 0.0."""
    y_true = np.array([5.0, 3.0, 1.0])
    y_pred = np.array([4.5, 2.5, 0.5])
    nfl_picks = np.array([1.0, 50.0, 150.0])  # all >10 picks apart

    acc = compute_within_tier_pairwise_accuracy(y_true, y_pred, nfl_picks, tier_window=10)
    assert acc == 0.0


# ── 5. Top-5 Day 3 Sleeper Precision ─────────────────────────────────────────

def test_top5_day3_sleeper_precision_all_positive():
    """When all top-5 Day 3 predictions achieve positive residuals, precision=1.0."""
    # 6 Day 3 picks; top 5 predicted best all have positive y_true
    y_true = np.array([3.0, 2.0, 1.0, 0.5, 0.1, -1.0])
    y_pred = np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])  # rank: 1st=highest pred
    nfl_picks = np.array([110.0, 120.0, 130.0, 140.0, 150.0, 160.0])  # all Day 3

    prec = compute_top5_day3_sleeper_precision(y_true, y_pred, nfl_picks)
    assert prec == pytest.approx(1.0, abs=1e-9)


def test_top5_day3_sleeper_precision_all_negative():
    """When all top-5 Day 3 predictions have negative residuals, precision=0.0."""
    y_true = np.array([-1.0, -2.0, -3.0, -4.0, -5.0, 10.0])  # last row positive but lower rank
    y_pred = np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])  # top 5 all predicted high
    nfl_picks = np.array([105.0, 115.0, 125.0, 135.0, 145.0, 200.0])  # all Day 3

    prec = compute_top5_day3_sleeper_precision(y_true, y_pred, nfl_picks)
    assert prec == pytest.approx(0.0, abs=1e-9)


def test_top5_day3_sleeper_precision_returns_none_when_no_day3_picks():
    """When no picks are on Day 3 (picks 103+), return None."""
    y_true = np.array([5.0, 3.0, 1.0])
    y_pred = np.array([4.0, 2.0, 0.5])
    nfl_picks = np.array([5.0, 15.0, 60.0])  # all Day 1/2

    prec = compute_top5_day3_sleeper_precision(y_true, y_pred, nfl_picks)
    assert prec is None


# ── 6. Residual Calibration Monotonicity ─────────────────────────────────────

def test_residual_calibration_monotonicity_passes_for_monotone_bins():
    """Monotonically increasing actual residuals across predicted bins must return True."""
    # 20 players: predicted and actual both increase together (monotone)
    n = 20
    y_pred = np.linspace(0.0, 4.0, n)
    y_true = np.linspace(0.0, 4.0, n) + np.random.default_rng(99).uniform(-0.2, 0.2, n)

    result = compute_residual_calibration_monotonicity(y_true, y_pred, n_bins=4)
    assert result is True


def test_residual_calibration_monotonicity_fails_for_inverted_bins():
    """Non-monotone actual residuals across predicted bins must return False."""
    # 20 players: predicted increases but actual residuals are inverted
    n = 20
    y_pred = np.linspace(0.0, 4.0, n)
    y_true = np.linspace(4.0, 0.0, n)  # fully inverted — bins will be anti-monotone

    result = compute_residual_calibration_monotonicity(y_true, y_pred, n_bins=4)
    assert result is False


# ── 7. Expected PPG / Curve Derivative Leakage Guard ─────────────────────────

def test_leakage_check_raises_on_expected_ppg_columns():
    """Explicit expected_ppg and curve_expected_ppg columns must raise."""
    for col in [
        "expected_ppg_at_pick",
        "expected_ppg",
        "expected_ppg_bucket",
        "curve_expected_ppg",
    ]:
        with pytest.raises(ValueError, match="prohibited"):
            check_head_b_feature_leakage([col])


def test_leakage_check_raises_on_expected_prefix_derivatives():
    """Any column starting with 'expected_' must raise (slot-expectation derivatives)."""
    for col in ["expected_ppg_slot", "expected_draft_value", "expected_anything"]:
        with pytest.raises(ValueError):
            check_head_b_feature_leakage([col])


def test_leakage_check_raises_on_curve_prefix_derivatives():
    """Any column starting with 'curve_' must raise (expectation curve derivatives)."""
    for col in ["curve_factor_v2", "curve_pick_value"]:
        with pytest.raises(ValueError):
            check_head_b_feature_leakage([col])


# ── 8. Runtime safety: no crash when day3_prec is None ───────────────────────

def test_position_run_no_crash_with_no_day3_picks(monkeypatch, tmp_path):
    """_run_position must not crash when day3_prec is None (all picks < 103)."""
    import run_head_b_bakeoff as m
    monkeypatch.setattr(m, "OOF_LOG_DIR", tmp_path / "oof_logs")

    base = {
        "final_college_age": "21.5", "wr_dominator_final": "0.3",
        "wr_breakout_age": "20.0", "wr_market_share_yds": "0.25",
        "wr_yards_per_reception_career": "12.0", "ryptpa": "0.5",
        "censored_incomplete_arc": "0",
    }
    rows = []
    for season, pick, res in [
        (2017, 5, 2.0), (2017, 10, 1.5), (2017, 15, 0.5), (2017, 20, -0.5), (2017, 25, -1.0),
        (2018, 8, 1.8), (2018, 18, -0.8),
        (2019, 12, 1.2), (2019, 22, -0.3),
        (2020, 16, 0.8), (2020, 26, -0.6),
    ]:
        rows.append({"position": "WR", "season": str(season),
                     "nfl_pick": str(pick), "residual_ppg": str(res), **base})

    result = m._run_position("WR", rows, "testrun", "20260524T000000Z")
    assert result["position"] == "WR"
    assert not result.get("skipped")


# ── 9. LOOO quarantine enforcement ───────────────────────────────────────────

def test_looo_quarantine_overrides_passing_gate(monkeypatch, tmp_path):
    """A gate-passing candidate must be quarantined when LOOO flags unstable features."""
    import run_head_b_bakeoff as m
    monkeypatch.setattr(m, "OOF_LOG_DIR", tmp_path / "oof_logs")
    # Force all gate evaluations to return a passing result
    passing_gate = HeadBGateResult(
        mandatory_r2_passes=True, r2=0.5, secondary_gates_passed=2,
        pairwise_accuracy_gate=True, day3_precision_gate=False,
        calibration_monotonicity_gate=True, final_passes=True, fail_reasons=[],
    )
    monkeypatch.setattr(m, "evaluate_head_b_gates",
                        lambda r2, pa, d3, mono: passing_gate)
    # Force LOOO to always flag instability
    monkeypatch.setattr(m, "flag_unstable_features",
                        lambda drift, threshold=25.0: ["final_college_age"])

    base = {
        "final_college_age": "21.5", "wr_dominator_final": "0.3",
        "wr_breakout_age": "20.0", "wr_market_share_yds": "0.25",
        "wr_yards_per_reception_career": "12.0", "ryptpa": "0.5",
        "censored_incomplete_arc": "0",
    }
    rows = []
    for season, pick, res in [
        (2017, 5, 2.0), (2017, 10, 1.5), (2017, 15, 0.5), (2017, 20, -0.5), (2017, 25, -1.0),
        (2018, 8, 1.8), (2018, 18, -0.8),
        (2019, 12, 1.2), (2019, 22, -0.3),
        (2020, 16, 0.8), (2020, 26, -0.6),
    ]:
        rows.append({"position": "WR", "season": str(season),
                     "nfl_pick": str(pick), "residual_ppg": str(res), **base})

    result = m._run_position("WR", rows, "testrun", "20260524T000000Z")
    assert result.get("unstable_features") == ["final_college_age"]
    for cand_name, gate in result.get("gate_results", {}).items():
        assert not gate.get("final_passes"), (
            f"Candidate {cand_name} must be quarantined; fail_reasons={gate.get('fail_reasons')}"
        )
        assert "looo_drift_quarantined" in gate.get("fail_reasons", []), (
            f"Quarantined candidate {cand_name} must record 'looo_drift_quarantined' in fail_reasons"
        )
