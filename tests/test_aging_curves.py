"""Tests for the piecewise-linear aging curves artifact (Task 5.2).

Enforces:
- resources/fitted_aging_curves_v1.json exists and has required structure.
- All five positions are present: RB, WR, TE, QB_pocket, QB_dual_threat.
- Peak ages match the Q3/Q4 decision record breakpoints.
- Curves are unit-normalized (0.0 to 1.0 relative value scale).
- RB declines faster than QB_pocket (physical vs cognitive position).
- The Python reader returns values in [0, 1] for any age.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.models.aging_curves import (
    AGING_CURVES_PATH,
    load_aging_curves,
    aging_curve_value,
)

REQUIRED_POSITIONS = {"RB", "WR", "TE", "QB_pocket", "QB_dual_threat"}
REQUIRED_KEYS = {
    "peak_age", "onset_of_decline_age", "entry_age",
    "ascent_slope_per_year", "decline_slope_per_year",
}


# ── File structure ────────────────────────────────────────────────────────────

def test_aging_curves_json_exists():
    assert AGING_CURVES_PATH.exists(), f"Missing: {AGING_CURVES_PATH}"


def test_aging_curves_json_has_required_top_level_keys():
    data = load_aging_curves()
    for key in ("schema_version", "methodology", "positions"):
        assert key in data, f"Missing top-level key: {key}"


def test_all_positions_present():
    data = load_aging_curves()
    positions = set(data["positions"].keys())
    missing = REQUIRED_POSITIONS - positions
    assert not missing, f"Missing positions in aging curves: {missing}"


def test_each_position_has_required_keys():
    data = load_aging_curves()
    for pos, spec in data["positions"].items():
        missing = REQUIRED_KEYS - set(spec.keys())
        assert not missing, f"Position '{pos}' missing keys: {missing}"


# ── Decision record alignment ─────────────────────────────────────────────────

def test_rb_onset_of_decline_is_26():
    data = load_aging_curves()
    assert data["positions"]["RB"]["onset_of_decline_age"] == 26


def test_wr_onset_of_decline_is_28():
    data = load_aging_curves()
    assert data["positions"]["WR"]["onset_of_decline_age"] == 28


def test_te_onset_of_decline_is_30():
    data = load_aging_curves()
    assert data["positions"]["TE"]["onset_of_decline_age"] == 30


def test_qb_pocket_onset_of_decline_is_33():
    data = load_aging_curves()
    assert data["positions"]["QB_pocket"]["onset_of_decline_age"] == 33


def test_qb_dual_threat_onset_of_decline_is_29():
    data = load_aging_curves()
    assert data["positions"]["QB_dual_threat"]["onset_of_decline_age"] == 29


# ── Curve shape invariants ────────────────────────────────────────────────────

def test_rb_declines_faster_than_qb_pocket():
    data = load_aging_curves()
    rb_slope = data["positions"]["RB"]["decline_slope_per_year"]
    qb_slope = data["positions"]["QB_pocket"]["decline_slope_per_year"]
    assert rb_slope > qb_slope, (
        f"RB decline slope ({rb_slope}) should exceed QB pocket ({qb_slope})"
    )


def test_pocket_qb_has_later_onset_than_dual_threat():
    data = load_aging_curves()
    pocket = data["positions"]["QB_pocket"]["onset_of_decline_age"]
    dual = data["positions"]["QB_dual_threat"]["onset_of_decline_age"]
    assert pocket > dual, f"Pocket QB onset ({pocket}) should be > dual-threat ({dual})"


# ── Python reader ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("position", list(REQUIRED_POSITIONS))
@pytest.mark.parametrize("age", [21, 24, 26, 29, 33, 38])
def test_aging_curve_value_returns_0_to_1(position, age):
    value = aging_curve_value(position, age)
    assert 0.0 <= value <= 1.0, (
        f"aging_curve_value('{position}', {age}) = {value} is out of [0, 1]"
    )


def test_aging_curve_value_at_peak_is_close_to_1():
    data = load_aging_curves()
    for pos in REQUIRED_POSITIONS:
        peak_age = data["positions"][pos]["peak_age"]
        value = aging_curve_value(pos, peak_age)
        assert value >= 0.90, (
            f"aging_curve_value('{pos}', {peak_age}) = {value:.3f}; expected ≥0.90 at peak"
        )


def test_aging_curve_value_declines_after_onset():
    for pos in REQUIRED_POSITIONS:
        data = load_aging_curves()
        onset = data["positions"][pos]["onset_of_decline_age"]
        v_at_onset = aging_curve_value(pos, onset)
        v_five_years_later = aging_curve_value(pos, onset + 5)
        assert v_five_years_later < v_at_onset, (
            f"'{pos}': value at onset+5 ({v_five_years_later:.3f}) "
            f"should be < at onset ({v_at_onset:.3f})"
        )


def test_aging_curve_value_unknown_position_raises():
    with pytest.raises((KeyError, ValueError)):
        aging_curve_value("K", 30)
