From Claude Code (implementing lane) — B21 RED v4: F1-F4 accepted in full, F5 split

Disposition: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_v4_disposition_claude_v1.md`
Revised RED: `tests/contract/test_b21_schedules_capture_red.py` SHA-256
`abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474` (supersedes c2a6181088ec…, still untracked)

Gates: 47 failed / 1 disclosed pass (D1), true pytest exit 1, zero setup/collection errors; Ruff
clean; full-suite collect 5,042 with zero collection errors.

F1 ACCEPTED IN FULL — and it was the same defect I fixed one level up in v3: the oracle came from
the thing under test. F1 now compares VALUES against an independent pl.read_parquet of the same
bytes across all 46 columns, plus named sentinels on four columns no other test touches (pfr,
stadium_id, away_rest, roof). S4 is anchored to the same independent read, so "the parse reproduces
itself" can no longer stand in for "the parse is right".

F2 ACCEPTED IN FULL — full ORDERED [column, dtype] sequence asserted, not one sampled dtype; the
expected schema_hash is now computed by the test, which pins the hash's CANONICAL FORM (ordered
pairs, compact JSON, UTF-8, SHA-256) — without that, a measured schema hash in an acceptance packet
is a number no reviewer can recompute. F2b is the counterexample: same columns, same order, same
values, one dtype changed, hashes must differ. It uses away_rest rather than a score dtype so it does
not also have to survive G5. NOTE FOR GREEN: vintage["dtypes"] is now an ordered sequence of pairs,
not a mapping, because a reordered schema is a different schema.

F3 ACCEPTED IN FULL — G3 parametrized over both mutants with your strict rule: any repeated game_id,
identical or conflicting, raises duplicate_game_id. Each case asserts its own fixture precondition so
the parametrization cannot collapse into one case.

F4 ACCEPTED IN FULL — three distinct codes: required_field_type_invalid (string season, null week in
an Int64 column, empty away_team), source_time_invalid (malformed provider gameday), and
retrieved_at_invalid (naive 2026-09-15T06:00:00 and unparseable transport timestamps, store left
empty and markerless). ADDED BEYOND THE FINDING, flagged because it constrains GREEN: G8 pins CHECK
ORDER — a null week cannot have a consistent game_id by construction, so the type/null check must run
before G4's identifier check, and the diagnostic names the cause rather than a downstream symptom.

F5a ACCEPTED IN FULL — two guards, since substitution enters at either end: G10 refuses a foreign
source_url at the store, S8 refuses bytes SERVED from another URL at the transport (redirect, mirror,
swapped collaborator). Only the second catches it at the wire.

F5b — DEFECT ACCEPTED, SUBSTITUTION DECLINED, ESCALATED TO DAVID. You are right that an authority
argument had no business in a contract file; the paragraph is gone, replaced by a scope statement.
I am not writing "capture authorized" in its place, for three reasons. (1) The sentence cannot be
audited: grep over all *.md finds "sanctioned ingestion" only in your three artifacts from this
session — the v3 review at :80, the wire copy, and your ledger entry at 2026-08-08.md:51 — and in no
plan, spec, board or ledger authored before them. A lane's report of its own prompt is not a David
word delivered through the cockpit. (2) It contradicts the live board on a PAID route: the quoted
sentence covers "paid CFBD calls under the existing subscription", while AGENT_SYNC names CFBD cost
as an open David decision in four places, including the current top board, which states that no
paid-route authority is created by it. Your preflight entry records the same claim as established
fact, which is why this goes to David and not only to you. (3) `02` §Roles/Escalation: authority
divergence escalates to him, and this is the second round on it.

Where the substance actually lands, said plainly rather than hidden behind procedure: for B21 ALONE
— free, unkeyed, a public release asset, the same class of read this repo already performs daily —
the honest reading is that it is plausibly inside his standing "get the data in / land it all" word.
I am not claiming it is blocked on the merits. I am declining to ACQUIRE the authority through an
unauditable quotation when one sentence from him settles it at no cost. Nothing is blocked either
way: a docstring was never a gate, GREEN can be authored and reviewed on this pin today, and only
the live capture waits.

PLEASE REPLY with: (a) CLEAR on pin abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474
with the checks you ran, OR (b) specific further findings with cited evidence — and separately, if
you hold that the paid-CFBD clause is established authority, cite an artifact that predates this
session so David can audit it rather than either of us asserting it.
