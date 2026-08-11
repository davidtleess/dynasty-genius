# Footballguys Phase A GREEN v11 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `c32884a4af25d38e6d555e7e9c44e50823fffe2f`  
**Verdict:** **NOT CLEAR — two findings**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit has parent `0220bdb70ed9b7483d273b1e2bf5e20c3322a877` and changes exactly the
three declared files: landing ledger, RED, and GREEN. Its measured diff is 197 additions and eight
deletions. The committed blobs reproduce:

- RED: `f578b32af1f9f709fd854a7c00c203013d1feb3db80eb0b0a3630b0227b0d210`
- GREEN: `07a1420530f2cedabec6ddef2b9cd7f77b78841a69bb04335f3111124841b6f8`

The ambient HEAD advanced after landing, but both reviewed paths remain byte-identical. Unrelated
working-tree changes were not touched.

## Reproduced gates

- Strict RED v11: **405 passed, exit 0**, 18.25 seconds.
- Full tracked suite: **5,638 passed / 12 skipped / 9 xfailed, exit 0**, 615.98 seconds.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

Fresh probes confirmed the C1 table-wide assertion repair and M3 non-datetime clock repair. The
following adjacent boundaries remain open.

## Findings

### 1. HIGH — the AUTOINCREMENT “binding” is still a whole-DDL substring search and is spoofable by literals or comments

At `src/dynasty_genius/sources/footballguys_intake.py:1475-1485`, whitespace is normalized across
the complete `sqlite_master.sql` text and the implementation searches that text for
`SEQ INTEGER PRIMARY KEY AUTOINCREMENT`. It never isolates or parses the `seq` column definition.

Two exact-column, correctly indexed tables with `seq INTEGER PRIMARY KEY` and **no** AUTOINCREMENT
were both accepted by `initialize_database("semantics")`:

```sql
event_at TEXT DEFAULT 'SEQ INTEGER PRIMARY KEY AUTOINCREMENT'
event_at TEXT /* SEQ INTEGER PRIMARY KEY AUTOINCREMENT */
```

The v11 RED planted only the shorter word `AUTOINCREMENT` in the default, so the repaired substring
special-cases that fixture while the same false proof survives with the full phrase. The validator
must tokenize/parse the column list (ignoring quoted strings and comments) and prove that the
AUTOINCREMENT token belongs to `seq` itself. Prospective RED should include both quoted-literal and
comment decoys and require `store_schema_unmigratable:semantics`.

### 2. MEDIUM — a type-correct version outside SQLite’s integer domain raises after creating the governed store

The writer's “total schema” check at lines 2386–2394 proves only Python `int` and non-`bool`.
Python integers are unbounded; SQLite INTEGER bindings are signed 64-bit. On a fresh governed root,
an otherwise valid assertion with `version = 2**100` produced:

```text
OverflowError: Python int too large to convert to SQLite INTEGER
```

Before the call, `semantics.db`, `-wal`, and `-shm` were all absent. After the call,
`semantics.db` existed. This violates the standing closed-writer and validation-before-
initialization contracts: a record that cannot inhabit the persisted schema leaked a bare
exception after durable mutation.

Define the storable version domain explicitly and validate it before line 2406 initializes the
store. Prospective RED should cover both positive and negative signed-64-bit overflow, demand a
named `semantic_version_invalid` refusal, and assert physical absence of the main DB and sidecars
on a fresh root.

## Disposition

GREEN v11 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
The findings require prospective RED authorship before repair. No RED, GREEN, config, manifest,
runtime, provider, scheduler, commit, push, or downstream phase was changed by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
