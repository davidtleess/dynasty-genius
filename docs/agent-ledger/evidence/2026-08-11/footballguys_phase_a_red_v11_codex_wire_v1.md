From Codex (RED-authoring lane) - Footballguys Phase A RED v11 authored; 12F/393P against unchanged GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `f578b32af1f9f709fd854a7c00c203013d1feb3db80eb0b0a3630b0227b0d210`
4,446 lines / 173,110 bytes.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v11_codex_v1.md`
SHA-256 `cbde90d5dbf7bbfcf77c2827002423af4a8c66e9f9a66a49fd51eddb407ff761`.

Baseline GREEN remains byte-exact at
`0a0bc0b439b744ff90a023adfa0fce1e1cdfdc1a38cabc37fec0f2353fd6f118`.

Exact strict command, reproduced twice:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`

**405 collected = 12 failed + 393 passed, exit 1.** Breakdown: C1 8, H2 1, M3 3.
Every inherited 389 control remains green; four new scalar anchors also pass. No skip/xfail
decorators; Ruff clean; strict compile clean; `git diff --check` clean.

C1 is deliberately broader than the single exploit: the active conflicting-key fixture binds the
Phase-C laundering failure, while an inactive-row matrix validates every assertion writer scalar
table-wide before active/key projection. H2 plants AUTOINCREMENT only in an unrelated DEFAULT.
M3 covers str, None and integer clock dependencies before method dispatch.

Nothing committed or pushed; no capture, provider contact, scheduler, or Phase B/C/D opens. H2 QB
rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) exact RED v11 reproduction and GREEN repair status, OR (b) any census or
contract mismatch.
