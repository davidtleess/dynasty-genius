# CFBD DATA promotion post-action repair — Codex CLEAR v1

**Date:** 2026-08-03
**Lane:** independent reviewer / RED author
**Verdict:** **CLEAR — G21 + G22 + G23 repair**

## Cleared contract

1. Guard jurisdiction comes from trusted caller configuration, before receipt access.
2. A receipt cannot alter its own `active_path` to opt out; inside jurisdiction, mismatch is
   `promotion_receipt_invalid`.
3. Unrelated targets are outside jurisdiction even when the real receipt is malformed.
4. Jurisdiction uses path identity, not lexical spelling: canonical, symlink, `..`, and inode aliases
   share one rule.
5. Unknown identity is a third state and raises `path_identity_unreadable`; an OS/stat failure never
   becomes write permission.
6. Both destructive production writers derive receipt and governed-active paths from one trusted
   default promotion spec and pass jurisdiction explicitly.
7. The real promoted target and both live aliases refuse with
   `promoted_projection_write_refused`; an unrelated target remains silent.

## Literal bytes and gates

- `src/dynasty_genius/capture/cfbd_data_promotion.py` SHA-256:
  `90fbb6b46d1442f050a74fb9bba0641bda2e44c59af030c7430803d938cbe7c2`.
- Reviewer RED bindings retained exactly:
  - v5 `6f142416ea81d9eb0779a6a0bb45c2b2b67190d12a815517a614d2f893d6cf81`
  - v6 `824737fd91b9fe1009878a119b01827ecea9b5fc95eeab07c808b19d8046276c`
  - v7 `8bca95b0ef3c2989679a7d1f46e3a321fc0ad9975bfe3b3b79136d96b003a195`
- Independent rerun of all eight promotion contract files: **124 passed**.
- Independent v5–v7 + W2b rerun: **79 passed**.
- Implementing-lane fresh full gate on the same final module bytes:
  **4,433 passed / 12 skipped / 9 xfailed / 0 failed; 4,454 collected, zero errors**.
  `4433 + 12 + 9 = 4454`; the +9 collection/pass delta is exactly v5 + v6 + v7.
- `verify_sprint_closeout.py`: **ENFORCE PASS** — python-suite, ruff, standalone-scripts.
- `git diff --check`: clean.

## Live state

- Active SHA-256:
  `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`.
- Durable local preimage SHA-256:
  `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`.
- Current receipt blob SHA-256:
  `70249d2856e163f9b7ad6ac1fb508bec32b0473fc7cab23e39dfcb18a7ff21f1`.
- Rollback ruling remains **do not roll back**; the data and evidence are coherent.

## Backup precision — not a repair blocker

The latest local backup marker is run `20260803T141500Z`, finished
`2026-08-03T17:44:49.984835+00:00`, `completed`, 494 files,
`sha256_verified: true`, with zero failures. It predates the promotion receipt timestamp
`2026-08-04T01:44:07.847Z`. Therefore it does **not** prove the new preimage is already offsite.

The required backup-manifest entry makes the history directory mandatory for the next scheduled
run; it routes the preimage into that run and makes absence/emptiness fail closed. Do not describe
the preimage as offsite-protected until a later completed, hash-verified run inventories that exact
path. Manual backup remains David-gated and was not requested or run here.

## Repository boundary

`HEAD == origin/main == 0a4965320483e97ac394b931eb0702fdaba40f52`; CI run `30871437708`
completed successfully for that pushed pre-repair commit. The cleared G21–G23 repair and reviewer
RED/evidence chain are still uncommitted and unpushed. This CLEAR authorizes neither action by
itself; the implementing lane relies on David's separately reported commit/push word.

No bakeoff, refresh, retrain, model write, feature promotion, result acceptance, or football ruling
is contained in this CLEAR. QB rushing remains a registered hypothesis **UNDER TEST** with no
result; this data movement supplies no evidence about it.
