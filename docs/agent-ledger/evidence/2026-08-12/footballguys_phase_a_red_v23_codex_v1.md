# Footballguys Phase A RED v23 — Codex v1

Date: 2026-08-12  
Layer: 1 — governed ingest and persistence  
Authority: David's standing instruction to work with Claude until this is production-grade  
Framing source: `footballguys_phase_a_intake_notice_framing_claude_v25.md`

## Pins

- RED: `tests/contract/test_footballguys_phase_a_red.py`
- RED SHA-256: `9f97d47468d8f9f8387e93ee2d58b7c6562e7adcf49dd53e6c458a4c7a3c1172`
- RED size: 7,027 lines / 270,814 bytes
- Baseline GREEN: `src/dynasty_genius/sources/footballguys_intake.py`
- GREEN SHA-256: `b0bf23acc3a2ecbcd2ef42ce515c52ef6a9d5e57602b19af7f56f73262cc54cb`

Both pins were measured immediately before the strict run and remained byte-equal after it.

## Strict failing census

Command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q -W error --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result: **632 collected = 8 failed + 624 passed, exit 1**.

- All **623 inherited v22 contracts pass**.
- V23 contributes **8 failing controls + 1 passing positive anchor**.
- Ruff: clean.
- Strict Python 3.14 compile: clean.
- `git diff --check`: clean.
- Focused v23 census: 8 failed + 1 passed.

## Finding 1 — corrupt orphan content-address reuse reports `written`

The v22 repair verifies an evidence identity only when an attachment or assertion already
references it. A content-addressed object is a separate deduplication identity. If a corrupt
or NULL object row already exists under the incoming evidence SHA without an attachment, the
writer's `INSERT OR IGNORE` silently reuses it, returns `written`, and the immediately loaded
semantic state is `active_evidence_unverifiable`.

V23 binds:

- NULL and wrong-byte orphan objects under the correct incoming SHA;
- exact refusal `semantic_evidence_unverifiable:evidence-horizon-v1`;
- all semantic tables byte/logically unchanged from the corrupt pre-call state;
- no active assertion appears after refusal;
- an exact-byte healthy orphan is reused successfully, leaves one object row, and produces a
  Phase-C-eligible governed assertion.

## Finding 2 — clock dependency failures leak bare exceptions

The v22 repair validates returned clock values but does not translate a failing dependency.
Injected clocks raising `RuntimeError` or `ValueError` escape all three public boundaries:
intake, semantic assertion write, and read model.

V23 binds:

- both exception classes on each public boundary;
- write paths translate them to exact `operation_clock_invalid`;
- write refusal leaves no governed database, sidecar, or raw object (private namespace/lock is
  allowed for intake);
- the read model renders the exact literal record-unreadable row, creates no filesystem state,
  and never leaks the dependency exception.

The contract catches ordinary `Exception`, not process-control `BaseException` classes.

## Scope and freeze

This RED opened no landing, commit, push, capture, provider contact, scheduler, or Phase B/C/D.
Claude reproduced 8F/624P, then GREEN `e714f81f…` passed 632/632. Its full tracked suite reported
5,865 passes with only the 15 standing untracked cadence-RED failures; Ruff, strict compile, diff
check, and the real-store byte-copy probe were clean. V23 is contract-CLEAR, not
production-clear: direct `semantic_state` clock defects are now bound by RED v24. H2 QB rushing
remains **UNDER TEST** and unrelated.
