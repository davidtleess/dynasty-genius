# Layer 1 source-gap analysis — Codex v1

**Date:** 2026-08-06 (America/New_York)  
**Layer:** Layer 1 data foundation  
**Scope:** read-only inventory and gap classification. No capture, adapter, schema, schedule,
consumer, paid call, commit, push, or enablement authority is inferred.

## Answer first

The current evidence does **not** establish that Dynasty Genius needs another external provider
immediately. The highest-priority gaps are mostly data that already flows from providers we already
use but is either uncataloged, fetched live without replayable capture, or normalized without the
exact source bytes.

The present ordering is:

1. reconcile an already-captured Sleeper league-history source that the canonical catalog omits;
2. canonicalize the existing nflverse/nflreadpy live reads, including Combine and the future
   realized-outcome schedule/stat reads;
3. retain and normalize the injury fields already present in Sleeper before purchasing or adding
   another injury provider;
4. acquire a production RAS dataset only if the architecture-governed risk/context use remains
   required;
5. keep market-only, fixture-only, proprietary, and enterprise sources conditional or blocked until
   they have a specific Layer 1 use and legal destination.

This is a source-gap answer, not a build plan. "Needed" below means the evidence supports a missing
Layer 1 dataset or capture property; it does not authorize its implementation.

## Method and classification contract

I treated provider, stream, capture, store, and consumer as separate objects. A provider is not
"missing" merely because one of its streams is not captured. A local artifact is not a replayable
capture merely because it contains normalized source fields.

Each candidate is classified as one of:

- **existing source / catalog omission** — bytes are already present but the canonical inventory
  does not row them;
- **existing source / absent replayable capture** — live or normalized data exists, but exact input
  bytes and source provenance do not;
- **existing source / absent production acquisition** — the provider is registered and the product
  use is already defined, but only a fixture or stub exists;
- **conditional new source** — another provider is justified only if a predeclared coverage test
  proves current sources inadequate;
- **not presently justified** — no specific decision, legal route, or non-duplicative increment is
  established.

I measured repository paths and code at `HEAD 1645af7`. Counts are grain-tagged; unlike grains are
not summed.

## SG1 — HIGH: four seasons of Sleeper league history are captured and backup-covered but absent
from the canonical catalog

The catalog's Sleeper rows cover the daily normalized league/universe bundle and the separate
transaction store. They do not row this physical capture:

`app/data/research/league_behavior/raw/2026-07-19/`

Measured contents:

| Item | Measured fact |
| :-- | :-- |
| Files | **173** = 172 endpoint snapshots + `fetch_log.json` |
| Disk allocation | **2,352 KiB** (`du -sk`) |
| League chain | 2023 → 2024 → 2025 → 2026 |
| Fetch log | ticket `EDGE-H1-00`; written `2026-07-20T02:35:10.017561Z`; **176 calls**, **0 failures** |
| Week payloads | 72 matchup files + 72 transaction files (18 weeks × 4 seasons) |
| Other endpoint payloads | 4 each of league, users, rosters, traded picks, drafts, draft object,
  and draft-picks object |
| Envelope | each endpoint snapshot records `fetched_at_utc`, `endpoint_url`, and `payload` |
| Backup | `app/config/backup_manifest.json` requires `app/data/research/league_behavior/raw` |

Primary repo evidence is
`docs/strategies/2026-07-19-league-behavior-evidence-pull-draft.md:1-7,40`; the physical counts above
were independently remeasured rather than copied from it.

**Correct classification:** existing Sleeper source; manual one-time exact endpoint capture;
replayable; backup-covered; no scheduled refresh; no production consumer established. This is
neither a new-provider gap nor the same stream as the daily normalized N18 bundle.

**Catalog consequence:** source A7 and the stream table are incomplete until this capture has its
own grain-preserving row. The catalog's candidate-source answer cannot be considered complete while
an existing raw source family is absent from the canonical rows.

## SG2 — HIGH: the current injury gap is not yet evidence that a new provider is required

The post-hoc nflverse injury archive is not point-in-time current-season coverage. But the existing
Sleeper `/players/nfl` source already carries current injury-shaped fields. A live read at
2026-08-06 measured:

| Field | Non-empty players |
| :-- | --: |
| total players | **12,210** |
| `injury_status` | **511** |
| `injury_body_part` | **433** |
| `practice_participation` | **1** |
| `injury_start_date` | **0** |

The fetched response was 14,625,337 bytes with SHA-256
`5115254e49ff1b210b11741ce9d661a111b2d44660d17f72d38948b5a0e07080`. It was used only for this
read-only measurement and was not added to the product store.

The product currently discards nearly all of this information. In
`src/dynasty_genius/sleeper_universe.py:247`, the normalized player projection retains only source
`status` as `sleeper_status`; it does not retain `injury_status`, `injury_body_part`,
`practice_participation`, or `injury_start_date`. N18 also does not retain the exact raw endpoint
response.

**Correct classification:** existing Sleeper source with absent exact raw capture and absent injury
normalization. The one non-empty practice-participation value is an offseason observation, not proof
of acceptable in-season practice-report coverage.

**Decision gate before naming a new provider:** during the regular season, measure Sleeper against a
predeclared denominator and freshness rule for rostered fantasy-relevant players. Only if it misses
the agreed coverage floor should Dynasty Genius add a sanctioned live injury/practice/game-status
provider. The comparison must distinguish designation, body part, practice status, game status, and
source timestamp; a single aggregate "injury coverage" percentage would hide the exact missing
field.

## SG3 — HIGH: the catalog's five direct reads are not the complete direct-read universe

The catalog rows the five inputs to the daily Feature Refresh, but at least three additional
nflverse/nflreadpy dataset routes matter to Layer 1:

| Dataset | Current route | Physical input capture | State |
| :-- | :-- | :-- | :-- |
| NFL Combine | `scripts/build_w2_features.py:520-523`, years 2015–2025 | none found | active
  training-file enrichment; fail-fast unless explicitly degraded |
| schedules | `scripts/run_realized_outcome_scoring.py:338-364` | none found | weekly job route,
  currently gated before source load by absent predictions |
| player stats | `scripts/run_realized_outcome_scoring.py:367-383` | none for that route | same;
  will become live once prediction snapshots exist |

The weekly Realized Outcome job is not hypothetical operational prose: its 2026-08-04 marker is a
terminal `noop` for `no_predictions_for_target`, and the output log has four such noops. That gate
means schedule/stat provider reads are not flowing today; it does **not** make their declared future
live route a replayable Layer 1 source.

The same five Feature Refresh frames are also loaded directly by
`scripts/assemble_engine_b_dataset.py:219-223`. That is a second consumer path, not five new
streams. It strengthens Option A: canonical capture needs to serve every consumer, not merely swap
the 09:15 job.

**Correct classification:** existing nflverse source, incomplete route/consumer inventory, and
absent replayable capture. Combine is the sharpest immediate omission because an active builder
already mutates the governed training CSV from the live response. Schedules and realized player
stats must be canonical before the first prediction-bearing in-season scoring run, not discovered
after it.

This finding does not automatically place validation-only and one-time freeze scripts into the
production schedule. Each caller still needs classification as production, scheduled, active
builder, validation-only, or frozen study input.

## SG4 — MED: historical row coverage is not point-in-time vintage coverage

The canonical nflverse raw tree contains 1,019 snapshot files, but the capture dates encoded in
their filenames are only **2026-07-31, 2026-08-02, 2026-08-03, and 2026-08-05**. Historical-season
rows inside those files can support retrospective analysis; they cannot reconstruct what the system
would have known before the first capture date.

**Correct classification:** missing point-in-time history is an acquisition-mode limitation, not a
new-provider gap. Content-addressed forward capture can stop the gap from growing. It cannot
retroactively manufacture prior vintages, and a later archive from another provider is not a valid
substitute for an as-of snapshot.

## SG5 — MED: college YPRR is captured from PFF but absent from the active training materialization

The PFF inventory contains NCAA `receiving_summary` files with a `yprr` column, and
`scripts/build_college_features.py:327-334` maps it to `yprr_college`. Yet the active
`prospects_with_outcomes_v3.csv` has **874** rows and **zero** non-empty `yprr_college` values.

**Correct classification:** existing paid/manual PFF source and existing builder, but absent
materialization/curation in the active Layer 1 training artifact. This is not evidence that another
college-efficiency provider is needed. The source-to-row identity/season join and the active-file
promotion path must be reconciled first.

## SG6 — HIGH: existing sources have additional parallel acquisition routes

A bounded caller audit found two current one-source/two-route conflicts beyond the five-frame
Feature Refresh problem:

- Roster Auditor directly requests Sleeper league, roster, and `/players/nfl` data instead of
  consuming N18. N18 itself is normalized-only, so neither route currently supplies exact replay.
- FantasyCalc has both the daily append-only forward-capture route and an independent request-time
  JSON-cache/live-fetch route used by the trade API and market-overlay service.

The CFBD foundation wrapper stages raw and curated outputs, but the underlying builder remains
directly invokable against the active training CSV. That is a bypassable canonical route, not a new
provider gap.

Full caller/class evidence is in `layer1_external_route_audit_codex_v1.md`.

## SG7 — MED: MFL rookie ADP is uncaptured, but its overlay destination is already designed

The catalog's R9 row says `mfl_rookie_adp` has no capture because its overlay destination is
undesigned. The first half is true; the second is not:

- `src/dynasty_genius/adapters/mfl_adp_adapter.py` defines the public MFL ADP/player-map reads,
  sanitization, cache semantics, intrinsic QB-count/TE-premium caveats, and normalized rows.
- `src/dynasty_genius/mfl_rookie_adp_divergence.py` defines a neutral, `decision_supported=false`
  overlay artifact.
- `scripts/build_mfl_rookie_adp_divergence.py` writes that artifact under `app/data/valuation/`,
  physically separate from Engine A/B feature stores.
- No MFL cache or divergence artifact exists on disk today; no scheduler calls the builder.

**Correct classification:** existing registered provider; adapter and separated descriptive-overlay
destination built; never captured or scheduled. Its aggregate blends QB counts and cannot be used to
calibrate Superflex QB value, but it has a narrower defined use as real-draft rookie ADP context.
Whether to prioritize a first capture before Layer 2 is a David priority decision, not an absent
design fact.

## Sources the evidence supports ingesting

### Required existing-source work before seeking new providers

| Priority | Provider / dataset family | Why it is needed | Minimum honest state |
| :-- | :-- | :-- | :-- |
| P0 | Sleeper league history | already captured but absent from canonical inventory | catalog row
  with endpoint grains, one-time/manual cadence, provenance, backup state, and consumer state |
| P0 | nflverse `player_stats`, `rosters`, `snap_counts`, `pbp`, `participation` | production
  consumers currently read live; participation can silently cap the season window for all five |
  exact provider capture, independent per-stream vintage, last-good export, consumer parity |
| P1 | nflverse Combine | active training enrichment reads live and keeps no replayable input |
  immutable source capture + parser/version provenance; builder consumes captured last-good |
| P1 | Sleeper `/players/nfl` injury fields | existing current source data is discarded and N18 is
  normalized-only | exact endpoint capture + explicit injury-field projection + in-season coverage
  measurement |
| P1 before go-live | nflverse schedules + realized weekly player stats | weekly score job declares
  live loaders that become active when predictions exist | captured weekly source vintage, finality
  provenance, and replayable score-run input |
| P1 | PFF NCAA receiving-summary → `yprr_college` | source files and builder exist, but the active
  874-row artifact contains zero values | reconcile identity/season joins and promote the verified
  projection without treating this as a new-source acquisition |

### Existing registered source with absent production acquisition

**RAS (`ras.football`)** remains fixture-only. This is a real missing acquisition if David retains
the architecture-governed use: low/missing RAS may generate risk/context flags, while high RAS may
not create positive model lift without separate validation. The missing work is not "add an
athleticism feature"; it is establish a legal, reproducible production dataset and identity join for
the narrow risk/context use. NFL Combine data does not silently become RAS; it may supply
overlapping raw measurements but not the proprietary composite and its historical calculation.

The physical gap is total in the active training artifact: across **874** rows,
`rb_ras_composite`, `wr_ras_composite`, and `te_ras_composite` each have **zero** non-empty values.
Feasibility is not established merely because RAS is described as free in the registry. RAS's own
database setup instructions say access to the underlying database requires an NDA and that the
database/underlying data may not be shared, while query results may be shared. The exact terms must
be reconciled with private backup, portability, retention, and derived-output rules before capture.
Primary source: <https://ras.football/2021/08/22/getting-set-up-for-ras-locally/>.

**MFL rookie ADP** is a second existing-source acquisition candidate, but market-overlay only. The
minimum honest capture would preserve the exact ADP/player-map responses and source timestamp,
write only the separated `app/data/valuation` overlay projection, carry the blended-QB-count and
TE-premium caveats, and never enter Engine A/B. Its useful source season is rookie-draft season, not
a year-round daily default.

### Conditional new source

**Current injury/practice/game-status provider:** conditional only. Reopen provider selection if the
in-season Sleeper completeness test fails. The required source must support point-in-time snapshots,
source timestamps, stable identity, legal retention, and exact replay. The nflverse/PlayerProfiler
archives cannot satisfy current-season point-in-time use merely because they later contain the
season's rows.

## Sources not presently justified as Layer 1 additions

- **`ff_rankings` / FantasyPros ECR through DynastyProcess:** remains `blocked_for_use`, no RED. It
  is expert consensus, not a market price, and its incremental decision use is unproven.
- **KTC:** scraping is prohibited; market overlay only.
- **RotoViz / Campus2Canton:** fixture/manual-export declarations do not establish a production
  need or a legal automated acquisition route.
- **Dynasty Data Lab / Dynasty Nerds / enterprise providers:** deferred or prohibited at the
  current phase; cost or access alone does not establish incremental value.
- **Narrative coaching/scheme feeds:** no granular Layer 1 decision contract currently says what
  fields, timestamps, or reproducibility standard they serve. Existing PBP, participation, roster,
  and depth-chart streams should be exhausted before adding subjective prose as fuel.

## What is still required before §H can be checked off

1. Add SG1's existing raw league-history capture to the canonical rows without summing unlike
   endpoint grains.
2. Enumerate every external read and classify the caller: scheduled production, active builder,
   validation-only, study-pinned, or dead/deferred.
3. Reconcile each stream to one canonical capture route and every consumer edge.
4. Resolve the live Sleeper and FantasyCalc parallel routes, and make the isolated CFBD wrapper the
   only governed acquisition path before treating those sources as reconciled.
5. Run the in-season Sleeper injury-field coverage test before selecting a new provider.
6. Reconcile the existing PFF YPRR projection into the active training artifact before seeking a
   duplicate college-efficiency provider.
7. Decide whether production RAS risk/context coverage is still required and, if yes, establish the
   legal acquisition/retention/backup path under the provider's NDA terms.
8. State the point-in-time ceiling honestly: forward capture prevents further loss but does not
   recreate pre-2026-07-31 nflverse vintages.
9. Correct R9's stale destination claim and ask David whether MFL's already-designed descriptive
   overlay merits a first source capture before Layer 2.
10. Keep market overlays physically and semantically separate from Engine A/B feature stores.

Until those steps are independently verified in the canonical catalog, the honest answer is:
**the repo has proven missing capture work, but no unconditional new external provider has yet been
proven necessary.**
