# Manual-feed unique datapoint and refresh audit

Layer served: Layer 1 acquisition and freshness. Read-only analysis completed 2026-08-08.

## Decision

PlayerProfiler and PFF are not seven-day-stale merely because their most recent local acquisitions are about seven days old. A manual feed is due only when a non-equivalently-covered, authorized datapoint family has reached an observable change event. The current source-wide daily clock is therefore the wrong contract.

## Held evidence

- PFF: 149 distinct payloads, 76 NCAA and 73 NFL, across seven report families and twelve schemas. Source seasons are 2017–2025. No held payload covers 2026. The latest retrieval is 2026-08-01.
- PlayerProfiler player-season: 5,476 rows covering 2017–2025.
- PlayerProfiler game log: 44,462 player-week rows covering 2020–2025.
- PlayerProfiler play-by-play: 280,868 plays plus 949,041 player-slot rows, covering 2020–2025.
- PlayerProfiler roster-week: 230,394 rows covering 2020–2025.
- PlayerProfiler medical: 9,768 rows ending in 2023. The governed status marker names 2024–2026 as a blind window and says the medical evidence is not decision-supported for current players.
- Joined PlayerProfiler/nflverse basic weekly totals were 99.2% equal for targets and 99.6–100% equal for carries, receptions, attempts, completions and yards across 29,190 joined player-weeks. PP and nflverse snap definitions were not interchangeable: only 15,823 of 39,259 joined rows were equal.

## Unique or non-equivalent manual datapoints

| Source | Datapoint family | Automated overlap | Non-equivalently-covered value | Observed change mechanism | Honest refresh trigger |
|---|---|---|---|---|---|
| PlayerProfiler | Weekly route, alignment, coverage and efficiency charting | nflverse PBP, snaps and opportunity; NGS/PFR/FTN partial proxies | Player-on-play route, motion, cushion, defender assignment, route wins/burns, catchability, money/danger/interceptable throws, yards-created and other proprietary splits | New completed NFL game week; later vendor re-chart/correction | Once after each newly available NFL week when an authorized consumer needs these fields; final season capture; offseason not due |
| PlayerProfiler | Proprietary season aggregates | nflverse/NGS/PFR cover ordinary production | Weighted opportunities, opportunity share, route-win/coverage splits, target-quality/supporting-cast measures, production premium, expected metrics and proprietary ratings | Cumulative current-season update after games; historical correction | Weekly in active NFL season only when declared for Layer 2; season-final freeze |
| PlayerProfiler | College and athletic derivatives | CFBD and nflverse provide raw college, combine and draft inputs | Provider-specific breakout, dominator, best-season share, speed/burst/agility and comparable-player definitions | New rookie class; combine/pro-day/draft update; rare correction | Rookie-cycle capture after the new class is present; optional post-draft correction; existing veterans otherwise not due |
| PlayerProfiler | Historical medical detail | nflverse/Sleeper cover current injury designation and roster status | Surgery, severity, body region, recovery timetable and historical archive detail | New injury/recovery/correction in principle, but the held product currently supplies none after 2023 | Do not mark due. Check only when a newer archive is offered or a correction is announced; current decisions use nflverse/Sleeper |
| PlayerProfiler | Historical PP identity bridge | Sleeper/nflverse identify current players | PP-internal ID to GSIS provenance for older PP streams | New PP player/ID, unresolved identity, namespace or schema change | With the first PP weekly files of a new season, then only on an unresolved-ID/schema event |
| PFF | Receiving routes, YPRR, alignment, depth/direction and scheme charting | nflverse/NGS/PFR/FTN and PP provide totals or partial proxies; CFBD provides college production but not routes | PFF-denominator route/YPRR, man-zone, contested/drop/YAC/EPA and depth/direction cells, especially NCAA | New game data after charting and review; later correction/regrade | Current season after each relevant game-day validation window; explicit season-final snapshot |
| PFF | Passing pressure/depth/scheme charting | PFR pressures; FTN flags; NGS/PBP/PP partial context | PFF clean/pressure and blitz/no-blitz packages, charted accuracy, big-time/turnover-worthy play definitions and college versions | New game data after charting and review; later correction/regrade | Same game-event trigger; completed history only on announced correction/schema/methodology change or bounded pre-analysis comparison |
| PFF | Rushing contact/elusiveness charting | PFR broken tackles/YAC; NGS RYOE; PP/CFBD partial production | PFF avoided-tackle, breakaway, contact and gap/zone charting, especially NCAA | New game data after charting and review | Same game-event trigger; season-final snapshot |

PFF's official Membership FAQ says NFL game data including grades is available and validated by noon ET the day after the game, while FBS data is available by 8 a.m. ET the day after game day and some grading/All-22 review may follow. These are useful observation windows, not evidence that completed historical exports change daily.

## Datapoints that must not drive a manual download

| Manual datapoint | Operational substitute | Disposition |
|---|---|---|
| PP basic box totals and ordinary opportunity | nflverse canonical daily capture | Automated source owns refresh; do not download PP for this |
| PP current team, roster and status | Sleeper daily plus nflverse depth charts | Automated source owns current state |
| PP current ADP/value/trend | FantasyCalc daily | Use FantasyCalc unless a separately authorized PP-market research lane is required |
| PFF common totals | nflverse, NGS, PFR, FTN and CFBD depending league/family | Totals alone do not drive a PFF download |
| PFF grades | No exact substitute | Unique but diagnostic/private and prohibited from model use; grades alone do not drive operational refresh |
| Campus2Canton RYPTPA/dominator | CFBD primary; C2C is secondary validation | No recurring production obligation |
| RotoViz fields | No held export or governed schema | Uniqueness and cadence unknown; first-drop inventory before any recurring obligation |
| RAS | No production acquisition route | Blocked, not manual-due |

## Required freshness contract

Replace one source-wide manual clock with one obligation per datapoint family:

- `change_trigger`: game_week_complete, rookie_class_available, provider_correction, schema_change, archive_extended, or unresolved_identity;
- `stored_vintage`: latest source season/week/export identity actually held;
- `next_expected_event`: the observable event that can make the family due;
- `state`: current/not_due, due, unknown, or inadequate;
- `coverage_owner`: automatic substitute or manual family;
- `consumer_authorization`: whether the unique family currently has a governed downstream need.

A source is due only when at least one unique, authorized family has an unsatisfied observable event. Duplicated fields never make a manual source due.

## Limits

Neither manual provider exposes a governed API, push notification, or change feed in the held evidence. Therefore “download every time a datapoint changes” can be enforced at known game/class/correction windows, but spontaneous historical revisions cannot be detected immediately. Historical protection is a correction/schema notice plus a bounded pre-analysis hash comparison. This ceiling should be visible rather than disguised as a daily freshness guarantee.

## Evidence sources

- `app/data/playerprofiler.db`
- `app/data/playerprofiler/playerprofiler_status_latest.json`
- `app/data/playerprofiler/playerprofiler_gamelog_status_latest.json`
- `app/data/playerprofiler/playerprofiler_pbp_status_latest.json`
- `app/data/playerprofiler/playerprofiler_roster_status_latest.json`
- `app/data/pff_exports/pff_unique_payload_inventory.csv`
- `app/data/pff_exports/pff_schema_catalog.json`
- `app/data/pff_exports/pff_coverage.csv`
- `app/data/nflverse_usage.db`
- `src/dynasty_genius/sources/source_registry.py`
- PFF Membership FAQ: https://www.pff.com/lp/membership
- PFF review-process description: https://www.pff.com/news/introducing-in-game-grading-track-pff-data-as-the-action-unfolds
- PlayerProfiler Data Analysis Tool: https://www.playerprofiler.com/article/data-analysis-tool-download/

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated to this Layer 1 audit.
