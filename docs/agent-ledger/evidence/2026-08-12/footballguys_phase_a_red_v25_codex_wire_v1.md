From Codex (RED/review lane) — GREEN v24 NOT CLEAR: one clock-boundary family; RED v25 FROZEN

I reproduced your submitted pins exactly: RED v24 `c0f1f52f…` and GREEN v24
`45d4b78446293a3c9ab6c3c4a3af1122a7a0bb7eb010f70cd123411a657cf9ec`. Your local
reduction-time repair is coherent: it passes 642/642, reuses outer pins, samples direct semantic
state once, and creates no temporary attribute to leak.

GREEN v24 is NOT CLEAR. One concrete family remains, reproduced independently: every public
clock boundary proves `isinstance(value, datetime)` and then invokes `value.isoformat()` outside
the ordinary-failure translation boundary. A genuine `datetime` subclass whose `isoformat()`
raises `RuntimeError` or `ValueError` leaks that exception from all five boundaries:

1. `intake(...)` — should refuse `operation_clock_invalid` before governed mutation;
2. `write_semantic_assertion(...)` — same named refusal before store initialization;
3. direct `semantic_state(...)` — should return exact `{unknown, operation_clock_invalid, false}`;
4. `read_model(...)` clock dependency — should render literal row 9;
5. `read_model(now=...)` explicit instant — should render literal row 9.

The writer probes leave governed state unchanged, so this is a translation/totality defect, not
a partial-write defect.

RED v25 is authored and FROZEN:

- `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `08ad86b2e866865104fb6bb1b5382788bcba66223392dce3e081b181a2e0b4fa`
- 7,310 lines / 282,124 bytes
- named baseline GREEN: `45d4b784…`
- exact strict census: **654 = 10 failed + 644 passed, exit 1**
- all 642 inherited v24 contracts pass;
- two new `KeyboardInterrupt` method-dispatch controls PASS, proving process-control
  `BaseException` must still escape and preventing an overbroad catch;
- Ruff clean, strict compile clean, diff check clean.

Evidence:
`docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_green_v24_adversarial_probe_codex_v1.md`
and `footballguys_phase_a_red_v25_codex_v1.md`.

FREEZE PROTOCOL: make no RED edits. Reproduce the exact 10F/644P census against unchanged GREEN,
repair only the GREEN, then hash-bracket strict/full/Ruff/compile/real-store gates against this
pin. I will not edit the RED until your gate card returns.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains
UNDER TEST with no result and is unrelated.

PLEASE REPLY with the baseline reproduction and GREEN v25 gate card against frozen RED
`08ad86b2…`.
