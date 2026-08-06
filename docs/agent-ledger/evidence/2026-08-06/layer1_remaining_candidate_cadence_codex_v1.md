# Layer 1 remaining automatic-candidate cadence — Codex v1

Date: 2026-08-06 ET  
Layer: Layer 1 inventory / refresh planning only  
Scope: B20 Combine, B21 schedules, B22 draft picks, B23 DynastyProcess `db_playerids`, R9 MFL rookie ADP  
Non-actions: no capture, cache write, scheduler, consumer migration, paid call, build, commit, push,
or enablement.

## Answer first

Three previously unverified upstream clocks are now established from primary workflows:

| Stream | Established upstream trigger | Conservative local check candidate |
| :-- | :-- | :-- |
| B20 Combine | 12:00 and 17:00 UTC, March 3–12, plus manual dispatch | one content-hash/ETag check at 20:00 UTC, March 3–13 |
| B21 schedules | every five minutes during the season | Tuesday 06:15 ET year-round, before the only loaded consumer's Tuesday 10:00 ET run |
| B22 draft picks | 05:00 UTC Wednesdays Sep–Feb; additionally daily Feb 1–15 and Apr 23–May 5; plus manual dispatch | 12:00 UTC on those calendar days |
| B23 DynastyProcess `db_playerids` | Friday 00:23 UTC plus manual dispatch; observed publication can lag several hours | Friday 08:15 ET, conditional on public blob SHA; retry Saturday 08:15 ET whenever Friday is unchanged or retrieval fails |

R9 MFL is **not schedulable**. Its upstream ADP mutation cadence remains unverified, and the current
adapter query is not rookie-only under the current documented API contract.

Every proposed check is content conditional: unchanged bytes create no observation. A workflow fire
is not proof of changed bytes, and a cron time is not a delivery SLA.

## B20 — Combine

Primary evidence:

- Official publisher workflow, pinned at upstream commit `68d9b31240bd5552bd11a43e0d572859a2701819`:
  [`update_combine.yaml`](https://github.com/nflverse/nflverse-pfr/blob/68d9b31240bd5552bd11a43e0d572859a2701819/.github/workflows/update_combine.yaml).
- Exact cron: `0 12,17 3-12 3 *`, plus `workflow_dispatch`. The executable expression means twice
  daily March 3–12. Its prose comment says March 3–10 and is stale; the cron governs.
- Official loader mapping:
  [`nflreadpy.load_combine`](https://github.com/nflverse/nflreadpy/blob/a4f33d2216b2d7179ab3420a49a9dc49e30c42fa/src/nflreadpy/load_combine.py)
  downloads the nflverse-data `combine/combine` release; local nflreadpy 0.1.5 matches.
- The publisher rebuilds the complete Combine release from PFR. A successful workflow can still
  produce unchanged bytes.
- Pinned publisher implementation:
  [`auto/update_combine.R`](https://github.com/nflverse/nflverse-pfr/blob/68d9b31240bd5552bd11a43e0d572859a2701819/auto/update_combine.R)
  and [`R/combine.R`](https://github.com/nflverse/nflverse-pfr/blob/68d9b31240bd5552bd11a43e0d572859a2701819/R/combine.R).
- Observed 2026 example: official Actions
  [run 23016027415](https://github.com/nflverse/nflverse-pfr/actions/runs/23016027415)
  started after the nominal March 12 trigger and completed at 17:52 UTC; the
  [official Combine release](https://github.com/nflverse/nflverse-data/releases/tag/combine)
  updated immediately before completion. The 20:00 UTC proposal is an observed-delay allowance,
  not an upstream delivery SLA.

Still unverified: PFR's own publication clock, when a class is complete, future event-calendar
alignment, and a guarantee that a successful workflow changes content.

## B21 — schedules

Primary/dependency evidence:

- nflverse's official
  [Data Update and Availability Schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html#nflverse-gameschedule-data)
  states Game/Schedule data updates every five minutes during the season (accessed 2026-08-06).
- The only loaded repo consumer is `scripts/run_realized_outcome_scoring.py`, scheduled by
  `ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist` for Tuesday 10:00 local. It
  loads schedules to establish week finality before scoring and currently healthy-noops before
  prediction-bearing work exists.
- `app/config/report_freshness.json` registers that consumer as weekly, Tuesday 10:00 local, with a
  three-hour grace and offseason dormancy.

Proposed local check: Tuesday 06:15 ET year-round, content-hash conditional, retaining upstream
source/retrieval time and exact source bytes. This is deliberately much slower than the five-minute
upstream rhythm because the active dependency is weekly. It leaves nearly four hours before the
consumer, catches offseason schedule publication/changes without inventing a separate calendar, and
creates no observation on unchanged bytes. A future decision needing intraday reschedule awareness
would require its own consumer/cadence amendment; none is inferred here.

## B22 — draft picks

Primary evidence:

- Official publisher workflow at the same upstream pin:
  [`update_draft_picks.yaml`](https://github.com/nflverse/nflverse-pfr/blob/68d9b31240bd5552bd11a43e0d572859a2701819/.github/workflows/update_draft_picks.yaml).
- Exact expressions:
  - `0 5 * 9-12,1 3` — Wednesdays at 05:00 UTC in Sep–Dec and Jan;
  - `0 5 1-15 2 3` — under POSIX/GitHub day-of-month OR day-of-week semantics, daily February
    1–15 plus every Wednesday in February;
  - `0 5 23-30 4 *` — daily April 23–30;
  - `0 5 1-5 5 *` — daily May 1–5;
  - plus `workflow_dispatch`.
- The YAML comment claiming four Wednesday runs at 0/6/12/18 UTC contradicts the expressions and is
  not carried as evidence.
- Official loader mapping:
  [`nflreadpy.load_draft_picks`](https://github.com/nflverse/nflreadpy/blob/a4f33d2216b2d7179ab3420a49a9dc49e30c42fa/src/nflreadpy/load_draft_picks.py)
  downloads the nflverse-data `draft_picks/draft_picks` release; local 0.1.5 matches.
- Pinned publisher implementation:
  [`auto/update_draft_picks.R`](https://github.com/nflverse/nflverse-pfr/blob/68d9b31240bd5552bd11a43e0d572859a2701819/auto/update_draft_picks.R)
  scrapes PFR, upserts the existing pick keys, and republishes the full release.
- Observed 2026 example: official Actions
  [run 25362813416](https://github.com/nflverse/nflverse-pfr/actions/runs/25362813416)
  completed May 5 at 07:26 UTC and the
  [official draft-picks release](https://github.com/nflverse/nflverse-data/releases/tag/draft_picks)
  updated at the same time. The 12:00 UTC proposal tolerates this observed lag; it is not a queue SLA.

Still unverified: PFR table settlement time, historical correction rhythm, queue-delay ceiling,
future Draft-calendar alignment, and whether a republish changes bytes.

## B23 — DynastyProcess `db_playerids`

Primary evidence:

- Official workflow pinned to the latest commit that changed that file,
  `eab3937b7ac0eeda7f40fd2e42b9a5ca68665bb9`:
  [`weekly-playerids.yml`](https://github.com/DynastyProcess/data/blob/eab3937b7ac0eeda7f40fd2e42b9a5ca68665bb9/.github/workflows/weekly-playerids.yml).
- Exact trigger: `23 0 * * 5` (Friday 00:23 UTC) plus `workflow_dispatch`.
- The workflow refreshes several component identity sources, builds `dp_playerids`, and commits the
  public files. Its commit/push steps explicitly tolerate no-change, so a fire is not a new vintage.
- Local `nflreadpy.load_ff_playerids()` calls
  `download("dynastyprocess", "db_playerids", CSV)` and may serve its parsed 24-hour cache. It does
  not retain the exact upstream CSV or upstream commit/blob provenance. Primary pins:
  [`load_ffverse.py`](https://github.com/nflverse/nflreadpy/blob/c167b56a73c346b8df49b86923df50a4be95660b/src/nflreadpy/load_ffverse.py),
  [`downloader.py`](https://github.com/nflverse/nflreadpy/blob/e75269dbab70c4dea4d91857c04736629414b73b/src/nflreadpy/downloader.py),
  and [`config.py`](https://github.com/nflverse/nflreadpy/blob/2b1989f6431f006803af0ae8b3500d636af9072f/src/nflreadpy/config.py).
- Official history query on 2026-08-06: the latest twelve scheduled workflow runs, from
  [run 25900332586](https://github.com/dynastyprocess/data/actions/runs/25900332586)
  (2026-05-15) through
  [run 30602862847](https://github.com/dynastyprocess/data/actions/runs/30602862847)
  (2026-07-31), all succeeded, started between 03:43 and 05:29 UTC, and finished about 3–7 minutes
  later. The corresponding twelve `files/db_playerids.csv` commits span
  [`a923a1a`](https://github.com/dynastyprocess/data/commit/a923a1aec4a5af98c169b4b9679da268752c7eec)
  through [`aa0a063`](https://github.com/dynastyprocess/data/commit/aa0a063b0b2ea4e86d0175ef64500f247c64b9ef),
  at 03:47–05:32 UTC. The current public file blob observed was `4081218f...`, 2,624,332 bytes.
  This observed range motivates Friday 08:15 ET; it does not establish an SLA.

Retry semantics are intentionally simple because a blob check alone cannot distinguish a successful
no-change build from a delayed or failed workflow: Friday records either `changed`,
`checked_no_change`, or `retrieval_failure`; `checked_no_change` creates no observation. Both
`checked_no_change` and `retrieval_failure` receive one Saturday 08:15 ET retry. Saturday again
records its own outcome and preserves last-good on no-change/failure. No workflow-status inference is
made from blob equality.

Still unverified: component-source clocks, an on-time SLA, guarantee of weekly changes, and semantic
revision policy.

## R9 — MFL rookie ADP: blocked by live endpoint semantics

Primary documentation (accessed 2026-08-06):

- [Official ADP API reference](https://api.myfantasyleague.com/2026/api_info?STATE=details&TYPE=adp&PRINTER=1)
  documents rookie-only as `IS_KEEPER=R`, no mocks as `IS_MOCK=0`, and exposes a result timestamp.
  It publishes no recomputation cadence.
- [Official players API reference](https://api.myfantasyleague.com/2026/api_info?STATE=details&TYPE=players&PRINTER=1)
  says the player database updates at most once daily and should be cached/requested no more than
  once daily.

Repo/live discriminator:

- Current adapter URL: `ROOKIES=1&IS_MOCK=No`. Live read returned **349** rows; first ID `16161`
  resolves through MFL's official players endpoint to **Bijan Robinson**, so it is not rookie-only.
- Documented URL: `IS_KEEPER=R&IS_MOCK=0`. Live read returned **114** rows with a different rookie
  cohort.
- These were read-only HTTP probes. No local MFL cache or artifact was written.

Disposition: `blocked` pending a corrected endpoint contract plus durable controls proving rookie-only
semantics, identity/output coverage, and market-overlay separation. Only after that repair and an
explicit enablement word is a cadence candidate meaningful. The conservative post-repair shape is:
weekly availability before the NFL Draft, at most daily from Draft completion through August 31,
weekly Sep–Dec; one ADP call plus a player-map call only when its independent 168-hour local TTL
expires; source timestamp + content hash; last-good/backoff on failure/429. Exact seasonal window
and upstream mutation SLA remain `UNVERIFIED`.

The machine declaration is part of the defect: `SOURCE_REGISTRY["mfl_rookie_adp"].notes` currently
calls `ROOKIES=1` documented and the result real completed-draft rookie ADP. A future authorized repair
must update the adapter, the registry declaration/notes, and RED controls together; this planning
artifact changes none of them.

## Review boundary

This artifact supplies cadence evidence and exposes the R9 blocker. It does not authorize fixing the
adapter, writing a RED, capturing a first artifact, installing a job, or changing any consumer.
