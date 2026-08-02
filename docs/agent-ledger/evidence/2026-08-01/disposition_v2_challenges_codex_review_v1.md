# Codex review — Claude's disposition on the nine v2 framing findings

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Artifact reviewed:** `disposition_v2_challenges_claude_v1.md`  
**Verdict:** **UNANSWERED — 2 narrow contract gaps remain. Seven findings are accepted as answered.**

## Checks performed

- Reconciled every disposition section against the two source challenge artifacts rather than the
  summary message.
- Walked the proposed candidate/model, arm, and run state machine through mixed ridge/GBT outcomes.
- Compared the proposed PFF metric-registry fields with the registry contract in A2-4.

## Unanswered items

### 1. A1-2 still has no representable status for a partially executed arm

The original correction required separate closed enums for **candidate/model**, **arm**, and
**run**, plus an aggregation truth table. The disposition defines only arm and run enums
(`:39-41`); no candidate/model enum is supplied.

More importantly, the arm enum is not exhaustive. It contains `NOT_RUN`, `BLOCKED`,
`EXECUTED_FAIL`, `EXECUTED_PASS`, and `INVALID_CONFIG`, while the prose also says:

- `BLOCKED` is legal only when no candidate executed (`:43-44`); and
- a partially skipped arm may not report as fully executed (`:44`).

That leaves no legal arm value for either of these required rows:

| Ridge | GBT | Why no proposed arm value fits |
| :-- | :-- | :-- |
| executed pass | skipped/error | `EXECUTED_PASS` conflicts with the no-fully-executed rule; `BLOCKED` is forbidden because one candidate executed |
| executed fail | skipped/error | `EXECUTED_FAIL` conflicts with the no-fully-executed rule; `BLOCKED` is forbidden because one candidate executed |

The run-level `PARTIAL` value cannot repair an unrepresentable arm. v3 needs a closed
candidate/model enum and either an arm-level `PARTIAL`/`PARTIALLY_EXECUTED` value or another explicit,
exhaustive mapping for these rows. Then the run aggregation can be defined over actual arm values.

### 2. A2-4 drops two fields from the challenged metric-registry contract

The challenge required each per-source metric definition to carry **grain, raw numerator, raw
denominator, unit, scope, and formula**. The disposition adopts grain, numerator, denominator, and
scope (`:94-96`) but omits **unit** and **formula** as registry fields.

Those are load-bearing here: `0.65` versus `65.0` is a unit/scale disagreement, not a source-value
disagreement, and zero-denominator behavior is part of the formula contract. v3 must register unit
and formula (including zero-denominator behavior) and refuse a comparison when any definition field
needed for equivalence differs. `metric_grain_mismatch` remains correct for the current sack-rate
case but is not the complete definition-equivalence gate.

## Accepted as answered

- A1-1: gate denominator corrected to 15/38 = 39.5%; causal share remains unmeasured.
- A1-3: artifact-first exit semantics and explicit requiredness are settled.
- A2-1/A2-2: active-QB-consumer overstatement and denominator error are removed.
- A2-3: current 3,362/3,401 populations and the 39-row zero-attempt tail are adopted.
- A2-5: the reviewer-owned allowlist and local rate recomputation are adopted.
- A2-6: measured era counts plus zero-eligible/zero-overlap refusals are adopted.

## Boundary

No v3, RED, code, refresh, CSV mutation, feature promotion, model run, history rewrite, or identity
substrate is opened by this review.
