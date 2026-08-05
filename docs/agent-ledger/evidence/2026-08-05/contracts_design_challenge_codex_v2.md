# Contracts stream design v2 challenge — Codex

Date: 2026-08-05

Reviewed artifact: `contracts_design_note_claude_v2.md`

Disposition: **DESIGN NOT CLEAR FOR RED**. David's accumulation/weekly ruling, the digest exclusion
list, strict JSON contract, and 25-column type pin are accepted. The remaining blockers are confined
to snapshot-axis accounting and artifact semantics; fix them in v3 before RED.

## Accepted

- David ruled: accumulate from capture one, weekly manual cadence, indefinite retention, no
  scheduler and no pruning authority.
- `content_sha256` includes every canonical normalized source column and correctly excludes only
  observation metadata (`snapshot_id`, `observed_at`) and derived fields
  (`dg_player_id`, `identity_status`, `row_key`; the digest itself is necessarily excluded).
- Row key `(snapshot_id, content_sha256)` is the correct accumulated observation identity.
- Strict JSON and nested-list invariants are sufficient as written.
- The six integer / seven float / one Boolean / ten string / one JSON output contract is correct.

## D1 — the identity count is attached to the wrong stage

Lines 78-79 say all **4,219** null-`gsis_id` source rows become `unknown` rows in the unresolved
artifact. Exact duplicate collapse happens first, so that is false for emitted/stored data.

Independent live census:

```text
source rows                    51,808
source null gsis_id             4,219
exact-unique stored rows        48,492
stored null gsis_id / unknown    4,098
null-id excess copies collapsed    121
stored canonical_resolved       32,198
stored source_only              12,196
stored unresolved total         16,294
```

The first snapshot's unresolved artifact is **16,294**, not 4,219: `source_only` is unresolved too.
Coverage must reconcile `32,198 + 12,196 + 4,098 = 48,492`, separately from
`48,492 + 3,316 collapsed = 51,808 source rows`.

## D2 — unresolved identity behavior cannot remain unchanged

The current publisher emits only `season_ingested` as identity context
(`nflverse_usage.py:1953-1975`). Snapshot rows deliberately have no season. Across weekly vintages,
repeated unresolved contracts would therefore be indistinguishable in the review artifact.

The accumulated unresolved artifact must carry `capture_axis`, `snapshot_id`, and `observed_at` for
snapshot rows while preserving `season` for seasonal rows. Its counts are cumulative across every
stored snapshot; the per-run coverage block is for the one snapshot captured in that run.

## D3 — “counts it once” must not mean “one stream-season”

Current `_totals` names every coverage block a `stream_season` and requires `season`
(`nflverse_usage.py:2325-2355`). Counting the snapshot there would reintroduce a synthetic season in
the status surface after correctly removing it from the data surface.

Keep existing seasonal keys unchanged and add explicit snapshot vocabulary, at minimum:

- `stream_seasons` counts only seasonal partitions;
- `stream_snapshots` counts snapshot partitions;
- `by_stream_snapshot` and `stream_snapshots_with_unresolved` key by snapshot ID;
- snapshot results/failure/captured-before-failure records use `snapshot_id` and `observed_at`, never
  a value stuffed into `season` or the existing `stream_season` durable key.

The durable capture/coverage store must likewise use honest snapshot partition fields or a separate
snapshot-capture table. `season=snapshot_id` is forbidden even if it is mechanically convenient.

## D4 — finish the axis/key fail-closed matrix

Pin these constructor and outcome combinations before RED:

- `snapshot_id` is observation-unique (use the run ID or an equally explicit run-unique ID), never
  derived from content; `observed_at` is recorded immediately after the loader returns.
- Two weekly captures with identical source content create **two** snapshots and two rows per
  distinct content digest; observation at a later time is new data even when values are unchanged.
- A retry with the same snapshot ID is idempotent/refuses overwrite; a new run ID is a new
  observation.
- `content_sha256`, `snapshot_id`, and `observed_at` are stored and emitted columns; snapshot tables
  do not carry `season_ingested`.
- A snapshot spec cannot silently carry seasonal key policy. If snapshot axis implies content keys,
  require empty declared grain/nullable-grain policy and refuse contradictory populated-grain
  settings; require exact-duplicate collapse for this contracts spec.
- Refuse snapshot specs with `min_season`, a `seasons` loader kwarg, unknown axis, or routing through
  the seasonal path; refuse a seasonal spec routed through snapshot logic. `_bind` must preserve the
  axis.
- Mixed runs, snapshot-only runs with an empty requested-season list, empty source snapshots,
  snapshot failure, export failure, and later recovery all retain honest partition/status records
  and prior-ready behavior.
- Hash collision refusal must compare canonical payloads, not merely notice duplicate digests; test
  it by substituting a constant digest for two unequal rows.

## D5 — state parsed and raw growth separately

Lines 20-22 use the raw 51,808 rows as parsed store growth. Exact collapse stores 48,492 rows per
current snapshot. At 52 captures/year that is approximately **2,521,584 parsed rows/year**, while raw
snapshots preserve approximately **2,694,016 source rows/year** at the current volume. Both are
approximate because the source already drifted during the session, but the distinction should be
stated.

## RED gate after v3

Once v3 corrects the identity census and makes the snapshot partition visible in store, status,
export, and unresolved identity, the RED may open. The RED should exercise two accumulated identical
snapshots, one changed snapshot, exact-collapse reconciliation, all snapshot/season totals, no
synthetic season anywhere, empty/failure/recovery paths, strict JSON, typed Parquet, and complete
non-regression of every existing seasonal stream.
