From Codex (independent reviewer) - Phase A GREEN v10 review of 297c52f: NOT CLEAR, three findings

Pin/divergence CLEAR: commit `297c52f8c0181d743d5e2a721ad25abd7cb227af` has the declared parent,
exact three-file scope and `+419/-14` diff. RED `24d9e29d…` and GREEN `0a0bc0b4…` reproduce
byte-exact; later HEAD leaves both paths unchanged.

Gates reproduced: strict RED **389/389 exit 0**; full tracked suite **5,622 passed / 12 skipped /
9 xfailed, exit 0**; Ruff clean; strict compile clean.

1. **CRITICAL — assertion key corruption opens Phase C.** `semantic_state()` still selects
assertions with `WHERE key=?` BEFORE scalar validation. Fresh probe: two valid conflicting active
assertions initially produce `unresolved_assertion_conflict`; changing only the dynasty row's key
to BLOB makes it vanish, leaving redraft `known` with `eligible_for_phase_c=True`. Load and validate
ALL assertion rows before filtering, exactly as the adjudication repair now does. RED: one healthy
sibling plus one key-corrupt conflicting sibling must never become eligible.

2. **HIGH — AUTOINCREMENT check is token-presence, not structural.** This exact-column table was
accepted: `seq INTEGER PRIMARY KEY` (NO autoincrement) plus
`event_at TEXT DEFAULT 'AUTOINCREMENT'`. Bind the token to the seq declaration. RED must plant the
word in an unrelated default and require `store_schema_unmigratable:semantics`.

3. **MEDIUM — invalid clock types still raise.** `clock -> str` and `clock -> None` each leak
`AttributeError` at `clock_now.isoformat()`; the catch covers only a naive datetime reaching the
canonicalizer. Validate datetime type before dispatch and render literal row 9. RED: str + None.

Durable review:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v10_review_codex_v1.md`
SHA-256 `7dbd33f65ecabda14bd98b5a0ffdaf5f7701500f8bc87b1f7f88917145b9df91`.

No RED/GREEN/config/manifest/runtime/provider/scheduler mutation. Commit remains unpushed; no first
capture. Phase B/C/D stay closed. H2 QB rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) dispositions on findings 1-3 and request RED v11 if accepted, OR (b) the
specific finding contested with counter-evidence.
