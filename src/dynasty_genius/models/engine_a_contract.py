"""Engine A v2 Data Contract — Shared constants for production and tests.

Defines the allowed features, prohibited columns, and provenance requirements
for the historical enrichment pipeline and the Engine A retrained models.
"""

# ── Baseline Schema ─────────────────────────────────────────────────────────
BASELINE_COLUMNS = {
    "gsis_id", "pfr_player_name", "position", "season",
    "pick", "round", "team", "college", "age",
    "y2_games", "y2_points", "y3_games", "y3_points",
    "y4_games", "y4_points", "total_games", "total_points",
    "y24_ppg", "low_sample_flag", "is_training",
}

# ── Allowed Enrichment Features ─────────────────────────────────────────────
CFBD_MODEL_INPUT_COLUMNS = {
    "dominator_rating",
    "receiving_yards_share",
    "source_dominator_rating",
    "source_receiving_yards_share",
}

PLAYERPROFILER_CONTEXT_COLUMNS = {
    "target_share",
    "breakout_age",
    "speed_score",
    "source_target_share",
    "source_breakout_age",
    "source_speed_score",
}

# Allowed in the enriched artifact. Model feature use is controlled by
# POSITION_FEATURE_MATRIX and source registry roles, not by artifact presence.
ALLOWED_ENRICHMENT_COLUMNS = CFBD_MODEL_INPUT_COLUMNS | PLAYERPROFILER_CONTEXT_COLUMNS

# ── Leakage: Prohibited Columns (Fail-Closed) ───────────────────────────────
PROHIBITED_COLUMNS = {
    "ktc_value", "ktc_rank", "adp", "fantasycalc_value",
    "dynastynerds_rank", "dynastydatalab_adp",
    "nfl_yards", "nfl_tds", "nfl_targets", "nfl_carries",
    "nfl_receptions", "nfl_air_yards", "nfl_yprr",
    "pff_grade", "pff_route_grade",
    "scout_note", "analyst_note", "narrative",
}

# Anchored regex for broader leakage scanning
LEAKAGE_REGEX = r"^ktc_|^adp|_rank$|^expert|^market_|^value_|^consensus"

# ── Position Mapping ────────────────────────────────────────────────────────
POSITION_FEATURE_MATRIX = {
    "WR": ["dominator_rating", "receiving_yards_share"],
    "RB": ["dominator_rating"],
    "TE": ["dominator_rating", "receiving_yards_share"],
    "QB": [], # Reserved for Phase B / Mobility signals
}
