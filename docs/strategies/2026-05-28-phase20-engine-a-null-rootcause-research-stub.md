---
title: Phase 20 Engine A College-Metric Null — Root-Cause Research Stub
status: RESEARCH STUB (side-session authored by Claude; awaiting David routing → research spec)
date: 2026-05-28
author: Claude (side session)
sibling: docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md (W5 referenced there; lives here, separate)
HARD SCOPE LOCK: Research-only. No production Engine A/B model change, no feature promotion, no .pkl/manifest/contract change may emerge from this stub or its eventual spec. Any drift toward a model change is a hard stop + escalation per the operating loop.
---

# Phase 20 Engine A College-Metric Null — Root-Cause Research

## The question

Phase 20 (and Engine A v3 Head B) failed to make the framework's **Tier-1 college metrics** (dominator, YPRR, college production/efficiency) beat a draft-capital + age baseline:
- W1 WR: 0/3 ridge folds (trimmed 5-feature set hurt RMSE +5.6%).
- W2 RB: 0/3 ridge + gbt (Spearman/NDCG regressed).
- W3 QB: blocked — CFBD API coverage 25.4% < 50% threshold; all 4 features dropped.

**Is this a data-coverage problem or a genuine finding?**
- **Hypothesis A (data):** CFBD coverage/quality is too thin (esp. QB), so the metrics never got a fair test. Fixable with better sourcing.
- **Hypothesis B (signal):** Draft capital + age genuinely *is* the ceiling for rookie prediction — which would be the model **empirically confirming the framework's own #1 tenet** ("draft capital is the single most predictive variable, bar none") while failing to confirm the Tier-2/3 ones. A real, valuable result, not a failure.

These have opposite implications, so distinguishing them matters before any further Engine A investment.

## Proposed research moves (no model change)

1. **Coverage census:** per position, per draft class, what fraction of prospects have non-null dominator / YPRR / college-production after identity join? Where does coverage collapse (QB clearly; quantify WR/RB)?
2. **Power analysis:** at the available n per fold, was there even enough signal-to-noise to detect incremental lift over the draft-capital baseline? (The WR n≈73 collinearity result hints at underpowering, not necessarily no-signal.)
3. **Coverage-stratified re-read:** on the subset *with* full college coverage, do the metrics add lift? (Isolates data-availability from signal.)
4. **Source alternatives:** is CFBD the binding constraint, or would a different college-stats source materially raise coverage? (Sourcing review only — no new pipeline build in this stub.)

## Acceptance / output

- A diagnostic memo answering "A vs B" with numbers, **not** a model change.
- If Hypothesis B holds: document it as a validated finding and stop pouring effort into college-metric enrichment.
- If Hypothesis A holds: scope a *separate, later* coverage-improvement spec (its own David approval).

## Counter-argument (Rule 5)

"This is navel-gazing — just keep trying features." Response: three straight nulls (Phase 16, 19 Head B, 20) across positions is itself evidence; spending more on feature engineering before knowing whether the ceiling is data or signal risks burning effort against Hypothesis B. The cheap diagnostic comes first.
