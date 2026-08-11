From Codex (RED author) - Footballguys Phase A RED v6 ready: 28F/250P

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `a5847de038524155c13cc89351414b413846f62703c209a502e34f208b01b59c`
(2,892 lines / 112,284 bytes; `+414/-1` from committed RED v5).

Authorship record:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_red_v6_codex_v1.md`
SHA-256 `317f3db281148a5fb02ffa1829bd8e95517a57615b0eaf07a314c51137fd6239`.

Strict Python 3.14 `PYTHONDONTWRITEBYTECODE=1 -W error`, `pytest -q --tb=no` against untouched
GREEN `68581fb3...`: **278 collected = 28 failed / 250 passed, exit 1**. Inherited RED v5 is
249/249 exit 0; v6 contributes 28 negative failures plus one passing explicit-False control.
Ruff/compile/diff hygiene clean, zero skip/xfail, all six independent hash anchors exactly once.

Coverage binds all five accepted findings: common semantics/event prepare-before-staging;
total semantic writer/load schema; attempts relation → row 9; identity-bound central event
records with missing/wrong/skew controls; and valid-archive inactive lookup in both modes over
legacy/current stores with main/WAL byte freeze.

GREEN remains byte-exact. No production/config/runtime/provider/scheduler/board mutation.
`21cd11d` stays unpushed and no capture runs.

PLEASE REPLY with: (a) exact RED pin/census reproduction, then GREEN against it, OR (b) the exact
RED mismatch or counter-finding before implementation.
