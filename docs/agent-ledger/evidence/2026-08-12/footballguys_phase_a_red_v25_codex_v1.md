# Footballguys Phase A RED v25 — Codex v1

Date: 2026-08-12  
Layer: 1 — source intake and governed persistence  
Test artifact: `tests/contract/test_footballguys_phase_a_red.py`  
Frozen RED SHA-256: `08ad86b2e866865104fb6bb1b5382788bcba66223392dce3e081b181a2e0b4fa`  
Size: 7,310 lines / 282,124 bytes  
Baseline GREEN SHA-256: `45d4b78446293a3c9ab6c3c4a3af1122a7a0bb7eb010f70cd123411a657cf9ec`

## Binding delta

RED v25 binds the GREEN-v24 finding that a datetime object may pass the `isinstance` guard
and still fail during validation method dispatch. It covers five public boundaries with both
`RuntimeError` and `ValueError`:

1. intake operation clock;
2. semantic assertion writer clock;
3. direct semantic-state clock;
4. read-model clock dependency;
5. read-model explicit `now` dependency.

Writer boundaries require the existing named `operation_clock_invalid` refusal before any
governed write. Read boundaries require their exact existing fail-closed states and no
filesystem or semantic-row mutation. Two positive controls require `KeyboardInterrupt` from
the same method-dispatch point to pass through, preventing an overbroad `BaseException` catch.

## Measured baseline census

Exact strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --tb=no -W error tests/contract/test_footballguys_phase_a_red.py
```

Result against unchanged GREEN v24:

- 654 collected;
- 10 failed — exactly the ordinary method-dispatch controls;
- 644 passed — all 642 inherited v24 contracts plus the two process-control positives;
- process exit 1.

Additional gates: focused v25 census `10 failed / 2 passed`; Ruff clean; strict compile clean;
`git diff --check` clean.

## Adequacy

- A repair that catches only failures from calling `self.clock()` still fails all ten new
  ordinary controls.
- A repair that catches `BaseException` passes those ten but fails the two process-control
  positives.
- A repair that covers only `_observe_operation_clock` still fails the two read-model families.
- A repair that covers only the clock dependency still fails the explicit-`now` family.

## Freeze and scope

This SHA is frozen for the implementing lane. Do not edit the RED until the GREEN census is
returned and reviewed. No commit, push, capture, provider contact, scheduler, or Phase B/C/D
action is authorized. QB rushing H2 remains UNDER TEST with no result and is unrelated.
