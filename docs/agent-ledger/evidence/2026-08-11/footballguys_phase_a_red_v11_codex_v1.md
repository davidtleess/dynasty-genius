# Footballguys Phase A RED v11 — Codex v1

**Date:** 2026-08-11 ET  
**Authority:** implementing lane accepted all three findings from the adversarial review of
`297c52f8c0181d743d5e2a721ad25abd7cb227af` and requested Codex-authored RED v11.  
**RED path:** `tests/contract/test_footballguys_phase_a_red.py`  
**RED SHA-256:** `f578b32af1f9f709fd854a7c00c203013d1feb3db80eb0b0a3630b0227b0d210`  
**Size:** 4,446 lines / 173,110 bytes  
**Baseline GREEN:** `0a0bc0b439b744ff90a023adfa0fce1e1cdfdc1a38cabc37fec0f2353fd6f118`

## Scope

RED v11 extends the inherited 389-contract Phase A suite. It changes no GREEN, configuration,
manifest, runtime store, provider state, scheduler, or downstream phase. Phase B/C/D remain closed.
H2 QB rushing remains **UNDER TEST** with no result and is unrelated.

## New controls

### C1 — every assertion scalar is validated table-wide before projection

- Two active conflicting horizon assertions are established as an unresolved conflict. Corrupting
  only one assertion's key to either empty TEXT or BLOB must return exactly
  `assertion_row_invalid`; the healthy sibling can never become Phase-C eligible through SQL
  filtering.
- A separate inactive-row matrix covers every remaining writer scalar before active/key
  projection: assertion identity, key, exact-integer version, allowlisted claim, and evidence
  identity. Empty, BLOB, wrong-vocabulary, TEXT-version, and REAL-version forms all require the
  same named fail-closed state.
- The inherited v10 exact-INTEGER active control remains binding. The new identity/evidence
  anchors also demonstrate that table-wide validation preserves already-correct branches.

### H2 — AUTOINCREMENT must belong to the `seq` declaration

- The exact expected table columns and identity index are retained.
- `seq` is `INTEGER PRIMARY KEY` without AUTOINCREMENT.
- The word `AUTOINCREMENT` is planted in `event_at TEXT DEFAULT 'AUTOINCREMENT'`.
- Initialization must refuse `store_schema_unmigratable:semantics`; whole-DDL substring search
  cannot satisfy the oracle.

### M3 — every non-datetime read clock fails closed before method dispatch

- String, `None`, and integer clock returns each call `read_model()` on a fresh governed root.
- Each must render literal framing row 9 through the existing oracle, never raise
  `AttributeError` or another bare exception.

## Failing-run census against the pinned GREEN

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result reproduced twice: **405 collected = 12 failed + 393 passed, process exit 1**. The binding
second run completed in 17.01 seconds.

Failure breakdown:

- C1 pre-filter/table-wide assertion validation: **8 failed**
- H2 declaration-bound AUTOINCREMENT proof: **1 failed**
- M3 non-datetime clock totality: **3 failed**

All inherited 389 controls remain green, along with four new table-wide scalar anchors that the
baseline already satisfies. There are no skip/xfail decorators. The RED is Ruff clean, compiles
under Python 3.14 `-W error`, and passes `git diff --check`.

## Disposition

RED v11 is authored and intentionally failing. GREEN remains byte-exact and untouched. The pair
may land only after implementing-lane reproduction, repair, adversarial review, and David's
separate landing word. No commit or push is authorized by this record.
