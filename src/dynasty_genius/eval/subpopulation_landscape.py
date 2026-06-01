"""Subpopulation / Axis-of-Edge Study — pre-registered constants + pure stats.

DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.

Characterizes Engine B vs DynastyProcess expert-consensus (`dynastyprocess_ecr_2qb`)
ranking quality against realized PPG across three pre-registered subpopulations
(aging-cliff transition, high model-vs-consensus disagreement, early-career),
for the whole player universe. Model-blind: all market/identity data is read-only
and joined *after* scoring; nothing here feeds Engine A/B training or any decision
surface (`decision_supported` is never True).

Spec: docs/superpowers/specs/2026-05-31-subpopulation-axis-of-edge-study-design.md
(dual-CLEARED, commit 11e3c2d). Plan: docs/superpowers/plans/
2026-05-31-subpopulation-axis-of-edge-study.md (commit cd8f2b8).

The constants below are PRE-REGISTERED: locked before analysis to protect
statistical integrity. They must remain module-level constants, never inline
literals, so a reviewer can confirm no threshold was tuned to a result.

Task 1: module scaffold + pre-registered constants.
"""
from __future__ import annotations

# Category neutral band on rho_diff: |rho_diff| < NEUTRAL_BAND is reported as
# `statistically_indistinguishable`, independent of the bootstrap CI (spec §4).
NEUTRAL_BAND = 0.05

# Axis 2: |model_rank - consensus_rank| >= this many ranking slots qualifies a
# player as a high model-vs-consensus disagreement case (spec §3, Axis 2).
DISAGREEMENT_MIN_SLOTS = 12

# Axis 3: experience = feature_season - draft_year; early-career = {0, 1, 2}
# seasons (spec §3, Axis 3).
EARLY_CAREER_MAX_EXP = 2

# Minimum slice size to compute Spearman rho; below this the slice reports
# `insufficient_n` (split min-n; NDCG cross-check gated separately at primary_k).
SPEARMAN_MIN_N = 30

# Early-career axis is only emitted when draft_year coverage meets this fraction;
# otherwise the axis surfaces `early_career_axis_unavailable` (fail-closed, no age
# substitution — spec §7).
COVERAGE_GATE = 0.95

# Benjamini-Hochberg target FDR over the aggregate per-(axis, slice, position)
# tests; powered_followup_candidate = (q_value <= FDR_Q) (spec §4/§9.3).
FDR_Q = 0.10

# Aging-cliff transition thresholds on age_at_feature_season — one season ahead of
# the constitution cliffs (RB26/WR28/TE30/QB33) to capture the transition window
# (spec §3, Axis 1).
AGING_THRESHOLDS = {
    "RB": 25,
    "WR": 27,
    "TE": 29,
    "QB": 32,
}
