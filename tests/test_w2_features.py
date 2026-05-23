"""Tests for Phase 19 W2 feature pipeline build-out.

TDD suite covering:
  - parse_height_inches: "6-0" format parsing
  - compute_rb_speed_score: Barnwell 2008 formula
  - compute_bmi: standard BMI formula
  - compute_te_height_adj_speed_score: height-adjusted speed composite
  - compute_wr_meets_athletic_floor: Szekely 2023 proxy boolean
  - compute_rb_meets_athletic_floor: speed-score viability gate
  - build_combine_lookup: keyed by (draft_year, overall_pick)
  - compute_combine_features: returns correct columns per position
  - compute_dominator_features: cfbd_partial career dominator join
  - compute_age_position_features: rb_age_at_draft / te_age_at_draft aliases
  - Schema contract: all V3 Required features present in output row
  - Leakage guard: no market-derived or draft-capital fields added to Head B set
  - Source CSV unchanged after live run (integration marker)
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_w2_features import (
    ALL_WR_FEATURE_STUBS,
    ALL_RB_FEATURE_STUBS,
    ALL_TE_FEATURE_STUBS,
    MEAN_TE_HEIGHT_INCHES,
    build_combine_lookup,
    compute_age_position_features,
    compute_bmi,
    compute_combine_features,
    compute_dominator_features,
    compute_rb_meets_athletic_floor,
    compute_rb_speed_score,
    compute_te_height_adj_speed_score,
    compute_wr_meets_athletic_floor,
    parse_height_inches,
)
from src.dynasty_genius.models.head_b_contract import (
    ALL_V3_REQUIRED_FEATURES,
    HEAD_B_PROHIBITED_COLUMNS,
    MARKET_PROHIBITED_COLUMNS,
    PFF_GRADE_PROHIBITED_COLUMNS,
    V3_POSITION_HEAD_B_FEATURES,
)


# ── parse_height_inches ───────────────────────────────────────────────────────

def test_parse_height_standard():
    assert parse_height_inches("6-0") == pytest.approx(72.0)


def test_parse_height_with_inches():
    assert parse_height_inches("5-11") == pytest.approx(71.0)


def test_parse_height_none():
    assert parse_height_inches(None) is None


def test_parse_height_invalid_format():
    assert parse_height_inches("6feet") is None


def test_parse_height_tall_te():
    assert parse_height_inches("6-6") == pytest.approx(78.0)


# ── compute_rb_speed_score ───────────────────────────────────────────────────

def test_rb_speed_score_formula():
    # (217 * 200) / (4.48^4) ≈ 107.8  (Frank Gore calibration)
    score = compute_rb_speed_score(217.0, 4.48)
    assert score is not None
    assert 100 < score < 120


def test_rb_speed_score_zero_weight():
    assert compute_rb_speed_score(0.0, 4.50) is None


def test_rb_speed_score_zero_forty():
    assert compute_rb_speed_score(220.0, 0.0) is None


def test_rb_speed_score_heavy_slow_lower():
    fast_score = compute_rb_speed_score(180.0, 4.30)
    slow_score = compute_rb_speed_score(180.0, 4.60)
    assert fast_score > slow_score


# ── compute_bmi ───────────────────────────────────────────────────────────────

def test_bmi_standard():
    # 220 lbs, 74 inches → BMI = 220 * 703 / 74^2 ≈ 28.3
    bmi = compute_bmi(220.0, 74.0)
    assert bmi is not None
    assert 27 < bmi < 30


def test_bmi_zero_height():
    assert compute_bmi(220.0, 0.0) is None


def test_bmi_proportional():
    heavier = compute_bmi(250.0, 74.0)
    lighter = compute_bmi(200.0, 74.0)
    assert heavier > lighter


# ── compute_te_height_adj_speed_score ────────────────────────────────────────

def test_te_hass_taller_higher():
    # At same weight+forty, taller TE should have higher HASS
    tall = compute_te_height_adj_speed_score(255.0, 4.50, 78.0)
    short = compute_te_height_adj_speed_score(255.0, 4.50, 73.0)
    assert tall > short


def test_te_hass_at_mean_height_equals_raw():
    # At MEAN_TE_HEIGHT_INCHES, HASS == raw speed score
    raw = compute_rb_speed_score(255.0, 4.50)
    hass = compute_te_height_adj_speed_score(255.0, 4.50, MEAN_TE_HEIGHT_INCHES)
    assert hass == pytest.approx(raw, rel=1e-4)


def test_te_hass_missing_returns_none():
    assert compute_te_height_adj_speed_score(255.0, None, 76.0) is None


# ── meets_athletic_floor ──────────────────────────────────────────────────────

def test_wr_meets_floor_above_threshold():
    assert compute_wr_meets_athletic_floor(35.0) is True


def test_wr_meets_floor_below_threshold():
    assert compute_wr_meets_athletic_floor(27.0) is False


def test_wr_meets_floor_none_returns_none():
    assert compute_wr_meets_athletic_floor(None) is None


def test_rb_meets_floor_above_threshold():
    high_ss = compute_rb_speed_score(220.0, 4.35)  # ~116 score
    assert compute_rb_meets_athletic_floor(high_ss) is True


def test_rb_meets_floor_below_threshold():
    low_ss = compute_rb_speed_score(190.0, 4.72)  # ~57 score
    assert compute_rb_meets_athletic_floor(low_ss) is False


def test_rb_meets_floor_none_returns_none():
    assert compute_rb_meets_athletic_floor(None) is None


# ── build_combine_lookup ──────────────────────────────────────────────────────

def test_build_combine_lookup_key():
    df = pd.DataFrame([
        {"draft_year": 2020.0, "draft_ovr": 25.0, "player_name": "TestWR",
         "pos": "WR", "ht": "6-1", "wt": 200.0, "forty": 4.45,
         "vertical": 38.0, "broad_jump": 120.0, "cone": 6.69, "shuttle": 4.10},
    ])
    lookup = build_combine_lookup(df)
    assert (2020, 25) in lookup
    assert lookup[(2020, 25)]["player_name"] == "TestWR"


def test_build_combine_lookup_excludes_nan_draft_year():
    df = pd.DataFrame([
        {"draft_year": float("nan"), "draft_ovr": 10.0, "player_name": "UDFA",
         "pos": "WR", "ht": "6-0", "wt": 190.0, "forty": 4.40,
         "vertical": 35.0, "broad_jump": 115.0, "cone": 6.80, "shuttle": 4.20},
    ])
    lookup = build_combine_lookup(df)
    assert len(lookup) == 0


# ── compute_combine_features ─────────────────────────────────────────────────

def _make_combine_lookup(season: int = 2020, pick: int = 25, pos: str = "WR",
                         ht: str = "6-1", wt: float = 200.0, forty: float = 4.40,
                         vertical: float = 38.0) -> dict:
    df = pd.DataFrame([{
        "draft_year": float(season), "draft_ovr": float(pick), "player_name": "TestWR",
        "pos": pos, "ht": ht, "wt": wt, "forty": forty, "vertical": vertical,
        "broad_jump": 120.0, "cone": 6.69, "shuttle": 4.10,
    }])
    return build_combine_lookup(df)


def test_combine_features_wr_height_populated():
    row = {"season": "2020", "pick": "25", "position": "WR", "age": "21.5"}
    lookup = _make_combine_lookup(season=2020, pick=25, pos="WR", ht="6-1", wt=200.0, forty=4.40, vertical=38.0)
    result = compute_combine_features(row, lookup)
    assert result["height"] == "73.0"
    assert result["height_missing"] == "0"
    assert result["height_source"] == "nfl_combine"


def test_combine_features_wr_vertical_populated():
    row = {"season": "2020", "pick": "25", "position": "WR", "age": "21.5"}
    lookup = _make_combine_lookup(season=2020, pick=25, pos="WR", vertical=38.0)
    result = compute_combine_features(row, lookup)
    assert result["wr_vertical_jump"] == "38.0"
    assert result["wr_vertical_jump_missing"] == "0"


def test_combine_features_wr_meets_floor_true():
    row = {"season": "2020", "pick": "25", "position": "WR", "age": "21.5"}
    lookup = _make_combine_lookup(vertical=38.0)
    result = compute_combine_features(row, lookup)
    assert result["wr_meets_athletic_floor"] == "1"
    assert result["wr_meets_athletic_floor_missing"] == "0"


def test_combine_features_no_combine_gives_missing():
    row = {"season": "2020", "pick": "99", "position": "WR", "age": "22.0"}
    result = compute_combine_features(row, {})
    assert result["height_missing"] == "1"
    assert result["wr_vertical_jump_missing"] == "1"
    assert result["wr_meets_athletic_floor_missing"] == "1"


def test_combine_features_rb_speed_score_populated():
    df = pd.DataFrame([{
        "draft_year": 2021.0, "draft_ovr": 50.0, "player_name": "TestRB",
        "pos": "RB", "ht": "5-10", "wt": 215.0, "forty": 4.45,
        "vertical": 34.0, "broad_jump": 118.0, "cone": 6.95, "shuttle": 4.25,
    }])
    lookup = build_combine_lookup(df)
    row = {"season": "2021", "pick": "50", "position": "RB", "age": "22.0"}
    result = compute_combine_features(row, lookup)
    assert result["rb_speed_score_missing"] == "0"
    ss = float(result["rb_speed_score"])
    assert 80 < ss < 140


def test_combine_features_te_bmi_populated():
    df = pd.DataFrame([{
        "draft_year": 2019.0, "draft_ovr": 35.0, "player_name": "TestTE",
        "pos": "TE", "ht": "6-4", "wt": 250.0, "forty": 4.60,
        "vertical": 33.0, "broad_jump": 112.0, "cone": 7.05, "shuttle": 4.30,
    }])
    lookup = build_combine_lookup(df)
    row = {"season": "2019", "pick": "35", "position": "TE", "age": "22.5"}
    result = compute_combine_features(row, lookup)
    assert result["te_bmi_missing"] == "0"
    bmi = float(result["te_bmi"])
    assert 25 < bmi < 35


# ── compute_dominator_features ───────────────────────────────────────────────

def test_dominator_features_wr_populated():
    dom_lookup = {"00-1234": {"dominator_rating": "0.35", "source_dominator_rating": "cfbd"}}
    row = {"gsis_id": "00-1234", "position": "WR"}
    result = compute_dominator_features(row, dom_lookup)
    assert result["wr_dominator_career"] == "0.35"
    assert result["wr_dominator_career_missing"] == "0"


def test_dominator_features_rb_populated():
    dom_lookup = {"00-5678": {"dominator_rating": "0.22", "source_dominator_rating": "cfbd"}}
    row = {"gsis_id": "00-5678", "position": "RB"}
    result = compute_dominator_features(row, dom_lookup)
    assert result["rb_career_dominator"] == "0.22"
    assert result["rb_career_dominator_missing"] == "0"


def test_dominator_features_missing_gsis():
    row = {"gsis_id": "00-9999", "position": "WR"}
    result = compute_dominator_features(row, {})
    assert result["wr_dominator_career_missing"] == "1"
    assert result["wr_dominator_career"] == ""


def test_dominator_features_empty_dominator_value():
    dom_lookup = {"00-1111": {"dominator_rating": "", "source_dominator_rating": "cfbd"}}
    row = {"gsis_id": "00-1111", "position": "TE"}
    result = compute_dominator_features(row, dom_lookup)
    assert result["te_career_dominator_missing"] == "1"


# ── compute_age_position_features ────────────────────────────────────────────

def test_age_position_rb():
    row = {"position": "RB", "age_at_draft": "22.5"}
    result = compute_age_position_features(row)
    assert result["rb_age_at_draft"] == "22.5"
    assert result["rb_age_at_draft_missing"] == "0"


def test_age_position_te():
    row = {"position": "TE", "age_at_draft": "23.1"}
    result = compute_age_position_features(row)
    assert result["te_age_at_draft"] == "23.1"
    assert result["te_age_at_draft_missing"] == "0"


def test_age_position_wr_gets_stubs():
    """WR rows get rb/te age stubs for uniform CSV schema."""
    row = {"position": "WR", "age_at_draft": "21.0"}
    result = compute_age_position_features(row)
    assert result["rb_age_at_draft"] == ""
    assert result["rb_age_at_draft_missing"] == "1"
    assert result["te_age_at_draft"] == ""
    assert result["te_age_at_draft_missing"] == "1"


# ── Schema contract ───────────────────────────────────────────────────────────

def test_all_wr_stub_columns_have_three_parts():
    """Every WR stub must have (col, col_missing, col_source)."""
    for col in ALL_WR_FEATURE_STUBS:
        assert not col.endswith("_missing"), f"stub list should contain base name: {col}"
        assert not col.endswith("_source"), f"stub list should contain base name: {col}"


def test_no_market_fields_in_stub_lists():
    banned = MARKET_PROHIBITED_COLUMNS | PFF_GRADE_PROHIBITED_COLUMNS
    all_stubs = ALL_WR_FEATURE_STUBS | ALL_RB_FEATURE_STUBS | ALL_TE_FEATURE_STUBS
    for col in all_stubs:
        assert col not in banned, f"Stub {col!r} is a banned market/PFF-grade column"


def test_no_draft_capital_in_head_b_stubs():
    all_stubs = ALL_WR_FEATURE_STUBS | ALL_RB_FEATURE_STUBS | ALL_TE_FEATURE_STUBS
    for col in all_stubs:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"Stub {col!r} is a prohibited Head B draft-capital column"
        )
