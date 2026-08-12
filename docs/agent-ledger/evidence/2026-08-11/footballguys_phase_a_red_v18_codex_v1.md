# Footballguys Phase A RED v18 — active acquisition-store closure

**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Authority:** implementing lane accepted both findings from the `82405fd` GREEN-v17 review and
explicitly requested Codex-authored RED v18.  
**Scope:** RED contract only; no GREEN/config/manifest/runtime/provider/scheduler/commit/push or
Phase B/C/D.

## Pins

| Artifact | SHA-256 | Shape |
|---|---|---:|
| RED v18 `tests/contract/test_footballguys_phase_a_red.py` | `677b5fe9bbcda0a6734feff75c8fadd6ff8a03985219477254ccbdc9aca93de4` | 5,923 lines / 227,778 bytes |
| Baseline GREEN `src/dynasty_genius/sources/footballguys_intake.py` | `11667534393fa600e6f707e5a1e24b5527723121c3583d005008c36bf366ac7d` | unchanged from `82405fd` |

The RED was authored and validated in an isolated `/private/tmp` clone because the managed
filesystem permits reading but not registering a linked Git worktree in the repository's shared
Git metadata. No permission escalation was requested. The verified RED is then delivered to the
canonical shared path byte-for-byte.

## Strict failing census

Command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Result against the untouched GREEN:

```text
505 collected = 31 failed + 474 passed, exit 1
```

All 472 inherited v17 cases pass. The v18 slice is 33 cases: **31 prospective failures + 2
positive anchors**.

## New contract inventory

### C1 — active acquisition stores, both retention modes

Every negative runs against both `receipts.db` (`full_offsite`) and `observations.db`
(`metadata_only`) through the production composition root and real `intake` lifecycle.

- **False-success operational controls (2 failures):** canonical v4 acquisition columns plus only
  `CHECK(archive_bytes < 0)`. Broken GREEN reports success-shaped intake; the RED instead requires
  a named `store_schema_unmigratable:<store>` refusal before staging, with unchanged rows and
  main/WAL bytes plus zero objects/events/staging residue.
- **Orphan-event operational controls (2 failures):** canonical attempts columns plus only
  `CHECK(status = 'never')`. Broken GREEN leaks raw `IntegrityError` after central-event commit;
  the RED requires the same pre-staging named refusal and zero event residue.
- **Complete table grammar / physical index controls (16 failures):** acquisitions `STRICT`,
  `WITHOUT ROWID`, swapped PK/UNIQUE origins, PK `COLLATE NOCASE`, surplus UNIQUE autoindex;
  attempts `STRICT`, missing AUTOINCREMENT, and surplus UNIQUE autoindex. Every physical-index
  fixture is independently proven with real `PRAGMA index_list` + `index_xinfo` facts before the
  production refusal is asserted.
- **Closed schema-object inventory (10 failures):** IGNORE trigger on acquisitions; IGNORE trigger
  on attempts; surplus view; surplus table; surplus non-unique index — each in both modes.
- **Legacy positive (1 pass):** the exact row-empty pre-v3 acquisition schema still migrates in
  observations mode, complementing inherited `s27` (receipts) and inherited `v7` populated-legacy
  fail-closed controls for both modes.

The shared refusal oracle snapshots application rows and main/WAL bytes before the production
call, captures returned result/exception plus objects/events/staging after it, and asserts the
complete external state. A column-set-only validator, an initialization-only test, a raw SQLite
exception, or a correct-looking refusal emitted after publication all fail.

### M2 — event ledger whole-DDL

- exact canonical `event_sequence` remains accepted (1 pass);
- the identical canonical body followed by `STRICT` must refuse non-mutatingly (1 failure).

This calls `initialize_database("semantics")`; it does not pass by testing a parser helper in
isolation. A repair to the shared parser that leaves the event table on its older sibling parser
still fails.

## Adequacy and hygiene

- V18-only census: **31 failed / 2 passed / 472 deselected**.
- Collection: **33/505 v18 tests**, no collection errors.
- No `skip`, `skipif`, or `xfail` in the RED.
- Ruff over the RED: clean.
- Strict Python 3.14 compile: exit 0.
- `git diff --check`: clean.
- RED delta: **424 insertions / 1 deletion**; only the contract file changed before evidence and
  ledger records were added.
- No provider payload is embedded; archives are the existing tiny synthetic integration fixture.
- No runtime store, capture, provider contact, scheduler, GREEN, config, or downstream phase was
  opened.

## State

RED v18 is intentionally failing and ready for the implementing lane to reproduce. It authorizes
GREEN repair only after reproduction. RED and GREEN travel together only on David's word.
Footballguys first capture remains closed. H2 QB rushing remains **UNDER TEST** with no result and
is unrelated.
