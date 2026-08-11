From Codex (RED-authoring lane) - Footballguys Phase A RED v10 authored; 18F/371P against unchanged GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `24d9e29d00e20768c687e748105c264cab8477929c7707bf370256835ba549ba`
4,285 lines / 166,834 bytes.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v10_codex_v1.md`
SHA-256 `1aadbbd6381517ff0c82c5be6affc36b0d35a28632471eb430938ff8c8957173`.

Baseline GREEN remains byte-exact at
`0f963e7371dc3b89e97de5f6b9f09e2c6d257f7c5c88155c87d8cf27cf134933`.

Strict command, reproduced twice against that unchanged GREEN:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`

**389 collected = 18 failed + 371 passed, exit 1.** Breakdown: C1 7, H2 6, H3 1,
H4 2, H5 2. Every inherited control remains green. No skip/xfail decorators; Ruff clean;
cold strict compile clean; `git diff --check` clean.

The new REDs bind the five accepted boundaries: exact semantic load scalar types; whole central
sequence schema plus duplicate/nonpositive/non-monotonic load checks; attempt exact-int branch
symmetry; one validated read clock with named fail-closed behavior; and fresh-root physical
absence for invalid calls to both semantic writers.

The pair lands only after repair, review, and David's separate word. Nothing committed or pushed;
no capture, provider contact, scheduler, or Phase B/C/D opens. H2 QB rushing remains UNDER TEST
with no result and is unrelated.

PLEASE REPLY with: (a) exact RED v10 reproduction and GREEN repair status, OR (b) any census or
contract mismatch.
