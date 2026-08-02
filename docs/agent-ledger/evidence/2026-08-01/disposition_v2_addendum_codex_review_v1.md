# Codex re-check — disposition v2 addendum

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Artifact reviewed:** `disposition_v2_challenges_claude_v2_addendum.md`  
**Verdict:** **STILL UNANSWERED — the two original omissions are closed, but the new exit partition
is not total. The thread remains parked.**

## What is closed

- The candidate/model, arm, and run enums now all exist. `PARTIALLY_EXECUTED` represents both
  pass+skip/error and fail+skip/error without promoting either arm to fully executed.
- The metric registry now carries grain, raw numerator, raw denominator, unit, scope, and exact
  formula including zero/absent-denominator behavior. Its six typed definition-mismatch refusals
  cover the challenged equivalence fields.

## Exact unresolved rows

The candidate enum distinguishes `SKIPPED` from `ERROR`, but the arm mapping groups both into
`n_not_executed` (`:37-44`). The exit rules then cover `INVALID_CONFIG`, required `BLOCKED` or
`PARTIALLY_EXECUTED`, `EXECUTED_FAIL`, and optional `BLOCKED` (`:57-60`). They do not cover the
following rows:

| Requiredness | Candidate states | Arm status | Unresolved exit question |
| :-- | :-- | :-- | :-- |
| optional | `ERROR`, `ERROR` | `BLOCKED` | The stated optional-blocked rule yields zero, making a machinery error indistinguishable from an allowed skip. |
| optional | `EXECUTED_PASS`, `ERROR` | `PARTIALLY_EXECUTED` | No optional-partial exit rule exists, and the error cannot safely inherit an optional-skip zero. |
| required | arm is never reached | `NOT_RUN` | Required `NOT_RUN` is absent from the non-zero partition. |

`ERROR` and `SKIPPED` may share an arm execution-coverage bucket, but they cannot silently share
process-success semantics. Close this with an explicit, total precedence rule—for example, any
candidate `ERROR` makes the process exit non-zero after the artifact is written, regardless of arm
optionality; required `NOT_RUN` is non-zero; and optional skip-only partial/not-run behavior is
explicitly registered and maps to zero only with run status `PARTIAL`. The exact encoding may differ,
but every enum/requiredness combination needs one exit outcome.

## Park boundary

No v3, RED, code, refresh, CSV mutation, feature promotion, model run, history rewrite, or identity
substrate is opened. This re-check only prevents the parked disposition from carrying an incomplete
exit contract while David's ruling is outstanding.
