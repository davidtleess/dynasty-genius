# Footballguys Phase A GREEN v12 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `62278abc71ffed7d104b4bdd17ec8a0cd763753a`  
**Verdict:** **NOT CLEAR — one HIGH finding**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit has parent `4f4ee97c41acf4781594fa1711a9badafff4f8e2` and changes exactly the
three declared files: landing ledger, RED, and GREEN. Its measured diff is 240 additions and ten
deletions. The committed blobs reproduce:

- RED: `7b26b0fc3788dd799e670b2b2b4e66ae429d9057659b173a44267c8910a1e287`
- GREEN: `e6cd167d2e33b15e63e1b7dfc23d0e6229c8889cbddba3f17f8f72d3ee6f8d28`

Later HEAD leaves both reviewed paths byte-identical. Unrelated working-tree changes were not
touched.

## Reproduced gates

- Strict RED v12: **412 passed, exit 0**, 64.00 seconds.
- Full tracked suite: **5,645 passed / 12 skipped / 9 xfailed, exit 0**, 592.27 seconds.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

Fresh probes confirmed that literal/comment decoys are stripped across single and double quotes,
block and line comments, brackets, and backticks. The signed-64 version repair also held at both
legal endpoints and both overflow directions.

## Finding

### 1. HIGH — the parser's “exact tokens” check accepts arbitrary trailing constraints on `seq`

At `src/dynasty_genius/sources/footballguys_intake.py:1351-1356`, the parser isolates the `seq`
column but compares only `tokens[1:5]` to `INTEGER PRIMARY KEY AUTOINCREMENT`. It does not require
that those are the complete tokens after the column name, contradicting the accepted exact-token
contract.

This valid SQLite declaration passed `initialize_database("semantics")`:

```sql
seq INTEGER PRIMARY KEY AUTOINCREMENT CHECK(seq > 100)
```

The consequence is immediate rather than cosmetic: the first governed event insertion then raised
`sqlite3.IntegrityError: CHECK constraint failed: seq > 100`, because the automatic first sequence
is 1. A store that must have refused before staging was therefore accepted and fails only at the
first state-advancing write.

Require the complete token sequence after the unquoted `seq` name to equal exactly
`INTEGER PRIMARY KEY AUTOINCREMENT`; no suffix tokens are permitted. Prospective RED should include
at least the load-bearing `CHECK(seq > 100)` suffix, assert pre-write
`store_schema_unmigratable:semantics`, and include the existing canonical declaration as the
positive control. A harmless-looking suffix such as redundant `UNIQUE` may be included as a second
negative to prove this is exact grammar rather than consequence-specific blocking.

## Disposition

GREEN v12 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
The finding requires prospective RED authorship before repair. No RED, GREEN, config, manifest,
runtime, provider, scheduler, commit, push, or downstream phase was changed by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
