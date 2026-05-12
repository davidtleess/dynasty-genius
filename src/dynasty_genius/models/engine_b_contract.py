"""Engine B Data Contract — Active Player Forecast.

Enforces the Q6 Leakage Contract: features must be strictly Season T.
Outcome is 2-year average PPG (T+1, T+2). See 03-engine-b-decision-record.md.
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
ENGINE_B_ALLOWED_FEATURES = frozenset({
    # Identity / metadata
    "player_id", "position", "age", "feature_season", "team",
    "depth_chart_position", "is_dual_threat",
    # NFL production — season T
    "ppg_t", "games_t", "total_points_t",
    "snap_share", "route_participation",
    "yprr", "tprr", "weighted_opportunity",
    # QB efficiency (context_signal promoted to Engine B)
    "epa_per_dropback", "cpoe", "dakota", "dropback_count", "pass_attempts",
    # Multi-year trends (T-1, T-2 — historical, not future)
    "ppg_t_minus_1", "ppg_t_minus_2", "snap_share_t_minus_1",
    # Aging-curve state (fitted, continuous)
    "aging_curve_value", "aging_curve_position",
})

# ── Positions with experimental Engine B signal ───────────────────────────────
# Engine B v1 does not outperform the naive baseline for these positions.
# The service layer must surface a caveat on any prediction for these positions.
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
