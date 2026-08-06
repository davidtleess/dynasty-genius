# Layer 1 inventory — Codex overnight verification v1

**Layer served:** Layer 1 data foundation.  
**Observed:** 2026-08-06 ET.  
**Catalog target read:** `docs/layer-1-data-inventory-catalog.md` at commit `6f13228`.  
**Method:** read-only repository, SQLite, manifest, marker, and filesystem probes. This artifact
does not authorize capture, scheduling, migration, commit, or push.

## Result

Table B-N is **not independently clear yet**. PlayerProfiler and FantasyCalc row counts reproduce,
but the new CFBD row has a material file-count error and the PFF/CFBD grains need correction. The
registry review also closes four previously unverified physical-state questions and exposes two
source/provenance mismatches.

## V1 — CFBD raw count is 1,202, not 810

`app/data/sources/cfbd_foundation/manifest_latest.json` pins:

- run `20260802T024342156864Z`;
- captured `2026-08-02T02:43:42.156864+00:00`;
- `raw_file_count = 1202`;
- curated `row_count = 874`;
- raw content SHA-256 `6270c8bc13dcce90358d6a2d79f1895c6c6afd5279c2249edfcc78ffee571679`.

The corresponding directory contains 1,203 JSON files: 1,202 payloads plus `manifest.json`.
Payload decomposition by filename is 404 `tpa_*`, 756 `qb_raw_*`, 14 `sp_ratings_*`, 14
`player_receiving_*`, and 14 `player_rushing_*`. Catalog N17's `810 files` is false for the promoted
run and must not be checked off.

The likely source of 810 is historical cache language (`tests/test_w2b_cfbd.py` calls the older
pre-array cache “~810”), but that is not the promoted run's manifest value.

## V2 — PFF's 149 is a raw-payload count, not an observation count

`app/data/pff_exports/pff_unique_payload_inventory.csv` contains 149 unique payload rows totaling
72,259,806 bytes. Their internal source-row counts sum to 134,392 across 14 league/report lanes
(seven report families in each of NCAA and NFL). Therefore catalog N15 cannot label `149` as
`obs (payload grain)`: 149 is a raw-file/payload count. If the catalog needs source observations,
it must row the league/report streams and state the overlap/deduplication rule before aggregating.

The seven report families are `passing_depth`, `passing_pressure`, `passing_summary`,
`receiving_depth`, `receiving_scheme`, `receiving_summary`, and `rushing_summary`.

## V3 — Table B-N counts independently reproduced

Direct SQLite counts reproduce:

- PlayerProfiler: 44,462 gamelog-week; 230,394 roster-week; 949,041 PBP-slot; 280,868
  PBP-play; 9,768 medical-history; 5,476 player-season; 3,290 identity; 57 + 6 capture rows.
  This reconciles to 1,520,009 `obs` + 3,290 `idn` + 63 `cap`.
- FantasyCalc forward: 20,043 raw `obs`; 20,043 joinable `alt`. The raw source is `fc_native`,
  snapshot dates 2026-06-24 through 2026-08-05.
- Legacy `fc_snapshots`: 2,185 DynastyProcess rows (2021-09-08 through 2024-09-08) and 4,605
  FantasyCalc rows (2026-06-12 through 2026-06-24), total 6,790. It is a mixed-source store.
- League transactions: 932 transaction `obs`, 1,692 movement `obs` at a different grain, and four
  capture rows.

## V4 — N12/N13 do not inherit the 09:20 scheduled cadence

The daily 09:20 plist is `com.davidleess.dynasty-league-capture` and runs
`scripts/run_league_snapshot_capture.py` into `app/data/league_runtime`. It does **not** run
`scripts/run_league_transaction_capture.py` and does not refresh `league_transactions.db`.
Repository search finds no scheduled invocation of the transaction-capture entrypoint. Its durable
marker reports a manual/one-off chain run finishing `2026-07-31T02:22:34.154335+00:00`.

Catalog N12/N13's consumer state `league context` is not an R7 consumer name. No production import
of `src.dynasty_genius.league_transactions` exists outside the capture script. Pending contrary
evidence, consumer state is `none`, and stream cadence is `manual_only` / absent schedule.

## V5 — R1 `nfl_data_py` physical state is a provenance mismatch

There is no Python import of `nfl_data_py` in the repository. `scripts/ingest_2026_draft.py` imports
`nflreadpy`, calls `nfl.load_draft_picks([2026])`, and writes an 80-player JSON artifact at
`resources/prospect_identity_2026.json`. Both the script and artifact label the source
`nfl_data_py_verified_nfl_draft` despite the actual loader being `nflreadpy`.

Consequences for the catalog:

- R1 is not an independently verified `nfl_data_py` capture.
- The physical artifact exists, but its source label and declared `parquet_snapshot` cache policy
  do not match the actual JSON/nflreadpy route.
- This is a source identity/provenance defect to record, not evidence that the named source is
  captured.

## V6 — R4 `ras` is fixture-only

`src/dynasty_genius/adapters/ras_adapter.py` defaults to
`resources/fixtures/ras_mock.csv`. That fixture is the only RAS data file found. The adapter and its
tests therefore establish fixture behavior, not a production RAS capture. Physical state:
`fixture_only`, no real-source capture, no scheduled refresh.

## V7 — R18 QB context is a live, consumer-triggered provider read

`fetch_qb_nfl_stats` in `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py` calls
`nfl.load_pbp(seasons)` and aggregates in memory. `app/services/roster_auditor.py` invokes it for
2024 and 2023 while building QB context cards. No raw snapshot or governed cache is written by this
path.

The registry declares `parquet_snapshot`, but physical behavior is `live_direct_read`,
consumer-triggered/on-demand, absent capture. It needs its own Table B stream row and must not be
treated as a captured weekly source merely because `freshness_hours = 168` is declared.

## V8 — R20 validation is registered but has no physical capture

The registry declares raw snapshots under `app/data/backtest/qb_validation/raw/`; that path has zero
files and the study has not run. Physical state is `registered_and_pinned; not captured`. QB rushing
production (H2) remains a registered hypothesis **under test**, with no result.

## V9 — Option A three-lane reconciliation

Gemini's independent response at
`docs/agent-ledger/evidence/2026-08-06/gemini_option_a_pressure_test_response.md` recommends Option
A, matching Claude and Codex. Two sentences require temporal/scope correction before consolidation:

1. It says the recovery backup is “still uploading”; upload has completed and the sequential
   restore/hash-verification drill is now running. Success is still unclaimed until the durable
   marker advances.
2. It says the 189.32 MiB Parquet directory can be “safely” added to the backup manifest. Manifest
   inclusion is a design precondition, but operational safety is not yet established while the
   current recovery run remains unfinished. Exact inclusion/retention and a non-duplicating ceiling
   must be proven, not inferred from size alone.

The cross-lane recommendation remains Option A: capture all five feature-refresh provider streams
into Layer 1 and have the feature job consume last-good canonical data. This is planning only; no
implementation or enablement authority is inferred.

## V10 — Table A arithmetic and route summary are false

The 20 registry keys and their declared role/cache/freshness/failure fields reproduce. Two prose
summaries immediately below the table do not:

- R10, R11, R12, R14, R15, R16, and R17 are **seven** prohibited-or-deferred sources with no
  capture, not six.
- “Only R19 has a production capture route built by an agent” is false. At minimum R8
  (`fantasycalc`) has the daily `run_fc_forward_capture.py` route and a 20,043-row store; R13 has a
  durable transaction-capture entrypoint/store even though it is not scheduled; R2 has the CFBD
  foundation capture/promotion path. Those routes have different operational states, but they
  exist. The catalog should state each route's measured state instead of collapsing authorship and
  production status into one sentence.

## Rerunnable probes

```bash
jq '{run_id,captured_at,raw_file_count,row_count,raw_content_sha256}' \
  app/data/sources/cfbd_foundation/manifest_latest.json

sqlite3 app/data/playerprofiler.db \
  "SELECT 'pp_gamelog_week',count(*) FROM pp_gamelog_week;"

sqlite3 app/data/fc_forward_capture.db \
  "SELECT source,min(snapshot_date),max(snapshot_date),count(*) \
   FROM fc_forward_capture_raw GROUP BY source;"

rg -n '(^|\\s)(import nfl_data_py|from nfl_data_py)' --glob '*.py' .
rg -n 'run_league_transaction_capture' ops
find app/data/backtest/qb_validation -type f
```
