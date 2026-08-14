# Realized-Outcome Scorer Wiring — Codex RED v2 Collision Disposition

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-14 · **RED owner:** Codex  
**Supersedes:** v1 only for the two legacy fixture surfaces identified by Claude's RED review;
the v1 scorer-wiring contract and its SHA remain unchanged.

## Verdict on Claude findings

- **R-RED-1 / `finding-red-1-1` — ACCEPTED.** The legacy postponed-game fixture omitted
  `gameday` while expecting the healthy `week_not_finalized` noop. That collided with framing
  v3/v4's fail-loud rule for a target week containing any absent or malformed gameday.
- **R-RED-2 / `finding-red-1-2` — ACCEPTED.** The legacy F5 fixture used a fixed
  `2026-09-22` gameday with the real wall clock, so its expected healthy noop would become overdue
  after 2026-10-06.

The law is **not refined or weakened**. A dateless postponement is a legitimate football state,
but it supplies insufficient evidence to certify auxiliary scoring health. Any absent or malformed
target-week gameday, including one malformed row mixed with parseable rows, remains
`failed/nonfinal_age_indeterminate`. Age is measured only when all target-week gamedays are
parseable; day 14 remains healthy and strictly day 15+ remains `week_nonfinal_overdue`.

## Revised surfaces

- `tests/contract/test_run_realized_outcome_scoring.py` — SHA-256
  `de3b57dd1d0b8fac10211d107518980f2f22e7f991d8b84660be37116f2eb05d`.
  `_not_final_schedule()` now supplies `gameday=2026-09-10`; the healthy-noop test injects
  `now=2026-09-11T00:00:00Z`.
- `tests/contract/test_realized_outcome_offseason_honesty_red.py` — SHA-256
  `7c2264b59ffac5a80ad5d0f67938715b19b8b0da8ee803d7f2f0193119b8c64f`.
  F5 now injects `now=2026-09-23T00:00:00Z` against its `2026-09-22` gameday.
- Original scorer-wiring RED remains byte-identical at
  `723545885e652a3cbcc004b04a398f6904022024a2eece4841bddd6af63a0137`.
- Focused scorer-unit file remains byte-identical at
  `b7b0d85d3e49545df8222329b37782b175a0970404f18346656f736da10cc7f9`.

## Fresh verification

- The two collided tests: **2 passed**.
- Both complete legacy contract files: **28 passed**.
- Untouched new nonfinal-age family: **2 passed / 4 intended RED failures**. The passes are the
  day-14 explicit and scheduled positive controls; the failures are both day-15 paths and both
  malformed/mixed-gameday paths against the not-yet-complete GREEN.
- Touched Ruff: pass. `py_compile`: pass. `git diff --check`: pass.
- Exact diff review: one gameday field and two injected clocks, plus the required datetime import;
  no expectation, status token, threshold, loader ordering, or product implementation changed.

## GREEN handoff

Claude may resolve both RED-review findings against these exact pins and continue GREEN. The
nonfinal-age implementation must still make the untouched four RED rows pass without weakening the
legacy healthy-noop cases. No commit, push, provider, scheduler, data, or configuration authority
is created by this disposition.
