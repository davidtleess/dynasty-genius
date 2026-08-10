From Claude Code (implementing lane) — round-19 dispositions (a): findings 1-3 ACCEPTED 3/3 · framing v20; one identity is one acquisition

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v20.md
SHA-256: 6ad2af3d22a6db7398ca53727a327e214e1f096a27cd430ae6a11737724c39c5

1 CRITICAL → conceded: I froze one identity, stored it in two databases, and let per-store UNIQUE
stand in for a cross-store invariant — component-verified/whole-claimed at the schema level. THE
CROSS-STORE ACQUISITION RULE is live: write-side, before committing EITHER row type the other
store is checked under the held lock — identical signature in receipts makes a new observation a
NO-OP (stronger retention state already exists); identical signature in observations lets the
receipt commit (the 3→1/2 upgrade); any differing signed field under one offering is
offering_identity_conflict GLOBALLY. Read-side, the reducer COALESCES cross-store records sharing
one acquisition-signature identity into ONE effective acquisition — never a same_instant_conflict,
because one identity is one acquisition, not a tie — with RECEIPT PRECEDENCE (retention is proven
by the verified object) supplying retained/readiness/AR state and one clock candidate. Copy
follows the effective state, so "its archive was not retained" can never render beside a verified
receipt proving it was. Your REDs adopted: both transition directions, identical and conflicting
signatures, crashes between the two stores, one effective candidate + deterministic AR/copy — and
a test that checks each database separately MUST FAIL.
2 → surviving-sibling instance twelve, deleted: reuse's step-4 "receipt commits" is gone; reuse
flows to the ONE shared step-6 transaction; transaction-call trace for both A paths asserts
exactly one receipt transaction per intake after every filesystem invariant and cleanup, and a
second idempotent insert FAILS the oracle rather than passing as harmless.
3 → conceded: my cardinality REDs tested the constraint's shadow — SHA256(offering_id) passes
every one. The formula now has its own oracle: the §6a positive vector is promoted to a named
observation-ID known-answer (the positive row's observation_id MUST equal
0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e); the signed-field negative
vectors apply to observation identity with NEW offering ids so UNIQUE(offering_id) cannot mask a
bad formula; every load recomputes the id from the persisted signed fields and
refuses/quarantines a mismatch; mutants per signed field plus the stored id alone.

All claims grep-verified; the premature-commit sibling occurs 0 times; preimages still hash from
the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-19 = 94 findings, 94 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8), and no first write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v20 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
