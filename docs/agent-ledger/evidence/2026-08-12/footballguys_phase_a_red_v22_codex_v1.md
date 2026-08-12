# Footballguys Phase A RED v22 — Codex v1

Date: 2026-08-12  
Layer: 1 — governed ingest and persistence  
Authority: David's standing instruction to work with Claude until this is production-grade  
Framing source: `footballguys_phase_a_intake_notice_framing_claude_v25.md`

## Pins

- RED: `tests/contract/test_footballguys_phase_a_red.py`
- RED SHA-256: `c06ff1065a26dee8faabbb33e995a88844ea9b17c7b6a97f8ccab353736f2bd4`
- RED size: 6,885 lines / 265,254 bytes
- Baseline GREEN: `src/dynasty_genius/sources/footballguys_intake.py`
- GREEN SHA-256: `a0e7793b58b79e90a98371ede3ac2dd164e3504dd36b447a0244a7a0f97a832f`

The first freeze `b8fe72ba…` was withdrawn after both lanes proved one inherited exact-code
assertion contradicted the new public boundary. The inherited assertion was narrowed to its real
fail-closed purpose: it accepts its historical internal `event_at_invalid:*` code or the new
public `operation_clock_invalid`, while the v22 controls bind the latter exactly. Claude restored
the baseline GREEN byte-for-byte and measured the final pin. Both hashes were verified before and
after that strict run and were byte-equal.

## Strict failing census

Command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q -W error --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result: **623 collected = 19 failed + 604 passed, exit 1**.

- All **602 inherited v21 contracts pass**.
- V22 contributes **19 failing controls + 2 passing positive anchors**.
- Ruff: clean.
- Strict Python 3.14 compile: clean.
- `git diff --check`: clean.
- Skip/xfail/skipif scan: zero occurrences.

## Finding 1 — success-shaped semantic writes over unverifiable evidence

The stable v21 GREEN reports `noop` for an identical assertion when its attachment is missing,
its evidence object is missing, or its evidence bytes no longer match their content address. A
new assertion reusing that evidence identity reports `written` under the same three corruptions.
The reducer correctly returns `active_evidence_unverifiable`; the writer therefore contradicts
the state it just declared successful.

V22 binds:

- attachment missing, evidence object missing, and evidence bytes corrupt;
- identical replay and new-assertion evidence-identity reuse as separate branches;
- exact named refusal `semantic_evidence_unverifiable:<evidence_id>`;
- zero logical mutation from the corrupt pre-call state;
- the corrupt active evidence remains fail-closed in the reducer;
- a fully verified identical replay remains an idempotent `noop` and byte/logically unchanged.

## Finding 2 — write-operation clock is not validated or pinned

The stable v21 GREEN consults the intake clock repeatedly after store initialization and staging.
Wrong-type clocks leak bare exceptions after governed state is created; a valid first value and
invalid later value can publish the paid ZIP and fail before its receipt. The semantic writer
accepts `None` as `now=None`, which disables future-time validation and can make a 2099 evidence
attachment Phase-C eligible.

V22 binds:

- `None`, text, integer, naive datetime, and fractional datetime for both intake and semantic
  assertion writes;
- exact named refusal `operation_clock_invalid`;
- no receipts/semantics/observations database or sidecar and no raw object on invalid-clock
  refusal (the private lock/namespace may exist);
- explicit 2099 semantic evidence with a `None` clock cannot bypass the future guard;
- one valid first clock followed by invalid values must still complete a valid intake with exactly
  one clock observation;
- the same one-call rule covers the malformed-archive attempt-record path;
- a normal semantic write observes the clock exactly once.

## Falsification matrix

| Input class | Evidence |
|---|---|
| valid nominal | verified replay remains `noop`; normal semantic clock observed once |
| boundary | aware fractional clock refuses; whole-second aware clock is the positive |
| missing/null | attachment row absent; object row absent; `None` clock |
| wrong type | text and integer clocks on both public write paths |
| malformed shape | corrupt retained evidence bytes; malformed archive attempt path |
| duplicate/conflict | evidence identity reused by a distinct assertion |
| empty collection | governed databases and objects remain absent/empty after clock refusal |
| cross-component | writer success result is checked against reducer state and retained-object tables |
| numeric/time edge | future 2099 evidence; fractional instant; naive datetime |
| synthetic/override | counted and changing injected clocks |

## Scope and freeze

This RED opened no GREEN landing, commit, push, capture, provider contact, scheduler, or Phase
B/C/D. Claude returned the complete hash-bracketed gate: GREEN `b0bf23ac…` passes 623/623; full
tracked suite has 5,856 passes with only the 15 standing untracked cadence-RED failures; Ruff,
strict compile, diff check, and the real-store byte-copy probe are clean. V22 is therefore
contract-CLEAR, not production-clear: subsequent adversarial probes found two new defects now
bound by RED v23. H2 QB rushing remains **UNDER TEST** and unrelated.
