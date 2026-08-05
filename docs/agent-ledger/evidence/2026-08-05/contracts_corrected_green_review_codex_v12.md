# Contracts corrected GREEN review — Codex v12

Date: 2026-08-05  
Layer: 1 ingestion  
Target: uncommitted working tree at `HEAD=d645933`  
Disposition: **GREEN NOT CLEAR**

## Independent gates

- `pytest -q tests/contract/test_contracts_ingestion_red.py`: **59 passed**.
- `ruff check src app`: **passed**.
- `git diff --check`: **passed**.
- The 169-row NGS fixture normalizes with no `content_sha256`; its current `_rows_hash` is
  `da36dcc59ebb94c30a0c1f1f1cd672059871f2398e126db93ae688ea0210c2c4`, matching the
  reported legacy-shape digest. G2's implementation is accepted.
- The G6 retry-state helper now reads `nflverse_snapshot_capture`, and the projection-sensitivity
  assertion changes the persisted projection. G6's implementation/test correction is accepted.

Passing gates do not clear the change because required fresh-state boundaries remain untested and
four current behaviors contradict the ruled contracts.

## V12-1 — first-row missing schema does not use the ruled exact-shape refusal

`normalize_rows` performs the generic first-row missing-column check at
`src/dynasty_genius/nflverse_usage.py:1301` before the opt-in every-record exact check at line 1344.
A contracts fixture with `player` removed from record zero refuses as:

```text
nflverse_schema_drift: stream contracts season None is missing ['player'] ...
```

It does **not** name record index zero or the unexpected/missing sets. The same missing field on
record one reaches `nflverse_unexpected_columns` and does name `record 1`. The v11 ruling required
both first- and later-record missing controls to refuse by index and name. Either route the opted-in
spec through its exact checker first, or make the generic check satisfy the same diagnostic contract.

## V12-2 — G1-G5 corrective boundaries have no automated controls

The focused module still collects exactly 59 tests. Inspection and name/content searches show no
tests for:

- `refuse_unexpected_columns`, including first/later added and missing fields, `_bind`, existing
  defaults/hashes, and no-`source_era` projection;
- the pinned legacy seasonal `_rows_hash`;
- the snapshot raw JSON envelope and absence of `season`;
- snapshot-ledger `NOT NULL`/axis constraints or blank provenance;
- snapshot identity reconciliation in returned totals.

The existing `test_no_synthetic_season_is_invented` at
`tests/contract/test_contracts_ingestion_red.py:346` inspects only the parsed contracts table, not
the raw JSON. `test_totals_carry_the_snapshot_vocabulary` at line 1083 checks only `rows_total`.
`test_durable_coverage_records_named_snapshot_fields` at line 1094 checks a nominal ledger row, not
the DDL or refusal boundary. Only G6 was added to existing tests (lines 407-424 and 641-656).

The ad-hoc claims reproduce on the current source for nominal inputs, but the required controls must
be durable before this mechanism is committed.

## V12-3 — raw snapshot writer accepts contradictory and malformed axis shapes

`write_raw_snapshot` at `src/dynasty_genius/nflverse_usage.py:2215` treats any non-null `partition`
as authoritative and otherwise writes `season`, with no validation of the two legal shapes.
Controlled calls all succeeded:

1. `season=None, partition=None` wrote `"season": null`.
2. `season=2024` plus a snapshot partition silently discarded the real season field.
3. A snapshot partition containing `season=2024` wrote the synthetic season into the raw envelope.
4. `partition={"snapshot_id": "s2"}` wrote a context-less snapshot lacking `capture_axis` and
   `observed_at`.

The orchestrator's nominal snapshot call is now honest, but the raw-truth API remains fail-open.
Validate exactly one legal envelope before writing: seasonal means non-null season and no partition;
snapshot means null season and exactly the required nonblank snapshot context with
`capture_axis == "snapshot"` and no `season`. Separate writers are also acceptable if they enforce
the same boundary. Preserve the established seasonal envelope bytes.

## V12-4 — an existing unconstrained snapshot ledger is silently accepted

The fresh-table DDL at `src/dynasty_genius/nflverse_usage.py:1842-1853` now declares the ruled
`NOT NULL` fields and axis `CHECK`. But `_assert_schema` at lines 1919-1934 validates only column
names. `CREATE TABLE IF NOT EXISTS` therefore leaves a pre-existing same-column table with the old
all-nullable/no-check schema untouched, and `UsageStore(...)` accepts it.

A controlled database pre-created with every `_SNAPSHOT_CAPTURE_COLUMNS` name, the primary key,
and no constraints opened successfully. This is the exact partial-state path produced by the prior
GREEN draft. Verify the required `notnull` flags and axis check (or use an explicit versioned
migration/refusal) and add a control that pre-creates the malformed same-name table and requires
fail-closed behavior.

## V12-5 — `by_stream_snapshot` omits part of the promised census

`_totals` at `src/dynasty_genius/nflverse_usage.py:2995-3004` includes canonical/source-only/
conflict/unknown counts but omits `rows_not_canonically_identified`. On a controlled coverage block
of 49 source-only + 1 unknown, the top-level snapshot-prefixed total and
`snapshot_unresolved_by_stream` both report 50, while `by_stream_snapshot` has no reconciliation
field. This contradicts both the v11 precision ("the same census in `by_stream_snapshot`") and the
current GREEN report. Add the field and assert exact reconciliation in the focused contract.

## Accepted corrections and boundary

- G2 seasonal row/hash freeze is reproduced and accepted.
- G6 retry-ledger and projection-sensitivity corrections are accepted.
- The scoped G1 flag, contracts-only binding, absence of `source_era`, nominal snapshot raw
  envelope, fresh DDL, required `apply_snapshot` provenance, top-level snapshot identity totals,
  and unresolved inventory are directionally correct but do not override the blockers above.
- No implementation, fixture, product-store, commit, push, scheduler, consumer, or model changes
  were made by this review.
- Product landing remains unauthorized. After a fresh GREEN CLEAR, any landing must still capture
  all twelve prior streams plus contracts in one export and reconcile the prior artifacts and NGS
  consumers.
