"""Engine A v3 Head B Feature Contract — Phase 19.

Defines:
  - HEAD_B_PROHIBITED_COLUMNS: draft-capital columns banned from Head B.
  - HEAD_B_PROHIBITED_REGEX: pattern for derived draft-capital names.
  - Universal and per-position feature sets for Head A and Head B.
  - Missingness and provenance flag naming conventions.
  - check_head_b_feature_leakage(): enforcement called by bake-off harness (W4).

Design rules (from design spec §1.3 and §3):
  - Both heads respect the universal market leakage ban (engine_a_contract.py).
  - Head B's draft-capital exclusion is an *additional* contract beyond the
    universal ban — encoded here as HEAD_B_PROHIBITED_COLUMNS and enforced by
    a dedicated test suite (tests/test_head_b_contract.py).
  - Subjective PFF film grades are prohibited from both heads; PFF objective
    charting (YPRR, MTF/touch, route counts) is a Candidate feature gated on
    §6.1 of the design spec.
  - Required features with unavailable sources get explicit nullable columns and
    provenance flags — no silent imputation.

Feature status vocabulary:
  Required      — must be attempted; missing rows get _missing="1" flag.
  Candidate     — gated on §6.1 PFF intake decision; quarantined until cleared.
  Excluded      — banned regardless of signal strength.
"""

from __future__ import annotations

import re

# ── Head B Draft-Capital Prohibition ─────────────────────────────────────────

HEAD_B_PROHIBITED_COLUMNS: frozenset[str] = frozenset({
    # Direct draft-capital fields in source training CSV
    "pick",
    "round",
    # Normalized / aliased forms
    "nfl_pick",
    "nfl_round",
    "overall_pick",
    # Common derived forms
    "pick_bucket",
    "round_bucket",
    "pick_log",
    "pick_squared",
    "pick_rank",
    "round_rank",
    "nfl_pick_log",
    "draft_capital_index",
    "draft_slot_normalized",
    "pick_percentile",
    "pick_relative",
    "draft_pick_value",
    "pick_value",
    "round_value",
})

# Anchored regex for broader draft-capital pattern matching.
# Used in check_head_b_feature_leakage() in addition to the explicit set.
HEAD_B_PROHIBITED_REGEX: str = (
    r"^pick$|^pick_"           # "pick" exact or "pick_*" (pick_log, pick_bucket …)
    r"|^round$|^round_"        # "round" exact or "round_*"
    r"|^nfl_pick|^nfl_round"   # "nfl_pick*", "nfl_round*"
    r"|^draft_capital|^draft_slot"  # derived capital composites
)

# ── Market Overlay Prohibition (cross-reference; engine_a_contract authoritative) ─

MARKET_PROHIBITED_COLUMNS: frozenset[str] = frozenset({
    "ktc_value", "ktc_rank", "adp", "fantasycalc_value",
    "dynastynerds_rank", "dynastydatalab_adp",
    "nfl_yards", "nfl_tds", "nfl_targets", "nfl_carries",
    "nfl_receptions", "nfl_air_yards", "nfl_yprr",
})

# ── Subjective PFF Grade Prohibition ─────────────────────────────────────────

PFF_GRADE_PROHIBITED_COLUMNS: frozenset[str] = frozenset({
    "pff_grade",
    "pff_route_grade",
    "pff_receiving_grade",
    "pff_blocking_grade",
    "pff_run_block_grade",
    "pff_pass_block_grade",
    "pff_overall_grade",
    "pff_pass_rush_grade",
})

# ── Missingness / Provenance Flag Convention ──────────────────────────────────
# For every Required feature column `col`:
#   col + MISSINGNESS_FLAG_SUFFIX  → "1" if value missing, "0" if present
#   col + PROVENANCE_FLAG_SUFFIX   → source identifier ("cfbd", "combine", "ras",
#                                    "nfl_data_py", "derived") or "" if missing

MISSINGNESS_FLAG_SUFFIX: str = "_missing"
PROVENANCE_FLAG_SUFFIX: str = "_source"


def get_missingness_flag_name(feature_col: str) -> str:
    """Return the missingness flag column name for a feature column."""
    return feature_col + MISSINGNESS_FLAG_SUFFIX


def get_provenance_flag_name(feature_col: str) -> str:
    """Return the provenance flag column name for a feature column."""
    return feature_col + PROVENANCE_FLAG_SUFFIX


# ── W1 Target Columns (must not be contaminated by W2 leakage rules) ─────────

W1_TARGET_COLUMNS: frozenset[str] = frozenset({
    "best3of4_ppg",
    "censored_incomplete_arc",
    "expected_ppg_at_pick",
    "residual_ppg",
    "head_b_training_eligible",
    "target_version",
    "curve_version",
})

# ── Universal Required Features (both heads, all positions) ──────────────────
# These are directly derivable from or present in the source training CSV.
# CFBD-derived columns (early_declare, final_college_age, era flags) are listed
# as Required but populated by the Phase 19 W2 enrichment pipeline; rows where
# source data is unavailable carry _missing="1".

UNIVERSAL_REQUIRED_BOTH_HEADS: frozenset[str] = frozenset({
    "age_at_draft",           # source column "age"; populated in W1 pipeline
    "early_declare",           # CFBD: years_played < typical for position
    "final_college_age",       # CFBD: age in final college season
    "weight",                  # NFL Combine / RAS
    "height",                  # NFL Combine / RAS
    "covid_eligibility_flag",  # CFBD: years_played > 4 or years_since_HS > 4
    "transfer_portal_flag",    # CFBD: school changes detected in career
})

# Draft capital — Head A only. Explicitly excluded from Head B.
DRAFT_CAPITAL_HEAD_A_ONLY: frozenset[str] = frozenset({
    "nfl_pick",    # = source "pick"
    "nfl_round",   # = source "round"
})

# ── WR Feature Contract ───────────────────────────────────────────────────────

WR_REQUIRED_BOTH_HEADS: frozenset[str] = frozenset({
    "wr_breakout_age",               # CFBD: season of first ≥20% dominator
    "wr_dominator_career",           # CFBD: career dominator rating
    "wr_dominator_final",            # CFBD: final-season dominator rating
    "wr_market_share_yds",           # CFBD: recv yds / team total yds
    "wr_rec_tds_per_game_final",     # CFBD: TDs per game, final season
    "wr_yards_per_reception_career", # CFBD: career YPR (aDOT proxy)
    "wr_vertical_jump",              # NFL Combine: Teramoto 2016 (p=0.004)
    "wr_meets_athletic_floor",       # Boolean: Szekely 2023 viability gate
    "wr_ras_composite",              # RAS.football composite score
    "wr_early_declare",              # CFBD: early-declare flag
})

WR_CANDIDATE_FEATURES: frozenset[str] = frozenset({
    "wr_yprr_final",                # PFF objective charting — gated on §6.1
    "wr_yprr_zone",                 # Quarantined — single-source claim
    "wr_first_downs_per_route_run", # Quarantined — single-source claim
    "wr_contested_target_rate",     # Quarantined — low confidence, not corroborated
})

WR_EXCLUDED_FEATURES: frozenset[str] = frozenset({
    "wr_40_yard_standalone",  # Not predictive in isolation
    "wr_bench_press",         # Kuzmits & Adams 2008 — not predictive
    "wr_broad_jump",          # Kuzmits & Adams 2008 — not predictive
})

# ── RB Feature Contract ───────────────────────────────────────────────────────

RB_REQUIRED_BOTH_HEADS: frozenset[str] = frozenset({
    "rb_speed_score",          # Barnwell 2008: weight × 40-time composite
    "rb_10_yard_split",        # NFL Combine: Teramoto 2016 peer-reviewed (p<0.001)
    "rb_weight",               # NFL Combine: durability + Speed Score component
    "rb_3cone",                # NFL Combine: lateral agility
    "rb_meets_athletic_floor", # Boolean: Szekely 2023 viability gate
    "rb_ras_composite",        # RAS.football composite score
    "rb_career_dominator",     # CFBD: career dominator (15% threshold)
    "rb_final_dominator",      # CFBD: final-season dominator
    "rb_scrimmage_ypg",        # CFBD: all-purpose yards per game
    "rb_rec_ypg",              # CFBD: receiving yards per game
    "rb_school_sp_plus",       # CFBD: SOS-adjusted school rating
    "rb_age_at_draft",         # nfl_data_py: chronological age at draft
})

RB_CANDIDATE_FEATURES: frozenset[str] = frozenset({
    "rb_mtf_per_touch",           # PFF objective charting — gated on §6.1
    "rb_tprr_final",              # PFF objective charting — gated on §6.1
    "rb_yards_created_per_carry", # Fantasy Points charted — ablation only
})

# ── TE Feature Contract ───────────────────────────────────────────────────────

TE_REQUIRED_BOTH_HEADS: frozenset[str] = frozenset({
    "te_ryptpa_final",               # CFBD: recv yds per team pass attempt
    "te_career_dominator",           # CFBD: career dominator (15% threshold)
    "te_yards_per_reception_career", # CFBD: YPR / aDOT proxy
    "te_deep_yard_share",            # CFBD: fraction of yards on deep routes
    "te_height_adj_speed_score",     # NFL Combine: height-adjusted speed
    "te_ras_composite",              # RAS.football (3.76 floor warning, not kill)
    "te_weight",                     # NFL Combine
    "te_bmi",                        # Derived: weight / height²
    "te_age_at_draft",               # nfl_data_py: routing only; expect ~0 coeff
})

TE_CANDIDATE_FEATURES: frozenset[str] = frozenset({
    "te_yprr_career",  # PFF objective charting — gated on §6.1
})

TE_EXCLUDED_FEATURES: frozenset[str] = frozenset({
    "te_breakout_age",         # Empirically reversed at TE — excluded per §3.5
    "te_receiving_grade_pff",  # Subjective PFF grade — excluded per §6.3
})

# ── Position Feature Matrices ─────────────────────────────────────────────────
# These define what columns a Head A or Head B model for each position is
# *allowed* to receive. The W3/W4 bake-off selects the actual training feature
# subset from within these sets.

V3_POSITION_HEAD_A_FEATURES: dict[str, frozenset[str]] = {
    "WR": UNIVERSAL_REQUIRED_BOTH_HEADS | DRAFT_CAPITAL_HEAD_A_ONLY | WR_REQUIRED_BOTH_HEADS,
    "RB": UNIVERSAL_REQUIRED_BOTH_HEADS | DRAFT_CAPITAL_HEAD_A_ONLY | RB_REQUIRED_BOTH_HEADS,
    "TE": UNIVERSAL_REQUIRED_BOTH_HEADS | DRAFT_CAPITAL_HEAD_A_ONLY | TE_REQUIRED_BOTH_HEADS,
}

# Head B: same as Head A minus DRAFT_CAPITAL_HEAD_A_ONLY.
V3_POSITION_HEAD_B_FEATURES: dict[str, frozenset[str]] = {
    "WR": UNIVERSAL_REQUIRED_BOTH_HEADS | WR_REQUIRED_BOTH_HEADS,
    "RB": UNIVERSAL_REQUIRED_BOTH_HEADS | RB_REQUIRED_BOTH_HEADS,
    "TE": UNIVERSAL_REQUIRED_BOTH_HEADS | TE_REQUIRED_BOTH_HEADS,
}

# All Required feature columns across all positions and heads.
ALL_V3_REQUIRED_FEATURES: frozenset[str] = (
    UNIVERSAL_REQUIRED_BOTH_HEADS
    | DRAFT_CAPITAL_HEAD_A_ONLY
    | WR_REQUIRED_BOTH_HEADS
    | RB_REQUIRED_BOTH_HEADS
    | TE_REQUIRED_BOTH_HEADS
)

# ── Leakage Enforcement ───────────────────────────────────────────────────────

def check_head_b_feature_leakage(feature_names: list[str]) -> None:
    """Raise ValueError if any feature violates Head B contracts.

    Checks in order:
    1. Direct membership in HEAD_B_PROHIBITED_COLUMNS (draft capital).
    2. Pattern match against HEAD_B_PROHIBITED_REGEX (derived draft capital).
    3. Direct membership in MARKET_PROHIBITED_COLUMNS.
    4. Direct membership in PFF_GRADE_PROHIBITED_COLUMNS.

    Called by the W4 bake-off harness before any Head B training run.
    """
    prohibited_pattern = re.compile(HEAD_B_PROHIBITED_REGEX)
    for name in feature_names:
        if name in HEAD_B_PROHIBITED_COLUMNS:
            raise ValueError(
                f"Head B leakage: '{name}' is a prohibited draft-capital column. "
                "Remove it from Head B feature list."
            )
        if prohibited_pattern.search(name):
            raise ValueError(
                f"Head B leakage: '{name}' matches draft-capital regex pattern. "
                "Remove it from Head B feature list."
            )
        if name in MARKET_PROHIBITED_COLUMNS:
            raise ValueError(
                f"Head B leakage: '{name}' is a prohibited market-overlay column."
            )
        if name in PFF_GRADE_PROHIBITED_COLUMNS:
            raise ValueError(
                f"Head B leakage: '{name}' is a prohibited subjective PFF grade column."
            )
