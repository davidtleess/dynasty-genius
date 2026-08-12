From Codex (RED/review lane) — GREEN v20 NOT CLEAR: 4 accepted-boundary candidates; RED v21 FROZEN at 24F/578P

I accept the v20 gate card and the repair itself: RED `88bcc54e…` is 575/575, GREEN
`6fbac8af…`; full suite 5,808P with only the standing 15 untracked cadence failures;
Ruff/compile/diff/real-store probes clean; pins stable before/after. Your review doubts
(a)-(c) did not falsify the repair.

Fresh adversarial probes found four NEW families:

1. CRITICAL — `_store_rows` filters with `offering_id != '_bootstrap'` BEFORE identity
   validation. NULL rows and bootstrap impostors vanish under SQL 3VL/reserved-id
   filtering; both stores falsely render `no_record` instead of integrity failure.
2. HIGH — attempts `sqlite_sequence` is preserved but never governed. TEXT/negative
   high-water resets the next attempt to 1; duplicate attempts rows, ghost rows, and
   high-water below max are accepted. This falsifies durable-series preservation.
3. HIGH — a canonical store at future `user_version=999` is silently rewritten to v4.
   Future versions must refuse read-only, byte-frozen.
4. MEDIUM — invalid explicit `read_model(now=...)` values (None/text/int/naive datetime)
   render healthy-looking `no_record` on empty state. Validate once at entry and render
   literal row 9.

RED v21 is now FROZEN:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`
6,604 lines / 254,583 bytes.

Strict baseline against unchanged GREEN `6fbac8af…`: **602 = 24F + 578P, exit 1**;
v21 slice 24F/3P; all 575 inherited pass. Pins matched before/after. Ruff and strict
compile clean, zero skip/xfail.

Evidence:
- `docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_green_v20_review_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_red_v21_codex_v1.md`

FREEZE PROTOCOL: I will make NO further edits to the RED until you return the complete
v21 gate with RED/GREEN hashes verified before and after strict module, tracked suite,
Ruff, compile, diff check, and real-store byte-copy probe. Reproduce 24F/578P before
editing. If you contest a contract, stop before GREEN and name it.

No commit/push/capture/provider/scheduler/Phase B-C-D. H2 remains UNDER TEST.
