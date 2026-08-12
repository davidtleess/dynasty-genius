From Codex (RED-authoring lane) — Phase A RED v16 AUTHORED: exact index signatures + marker grammar

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256: `0c4199a888240850496283e90ea4d3b2b308fc6a4d5a60d20e31142c7b688e6d`
Size: 5,052 lines / 196,973 bytes.

Against unchanged GREEN `7dc64bf502b2a260ea3c4c050ad93b6fd5bf45c50f67720114dadfffdf0d4103`,
the exact strict command reproduced twice:

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`

**446 collected = 11 failed + 435 passed, exit 1.**

Failure partition:
- H1: four surplus SQLite autoindexes — `UNIQUE(claim)`, `UNIQUE(provenance)`,
  `UNIQUE(evidence_blob)`, and `UNIQUE(authority)` — across all four non-grammar semantic
  tables. Existing v14/v15 controls already close `event_sequence` grammar and surplus indexes.
- H2: seven malformed `acquisitions` marker schemas — missing/extra/wrong-order columns,
  missing PK, missing UNIQUE, surplus UNIQUE/autoindex, and a column-definition suffix.
- Both new canonical controls pass.

Every negative starts with populated application evidence, requires the exact named
`store_schema_unmigratable:semantics` refusal, freezes main/WAL size+SHA, and preserves all
application rows. No skip/xfail. Ruff and strict compile are clean; `git diff --check` is clean.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v16_codex_v1.md`
SHA-256: `d8b50bb4d8eaddebed9743eb251a2a1ebec6da70b8d30ae9b64257677183c695`

PLEASE REPRODUCE the exact strict census against the unchanged GREEN before repair, then GREEN
against this pin. The pair lands only on David's word. No commit/push/capture/provider/scheduler/
Phase B-C-D opens here. H2 QB rushing remains UNDER TEST with no result and is unrelated.
