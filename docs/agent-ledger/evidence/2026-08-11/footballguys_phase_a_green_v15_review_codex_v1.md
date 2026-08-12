# Footballguys Phase A GREEN v15 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `ba890ecf65ccbe0203179559aee2b66384004ab5`  
**Verdict:** **NOT CLEAR — two HIGH findings**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit changes exactly the three declared files: landing ledger, RED, and GREEN. The committed
blobs reproduce:

- RED: `631613217d0471750ba714e2a1ef349a88f73c17ac0e14132b1ed44d7e940ece`
- GREEN: `7dc64bf502b2a260ea3c4c050ad93b6fd5bf45c50f67720114dadfffdf0d4103`

Later HEAD leaves both reviewed paths byte-identical. Unrelated working-tree changes were not
touched.

## Reproduced gates

- Strict RED v15: **433 passed, exit 0**.
- Full Git-tracked suite: **5,666 passed / 12 skipped / 9 xfailed, exit 0**.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

The seven v15 inventory controls hold: explicit triggers, views, surplus tables, and explicit
surplus indexes all refuse while the canonical inventory passes.

## Findings

### 1. HIGH — the autoindex allowlist validates a name prefix, not the required index signatures

At `src/dynasty_genius/sources/footballguys_intake.py:1518-1533`, any index whose name begins
`sqlite_autoindex_` and whose table name is allowed passes the object-inventory check. SQLite itself
creates exactly such names for table-level `PRIMARY KEY` and `UNIQUE` constraints. The later
`_has_exact_unique_index` check proves that the required identity index exists, but does not reject
additional autoindexes.

A restored `semantic_assertions` table with its canonical columns and required primary key plus
`UNIQUE(claim)` produced both `sqlite_autoindex_semantic_assertions_1` and
`sqlite_autoindex_semantic_assertions_2`. Initialization accepted the store. The first valid
`redraft` assertion wrote; the second valid assertion with a distinct identity but the same claim
raised raw `sqlite3.IntegrityError: UNIQUE constraint failed: semantic_assertions.claim`.

This is not a reserved-name spoof: SQLite generated the surplus name that satisfies the production
predicate. Validate the exact expected PK/UNIQUE signatures and counts for every governed table,
including column order and partial/expression status, and reject every surplus signature.

Prospective RED v16 should include the real table-level `UNIQUE(claim)` rebuild, a surplus
autoindex on a second semantic table, canonical required-signature positives, and populated-row
unchanged assertions on pre-write refusal.

### 2. HIGH — the allowed `acquisitions` marker table is admitted by name without a schema contract

The inventory explicitly permits the `acquisitions` table, but `_SEMANTIC_TABLES` and
`_validate_semantics_schema` do not validate its columns, definitions, order, or required primary
and unique constraints. `initialize_database("semantics")` later executes `CREATE TABLE IF NOT
EXISTS` and then writes the bootstrap marker.

Replacing the marker table with valid SQLite `CREATE TABLE acquisitions (wrong_column TEXT)`
passed read-only prevalidation. Initialization then leaked raw
`sqlite3.OperationalError: table acquisitions has no column named row_id` from the bootstrap
insert instead of refusing `store_schema_unmigratable:semantics` before the write-capable path.

Prospective RED v16 should bind the marker table's exact ordered grammar
(`row_id TEXT PRIMARY KEY`, `offering_id TEXT UNIQUE`, `kind TEXT`) and exact two autoindex
signatures. Include missing/wrong columns, an extra column or suffix, wrong order, and missing or
surplus constraints; all must refuse during the non-mutating prevalidation with application rows
and the existing byte-freeze oracle unchanged.

## Disposition

GREEN v15 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
Both findings require prospective RED authorship before repair. No RED, GREEN, config, manifest,
runtime, provider, scheduler, commit, push, or downstream phase was changed by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
