# TW28-IDENTITY-4 — Codex correction addendum to current framing-v2 challenge

**Reviewer:** Codex  
**Date:** 2026-07-28  
**Applies to:** `identity_honesty_fix_framing_codex_challenge_v2_current.md`
at SHA-256
`7abe7454cea312f0905c26ec199f342ed84e37b5e7e7ba115023d17b4d61b3f9`

## Correction

Item 7 calls all 6,027 `PRE_MODEL` rows outside QB/RB/WR/TE the live
“category-copy negative control.” That is too broad.

Independent re-measurement:

- 6,009 `PRE_MODEL` rows have a **present, non-modeled position**. These are the true
  live category-copy negative control.
- 18 `PRE_MODEL` rows have **no position**. They belong to the unknown-position
  fallback required separately by item 8, not to the earned category-copy branch.
- 222 `INACTIVE` rows also have no position, and the sentinel is the remaining
  position-absent row: 6,009 + 18 = 6,027; 222 + 18 + 1 = 241 total rows with no
  position.

The core challenge is unchanged: seed 9's INACTIVE-at-modeled-position overlap is
synthetic (live count zero), and Route 1 needs explicit null/unknown-position
precedence. The corrected measured live negative control is **6,009**, not 6,027.

This addendum preserves the original hash-specific challenge as written and makes the
reviewer's correction visible rather than silently rewriting it.
