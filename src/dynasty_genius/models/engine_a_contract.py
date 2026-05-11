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
    "completion_pct",
    "yards_per_attempt",
    "td_int_ratio",
    "sack_rate",
    "all_purpose_yards",
    "passing_yards_share",
    "ppa",
    "wepa",
    "rushing_yards",
    "rushing_tds",
    "source_dominator_rating",
    "source_receiving_yards_share",
    "source_completion_pct",
    "source_yards_per_attempt",
    "source_td_int_ratio",
    "source_sack_rate",
    "source_all_purpose_yards",
    "source_passing_yards_share",
    "source_ppa",
    "source_wepa",
    "source_rushing_yards",
    "source_rushing_tds",
}

PLAYERPROFILER_CONTEXT_COLUMNS = {
    "target_share",
    "breakout_age",
    "speed_score",
    "source_target_share",
    "source_breakout_age",
    "source_speed_score",
}

# ── QB Professional Context (context_signal only — never model inputs) ────────
QB_CONTEXT_COLUMNS = {
    "epa_per_dropback",
    "cpoe",
    "dakota",
    "dropback_count",
    "pass_attempts",
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
    "QB": [
        "completion_pct",
        "yards_per_attempt",
        "td_int_ratio",
        "sack_rate",
        "all_purpose_yards",
        "passing_yards_share",
        "ppa",
        "wepa",
        "rushing_yards",
        "rushing_tds",
    ],
}
