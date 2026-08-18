# PR #158 merge-strategy review — Codex v1

Date: 2026-08-18
Thread: `w#dvs-disclosure-1`
Verdict: **MERGE-STRATEGY CLEAR — merge commit, preserve branch**

## Strategy ruling

Concur with:

```bash
gh pr merge 158 --repo davidtleess/dynasty-genius --merge
```

Do not add `--delete-branch`. Do not squash. Do not rebase.

## Why merge commit is the correct strategy

1. **It preserves the reviewed commit identity.** PR #158 contains exactly one commit,
   `f29a1b7424f5143838a4125338358f20ed0677c0`, whose production, contract, and review blobs were
   independently pin-verified. A merge commit retains that object unchanged as its second parent.
   Squash or rebase would create a new commit SHA and discard the strongest audit binding without
   resolving any divergence.
2. **It matches repository history.** Recent first-parent PR landings, including #157, #133, #128,
   and #126, are merge commits. All three GitHub merge methods are enabled, so this is a deliberate
   convention choice rather than a platform restriction.
3. **There is nothing to linearize.** Live GitHub state shows base
   `33562fdafd9b4c554078d69fa63cf2b4eef5491c`, head `f29a1b7…`, one commit, `MERGEABLE`, and
   `CLEAN`. The head is already directly based on the current base.
4. **Branch preservation is the least-destructive boundary.** Repository setting
   `delete_branch_on_merge=false`; omitting `--delete-branch` leaves branch deletion as a separate
   David decision.

## Live PR and CI verification

- GitHub connector and `gh pr view` independently report PR #158 OPEN, non-draft, head
  `f29a1b7…`, base `33562fd…`, one commit, 27 changed files, +1,859/-4, mergeable/CLEAN.
- Actions run `32175380028` is complete/success on exact head `f29a1b7…`:
  Frontend checks passed in 1m0s; Python checks passed in 3m24s.
- The Python job log independently reports **6,145 passed / 44 skipped / 0 failed** in 145.04s.
  This is the clean-checkout result. The differing local count is not a regression signal because
  it is a different tree and environment; the untracked governed-cadence RED is absent from CI.

## Additive-valuation consumer challenge

A committed-tree sweep at `f29a1b7` found no positional or exact-shape consumer threatened by the
two additive valuation keys:

- Production and script consumers read `valuation` by named key through `.get(...)` or explicit
  subscripting. No consumer iterates `valuation.values()`, destructures by position, or compares the
  valuation key set for exact equality.
- The API `PlayerModelLane` is manually constructed from named existing fields. It does not receive
  the two additions, which is the already-disclosed reason Studio R1 remains backend-half only.
- No frontend code directly consumes the artifact's valuation block.
- The one exact whole-row contract is `test_surface3_pvo_preservation.py`; its expected valuation
  block was deliberately widened for both keys and passes in CI and the focused 23-test bundle.
- Model-forward capture canonicalizes dictionaries with sorted keys; the new disclosure fields
  intentionally contribute to the semantic row content, not positional interpretation.

No concrete consumer objection survives this sweep.

## Execution guard and post-merge receipt

Immediately before executing the merge, re-fetch PR state and require all of these to remain exact:

- head `f29a1b7…`
- base `33562fd…`
- state OPEN, non-draft, mergeable `MERGEABLE`, merge state `CLEAN`
- Frontend and Python checks completed successfully

Any change to head, base, merge state, or checks invalidates this strategy CLEAR and returns to the
cockpit before merge. After execution, record the actual merge SHA, verify its ordered parents are
base `33562fd…` and reviewed head `f29a1b7…`, verify remote `main` points to the merge commit, retain
the branch, and report exact-head post-merge CI when available.

## Boundaries

- David's verbatim “merge it” supplies merge authority; this review does not broaden it to branch
  deletion, further code changes, API/client regeneration, Studio R2-R5 work, or cleanup.
- Studio R1 remains half-closed after merge.
- The previously recorded whole-commit `git diff --check` qualification remains evidence-only and
  non-blocking: 14 CommonMark hard-break spaces in seven exact hash-pinned review files, no
  production/test line, no commit divergence.

**MERGE-STRATEGY CLEAR: merge commit, preserve branch.**
