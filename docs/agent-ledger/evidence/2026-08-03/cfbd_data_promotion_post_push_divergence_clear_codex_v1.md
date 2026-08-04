# CFBD DATA promotion post-push divergence — Codex CLEAR v1

**Date:** 2026-08-03  
**Range:** `111c26deddac080d8d443c118ddc3d047a297983..7ddc156792051d821de545118edf05fd647d2ecb`  
**Verdict:** **DIVERGENCE-VERIFY CLEAR**

## Verified Git state

- `HEAD == origin/main == 7ddc156792051d821de545118edf05fd647d2ecb`, 0/0.
- Parent is `fbbde7727f6c307426bb236cee46e2e5baceaca2`.
- Correction scope: five paths, +128 / -2 — ledger, two first-committed evidence files, and one
  terminal blank-line deletion from each of v6 and v7.
- Worktree was clean before this CLEAR artifact was authored.
- `git diff --check fbbde77..7ddc156`: zero output, exit 0.
- `git diff --check 111c26d..7ddc156`: zero output, exit 0.

## Corrected proof obligation

Claude's objection is sustained: `git diff -w` alone does not hide deletion of an otherwise blank
line. The correct proof for this change class is:

`git diff -w --ignore-blank-lines fbbde77..7ddc156 -- <v6> <v7>`

It is empty. The literal diff contains exactly one deleted empty line in each RED and no other hunk.
Both RED files pass together: **3 passed**.

Committed current SHA-256 values:

- v6: `84f3df77f371c6b2b8d932437299e285755eed129af839e331e69971a0a9e0f2`
  (supersedes `824737fd91b9fe1009878a119b01827ecea9b5fc95eeab07c808b19d8046276c`).
- v7: `d90841b321f9f988ee96b2f531e4a9ffcd686c314914e023937dd7d7b71f9313`
  (supersedes `8bca95b0ef3c2989679a7d1f46e3a321fc0ad9975bfe3b3b79136d96b003a195`).
- Promotion module remains the cleared
  `90fbb6b46d1442f050a74fb9bba0641bda2e44c59af030c7430803d938cbe7c2`.

Historical artifacts and verbatim wire records correctly retain the hashes of the blobs reviewed at
the time; the ledger's additive supersession table carries the forward state.

## Late-evidence precision

The divergence review and its wire record arrived untracked after `fbbde77` and were normalized
before their first commit in `7ddc156`. Their pre-normalization blobs were never committed and their
hashes were never cited as binding, so they do not require historical SHA supersession. The ledger
phrase that the two late artifacts had supersessions “above” should be read as normalization scope,
not as a claim that a prior committed/cited blob existed. This paragraph is the additive precision
record.

## Remote and live state

- GitHub Actions run `30872235712` completed **successfully** for `7ddc156`; Python checks and
  Frontend checks both succeeded.
- Active SHA-256 remains
  `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`.
- Preimage SHA-256 remains
  `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`.
- Receipt blob SHA-256 remains
  `70249d2856e163f9b7ad6ac1fb508bec32b0473fc7cab23e39dfcb18a7ff21f1`.
- No rollback is warranted.

Backup precision remains unchanged: the latest verified backup predates promotion, so current
offsite inclusion is not proven. No bakeoff, refresh, retrain, model/feature promotion, result
acceptance, or football ruling occurred. QB rushing remains **UNDER TEST** with no result.

