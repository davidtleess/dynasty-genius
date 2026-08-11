From Codex (RED-authoring lane) - Footballguys Phase A RED v13 authored; 2F/413P against unchanged GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `b40126f39c4eeae0dc481b4b2a7ae07b51052f021973b3b2c9b802027e5c898b`
4,606 lines / 179,509 bytes.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v13_codex_v1.md`
SHA-256 `91533559c0434e655da353dcaf5dcdc60f132b7a1512206bc51d8ccd38451abb`.

Baseline GREEN remains byte-exact at
`e6cd167d2e33b15e63e1b7dfc23d0e6229c8889cbddba3f17f8f72d3ee6f8d28`.

Exact strict command, reproduced twice:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`

**415 collected = 2 failed + 413 passed, exit 1.** Both suffix negatives fail. The canonical
positive and all inherited 412 controls pass. No skip/xfail decorators; Ruff clean; strict compile
clean; `git diff --check` clean.

The control binds complete exact seq grammar with `CHECK(seq > 100)` and redundant `UNIQUE`
negatives, preventing a consequence-specific special case.

Nothing committed or pushed; no capture, provider contact, scheduler, or Phase B/C/D opens. H2 QB
rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) exact RED v13 reproduction and GREEN repair status, OR (b) any census or
contract mismatch.
