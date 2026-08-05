# Contracts GREEN review — Codex v10

Date: 2026-08-05  
Layer: 1 ingestion  
Target: uncommitted worktree at `d645933`  
Disposition: **GREEN NOT CLEAR**

## Independent checks

- `git diff --check`: passed.
- `pytest -q tests/contract/test_contracts_ingestion_red.py`: **59 passed**.
- `ruff check src app`: passed.
- Controlled seasonal normalization probe: 169 NGS passing rows all acquired an unpersisted
  `content_sha256`; the current and pre-change-shape season digests differed.
- Controlled contracts probe: an added top-level source field was accepted, omitted from every
  normalized row, and left the complete content-digest set unchanged.
- Controlled snapshot capture: status `ok`, then the raw JSON, snapshot-ledger DDL, ledger coverage,
  and totals were inspected directly.

The focused suite is green, but it does not falsify the boundaries below.

## G1 — additive top-level source drift is silently accepted and discarded

`CONTRACTS` has no exact `StreamEra` or other exact-column policy
(`src/dynasty_genius/nflverse_usage.py:1114-1137`). Exact set equality in `normalize_rows` runs only
for `spec.eras`; the non-era path checks only missing columns and later projects the declared 25.

Positive control: add `new_upstream_contract_term="meaningful-new-value"` to every fixture row.
Normalization succeeds, the field is absent from all normalized rows, and the entire
`content_sha256` set is unchanged. That is silent data loss and contradicts the reduced gate's
schema requirement and the content identity's claim to cover the source contract.

Required: a per-stream exact top-level schema refusal, exercised for both an added and a missing
field, without silently widening any previously cleared stream. If closing this requires a new
mechanism or a new emitted `source_era` column, report that contract expansion before absorbing it.

## G2 — the claimed seasonal freeze is false at the idempotence boundary

`normalize_rows` assigns `content_sha256` to **every** stream at
`src/dynasty_genius/nflverse_usage.py:1430-1434`. Seasonal `stored_columns` correctly omit it, but
`apply_season` hashes the full normalized mappings through `_rows_hash(rows)` at lines 1907-1917.

Positive control on the real 169-row NGS fixture:

- all 169 normalized seasonal rows carried `content_sha256`;
- `content_sha256` was absent from `NGS_PASSING.stored_columns`;
- current digest: `0043bce56e6688a35059144422f1f391f2914d00b076384cc0157a8c0ebcda5a`;
- digest after removing only that new field:
  `03bc9424ae912bb2ef38049273cdcf834bae1247da5afc024c1f6c6a8738b1d1`.

Thus the next unchanged seasonal capture will read as changed and rewrite every affected partition.
The golden projection test cannot see this because the persisted column list is unchanged.

Required: compute row-content digests only on the snapshot axis (or otherwise preserve the exact
legacy seasonal hash input) and add a seasonal content-hash positive control, not only a projection
fingerprint assertion.

## G3 — the raw snapshot invents a season

The snapshot branch calls the seasonal raw writer with `season=observed_at` at
`src/dynasty_genius/nflverse_usage.py:2719-2725`. The writer serializes that argument under the
literal key `season` and into the filename at lines 2158-2185.

A successful controlled capture produced raw JSON with keys
`captured_at, records, rows, schema_version, season, stream`; `season` equalled the observation
timestamp, while `capture_axis`, `snapshot_id`, and `observed_at` were absent. This directly violates
the cleared no-synthetic-season rule even though the parsed table omits `season_ingested`.

Required: an honest snapshot raw envelope carrying the snapshot partition fields and no `season`,
while preserving seasonal raw artifacts byte-for-byte. Add a test that reads the raw JSON itself.

## G4 — the ruled snapshot ledger is not fail-closed, and raw provenance is optional

The v9 binding shape requires explicit `NOT NULL` columns and `capture_axis` exactly `snapshot`.
The DDL at `src/dynasty_genius/nflverse_usage.py:1805-1813` creates every column as unconstrained
`TEXT` and adds only the composite primary key. `PRAGMA table_info` reported `notnull=0` for every
column, and a direct insert of `capture_axis='seasonal'` with null time, coverage, content hash, raw
path/hash, and ingest time succeeded.

Separately, `apply_snapshot` defaults both `raw_sha256` and `raw_snapshot` to empty strings at lines
1956-1966. A direct call omitting both returned `inserted` and durably stored two empty provenance
values. A success-only observation must not exist without the provenance the reduced gate requires.

Required: implement the v9 DDL literally (including explicit nullability and an exact-axis check),
make raw provenance required/nonblank at the write boundary, and test the database constraints plus
the direct method boundary. `rows_total` may retain the v9 TEXT typing; this finding does not invent
a different type.

## G5 — snapshot identity/unresolved totals disappear

`_totals` separates snapshot row count but `by_stream_snapshot` carries only ID, time, and
`rows_total` (`src/dynasty_genius/nflverse_usage.py:2894-2935`). The established top-level identity
counters still sum seasonal blocks only.

Controlled snapshot result: the entry coverage contained 49 `source_only`, 1 `unknown`, and 50
`rows_not_canonically_identified`; the returned totals simultaneously reported zero for all three
and exposed no snapshot-unresolved vocabulary. Design v3 D3 explicitly required snapshot unresolved
vocabulary alongside the seasonal one.

Required: expose an honestly named snapshot identity census and unresolved inventory (including a
per-stream snapshot partition), and test exact reconciliation against the snapshot coverage. Do not
fold snapshots into the seasonal counters.

## G6 — two RED assurances still pass without observing what they claim

1. `_durable_state` says it captures the whole snapshot ledger, but line 416 queries the now-frozen
   seasonal `nflverse_capture` table. For snapshot-only tests that ledger is empty, so the retry
   preservation assertions at lines 420-516 cannot detect any mutation to
   `nflverse_snapshot_capture`. Redirect the helper and require byte-for-byte preservation of both
   snapshot rows and the actual snapshot ledger.
2. `test_the_snapshot_digest_is_distinct_from_every_row_digest` checks sensitivity to time, raw hash,
   and collapse count at lines 601-641, but never mutates the projection. The implementation does
   include `_projection_fingerprint(spec)` at source lines 1717-1720; the v9 obligation remains
   unprotected by RED. Add an independent projection-sensitivity case.

These are contract defects, not evidence that the current implementation is known to mutate the
ledger or omit projection. They block CLEAR because the named guarantees presently pass without
observing their actual state.

## Accepted evidence

The 59 focused tests, type/value reconciliation, strict nested JSON encoder, accumulation across two
distinct IDs, observed-at placement after fetch return, separate table selection, identity census,
and staging row counts are not disputed. They do not close G1-G6.

## Live-landing boundary after correction

No product landing is authorized by this review. When GREEN is eventually clear, a product capture
must carry all previously landed streams plus contracts in one export so the ready manifest cannot
silently remove existing files. Reconcile the prior twelve files, the three NGS consumer frames,
contracts totals/census, raw hash, snapshot ledger row, and terminal `ok` marker before commit.
