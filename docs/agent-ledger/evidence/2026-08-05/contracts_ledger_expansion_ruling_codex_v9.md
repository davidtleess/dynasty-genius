# Contracts snapshot-ledger expansion ruling — Codex v9

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **Use a separate snapshot ledger; keep `coverage_json`**

## Finding

The implementation stop was correct. The existing `nflverse_capture` table is structurally and
semantically seasonal:

- primary key: `stream_season`;
- partition column: `season`;
- `apply_season`, `record_failure`, `captures()`, `read_only_summary()` and export season metadata
  consume that shape;
- the live product store currently has 101 rows and exactly the nine existing columns;
- design v3 explicitly forbids putting `snapshot_id` into `season` or `stream_season`.

Adding nullable snapshot columns does not solve the primary-key lie. Using
`contracts:snapshot:<id>` in `stream_season` would directly violate the cleared design. Renaming the
shared key to `partition_key` would require a non-additive migration and broaden all twelve reviewed
seasonal streams.

## Binding ledger shape

Create a separate table named **`nflverse_snapshot_capture`** with:

1. `stream` TEXT NOT NULL
2. `snapshot_id` TEXT NOT NULL
3. `capture_axis` TEXT NOT NULL, exactly `snapshot`
4. `observed_at` TEXT NOT NULL
5. `rows_total` TEXT (matching the current store's SQLite typing convention)
6. `coverage_json` TEXT NOT NULL
7. `content_hash` TEXT NOT NULL — the snapshot-level idempotence digest
8. `raw_snapshot` TEXT NOT NULL
9. `raw_sha256` TEXT NOT NULL
10. `ingested_at` TEXT NOT NULL
11. primary key **`(stream, snapshot_id)`**

Do not add `season`, `stream_season`, `partition_key`, `status`, or `failure_reason`. A row in this
table is a successfully durable snapshot observation. Attempt/failure truth remains in the run
marker, as with the established last-good invariant; do not write a misleading failed observation
row.

The composite primary key is honest for future mixed runs containing more than one snapshot stream:
one run-level snapshot ID may legitimately identify observations for multiple streams.

## Existing seasonal state is frozen

- Do not rename `coverage_json`.
- Do not add `coverage` as a database column. `coverage` remains the decoded API/result name.
- Do not alter `_CAPTURE_COLUMNS`, `nflverse_capture`, `stream_season`, its primary key, seasonal
  writers, or seasonal readers.
- `UsageStore.captures()` remains seasonal-only.
- Add `UsageStore.snapshot_captures()` for the new table; it decodes `coverage_json` to `coverage`.
- `read_only_summary()` may add a separate `snapshot_captures` collection but must preserve the
  existing `captures` meaning and remain physically read-only.
- Export/manifest season inventory continues to derive only from seasonal captures. Any snapshot
  inventory is a separate named field, never synthetic season content.

Create the snapshot ledger only when the store is opened with at least one snapshot spec. This is a
new table, not a migration of the shared seasonal table.

## RED corrections authorized

Correct the RED rather than production schema:

- query `nflverse_snapshot_capture`, not `nflverse_capture`, for snapshot durable state;
- parse `coverage_json`, not a nonexistent `coverage` column;
- assert the existing seasonal ledger retains exactly its existing schema and receives no snapshot
  rows in a mixed run;
- keep all other cleared RED semantics unchanged.

This is a targeted response to the reported expansion, not a new broad review round.

## Existing digest obligation

The current in-progress `snapshot_idempotence_digest` description reports rows + coverage +
observed-at + raw hash. The cleared v3 contract also requires the persisted **projection** contract.
Include `_projection_fingerprint(spec)` in the snapshot digest. This is not a new expansion; it is a
previously cleared obligation. `raw_snapshot` path need not be hashed if `apply_snapshot` compares it
separately and refuses a same-ID mismatch, as the RED already requires.

After these targeted changes, rerun the focused contracts RED, the existing seasonal ingestion
contracts, full collection and Ruff. Report any further contract expansion before absorbing it.
