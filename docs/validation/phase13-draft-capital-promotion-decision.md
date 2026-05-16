---
document: Phase 13 Draft-Capital Promotion Decision
phase: 13
task: 13.2.3
status: VALIDATION_ONLY
date: 2026-05-15
owner: David
prepared_by: Codex
governance:
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - docs/superpowers/specs/2026-05-15-phase13-final-spec.md
---

# Phase 13 Draft-Capital Promotion Decision

## Decision

Do not promote a new Engine A draft-capital transform in Phase 13 at this time.

Record Task 13.2.3 as **VALIDATION_ONLY / NO PRODUCTION CHANGE**.

## Rationale

The Phase 13.2 implementation now has the correct validation machinery:

- candidate manifest for current baseline, log-decay, position-bucketed, and position-isotonic-step transforms;
- leave-one-draft-class-out evaluation harness;
- bake-off evaluator that compares all required manifest candidates;
- market-derived input rejection;
- small-cohort handling for TE;
- immutable identity snapshot utility.

However, the promotion gate in the approved Phase 13 spec requires more than a working harness. A draft-capital change may be promoted only after:

- the relevant historical identity snapshot is locked for the real backtest cohort;
- the candidate beats the current baseline and log-decay baseline on within-class rank correlation;
- confidence intervals support real lift;
- breakpoints remain stable under pick jitter;
- no market-derived fields enter training data;
- validation artifacts/model-card updates are generated.

The current repo state proves the harness and contracts, but it does not yet contain a real historical bake-off artifact over a locked cohort. The bake-off tests use synthetic/fixture-backed rows to validate behavior, not to justify production model changes.

## Gate Assessment

| Gate | Status | Notes |
|---|---|---|
| Locked historical identity snapshot | Not met for real cohort | Snapshot utility exists, but no real historical cohort snapshot is recorded as the promotion substrate. |
| Beats current baseline | Not assessed on real cohort | Harness supports comparison, but no real artifact is present. |
| Beats log-decay control | Not assessed on real cohort | Control is implemented in manifest and bake-off tests. |
| CI supports real lift | Not met | LOOCV metrics exist, but no real fold artifact/CI review exists for promotion. |
| Pick-jitter stability | Not met | Fixture behavior covers cliff expectations; real cohort stability has not been run. |
| Market leakage guard | Met at harness level | Market-derived `source_fields` are rejected. |
| Model-card / validation artifact | Not met for production promotion | No Engine A model-card update should be emitted until real validation exists. |

## Production Impact

No Engine A feature transform changes are approved by this decision.

No Engine A model artifact is retrained or promoted.

No Engine B behavior changes.

TE remains `EXPERIMENTAL`.

DVS remains out of scope.

Market data remains overlay-only and is not used in training rows.

## Accepted Outcome

Task 13.2.3 is complete as a governance decision:

- **Decision:** validation-only.
- **Production behavior:** unchanged.
- **Leading-candidate implementation:** deferred until real historical artifact review.
- **Next phase work:** proceed to Task 13.3.0 PFF Feasibility Memo.

## Future Promotion Requirements

Before revisiting draft-capital promotion, run the bake-off over real historical Engine A rows with:

- an immutable `identity_snapshot_{run_id}.json`;
- persisted bake-off result artifact by position;
- confidence intervals for primary rank metrics;
- pick-jitter sensitivity report;
- explicit comparison against current baseline and log-decay;
- documented failure or promotion recommendation.

If those artifacts show durable lift, write a narrow implementation spec for the winning transform rather than changing Engine A directly from research code.
