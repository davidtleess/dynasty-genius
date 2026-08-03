# nflverse injuries post-live fixes — Codex review v1

**Date:** 2026-08-02  
**Lane:** Codex, independent integration review  
**Layer:** 1 (ingest)  
**Verdict:** **NOT CLEAR — 6 blocking rows, 2 material rows**

## What reconciles

The current live artifact is internally consistent. Read-only checks against
`app/data/nflverse_usage.db` and the ready-marker-selected Parquet independently found:

- 34,812 injury rows and 34,812 distinct `row_key` values.
- 28,744 `revisioned` rows and 6,068 `single_observation` rows.
- 2025 `season_type`: 5,783 `REG`, 285 `POST`, 0 null.
- All six injury capture rows are `ok`; the 2020–2025 row counts reconcile exactly to the table.
- The ready marker and Parquet both report 34,812 injury rows; `season` and `week` are `Int64`.
- Raw snapshots independently confirm two 16-column shapes: 2020–2024 carry
  `date_modified`; 2025 carries `season_type`. The five-coordinate key has two duplicate groups
  in 2024 and zero in 2025, matching the stated era evidence.
- The reported 84-pass nflverse slice and Ruff result reproduce: `84 passed, 4190 deselected`;
  `ruff check src app tests/contract/test_nflverse_injuries_red.py` is clean.

This is evidence that the manual production repair produced a coherent current artifact. It is
not evidence that the code will preserve that state on the next source or schema transition.

## Blocking findings

### B1 — the era resolver does not match an exact column set

`StreamEra.matches` checks only `requires` and `forbids`
(`src/dynasty_genius/nflverse_usage.py:184`), and `normalize_rows` takes the first match
(`:544`). An otherwise-valid 2025 row with `unexpected_provider_field` is accepted as
`single_observation`; the field is silently discarded. That directly contradicts the class and
error text's promise that an unrecognised column set refuses.

**Reproducer result:** `extra_column 1 preserved False era single_observation`.

Require exact equality with the declared era columns, require exactly one match, and lock both an
added-column refusal and an ambiguous-era refusal. Otherwise fix 4 recreates itself on the next
additive provider field.

### B2 — integer normalization does not govern the row key

The normalized values are written to `row` at `:574-588`, but populated-grain validation and
`_row_key` still read the original `record` at `:595-609`. Two semantically identical records,
one with `season/week = 2020.0/1.0` and one with `2020/1`, normalize to the same stored values yet
produce different keys and pass the duplicate gate.

**Reproducer result:** two rows accepted; stored coordinates are both `(2020, 1)`, while keys are
`season=2020.0|...|week=1.0|...` and `season=2020|...|week=1|...`.

Build blank-grain checks and the row key from the normalized row, and add this exact mixed-type
duplicate as a refusal test.

### B3 — schema-changing rows can still be skipped by the content hash

The disclosed defect reproduces exactly. `_rows_hash` covers only normalized rows (`:681-685`),
and `apply_season` returns `unchanged` solely on that digest (`:793-803`). In a temporary store:

1. insert rows that already carry `source_era`/`season_type` through an older projection that has
   no columns for them;
2. add those columns;
3. apply the identical normalized rows through the widened spec.

The second apply returns `unchanged`, and both new columns remain `NULL`. A manual production
`DELETE` is a one-time recovery, not a repair of the state machine.

The idempotence identity must include the persisted projection contract (at minimum ordered stored
columns plus declared dtypes/normalization version), and the contract needs the exact schema-widening
positive control. Same rows + different persisted projection must not be `unchanged`.

### B4 — the public schema version did not change

`SCHEMA_VERSION` remains `nflverse_usage.v3` (`:45`) even though the store and exports gained
`source_era` and `season_type`, row-key semantics became era-dependent, and raw/ready artifacts
with the old and new contracts are therefore indistinguishable by version. The live ready marker
and all six new raw envelopes confirm the changed artifact is still labelled v3.

This needs a version bump and the existing every-surface version lock rerun against it. The test
header is also now false: it says 16 columns before 2025 versus 17 in 2025 and that `season_type`
is deliberately absent (`tests/contract/test_nflverse_injuries_red.py:20-23`); the raw evidence
shows 16 versus 16, one column swapped for another. The old `season_type_is_not_declared` contract
at `:122-128` must be rewritten to describe era-local declaration rather than left green on the
default-era implementation detail.

### B5 — the schema transition is not reproducible from code

On an existing v3 injuries table, `UsageStore` now sees the two missing columns and refuses at
`src/dynasty_genius/nflverse_usage.py:767-776`. Production works only because two manual `ALTER
TABLE` statements and a manual delete/re-capture were performed outside the implementation. The
error tells the operator to “rebuild it from the raw snapshots,” but no raw-replay path performs
that rebuild.

Choose and test one operational contract before commit: a narrowly additive, versioned migration;
or an explicit rebuild command that actually replays the retained raw snapshots. The production
commands should be durable evidence, but they cannot be the only deployment mechanism.

### B6 — “declared at construction” still fails for an empty stream

`publish_export` uses an explicit schema only when rows exist; the empty branch is a zero-column
`pl.DataFrame()` (`:1039-1043`). A temporary empty injuries store publishes a Parquet with
`Schema()`, not the declared injury columns. That makes consumer schema depend on whether the
current table happens to be empty.

Construct from `spec.stored_columns` for both empty and populated streams, then apply declared
casts. Lock the empty Parquet's columns and numeric dtypes.

## Material findings

### M1 — wrong integer types are deferred past normalization

`bool` and nonnumeric text both fall through at `:576-581`. Focused probes show `week=True` and
`week="not-a-number"` are accepted by `normalize_rows` and enter its key. A later export cast will
refuse the text, but only after the SQLite season has been rewritten; the normalization contract
itself does not distinguish an integer from a non-integer. By contrast NaN, ±inf, and fractional
values refuse correctly.

Refuse bool and nonnumeric values with the same typed normalization error (unless null is explicitly
allowed), and test wrong-type plus non-finite rows at the normalization boundary.

### M2 — the new persistence test is another structural proxy

`test_every_era_column_has_a_home_in_the_table` (`tests/contract/test_nflverse_injuries_red.py:565`)
checks membership in `stored_columns`; it does not create a store, insert both eras, and read the
values back. The current live artifact proves today's values landed, but the durable test would not
catch a future insert/projection regression. Add a temporary-store round trip that asserts
`source_era`, `date_modified`, and `season_type` after storage and export.

## Falsification matrix

| Row | Result |
| :-- | :-- |
| valid nominal / live artifact | PASS; counts, keys, types, eras reconcile |
| boundary (2020 Float64, 2025 swapped column) | current live output PASS |
| missing required era marker | PASS; existing test refuses |
| null / blank grain | PASS from existing contract rows |
| wrong type | **FAIL**; bool and nonnumeric text accepted by normalization |
| malformed / additive shape | **FAIL**; unknown extra column accepted and dropped |
| duplicate / conflict | exact duplicate PASS; **semantic float/int duplicate FAIL** |
| empty collection/export | empty normalize is accepted; **empty export loses schema** |
| cross-component shape | current live store PASS; **schema hash + deploy transition FAIL** |
| numeric edge | NaN, ±inf, fractional refuse; bool/text gap remains |
| synthetic / override | year-shape mismatch is correctly resolved by shape, not year |

## Miss accounting

My prior offline CLEAR missed these live-era defects because I reviewed a single synthetic 2024
shape and the declared contract, not the archived multi-season source shapes through the real
capture → store → export boundary; I also accepted structural assertions where a schema transition
counterexample was required.

## Disposition

**NOT CLEAR.** Do not commit or push the four-fix body yet. The present production artifact is
coherent and need not be deleted or re-fetched for this review; the required work is to make the
transition and its guards reproducible, versioned, and non-vacuous.
