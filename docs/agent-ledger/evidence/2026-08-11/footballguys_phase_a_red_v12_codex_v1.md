# Footballguys Phase A RED v12 — Codex v1

**Date:** 2026-08-11 ET  
**Authority:** implementing lane accepted both findings from the adversarial review of
`c32884a4af25d38e6d555e7e9c44e50823fffe2f` and requested Codex-authored RED v12.  
**RED path:** `tests/contract/test_footballguys_phase_a_red.py`  
**RED SHA-256:** `7b26b0fc3788dd799e670b2b2b4e66ae429d9057659b173a44267c8910a1e287`  
**Size:** 4,556 lines / 177,389 bytes  
**Baseline GREEN:** `07a1420530f2cedabec6ddef2b9cd7f77b78841a69bb04335f3111124841b6f8`

## Scope

RED v12 extends the inherited 405-contract Phase A suite. It changes no GREEN, configuration,
manifest, runtime store, provider state, scheduler, or downstream phase. Phase B/C/D remain closed.
H2 QB rushing remains **UNDER TEST** with no result and is unrelated.

## New controls

### H1 — seq AUTOINCREMENT ownership is parser-proven

Three exact-column, correctly indexed schemas retain `seq INTEGER PRIMARY KEY` without
AUTOINCREMENT while planting the full phrase `SEQ INTEGER PRIMARY KEY AUTOINCREMENT` in:

- a single-quoted DEFAULT literal;
- a block comment;
- a line comment crossing a newline before the closing parenthesis.

Each must refuse `store_schema_unmigratable:semantics`. Passing requires isolating the top-level
`seq` column definition after ignoring quoted strings and comments; normalized whole-DDL substring
search cannot satisfy the oracle. The inherited production-schema positive remains binding.

### M2 — version values occupy the complete signed-64 persistence domain

- `2**63` and `-(2**63)-1` must each produce a named `semantic_version_invalid` refusal before
  initializing the semantic store.
- On a fresh root, `semantics.db`, `semantics.db-wal`, and `semantics.db-shm` must remain absent.
- `-2**63` and `2**63-1` are positive boundary anchors: both must persist and read back as the
  effective assertion, preventing an off-by-one or unsigned repair.

## Failing-run census against the pinned GREEN

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result reproduced twice: **412 collected = 5 failed + 407 passed, process exit 1**. The binding
second run completed in 23.19 seconds.

Failure breakdown:

- H1 parser-level AUTOINCREMENT ownership: **3 failed**
- M2 signed-64 overflow purity: **2 failed**

All inherited 405 controls and both new legal-boundary anchors remain green. There are no
skip/xfail decorators. The RED is Ruff clean, compiles under Python 3.14 `-W error`, and passes
`git diff --check`.

## Disposition

RED v12 is authored and intentionally failing. GREEN remains byte-exact and untouched. The pair
may land only after implementing-lane reproduction, repair, adversarial review, and David's
separate landing word. No commit or push is authorized by this record.
