# Footballguys Phase A RED v13 — Codex v1

**Date:** 2026-08-11 ET  
**Authority:** implementing lane accepted the sole finding from the adversarial review of
`62278abc71ffed7d104b4bdd17ec8a0cd763753a` and requested Codex-authored RED v13.  
**RED path:** `tests/contract/test_footballguys_phase_a_red.py`  
**RED SHA-256:** `b40126f39c4eeae0dc481b4b2a7ae07b51052f021973b3b2c9b802027e5c898b`  
**Size:** 4,606 lines / 179,509 bytes  
**Baseline GREEN:** `e6cd167d2e33b15e63e1b7dfc23d0e6229c8889cbddba3f17f8f72d3ee6f8d28`

## Scope

RED v13 extends the inherited 412-contract Phase A suite. It changes no GREEN, configuration,
manifest, runtime store, provider state, scheduler, or downstream phase. Phase B/C/D remain closed.
H2 QB rushing remains **UNDER TEST** with no result and is unrelated.

## New control

One parameterized initialization control rebuilds `event_sequence` with three legal SQLite seq
declarations:

- canonical `seq INTEGER PRIMARY KEY AUTOINCREMENT` — must remain accepted;
- `seq INTEGER PRIMARY KEY AUTOINCREMENT CHECK(seq > 100)` — must refuse
  `store_schema_unmigratable:semantics`;
- `seq INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE` — must refuse the same way.

The first negative makes the operational consequence load-bearing: sequence 1 cannot be inserted.
The redundant-UNIQUE negative proves the oracle requires complete exact grammar rather than merely
blocking a known harmful suffix. Passing requires the complete token list after `seq` to equal
exactly `INTEGER PRIMARY KEY AUTOINCREMENT`.

## Failing-run census against the pinned GREEN

Exact command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result reproduced twice: **415 collected = 2 failed + 413 passed, process exit 1**. The binding
second run completed in 20.52 seconds.

Both suffix negatives fail. The new canonical positive and all inherited 412 controls remain
green. There are no skip/xfail decorators. The RED is Ruff clean, compiles under Python 3.14
`-W error`, and passes `git diff --check`.

## Disposition

RED v13 is authored and intentionally failing. GREEN remains byte-exact and untouched. The pair
may land only after implementing-lane reproduction, repair, adversarial review, and David's
separate landing word. No commit or push is authorized by this record.
