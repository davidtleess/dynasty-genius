# Layer 1 cadence audit — Codex overnight v1

**Layer:** Layer 1 ingestion.  
**Observed:** 2026-08-06T00:44:01-0400 EDT.  
**Scope:** read-only `launchctl print`, committed plists/config, logs, durable markers, and producer
searches. No job was installed, loaded, run, stopped, or changed.

## Rule used

A committed plist, a loaded scheduler job, a successful fire, a freshness policy, and an upstream
stream refresh are five different facts. A row is automatic only when the producer edge reaches the
named stream/store.

## Results

| Stream/store | Declared job | Loaded state | Last durable evidence | Actual refresh classification |
| :-- | :-- | :-- | :-- | :-- |
| Canonical `nflverse_usage.db` (B1–B13) | **none**; no `run_nflverse_usage_capture` reference under `ops/` | none | manual run `nflverse-usage-20260805T1334216901700000` | `manual_only`; no scheduled capture |
| Feature Refresh's five live reads | daily 09:15 `com.davidleess.dynasty-feature-refresh` | loaded; not running; `runs=2`, last exit 0 at observation | log history: 39 fires = 4 ok, 34 noop, 1 refusal; latest report generated 2026-08-03T13:38:58Z | consumer job fires daily, but **does not capture** the five streams |
| `fc_forward_capture.db` | daily 09:00 `com.davidleess.dynasty-fc-snapshot` | loaded; not running; `runs=2`, last exit 0 | marker ok, retrieved 2026-08-05T13:00:00.788173Z, 475 rows appended that run | automatic active; freshness registration is still absent |
| Legacy `fc_snapshots.db` | none; forward job explicitly supersedes it | none | last `fc_native` date 2026-06-24; DynastyProcess history through 2024-09-08 | frozen/manual archive, not refreshed by the 09:00 job |
| Sleeper `league_runtime` snapshot bundle | daily 09:20 `com.davidleess.dynasty-league-capture` | loaded; not running; `runs=2`, last exit 0 | 21 success log lines, latest marker run `league-20260805T132003Z`, finished 2026-08-05T13:20:08Z | automatic active; this is the real 09:20 stream |
| Sleeper `league_transactions.db` | **none**; no transaction-capture entrypoint under `ops/` | none | manual marker finished 2026-07-31T02:22:34Z, 932 transactions / 1,692 movements | `manual_only`; must not inherit 09:20 cadence |
| PlayerProfiler store | none | none | four manual-ingest markers ok, finishing 2026-08-01 between 03:47Z and 13:36Z | `manual_only` under current sanctioned export path |
| PFF exports | none | none | unique-payload inventory mtime 2026-08-01T09:47:33-0400 | `manual_only` |
| CFBD foundation | none under `ops/` | none | marker ok, run `20260802T024342156864Z`, 1,202 payloads / 874 curated rows | `manual_only` today; automatic candidate only after paid-call budget/cadence ruling |
| RAS / RotoViz / Campus2Canton fixtures | none | none | tracked fixture files only | `static_fixture`, not production refresh streams |
| MFL rookie ADP | no job; cache directory has no files | none | no physical capture found | automatic candidate; no current capture/store |
| R18 QB context | no source-capture job | none | live `nfl.load_pbp([2024, 2023])` when Roster Auditor runs | consumer-triggered live read of B18 PBP; absent capture |
| R20 QB validation | none | none | raw path has zero files; study not run | `static_pinned` registration, not captured |

## Evidence pins

| Row | Scheduler / producer evidence | Durable artifact / timestamp evidence |
| :-- | :-- | :-- |
| Canonical nflverse | no `run_nflverse_usage_capture` reference under `ops/`; producer is `scripts/run_nflverse_usage_capture.py` | `app/data/nflverse_usage/export/nflverse_usage.ready.json`: run `nflverse-usage-20260805T1334216901700000`, captured `2026-08-05T13:34:21.690170+00:00` |
| Feature Refresh live reads | `ops/launchd/com.davidleess.dynasty-feature-refresh.plist`; `scripts/run_feature_refresh.py`; daily 09:15 | `app/data/features_runtime/feature_refresh_latest_report.json`: `ok`, generated `2026-08-03T13:38:58.568792+00:00`; `app/data/logs/feature_refresh.out.log`: 39 recorded lines at observation |
| FantasyCalc forward | `ops/launchd/com.davidleess.dynasty-fc-snapshot.plist`; `scripts/run_fc_forward_capture.py`; daily 09:00 | `app/data/capture/fc_forward_capture_latest_report.json`: `ok`, retrieved `2026-08-05T13:00:00.788173+00:00`; `app/data/logs/fc_forward_capture.out.log` |
| Sleeper league runtime | `ops/launchd/com.davidleess.dynasty-league-capture.plist`; `scripts/run_league_snapshot_capture.py`; daily 09:20 | `app/data/league_runtime/ready_latest.json`: run `league-20260805T132003Z`, source-captured `2026-08-05T13:20:03.348137+00:00`; `capture_status_latest.json`: `ok`, finished `2026-08-05T13:20:08.045189+00:00`; `app/data/logs/league_capture.out.log`: 21 success lines |
| Sleeper transactions | no `run_league_transaction_capture` invocation under `ops/` | `app/data/league_transactions/transaction_capture_status_latest.json`: `ok`, finished `2026-07-31T02:22:34.154335+00:00` |
| PlayerProfiler | no PlayerProfiler capture invocation under `ops/` | four markers under `app/data/playerprofiler/`: `playerprofiler_status_latest.json`, `playerprofiler_gamelog_status_latest.json`, `playerprofiler_roster_status_latest.json`, `playerprofiler_pbp_status_latest.json`; all `ok`, finishing from `2026-08-01T03:47:35.370993+00:00` through `2026-08-01T13:36:41.254502+00:00` |
| PFF | no PFF producer under `ops/`; manual export surface | `app/data/pff_exports/pff_unique_payload_inventory.csv`, filesystem mtime `2026-08-01 09:47:33 EDT` |
| CFBD foundation | no `run_cfbd_foundation_refresh` invocation under `ops/` | `app/data/sources/cfbd_foundation/status_latest.json` and `manifest_latest.json`: run `20260802T024342156864Z`, `ok`, captured `2026-08-02T02:43:42.156864+00:00`, 1,202 raw payloads / 874 curated rows |
| RAS | no producer under `ops/` | `resources/fixtures/ras_mock.csv` is the only RAS data file found |
| MFL rookie ADP | no job under `ops/` | configured cache directory contains no captured files |
| R18 QB context | `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py` live call; `app/services/roster_auditor.py` consumer | no raw snapshot or cache written by the route |
| R20 QB validation | no job under `ops/` | `app/data/backtest/qb_validation/raw/` contains zero files; registered study has not run |

## Installed-job evidence ceiling

`launchctl print` proves each named label was loaded at the observation time and reports current
state/run counter/last exit. Its `runs=2` counter is not treated as historical fire count. Historical
claims come only from logs and markers.

## Findings for the catalog

1. The 09:20 row must be named Sleeper **league-runtime/universe snapshot**, not generic “Sleeper
   Capture.” It does not refresh historical transactions.
2. Canonical nflverse capture remains entirely unscheduled even though the separate Feature Refresh
   consumer fires daily.
3. PlayerProfiler, PFF, CFBD, Sleeper transactions, and legacy FantasyCalc history are manual/static
   at present. A marker from a past manual run is not an automatic cadence.
4. The five Option A streams need capture jobs and markers before the current consumer job can stop
   making live reads. The recommended dependency order is capture → coherent last-good bundle →
   Feature Refresh.
5. Backup health remains an enablement precondition; this audit creates no enablement authority.

## Gemini task state

Gemini was asked via a shared-file handoff to independently audit these facts. Its pane reached a
permission dialog for `launchctl list`. Codex did not press that dialog: another lane's prompt is not
Codex's to submit. This audit therefore stands as the Codex lane's evidence pending any later Gemini
response; it is not attributed to Gemini.
