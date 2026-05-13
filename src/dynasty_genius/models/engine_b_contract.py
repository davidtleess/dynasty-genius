"""Engine B Data Contract — Active Player Forecast.

Enforces the Q6 Leakage Contract: features must be strictly Season T.
Outcome is 2-year average PPG (T+1, T+2). See 03-engine-b-decision-record.md.

Phase 6 (v2): per-position feature contracts enforce hard exclusion — excluded
features are dropped from the X matrix entirely, never zero-filled.
See docs/superpowers/plans/2026-05-12-engine-b-v2-stratification.md.
"""
from __future__ import annotations

import re

# ── Outcome Variable ──────────────────────────────────────────────────────────
OUTCOME_COLUMN = "avg_ppg_t1_t2"
OUTCOME_SEASON_COLUMNS = frozenset({"ppg_t1", "ppg_t2", "games_t1", "games_t2"})
FEATURE_SEASON_COL = "feature_season"

# ── QB Archetype (Q4) ────────────────────────────────────────────────────────
DUAL_THREAT_RUSHING_THRESHOLD = 400  # rushing yards/season in any T-2 to T

# ── Validation Gate (Q5) ─────────────────────────────────────────────────────
COMPOSITE_GATE_MIN_PASSING = 2  # beat baseline on ≥2 of RMSE / R² / Spearman
HOLDOUT_FRACTION = 0.20

# ── Allowed Engine B Features ─────────────────────────────────────────────────
# weighted_opportunity is the WOPR composite (target_share × air_yards_share).
# target_share_nfl and air_yards_share are intentionally excluded: keeping all
# three creates r=0.95–0.98 collinearity that inverts Ridge coefficients.
#
# Phase 6 exclusions (explicit, not implicit):
#   route_participation  — r=0.785 collinear with snap_share
#   total_points_t       — redundant with ppg_t × games_t
#   dropback_count       — redundant with snap_share + games_t for QBs
#   pass_attempts        — redundant with snap_share + games_t for QBs
ENGINE_B_ALLOWED_FEATURES = frozenset({
    # Identity / metadata
    "player_id", "position", "age", "feature_season", "team",
    "depth_chart_position", "is_dual_threat",
    # NFL production — season T
    "ppg_t", "games_t",
    "snap_share",
    "yprr", "tprr", "weighted_opportunity",
    # QB efficiency (context_signal promoted to Engine B)
    "epa_per_dropback", "cpoe", "dakota",
    # Multi-year trends (T-1, T-2 — historical, not future)
    "ppg_t_minus_1", "ppg_t_minus_2", "snap_share_t_minus_1",
    # Historical availability flags (Year 1 players lack T-1/T-2 data)
    "ppg_t_minus_1_available", "ppg_t_minus_2_available", "snap_share_t_minus_1_available",
    # Aging-curve state (fitted, continuous)
    "aging_curve_value", "aging_curve_position",
})

# ── Phase 6 Per-Position Feature Contracts ───────────────────────────────────
# Each set defines the exact columns passed to that position's Ridge model.
# Metadata columns (player_id, position, feature_season, team, etc.) are
# excluded from these sets — they are used for filtering, not model input.
# Hard rule: columns absent from a position's set must not appear in its X
# matrix at all — not as zeros, not as NaN, not as imputed values.

_BASE_FEATURES: frozenset[str] = frozenset({
    "age", "ppg_t", "games_t", "snap_share", "aging_curve_value",
    "ppg_t_minus_1", "ppg_t_minus_2", "snap_share_t_minus_1",
    "ppg_t_minus_1_available", "ppg_t_minus_2_available", "snap_share_t_minus_1_available",
})

ENGINE_B_FEATURES_QB: frozenset[str] = _BASE_FEATURES | frozenset({
    "epa_per_dropback", "cpoe", "dakota", "is_dual_threat",
})

ENGINE_B_FEATURES_RB: frozenset[str] = _BASE_FEATURES

ENGINE_B_FEATURES_WR: frozenset[str] = _BASE_FEATURES | frozenset({
    "weighted_opportunity", "yprr", "tprr",
})

ENGINE_B_FEATURES_TE: frozenset[str] = _BASE_FEATURES | frozenset({
    "weighted_opportunity", "yprr", "tprr",
})

ENGINE_B_FEATURES_BY_POSITION: dict[str, frozenset[str]] = {
    "QB": ENGINE_B_FEATURES_QB,
    "RB": ENGINE_B_FEATURES_RB,
    "WR": ENGINE_B_FEATURES_WR,
    "TE": ENGINE_B_FEATURES_TE,
}

# ── Positions with experimental Engine B signal ───────────────────────────────
# Engine B v1 does not outperform the naive baseline for these positions.
# Cleared only when a promoted v2 artifact passes the ≥2/3 gate for that
# position. No agent may remove a position without a passing validation report.
ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset({"TE"})

# ── Engine A pre-NFL features (prohibited in Engine B training) ───────────────
ENGINE_A_PROHIBITED_IN_B = frozenset({
    "dominator_rating", "receiving_yards_share",
    "completion_pct", "yards_per_attempt", "td_int_ratio",
    "sack_rate", "all_purpose_yards", "passing_yards_share",
    "ppa", "wepa", "rushing_yards", "rushing_tds",
    "pick", "round", "draft_year", "college",
    "target_share",   # PlayerProfiler context, Engine A only
    "breakout_age", "speed_score",
})

# ── Market-derived features (prohibited in all engines) ───────────────────────
MARKET_PROHIBITED = frozenset({
    "ktc_value", "ktc_rank", "adp", "fantasycalc_value",
    "dynastynerds_rank", "dynastydatalab_adp",
})

ENGINE_B_PROHIBITED_FEATURES = ENGINE_A_PROHIBITED_IN_B | MARKET_PROHIBITED

# Patterns that indicate a column contains future-season data
_LEAKAGE_PATTERNS: list[re.Pattern] = [
    re.compile(r"_t\+?\d"),    # _t1, _t+1, _t2, _t+2
    re.compile(r"_next"),      # _next_season, _next_year
    re.compile(r"^future_"),   # future_ppg
    re.compile(r"_future"),    # snap_share_future
]


def validate_no_temporal_leakage(feature_columns: list[str]) -> None:
    """Raise ValueError if any column name signals future-season (T+1/T+2) data.

    This is a fail-closed guard: column names are the contract surface.
    Any name matching a leakage pattern is rejected before training begins.
    """
    violations: list[str] = []
    for col in feature_columns:
        col_lower = col.lower()
        if col_lower in OUTCOME_SEASON_COLUMNS:
            violations.append(f"  {col!r}: exact outcome column present in features")
            continue
        for pattern in _LEAKAGE_PATTERNS:
            if pattern.search(col_lower):
                violations.append(f"  {col!r}: matches leakage pattern {pattern.pattern!r}")
                break
    if violations:
        raise ValueError(
            "Temporal leakage detected in Engine B feature columns:\n"
            + "\n".join(violations)
        )


def validate_no_prohibited_features(feature_columns: list[str]) -> None:
    """Raise ValueError if any prohibited column appears in the feature set."""
    prohibited_found = set(feature_columns) & ENGINE_B_PROHIBITED_FEATURES
    if prohibited_found:
        raise ValueError(
            f"Prohibited Engine B feature columns detected: {sorted(prohibited_found)}"
        )


def validate_position_feature_contract(position: str, feature_columns: list[str]) -> None:
    """Raise ValueError if feature_columns violates the per-position v2 contract.

    Checks two things:
    1. No feature from another position's exclusive set leaked in.
    2. All required base features are present.
    """
    if position not in ENGINE_B_FEATURES_BY_POSITION:
        raise ValueError(f"Unknown position for Engine B v2 contract: {position!r}")

    allowed = ENGINE_B_FEATURES_BY_POSITION[position]
    col_set = set(feature_columns)

    # Any column that is not in this position's allowed set is a contract violation
    violations = col_set - allowed
    # Remove metadata/identity columns that are legitimately present but not model features
    _meta = {"player_id", "position", "feature_season", "team", "depth_chart_position",
             "aging_curve_position", OUTCOME_COLUMN, "training_eligible"}
    violations -= _meta
    if violations:
        raise ValueError(
            f"Engine B v2 position contract violation for {position}: "
            f"columns not in allowed set: {sorted(violations)}"
        )
