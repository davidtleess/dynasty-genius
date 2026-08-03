# nflverse schema-era tooling — Codex review v1

Date: 2026-08-02  
Layer: 1 (ingest/source contracts)  
Verdict: **NOT CLEAR — five blocking rows and one material provenance row**

Reviewed the newly added generator, fixture bundle, replay contract, and live preflight. Codex did
not edit Claude-owned files.

## T1 — dtype profile is neither whole-snapshot nor cumulative (blocking)

`build_nflverse_era_fixtures.build()` says it profiles every snapshot of a shape, but on each file
it assigns:

```python
entry["profile"] = _column_profile(entry["records"] + records[:200])
```

`entry["records"]` is the first five rows of the first snapshot. Each later assignment therefore
forgets every intervening snapshot, and every snapshot is sampled to 200 rows despite the docstring
saying "across the whole snapshot."

Positive counterexample: three same-shape snapshots carried `a=int`, then `a=str`, then `a=int`.
The generated profile was `{'a': ['int']}`; the middle-only string kind disappeared.

Accumulate the union across every snapshot and every row (or rename/disclose a sampling contract,
which would be weaker than the authorized dtype fingerprint and would not justify the current
claim).

## T2 — the live preflight cannot detect season-specific dtype drift (blocking)

The fixture merges 2020–2024 injuries into one allowed kind set: `season/week = {float, int}`. The
preflight then accepts any observed subset of that era-wide set. This avoids the 2024 false alarm,
but introduces the inverse false negative:

- 2020 changing from float to int would pass because int appeared in later seasons.
- 2024 changing from int to float would pass because float appeared in 2020.

That is the exact cross-season dtype class this tooling is meant to guard. Pin dtype kinds by
season (or an equivalent season-specific source-shape identity) and compare the requested season to
its own allowed profile; retain an era-level union only as descriptive metadata.

## T3 — "every archived shape through capture → store → export" is false (blocking)

`test_each_archived_shape_normalizes` sends all six shapes only through `normalize_rows`. The only
actual `run_usage_capture` / SQLite / Parquet replay covers the two injury eras. The three NGS
streams and snap counts never traverse store/export from these archived fixtures.

The module title and contract explicitly claim every archived real shape through the actual path.
Parameterize the end-to-end replay over every pinned shape, including stored row conservation and
exported schema/row conservation.

## T4 — the real replay omits the dtype witness it claims to exercise (blocking)

For a multi-season shape, `fixture_rows` is fixed from the first snapshot only. The 2020–2024
injury fixture therefore contains 2020 float rows only; the metadata mentions later ints, but no
archived int row is replayed. Synthetic tests elsewhere cover ints, but this harness's earned claim
is archived-real replay.

Choose minimal witness rows that collectively realize every pinned season-specific dtype variant,
or carry per-season fixture slices and replay each one.

## T5 — live preflight covers only two of five streams and has no durable contract (blocking)

The pinned bundle includes injuries, snap counts, and all three NGS streams. The preflight loader
map wires only `injuries` and `snap_counts`; each NGS stream returns "no preflight loader wired"
despite the module saying "one small fetch per stream." Reuse the bound stream loaders/kwargs or
wire all five explicitly.

No test imports or executes `nflverse_fingerprint_preflight.py`. The reported injected-drift check
is manual session evidence and can disappear while the suite stays green. Add offline injected
tests for exact match, added/removed column, season-specific dtype change, unknown stream, empty
response, and no-write behavior. The live call remains corroboration, not the only guard.

## T6 — archived source provenance is not pinned (material)

The fixture records a generic source directory, seasons, and row counts, but no content hash for
the raw envelope(s) that produced each profile/fixture slice. A later machine cannot determine
which archived bytes were the source of record or distinguish a rewritten raw file with the same
season/count.

Record source snapshot SHA-256 by stream/season (without absolute paths) and make `--check` verify
those hashes when the archives are present. This matches the authoritative-provider bundle's core
property: the contract is pinned to named bytes, not merely to a mutable directory.

## Checks that do hold

- The injury column swap is represented as two distinct 16-column shapes.
- Fixture payload size is bounded and the source is public nflverse data.
- The current live preflight was exercised against 2020/2024/2025 and refused an injected new kind.
- The first exact-equality dtype implementation correctly self-falsified on a valid 2024 season;
  the issue is that the replacement chose an era union instead of a season-specific profile.

Mutation-pilot results were still in flight during this review and are not covered by this verdict.
