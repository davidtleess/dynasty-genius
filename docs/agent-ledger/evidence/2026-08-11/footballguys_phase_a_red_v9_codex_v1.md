# Footballguys Phase A RED v9 — Codex v1

**Date:** 2026-08-11 ET  
**Authority:** implementing lane accepted all five adversarial findings against committed GREEN
`7e39763afcf8449545f7ca6878c5f2d8d942276d` and requested Codex-authored RED v9.  
**RED path:** `tests/contract/test_footballguys_phase_a_red.py`  
**RED SHA-256:** `54eccc7326cba73d2e6d662c16b239387344dfcd0a3b1e170bc38ebaecf79332`  
**Size:** 3,973 lines / 155,087 bytes  
**Baseline GREEN:** `241d031dc4e36ee3f54500df8d6e9ad2bcd9fb208bdc5f062d0fc4b6c7ad8f4c`

## Scope

RED v9 extends the inherited 340-contract Phase A suite. It changes no GREEN, configuration,
manifest, runtime store, provider state, scheduler, or downstream phase. Phase B/C/D remain closed.
H2 QB rushing remains **UNDER TEST** with no result and is unrelated.

For finding H4, this RED chooses the non-mutating contract: refusal-class validation must occur
before any write-capable connection or `PRAGMA journal_mode`. This retains the already-stated
byte-freeze guarantee rather than narrowing it.

## New controls

### C1 — every semantic identity constraint is physical and duplicates fail before projection

- For each of `semantic_assertions(assertion_id)`,
  `semantic_attachments(evidence_id)`,
  `semantic_evidence_objects(evidence_sha256)`, and
  `semantic_adjudications(adjudication_id)`, initialization refuses:
  - the exact column set with no identity constraint;
  - a unique index on the wrong column;
  - a partial unique index on the identity column.
- For each table, a restored duplicate identity must return exactly
  `state=unknown`, `reason=semantic_identity_duplicate:<table>`, and
  `eligible_for_phase_c=False` before any dictionary or reducer projection.

This is 16 prospective failures: 12 structural substitutes plus four load-side duplicates.

### H2 — event uniqueness names the exact key

- Exact event columns with `UNIQUE(subject_id)` refuse.
- A partial `UNIQUE(event_id) WHERE event_type='attempt'` refuses.
- The inherited canonical positive continues to prove duplicate `event_id` insertion fails in
  SQLite.

### H3 — event order is a closed typed contract

- Matching acquisition/central event instants that are naive, fractional, future, or malformed
  must all render a named fail-closed state; none may reconcile into an exception or a hidden
  overlay.
- Persisted `event_seq` represented as TEXT in both the acquisition claim and central record must
  fail closed rather than being coerced with `int()`.
- A fractional writer clock must be refused with a named `event_at_invalid:*` error rather than
  producing a committed acquisition event.

### H4 — byte-freeze precedes WAL establishment

- A populated bare DELETE-mode semantic ledger must refuse
  `store_migration_unreconcilable:semantics` with its main/WAL fingerprint byte-identical,
  no object, and no staging creation.

### H5 — adjudication identity fields are total

- Unhashable and wrong scalar types for `adjudication_id`, `key`, and
  `effective_assertion_id` must reach field-specific named refusals before membership checks or
  SQLite binding.
- Each mutant asserts unchanged adjudication-row count and byte-equivalent effective semantic
  state.

## Failing-run census against the pinned GREEN

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result: **371 collected = 31 failed + 340 passed, process exit 1** in 15.84s.

Failure breakdown:

- C1 semantic constraints and duplicate projection: **16 failed**
- H2 exact event-id uniqueness: **2 failed**
- H3 canonical event instant/sequence/writer: **6 failed**
- H4 DELETE-mode byte-freeze: **1 failed**
- H5 adjudication totality: **6 failed**

All inherited 340 controls remain green. There are no skip/xfail decorators. The RED file is Ruff
clean, compiles under `-W error`, and passes `git diff --check`.

## Disposition

RED v9 is authored and intentionally failing. GREEN remains untouched. The RED/GREEN pair may land
only after implementing-lane reproduction, repair, adversarial review, and David's separate landing
word. No commit or push is authorized by this record.
