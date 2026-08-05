# Contracts RED adversarial challenge — Codex v4

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **NOT CLEAR for GREEN**

## Independent execution

- `.venv/bin/python3.14 -m pytest -q tests/contract/test_contracts_ingestion_red.py`:
  33 collected, 30 failed, 3 passed, zero collection errors. The failures reproduce the absent
  implementation rather than a collection defect.
- `ruff check tests/contract/test_contracts_ingestion_red.py
  docs/agent-ledger/evidence/2026-08-05/build_contracts_fixture_claude_v1.py`: pass.
- Fixture generator `--check`, rerun with network access: `ALL ARTIFACTS MATCH SOURCE`.

The measured fixture basis is accepted. The RED is not yet adequate because the following tests
can pass while the cleared v3 contract is violated.

## R1 — the claimed deep JSON round-trip does not compare source and result

`tests/contract/test_contracts_ingestion_red.py:467` builds `by_key` but never uses it. The loop
only proves that stored JSON parses, the first element has 13 keys, and the final year is `Total`.
It passes if middle elements are reordered, values change, or numeric/null types are stringified.

Required correction: independently canonicalize the fixture's exact-unique source rows and deep,
type-sensitive compare every non-null `cols` structure with the parsed normalized/stored value.

## R2 — all 25 emitted types are untested

`test_all_twenty_five_columns_are_type_pinned` at line 156 checks declarations only. No test reads
the published `contracts.parquet`. It therefore cannot catch the depth-charts class of defect where
declarations are correct but SQLite/publisher emits strings.

Required correction: read the emitted Parquet and pin six `Int64`, seven `Float64`, one `Boolean`,
ten strings and one JSON string; reconcile per-column non-null counts/values with the source after
collapse, including literal `year_signed == 0` and SQL NULL for null `cols`.

## R3 — neither digest is proved to have the cleared meaning

`test_the_row_digest_is_separate_from_the_snapshot_digest` at line 355 never observes a snapshot
digest and never independently recomputes a row digest. Random unique 64-character strings pass.
The two-run accumulation test at line 276 also does not compare the `content_sha256` sets across
snapshots, so an implementation that wrongly hashes `snapshot_id` or `observed_at` into row content
passes.

Required correction: independently compute SHA-256 over the canonical 25 source columns, assert
exact equality, assert a `cols`-only payload change changes it, prove identical content has identical
row-digest sets across distinct snapshots, and inspect a distinct snapshot-level digest that changes
when coverage/provenance changes.

## R4 — retry provenance and non-rewrite are prose, not assertions

The `apply_snapshot` calls at lines 296-352 carry no raw hash/provenance, although the docstring
claims it must match. The unchanged test checks only the returned word; an implementation may
rewrite the stored observation and return `unchanged`. Refusal tests do not verify the original
success survives. There is no same-ID changed-row-payload case; the constant-digest collision test
is a different boundary.

Required correction: make required provenance part of the exercised call; test same ID/different
raw hash and same ID/different row payload refuse; after every retry/refusal inspect durable rows,
observed-at, coverage/digest/provenance and original ingest metadata to prove no rewrite.

## R5 — the original seasonless-loader failure boundary is not exercised

`test_a_seasons_kwarg_never_reaches_a_snapshot_loader` at line 382 passes a custom `fetch`, so it
never reaches the default fetcher that historically called every loader with `seasons=[season]`.
The production `load_contracts()` binding could still receive a forbidden keyword and this test
would pass.

Required correction: run the default-fetch path with a bound spy loader and assert exactly one call
with no positional/keyword season argument.

## R6 — the no-synthetic-season test requires the forbidden column

At lines 252-256 the test first reads table columns and then executes `SELECT season_ingested`.
That requires the snapshot table to contain `season_ingested`, contradicting the cleared design
that snapshot partitions do not carry a synthetic seasonal field.

Required correction: assert `season_ingested` is absent from the snapshot table and export.

## R7 — fail-closed cases are confounded and incomplete

The snapshot-plus-`min_season` constructor at line 405 also supplies seasonal `grain=("a",)`, so it
may raise for the wrong contradiction; the broad regex still passes. There are no isolated tests for
snapshot seasonal grain/nullability settings, `loader_kwargs` containing seasons, or cross-routing a
seasonal spec through the snapshot path and vice versa.

Required correction: start from one valid snapshot helper and mutate exactly one prohibited field
per test with a precise error; exercise both wrong execution routes.

## R8 — empty, mixed, failure and recovery contracts are under-asserted

- Line 421 proves only returned zero counters, not a durable zero-row snapshot observation with
  ID/time/raw hash/coverage nor a typed empty Parquet.
- Line 429 proves only totals; it can corrupt the seasonal rows/artifact and pass. Compare a
  representative seasonal-only capture with a mixed capture by count and content hash, and pin the
  fetch arguments for both axes.
- Line 448 covers fetch failure only. v3 explicitly required an export-stage failure and recovery.
  Fail inside the real publisher after work begins, prove the prior ready snapshot remains intact,
  then prove a clean recovery produces honest accumulated state.

## R9 — unresolved context may be entirely null

`test_unresolved_snapshot_rows_carry_snapshot_context` at line 216 checks column presence and only
the `capture_axis` value. Null or mixed `snapshot_id`/`observed_at` values pass.

Required correction: require non-null values, exactly the current result ID/time for every snapshot
unresolved row, and preserve seasonal partition context for seasonal rows in a mixed artifact.

## R10 — the measured Polars-Series encoder boundary is not exercised, and the generator hides it

All fixture values enter normalization as Python lists. No positive control supplies the Polars
`Series` value that motivated the explicit conversion contract. Add that positive path and compare
its exact order/types after encoding.

Separately, `build_contracts_fixture_claude_v1.py:57`, `:68`, and `:123` use `default=str`. That is
the fallback coercion the design explicitly banned and can make `--check` silently normalize an
upstream type drift instead of refusing. Remove `default=str`; use strict serialization with
`allow_nan=False` after explicit plain-value conversion.

## Accepted portions

Collection discipline, current RED counts, fixture/live-source freshness, post-collapse census
reconciliation, unresolved-total vocabulary, distinct-run accumulation count, coverage-sensitive
collapse falsifier, literal collision refusal, empty-season snapshot invocation, binding/default
axis declarations, and the consumer-boundary scan are directionally sound. This disposition is a
contract challenge only; it does not authorize GREEN, commit, live landing or push.
