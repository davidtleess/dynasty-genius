# Layer 1 source-publish cadence and proposed local checks — Codex v1

**Layer:** Layer 1 ingestion.  
**Observed:** 2026-08-06 ET.  
**Status:** planning evidence only. No capture, job, scheduler, store, consumer, or enablement is
authorized by this artifact.

## Why this exists

The catalog correctly separates upstream publish cadence, our capture cadence, job fire cadence,
and freshness policy. This pass pins the upstream clocks for the nflverse-backed streams and turns
them into a proposed morning-capture schedule. A provider that checks four times per day does not
require us to create four duplicate observations; unchanged content must remain a no-change check.

## Primary-source pins

- nflverse's current [Data Update and Availability Schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
  states:
  - PBP and player stats update nightly after each game day, with additional game-day runs; users
    should update again Thursday after NFL stat corrections.
  - FTN charting checks at 00/06/12/18 UTC in season; underlying FTN availability can lag games by
    up to 48 hours.
  - 2023+ participation data is published only after all postseason games; it does not update in
    season.
  - rosters update daily at 07:00 UTC.
  - NGS weekly stats update nightly around 03:00–05:00 ET in season.
  - PFR snap counts check at 00/06/12/18 UTC in season.
  - PFR advanced stats update daily at 07:00 UTC in season.
  - depth charts update daily at 07:00 UTC year-round.
- nflverse's official PBP workflow
  [update_data.yaml](https://github.com/nflverse/nflverse-pbp/blob/866020fdf54bee79ea11b6cf69168d438dd26dea/.github/workflows/update_data.yaml)
  schedules 09:00 UTC daily plus post-TNF/Sunday/Monday game windows in January, February, and
  September–December. Player stats run downstream of the same PBP update.
- ffverse's official `ep-update-data.yaml` schedules `ff_opportunity` after TNF, Sunday early/late,
  SNF, and MNF game windows in January, February, and September–December.
- nflverse's official `rotc` `update_otc.yaml` updates contracts every day at 07:00 UTC.
- The current nflverse schedule page says its injury source died after 2024 and says no 2025 data
  is available. The actual official `injuries` release contradicts that sentence: `injuries_2025`
  assets were published `2026-03-18T12:45:31Z`, after the 2025 postseason. This proves a 2025
  historical archive exists, but does **not** establish an in-season injury feed. The local store
  contains 6,068 season-2025 rows with null `date_modified`; it cannot be treated as evidence of a
  live 2025 source.

## Historical-season immutability is falsified at the release-asset boundary

The open question in the three-lane Option A recommendation was whether an already-published
season file can be treated as immutable. Official GitHub release asset metadata says **no**:

- `stats_player_week_2018.parquet` was updated `2026-07-10T06:48:57Z`;
- `snap_counts_2018.parquet` was updated `2025-10-06T06:51:00Z`;
- `play_by_play_2018.parquet` was updated `2025-04-30T06:39:20Z`.

Those timestamps are many years after the seasons ended. They do not prove which rows changed—the
overwrite may be a correction, rebuild, or format regeneration—but they do prove the provider asset
at a stable season URL is mutable. Retention therefore cannot overwrite a prior accepted season
solely because the URL/season key is unchanged. The canonical contract needs content-addressed
versions and a no-change check; any changed bytes under an existing season key create a new source
version and trigger reconciliation. This closes the retention-policy question without claiming a
semantic revision rate that was not measured.

## Proposed nflverse-backed schedule

These are target checks, not authorized clocks. Two calendars are intentionally distinct:

- **provider game-data calendar** — the upstream workflow's January/February/September–December
  window, not a borrowed product-season definition;
- **postseason archive-discovery calendar** — weekly February–March/April checks for annual files
  that do not exist during the season, then a low-frequency availability check.

| Catalog stream | Upstream change rhythm | Proposed local capture check | Freshness / no-change rule | Blocking note |
| :-- | :-- | :-- | :-- | :-- |
| B1–B3 NGS passing/rushing/receiving | nightly 03:00–05:00 ET in season | daily 06:15 ET in provider-active months; weekly check otherwise | fresh by 09:15 consumer; unchanged bytes create no observation | existing canonical capture is manual; scheduler still needs design/word |
| B4 canonical snap counts / B17 duplicate live read | provider checks 00/06/12/18 UTC in season | one canonical check daily 07:15 ET in provider-active months; weekly otherwise | one last-good B4 export; B17 is retired only after parity control | do not create a second captured stream for B17 |
| B5 injuries — historical archive | no established live feed; 2025 archive appeared only after postseason | weekly availability check February–April, then freeze the completed season | content-addressed annual archive; never claim current injury freshness | current-season injury state is **blocked pending a replacement sanctioned source** |
| B6–B9 PFR advanced passing/rushing/receiving/defense | daily 07:00 UTC in season | daily 06:15 ET in provider-active months; weekly otherwise | same-day last good; no-change on identical bytes | four grains may share a job only with separate per-stream markers/counts |
| B10 ff opportunity | after TNF/Sunday/SNF/MNF game windows in provider-active months | daily 06:30 ET in provider-active months; weekly otherwise | last provider release; unchanged bytes create no observation | derived upstream from PBP but remains its own source release/contract |
| B11 FTN charting | provider checks 4× daily; charting may lag a game up to 48h | daily 07:15 ET in provider-active months; weekly otherwise | freshness ceiling must allow documented 48h source lag | CC-BY-SA attribution/retention remains part of artifact contract |
| B12 depth charts | daily 07:00 UTC year-round | candidate daily 06:15 ET check, but **automatic capture DEFERRED pending the storage/retention contract below** | timestamp/content-vintage keyed; unchanged pull is no-change | post-2024 data is timestamp-grain, not week-grain; current JSON envelope is unsafe for daily accrual |
| B13 contracts | daily 07:00 UTC year-round | daily 06:15 ET year-round | snapshot vintage/content hash; same vintage + changed bytes conflicts | first production capture is the separately gated contracts landing |
| B15 player stats | same nightly/game-window workflow as PBP | daily 06:30 ET in provider-active months; weekly otherwise | Thursday check is the correction-quality frontier | new canonical stream under Option A |
| B16 rosters | daily 07:00 UTC | daily 06:15 ET year-round | daily source vintage/content hash | new canonical stream under Option A |
| B18 PBP | nightly plus game windows; Thursday is cleanest after stat corrections | daily 06:30 ET in provider-active months; weekly otherwise | coherent current-season last good; Thursday correction retained | one stream, two eventual consumers; Roster Auditor migration is separate scope |
| B19 participation | 2023+ publishes after postseason only; no in-season updates | postseason archive-discovery calendar: weekly February–March until the just-finished season appears, then freeze; monthly availability check otherwise | annual historical partition, not daily-current freshness | the 09:15 job must stop downloading it daily; last-good historical participation remains valid |

## HIGH — participation currently caps the entire five-frame season window

The postseason-only cadence is not merely wasted daily I/O. The current 09:15 job couples all five
frames into one season-ceiling probe:

1. `_load_source` evaluates `player_stats`, `rosters`, `snap_counts`, `pbp`, and `participation` in
   one dict literal.
2. Any loader `ConnectionError` escapes the entire function.
3. `_resolve_default_source` responds by stepping the **whole** season window down once and
   reloading all five frames.
4. `main` derives `season_end` from that fallback `player_stats` frame and can publish `ok`/`noop`.

Codex independently reproduced the availability boundary on 2026-08-06:

| Asset | HTTP result |
| :-- | --: |
| `pbp_participation_2025.parquet` | 200 |
| `pbp_participation_2026.parquet` | 404 |
| `play_by_play_2025.parquet` | 200 |
| `play_by_play_2026.parquet` | 404 *(expected before 2026 games publish)* |

A controlled loader probe then made the four other 2026 frames available while only
`load_participation(...2026)` raised. `_resolve_default_source(2018, 2026)` retried **every** loader
through 2025 and returned `effective_end = 2025`; every returned frame's maximum season was 2025.
That isolates participation as sufficient to cap all four otherwise-current frames.

This fallback is already executed benignly in the offseason because 2026 source assets do not yet
exist. The observed Feature Refresh log spans only 2026-06-28 through 2026-08-05, so the scheduled
path has never run in season. Once 2026 PBP/player-stats/rosters/snap-count assets begin publishing
but participation remains absent until after the postseason, the current route can silently drop
the entire 2026 season every morning while returning a healthy `ok`/`noop` state.

This is the strongest measured argument for Option A: independent capture clocks make an annual
participation partition incapable of capping the four current-season streams. It is a diagnosis and
planning requirement, **not authority to patch the live job in this artifact.**

## B12 depth-chart retention is a blocking design decision

Post-2024 depth charts append a new timestamped vintage daily. Under the current raw-envelope shape,
three local 2025 snapshots are each **145,483,884 bytes** (138.74 MiB), while the official 2025
Parquet asset is **2,584,724 bytes**. The JSON envelope is **56.29×** the compressed provider asset;
one such snapshot daily would add about **49.45 GiB/year** before backup copies, for a stream with
no consumer today. The exact provider Parquet would be about 0.88 GiB/year at the same daily rate.

Therefore B12 must not be enabled with the existing JSON raw writer. Its RED must first choose and
test a compressed exact-source representation, a content/no-change check, an explicit retention
ceiling, and an as-of replay promise. Until those are settled, B12 is a daily-check candidate but
automatic capture is deferred. This is a storage/retention block, not an argument for an invisible
live provider read.

## Option A morning dependency

The five-stream Option A recommendation does **not** mean five identical daily source clocks.

```text
06:15–07:15 ET source-aware capture checks
        -> per-stream schema/identity/provenance gates
        -> coherent last-good bundle marker by 08:45 ET
        -> 09:15 Feature Refresh reads only that marker
```

`participation` is the sharp discriminator: it is annual/postseason data, so a daily provider read
cannot make it fresher. The coherent bundle carries its last accepted historical partition while
PBP/player stats/rosters/snap counts advance on their own source vintages. A bundle must name every
component vintage; it must not pretend all five share one observation clock.

## Non-nflverse schedule dispositions from current evidence

| Stream/source | Proposed classification/cadence | Remaining gate |
| :-- | :-- | :-- |
| Sleeper league/universe normalized snapshot | retain current daily 09:20 check for now | raw endpoint replay is absent; health verification and raw-capture design remain open |
| Sleeper transactions | candidate: daily current-season capture plus weekly full-chain reconciliation | incremental/current-season parity, call ceiling, marker/freshness policy, enablement word |
| FantasyCalc forward | retain current daily 09:00 capture | add freshness registration and prove operational health; preserve market separation |
| CFBD | no automatic clock yet | paid-call monthly/run ceiling and event cadence require David's ruling |
| PlayerProfiler | manual-only pending sanctioned acquisition audit | access/legal/reliability gate |
| PFF / RotoViz / Campus2Canton | manual-only | human export/upload is the current contract |
| MFL rookie ADP | automatic candidate, at most daily | separated market-overlay destination and exact scoring limitations first |
| DynastyProcess historical pins / QB validation inputs | static pinned | automation must be physically unable to overwrite registered evidence |
| ff_rankings / prohibited enterprise sources / KTC | blocked or prohibited | current rulings remain; no schedule |

## Planning conclusions

1. A single daily canonical job is acceptable only as an orchestrator; each stream still needs its
   own source clock, marker, row/count reconciliation, and no-change outcome.
2. The morning deadline is driven by the existing 09:15 consumer, but the source clock determines
   whether a component can legitimately change.
3. Current-season injury data is the first concrete candidate-new-source gap exposed by cadence
   research. Any injury-derived current-season feature had **no live 2025 input for the entire 2025
   season**; the 6,068 season-2025 rows now in the store arrived as a post-hoc archive and have null
   `date_modified`. Row presence today must not be misread as point-in-time coverage. The historical
   nflverse archive does not satisfy current-season availability.
4. Participation must be removed from the “daily source” mental model even though it remains one of
   the five Option A capture contracts.
5. The completed backup recovery clears the failed-marker precondition **ONLY**. Manifest coverage,
   the anti-rot enforcement gap, a numeric storage ceiling, and David's separate enablement word all
   remain. Every new raw/store path must enter the manifest and pass the anti-rot/reviewer gate
   before enablement.
