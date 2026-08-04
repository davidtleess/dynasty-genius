# CFBD DATA promotion post-action review — Codex v3

**Date:** 2026-08-03
**Lane:** independent reviewer / RED author
**Verdict:** **NOT CLEAR — G23 unknown identity fails open**

G22's resolved/inode identity direction is correct, but the shared `_same_file` helper catches an
`OSError` and returns `False`. That boolean means two different things at its call sites:

- role distinctness reads `False` as “assume distinct”; and
- guard jurisdiction reads `False` as “assume unrelated, permit the write.”

An operating-system/stat failure proves neither. The guard's own contract says inability to prove a
write safe must never grant it.

## Binding RED

`tests/contract/test_cfbd_data_promotion_green_review_red_v7.py`
SHA-256: `8bca95b0ef3c2989679a7d1f46e3a321fc0ad9975bfe3b3b79136d96b003a195`
Census: **1 collected / 0 passed / 1 failed / 0 errors**.

The row creates an alias to the promoted fixture and injects OS failures into both resolved-path
and inode identity checks. The current helper returns `False`, jurisdiction stands down, and no
exception is raised.

## Required correction

Unknown identity must be a third state, not `False`. The shared helper may raise a governed
`CfbdPromotionError` with reason `path_identity_unreadable`; that gives both role-distinctness and
guard jurisdiction the same fail-closed behavior. Ordinary lexical, resolved, and inode equality
remain unchanged.

The rollback ruling remains unchanged: **do not roll back**. G23 affects only the uncommitted guard
repair. The pending full gate is superseded until v5, v6, and v7 are green on the literal final
bytes. The RED uses only `tmp_path`; no live artifact was touched. No push.

QB rushing remains a registered hypothesis **UNDER TEST** with no result.
