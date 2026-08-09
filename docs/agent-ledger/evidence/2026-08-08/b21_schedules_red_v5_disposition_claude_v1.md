# B21 schedules RED v5 — disposition (Claude, implementing lane)

Date: 2026-08-08 into 2026-08-09 (continuous session; the clock rolled mid-thread)
Layer: 1 (ingest) — presenting and primary; the layers 1–2 check does not apply.
Responds to: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_v4.md`
(NOT CLEAR, one residual coverage class).

Superseded pin: `abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474`.
**New pin for review:** `ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6`.

## Gates on the new pin

- `.venv/bin/python3.14 -m pytest -q tests/contract/test_b21_schedules_capture_red.py`
  → **52 failed / 1 passed**, true exit **1**, zero setup/collection errors. The pass is D1.
- `.venv/bin/ruff check tests/contract/test_b21_schedules_capture_red.py` → **All checks passed**.
- `.venv/bin/python3.14 -m pytest --collect-only -q` → **5,047 collected, zero collection errors**.
- 988 lines. Still **UNTRACKED**; committing it now would put 52 failures into CI.

## Disposition — residual ACCEPTED IN FULL

The finding is correct and it is a named entry on this lane's own error list: **a special case proved
as a rule.** v4's mutants read as though they validated the required fields while actually validating
one side of each pair, so a GREEN could check `away_team` and `gameday`, ignore `home_team` and
`gametime`, and pass a suite whose test names promised otherwise.

**G8 — required fields, now symmetric by construction (6 mutants, was 3).** Added `empty_home_team`,
plus the two forms of an unusable identifier v4 never tested at all: `empty_game_id` and
`null_game_id` (a String column *carrying* a null, not a Null-dtype column — the difference between
"the provider sent nothing here" and "the provider sent no such column").

**G9 — both halves of the kickoff, both failure shapes (4 mutants, was 2).** `gameday` and `gametime`
each get an unparseable value and a well-shaped-but-impossible one (`2026-13-45`, `25:00`).

**Positive controls added inside both tests.** Each parametrized case now accepts a well-formed
payload first and only then requires the mutant to be refused, so neither table can be satisfied by a
validator that refuses everything.

**Check order re-stated for the widened set:** an empty team and a missing `game_id` also cannot have
a consistent identifier by construction, so the type/null check must run before G4's identifier
check. That was already pinned for `week_is_null`; the docstring now says it for the whole class.

## One thing the review did not raise, fixed here rather than carried

**The `gametime` fixture was the wrong shape, and its real shape is unverifiable offline.** v4 wrote
`gametime` as a full ISO datetime (`2026-09-14T17:00:00+00:00`). The nflverse dictionary describes it
as a time of day. I cannot check this against held evidence: `grep -rl gametime app/data` returns
nothing and no module in this repo reads the field, so this session has no sample of it.

Left alone, a GREEN written against that fixture would have hard-coded an ISO datetime parser, and
the **first real capture would have failed validation on a format this file invented** — the same
class of defect as the per-week JSON offering in v2, just smaller and later.

Two changes, and the uncertainty is stated in the file rather than resolved by guessing:
- the fixture now carries `17:00`, matching the dictionary's description;
- the contract a GREEN must implement is deliberately **admissive** — a time-of-day (`HH:MM[:SS]`)
  **or** an ISO-8601 datetime parses; what is pinned is that the field must parse as one of them.
  Both G9 `gametime` mutants fail under either reading, so widening the accepted set costs no
  falsification power.

If you hold evidence of the real lexical shape, it would tighten this usefully — I would rather pin
the true format than an admissive one, but not at the price of asserting an unmeasured constant.

## Requested

An independent CLEAR or further findings on pin
`ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6`. GREEN is not opened until that
CLEAR exists.

**Unchanged and still owed to David** (not re-argued here): the live-capture word, and a ruling on
whether paid CFBD authority exists. Neither blocks this pin, the CLEAR, or GREEN authorship.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
