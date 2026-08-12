# Footballguys Phase A GREEN v22 — adversarial probe record

Date: 2026-08-12  
Layer: 1 — governed ingest and persistence  
Authority: David's standing instruction to work with Claude until this is production-grade

## Pins under review

- Final frozen RED v22: `c06ff1065a26dee8faabbb33e995a88844ea9b17c7b6a97f8ccab353736f2bd4`
- Held GREEN v22: `b0bf23acc3a2ecbcd2ef42ce515c52ef6a9d5e57602b19af7f56f73262cc54cb`
- Strict coherence control: 623 passed, exit 0.

The complete hash-bracketed gate remains Claude's active work. These probes are independent of
that census and make no landing claim.

## Critical 1 — corrupt orphan evidence object still yields `written`

Setup:

1. Initialize the governed semantics store.
2. Insert an unreferenced `semantic_evidence_objects` row under the SHA-256 of the incoming
   provider-authentic evidence, but with corrupt bytes.
3. Submit a new assertion and attachment using a new evidence identity and those authentic
   incoming bytes.

Observed result:

```text
writer result = {"status": "written"}
loaded state = {"state": "unknown", "reason": "active_evidence_unverifiable",
                "eligible_for_phase_c": false}
```

Cause: the new verification branch runs only when the incoming *evidence identity* is already
referenced by an attachment or assertion. The content-addressed object identity is a separate
deduplication edge. `INSERT OR IGNORE` silently reuses a pre-existing corrupt object row without
verifying its bytes, then the writer reports success over evidence the reducer immediately
rejects.

Required boundary: before reusing an existing content-addressed evidence object, descriptor/row
bytes must verify against the incoming SHA and bytes. Corrupt or missing existing content must
refuse by the named semantic-evidence code with all semantic rows unchanged. A pre-existing
healthy orphan object with exact bytes remains a positive reuse case.

## High 2 — a failing clock dependency leaks bare exceptions

Injected `clock` callables that raise `RuntimeError("clock down")` were exercised at each public
clocked boundary.

Observed:

- `intake(...)` raises bare `RuntimeError`; only the permitted private namespace/lock exists.
- `write_semantic_assertion(...)` raises bare `RuntimeError`; no governed store exists.
- `read_model(...)` raises bare `RuntimeError` instead of literal row 9.

The v22 wrong-type/time-shape controls do not exercise dependency failure. A clock dependency
failure is not a domain result and must fail closed through the same named public state as an
invalid clock value: `operation_clock_invalid` for writes and the literal record-unreadable row
for the read model. No governed data may be created or advanced.

## Scope

No RED was edited while Claude's final v22 gate was running. These findings are candidates for
the next RED only after that frozen gate returns. No commit, push, capture, provider contact,
scheduler, or Phase B/C/D is opened. H2 QB rushing remains **UNDER TEST** and unrelated.
