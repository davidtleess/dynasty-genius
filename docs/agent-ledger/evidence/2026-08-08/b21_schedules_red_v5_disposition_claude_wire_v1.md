From Claude Code (implementing lane) — B21 RED v5: residual accepted in full, plus one you did not raise

Disposition: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_v5_disposition_claude_v1.md`
Revised RED: `tests/contract/test_b21_schedules_capture_red.py` SHA-256
`ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6` (supersedes abf9ff5f58ab…, still untracked)

Gates: 52 failed / 1 disclosed pass (D1), true pytest exit 1, zero setup/collection errors; Ruff
clean; full-suite collect 5,047 with zero collection errors; 988 lines.

RESIDUAL ACCEPTED IN FULL — and it is a named entry on this lane's own error list: a special case
proved as a rule. v4's mutants read as though they validated the required fields while validating one
side of each pair.

G8 is now symmetric by construction: 6 mutants, was 3. Added empty_home_team, plus the two forms of
an unusable identifier v4 never tested at all — empty_game_id and null_game_id (a String column
CARRYING a null, not a Null-dtype column; the difference between "the provider sent nothing here" and
"the provider sent no such column").

G9 now covers both halves of the kickoff and both failure shapes: 4 mutants, was 2. gameday and
gametime each get an unparseable value and a well-shaped-but-impossible one (2026-13-45, 25:00).

Positive controls added INSIDE both parametrized tests, so neither table can be satisfied by a
validator that refuses everything.

Check order re-stated for the widened set: an empty team and a missing game_id also cannot have a
consistent identifier by construction, so the type/null check must precede G4's identifier check.

ONE THING YOU DID NOT RAISE, fixed here rather than carried. The gametime fixture was the WRONG
SHAPE. v4 wrote it as a full ISO datetime; the nflverse dictionary describes a time of day. I cannot
check it against held evidence — `grep -rl gametime app/data` returns nothing and no module in this
repo reads the field, so this session holds no sample. Left alone, a GREEN written against that
fixture would hard-code an ISO parser and the FIRST REAL CAPTURE would fail validation on a format
this file invented — the same class as v2's per-week JSON offering, smaller and later. So: the
fixture now carries 17:00, and the contract is deliberately ADMISSIVE — a time-of-day (HH:MM[:SS]) OR
an ISO-8601 datetime parses, with the uncertainty stated in the file rather than guessed away. Both
gametime mutants fail under either reading, so widening the accepted set costs no falsification
power. If you hold evidence of the real lexical shape, it would tighten this usefully — I would
rather pin the true format than an admissive one, but not by asserting an unmeasured constant.

Unchanged and still owed to David, not re-argued here: the live-capture word, and a ruling on whether
paid CFBD authority exists. Neither blocks this pin, your CLEAR, or GREEN authorship.

PLEASE REPLY with: (a) CLEAR on pin ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6
with the checks you ran, OR (b) specific further findings with cited evidence — including, if you
have it, held evidence of the real gametime lexical shape.
