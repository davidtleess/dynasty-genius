"""Engine B data contract tests.

Enforces the Q6 Leakage Contract from 03-engine-b-decision-record.md:
- Strict Season T temporal cutoff — no feature may reference T+1 or T+2.
- Engine A pre-NFL features are prohibited in Engine B training.
- Market-derived features are prohibited.
- Outcome variable is 2-year average PPG (T+1, T+2).
- QB dual-threat threshold is 400 rushing yards/season.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    DUAL_THREAT_RUSHING_THRESHOLD,
    ENGINE_B_ALLOWED_FEATURES,
    ENGINE_B_EXPERIMENTAL_POSITIONS,
    ENGINE_B_PROHIBITED_FEATURES,
    OUTCOME_COLUMN,
    OUTCOME_SEASON_COLUMNS,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_outcome_column_is_2yr_avg_ppg():
    assert OUTCOME_COLUMN == "avg_ppg_t1_t2"


def test_outcome_season_columns_defined():
    assert "ppg_t1" in OUTCOME_SEASON_COLUMNS
    assert "ppg_t2" in OUTCOME_SEASON_COLUMNS


def test_dual_threat_threshold_is_400():
    assert DUAL_THREAT_RUSHING_THRESHOLD == 400


def test_outcome_column_not_in_allowed_features():
    assert OUTCOME_COLUMN not in ENGINE_B_ALLOWED_FEATURES


def test_outcome_season_columns_not_in_allowed_features():
    overlap = OUTCOME_SEASON_COLUMNS & ENGINE_B_ALLOWED_FEATURES
    assert not overlap, f"Outcome columns in allowed features: {overlap}"


# ── Engine A pre-NFL features are prohibited in Engine B ─────────────────────

def test_dominator_rating_is_prohibited():
    assert "dominator_rating" in ENGINE_B_PROHIBITED_FEATURES


def test_college_production_features_are_prohibited():
    college_features = {
        "completion_pct", "yards_per_attempt", "td_int_ratio",
        "sack_rate", "ppa", "wepa", "pick", "round", "draft_year", "college",
    }
    missing = college_features - ENGINE_B_PROHIBITED_FEATURES
    assert not missing, f"Engine A college features not prohibited: {missing}"


def test_market_features_are_prohibited():
    market_features = {"ktc_value", "ktc_rank", "adp", "fantasycalc_value"}
    missing = market_features - ENGINE_B_PROHIBITED_FEATURES
    assert not missing, f"Market features not prohibited: {missing}"


def test_prohibited_features_do_not_appear_in_allowed():
    overlap = ENGINE_B_ALLOWED_FEATURES & ENGINE_B_PROHIBITED_FEATURES
    assert not overlap, f"Prohibited features in allowed set: {overlap}"


# ── validate_no_temporal_leakage ──────────────────────────────────────────────

def test_clean_feature_columns_pass_leakage_check():
    clean_cols = ["player_id", "age", "feature_season", "ppg_t", "snap_share", "epa_per_dropback"]
    validate_no_temporal_leakage(clean_cols)  # must not raise


def test_ppg_t1_column_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["player_id", "ppg_t", "ppg_t1"])


def test_ppg_t2_column_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["player_id", "ppg_t2"])


def test_games_t1_column_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["player_id", "games_t1"])


def test_column_with_t1_suffix_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["snap_share_t1"])


def test_column_with_next_suffix_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["ppg_next_season"])


def test_column_with_future_in_name_raises_leakage_error():
    with pytest.raises(ValueError, match="leakage"):
        validate_no_temporal_leakage(["future_ppg"])


def test_multiple_leakage_violations_all_reported():
    with pytest.raises(ValueError) as exc_info:
        validate_no_temporal_leakage(["ppg_t1", "games_t2", "snap_share"])
    msg = str(exc_info.value)
    assert "ppg_t1" in msg
    assert "games_t2" in msg


# ── validate_no_prohibited_features ──────────────────────────────────────────

def test_clean_features_pass_prohibited_check():
    clean = ["player_id", "age", "snap_share", "epa_per_dropback"]
    validate_no_prohibited_features(clean)  # must not raise


def test_market_feature_raises_prohibited_error():
    with pytest.raises(ValueError, match="[Pp]rohibited"):
        validate_no_prohibited_features(["player_id", "ktc_value"])


def test_college_feature_raises_prohibited_error():
    with pytest.raises(ValueError, match="[Pp]rohibited"):
        validate_no_prohibited_features(["dominator_rating", "age"])


def test_prohibited_check_reports_all_violations():
    with pytest.raises(ValueError) as exc_info:
        validate_no_prohibited_features(["ktc_value", "dominator_rating", "age"])
    msg = str(exc_info.value)
    assert "ktc_value" in msg
    assert "dominator_rating" in msg


# ── Multicollinearity guard ───────────────────────────────────────────────────

def test_target_share_nfl_not_in_allowed_features():
    """weighted_opportunity subsumes target_share_nfl — sub-component must not
    appear alongside the composite to prevent r=0.978 collinearity."""
    assert "target_share_nfl" not in ENGINE_B_ALLOWED_FEATURES


def test_air_yards_share_not_in_allowed_features():
    """weighted_opportunity subsumes air_yards_share — sub-component must not
    appear alongside the composite to prevent r=0.949 collinearity."""
    assert "air_yards_share" not in ENGINE_B_ALLOWED_FEATURES


def test_weighted_opportunity_is_in_allowed_features():
    """The composite (WOPR) must remain; the sub-components are removed."""
    assert "weighted_opportunity" in ENGINE_B_ALLOWED_FEATURES


# ── Experimental positions ────────────────────────────────────────────────────

def test_engine_b_experimental_positions_defined():
    assert isinstance(ENGINE_B_EXPERIMENTAL_POSITIONS, frozenset)


def test_te_is_experimental_position():
    """Engine B v1 does not outperform the naive baseline for TEs.
    TE must be flagged experimental so the service layer adds the caveat."""
    assert "TE" in ENGINE_B_EXPERIMENTAL_POSITIONS


def test_qb_rb_wr_are_not_experimental():
    for pos in ("QB", "RB", "WR"):
        assert pos not in ENGINE_B_EXPERIMENTAL_POSITIONS, (
            f"{pos} passes the v1 holdout gate and must not be marked experimental"
        )
