# CFBD FBS schedules RED v4 — independent CLEAR

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **CLEAR**

## Cleared pin and checks

- `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 1,465 lines:
  `8eb194c5dddc78275dfe4f3aed728e8a6603083909be4a37063ebf63c86b1d97`
- Pin independently recomputed and matched.
- Focused RED independently reproduced: **171 failed / 1 disclosed pass** in 2.12s, true exit 1,
  zero setup or collection errors. Failures are the intentional absent-module/CLI RED state.
- `uvx ruff check`: **clean**.
- Read the complete revised contract and the v4 disposition. F1-F7 and residuals R1-R2 are fully
  disposed.

## Review disposition

- Exact raw JSON bytes and the logical schema are correctly separated; JSON member order is not
  treated as schema.
- The accepted top-level and nested shape is pinned to CFBD OpenAPI v5.21.0, including enum,
  integer, finite-number, line-score, and `GamePlayoff` behavior.
- Response scope is FBS games from the normal `regular|postseason` offering; FBS-vs-non-FBS remains
  valid and all-non-FBS is refused.
- Duplicate member names are detected at Game and nested-object depth before Python can silently
  overwrite a value.
- A paid identical reacquisition creates another accounted check but not another content vintage;
  local replay is a distinct zero-call, zero-mutation operation.
- Remaining-quota telemetry is nullable; actual local attempts are always recorded.
- Production HTTP transport, credential scrubbing, CLI failure surfaces, rollback, corrupt-address
  reuse, quarantine, failed audits, containment, and backup coverage are all contracted.

## Verdict

**CLEAR** on pin `8eb194c5…`. GREEN implementation may begin. The live paid request remains after
GREEN review, not before it.

