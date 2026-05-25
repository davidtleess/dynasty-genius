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
    ENGINE_B_BASE_FEATURES,
    ENGINE_B_EXPERIMENTAL_POSITIONS,
    ENGINE_B_FEATURES_BY_POSITION,
    ENGINE_B_FEATURES_QB,
    ENGINE_B_FEATURES_RB,
    ENGINE_B_FEATURES_TE,
    ENGINE_B_FEATURES_WR,
    ENGINE_B_PROHIBITED_FEATURES,
    OUTCOME_COLUMN,
    OUTCOME_SEASON_COLUMNS,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
    validate_position_feature_contract,
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


# ── Phase 6 explicit exclusions ──────────────────────────────────────────────

def test_route_participation_excluded_from_all_models():
    """r=0.785 collinear with snap_share — removed in Phase 6."""
    assert "route_participation" not in ENGINE_B_ALLOWED_FEATURES


def test_total_points_t_excluded_from_all_models():
    """Redundant with ppg_t × games_t — removed in Phase 6."""
    assert "total_points_t" not in ENGINE_B_ALLOWED_FEATURES


def test_dropback_count_excluded_from_all_models():
    """Redundant with snap_share + games_t — removed in Phase 6."""
    assert "dropback_count" not in ENGINE_B_ALLOWED_FEATURES


def test_pass_attempts_excluded_from_all_models():
    """Redundant with snap_share + games_t — removed in Phase 6."""
    assert "pass_attempts" not in ENGINE_B_ALLOWED_FEATURES


# ── Phase 6 per-position feature contracts ───────────────────────────────────

_BASE = {"age", "ppg_t", "games_t", "snap_share", "aging_curve_value",
         "ppg_t_minus_1", "ppg_t_minus_2", "snap_share_t_minus_1",
         "ppg_t_minus_1_available", "ppg_t_minus_2_available",
         "snap_share_t_minus_1_available"}

def test_all_positions_have_base_features():
    for pos, feature_set in ENGINE_B_FEATURES_BY_POSITION.items():
        missing = _BASE - feature_set
        assert not missing, f"{pos} missing base features: {missing}"


def test_qb_features_include_efficiency_metrics():
    for col in ("epa_per_dropback", "cpoe", "dakota", "is_dual_threat"):
        assert col in ENGINE_B_FEATURES_QB, f"QB contract missing {col}"


def test_rb_features_exclude_receiver_and_qb_metrics():
    receiver = {"weighted_opportunity", "yprr", "tprr"}
    qb_only  = {"epa_per_dropback", "cpoe", "dakota", "is_dual_threat"}
    assert not (receiver & ENGINE_B_FEATURES_RB), "RB contract must not include receiver metrics"
    assert not (qb_only  & ENGINE_B_FEATURES_RB), "RB contract must not include QB-only metrics"


def test_wr_features_include_receiver_metrics():
    for col in ("weighted_opportunity", "yprr", "tprr"):
        assert col in ENGINE_B_FEATURES_WR, f"WR contract missing {col}"


def test_te_features_include_receiver_metrics():
    for col in ("weighted_opportunity", "yprr", "tprr"):
        assert col in ENGINE_B_FEATURES_TE, f"TE contract missing {col}"


def test_qb_efficiency_excluded_from_rb_wr_te():
    qb_only = {"epa_per_dropback", "cpoe", "dakota", "is_dual_threat"}
    for pos in ("RB", "WR", "TE"):
        leaked = qb_only & ENGINE_B_FEATURES_BY_POSITION[pos]
        assert not leaked, f"{pos} contract contains QB-only features: {leaked}"


def test_receiver_metrics_excluded_from_qb_rb():
    receiver = {"weighted_opportunity", "yprr", "tprr"}
    for pos in ("QB", "RB"):
        leaked = receiver & ENGINE_B_FEATURES_BY_POSITION[pos]
        assert not leaked, f"{pos} contract contains receiver-only features: {leaked}"


def test_all_position_features_subset_of_allowed():
    meta = {"player_id", "position", "feature_season", "team",
            "depth_chart_position", "aging_curve_position"}
    for pos, feature_set in ENGINE_B_FEATURES_BY_POSITION.items():
        outside = feature_set - ENGINE_B_ALLOWED_FEATURES - meta
        assert not outside, f"{pos} contract has features outside ALLOWED set: {outside}"


def test_position_contract_validator_accepts_valid_features():
    valid_wr = sorted(ENGINE_B_FEATURES_WR)
    validate_position_feature_contract("WR", valid_wr)  # must not raise


def test_position_contract_validator_rejects_cross_position_leak():
    with pytest.raises(ValueError, match="contract violation"):
        validate_position_feature_contract("RB", ["age", "ppg_t", "epa_per_dropback"])


def test_position_contract_validator_rejects_unknown_position():
    with pytest.raises(ValueError, match="Unknown position"):
        validate_position_feature_contract("K", ["age", "ppg_t"])


def test_position_contract_validator_rejects_missing_required():
    """Passing a subset of required features must raise — partial feature lists are invalid."""
    with pytest.raises(ValueError, match="contract violation"):
        validate_position_feature_contract("WR", ["age", "ppg_t"])


def test_engine_b_base_features_is_public():
    """_BASE_FEATURES renamed ENGINE_B_BASE_FEATURES — must be importable and a frozenset."""
    assert isinstance(ENGINE_B_BASE_FEATURES, frozenset)
    assert "age" in ENGINE_B_BASE_FEATURES
    assert "ppg_t" in ENGINE_B_BASE_FEATURES
    assert "snap_share" in ENGINE_B_BASE_FEATURES


def test_features_by_position_covers_all_four_positions():
    assert set(ENGINE_B_FEATURES_BY_POSITION.keys()) == {"QB", "RB", "WR", "TE"}


# ── Experimental positions ────────────────────────────────────────────────────

def test_engine_b_experimental_positions_defined():
    assert isinstance(ENGINE_B_EXPERIMENTAL_POSITIONS, frozenset)


def test_te_is_not_experimental_after_phase13_gate_pass():
    """Phase 13.3 promoted TE after corrected walk-forward validation."""
    assert "TE" not in ENGINE_B_EXPERIMENTAL_POSITIONS


def test_qb_rb_wr_are_not_experimental():
    for pos in ("QB", "RB", "WR"):
        assert pos not in ENGINE_B_EXPERIMENTAL_POSITIONS, (
            f"{pos} passes the holdout gate and must not be marked experimental"
        )
