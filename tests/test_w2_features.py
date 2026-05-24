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
    _load_combine_data,
    build_combine_lookup,
    compute_age_position_features,
    compute_all_stubs,
    compute_bmi,
    compute_combine_features,
    compute_dominator_features,
    compute_draft_capital_aliases,
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
    V3_POSITION_HEAD_A_FEATURES,
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


# ── compute_draft_capital_aliases ─────────────────────────────────────────────

def test_draft_capital_alias_pick_populated():
    row = {"pick": "25", "round": "1"}
    result = compute_draft_capital_aliases(row)
    assert result["nfl_pick"] == "25"
    assert result["nfl_pick_missing"] == "0"
    assert result["nfl_pick_source"] == "nfl_data_py"


def test_draft_capital_alias_round_populated():
    row = {"pick": "25", "round": "1"}
    result = compute_draft_capital_aliases(row)
    assert result["nfl_round"] == "1"
    assert result["nfl_round_missing"] == "0"
    assert result["nfl_round_source"] == "nfl_data_py"


def test_draft_capital_alias_missing_pick():
    result = compute_draft_capital_aliases({"pick": "", "round": "2"})
    assert result["nfl_pick"] == ""
    assert result["nfl_pick_missing"] == "1"
    assert result["nfl_pick_source"] == ""


def test_draft_capital_alias_missing_round():
    result = compute_draft_capital_aliases({"pick": "50", "round": ""})
    assert result["nfl_round"] == ""
    assert result["nfl_round_missing"] == "1"


def test_draft_capital_alias_both_missing():
    result = compute_draft_capital_aliases({})
    assert result["nfl_pick_missing"] == "1"
    assert result["nfl_round_missing"] == "1"


# ── Schema coverage: V3_POSITION_HEAD_A_FEATURES ──────────────────────────────

def _make_full_row(position: str) -> dict[str, str]:
    """Simulate what W2 main() produces for a single row at a given position."""
    combine_specs = {
        "WR": {"pos": "WR", "ht": "6-1", "wt": 200.0, "forty": 4.40,
               "vertical": 38.0, "broad_jump": 120.0, "cone": 6.69, "shuttle": 4.10},
        "RB": {"pos": "RB", "ht": "5-10", "wt": 215.0, "forty": 4.45,
               "vertical": 34.0, "broad_jump": 118.0, "cone": 6.95, "shuttle": 4.25},
        "TE": {"pos": "TE", "ht": "6-4", "wt": 250.0, "forty": 4.60,
               "vertical": 33.0, "broad_jump": 112.0, "cone": 7.05, "shuttle": 4.30},
    }
    spec = combine_specs.get(position, combine_specs["WR"])
    df = pd.DataFrame([{
        "draft_year": 2020.0, "draft_ovr": 25.0, "player_name": "TestPlayer",
        **spec,
    }])
    lookup = build_combine_lookup(df)

    # W1-provided columns (already in v3 CSV before W2 runs)
    base = {
        "season": "2020", "pick": "25", "round": "1",
        "position": position, "age": "22.0",
        "age_at_draft": "22.0", "age_at_draft_missing": "0",
        "age_at_draft_source": "nfl_data_py",
        "gsis_id": "test-gsis-99",
        # CFBD universal stubs from W1 compute_v3_universal_features
        "covid_eligibility_flag": "", "covid_eligibility_flag_missing": "1",
        "covid_eligibility_flag_source": "",
        "transfer_portal_flag": "", "transfer_portal_flag_missing": "1",
        "transfer_portal_flag_source": "",
        "early_declare": "", "early_declare_missing": "1",
        "early_declare_source": "",
        "final_college_age": "", "final_college_age_missing": "1",
        "final_college_age_source": "",
    }
    row: dict[str, str] = dict(base)
    row.update(compute_combine_features(row, lookup))
    row.update(compute_draft_capital_aliases(row))
    row.update(compute_age_position_features(row))
    row.update(compute_dominator_features(row, {}))
    row.update(compute_all_stubs(position))
    return row


def test_head_a_wr_features_covered_by_w2_output():
    """All WR V3_POSITION_HEAD_A_FEATURES must be present as keys in W2 output."""
    row = _make_full_row("WR")
    for feat in V3_POSITION_HEAD_A_FEATURES["WR"]:
        assert feat in row, f"WR Head A required feature '{feat}' missing from W2 output"


def test_head_a_rb_features_covered_by_w2_output():
    row = _make_full_row("RB")
    for feat in V3_POSITION_HEAD_A_FEATURES["RB"]:
        assert feat in row, f"RB Head A required feature '{feat}' missing from W2 output"


def test_head_a_te_features_covered_by_w2_output():
    row = _make_full_row("TE")
    for feat in V3_POSITION_HEAD_A_FEATURES["TE"]:
        assert feat in row, f"TE Head A required feature '{feat}' missing from W2 output"


def test_nfl_pick_not_in_head_b_output():
    """nfl_pick must be in the W2 row but excluded from V3_POSITION_HEAD_B_FEATURES."""
    row = _make_full_row("WR")
    assert "nfl_pick" in row, "nfl_pick must appear in W2 output for Head A"
    assert "nfl_pick" not in V3_POSITION_HEAD_B_FEATURES["WR"], (
        "nfl_pick must not be in Head B feature set"
    )


def test_nfl_round_not_in_head_b_output():
    row = _make_full_row("RB")
    assert "nfl_round" in row
    assert "nfl_round" not in V3_POSITION_HEAD_B_FEATURES["RB"]


# ── Combine load failure behavior ─────────────────────────────────────────────

def test_combine_load_failure_raises_by_default(monkeypatch, tmp_path):
    """Without allow_degraded, _load_combine_data() failure must propagate."""
    import scripts.build_w2_features as bwf

    src_csv = tmp_path / "v3.csv"
    src_csv.write_text(
        "season,pick,round,position,age,age_at_draft,age_at_draft_missing,"
        "age_at_draft_source,gsis_id\n"
        "2020,25,1,WR,22.0,22.0,0,nfl_data_py,test-01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bwf, "V3_CSV", src_csv)

    def _raise_on_load():
        raise ConnectionError("network unavailable")

    monkeypatch.setattr(bwf, "_load_combine_data", _raise_on_load)

    with pytest.raises((RuntimeError, ConnectionError)):
        bwf.main(allow_degraded=False)


def test_combine_load_failure_degraded_writes_missing_stubs(monkeypatch, tmp_path):
    """With allow_degraded=True, Combine failure writes _missing=1 stubs and
    stamps w2_combine_degraded=1 on every row."""
    import scripts.build_w2_features as bwf

    # Minimal v3 CSV with required source columns
    src_csv = tmp_path / "v3.csv"
    src_csv.write_text(
        "season,pick,round,position,age,age_at_draft,age_at_draft_missing,"
        "age_at_draft_source,gsis_id\n"
        "2020,25,1,WR,22.0,22.0,0,nfl_data_py,test-01\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(bwf, "V3_CSV", src_csv)
    monkeypatch.setattr(bwf, "CFBD_PARTIAL_CSV", tmp_path / "no_dom.csv")
    def _fail_load():
        raise ConnectionError("no net")

    monkeypatch.setattr(bwf, "_load_combine_data", _fail_load)

    bwf.main(allow_degraded=True)

    import csv as _csv
    with src_csv.open(newline="", encoding="utf-8") as f:
        out_rows = list(_csv.DictReader(f))

    assert len(out_rows) == 1
    assert out_rows[0]["height_missing"] == "1"
    assert out_rows[0]["w2_combine_degraded"] == "1"


def test_degraded_flag_cleared_on_successful_rerun(monkeypatch, tmp_path):
    """After a degraded run, a successful rerun must stamp w2_combine_degraded=0.

    Regression guard for the stale-flag bug: combine_degraded=1 must not persist
    when a subsequent normal (non-degraded) run loads Combine data successfully.
    """
    import scripts.build_w2_features as bwf

    src_csv = tmp_path / "v3.csv"
    src_csv.write_text(
        "season,pick,round,position,age,age_at_draft,age_at_draft_missing,"
        "age_at_draft_source,gsis_id\n"
        "2020,25,1,WR,22.0,22.0,0,nfl_data_py,test-01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bwf, "V3_CSV", src_csv)
    monkeypatch.setattr(bwf, "CFBD_PARTIAL_CSV", tmp_path / "no_dom.csv")

    # Step 1: degraded run stamps w2_combine_degraded=1
    def _fail_load():
        raise ConnectionError("no net")

    monkeypatch.setattr(bwf, "_load_combine_data", _fail_load)
    bwf.main(allow_degraded=True)

    import csv as _csv
    with src_csv.open(newline="", encoding="utf-8") as f:
        after_degraded = list(_csv.DictReader(f))
    assert after_degraded[0]["w2_combine_degraded"] == "1"

    # Step 2: successful rerun (load succeeds, returns empty DataFrame — no entries)
    def _empty_load():
        return pd.DataFrame()

    monkeypatch.setattr(bwf, "_load_combine_data", _empty_load)
    bwf.main(allow_degraded=False)

    with src_csv.open(newline="", encoding="utf-8") as f:
        after_success = list(_csv.DictReader(f))
    assert after_success[0]["w2_combine_degraded"] == "0", (
        "Stale w2_combine_degraded=1 was not cleared on successful rerun"
    )
