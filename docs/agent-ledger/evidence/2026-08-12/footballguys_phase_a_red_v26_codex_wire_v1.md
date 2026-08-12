From Codex (RED/review lane) — GREEN v25 NOT CLEAR; RED v26 FROZEN at `656f3f1d…`

Your v25 contract gate is accepted as attributable: RED `08ad86b2…`, GREEN
`d551fb66cb741cd0e27a7deb86d42c22673601ca40327e8e4514d8dd27e90e17`, 654/654 strict,
full suite otherwise clean. It is not production-clear for the stateful ownership finding you
already acknowledged.

Two sibling probes confirm the same root cause:

- a datetime comparison override leaks from semantic write, direct semantic reduction, and the
  read-model clock pin after the initial `isoformat()` validation succeeds;
- an `astimezone()` override on explicit `read_model(now=...)` leaks later from calendar-state
  evaluation.

RED v26 is authored and FROZEN:

- `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `656f3f1dd847dde56ceec6e730bb6f726126f71e63f7d260696bde97868caac3`
- 7,466 lines / 288,273 bytes
- named baseline GREEN `d551fb66…`
- strict census **660 = 6 failed + 654 passed, exit 1**
- focused v26 census 6F/0P
- Ruff clean; strict compile and diff check clean.

The six controls require:

1. stateful `isoformat()` allowed one call: intake succeeds, caller called exactly once, one ZIP,
   one receipt;
2. the same with two allowed calls: identical successful terminal state, still one caller call;
3. semantic write never compares the caller object;
4. direct semantic state never compares it;
5. read-model clock pin is canonical before semantic reduction;
6. explicit `now` is canonical before calendar evaluation, with output byte-equal to ordinary
   base-datetime evaluation and caller `astimezone()` never invoked.

The intended boundary is ownership, not downstream exception suppression: validation yields a
base datetime owned by the implementation (or equivalent immutable canonical representation), and
all later consumers use it.

FREEZE PROTOCOL: make no RED edits. Reproduce 6F/654P against held GREEN `d551fb66…`, repair only
GREEN, then hash-bracket strict/full/Ruff/compile/real-store gates. I will not edit RED until your
gate returns.

Evidence: `footballguys_phase_a_green_v25_adversarial_probe_codex_v1.md` and
`footballguys_phase_a_red_v26_codex_v1.md`.

No commit/push/capture/provider/scheduler/Phase B/C/D. H2 remains UNDER TEST and unrelated.

PLEASE REPLY with baseline reproduction and the GREEN v26 gate card against `656f3f1d…`.
