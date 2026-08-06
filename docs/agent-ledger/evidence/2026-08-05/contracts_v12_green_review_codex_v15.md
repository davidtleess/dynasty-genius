# Contracts V12 GREEN review — Codex v15

Date: 2026-08-05  
Layer: 1 ingestion  
Target: uncommitted working tree requested in `contracts_v12_green_claude_v14.md`  
Disposition: **GREEN NOT CLEAR**

## Target pinned

- `src/dynasty_genius/nflverse_usage.py` sha256
  `272a2290ad6b1af92847cfefbb8b78ec93479e7b94919e236b6f10b663ba7d57`
- `tests/contract/test_contracts_ingestion_red.py` sha256
  `9742250bec3b593df2971287ae5fa9c6828f3d5ff27fbe2000844472d3b65dbb`
- Implementer evidence sha256
  `6dc34b54fa7945f3047edaf63f27da82d19d276bc42569073b64668ece8bd32f`

The requested file-scope statement matched the repository at review start: three tracked modified
files (`nflverse_usage.py`, the contracts contract, and today's ledger) plus the one untracked
implementer evidence artifact. No fixture, product store, export, script, config, scheduler,
consumer, or model file was changed.

## Independent gates

- Contracts contract: **82 passed**.
- Step-1 focused ingestion slice named on the board: **147 passed**.
- `.venv/bin/ruff check src app`: **passed**.
- `git diff --check`: **passed**.
- Controlled probes exercised snapshot-envelope metadata collisions and SQLite constraint
  discrimination; their results are recorded below.

Passing gates do not clear the change because one current runtime path violates the exact-envelope
contract and the load-bearing V12-2 controls do not independently prove several guarantees they
claim.

## F1 — snapshot partitions can overwrite the raw artifact's authoritative metadata

`write_raw_snapshot` validates that a snapshot partition contains the three required keys and no
`season`, but it does **not** require the partition key set to equal those three keys. At
`src/dynasty_genius/nflverse_usage.py:2366`, `metadata.update(partition)` lets every extra key replace
the writer's authoritative values.

A controlled call supplied the required snapshot context plus:

```text
stream=spoofed_stream
rows=999
captured_at=spoofed_time
schema_version=spoofed_schema
extra_context=accepted
```

The function returned successfully and the written artifact reported all five supplied values,
even though the real call used stream `contracts`, one record, the real capture timestamp, and the
module schema version. Thus the artifact can lie about its source, count, time, and schema while
passing every new test. This contradicts V12-3's ruled shape: exactly one legal snapshot envelope,
with exactly the required snapshot context, validated before writing.

**Required correction:** require the snapshot partition key set to be exactly
`{capture_axis, snapshot_id, observed_at}` before creating the raw directory/file. Add durable
controls for an arbitrary extra key and for collisions with the writer-owned metadata keys; every
case must refuse and write no file. Preserve the seasonal byte freeze.

## F2 — the new axis-CHECK positive control passes for the wrong reason

`test_a_freshly_created_snapshot_ledger_enforces_its_constraints` inserts only `stream`,
`snapshot_id`, and `capture_axis='seasonal'`. Five other required columns are `NOT NULL`, so the
expected `sqlite3.IntegrityError` does not demonstrate that the axis CHECK fired.

The independent discriminator used a table with all eight required `NOT NULL` declarations but **no
axis CHECK**:

- the test's three-column insertion still raised `IntegrityError`;
- the same `capture_axis='seasonal'` insertion with every required column populated succeeded.

Therefore the current control would remain green if the runtime axis CHECK vanished.

**Required correction:** populate every required non-axis field with a valid nonblank value in the
negative INSERT so the axis CHECK is the only possible failure.

## F3 — V12-2's durable matrix still does not isolate all v11 guarantees

The implementation is directionally correct, but several named controls remain coupled or absent:

1. The pre-existing bad-ledger test removes both guarantee classes at once (nullable required
   columns **and** no axis CHECK), while the fresh-table control has both. An implementation that
   verifies only NOT NULL or only the CHECK can pass both tests. Add two independent partial-state
   controls: all required columns NOT NULL with no CHECK, and a valid CHECK with at least one
   required column nullable.
2. The implementer evidence says the partially constrained no-CHECK case was an ad-hoc probe. It is
   not durable coverage. The v11 ruling explicitly required durable DDL constraints and blank
   provenance controls. Add a parameterized `apply_snapshot` control for blank `snapshot_id`,
   `observed_at`, `raw_sha256`, and `raw_snapshot` with every other input valid.
3. The four V12-1 diagnostic tests assert the error family, record index, and offending field, but
   do not assert both named sets. A missing-field diagnostic can omit `unexpected []`, or an
   added-field diagnostic can omit `missing []`, and the controls still pass. Pin both labels and
   both exact sets for first and later rows, as v11 required.
4. `test_the_seasonal_raw_envelope_is_byte_stable` parses JSON and compares keys/values; it does not
   compare bytes. Reformatting or reordering the established artifact passes a test named
   byte-stable. Pin the exact expected bytes (or an equivalent independent baseline-byte oracle),
   while retaining the parsed semantic assertions.

These are bounded control repairs, not a request to reopen the contracts design or expand the
production mechanism beyond the exact-envelope fix in F1.

## Accepted portions

- **V12-1 implementation ordering:** accepted. The exact check moved once, before the generic
  first-row check and exclusion/collapse. The opt-in flag remains contracts-only; the other twelve
  specs remain false. The 147-test prior-ingestion slice passed.
- **V12-3 seasonal integer handling:** accepted in principle. Python `int` behavior is unchanged;
  `numpy.int64` normalizes to the same JSON number; float/string/bool refuse. Current seasonal
  callers pass Python integers. The remaining defect is the snapshot partition allow-list in F1.
- **V12-4 implementation:** the constructor verifies required-column `notnull` flags and the axis
  CHECK and refuses rather than migrating. The live-store absence claim was not needed for this
  verdict. The blocker is durable discrimination, not a demand for migration.
- **V12-5 implementation/control:** accepted. One shared census vocabulary drives the seasonal
  totals, snapshot totals, and `by_stream_snapshot`; the control proves a nonzero unresolved
  population and exact reconciliation.
- **Boundaries:** contracts remains `substrate_only`; no landing, capture, export, scheduler,
  consumer, model/feature use, commit, or push is cleared. H2 QB rushing remains a registered
  hypothesis **UNDER TEST** with no result.

## Next review

Close F1-F3 in the same working tree and route a narrow fresh GREEN. Re-run the 82-test contracts
module plus the 147-test prior-ingestion slice and Ruff. The next review can remain focused on the
snapshot partition allow-list and the repaired V12-2 controls; no broad redesign is requested.
