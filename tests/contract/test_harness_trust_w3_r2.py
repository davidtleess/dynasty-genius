"""Harness Trust Completion W3.1 RED: OOS R2 metric contract."""
from __future__ import annotations

import pytest

from src.dynasty_genius.eval.backtest_metrics import compute_r2


def test_compute_r2_exact_value_on_known_fixture():
    assert compute_r2(
        [1.0, 2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0, 4.0],
    ) == pytest.approx(1.0)
    assert compute_r2(
        [1.0, 2.0, 3.0, 4.0],
        [2.5, 2.5, 2.5, 2.5],
    ) == pytest.approx(0.0)


def test_compute_r2_negative_is_returned_not_clamped():
    r2 = compute_r2([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0])

    assert r2 < 0.0


def test_compute_r2_zero_variance_truth_fails_closed_to_none():
    assert compute_r2([5.0, 5.0, 5.0], [5.0, 5.1, 4.9]) is None


def test_compute_r2_nan_or_inf_in_pred_fails_closed_to_none():
    assert compute_r2([1.0, 2.0, 3.0], [1.0, float("nan"), 3.0]) is None
    assert compute_r2([1.0, 2.0, 3.0], [1.0, float("inf"), 3.0]) is None


def test_compute_r2_nan_or_inf_in_truth_fails_closed_to_none():
    assert compute_r2([1.0, float("nan"), 3.0], [1.0, 2.0, 3.0]) is None
    assert compute_r2([1.0, float("-inf"), 3.0], [1.0, 2.0, 3.0]) is None


def test_compute_r2_length_mismatch_or_empty_raises():
    with pytest.raises(ValueError):
        compute_r2([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        compute_r2([], [])


def test_compute_r2_finite_inputs_with_overflowing_intermediate_fails_closed_to_none():
    # Codex W3.1 independent-review finding: finite inputs whose squared sums
    # overflow float64 must fail closed (non-finite computed metric → None).
    assert compute_r2([1e154, 2e154, 3e154], [3e154, 2e154, 1e154]) is None
