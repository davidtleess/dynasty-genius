---
document: Engine B Design Decisions
version: 1.0.0
last_updated: 2026-05-11
authority: analytical_design
governed_phase: Phase 5 / Engine B
---

# Engine B Design Decision Record

This document formalizes the binding design decisions for Engine B (Active Player Forecast). No implementation work may deviate from these rules without a David-approved version bump to this document.

## Q1: Outcome Variable
**Decision:** 2-year average PPG (years T+1 and T+2).
**Rationale:** Dynasty asset management requires stability over single-season volatility. A two-year window separates predictive efficiency from injury or schedule-based noise.

## Q2: Prediction Horizon
**Decision:** 2-year.
**Rationale:** Aligns with standard trade decision windows. 1-year is too volatile; 3-year excessively limits the active player pool due to data longevity requirements.

## Q3: Aging Curve Representation (Phase 5 Prerequisite)
**Decision:** Piecewise linear (Ascent-Peak-Decline).
**Rationale:** Provides an interpretable "ascent" slope and "decline" slope with a position-specific peak age breakpoint.
**QB Breakpoints:** Dual-threat QBs (onset ~29), Pocket passers (onset ~33).

## Q4: QB Archetype Split
**Decision:** Single QB model with an interaction term.
**Rationale:** Prevents sample size fragmentation while capturing the faster physical decay of mobile QBs.
**Classification:** `is_dual_threat = True` if rushing yards > 400/season in any season T-2 to T.

## Q5: Validation Gates for Engine B
**Decision:** Must outperform "Prior-Year PPG" (Naive Baseline).
**Structure:** Composite gate (RMSE, R², Spearman) on a 20% held-out test set.
**Success Criteria:** Improvement on ≥2/3 metrics vs. the naive baseline.

## Q6: Leakage Contract
**Decision:** Strict Season T temporal cutoff.
**Mandate:** A separate `src/dynasty_genius/models/engine_b_contract.py` is required.
**Rule:** No feature may access data from season T+1 or later. Features are strictly derived from season T and historical production (T-n).
