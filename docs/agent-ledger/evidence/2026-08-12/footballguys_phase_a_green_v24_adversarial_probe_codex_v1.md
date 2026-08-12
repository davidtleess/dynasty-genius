# Footballguys Phase A GREEN v24 adversarial probe — Codex v1

Date: 2026-08-12  
Layer: 1 — source intake and governed persistence  
Reviewed GREEN: `src/dynasty_genius/sources/footballguys_intake.py`  
GREEN SHA-256: `45d4b78446293a3c9ab6c3c4a3af1122a7a0bb7eb010f70cd123411a657cf9ec`  
Reviewed RED v24 SHA-256: `c0f1f52fb9481c98fe7fe38a68b8949f790cb9c202b834155879650208f334ad`

## Verdict

NOT CLEAR. One concrete fail-closed clock-boundary defect remains.

## Finding C1 — datetime method dispatch leaks after the type guard

Every public clock boundary first proves `isinstance(value, datetime)` and then calls
`value.isoformat()` outside the ordinary-failure translation boundary. A real subclass of
`datetime` can therefore pass the type guard and raise from `isoformat()`.

Measured with a `datetime` subclass whose `isoformat()` raises `RuntimeError`:

- `intake(...)` leaked `RuntimeError` instead of `operation_clock_invalid`;
- `write_semantic_assertion(...)` leaked `RuntimeError` instead of
  `operation_clock_invalid`;
- direct `semantic_state(...)` leaked `RuntimeError` instead of returning the exact
  `{unknown, operation_clock_invalid, False}` state;
- `read_model(...)` leaked `RuntimeError` both when the clock dependency supplied the
  subclass and when the explicit `now` argument supplied it.

The writer probes left governed state unchanged, so this is a translation/totality defect,
not a partial-write defect. The same probes with `ValueError` reproduce the leak.

## Required boundary

The complete validation operation — type check, method dispatch, and canonical validation —
must translate ordinary `Exception` subclasses through the existing named failure for each
public boundary. `KeyboardInterrupt`/`SystemExit` and other process-control `BaseException`
classes must continue to pass through.

## Scope

No commit, push, capture, provider contact, scheduler, or Phase B/C/D action is opened. QB
rushing H2 remains UNDER TEST with no result and is unrelated.
