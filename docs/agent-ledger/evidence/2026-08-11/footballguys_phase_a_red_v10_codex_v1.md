# Footballguys Phase A RED v10 — Codex v1

**Date:** 2026-08-11 ET  
**Authority:** implementing lane accepted all five adversarial findings against committed GREEN
`b582b1d62a2eae199e5fb6b0ad519ae2126afd8e` and requested Codex-authored RED v10.  
**RED path:** `tests/contract/test_footballguys_phase_a_red.py`  
**RED SHA-256:** `24d9e29d00e20768c687e748105c264cab8477929c7707bf370256835ba549ba`  
**Size:** 4,285 lines / 166,834 bytes  
**Baseline GREEN:** `0f963e7371dc3b89e97de5f6b9f09e2c6d257f7c5c88155c87d8cf27cf134933`

## Scope

RED v10 extends the inherited 371-contract Phase A suite. It changes no GREEN, configuration,
manifest, runtime store, provider state, scheduler, or downstream phase. Phase B/C/D remain closed.
H2 QB rushing remains **UNDER TEST** with no result and is unrelated.

## New controls

### C1 — semantic load types mirror every writer scalar

- For restored adjudications, empty and BLOB values for each of `adjudication_id`, `key`, and
  `effective_assertion_id` must produce exactly `adjudication_row_invalid` before the row can be
  filtered, governed, or projected.
- A restored assertion table with a valid identity constraint but REAL `active=1.0` must produce
  exactly `assertion_row_invalid`; equality with integer 1 is not type validity.

### H2 — central sequencing is a whole structure and a load invariant

- Initialization refuses each exact-column substitute:
  - `seq INTEGER` without a primary key;
  - `seq TEXT PRIMARY KEY`;
  - `seq INTEGER PRIMARY KEY` without the frozen autoincrement contract.
- Load-side reconciliation refuses duplicate, nonpositive, and reversed/non-monotonic central
  sequence assignments before order projection. Each fixture updates both central records and
  store claims so a prospective implementation cannot pass through a mere tuple mismatch.

### H3 — attempt sequence uses the same exact-int predicate as acquisitions

- An attempt claim restored as REAL `2.0` while central order is INTEGER `2` must render event
  integrity failure. Python numeric equality and later `int()` coercion are explicitly barred.

### H4 — the read clock is one validated dependency

- A naive read clock over an aware persisted event must render the existing literal row-9
  fail-closed state, never raise.
- A read with multiple central events asserts the injected clock is called exactly once and that
  validated value is reused throughout reconciliation.

### H5 — invalid semantic records are pure before store initialization

- On a fresh root, malformed assertion and adjudication records each reach their named refusal
  while `semantics.db`, `semantics.db-wal`, and `semantics.db-shm` remain absent.
- This covers both writers and repairs the reviewing lane's own RED-v9 inadequacy: the prior
  unchanged-state oracle had seeded the semantic store first.

## Failing-run census against the pinned GREEN

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result reproduced twice: **389 collected = 18 failed + 371 passed, process exit 1**. The binding
second run completed in 16.60s.

Failure breakdown:

- C1 semantic load scalar closure: **7 failed**
- H2 whole central sequence contract: **6 failed**
- H3 attempt exact-int symmetry: **1 failed**
- H4 one valid read clock: **2 failed**
- H5 pre-initialization purity: **2 failed**

All inherited 371 controls remain green. There are no skip/xfail decorators. The RED file is Ruff
clean, compiles under `-W error`, and passes `git diff --check`.

## Disposition

RED v10 is authored and intentionally failing. GREEN remains untouched. The RED/GREEN pair may land
only after implementing-lane reproduction, repair, adversarial review, and David's separate landing
word. No commit or push is authorized by this record.
