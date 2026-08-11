# Footballguys Phase A GREEN v10 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `297c52f8c0181d743d5e2a721ad25abd7cb227af`  
**Verdict:** **NOT CLEAR — three findings**  
**Layer:** 1 — ingest/persistence

## Pin and divergence audit

The commit has parent `36882f78b0d10597e0664221a7cdd00c3a979d55` and changes exactly the
three declared files: the landing ledger entry, RED, and GREEN. Its measured diff is 419 additions
and 14 deletions (`+7/-0`, `+99/-13`, and `+313/-1`, respectively). The committed blobs reproduce:

- RED: `24d9e29d00e20768c687e748105c264cab8477929c7707bf370256835ba549ba`
- GREEN: `0a0bc0b439b744ff90a023adfa0fce1e1cdfdc1a38cabc37fec0f2353fd6f118`

The ambient HEAD advanced after this landing, but both reviewed paths remain byte-identical to the
commit. Unrelated existing working-tree changes were not touched.

## Reproduced gates

- Strict RED v10: **389 passed, exit 0**, 23.31 seconds.
- Full tracked suite: **5,622 passed / 12 skipped / 9 xfailed, exit 0**, 498.17 seconds.
- Ruff `src app`: clean.
- GREEN and RED compile under Python 3.14 `-W error` with bytecode writing disabled.

Passing inherited gates do not clear the following fresh probes.

## Findings

### 1. CRITICAL — a corrupt assertion key is filtered before validation and can promote a formerly conflicting horizon to Phase-C eligible

`semantic_state()` selects assertions with `WHERE key=?` at
`src/dynasty_genius/sources/footballguys_intake.py:2568`, then validates only the surviving rows at
line 2658. This is the same pre-validation filtering class repaired for adjudications, but the
assertion sibling remained.

Fresh probe:

1. Write two valid active assertions for the governed horizon key: `redraft` and
   `dynasty_startup`. The reducer correctly returns `unresolved_assertion_conflict`, not eligible.
2. Restore-corrupt only the dynasty assertion's persisted `key` to BLOB `b"invalid-key"`.
3. Reopen and read the governed horizon key.

Observed result:

```text
before: unknown / unresolved_assertion_conflict / eligible_for_phase_c=False
after:  known / redraft / assertion_id=redraft / eligible_for_phase_c=True
```

Every hash and attachment remains valid; the corrupt conflicting row simply disappears in SQL.
This contradicts the accepted “every writer scalar before any projection” boundary and changes a
closed horizon gate into an eligible one. Load all assertion rows, validate every writer scalar
(including the key) first, then filter/reduce. RED must include one healthy sibling plus one
key-corrupt conflicting sibling and assert that eligibility cannot open.

### 2. HIGH — the AUTOINCREMENT validator accepts the token in an unrelated default expression

The schema guard at lines 1471–1481 checks only whether the raw `sqlite_master.sql` string contains
`AUTOINCREMENT`. A table with the exact expected columns and indexes but this definition passes:

```sql
CREATE TABLE event_sequence (
  seq INTEGER PRIMARY KEY,
  event_id TEXT UNIQUE,
  event_type TEXT,
  store_name TEXT,
  subject_id TEXT,
  event_at TEXT DEFAULT 'AUTOINCREMENT'
)
```

Fresh initialization accepted it even though `seq` does not carry the frozen AUTOINCREMENT
contract. The v10 negative covers only total token absence, so it passes this broken guard. The
validation must bind the token to the `seq INTEGER PRIMARY KEY AUTOINCREMENT` declaration rather
than search the whole DDL text; RED should plant the token in a default while omitting it from
`seq` and require `store_schema_unmigratable:semantics`.

### 3. MEDIUM — non-datetime clock values still raise before the named row-9 fallback

`read_model()` calls `clock_now.isoformat()` at line 3018 and catches only
`FootballguysIntakeError`. The v10 RED covers a naive `datetime`, which has `isoformat()` and
therefore reaches the catchable canonicalizer. It does not cover other invalid dependency values.

Fresh probes with empty governed roots produced:

```text
clock -> "2026-08-10T12:00:00-04:00" : AttributeError: 'str' object has no attribute 'isoformat'
clock -> None                        : AttributeError: 'NoneType' object has no attribute 'isoformat'
```

The accepted boundary was an invalid clock dependency becoming named fail-closed state, never a
bare exception. Establish `datetime` type before method dispatch (or otherwise totalize the
conversion) and render literal row 9. RED should cover at least `str` and `None`, not only the
naive-datetime species.

## Disposition

GREEN v10 is **NOT CLEAR**. The commit remains unpushed and no first capture should run against it.
The three findings require prospective RED authorship before repair. No RED, GREEN, config,
manifest, runtime, provider, scheduler, commit, push, or downstream phase was changed by this
review. Phase B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is
unrelated.
