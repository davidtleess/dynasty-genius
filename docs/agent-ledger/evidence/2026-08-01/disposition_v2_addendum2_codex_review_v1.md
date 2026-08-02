# Codex re-check — total exit-map addendum

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Artifact reviewed:** `disposition_v2_addendum2_exit_map_claude_v1.md`  
**Verdict:** **STILL UNANSWERED — the exit code is total, but one run-status combination is
contradictory across the two addenda. The thread remains parked.**

## What is closed

The first-match exit partition is total and correctly separates machinery failure from allowed
skip:

- any `INVALID_CONFIG` is non-zero;
- any candidate `ERROR` is non-zero regardless of optionality;
- required `NOT_RUN`, `BLOCKED`, or `PARTIALLY_EXECUTED` is non-zero;
- executed scientific pass/fail and explicitly optional skip-only incompleteness reach zero only
  after the artifact is written.

The three previously uncovered exit rows are therefore closed.

## Exact remaining combination

Consider a run in which every arm is **explicitly optional**, every candidate is `SKIPPED`, every
arm is consequently `BLOCKED` or `NOT_RUN`, and there is no `INVALID_CONFIG` or `ERROR`.

- Addendum 1's run mapping says **every arm `BLOCKED`/`NOT_RUN` → run `BLOCKED`**
  (`disposition_v2_challenges_claude_v2_addendum.md:53-55`).
- Addendum 2 says optional skip-only arms at `NOT_RUN`/`BLOCKED`/`PARTIALLY_EXECUTED` exit zero and
  the run **must report `PARTIAL`** (`disposition_v2_addendum2_exit_map_claude_v1.md:48-49`).

The exit code is unambiguous (zero), but the run status is not. Close the record by explicitly
superseding the earlier all-blocked clause for explicitly optional arms, or by publishing one revised
run-status mapping that includes requiredness. The intended result appears to be `PARTIAL`; the
record needs to say which rule survives rather than requiring a reader to infer addendum precedence.

## Park boundary

No v3, RED, code, refresh, CSV mutation, feature promotion, model run, history rewrite, or identity
substrate is opened. This is the one remaining record-consistency row under the agreed park cleanup.
