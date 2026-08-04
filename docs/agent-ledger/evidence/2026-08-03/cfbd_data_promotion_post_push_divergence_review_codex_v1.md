# CFBD DATA promotion post-push divergence review — Codex v1

**Date:** 2026-08-03
**Commit audited:** `fbbde7727f6c307426bb236cee46e2e5baceaca2`
**Base:** `111c26deddac080d8d443c118ddc3d047a297983`
**Verdict:** **NOT CLEAR — D1 two reviewer-authored EOF blank lines**

## Matched

- `HEAD == origin/main == fbbde7727f6c307426bb236cee46e2e5baceaca2`; parent is `0a49653`.
- Commit scope is the reported 15 paths, +691 / -14.
- Committed module SHA-256 is the cleared
  `90fbb6b46d1442f050a74fb9bba0641bda2e44c59af030c7430803d938cbe7c2`.
- Committed v5/v6/v7 RED SHA-256 values match their binding hashes exactly.
- Worktree is clean.
- CI run `30871963240` exists for this commit and was still in progress at audit time.

## D1 — combined-range diff check fails

`git diff --check 111c26d..fbbde77` reports exactly:

```text
tests/contract/test_cfbd_data_promotion_green_review_red_v6.py:46: new blank line at EOF.
tests/contract/test_cfbd_data_promotion_green_review_red_v7.py:54: new blank line at EOF.
```

These blank lines were authored by Codex. Claude correctly preserved the binding RED blobs under
the instruction not to edit reviewer REDs and disclosed the divergence. Codex now narrows that
instruction: assertions and executable content remain immutable, but these two terminal blank lines
must be normalized in a correction commit.

## Required correction

1. Remove exactly the terminal blank-line divergence from v6 and v7; change no assertion, token, or
   executable content.
2. Prove whitespace-only scope with an empty:
   `git diff -w fbbde77..CORRECTION -- <v6> <v7>`.
3. Recompute both current RED hashes and record additive old → current supersessions in the ledger
   and correction evidence. Do not rewrite historical review/CLEAR artifacts or verbatim wire
   records; their old hashes truthfully identify the blobs reviewed at the time.
4. Require zero output / exit 0 from both:
   `git diff --check fbbde77..CORRECTION` and
   `git diff --check 111c26d..CORRECTION`.
5. Report the correction commit SHA, committed hashes, clean worktree, origin relation, and CI result
   if pushed under David's action word.

No full Python rerun is required for two whitespace-only test-file normalizations when the `-w`
proof is empty. CI for the correction remains the remote gate if it is pushed.

## Boundary

This finding does not challenge the G21–G23 repair, live promotion, preimage, receipt, or no-rollback
ruling. It does not authorize commit or push. The current backup precision also stands: the latest
verified backup predates promotion, so offsite inclusion remains unproven until a later inventory.
QB rushing remains **UNDER TEST** with no result.
