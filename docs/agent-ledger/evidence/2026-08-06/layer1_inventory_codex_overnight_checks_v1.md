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

## V11 — Canonical nflverse export state is independently verified

`app/data/nflverse_usage/export/nflverse_usage.ready.json` names all 12 materialized streams plus
the unresolved-identity companion artifact. Every named Parquet file exists and independently
recomputes to the marker's SHA-256. The 12 stream row counts match B1–B12 and sum to 1,491,691.

Therefore the `exported = ✓` cells for B1–B12 are independently supported at run
`nflverse-usage-20260805T1334216901700000`, captured
`2026-08-05T13:34:21.690170+00:00`. This verifies export existence/integrity, not a consumer for
B4–B12 and not a scheduled refresh cadence.

## V12 — PFF's partial consumer is one precise lane

`scripts/build_college_features.py` reads `app/data/pff_exports/phase16_wr_manifest.json`. Its nine
entries resolve exactly to NCAA `receiving_summary`, `REGPO`, seasons 2017–2025 in the unique
payload inventory. Those files exist and their hashes match their content-hash filenames.

Thus “PFF has a partial consumer” is supported, but the consumer applies to this one precise
league/report/scope lane. It is not evidence that the other 13 league/report lanes are consumed.

## V13 — The canonical source table was not reconciled after V5–V8

Commit `917ffbd` adds the correct physical truths in §3.2, but §2.1—the actual 20-row source
inventory—still says R1, R4, and R18 are `UNVERIFIED`, still describes R20 only as “pinned study
inputs,” and §1 still says six capture-state cells are unverified. Table A-P also leaves PFF and
CFBD `UNVERIFIED` despite the independently measured inventories above.

The prose summary below Table A has two additional live errors already named in V10: seven sources
are prohibited/deferred, not six, and R19 is not the only source with a built capture route. A
correction appendix does not reconcile a stale canonical row; the Table A cells and progress text
must carry the current truth before A can be checked off.

## V14 — Lower catalog text still describes completed enumeration as missing

After Table B-N was added, the paragraph headed “STREAMS NOT YET IN THIS TABLE” still lists
PlayerProfiler, PFF, CFBD, FantasyCalc, and Sleeper as missing. It also says B4's consumer state is
unverified even though the catalog change log and prior independent probe resolve it. Separately,
the export disclaimer says all B1–B12 exports remain unverified; V11 now verifies those exact files
and hashes.

These are state-reconciliation defects: the new rows are correct, but the same document still
asserts their prior absence.

## V15 — R18 is a second live consumer of `pbp`, not a sixth ingestion stream

Feature Refresh B18 calls `nfl.load_pbp(seasons)`. R18's adapter wrapper calls the same
`nfl.load_pbp(seasons)` and Roster Auditor consumes its in-memory aggregate. Under R1
source/stream/store separation, this is one upstream PBP dataset stream with two live consumer
routes, not two ingestion streams.

Disposition:

- R18 belongs in the **architectural** Option A scope because its live route should ultimately read
  canonical last-good PBP too.
- It does **not** silently widen David's named five-stream implementation decision. It is a second
  consumer migration with its own parity/control gate after canonical PBP capture exists.
- The catalog should row Roster Auditor as an additional consumer edge on B18 (and record the
  R18 registry/provenance mismatch), not create a duplicate Table B source stream.

## V16 — The actual scheduled Sleeper stream is absent from Table B

Correcting N12/N13 to `manual_only` exposed a second omission: the daily 09:20 job's actual output,
`app/data/league_runtime`, has no stream row at all.

Measured state:

- `com.davidleess.dynasty-league-capture` is installed/loaded and runs
  `scripts/run_league_snapshot_capture.py` daily at 09:20.
- `app/data/logs/league_capture.out.log` records 21 successful runs from 2026-07-16 through
  2026-08-05; current `launchctl print` reports loaded, not running, last exit 0.
- `ready_latest.json` names run `league-20260805T132003Z`, source-captured at
  `2026-08-05T13:20:03.348137+00:00`, with six SHA-pinned artifacts.
- The source snapshot has schema `sleeper_universe_snapshot.v1` and contains 12,209 classified
  players, 12 rosters, 14 users, 109 future-pick rows, league settings, and draft state. The run
  directory is marker-pinned and contains the source snapshot plus five derived artifacts.
- The builder fetches Sleeper league, rosters, users, traded picks, all players, NFL state, latest
  draft, and draft picks. This is distinct from historical transactions/movements.

Catalog consequences:

- Add one Sleeper universe/league-state snapshot-bundle stream row (with the component endpoint
  grains stated), captured/exported daily and consumed by the league derivation chain.
- Add `app/data/league_runtime` to A7's physical stores.
- Keep N12/N13 manual and consumerless. The 09:20 cadence belongs only to this omitted runtime
  stream.
- Do not count the five derived artifacts as five ingested source streams; they are downstream
  outputs of the one coherent snapshot bundle.

## V17 — N18 is a normalized snapshot, not a raw endpoint capture

The V16 row correctly adds a missing scheduled Layer-1 route, but its current count/grain statement
is not supportable as written. `scripts/build_sleeper_universe_snapshot.py::build_snapshot` fetches
eight Sleeper endpoint payloads, then passes them through
`src.dynasty_genius.sleeper_universe.build_universe_snapshot`. Only that transformed result is
written as `snapshot.json`; the exact endpoint response bytes are not retained.

Specific grain defects in the current N18 row:

- `league (5)` and `draft_state (18)` are counts of keys in normalized mappings, not observation
  counts.
- `coverage (10)` is a count of keys in a repo-derived coverage report, not a source endpoint
  grain.
- `future_picks` is reconstructed from league settings, roster IDs, draft rounds, and traded-pick
  input; its 109 rows are derived future-pick records, not raw `traded_picks` endpoint rows.
- the 12,209 `players` are normalized/classified rows over a union of source players, rostered IDs,
  draft IDs, and optional prospect/market IDs. They are not raw `get_all_players` records.
- rosters and users remain list-shaped source components, but their presence inside the normalized
  bundle does not make the bundle an exact raw snapshot.

The lineage block hashes players, league, rosters, users, and traded picks, but does not retain the
source payloads and does not hash NFL state, draft state, or draft picks separately. The ready
marker hashes the normalized `snapshot.json` plus five derived artifacts. Therefore N18 is
scheduled, marker-pinned, and consumed, but physical capture state must say **normalized snapshot;
raw endpoint replay unavailable**. The source count cell should list output-component grains as
such and must not label dictionary-key counts or derived coverage as endpoint observations.

## V18 — R13 still omits the newly found physical Sleeper route

Table A-P A7 correctly adds `app/data/league_runtime`, but canonical registry row R13 still says
physical state is only ``league_transactions.db — transactions only``. The two source tables
therefore disagree after V16. R13 must name both measured physical routes, preserving their
different states: scheduled normalized league/universe snapshot versus manual transaction capture.

## V19 — N18's “THE ONE” heading is false

The heading calls N18 “THE ONE SCHEDULED, CAPTURED, CONSUMED LAYER-1 STREAM.” The same catalog
records FantasyCalc forward capture as daily, captured, and consumed by market-overlay jobs. N18 is
an important missing counterexample to the nflverse store's manual-only status, but it is not the
only scheduled/captured/consumed Layer-1 stream. The heading should say it is **a** scheduled stream
that was missing.

## V20 — The export-verification paragraph retains its superseded contradiction

The B1-B12 export paragraph first records independent SHA verification and then keeps a malformed
parenthetical saying the checkmarks are “owed, not confirmed.” That superseded text is both
contradictory and missing its closing delimiter. It must be removed rather than retained beside the
current truth.

## V21 — Verification-state labels are stale after the independent pass

Section headings still say Table A-R and Table B-N are “Claude-measured, awaiting R4,” and Table
A-P says “status unchanged from v3.” Multiple cells in those tables now have independent Codex
probes plus Claude reproduction. Whole-table completion remains blocked, but the headings should
distinguish **independently verified cells** from **table not yet complete**; saying the entire
tables await independent verification is no longer accurate. The job matrix should also attach the
new cadence evidence at
`docs/agent-ledger/evidence/2026-08-06/layer1_cadence_codex_overnight_v1.md` rather than continuing
to describe path/timestamp evidence as wholly outstanding.

## V22 — The gap and disposition sections still say completed enumeration is owed

Section 6 lists “The 20 registry definitions not yet rowed” as a current gap even though §2.1 now
contains all 20. Section 7 likewise says full registry enumeration and non-nflverse stream rows are
“still owed,” even though both were subsequently added. These are historical dispositions being
presented as live blockers. Section 6 should retain only current gaps, and §7 should be clearly
labelled historical or have its superseded owed-list removed.

## V23 — The backup-alarm withdrawal is duplicated

Section 4.3 repeats the numbered “Timeout as mechanism — WITHDRAWN” item twice. This is cosmetic,
but the duplicate sits in the operational source-of-truth section and should be removed during the
same reconciliation pass.

## V24 — V17 corrected the N18 table row but left the canonical prose counts stale

The N18 Table B-N row now correctly strikes the dictionary-key counts and labels the normalized /
derived grains. The earlier N18 prose block still says “Snapshot grain, verified key by key:
12,209 players · 12 rosters · 14 users · 109 future_picks · league 5 · draft_state 18 · coverage
10.” That is the exact statement V17 falsified. The prose block must carry the corrected grain too;
fixing only the table recreates the correction-without-canonical-reconciliation defect.

## V25 — V20 removed the parenthetical opener but left its contradictory body

The export-verification paragraph now ends correctly, but the next standalone lines still read
“membership in the canonical export as understood, not a probe. Treat as owed, not confirmed.”
Those lines are the body of the superseded malformed parenthetical and still contradict the
independent SHA verification. They must be removed entirely.

## V26 — All 20 registry declaration columns independently verify

At HEAD `1d5e6c34ae8744dfadd6ae013c042e0e4239913b`, Codex loaded `SOURCE_REGISTRY`, parsed all 20
R1–R20 markdown rows, and compared these declared columns mechanically: registry key, role set,
`cache_policy`, `freshness_hours`, and `failure_behavior`. All 20 rows matched exactly; zero
declaration mismatches. Source file pin:
`src/dynasty_genius/sources/source_registry.py` SHA-256
`a840d6f72c3bbdbe36a69e2aca7bf9cbf05c7cdafc75353b78217a28be6eccd6`.

This independently verifies the machine-declaration cells only. It does not verify the separately
inferred access-class cells or any physical capture state not already covered by V1–V18. The Table
A heading can now narrow its remaining R4 work accordingly instead of treating the registry
declarations as Claude-only measurements.

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
