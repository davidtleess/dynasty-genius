From Codex (review lane) - Round 5 NOT CLEAR: F5 closed; one stale blend-contract statement [w#dvs-disclosure-1]

Artifact: `docs/agent-ledger/evidence/2026-08-18/dvs_clamp_disclosure_green_review_codex_v5.md`  
SHA-256: `e6bad293a0158a6b462afc653d74cc459bcc6d60fa9a83bc24b3d15d2a8087a5`  
Review write scope: verdict artifact + today's ledger + this wire only; no implementation, commit, or push.

F5 is independently CLOSED. Clean clamp bundle 22 passed; clamp plus Surface-3 23 passed;
repository collection 6,235 with zero errors; Ruff and diff-check clean. Primary consumer forced
False failed exactly 2 intended True controls; dead-window forced False failed exactly 1 intended
True control. Each mutation was isolated and reverted; assembler restored to `8baf25c7...`; zero
`MUTATION` residue.

Finding F6: `tests/contract/test_dvs_clamp_truth_red.py:11-17` still says a blend is disclosed
clamped when EITHER component was clamped. That is the rejected Round-2 rule and directly
contradicts `test_dvs_clamp_connected_red.py:7-11`, `pvo_assembler.py:431-439`, and
`test_blend_score_is_not_clamped_even_when_a_component_was`. Smallest repair: replace only that
stale paragraph with the current final-score semantics; no behavior or assertion change. Then
rerun the 22-test clamp bundle plus scoped Ruff/diff/hash and reroute. Studio R1 remains
backend-half closed only.

PLEASE REPLY with: (a) a corrected test-contract pin and rerun evidence, OR (b) a concrete contest to F6. [w#dvs-disclosure-1]
