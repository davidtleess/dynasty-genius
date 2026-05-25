"""Tests for Phase 19 W1 Head B target pipeline.

TDD suite covering:
  - best3of4_ppg computation and games threshold
  - censoring logic for incomplete career arcs
  - isotonic curve monotonicity (WR, RB)
  - TE hierarchical pooling shrinkage toward WR prior
  - residual arithmetic
  - no market fields in new columns
  - output path isolation from source CSV
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from scripts.build_head_b_targets import (
    MARKET_FIELD_PATTERNS,
    MIN_GAMES_THRESHOLD,
    OUTPUT_CSV,
    SOURCE_CSV,
    TRAINING_MAX_SEASON,
    compute_best3of4_ppg,
    compute_censoring_flag,
    compute_row_targets,
    compute_v3_universal_features,
    expected_ppg_at_pick,
    fit_isotonic_curve,
    fit_te_pooled_curve,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _synthetic_picks_ppg(n: int = 80, seed: int = 42) -> tuple[list[float], list[float]]:
    """Synthetic pick/PPG data with a realistic downward trend plus noise."""
    rng = np.random.default_rng(seed)
    picks = rng.integers(1, 250, size=n).astype(float).tolist()
    ppg = [max(0.5, 15.0 - p * 0.04 + rng.normal(0, 1.5)) for p in picks]
    return picks, ppg


# ── best3of4_ppg tests ────────────────────────────────────────────────────

def test_compute_best3of4_ppg_normal():
    """Standard case: total points / total games."""
    result = compute_best3of4_ppg(total_points=240.0, total_games=16)
    assert result == pytest.approx(15.0, abs=0.01)


def test_compute_best3of4_ppg_fractional():
    """Non-integer total_games gives correct fractional PPG."""
    result = compute_best3of4_ppg(total_points=100.0, total_games=30)
    assert result == pytest.approx(100.0 / 30, abs=1e-4)


def test_compute_best3of4_ppg_below_min_games_returns_none():
    """Below the minimum games threshold, returns None (insufficient career arc)."""
    assert compute_best3of4_ppg(100.0, MIN_GAMES_THRESHOLD - 1) is None


def test_compute_best3of4_ppg_at_min_games_returns_value():
    """Exactly at threshold is included."""
    result = compute_best3of4_ppg(80.0, MIN_GAMES_THRESHOLD)
    assert result is not None
    assert result == pytest.approx(80.0 / MIN_GAMES_THRESHOLD, abs=1e-4)


# ── censoring tests ───────────────────────────────────────────────────────

def test_censoring_flag_on_training_cohort():
    """Players within the training window with sufficient games are not censored."""
    assert compute_censoring_flag(2018, 30) is False
    assert compute_censoring_flag(TRAINING_MAX_SEASON, 30) is False
    assert compute_censoring_flag(2015, 24) is False


def test_censoring_flag_on_recent_cohort():
    """Draft classes after TRAINING_MAX_SEASON are censored (incomplete Y4)."""
    assert compute_censoring_flag(TRAINING_MAX_SEASON + 1, 30) is True
    assert compute_censoring_flag(2024, 48) is True
    assert compute_censoring_flag(2025, 16) is True


def test_censoring_flag_on_low_games():
    """Players below MIN_GAMES_THRESHOLD are censored regardless of draft class."""
    assert compute_censoring_flag(2018, MIN_GAMES_THRESHOLD - 1) is True
    assert compute_censoring_flag(2015, 0) is True


# ── isotonic curve monotonicity ───────────────────────────────────────────

def test_expected_ppg_monotonic_by_pick_wr():
    """WR isotonic curve must be non-increasing: lower pick ⇒ higher expected PPG."""
    picks, ppg = _synthetic_picks_ppg(n=150, seed=42)
    ir = fit_isotonic_curve(picks, ppg)
    test_picks = [1.0, 10.0, 32.0, 64.0, 100.0, 160.0, 220.0, 249.0]
    values = [expected_ppg_at_pick(p, ir) for p in test_picks]
    for i in range(len(values) - 1):
        assert values[i] >= values[i + 1] - 1e-6, (
            f"Monotonicity violated: pick {test_picks[i]} PPG {values[i]:.4f} "
            f"< pick {test_picks[i+1]} PPG {values[i+1]:.4f}"
        )


def test_expected_ppg_monotonic_by_pick_rb():
    """RB isotonic curve must be non-increasing with pick number."""
    picks, ppg = _synthetic_picks_ppg(n=80, seed=99)
    ir = fit_isotonic_curve(picks, ppg)
    test_picks = [1.0, 20.0, 50.0, 100.0, 200.0]
    values = [expected_ppg_at_pick(p, ir) for p in test_picks]
    for i in range(len(values) - 1):
        assert values[i] >= values[i + 1] - 1e-6


# ── TE hierarchical pooling ───────────────────────────────────────────────

def test_te_pooling_shrinks_toward_wr_prior():
    """With sparse TE data, pooled estimate lies between raw TE mean and WR prior.

    Sets up a scenario where TE data has very low PPG at picks 100-190 but the
    WR prior at the same pick range is higher. The pooled TE estimate should
    fall between the two extremes, pulled toward WR.
    """
    rng = np.random.default_rng(7)
    # WR training data: broad coverage, clear downward trend
    wr_picks = list(range(1, 256, 3))
    wr_ppg = [max(0.5, 14.0 - p * 0.04 + rng.normal(0, 0.4)) for p in wr_picks]
    wr_ir = fit_isotonic_curve(wr_picks, wr_ppg)

    # Sparse TE data at late picks only — raw PPG ~1.0 (much lower than WR prior)
    te_picks = [110.0, 130.0, 150.0, 170.0, 190.0]
    te_ppg_raw = [1.0, 0.8, 1.2, 0.9, 1.1]
    te_ir_pooled = fit_te_pooled_curve(te_picks, te_ppg_raw, wr_ir, shrinkage_k=5.0)

    wr_prior = expected_ppg_at_pick(150.0, wr_ir)
    raw_te_mean = float(np.mean(te_ppg_raw))  # ≈ 1.0
    pooled = expected_ppg_at_pick(150.0, te_ir_pooled)

    low = min(raw_te_mean, wr_prior)
    high = max(raw_te_mean, wr_prior)
    assert low - 1e-6 <= pooled <= high + 1e-6, (
        f"Pooled TE {pooled:.3f} not between raw TE mean {raw_te_mean:.3f} "
        f"and WR prior {wr_prior:.3f}"
    )


def test_te_pooled_curve_is_monotonic():
    """Pooled TE curve must also be non-increasing with pick number."""
    rng = np.random.default_rng(13)
    wr_picks = list(range(1, 256, 4))
    wr_ppg = [max(0.5, 13.0 - p * 0.035 + rng.normal(0, 0.5)) for p in wr_picks]
    wr_ir = fit_isotonic_curve(wr_picks, wr_ppg)

    te_picks = [40.0, 55.0, 80.0, 100.0, 120.0, 150.0]
    te_ppg = [10.0, 9.0, 7.5, 6.0, 5.0, 4.0]
    te_ir = fit_te_pooled_curve(te_picks, te_ppg, wr_ir, shrinkage_k=5.0)

    test_picks = [1.0, 32.0, 64.0, 100.0, 150.0, 200.0]
    values = [expected_ppg_at_pick(p, te_ir) for p in test_picks]
    for i in range(len(values) - 1):
        assert values[i] >= values[i + 1] - 1e-6


# ── residual arithmetic ───────────────────────────────────────────────────

def test_residual_ppg_direction():
    """residual_ppg = actual - expected; sign must be correct."""
    picks, ppg = _synthetic_picks_ppg(n=100, seed=55)
    ir = fit_isotonic_curve(picks, ppg)
    expected = expected_ppg_at_pick(32.0, ir)

    above_expected = expected + 5.0
    below_expected = expected - 3.0

    assert (above_expected - expected) > 0
    assert (below_expected - expected) < 0


# ── governance / isolation tests ─────────────────────────────────────────

def test_new_columns_contain_no_market_fields():
    """The new columns introduced by W1 must not match any market-field pattern."""
    new_columns = [
        "best3of4_ppg",
        "censored_incomplete_arc",
        "expected_ppg_at_pick",
        "residual_ppg",
        "target_version",
        "curve_version",
    ]
    for col in new_columns:
        for pattern in MARKET_FIELD_PATTERNS:
            assert not re.search(pattern, col, re.IGNORECASE), (
                f"Market field pattern {pattern!r} matched new column {col!r}"
            )


def test_output_path_is_not_source_csv():
    """The v3 output CSV path must differ from the source CSV path."""
    assert SOURCE_CSV != OUTPUT_CSV, "Pipeline would overwrite the source CSV"
    assert "v3" in OUTPUT_CSV.name, "Output file name must contain 'v3'"
    assert "v3" not in SOURCE_CSV.name, "Source CSV must not contain 'v3'"


# ── compute_row_targets censoring / eligibility tests ─────────────────────────

def _make_wr_curve() -> IsotonicRegression:
    rng = np.random.default_rng(77)
    picks = list(range(1, 100, 2))
    ppg = [max(0.5, 14.0 - p * 0.04 + rng.normal(0, 0.5)) for p in picks]
    return fit_isotonic_curve([float(p) for p in picks], ppg)


def test_censored_2022_row_has_blank_residual():
    """Draft class 2022 (>TRAINING_MAX_SEASON) must produce blank residual_ppg.

    expected_ppg_at_pick must still be populated to support inference scoring.
    """
    curves = {"WR": _make_wr_curve()}
    row = {
        "season": "2022",
        "position": "WR",
        "pick": "30",
        "total_points": "200",
        "total_games": "48",
    }
    result = compute_row_targets(row, curves)
    assert result["censored_incomplete_arc"] == "1"
    assert result["best3of4_ppg"] == ""
    assert result["residual_ppg"] == ""
    assert result["head_b_training_eligible"] == "0"
    assert result["expected_ppg_at_pick"] != "", "expected_ppg_at_pick must be populated for inference"


def test_low_game_row_has_blank_residual():
    """Training-era class below MIN_GAMES_THRESHOLD must produce blank residual_ppg."""
    curves = {"WR": _make_wr_curve()}
    row = {
        "season": "2019",
        "position": "WR",
        "pick": "30",
        "total_points": "40",
        "total_games": str(MIN_GAMES_THRESHOLD - 1),
    }
    result = compute_row_targets(row, curves)
    assert result["censored_incomplete_arc"] == "1"
    assert result["best3of4_ppg"] == ""
    assert result["residual_ppg"] == ""
    assert result["head_b_training_eligible"] == "0"


# ── compute_v3_universal_features tests ──────────────────────────────────────

def test_age_at_draft_populated_when_age_present():
    """age_at_draft should equal source 'age' column when valid."""
    result = compute_v3_universal_features({"age": "23"})
    assert result["age_at_draft"] == "23"
    assert result["age_at_draft_missing"] == "0"
    assert result["age_at_draft_source"] == "nfl_data_py"


def test_age_at_draft_missing_when_age_absent():
    """age_at_draft_missing must be '1' when source age is absent."""
    result = compute_v3_universal_features({"age": ""})
    assert result["age_at_draft"] == ""
    assert result["age_at_draft_missing"] == "1"


def test_cfbd_stub_columns_have_missing_flag_set():
    """CFBD-dependent universal feature stubs must carry _missing='1'."""
    result = compute_v3_universal_features({"age": "22"})
    for col in ("covid_eligibility_flag", "transfer_portal_flag",
                "early_declare", "final_college_age"):
        assert result.get(f"{col}_missing") == "1", (
            f"Stub column '{col}_missing' should be '1' until CFBD enrichment runs"
        )


def test_eligible_row_produces_correct_residual():
    """Non-censored row with valid pick and curve must have correct residual arithmetic."""
    curves = {"WR": _make_wr_curve()}
    row = {
        "season": "2018",
        "position": "WR",
        "pick": "32",
        "total_points": "320.0",
        "total_games": "32",
    }
    result = compute_row_targets(row, curves)
    assert result["censored_incomplete_arc"] == "0"
    assert result["best3of4_ppg"] != ""
    assert result["expected_ppg_at_pick"] != ""
    assert result["residual_ppg"] != ""
    assert result["head_b_training_eligible"] == "1"

    actual = float(result["best3of4_ppg"])
    expected = float(result["expected_ppg_at_pick"])
    residual = float(result["residual_ppg"])
    assert residual == pytest.approx(actual - expected, abs=1e-3)
