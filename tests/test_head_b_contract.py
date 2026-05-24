"""Tests for Phase 19 W2 Head B feature contract.

TDD suite covering:
  - HEAD_B_PROHIBITED_COLUMNS bans draft capital (pick, round, nfl_pick, nfl_round, derived)
  - HEAD_B_PROHIBITED_REGEX catches derived draft-capital names
  - No Head B position feature matrix entry violates the prohibition
  - Head A may include draft capital
  - Market overlay fields remain banned from both heads
  - Subjective PFF grades rejected from all heads
  - W1 target columns not contaminated by W2 prohibition sets
  - TE excluded features (te_breakout_age, te_receiving_grade_pff)
  - Provenance flag naming convention
  - check_head_b_feature_leakage() raises on violations, passes on clean lists
  - V3 artifacts remain gitignored
  - age_at_draft is present in all position feature matrices
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.dynasty_genius.models.head_b_contract import (
    ALL_V3_REQUIRED_FEATURES,
    DRAFT_CAPITAL_HEAD_A_ONLY,
    HEAD_B_PROHIBITED_COLUMNS,
    HEAD_B_PROHIBITED_REGEX,
    MARKET_PROHIBITED_COLUMNS,
    MISSINGNESS_FLAG_SUFFIX,
    PFF_GRADE_PROHIBITED_COLUMNS,
    PROVENANCE_FLAG_SUFFIX,
    TE_EXCLUDED_FEATURES,
    V3_POSITION_HEAD_A_FEATURES,
    V3_POSITION_HEAD_B_FEATURES,
    W1_TARGET_COLUMNS,
    WR_CANDIDATE_FEATURES,
    check_head_b_feature_leakage,
    get_missingness_flag_name,
    get_provenance_flag_name,
)

ROOT = Path(__file__).resolve().parents[1]


# ── HEAD_B_PROHIBITED_COLUMNS direct membership ───────────────────────────────

def test_head_b_prohibited_includes_pick():
    assert "pick" in HEAD_B_PROHIBITED_COLUMNS


def test_head_b_prohibited_includes_round():
    assert "round" in HEAD_B_PROHIBITED_COLUMNS


def test_head_b_prohibited_includes_nfl_pick():
    assert "nfl_pick" in HEAD_B_PROHIBITED_COLUMNS


def test_head_b_prohibited_includes_nfl_round():
    assert "nfl_round" in HEAD_B_PROHIBITED_COLUMNS


def test_head_b_prohibited_includes_derived_draft_capital():
    """Common derived draft-capital fields must be explicitly prohibited."""
    derived = {
        "pick_bucket", "round_bucket", "pick_log", "pick_squared",
        "draft_capital_index", "draft_slot_normalized",
    }
    for col in derived:
        assert col in HEAD_B_PROHIBITED_COLUMNS, (
            f"Expected derived field '{col}' in HEAD_B_PROHIBITED_COLUMNS"
        )


# ── HEAD_B_PROHIBITED_REGEX pattern matching ──────────────────────────────────

def test_prohibited_regex_matches_pick_exact():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    assert pattern.search("pick"), "regex must match exact 'pick'"


def test_prohibited_regex_matches_pick_prefix():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    for col in ("pick_log", "pick_bucket", "pick_rank", "pick_squared"):
        assert pattern.search(col), f"regex must match '{col}'"


def test_prohibited_regex_matches_round_exact():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    assert pattern.search("round"), "regex must match exact 'round'"


def test_prohibited_regex_matches_round_prefix():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    assert pattern.search("round_bucket")
    assert pattern.search("round_rank")


def test_prohibited_regex_matches_nfl_pick_and_round():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    assert pattern.search("nfl_pick")
    assert pattern.search("nfl_round")
    assert pattern.search("nfl_pick_log")


def test_prohibited_regex_matches_draft_capital_prefix():
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    assert pattern.search("draft_capital_index")
    assert pattern.search("draft_slot_normalized")


def test_prohibited_regex_does_not_match_clean_features():
    """Legitimate feature names must not trigger the regex."""
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    clean = [
        "wr_breakout_age",
        "rb_speed_score",
        "age_at_draft",
        "wr_ras_composite",
        "te_ryptpa_final",
        "covid_eligibility_flag",
        "transfer_portal_flag",
        "early_declare",
    ]
    for col in clean:
        assert not pattern.search(col), (
            f"'{col}' should not match draft-capital regex but did"
        )


# ── Position feature matrix — Head B exclusions ───────────────────────────────

def test_head_b_wr_features_exclude_draft_capital():
    """No WR Head B feature may be in HEAD_B_PROHIBITED_COLUMNS."""
    for col in V3_POSITION_HEAD_B_FEATURES["WR"]:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"WR Head B feature '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )


def test_head_b_rb_features_exclude_draft_capital():
    for col in V3_POSITION_HEAD_B_FEATURES["RB"]:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"RB Head B feature '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )


def test_head_b_te_features_exclude_draft_capital():
    for col in V3_POSITION_HEAD_B_FEATURES["TE"]:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"TE Head B feature '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )


def test_head_b_features_exclude_draft_capital_via_regex():
    """No Head B feature for any position matches the draft-capital regex."""
    pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    for position, features in V3_POSITION_HEAD_B_FEATURES.items():
        for col in features:
            assert not pattern.search(col), (
                f"{position} Head B feature '{col}' matches draft-capital regex"
            )


# ── Position feature matrix — Head A inclusions ───────────────────────────────

def test_head_a_features_include_draft_capital_all_positions():
    """Every Head A position must include the full DRAFT_CAPITAL_HEAD_A_ONLY set."""
    for position, features in V3_POSITION_HEAD_A_FEATURES.items():
        assert DRAFT_CAPITAL_HEAD_A_ONLY.issubset(features), (
            f"{position} Head A is missing draft-capital features: "
            f"{DRAFT_CAPITAL_HEAD_A_ONLY - features}"
        )


def test_head_b_excludes_draft_capital_head_a_only_columns():
    """Head B must never include the Head-A-only draft capital columns."""
    for position, features in V3_POSITION_HEAD_B_FEATURES.items():
        overlap = DRAFT_CAPITAL_HEAD_A_ONLY & features
        assert not overlap, (
            f"{position} Head B contains Head-A-only draft capital: {overlap}"
        )


# ── Market field exclusions ───────────────────────────────────────────────────

def test_head_b_features_exclude_market_fields():
    for position, features in V3_POSITION_HEAD_B_FEATURES.items():
        for col in features:
            assert col not in MARKET_PROHIBITED_COLUMNS, (
                f"{position} Head B feature '{col}' is a prohibited market field"
            )


def test_head_a_features_exclude_market_fields():
    for position, features in V3_POSITION_HEAD_A_FEATURES.items():
        for col in features:
            assert col not in MARKET_PROHIBITED_COLUMNS, (
                f"{position} Head A feature '{col}' is a prohibited market field"
            )


# ── Subjective PFF grade exclusions ──────────────────────────────────────────

def test_head_b_features_exclude_pff_grades():
    for position, features in V3_POSITION_HEAD_B_FEATURES.items():
        for col in features:
            assert col not in PFF_GRADE_PROHIBITED_COLUMNS, (
                f"{position} Head B feature '{col}' is a prohibited PFF grade column"
            )


def test_head_a_features_exclude_pff_grades():
    for position, features in V3_POSITION_HEAD_A_FEATURES.items():
        for col in features:
            assert col not in PFF_GRADE_PROHIBITED_COLUMNS, (
                f"{position} Head A feature '{col}' is a prohibited PFF grade column"
            )


def test_pff_grade_set_includes_key_subjective_grades():
    """The PFF grade prohibition set must cover the key subjective columns."""
    for col in ("pff_grade", "pff_route_grade", "pff_receiving_grade"):
        assert col in PFF_GRADE_PROHIBITED_COLUMNS


# ── W1 target column isolation ────────────────────────────────────────────────

def test_w1_target_columns_not_in_head_b_prohibited():
    """Non-expectation W1 target columns must not overlap with draft-capital prohibition.

    Columns that derive from the draft slot (expected_ppg_at_pick, curve_expected_ppg)
    are intentionally in both W1_TARGET_COLUMNS and HEAD_B_PROHIBITED_COLUMNS: they are
    W1 pipeline outputs that are also banned as Head B training features because they
    encode draft slot information.
    """
    _draft_slot_derived_targets: frozenset[str] = frozenset({
        "expected_ppg_at_pick",
        "curve_expected_ppg",
    })
    for col in W1_TARGET_COLUMNS - _draft_slot_derived_targets:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"W1 target column '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )


def test_w1_target_columns_not_in_market_prohibited():
    for col in W1_TARGET_COLUMNS:
        assert col not in MARKET_PROHIBITED_COLUMNS


def test_w1_target_columns_not_in_pff_grade_prohibited():
    for col in W1_TARGET_COLUMNS:
        assert col not in PFF_GRADE_PROHIBITED_COLUMNS


def test_w1_target_columns_include_key_residual_fields():
    """Key W1 outputs must be documented in W1_TARGET_COLUMNS."""
    for col in ("residual_ppg", "expected_ppg_at_pick", "head_b_training_eligible",
                "censored_incomplete_arc", "best3of4_ppg"):
        assert col in W1_TARGET_COLUMNS


# ── TE excluded feature governance ───────────────────────────────────────────

def test_te_breakout_age_is_excluded():
    """te_breakout_age is empirically reversed at TE — must be in TE_EXCLUDED_FEATURES."""
    assert "te_breakout_age" in TE_EXCLUDED_FEATURES


def test_te_pff_subjective_grade_is_excluded():
    assert "te_receiving_grade_pff" in TE_EXCLUDED_FEATURES


def test_te_excluded_not_in_head_a_or_head_b():
    for col in TE_EXCLUDED_FEATURES:
        assert col not in V3_POSITION_HEAD_A_FEATURES["TE"], (
            f"Excluded TE feature '{col}' appears in Head A TE features"
        )
        assert col not in V3_POSITION_HEAD_B_FEATURES["TE"], (
            f"Excluded TE feature '{col}' appears in Head B TE features"
        )


# ── WR candidate quarantine ───────────────────────────────────────────────────

def test_wr_quarantined_candidates_not_in_required_sets():
    """Quarantined WR candidates must not appear in any Head's required feature set."""
    quarantined = {
        "wr_yprr_zone",
        "wr_first_downs_per_route_run",
        "wr_contested_target_rate",
    }
    for col in quarantined:
        assert col not in V3_POSITION_HEAD_B_FEATURES["WR"], (
            f"Quarantined WR candidate '{col}' is in Head B WR features"
        )
        assert col not in V3_POSITION_HEAD_A_FEATURES["WR"], (
            f"Quarantined WR candidate '{col}' is in Head A WR features"
        )


# ── age_at_draft presence in all matrices ─────────────────────────────────────

def test_age_at_draft_in_all_head_a_positions():
    for position, features in V3_POSITION_HEAD_A_FEATURES.items():
        assert "age_at_draft" in features, (
            f"age_at_draft missing from {position} Head A feature matrix"
        )


def test_age_at_draft_in_all_head_b_positions():
    for position, features in V3_POSITION_HEAD_B_FEATURES.items():
        assert "age_at_draft" in features, (
            f"age_at_draft missing from {position} Head B feature matrix"
        )


# ── Provenance flag naming ────────────────────────────────────────────────────

def test_missingness_flag_suffix():
    assert MISSINGNESS_FLAG_SUFFIX == "_missing"


def test_provenance_flag_suffix():
    assert PROVENANCE_FLAG_SUFFIX == "_source"


def test_get_missingness_flag_name():
    assert get_missingness_flag_name("wr_breakout_age") == "wr_breakout_age_missing"
    assert get_missingness_flag_name("rb_speed_score") == "rb_speed_score_missing"


def test_get_provenance_flag_name():
    assert get_provenance_flag_name("rb_speed_score") == "rb_speed_score_source"
    assert get_provenance_flag_name("te_ryptpa_final") == "te_ryptpa_final_source"


def test_provenance_flag_names_are_distinct():
    """_missing and _source flags for the same column must differ."""
    col = "wr_breakout_age"
    assert get_missingness_flag_name(col) != get_provenance_flag_name(col)


# ── check_head_b_feature_leakage enforcement ─────────────────────────────────

def test_leakage_check_raises_on_pick():
    with pytest.raises(ValueError, match="pick"):
        check_head_b_feature_leakage(["age_at_draft", "pick", "wr_breakout_age"])


def test_leakage_check_raises_on_round():
    with pytest.raises(ValueError, match="round"):
        check_head_b_feature_leakage(["round"])


def test_leakage_check_raises_on_nfl_pick():
    with pytest.raises(ValueError):
        check_head_b_feature_leakage(["nfl_pick"])


def test_leakage_check_raises_on_nfl_round():
    with pytest.raises(ValueError):
        check_head_b_feature_leakage(["nfl_round"])


def test_leakage_check_raises_on_derived_pick_via_regex():
    """Derived names matching the regex must trigger the leakage check."""
    with pytest.raises(ValueError):
        check_head_b_feature_leakage(["pick_log"])


def test_leakage_check_raises_on_market_field():
    with pytest.raises(ValueError, match="market"):
        check_head_b_feature_leakage(["ktc_value"])


def test_leakage_check_raises_on_pff_grade():
    with pytest.raises(ValueError, match="PFF grade"):
        check_head_b_feature_leakage(["pff_grade"])


def test_leakage_check_raises_on_pff_receiving_grade():
    with pytest.raises(ValueError):
        check_head_b_feature_leakage(["pff_receiving_grade"])


def test_leakage_check_passes_on_clean_feature_list():
    """A valid Head B feature list must not raise."""
    clean = [
        "age_at_draft",
        "wr_breakout_age",
        "wr_dominator_career",
        "wr_vertical_jump",
        "wr_meets_athletic_floor",
        "covid_eligibility_flag",
        "transfer_portal_flag",
        "early_declare",
    ]
    check_head_b_feature_leakage(clean)  # must not raise


def test_leakage_check_passes_on_empty_list():
    check_head_b_feature_leakage([])  # must not raise


# ── ALL_V3_REQUIRED_FEATURES completeness ─────────────────────────────────────

def test_all_v3_required_contains_universal():
    from src.dynasty_genius.models.head_b_contract import UNIVERSAL_REQUIRED_BOTH_HEADS
    assert UNIVERSAL_REQUIRED_BOTH_HEADS.issubset(ALL_V3_REQUIRED_FEATURES)


def test_all_v3_required_contains_draft_capital():
    assert DRAFT_CAPITAL_HEAD_A_ONLY.issubset(ALL_V3_REQUIRED_FEATURES)


# ── V3 artifact gitignore governance ─────────────────────────────────────────

def test_v3_csv_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text()
    assert "prospects_with_outcomes_v3.csv" in gitignore, (
        "prospects_with_outcomes_v3.csv must be listed in .gitignore"
    )


def test_v3_curves_json_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text()
    assert "expected_ppg_curves_v3.json" in gitignore, (
        "expected_ppg_curves_v3.json must be listed in .gitignore"
    )
