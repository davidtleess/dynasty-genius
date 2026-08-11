From Codex (RED-authoring lane) - Footballguys Phase A RED v12 authored; 5F/407P against unchanged GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `7b26b0fc3788dd799e670b2b2b4e66ae429d9057659b173a44267c8910a1e287`
4,556 lines / 177,389 bytes.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v12_codex_v1.md`
SHA-256 `8c9193860c62d183c85afc42f93ecbe0693a627b68ec0db4d9a79302c8f79898`.

Baseline GREEN remains byte-exact at
`07a1420530f2cedabec6ddef2b9cd7f77b78841a69bb04335f3111124841b6f8`.

Exact strict command, reproduced twice:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`

**412 collected = 5 failed + 407 passed, exit 1.** Breakdown: H1 3, M2 2. Every inherited
405 control and both new signed-64 legal-boundary anchors remain green. No skip/xfail decorators;
Ruff clean; strict compile clean; `git diff --check` clean.

H1 independently binds single-quoted literal, block-comment and line-comment decoys containing the
full expected seq phrase. M2 binds both overflow directions plus exact min/max passing anchors and
fresh-root main/WAL/SHM absence.

Nothing committed or pushed; no capture, provider contact, scheduler, or Phase B/C/D opens. H2 QB
rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) exact RED v12 reproduction and GREEN repair status, OR (b) any census or
contract mismatch.
