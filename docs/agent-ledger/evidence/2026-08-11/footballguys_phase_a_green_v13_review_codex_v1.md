# Footballguys Phase A GREEN v13 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `e19d056c291b6252f71a53b564116a1c1bad7b3f`  
**Verdict:** **NOT CLEAR — one HIGH finding**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit changes exactly the three declared files: landing ledger, RED, and GREEN. The committed
blobs reproduce exactly:

- RED: `b40126f39c4eeae0dc481b4b2a7ae07b51052f021973b3b2c9b802027e5c898b`
- GREEN: `7d1090c27e8f7c3a87384315c47d02a8f900b183bfbe5663100b58d6169365b8`

Later HEAD leaves both reviewed paths byte-identical. Unrelated working-tree changes were not
touched.

## Reproduced gates

- Strict RED v13: **415 passed, exit 0**.
- Full Git-tracked suite in the primary tree: **5,648 passed / 12 skipped / 9 xfailed, exit 0**.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

An exact-commit detached worktree initially produced three frontend-linter failures solely because
it had no `frontend/node_modules`; all three became green after binding the already-installed
dependency directory. The clean checkout otherwise produced **5,610 passed / 34 skipped / 9
xfailed**; the additional skips were local-artifact availability differences. This environmental
accounting does not affect the finding below.

Fresh parser probes confirmed that the repaired column-level rule accepts the canonical,
lowercase, and comment-equivalent declarations and refuses valid SQLite suffix variants including
`NOT NULL`, `CHECK`, `UNIQUE`, `COLLATE BINARY`, and reordered `ASC`.

## Finding

### 1. HIGH — a table-level constraint bypasses the exact `seq`-column grammar and breaks the first event write

At `src/dynasty_genius/sources/footballguys_intake.py:1348-1361`,
`_seq_declaration_is_governed` now correctly requires the complete token list of the `seq` column.
But `_validate_semantics_schema` still treats that column check plus `PRAGMA table_info` and the
required unique index as proof of the whole event-ledger schema. SQLite does not expose table-level
constraints through `PRAGMA table_info`.

This valid SQLite table passed `initialize_database("semantics")`:

```sql
CREATE TABLE event_sequence (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE,
  event_type TEXT,
  store_name TEXT,
  subject_id TEXT,
  event_at TEXT,
  CHECK(seq > 100)
)
```

The first direct governed `_allocate_event(...)` then raised
`sqlite3.IntegrityError: CHECK constraint failed: seq > 100`. The same operational failure that
v13 closed as a column suffix therefore remains reachable as a separate table-constraint segment:
the store is accepted during the required pre-write validation and fails only at the first
state-advancing event write.

Prospective RED v14 should bind the **complete event-sequence table grammar**, not merely another
`seq` suffix. At minimum:

1. retain the canonical table as a positive control;
2. add the load-bearing table-level `CHECK(seq > 100)` negative and require
   `store_schema_unmigratable:semantics` at initialization;
3. add a syntactically distinct named table constraint or redundant table-level `UNIQUE(seq)`
   negative so an implementation that merely searches for the literal `CHECK` still fails; and
4. assert refusal occurs before any governed event row or other state advance.

The implementation may parse and validate every top-level event-table segment or prove an
equivalent closed schema, but unexpected table constraints cannot remain invisible.

## Disposition

GREEN v13 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
The finding requires prospective RED authorship before repair. No RED, GREEN, config, manifest,
runtime, provider, scheduler, commit, push, or downstream phase was changed by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
