"""Engine B Data Contract — Active Player Forecast.

Enforces the Q6 Leakage Contract: features must be strictly Season T.
Outcome is 2-year average PPG (T+1, T+2). See 03-engine-b-decision-record.md.

Phase 6 (v2): per-position feature contracts enforce hard exclusion — excluded
features are dropped from the X matrix entirely, never zero-filled.
See docs/superpowers/plans/2026-05-12-engine-b-v2-stratification.md.

DG-159 (2026-09-04) — ONE DENOMINATOR. David's ruling, relayed the same evening:

    "we need to put the tight ends on the same kind of scale as the rest of the
     players ... It can't have its own scale; it can have a calibration to the
     position, but it has to be on the same scale."

and, on the value: the ceiling must be "the absolute best player in the league, or
something mathematically achievable because we believe it is a Hall of Fame level
Dynasty asset", and "not unreachable or extremely reachable". He chose 20.1 knowing
every cross-positional number on his screen drops about 28% and that the best tight
end goes from 100 to about 47.

Every displayed score is now ``ppg / DVS_SCALE_ANCHOR_PPG[pos] * 100``, and the anchor
is the same number at every position. Position scarcity lives entirely in the
replacement line, which is the "calibration to the position" half of his sentence.

**ENGINE_B_P90_PPG is NOT the denominator any more, and must not be edited to become
one.** It stays what it always measured: the 90th percentile of each position's own
outcome distribution. That is what makes the ceiling of a position sayable —
``P90[TE] / anchor * 100 = 46.8`` is the honest statement that the best tight end is
worth 46.8 on this scale. Overwrite these with 20.1s and that number cannot be computed
from anything left in the code, and two guards built for this change go quiet with every
test still green (decision_logic/counter_arguments.py's derived "top fifth" threshold
becomes a hard 80 that three of four positions can never reach; see
tests/contract/test_dg159_one_scale.py, which pins the separation).

The coupled set, all four members derived from the anchor in models/dvs_scale.py:

    lambda[pos]          = anchor[pos] / anchor[XVAR_ANCHOR_POSITION]     -> 1.000
    replacement_dvs[pos] = REPLACEMENT_PPG[pos] / anchor[pos] * 100
    sigma[pos]           = model_rmse[pos]      / anchor[pos] * 100       (models/dvs_band.py)

and the cancellation identity survives the change of denominator unaltered:

    unclamped xVAR = (DVS - replacement_DVS) * lambda = (ppg - replacement_ppg) * 100 / anchor

RETRACTED EDIT — DO NOT APPLY (SR-13 / DG-092; retraction 2026-08-20):
an earlier SEASON-BRIEF.md instructed that ``XVAR_LAMBDA_ENGINE_B['TE']``
should be 0.703 rather than the then-shipped 0.648, claiming "every TE is
undervalued ~8% in every cross-positional comparison". That finding is
RETRACTED. If you are reading a copy of the brief that still says it, the
copy is stale — this docstring is the record. Under four denominators the
position ceiling cancelled, so TE was not undervalued by the lambda at all;
under one denominator every lambda is 1.000 and there is nothing left to
mis-set. Either way, editing a lambda alone CREATES a distortion rather than
removing one. DVS_SCALE_ANCHOR_PPG, XVAR_LAMBDA_*, REPLACEMENT_PPG and
ENGINE_*_REPLACEMENT_DVS are one coupled system: move them together (new
derivation + David approval) or none. The coupled-identity contract tests in
tests/contract/test_phase15_xvar.py and tests/contract/test_dg159_one_scale.py
fail if any one moves alone.

The clamp-ordering defect this docstring used to name as "the REAL TE defect"
(11 of 89 TEs at the ceiling) was fixed in DG-157: the cross-positional value
now comes off the UNCAPPED score, so a player at the ceiling is no longer
priced at it.
"""
from __future__ import annotations

import re

# ── Outcome Variable ──────────────────────────────────────────────────────────
OUTCOME_COLUMN = "avg_ppg_t1_t2"
OUTCOME_SEASON_COLUMNS = frozenset({"ppg_t1", "ppg_t2", "games_t1", "games_t2"})
FEATURE_SEASON_COL = "feature_season"

# ── What each position actually produces ─────────────────────────────────────
# P90 of avg_ppg_t1_t2 from engine_b_features_v2.csv, May 2026 diagnostic. A
# measured fact about each position's outcome distribution — NOT a scale choice,
# and since DG-159 no longer the denominator anything is divided by.
#
# Its remaining job is to say how high a position can reach on the shared scale:
# `P90[pos] / DVS_SCALE_ANCHOR_PPG[pos] * 100` is that position's ceiling — QB 100,
# RB 78.1, WR 72.1, TE 46.8. Overwriting these with the anchor destroys that
# statement and silently disarms the derived counter-argument threshold; see the
# module docstring and tests/contract/test_dg159_one_scale.py.
#
# Frozen at May 2026 values. Recompute only when the Engine B training
# distribution materially changes — new diagnostic run and David approval.
ENGINE_B_P90_PPG: dict[str, float] = {
    "QB": 20.1,
    "RB": 15.7,
    "WR": 14.5,
    "TE": 9.4,
}

# ── The one denominator every displayed score is divided by ──────────────────
# DG-159. David's ruling, 2026-09-04: one scale for every position, anchored at
# 20.1 points a game. The same value at all four positions IS the ruling — a
# position-varying entry here would be four scales again wearing one name.
#
# 20.1 is the quarterback P90: the most points a game any position is expected to
# produce, so a score of 100 means "the best any football player is projected to
# be", and no position's ceiling exceeds it. That satisfies both halves of what he
# asked for — achievable, because a real quarterback reaches it, and not extremely
# reachable, because only one position can.
#
# Consequences he was told before choosing, measured on the 2026-09-04T18:00:04Z
# artifact: every cross-positional number falls by a uniform factor of about 0.72
# (a change of unit, not of meaning — every ordering, sign and ratio is preserved),
# and the best tight end goes from a pinned 100 to about 47.
DVS_SCALE_ANCHOR_PPG: dict[str, float] = {
    "QB": 20.1,
    "RB": 20.1,
    "WR": 20.1,
    "TE": 20.1,
}

# ── VAR Replacement Baselines (12-team Superflex Full PPR) ────────────────────
# Rank N such that the Nth-best player at the position defines replacement level.
# David's 2026-08-31 ruling 5: "Compute it as an order statistic from the real
# lineup structure. 'Replacement TE = the 12th-best TE, because your league starts
# 12.'"
#
# DG-159 corrects two of the four, on his 2026-09-04 ruling to take both. His
# league starts QB/RB/RB/WR/WR/TE/FLEX/FLEX/SUPER_FLEX across 12 teams: 12
# dedicated quarterback seats, 24 running back, 24 receiver, 12 tight end, and 36
# shared. The four ranks that shipped demanded 48 of those 36 shared places, so no
# split of the flex could make them jointly true (DG-160's shared-slot budget;
# features/replacement_reasoning.py). Receiver alone demanded 28, from a comment
# deriving WR53 as "12 x 3 = 36" — a third dedicated receiver slot the league does
# not have. It starts two.
#
# These are the counts an optimally-filled league week produces: every scored
# player ordered by his served points a game, dedicated seats filled first, then
# the 24 flex and 12 superflex places to the best eligible remaining. Measured on
# the 2026-09-04T18:00:04Z artifact (582 scored players):
#
#     QB  12 dedicated + 12 superflex = 24 started  ->  QB25   (unchanged)
#     RB  24 dedicated +  4 flex      = 28 started  ->  RB29   (was 33)
#     WR  24 dedicated + 20 flex      = 44 started  ->  WR45   (was 53)
#     TE  12 dedicated +  0           = 12 started  ->  TE13   (unchanged)
#
# The 36 shared places are exactly consumed, which is the budget balancing rather
# than a split being assumed. QB and TE were already right and do not move: a
# correction that moved all four would have been fitting, not deriving.
#
# The running-back and receiver ranks are decided at a margin of 0.175 points a
# game, and one player sits across it — Jordyn Tyson, a receiver Sleeper marks
# Inactive, at 10.94. Counting him gives RB29/WR45; excluding him gives RB30/WR44.
# He is counted, because availability is already inside every served score
# (`apply_availability` in pvo_assembler.py) and filtering on status on top of that
# would discount him twice. The alternative is worth 1.10 cross-positional points
# to every receiver, and the choice is recorded here rather than left implicit.
ENGINE_B_VAR_THRESHOLDS: dict[str, int] = {
    "QB": 25,
    "RB": 29,
    "WR": 45,
    "TE": 13,
}

# ── Cross-Positional Scarcity Multipliers (Λ_pos) ─────────────────────────────
# lambda[pos] = DVS_SCALE_ANCHOR_PPG[pos] / DVS_SCALE_ANCHOR_PPG[XVAR_ANCHOR_POSITION]
# (models/dvs_scale.py: derive_lambda). Its only job is to convert a position's
# own scale into the anchor's before points above replacement are compared.
#
# Under one denominator there is no position-specific scale left to convert, so
# every multiplier is 1.000. That is the cancellation identity doing its job, not
# being switched off — the arithmetic it guaranteed is unchanged:
#
#     unclamped xVAR = (DVS - replacement_DVS) * 1.000
#                    = (ppg - replacement_ppg) * 100 / anchor
#
# DO NOT edit any single value here. "TE should be 0.703" is RETRACTED
# (2026-08-20) — see the module docstring. A lambda-only edit CREATES a
# distortion rather than removing one. tests/contract/test_phase15_xvar.py and
# tests/contract/test_dg159_one_scale.py enforce the coupled identity.
XVAR_LAMBDA_ENGINE_B: dict[str, float] = {
    "QB": 1.000,
    "RB": 1.000,
    "WR": 1.000,
    "TE": 1.000,
}

# Engine A scored a prospect against ITS OWN four ceilings, so its multipliers used
# to differ from Engine B's and the two engines' cross-positional values were on
# different units — a rookie and a veteran with the same points above replacement
# did not carry the same number (Engine A's were inflated about 14%). One
# denominator serves both engines, so the two tables are now the same table.
XVAR_LAMBDA_ENGINE_A: dict[str, float] = {
    "QB": 1.000,
    "RB": 1.000,
    "WR": 1.000,
    "TE": 1.000,
}

XVAR_ANCHOR_POSITION: str = "WR"

# ── Trade Evaluation Constants ───────────────────────────────────────────────
# TRADE_PARITY_BAND governs trade fairness math only.
# NOISE_BAND (market_overlay_service.py) governs veteran divergence flag suppression.
# These are separate constants with separate governance. Do NOT alias one to the other.
TRADE_PARITY_BAND: float = 0.10
CONSOLIDATION_KAPPA: float = 0.04
CONSOLIDATION_FLOOR: float = 0.80

# ── What a replacement player produces, in points a game ─────────────────────
# The Nth-best player at each position, N from ENGINE_B_VAR_THRESHOLDS, measured on
# the served scale (`apply_availability(projection_2y, availability_p)`, which is
# what the score itself divides — see pvo_assembler.py). Frozen here rather than
# recomputed at inference time: a replacement level that moved whenever anyone
# else's projection moved would shift every player's number for reasons no card
# could explain.
#
# DG-159 derives these for the first time. They previously existed ONLY as inline
# comments on the two tables below — QB 12.91 / RB 7.29 / WR 8.79 / TE 8.99 — citing
# app/data/backtest/phase14/var_batch_20260516_190328.json as their source. That
# artifact does not contain them; it holds 13.47 / 8.59 / 8.65 / 9.76. Nor does any
# feature season of engine_b_features_v2.csv reproduce them at the shipped ranks,
# nor any population of the served artifact. The numbers were unreachable by any
# derivation, which is why they are computed and dated here instead.
#
# Measured on the 2026-09-04T18:00:04Z artifact, 582 scored players across both
# engines. Re-derive with a dated diagnostic and David's approval, never silently:
# these move ENGINE_*_REPLACEMENT_DVS with them.
REPLACEMENT_PPG: dict[str, float] = {
    "QB": 12.26,  # QB25
    "RB": 9.09,  # RB29
    "WR": 9.05,  # WR45
    "TE": 8.41,  # TE13
}

# ── Where replacement sits on the shared 0-100 scale ─────────────────────────
# replacement_dvs[pos] = REPLACEMENT_PPG[pos] / DVS_SCALE_ANCHOR_PPG[pos] * 100
# (models/dvs_scale.py: derive_replacement_dvs).
#
# This line is the "calibration to the position" David's ruling keeps: on one scale
# a tight end reads low because a tight end produces less football, and what makes
# him startable is that his 46.8 ceiling still clears a replacement at 41.8. That
# comparison is the card's job to show — the raw number alone would mislead.
#
# One table serves both engines. Two existed only because the engines divided by
# different ceilings; replacement level is a fact about the LEAGUE's lineup
# structure and does not depend on which model scored the player.
ENGINE_B_REPLACEMENT_DVS: dict[str, float] = {
    "QB": 61.0,  # 12.26 / 20.1
    "RB": 45.2,  # 9.09 / 20.1
    "WR": 45.0,  # 9.05 / 20.1
    "TE": 41.8,  # 8.41 / 20.1
}

# The same table. Kept as a separate name because the assembler selects by engine;
# tests/contract/test_dg159_one_scale.py pins that they are equal, so a future edit
# to one alone is caught rather than silently splitting the two engines' units again.
ENGINE_A_REPLACEMENT_DVS: dict[str, float] = dict(ENGINE_B_REPLACEMENT_DVS)

# ── Bayesian Blending Constants ──────────────────────────────────────────────

# k_pos: the effective number of games at which the likelihood (Engine B)
# is equal-weighted to the prior (Engine A).
# REQUIRED: fit these from Engine B per-position residual variance before changing.
# Do not adjust k_pos without a validated residual analysis artifact.
DVS_BLEND_K: dict[str, int] = {
    "QB": 6,
    "RB": 5,
    "WR": 5,
    "TE": 7,
}

# Minimum games in feature season required for Engine B DVS eligibility.
# Below this threshold, a player is in the Dead Window: retain Engine A DVS
# with explicit caveat, or stay PRE_MODEL if Engine A data is also absent.
#
# DG-143, David's ruling 2026-09-03 (8 -> 4): a player who missed most of a season
# still gets the model's genuine estimate. His words: "the model is always making
# its genuine estimate". 114 players were refused a number while the pipeline had
# already produced a projection for every one of them.
#
# The served value already prices the absence -- it is P(plays) x E[points | plays]
# (pvo_assembler.apply_availability), and measured on the live 2025 population the
# 4-7 game cohort averages P(plays) 0.488 against 0.847 for 8+ game players. The
# gate was withholding the number, not the discount.
#
# WHAT THIS IS NOT JUSTIFIED BY: an auditor's holdout comparison (RMSE 3.28 for
# 4-7 games vs 3.19 for 8+) does NOT support it -- that filter conditions on the
# outcome and so measured only the ~half of the cohort who came back. Scored
# honestly, ordering for these players is roughly half as good (Spearman 0.380 vs
# 0.781). This constant rests on David's ruling. The market check is WEAKER than
# first reported (DG-143 ticket, closeout audit 2026-09-03 morning): the 0.711
# Spearman against FantasyCalc was the most favourable of seven daily snapshots;
# across all seven the new cohort runs 0.634-0.711 (0.643 on 09-03's own market)
# against a baseline holding 0.788-0.805 -- a gap of ~0.13, not 0.08 -- and at
# n=32 fifteen percent of random subsets of already-scored players score at or
# below 0.711 by chance. What stands on its own: of the 82 players the market
# declines to price at all, 94% score below 20.
ENGINE_B_MIN_GAMES_T: int = 4

# ── PPG season-type ruling (DG-024, David 2026-08-19) ────────────────────────
# David ruled, verbatim, "all games" — Engine B's points-per-game counts every
# game a player played, POSTSEASON INCLUDED. `fetch_and_agg_stats` therefore has
# no `season_type` filter, and that absence is CORRECT BY DECISION, NOT A DEFECT.
# If you are reading this because you found the missing filter and thought it was
# a bug: it is not, and this is the record. That misreading has happened once.
#
# What the ruling does NOT license is silence when the world moves. Preseason is
# absent from `load_player_stats` because nflverse does not publish it there — an
# upstream behaviour, not an invariant this repo enforces. The ruled set below is
# the enforcement: an unruled season type RAISES and names itself, so David is
# asked rather than having his ruling silently reinterpreted. A silent filter
# would overturn the ruling; a loud failure escalates it.
PPG_RULED_SEASON_TYPES: frozenset[str] = frozenset({"REG", "POST"})

# Secondary tripwire: the most games a player can appear in under the ruled set.
# 17 regular-season games (18 week-slots, one bye) + 4 postseason games. Measured
# 2026-08-25 against engine_b_features_v2.csv: max 21, p99 20.
#
# This is the WEAKER of the two checks and must not be mistaken for a second
# guarantee. `games_t` counts DISTINCT WEEKS, and POST continues the regular-season
# numbering (REG 1–18, POST 19–22), so postseason raises it. A hypothetical PRE
# numbered 1–3 would collide with REG weeks and NOT raise it at all, while still
# diluting `ppg_t` — a mean over weekly rows. The season-type assertion is the
# load-bearing check; this one catches only the range-extending case.
#
# If the NFL schedule itself changes, update this deliberately. That is the point.
PPG_MAX_GAMES_T: int = 21

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
    # Phase 13.3 TE-only role-risk feature
    "te_role_is_risk_profile",
})

# ── Phase 6 Per-Position Feature Contracts ───────────────────────────────────
# Each set defines the exact columns passed to that position's Ridge model.
# Metadata columns (player_id, position, feature_season, team, etc.) are
# excluded from these sets — they are used for filtering, not model input.
# Hard rule: columns absent from a position's set must not appear in its X
# matrix at all — not as zeros, not as NaN, not as imputed values.

ENGINE_B_BASE_FEATURES: frozenset[str] = frozenset({
    "age", "ppg_t", "games_t", "snap_share", "aging_curve_value",
    "ppg_t_minus_1", "ppg_t_minus_2", "snap_share_t_minus_1",
    "ppg_t_minus_1_available", "ppg_t_minus_2_available", "snap_share_t_minus_1_available",
})

ENGINE_B_FEATURES_QB: frozenset[str] = ENGINE_B_BASE_FEATURES | frozenset({
    "epa_per_dropback", "cpoe", "dakota", "is_dual_threat",
})

ENGINE_B_FEATURES_RB: frozenset[str] = ENGINE_B_BASE_FEATURES

ENGINE_B_FEATURES_WR: frozenset[str] = ENGINE_B_BASE_FEATURES | frozenset({
    "weighted_opportunity", "yprr", "tprr",
})

ENGINE_B_FEATURES_TE: frozenset[str] = ENGINE_B_BASE_FEATURES | frozenset({
    "weighted_opportunity", "yprr", "tprr",
    # Phase 13.3 te_role_is_risk_profile DROPPED 2026-06-26 — its negative-coefficient
    # promotion basis was a Tyler-Conklin contamination artifact (null on the deduped seed);
    # re-derivation justified by G2 stability only. Still a computed column (ALLOWED_FEATURES /
    # ENGINE_B_OUTPUT_COLUMNS), just not a TE model input. See
    # docs/validation/2026-06-26-te-role-risk-contamination-finding.md + the re-derivation spec.
})

ENGINE_B_FEATURES_BY_POSITION: dict[str, frozenset[str]] = {
    "QB": ENGINE_B_FEATURES_QB,
    "RB": ENGINE_B_FEATURES_RB,
    "WR": ENGINE_B_FEATURES_WR,
    "TE": ENGINE_B_FEATURES_TE,
}

# ── OPTIONAL per-position features — present-if-available, never required ─────
# David's word, 2026-07-31: place NGS per position, "optional-if-present, and
# don't touch QB-1".
#
# This is a SEPARATE mapping on purpose. The REQUIRED sets above are read by
# `backtest_harness.py` (which the QB-1 walk-forward runs through) and are pinned
# by exact-equality contract tests tied to ratified validation state. Adding to
# them made NGS a HARD REQUIRED column of every path those positions touch — the
# QB-1 walk-forward raised `KeyError: [...] not in index` and TE deployment
# training raised `missing required columns`. Optionality therefore lives beside
# the contract, not inside it: the required sets are byte-unchanged, so QB-1 and
# every pinned contract see exactly what they saw before.
#
# These six are POSITION-EXCLUSIVE by measurement on the published candidate —
# each is populated for exactly one position and 0.0% for every other:
#     CPOE / time-to-throw          QB 79.1%
#     separation / cushion          WR 54.1%   TE 35.1%
#     RYOE-per-att / stacked box    RB 47.9%
# That is why they must never enter the UNIFIED matrix, which fits all positions
# together behind a median imputer: there they would not be sparse, they would be
# a WRONG CONSTANT (the QB median CPOE written into 2,485 mostly-non-QB rows).
#
# A consumer opts in explicitly and must intersect with the columns actually
# present. Absence is normal and is never an error.
ENGINE_B_OPTIONAL_FEATURES_BY_POSITION: dict[str, frozenset[str]] = {
    # `ngs_completion_percentage_above_expectation` correlates 0.852 with the
    # existing `cpoe` across their 258 shared QB rows and is the LESS complete of
    # the two (79.1% vs 100%). Kept because Ridge is built for collinear
    # predictors, but it is the one field whose incremental value is genuinely
    # open — name it first if a validation has to drop one.
    "QB": frozenset({
        "ngs_completion_percentage_above_expectation",
        "ngs_avg_time_to_throw",
    }),
    # RB had ZERO position-specific features: it ran on base features alone, which
    # is the likeliest reason it is the weakest Engine B position. These are its
    # first two, and both measure usage QUALITY rather than volume.
    "RB": frozenset({
        "ngs_rush_yards_over_expected_per_att",
        "ngs_percent_attempts_gte_eight_defenders",
    }),
    # Coverage metrics, not production metrics — no existing receiver feature
    # measures how a player is DEFENDED, only what he produced.
    "WR": frozenset({"ngs_avg_separation", "ngs_avg_cushion"}),
    "TE": frozenset({"ngs_avg_separation", "ngs_avg_cushion"}),
}


def optional_features_present(position: str, available_columns) -> list[str]:
    """The position's optional features that this frame actually carries.

    Returns a sorted list, empty when none are present. Absence is the normal
    case for any dataset built before the NGS streams landed, and must never
    raise — that is the whole meaning of optional-if-present.
    """
    optional = ENGINE_B_OPTIONAL_FEATURES_BY_POSITION.get(position, frozenset())
    return sorted(optional & set(available_columns))

# ── Positions with experimental Engine B signal ───────────────────────────────
# Engine B v1 does not outperform the naive baseline for these positions.
# Cleared only when a promoted v2 artifact passes the ≥2/3 gate for that
# position. No agent may remove a position without a passing validation report.
ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset()

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


def validate_ppg_season_types(observed: object) -> None:
    """Raise ValueError if PPG is about to be computed over an unruled season type.

    `observed` is the set of `season_type` values present in the rows that feed the
    points-per-game aggregate, or **None** when the frame carries no `season_type`
    column at all.

    Fail-closed in both directions. An unruled value is rejected because it would
    silently redefine David's 2026-08-19 ruling (DG-024). An absent column is also
    rejected: absence is not evidence of cleanliness, and a guard that passes when
    it cannot see anything is worth nothing. Measured 2026-08-25, `season_type` is
    present for every vintage 2016-2025, so the absent branch does not fire against
    today's nflreadpy.

    This guard NEVER filters. Filtering would overturn the ruling by quietly
    changing what PPG means; raising escalates the decision to David, which is
    where a definition change belongs.
    """
    if observed is None:
        raise ValueError(
            "PPG season-type guard: the player-stats frame carries no `season_type` "
            "column, so David's 2026-08-19 'all games' ruling "
            f"({', '.join(sorted(PPG_RULED_SEASON_TYPES))}) cannot be verified. "
            "Absent is not the same as clean — refusing to compute PPG rather than "
            "assume it is safe."
        )
    unruled = sorted({str(value) for value in observed} - PPG_RULED_SEASON_TYPES)
    if unruled:
        raise ValueError(
            "PPG season-type guard: unruled season type(s) "
            f"{', '.join(repr(value) for value in unruled)} present in the rows "
            "feeding points-per-game. David ruled 2026-08-19 that PPG counts "
            f"{', '.join(sorted(PPG_RULED_SEASON_TYPES))} — all games, postseason "
            "included (DG-024). This is NOT filtered automatically: a silent filter "
            "would reinterpret his ruling. Take the new season type to David and "
            "extend PPG_RULED_SEASON_TYPES only on his word."
        )


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
    2. All required features for this position are present.
    """
    if position not in ENGINE_B_FEATURES_BY_POSITION:
        raise ValueError(f"Unknown position for Engine B v2 contract: {position!r}")

    allowed = ENGINE_B_FEATURES_BY_POSITION[position]
    col_set = set(feature_columns)

    _meta = {"player_id", "position", "feature_season", "team", "depth_chart_position",
             "aging_curve_position", OUTCOME_COLUMN, "training_eligible"}

    # Extra columns not in this position's contract. Optional features are
    # PERMITTED here but never required below — a caller that supplies them is
    # in contract, and a caller that omits them is equally in contract.
    optional = ENGINE_B_OPTIONAL_FEATURES_BY_POSITION.get(position, frozenset())
    extra = col_set - allowed - optional - _meta
    if extra:
        raise ValueError(
            f"Engine B v2 position contract violation for {position}: "
            f"columns not in allowed set: {sorted(extra)}"
        )

    # Missing required features
    missing = allowed - col_set
    if missing:
        raise ValueError(
            f"Engine B v2 position contract violation for {position}: "
            f"missing required features: {sorted(missing)}"
        )
