# Codex offline review — CFBD live-probe endpoint/stat correction

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Scope:** working-tree endpoint/stat-name correction only; no live request and no refresh mutation  
**Verdict:** **CORRECTION CONFIRMED; one regression assertion is still missing.**

## Independently confirmed

- The production diff replaces `/stats/team/season` with `/stats/season` and reads
  `sacksOpponent` instead of the nonexistent `sacksAllowed` field.
- `cfbd_receiving_adapter.py` already uses `/stats/season`, corroborating the endpoint correction.
- `git show 968321a^:src/dynasty_genius/adapters/cfbd_qb_adapter.py` proves both wrong values were
  pre-existing: the parent code calls `/stats/team/season` and reads `sacksAllowed` at lines
  157/171 of that blob.
- The corrected formula is `sacksOpponent / (passAttempts + sacksOpponent)`, which yields
  `18 / 448 = 0.040178...` for the repaired mock fixture.
- Offline focused slice after the edits:
  `tests/contract/test_cfbd_qb_ingest_red.py`, `tests/test_cfbd_qb_adapter.py`,
  `tests/test_w2b_cfbd.py`, and `tests/contract/test_cfbd_qb_ingest_green_review.py` →
  **114 passed, 2 skipped** in 3.46s.

## Missing regression assertion

The corrected routers now return `sacksOpponent`, but neither the RED identity test nor the adapter
suite asserts the resulting `sack_rate`. The RED identity row currently checks YPA, TD:INT,
pass-attempts, PPA, and WEPA only. Therefore the team route may again return `[]` or the field lookup
may regress while this focused slice remains green—the exact vacuity the live probe exposed.

Before a final post-edit census, add one contract assertion on the corrected provider-shaped fixture:

```python
assert result["sack_rate"] == pytest.approx(18 / (430 + 18))
```

This does not block or invalidate the authorized refresh already running; it is a pre-commit
regression lock. The inert `sacksAllowed` record in the raw-persistence review fixture remains
untouched because that test asserts verbatim storage and reads only `passAttempts`.

## Boundary

No paid call, refresh command, running-process interaction, code/test edit, active CSV change,
promotion, or model work was performed by Codex.
