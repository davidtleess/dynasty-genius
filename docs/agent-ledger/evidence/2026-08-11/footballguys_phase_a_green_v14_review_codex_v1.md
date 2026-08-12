# Footballguys Phase A GREEN v14 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `f9712449e68be130eab1098bcfbccc20d4d67c3f`  
**Verdict:** **NOT CLEAR — one HIGH finding**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit changes exactly the three declared files: landing ledger, RED, and GREEN. The committed
blobs reproduce:

- RED: `9e5e12c2f43f988bb3e819b4377be54b4c4886e6ace49a944962a47cce24e0e8`
- GREEN: `8bbb7583507cf712b3f12679958b2d9e79c85e3966bf9243d38bbee1430251b8`

Later HEAD leaves both reviewed paths byte-identical. Unrelated working-tree changes were not
touched. The wire subject contained an unevaluated shell expression, but the body supplied the
full commit id above and the repository pin matches it.

## Reproduced gates

- Strict RED v14: **425 passed, exit 0**.
- Full Git-tracked suite: **5,658 passed / 12 skipped / 9 xfailed, exit 0**.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

The v14 repair holds for every inherited whole-table case: six exact ordered column segments are
required, all extra table-constraint segments refuse, and modified definitions/order refuse.

## Finding

### 1. HIGH — closed table DDL does not close executable schema objects around the governed table

At `src/dynasty_genius/sources/footballguys_intake.py:1289-1369`,
`_event_table_grammar_is_governed` correctly validates the complete `CREATE TABLE` column list.
But `_validate_semantics_schema` does not reject triggers and only proves that each required unique
index exists; it does not reject surplus unique indexes. Those objects live as separate
`sqlite_master` rows, so the canonical `CREATE TABLE event_sequence ...` text remains unchanged
and passes the repaired parser.

Three fresh restored-schema probes all passed `initialize_database("semantics")`:

1. `BEFORE INSERT ... RAISE(ABORT, 'event blocked')` caused the first governed event allocation to
   raise raw `sqlite3.IntegrityError: event blocked`.
2. `BEFORE INSERT ... RAISE(IGNORE)` silently returned `event_seq=0` while the central ledger
   remained at zero rows.
3. `CREATE UNIQUE INDEX one_event_type ON event_sequence(event_type)` allowed one attempt event,
   then raised raw `sqlite3.IntegrityError` on the second event of the same type.

This is one schema-inventory defect, not three findings. The validated table bytes are canonical
in every case, but executable persisted schema state changes the writer's behavior after the
required pre-write validation. Restored/corrupt store validation is already an in-model contract;
this finding does not claim protection against live out-of-model namespace mutation.

Prospective RED v15 should bind a closed **schema-object inventory**, not blacklist these SQL
strings. At minimum:

1. canonical semantics schema with no triggers and only the expected PK/UNIQUE index signatures is
   the positive control;
2. aborting and ignoring triggers on `event_sequence` both require
   `store_schema_unmigratable:semantics` during initialization;
3. a trigger on a second governed semantic table proves the rule is table-set-wide rather than an
   `event_sequence` special case;
4. the surplus unique index on `event_type` requires the same pre-write refusal; and
5. every refusal leaves central and semantic application rows unchanged.

The validator may compare normalized `sqlite_master`/PRAGMA object signatures or prove an
equivalent closed inventory. SQLite's internal `sqlite_sequence` and required autoindexes must be
handled explicitly rather than treated as unexplained extras.

## Disposition

GREEN v14 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
The finding requires prospective RED authorship before repair. No RED, GREEN, config, manifest,
runtime, provider, scheduler, commit, push, or downstream phase was changed by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
