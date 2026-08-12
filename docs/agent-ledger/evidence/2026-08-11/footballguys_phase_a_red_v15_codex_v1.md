# Footballguys Phase A RED v15 — Codex v1

**Date:** 2026-08-11 ET  
**Layer:** 1 — ingest/persistence  
**Baseline GREEN:** `src/dynasty_genius/sources/footballguys_intake.py` SHA-256
`8bbb7583507cf712b3f12679958b2d9e79c85e3966bf9243d38bbee1430251b8`

## Authority and scope

The implementing lane accepted the sole adversarial finding against commit `f971244` and
explicitly requested Codex-authored RED v15. The accepted rule closes the semantics database over
its whole SQLite object inventory, not merely its table text.

This act changes only the prospective contract plus evidence/ledger/wire. It authorizes no GREEN,
config, manifest, runtime, provider, scheduler, commit, push, capture, or Phase B/C/D work.

## Controls added

The canonical positive contains the real governed inventory: acquisitions marker table, five
semantic/event tables, `sqlite_sequence`, and the required PK/UNIQUE autoindexes.

Seven noncanonical fixtures add, one at a time:

1. an aborting event-sequence trigger;
2. an ignoring event-sequence trigger;
3. an aborting trigger on a second governed table (`semantic_assertions`);
4. a view;
5. an extra table;
6. a surplus unique index; and
7. a surplus non-unique index.

The view, extra-table, and non-unique-index cases extend the minimum requested examples because the
accepted inventory is exact; testing only triggers and unique indexes would permit an
object-type-specific implementation to pass while still accepting forbidden objects.

Before each reopen, the fixture persists both a central event row and real semantic assertion,
attachment, and evidence rows. Every negative requires
`store_schema_unmigratable:semantics` during initialization, then compares all governed
application rows to the pre-attempt snapshot. The unchanged-state oracle is therefore non-vacuous.

## Binding census

Exact strict command, run twice:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Both runs produced:

```text
433 collected = 7 failed + 426 passed, exit 1
```

The failures are exactly the seven noncanonical object inventories. The canonical inventory and
all inherited 425 contracts pass.

## Quality gates

- Ruff on the RED: clean.
- Python 3.14 compilation under `-W error`, with bytecode writing disabled: clean.
- No skip, skipif, or xfail markers/calls.
- `git diff --check`: clean.
- Baseline GREEN remains byte-identical at `8bbb7583…`.

## State

RED v15 is authored and intentionally failing. Nothing is committed or pushed. No capture,
provider contact, scheduler, or Phase B/C/D work opens. H2 QB rushing remains **UNDER TEST** with
no result and is unrelated.
