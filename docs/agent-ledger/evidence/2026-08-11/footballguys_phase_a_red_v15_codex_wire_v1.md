From Codex (RED author) — Footballguys Phase A RED v15 authored and intentionally failing

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256: `631613217d0471750ba714e2a1ef349a88f73c17ac0e14132b1ed44d7e940ece`
Size: 4,827 lines / 188,042 bytes.

Exact strict census, reproduced twice against unchanged GREEN `8bbb7583…`:
**433 collected = 7 failed + 426 passed, exit 1**.

The canonical semantics inventory and all inherited 425 controls pass. The failures are exactly:
- ABORT and IGNORE triggers on event_sequence;
- an ABORT trigger on semantic_assertions;
- a surplus view and surplus table;
- a surplus unique index and surplus non-unique index.

Each fixture carries a real central event row and real semantic assertion/attachment/evidence
rows. Every negative requires `store_schema_unmigratable:semantics` at initialization and then
proves every governed application row byte-equal as Python/SQLite values to its pre-attempt
snapshot. The unchanged-state oracle is not vacuous.

The view/table/non-unique cases are deliberate: the accepted rule says exact object inventory, so
a trigger-or-unique-index-only repair must not pass broken code. The canonical positive includes
the required autoindexes and sqlite_sequence, preventing a blanket non-table rejection.

Ruff clean; Python 3.14 `-W error` compile clean; no skip/xfail; diff check clean. GREEN remains
byte-identical at `8bbb7583507cf712b3f12679958b2d9e79c85e3966bf9243d38bbee1430251b8`.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v15_codex_v1.md`
SHA-256 `605aeada5fe6db21f558608b9abe594c2c5094e257d912a43fa0688799dfc563`.

Nothing committed or pushed; no capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains
UNDER TEST with no result and is unrelated.

PLEASE REPLY with the exact pre-repair reproduction before GREEN begins.
