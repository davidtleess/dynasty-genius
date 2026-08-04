# CFBD DATA promotion post-action review — Codex v2

**Date:** 2026-08-03
**Lane:** independent reviewer / RED author
**Verdict:** **NOT CLEAR — G22 lexical-path jurisdiction bypass**

G21's trusted-source direction is accepted, but the literal implementation compares trusted
jurisdiction using lexical `Path` equality:

```python
if active_path != governed:
    return
```

A symlink alias or a path containing `..` can reach the exact governed active file while comparing
unequal lexically. Both cases therefore return silently and permit a destructive writer to reach
the promoted bytes through another spelling.

## Binding RED

`tests/contract/test_cfbd_data_promotion_green_review_red_v6.py`
SHA-256: `824737fd91b9fe1009878a119b01827ecea9b5fc95eeab07c808b19d8046276c`
Census: **2 collected / 0 passed / 2 failed / 0 errors**.

The two rows independently prove symlink and `..` aliases resolve to the same file as the trusted
governed active path, then require the ordinary live refusal
`promoted_projection_write_refused`.

## Required correction

Jurisdiction is path identity, not spelling:

1. Compare resolved `active_path` and resolved trusted `governed_active_path` before deciding the
   target is unrelated.
2. Once jurisdiction is established, validate `receipt.active_path` against the trusted governed
   path, not the caller's possibly aliased spelling.
3. Digest/read the supplied active target and retain the ordinary promoted-write refusal.

This is the same path-identity class already governed by the state machine's role-distinctness
matrix. The fix should reuse a single path-identity helper rather than create another hand-selected
comparison rule.

## State and boundary

The rollback ruling is unchanged: **do not roll back**. The live promoted state remains coherent;
G22 affects the uncommitted guard repair. The fresh full gate is superseded until both reviewer RED
files are green on the literal final bytes. Nothing under the live data/evidence tree was touched by
this review; both cases execute below `tmp_path`. No push.

QB rushing remains a registered hypothesis **UNDER TEST** with no result. This work supplies no
evidence about it.
