# Footballguys Phase A RED v24 — Codex v1

Date: 2026-08-12  
Layer: 1 — governed semantic evidence read boundary  
Authority: David's standing instruction to work with Claude until this is production-grade  
Framing source: `footballguys_phase_a_intake_notice_framing_claude_v25.md`

## Pins and census

- RED: `tests/contract/test_footballguys_phase_a_red.py`
- RED SHA-256: `c0f1f52fb9481c98fe7fe38a68b8949f790cb9c202b834155879650208f334ad`
- RED size: 7,157 lines / 275,572 bytes
- Baseline GREEN: `src/dynasty_genius/sources/footballguys_intake.py`
- GREEN SHA-256: `e714f81fdbd30a7ea091e21d690b87c66273dd5ebc782d336d281bf1aaac866a`

Strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q -W error --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result: **642 collected = 9 failed + 633 passed, exit 1**.

- All **632 inherited v23 contracts pass**.
- V24 contributes **9 failing controls + 1 passing positive anchor**.
- Ruff, strict Python 3.14 compile, and `git diff --check`: clean.

## Finding — direct semantic-state reads have no validated time basis

The v22/v23 write and `read_model` repairs do not govern the public direct
`semantic_state(key=...)` seam. That method samples `_now()` independently once per attachment.
Consequences reproduced:

- clocks raising `RuntimeError` or `ValueError` leak bare exceptions;
- `None` and fractional clocks can return a Phase-C-eligible known state;
- text, integer, and naive clocks are misclassified as `active_evidence_unverifiable`, hiding the
  actual broken dependency;
- a restored 2099 attachment becomes Phase-C eligible when `None` disables the future check;
- two attachments cause two clock samples, so one reduction can span different instants or fail
  on its second sample.

V24 binds:

- ordinary dependency failures and all five v22 invalid-value classes to exact state
  `{state: unknown, reason: operation_clock_invalid, eligible_for_phase_c: false}`;
- no semantic table mutation on refusal;
- restored future evidence remains ineligible under an invalid clock;
- a direct multi-attachment reduction samples and validates exactly one clock;
- `read_model` reuses its already-pinned read clock when it enters `semantic_state`, proven with
  governed semantic evidence and an acquisition (one total clock call).

The intended implementation owns a temporary semantic-read pin only when neither a read-model nor
write-operation pin already exists, and clears it on every exit. It does not catch process-control
`BaseException` classes.

## Scope and freeze

This RED opens no landing, commit, push, capture, provider contact, scheduler, or Phase B/C/D.
The pin is frozen pending Claude's attributable baseline and complete GREEN gate. H2 QB rushing
remains **UNDER TEST** and unrelated.
