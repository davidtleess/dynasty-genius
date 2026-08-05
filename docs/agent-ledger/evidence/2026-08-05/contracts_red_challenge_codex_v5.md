# Contracts revised RED challenge — Codex v5

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **NOT CLEAR for GREEN**

## Independent execution

- Focused RED: 48 collected, 45 failed, 3 passed, zero collection errors.
- Full tree: 4,621 collected, zero collection errors.
- `uvx ruff check` on the revised test and generator: pass.
- Revised strict generator `--check`, rerun against the live source: `ALL ARTIFACTS MATCH SOURCE`.

R10's generator correction is accepted: `default=str` is gone, strict serialization is used, and
the fixture remains byte-stable. The following test defects remain.

## S1 — R1 now has a demonstrably non-unique comparison key

`tests/contract/test_contracts_ingestion_red.py:725-733` calls a six-field tuple a stable natural
identifier and uses `setdefault`. It is not unique even in the 195-row fixture. Independent census:

- 192 six-field keys for 195 rows;
- one key has two **different** source rows:
  `(30, 2016, "Bears", "C", 0.965, 0.965)`;
- the cleared nine-field candidate has zero differing-payload collisions in the fixture.

Therefore a correct implementation can be compared with the wrong source `cols` payload and fail.
Pair exact-unique source and normalized rows by an independently computed canonical full-source
digest, not a lossy business-key proxy.

## S2 — R2 still does not test all 25 columns or their values

Lines 182-200 assert dtypes/non-null counts only for six integers, seven floats, one Boolean and
`cols`: 15 columns. The ten declared string columns have neither dtype nor completeness checks.
No column has exact value reconciliation; replacing every non-null value with another non-null value
passes. The test name and disposition claim all 25 columns, but the assertions do not.

Pin all ten strings as `Utf8` and compare the complete normalized/emitted source projection by a
canonical row multiset or exact per-column values, not only non-null counts. This also must prove the
emitted `year_signed == 0` and null `cols` outcomes rather than only their normalized forms.

## S3 — R3's recomputation is not independent

Lines 460-471 compute both the implementation digest and the expected digest using the production
module's `row_content_digest`. The same incorrect inclusion/exclusion/canonicalization on both sides
passes. Only 25 rows are sampled, and the requested `cols`-only mutation falsifier is absent.

Compute the expected SHA-256 in test code from the pinned 25 source columns, strict canonical JSON,
and the cleared exclusion list; assert all rows, and prove a `cols`-only payload change changes the
digest. The suite still never asserts `row_key == snapshot_id + content_sha256` or observes the
separate snapshot-level idempotence digest.

## S4 — R4 still inspects only three row fields

`_durable_state` at lines 352-358 reads only `snapshot_id`, `observed_at`, and `content_sha256` from
`contracts`. It cannot detect a retry rewriting `ingested_at`, raw path/hash, coverage counters,
projection contract, snapshot-level digest, or durable snapshot metadata. Those are exactly the
immutable facts the v3 retry contract names.

Snapshot-level durable metadata must be queryable and included in the before/after comparison for
the no-op and every refusal case. A three-column row projection is not proof that the first success
was preserved.

## S5 — R5 still permits an argument to reach the zero-argument loader

Lines 533-538 assert positional args are empty and only that the plural key `seasons` is absent.
`spy(season=None)` passes, although `load_contracts()` takes no arguments and the design requires a
zero-argument call. Assert `kwargs == {}`.

## S6 — R7's supposedly valid snapshot spec violates D4-7

`_valid_snapshot_kwargs` at lines 541-548 supplies `grain=("otc_id",)`. Design v3 D4-7 says the
snapshot-content path refuses seasonal grain/nullability settings; its row identity is the derived
content digest and row key, not a source grain. Because the control bakes in a grain, the refusal
matrix ratifies the opposite contract.

Start from a genuinely valid snapshot spec with no seasonal grain setting and separately assert
that adding source `grain`, populated-grain enforcement, or nullable-grain settings refuses. Pin the
actual `CONTRACTS` spec to the same rule.

## S7 — required snapshot fields and timing are not proved on the contracts artifact

Design v3 D4-2/D4-5 requires fetch-boundary `observed_at` and stored **and emitted**
`content_sha256`, `snapshot_id`, and `observed_at`. The suite reads these fields from the database or
unresolved artifact, but never asserts all three on `contracts.parquet`, never asserts the composite
row key, and never controls time around fetch to prove `observed_at` is stamped after return rather
than at run start.

The v3 honest vocabulary also names `by_stream_snapshot`, durable coverage, failure records and
captured-before-failure state. No test mentions `by_stream_snapshot` or inspects snapshot partition
fields in failure/durable coverage records.

## S8 — R8's content and recovery assertions remain proxies

- Mixed run, lines 612-639: correct fetch arguments and row count are asserted, but not seasonal
  content. Replacing every seasonal value while preserving count passes. Compare a seasonal-only
  capture with the mixed capture by exact normalized/emitted content hash.
- Empty snapshot, lines 642-660: the supposedly correctly typed empty Parquet checks only the six
  integer fields. The other 19 source columns and snapshot metadata can be wrongly typed/missing.
- Export failure/recovery, lines 663-692: only marker bytes/status are checked. Recovery may drop
  the first snapshot, retain a corrupt partial snapshot, or publish the wrong number/content of
  observations and still pass. Assert the exact durable and emitted snapshot IDs, per-snapshot row
  counts/content hashes, coverage, and terminal failure/recovery state.

## S9 — R9 closes snapshot context but not the seasonal half of D2

Lines 253-271 correctly require non-null exact snapshot context for snapshot unresolved rows. But
design v3 D2 also requires seasonal unresolved rows to retain season in the mixed artifact. The mixed
test never inspects `unresolved_identity.parquet`; that half remains untested.

## Accepted corrections

- R6 now correctly requires `season_ingested` to be absent.
- The strict generator and Polars-Series/non-JSON positive controls close the original R10 defect.
- Snapshot unresolved non-null/exact context closes the snapshot half of R9.
- Added provenance mutations, changed-row case, collision falsifier, default-fetch route, isolated
  constructor mutations, cross-route calls, empty/export-failure cases and mixed-axis arguments are
  directionally correct, subject to S4-S8 above.

No GREEN, commit, live landing or push is cleared by this disposition.
