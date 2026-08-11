# Footballguys Phase A RED v7 — Codex authorship record

Date: 2026-08-10  
Layer: 1 — intake/persistence  
Authority: Claude accepted all three `e8fc4ec` GREEN-review findings, zero contested, and
explicitly requested Codex-authored RED v7.

## Pin

- Contract: `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256: `ac9d903aab5e52130b951665af626bc8ef0f57346372fb1b2ddace836843cd22`
- Size: 3,212 lines / 125,348 bytes
- Delta from committed RED v6: `+321/-1`
- Reviewed GREEN remains untouched at
  `43fddc5ef59b2c9f1352f99b7fdd6381b34d86f507204c0ba9fd0688541fbf71`.

## Binding census

Exact strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no \
  tests/contract/test_footballguys_phase_a_red.py
```

Result against untouched GREEN:

```text
318 collected = 28 failed / 290 passed, process exit 1
```

Inherited RED v6 alone remains:

```text
278 passed / 40 deselected, process exit 0
```

RED v7 contributes 40 cases: 28 negative failures and 12 positive/adjacent controls.

## C1 — total semantic writer schema and symmetric load validation

New cases:

- missing top-level assertion/attachment sections have exact named refusals;
- every required assertion/attachment field missing has an exact dotted-field refusal;
- non-mapping sections are named type refusals;
- all ten field-type controls assert the domain error boundary, never `KeyError`/`TypeError`;
- a restored future evidence retrieval instant is unknown and never eligible;
- empty or BLOB evidence identity, mirrored across assertion and attachment rows, is unknown and
  never eligible.

Failure/control split: 17 failing, 10 passing. The passing wrong-type controls prove the new RED
does not merely make every semantic write red; the committed GREEN already rejects those explicit
values and fails only the presence/load siblings named by the review.

## C2 — bidirectional event reconciliation and safe legacy handling

New cases:

- NULL and empty acquisition event claims fail closed;
- NULL and empty attempt event claims fail closed;
- central acquisition and attempt events lacking their store row fail closed;
- populated pre-event receipts and observations stores refuse before staging with
  `store_migration_unreconcilable:<store>`;
- repeating an intake while its unmatched central event exists refuses
  `event_ledger_unreconciled`, preserves the exact event ledger, and keeps the integrity state.

All nine cases fail against the committed GREEN.

### Deliberate correction to the proposed GREEN shape

RED v7 does **not** require a generic prepare-time sweep that deletes unmatched central events and
does **not** require identity to be fabricated for every populated legacy row. An orphan central
event is indistinguishable from a skewed/lost acquisition store, and early legacy schemas lack
enough historical event coordinates to reconstruct cross-store order. Deletion/backfill would
turn absence of proof into proof. The safe v7 contract is fail-closed preservation; any later
reconciliation mechanism must be provenance-safe and separately earned.

Row-empty legacy stores remain covered by the inherited migration positives and may migrate.

## C3 — WAL-aware, side-effect-bounded inactive reads

The fixture creates a real current store, then installs a closed `main + nonempty WAL + no SHM`
snapshot whose committed WAL frames drop the `attempts` table. It is not a mocked classifier and
does not leave the fixture writer open.

For both retention directions, RED requires:

- the valid archive reaches the inactive lookup;
- the committed WAL state is observed and framing row 9 renders;
- main/WAL membership, byte count, and SHA-256 remain exact;
- SHM is the only permitted new residue.

Two negative cases fail. Two companion cases prove a checkpointed WAL-absent inactive store
materializes neither WAL nor SHM and pass against the existing immutable branch.

## Anti-shadow and hygiene checks

- Strict inherited suite: 278/278, exit 0.
- Ruff on the touched test: clean.
- Cold Python 3.14 `py_compile -W error`: clean.
- `git diff --check`: clean.
- Skip/skipif/xfail markers: zero.
- All six independent known-answer hash anchors remain present exactly once.
- The two populated-legacy fixtures bootstrap the real governed 0700 namespace before installing
  the old schema; they fail on the intended migration predicate, not namespace permissions.
- The WAL fixture proves the physical consequence at the production SQLite seam and asserts both
  observation and byte preservation.

## Gate

RED v7 is uncommitted. Claude must reproduce this exact pin and 28F/290P census before repairing
GREEN. RED and GREEN travel together only on David's later landing word. `e8fc4ec` remains
unpushed; no first capture, provider contact, scheduler, runtime-store mutation, push, or Phase
B/C/D work opens. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
