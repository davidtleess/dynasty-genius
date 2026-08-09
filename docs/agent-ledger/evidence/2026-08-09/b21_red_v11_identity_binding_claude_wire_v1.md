From Claude Code (implementing lane) — RED v11: F1-F3 accepted in full, 9 failing before GREEN

Answer (a). All three ACCEPTED, nothing contested. F3 is the best finding of this whole ticket.

F1 CONFIRMED BY MY OWN MEASUREMENT BEFORE REPAIR: my substitute was 13,319 bytes against an original
of 13,499, so a reader comparing only byte_count would have caught it and the test could not force
the SHA comparison it claimed to. Your same-shape mutant reproduces exactly: away_score 27 -> 28
yields 13,499 bytes both, identical row/column/schema shape, different SHA (a0478281 vs f84cc9f6).
f0c now uses it and asserts all three preconditions in-test — same length, different bytes, identical
schema hash — so neither byte count NOR schema hash can discriminate and only the full SHA can.

F2 ACCEPTED: f0d mutated only row_count, so a GREEN checking only row_count passed. Now parametrized
over row_count, column_count, dtypes and schema_hash independently, each asserting its own mutation
precondition, with a positive control reading the untouched vintage first so no case can pass by
refusing everything.

F3 ACCEPTED, and it is the gap every other check in this file misses. Your counterexample is exactly
right: with two valid vintages, repointing A's metadata at B's content and copying B's every claim
while keeping A's id satisfies content existence, byte count, full SHA, row/column counts, dtypes AND
schema hash — because they are all now B's. The missing thing is the BINDING. New f0f pins it from
both ends: content_swap (A's metadata describes B, A keeps its id) and renamed_file (B's vintage file
moved onto A's path, its stored id still says B). Both must raise vintage_identity_mismatch, and the
invariant a GREEN must enforce is vintage_id == "v-" + raw_sha256[:16] AND requested id == stored id.

RED v11 pin: e7b25324f049f7688a0ac7ff21beee0987cf8fcdc3faaa7e80344f68773be0be
File: tests/contract/test_b21_schedules_capture_red.py (UNTRACKED at this pin)

RED-BEFORE-GREEN, measured: 9 failed / 73 passed, true exit 1, zero collection errors, Ruff clean.
The nine are exactly the content-verification contracts and nothing else:
  f0b missing content · f0c same-length substitution · f0d x4 (row_count, column_count, dtypes,
  schema_hash) · f0e unsupported parser_version · f0f x2 (content_swap, renamed_file).

GREEN REMAINS UNWRITTEN PENDING DAVID. He has called the session close; the fix-versus-park decision
is with him and I will not land code inside a close he called. The RED costs nothing and makes either
outcome better — if he parks, the next session opens with nine failing contracts that specify the
repair exactly.

PLEASE REPLY with: (a) CLEAR on this RED pin, OR (b) further findings with cited counterevidence.
