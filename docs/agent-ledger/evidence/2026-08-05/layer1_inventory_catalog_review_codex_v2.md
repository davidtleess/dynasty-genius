# Layer 1 Data Inventory Catalog — Codex adversarial review v2

Date: 2026-08-05
Layer: Layer 1 data foundation
Artifact reviewed: `docs/layer-1-data-inventory-catalog.md`
Reviewed SHA-256: `37932426a0f0ed864e51abd3be1274e504aed35d92334ca354822ca4516ea689`
Sections reviewed: §2 sources, §3 ingestion streams, §4 refresh frequencies
Verdict: **NOT CLEAR for phase B. Seven findings.**

## Dataset and intended grain

David's catalog must support a checked inventory of sources, ingestion streams, refresh frequencies,
schemas, Player 360 fields, semantic metrics, and remaining ingestion gaps. The load-bearing grains
are therefore different entities: external source, source stream, raw/normalized table, capture
ledger, identity bridge, scheduled producer/consumer job, schema field/era, Player 360 field, and
semantic metric. A count or status is trustworthy only at its declared grain.

## Checks performed

- Pinned and read the complete 220-line catalog.
- Enumerated every table in `app/data/nflverse_usage.db`, `playerprofiler.db`,
  `fc_forward_capture.db`, `fc_snapshots.db`, `league_transactions.db`,
  `model_forward_capture.db`, and `market_divergence_history.db` with SQLite read-only mode.
- Counted every table separately instead of summing first.
- Grouped `fc_snapshots` by `source` and date range.
- Compared the catalog against all 20 `SOURCE_REGISTRY` definitions.
- Compared §3 against the 13 `build_streams()` specs at `2a42759`.
- Searched every production Python/script/LaunchAgent caller for the 13 nflverse tables/loaders and
  `run_usage_capture`.
- Read `load_nextgen_from_export`, `run_feature_refresh.py`, the eight LaunchAgent definitions,
  `app/config/report_freshness.json`, Gemini's transcript clarification, and the current backup
  marker/log.

## F1 — source/stream enumeration is materially incomplete

**Severity: Critical for catalog completion. Confidence: high.**

The progress checklist marks Sources and Ingestion Streams `[x]` enumerated, but Table B contains
only the 13 canonical nflverse specs plus `ff_rankings`. It contains no stream rows for:

- PlayerProfiler's player-season, medical, weekly roster, gamelog, advanced-PBP play/slot, capture,
  and identity tables;
- PFF's seven report families/manual ingest paths;
- CFBD's provider payload families and curated table;
- FantasyCalc forward raw/joinable capture and legacy native/archive series;
- Sleeper league snapshot, transaction, and movement streams;
- direct production nflreadpy loads in `run_feature_refresh.py` (`player_stats`, `rosters`,
  `snap_counts`, `pbp`, `participation`);
- validation/context adapters represented by `nflreadpy_qb_context` and
  `nflreadpy_qb_validation`.

Table A has nine rows while the machine registry alone has 20 definitions, and the prior discovery
inventory contains additional active, fixture-only, deferred, prohibited, enterprise, and absent
sources. §5 admits candidate external sources are not enumerated. Therefore §1 A/B cannot be checked.

**Risk:** downstream schema, Player 360, metric, and source-gap inventories would inherit an
incomplete universe and could be internally perfect while omitting production data paths.

**Required remediation:** define the inventory universe explicitly, enumerate every source and every
concrete loader/export stream, then mark deferred/prohibited/fixture-only rows rather than omitting
them. Set §1 A/B back to partial until independently verified.

## F2 — Table A violates its own source grain

**Severity: High. Confidence: high.**

- A7 DynastyProcess archive and A9 `ff_rankings` are the same external source family. Under R1,
  DynastyProcess is one source with separate archive/latest/weekly stream rows; `ff_rankings` is not
  a second source.
- A5 and A6 split FantasyCalc by store, while A6 itself combines two distinct source families.
  `fc_snapshots` measures exactly 6,790 rows from `dp_archive` (2,185; 2021-09-08 through
  2024-09-08) and `fc_native` (4,605; 2026-06-12 through 2026-06-24). A row whose provider is
  `mixed` cannot be a source entity.
- A8 is labelled Sleeper league/roster/universe but points only to
  `league_transactions.db`; league/roster/universe snapshot files live elsewhere and are not
  represented by that store or its three tables.

**Risk:** source-level licence, cadence, freshness, and retention fields become properties of a
store/loader rather than the provider, causing exactly the cross-family conflation R1 exists to
prevent.

**Required remediation:** normalize source, stream, and store into separate IDs with explicit
parent keys. Stores may contain multiple source families but must not become source rows.

## F3 — headline row totals mix grains and double-count representations

**Severity: High. Confidence: high.**

The 101-row discrepancy is resolved exactly:

| Store | Catalog total | Measured decomposition | Safe interpretation |
| :-- | --: | :-- | :-- |
| nflverse | 1,491,792 | 1,491,691 rows across 12 source-stream tables + 101 `nflverse_capture` ledger rows | 1,491,691 stream rows; 101 capture events |
| PlayerProfiler | 1,523,362 | 1,520,009 rows across six normalized source-data tables + 3,290 identity-bridge rows + 63 capture-ledger rows | three separate grains |
| FantasyCalc forward | 40,086 | 20,043 raw + 20,043 joinable rows | 20,043 captured observations represented twice, not 40,086 observations |
| Sleeper transactions | 2,628 | 932 transactions + 1,692 transaction movements + 4 season-capture rows | transaction, movement, and capture grains |
| Model forward output | 1,038,104 | 536,885 raw + 25,338 joinable + 475,880 prediction snapshots + 1 metadata row | heterogeneous derived tables; no meaningful additive observation total |

The catalog's “two largest external datasets” statement relies on these additive totals and is not
safe as written.

**Risk:** volume comparisons, change detection, coverage percentages, and source-priority claims are
biased by duplicate representations and metadata growth.

**Required remediation:** report one row per physical table with grain/category
(`raw`, `normalized`, `identity`, `capture_ledger`, `derived`) and only aggregate tables with the same
unit. Add a stable test that the nflverse source-row sum excludes `nflverse_capture`.

## F4 — §4 mistakes a consumer/feature job for a twelve-stream ingestion job

**Severity: High. Confidence: high.**

The catalog says the nflverse Feature Refresh job “covers twelve seasonal streams collectively.” It
does not.

`scripts/run_feature_refresh.py`:

- reads only `ngs_passing`, `ngs_receiving`, and `ngs_rushing` from the canonical last-good export
  through `load_nextgen_from_export`;
- independently calls live nflreadpy for `player_stats`, `rosters`, `snap_counts`, `pbp`, and
  `participation`;
- never invokes `run_usage_capture()` and does not refresh the canonical SQLite store;
- has no path to canonical injuries, PFR advanced stats, FF opportunity, FTN charting, or depth
  charts.

The repo has a manual `scripts/run_nflverse_usage_capture.py`; no LaunchAgent or production script
calls `run_usage_capture` automatically.

**Risk:** the catalog would assign a daily job cadence and freshness semantics to streams that are
not scheduled at all, hiding an absent scheduler/capture fact and conflating read-side consumption
with write-side ingestion.

**Required remediation:** add a `job_role` field (`source_capture`, `consumer_refresh`,
`derived_report`, `backup`) and explicit stream↔job edges. For B1-B12 the scheduled capture cadence
is presently `none`; the manual capture command is a separate runnable path. Inventory the direct
feature-refresh loaders as their own streams rather than treating them as canonical-store refreshes.

## F5 — §4's pass/durability/evidence claims conflict

**Severity: Medium. Confidence: high.**

- The heading says `FIRST PASS RECEIVED`, but the same section says Gemini has not issued its final
  operational-slice pass. Gemini issued a telemetry report and a valid OPS ALARM, not a catalog
  verification pass. A report must not be renamed a pass.
- The text says the operational matrix exists only in the daily ledger. The ledger diff contains a
  three-bullet summary, not the matrix. The matrix is now durable in this catalog, so “only in the
  daily ledger” is both factually wrong and temporally stale.
- The table drops the plist path, log path, marker path, last-run timestamp, and evidence timestamp
  Gemini supplied. Values cannot be independently checked cell-by-cell without those pins.
- `app/config/report_freshness.json` does not contain an `fc_snapshot` artifact or the offsite
  backup. FantasyCalc's 24-hour source declaration and the backup's standing governance law may
  still support daily expectations, but they require their actual paths in separate evidence
  columns rather than being presented as one homogeneous freshness registry.

**Required remediation:** rename the section `telemetry increment received`; add evidence-path and
measured-at columns; distinguish source freshness policy, artifact freshness registration, and
standing governance threshold. Request Gemini's final operational completeness acknowledgment only
after all operational rows are durable and corrected.

## F6 — Table B prevents per-stream verification and leaves measured cells stale

**Severity: Medium. Confidence: high.**

B6–B9 combine four PFR streams in one row, so their schemas, grains, counts, identities, eras,
cadences, and dispositions cannot be independently checked. Read-only counts are:

- `pfr_pass`: 5,424
- `pfr_rush`: 18,461
- `pfr_rec`: 35,724
- `pfr_def`: 62,345

The three NGS counts were remeasured and match their inherited figures (5,933 / 6,059 / 14,731), so
their dagger can be replaced with a current measurement. B4's disposition remains `UNVERIFIED`, yet
the summary asserts a closed 3/9/1 partition. A summary is not independently established until each
member row has one mutually clear lifecycle/disposition state.

**Required remediation:** one row per stream; populate all exact counts; keep lifecycle dimensions
separate (`bound`, `captured`, `exported`, `consumed`, `decision_supported`) rather than forcing
“never run” and `substrate_only` into one status slot.

## F7 — the source-gap register is not yet safe to answer David

**Severity: High for the requested deliverable. Confidence: high.**

- PFF is labelled `absent consumer` while the note says `build_college_features.py` consumes one
  family. The correct kind is partial consumer coverage, with family-level rows.
- “Nine nflverse streams” does not name the nine, and `snap_counts` has a live direct-nflreadpy
  consumer path even though that consumer does not read the canonical stored table. Store-consumer
  and provider-stream consumer must be distinguished.
- Candidate external sources are explicitly not enumerated, so no conclusion about sources still
  needing ingestion is possible.

**Required remediation:** defer David-facing source-gap conclusions until F1/F2 are repaired, then
grade every source/stream separately as absent source, loader, capture, normalization, export,
consumer, or decision use. `partial` must be representable; it is not equivalent to `absent`.

## What passed

- The foundational distinction between source and stream is correct even though the first rows do
  not yet implement it consistently.
- The 13 bound nflverse specs, axes, physical table names, and contracts table absence are accurate.
- All measured physical-table counts reproduced; the issue is their aggregation grain, not the
  underlying SQLite counts.
- The failed-backup OPS ALARM is valid, pauses no registered dependent, and authorizes nothing.
- Timeout withdrawal and separation of failed status from projected staleness are correct.
- DynastyProcess use/save approval and withdrawal of the generic licence blocker are correctly
  recorded.

## Minimum fix cycle before phase B

1. Reopen §1 A/B/C as partial.
2. Normalize source, stream, store, and job entities/edges.
3. Enumerate all active/direct/manual/fixture/deferred/prohibited sources and streams.
4. Replace mixed-grain totals with per-table counts and declared grains.
5. Correct §4's feature-refresh semantics and evidence pins.
6. Split B6–B9 and remeasure all rows.
7. Rebuild §5 from the complete normalized inventory.

Then route a fresh catalog pin for another adversarial pass. Phase B and Layer 2 research remain
closed. H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
