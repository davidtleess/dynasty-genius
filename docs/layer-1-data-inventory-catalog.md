# Layer 1 Data Inventory Catalog

**The durable tracked artifact David ordered on 2026-08-05.** Not a chat summary, not a scratch file.

> **David's ruling (verbatim extract):** *"take full inventory on Layer 1 data - sources, ingestion
> streams, refresh frequencies, --- then granularly take inventory of the catalog, the Player 360,
> the semantic layer and metrics, and the schemas - KEEP TRACK OF THIS INVENTORY DILIGENTLY - tell me
> what sources we still need to injest - and when we've done that work - and finishe updated and
> checked off everything clearly and cleanly on the Layer 1 Data Inventory Catalog --- THEN we will
> have a long and deep research session on how layer 2 should consume layer 1."*
> Full text: `docs/agent-ledger/2026-08-05.md`, 22:15 entry.

**THE GATE: the Layer 2 consumption research session does not open until this catalog is complete
and checked off.** No agent opens Layer 2 design work off this document.

**Authority note.** Agent-authored inventory. It records measured state and gaps. **It does not rule
on priority, sufficiency, or what to build** — `05` §1 sequencing is David's.

**v2 — REBUILT after Codex returned NOT CLEAR on v1 with seven findings.** All seven accepted, none
contested; F3, F4 and F6 independently reproduced before rebuilding. Disposition: §7.

---

## §0. Rules

**R1 — SOURCE ≠ STREAM ≠ STORE.** Three entities, three grains. A source with four loaders is one
A-row and four B-rows. *(Codex INV-1, hardened by F2.)*

**R2 — every cell is a MEASURED pin or is marked `UNVERIFIED`.** `docs/data-inventory.md` is
discovery input, **never** inherited confirmation — it is internally stale.

**R3 — JOB cadence ≠ FRESHNESS cadence ≠ STREAM cadence.** Three different clocks. **A consumer
job's cadence is NOT its upstream stream's ingestion cadence** *(F4)*.

**R4 — CHECKED OFF only on independent verification.** Claude authors, Codex verifies each cell
against a pinned probe, Gemini supplies operational facts. A cell Claude measured alone is
`measured`, not `verified`.

**R5 — GRAIN-TAGGED COUNTS ONLY.** *(F3, the rule that produced the worst v1 error.)* A store total
is **not** a source-observation count. Every count is tagged:
`obs` = source observation rows · `idn` = identity/bridge rows · `cap` = capture-ledger/metadata rows
· `alt` = an alternate representation of rows already counted. **`alt` is never added.**

**R6 — gaps separated by KIND:** absent source · absent loader · absent capture · absent
normalization · absent consumer · absent schedule.

**R7 — stream STATE is multi-valued, never one cell** *(F6)*: `bound` (a StreamSpec exists) ·
`captured` (rows in a store) · `exported` · `consumed` · `decision_supported`. A stream can be bound
and never captured.

---

## §1. Progress

- [ ] **A. Sources** — **all 20 registry definitions now enumerated** in §2.1 with their declared
      role/cache/freshness/failure fields and a separately-stated physical capture state, including
      the deferred, fixture-only and prohibited states (F1's named blocker). **Codex V5–V8 + V10–V13
      resolved the physical capture states and they are now carried in the §2.1 rows themselves, not
      in an appendix.** **Still UNCHECKED:** R4 requires independent per-cell verification of the
      corrected table, and the two **provenance defects** it surfaced (R1's `nfl_data_py` mislabel,
      R18's declared-vs-actual route) are recorded but unresolved.
      *(This line previously asserted "six capture-state cells are `UNVERIFIED`" and was left standing
      after V5–V8 resolved four of them — the §5 defect again, in the progress block that is supposed
      to describe the document's own state. **No count is stated here now**; §2.1 is the source of truth.)*
      *(Deliberately carries NO row-count total for the physical table — a count describing a table
      in the same commit that changes it is the §5 defect, instances 5 and 6. Counts come from a
      probe, not from this document.)*
- [ ] **B. Ingestion streams** — **the five direct provider reads are rowed (B15–B19)**, the
      non-registry gap is recorded in §2.2, and **PlayerProfiler, FantasyCalc, Sleeper, PFF and CFBD
      are now rowed by grain in §3.1 (Table B-N)**. **Still missing:** per-stream
      `bound`/`captured`/`exported` states on B-N, refresh cadence per stream, and the
      validation/context streams. **No B-N row is verified** — R4 makes a Claude-only measurement
      `measured`, not checked off.
- [ ] **C. Refresh frequencies** — **REOPENED (F4/F5).** Job matrix received; stream↔job edges wrong
      in v1 and now corrected; per-stream cadence unresolved.
- [ ] **D. Catalog** · [ ] **E. Player 360** · [ ] **F. Semantic layer + metrics** · [ ] **G. Schemas**
      *(phase B — CLOSED until A–C clear)*
- [ ] **H. Sources we still need to ingest** *(§6 — cannot be answered yet, F7)*
- [ ] **I. Every row independently verified** · [ ] **J. → Layer 2 research opens**

> **v1 marked A and B `[x]`. That was false** — enumeration was partial and the checkmarks asserted
> a completeness that did not exist. Unchecked and reopened.

---

## §2. Table A — SOURCES

### §2.1 Table A-R — the 20 machine-registry definitions
*(F1 CLOSED. **Mixed verification state *(V21)*: several cells now carry INDEPENDENT Codex probes plus Claude reproduction — R1/R4/R18/R20 physical states, the seven-source count, the built-route claim. Others remain Claude-measured only. Whole-table completion is still blocked; it is no longer true that the entire table awaits independent verification.)***

**Enumerated 2026-08-06** by loading `SOURCE_REGISTRY` from
`src/dynasty_genius/sources/source_registry.py` and dumping every dataclass field — not by reading
prose. Rerunnable:

```bash
.venv/bin/python3.14 -c "from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY; \
print(len(SOURCE_REGISTRY)); [print(k) for k in SOURCE_REGISTRY]"
# measured: 20
```

`role` · `cache_policy` · `freshness_hours` · `failure_behavior` are **registry declarations**, not
observed behaviour. **Capture state is a separate, physical question** and is the last column;
`UNVERIFIED` there means no probe was run this session, per R2.

| # | Registry key | Role | Cache policy | Fresh (h) | On failure | Access class | Capture state (physical) |
| :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| R1 | `nfl_data_py` | model_input + training_label | `parquet_snapshot` | 168 | `use_cached` | free | **NOT a `nfl_data_py` capture — PROVENANCE DEFECT.** No `nfl_data_py` import exists; `ingest_2026_draft.py` uses **nflreadpy**, writes JSON, labels it `nfl_data_py_verified_nfl_draft` *(V5)* |
| R2 | `cfbd` | model_input | `json_cache` | 720 | `skip_enrichment` | **paid** | partial — `sources/cfbd_foundation/`; promoted 2026-08-04 |
| R3 | `playerprofiler` | context_signal | `json_cache` | — | `skip_enrichment` | **manual, by David** | `playerprofiler.db` — 1,520,009 `obs` |
| R4 | `ras` | context_signal | `json_cache` | — | `skip_enrichment` | free | **`fixture_only`** — adapter defaults to `resources/fixtures/ras_mock.csv`, the only RAS data file *(V6)* |
| R5 | `pff` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | 149 payloads / 7 families; 1 partial consumer |
| R6 | `rotoviz` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | **fixture-only — no capture** |
| R7 | `campus2canton` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | **fixture-only — no capture** |
| R8 | `fantasycalc` | market_overlay | `json_cache` | 24 | `use_cached` | free | `fc_forward_capture.db` — 20,043 `obs` |
| R9 | `mfl_rookie_adp` | market_overlay | `json_cache` | 24 | `use_cached` | free | **no capture** — overlay destination undesigned |
| R10 | `dynasty_data_lab` | market_overlay | `none` | — | `skip_enrichment` | **paid** ($4/1k req) | **deferred — no capture** |
| R11 | `dynasty_nerds` | market_overlay | `none` | — | `skip_enrichment` | no clean API | **deferred — no capture** |
| R12 | `ktc` | market_overlay | `none` | — | `skip_enrichment` | **PROHIBITED** — ToS bars scraping | **none, by rule** |
| R13 | `sleeper` | context_signal | `json_cache` | 1 | `use_cached` | free | **TWO measured routes, different states *(V18)*:** (a) **`app/data/league_runtime/` — SCHEDULED daily 09:20, normalized snapshot, consumed, raw replay unavailable** *(N18)*; (b) `league_transactions.db` — **manual_only**, no consumer |
| R14 | `sportradar` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — ~$7,200/yr | **none, by rule** |
| R15 | `genius_sports` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — enterprise | **none, by rule** |
| R16 | `stats_perform` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — enterprise | **none, by rule** |
| R17 | `rolling_insights` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — $4,200–7,200/yr | **none, by rule** |
| R18 | `nflreadpy_qb_context` | context_signal | `parquet_snapshot` | 168 | `skip_enrichment` | free | **`live_direct_read`, consumer-triggered** via Roster Auditor; no snapshot, no cache. **A SECOND LIVE CONSUMER OF THE B18 `pbp` STREAM — not its own stream** *(V7/V15)*. Declared `parquet_snapshot` ≠ actual route |
| R19 | `nfl_nextgen_stats` | context_signal | `sqlite_store_with_raw_snapshots` | 168 | `use_cached` | free | **canonical** — `nflverse_usage.db`, B1–B13 |
| R20 | `nflreadpy_qb_validation` | **validation_study** | `parquet_snapshot` | — | `fail_closed` | free | **`registered_and_pinned; NOT captured`** — `app/data/backtest/qb_validation/raw/` holds **zero files**; the study has not run *(V8)*. Walled to `eval/qb_validation/` |

**Registry composition, corrected *(V10)*:** **SEVEN** prohibited-or-deferred with no capture by
rule — R10, R11, R12, R14, R15, R16, R17 *(this read "6" and was arithmetic, not judgement)* ·
3 fixture/manual-export only (R5–R7) · 1 validation-pinned (R20) · 1 canonical multi-stream
adapter (R19).

**The claim "Only R19 has a production capture route built by an agent" is WITHDRAWN — it was
false.** Built capture routes also exist for **R8 `fantasycalc`** (`scripts/run_fc_forward_capture.py`,
daily, 20,043-row store), **R13 `sleeper`** (`scripts/run_league_transaction_capture.py`, durable
store, **not scheduled**), and **R2 `cfbd`** (`scripts/run_cfbd_foundation_refresh.py`, paid,
capture + promotion path). Those routes differ in operational state; **each row states its own
measured state rather than collapsing authorship and production status into one sentence.**

### §2.2 ⛔ NEW FINDING — five production provider reads that NO registry entry declares

**Measured 2026-08-06.** `scripts/run_feature_refresh.py::_load_source` pulls **`player_stats`,
`rosters`, `snap_counts`, `pbp`, `participation`** directly from `nflreadpy` on every 09:15 fire.
**No entry in Table A-R declares these frames as that job uses them.** The three near-neighbours
are each a different use, verified field-by-field:

- `nfl_data_py` (R1) — `allowed_fields` = `pick · round · age · team · draft_year` (draft capital).
- `nflreadpy_qb_context` (R18) — `allowed_fields` = `cpoe · epa_per_dropback · dropback_count ·
  dakota · pass_attempts`.
- `nflreadpy_qb_validation` (R20) — pinned study inputs, `fail_closed`, walled to
  `src/dynasty_genius/eval/qb_validation/` by the F33 wall.

`01` §Source Adapter Rules requires one adapter per external source, a raw snapshot before parsing,
and source-timestamp/parser-version provenance. **These five reads satisfy none of those.** Recorded
as a MEASURED FACT and a gap of kind *absent source declaration* + *absent capture* (R6). **Not
authority to build, register, or schedule anything.** This is the object of David's A/B pressure
test — see `docs/agent-ledger/evidence/2026-08-05/layer1_feature_refresh_route_recommendation_claude_v1.md`.

### §2.3 Table A-P — PHYSICAL sources present in the repo
*(**PFF and CFBD rows now carry independently verified inventories *(V1/V2/V12)*; A7 carries the V16 route addition.** Remaining rows are Claude-measured.)*

| # | Source (provider + dataset family) | Access | Stores | Status |
| :-- | :-- | :-- | :-- | :-- |
| A1 | nflverse via `nflreadpy 0.1.5` | free | `nflverse_usage.db` | partial |
| A2 | PlayerProfiler | **manual, by David** | `playerprofiler.db` | partial |
| A3 | PFF | **manual, by David** | `app/data/pff_exports/` | **measured** — 149 payloads / 134,392 internal source rows / 14 lanes *(V2)*; consumer is ONE lane *(V12)* |
| A4 | CFBD | **paid** | `sources/cfbd_foundation/` | **measured** — promoted run `20260802T024342156864Z`, **1,202** raw payloads, 874 curated rows *(V1)* |
| A5 | FantasyCalc | free | `fc_forward_capture.db` + part of `fc_snapshots.db` | partial |
| A6 | **DynastyProcess** *(ONE source — v1 split it into A7/A9 by loader, F2)* | free, GPL-3.0 repo | pinned `values.csv`; part of `fc_snapshots.db` | partial |
| A7 | Sleeper | free | `league_transactions.db` *(transactions — **manual_only**, no consumer)* **+ `app/data/league_runtime/` (daily 09:20 snapshot bundle, 21 runs, consumed — added V16)** | partial |

**A6 DynastyProcess is in NO registry entry** — a physical source with pinned data and no machine
declaration. Recorded, not opened.

**Derived — OUR OUTPUT, not fuel:** `model_forward_capture.db`, `market_divergence_history.db`.
Never counted as ingested source data.

**Licence:** David approved using **and saving** DynastyProcess data 2026-05-30. The generic
retention/licence blocker was agent-manufactured and is withdrawn.

---

## §3. Table B — STREAMS, grain-tagged *(INCOMPLETE — F1)*

Measured 2026-08-05, read-only, at commit `2a42759`. **13 loader-bound StreamSpecs; 12 materialized
as source tables.** *(V2-F3: "13 streams" conflated bound specs with materialized tables.)*

**R7 state columns — all five, never collapsed** *(V2-F2)*. `consumed` names the consumer or `none`;
**the landing-disposition vocabulary (`substrate_only`/`blocked_for_use`) is a SEPARATE column and
must never sit in a state cell** — v2 put `blocked_for_use` in B14's consumer cell.

| # | Stream | Table | `obs` | bound | captured | exported | consumed | dec_sup | disposition |
| :-- | :-- | :-- | --: | :-: | :-: | :-: | :-- | :-: | :-- |
| B1 | `ngs_passing` | `ngs_passing` | **5,933** | ✓ | ✓ | ✓ | feature refresh (via export) | ✗ | `existing_consumer` |
| B2 | `ngs_rushing` | `ngs_rushing` | **6,059** | ✓ | ✓ | ✓ | " | ✗ | `existing_consumer` |
| B3 | `ngs_receiving` | `ngs_receiving` | **14,731** | ✓ | ✓ | ✓ | " | ✗ | `existing_consumer` |
| B4 | `snap_counts` | `player_snap_count` | **253,106** | ✓ | ✓ | ✓ | **none** — canonical export has no production consumer; the daily job's `nflreadpy.load_snap_counts` is a SEPARATE provider-read stream *(V2-F4, Codex probe)* | ✗ | `substrate_only` |
| B5 | `injuries` | `nflverse_injury_report` | **45,337** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B6 | `pfr_pass` | `pfr_pass` | **5,424** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B7 | `pfr_rush` | `pfr_rush` | **18,461** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B8 | `pfr_rec` | `pfr_rec` | **35,724** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B9 | `pfr_def` | `pfr_def` | **62,345** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B10 | `ff_opportunity` | `ff_opportunity` | **47,282** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B11 | `ftn_charting` | `ftn_charting` | **185,215** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B12 | `depth_charts` | `depth_charts` | **812,074** | ✓ | ✓ | ✓ | none | ✗ | `substrate_only` |
| B13 | `contracts` | *(absent)* | **0** | ✓ | **✗ never run** | ✗ | none | ✗ | `substrate_only` |
| B14 | `ff_rankings` | *(none)* | 0 | ✗ | ✗ | ✗ | none | ✗ | `blocked_for_use` |
| B15 | `player_stats` **(direct provider read — §2.2)** | *(none)* | 0 | ✗ | ✗ | ✗ | **09:15 Feature Refresh, live from `nflreadpy`** | ✗ | **undeclared — see §2.2** |
| B16 | `rosters` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | " | ✗ | **undeclared** |
| B17 | `snap_counts` **(direct provider read — DUPLICATE of B4)** | *(none)* | 0 | ✗ | ✗ | ✗ | " | ✗ | **undeclared — two live routes to one source** |
| B18 | `pbp` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | " | ✗ | **undeclared** |
| B19 | `participation` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | " | ✗ | **undeclared** |

### ⛔ N18 — **A** SCHEDULED, CAPTURED, CONSUMED LAYER-1 STREAM THAT WAS MISSING ENTIRELY

**Found only because correcting my own N12/N13 cadence error exposed it *(V16, Codex)*.** I had
attributed the daily 09:20 cadence to the transaction tables; when that was withdrawn, the cadence
had no stream to belong to — and the real one had **no row in this catalog at all.**

Measured and independently reproduced:
* `com.davidleess.dynasty-league-capture` runs `scripts/run_league_snapshot_capture.py` **daily at
  09:20**, loaded, **last exit 0**.
* **21 successful runs**, 2026-07-16 → 2026-08-05 (`app/data/logs/league_capture.out.log`).
* `ready_latest.json` pins run **`league-20260805T132003Z`**, source-captured
  **`2026-08-05T13:20:03.348137+00:00`**, with **six** SHA-pinned artifacts.
* Snapshot grain, verified key by key: **12,209** players · **12** rosters · **14** users ·
  **109** `future_picks` · `league` 5 · `draft_state` 18 · `coverage` 10.

**Corrections this forces:**
1. **`app/data/league_runtime` is added to A7's physical stores** — it was not listed.
2. **N12/N13 stay `manual_only` and consumerless.** The 09:20 cadence belongs **only** to N18.
3. **The five derived artifacts** (`coverage`, `provenance`, `roster_cut_report`, `team_posture`,
   `team_value_matrix`) are **downstream outputs of one coherent bundle — NOT five ingested source
   streams.** Counting them as streams would inflate the inventory with our own outputs, which is the
   same error class as counting `model_forward_capture.db` as fuel.
4. **PHYSICAL CAPTURE STATE: `normalized snapshot; RAW ENDPOINT REPLAY UNAVAILABLE` *(V17)*.**
   `build_snapshot` fetches eight Sleeper endpoints and passes them through
   `build_universe_snapshot`; **only the transformed result is written.** The exact endpoint response
   bytes are never retained, and the lineage block hashes players/league/rosters/users/traded-picks
   but not NFL state, draft state, or draft picks. **A marker-pinned normalized bundle is not a raw
   capture**, and this stream cannot satisfy `01` §Source Adapter Rules' raw-snapshot-before-parsing
   requirement as it stands. *(My V16 row implied otherwise by listing everything as flat counts.)*
5. **This materially qualifies the session's headline finding.** *"The canonical ingestion store has
   NO SCHEDULED REFRESH"* remains true **of `nflverse_usage.db`** — but it must never be read as
   *"Layer 1 has no scheduled ingestion."* **N18 is scheduled, captured, marker-pinned, and
   consumed.** It is the counter-example, and the catalog missed it.

**B15–B19 are streams with a PRODUCTION CONSUMER and NO capture** — the exact inverse of B5–B13
(captured, no consumer). They are rowed here because R1 makes a stream an inventory entity whether
or not we store it; `obs = 0` records that **we keep nothing**, not that nothing flows. **B17 is the
duplicate route to B4** (`player_snap_count`, 253,106 `obs`). Disposition for all five is David's
open A/B decision, not the catalog's to assign.

### §3.1 Table B-N — NON-NFLVERSE streams
*(F1/F6 blocker. **Mixed verification state *(V21)*: PlayerProfiler/FantasyCalc/Sleeper counts, the CFBD 1,202 figure, the PFF 149/134,392 split and its one consumer lane are INDEPENDENTLY verified; per-stream R7 states and cadence are not. Table not complete.**)*

Measured by opening each store and counting per table, then decomposing by R5 grain. **`alt` is
never added to a total.**

| # | Source | Stream / table | Count | Grain | Consumer state |
| :-- | :-- | :-- | --: | :-- | :-- |
| N1 | PlayerProfiler | `pp_gamelog_week` | 44,462 | `obs` | none |
| N2 | PlayerProfiler | `pp_roster_week` | 230,394 | `obs` | none |
| N3 | PlayerProfiler | `pp_pbp_slot` | 949,041 | `obs` | none |
| N4 | PlayerProfiler | `pp_pbp_play` | 280,868 | `obs` | none |
| N5 | PlayerProfiler | `pp_medical_history` | 9,768 | `obs` | none |
| N6 | PlayerProfiler | `pp_player_season` | 5,476 | `obs` | none |
| N7 | PlayerProfiler | `pp_identity_bridge` | 3,290 | `idn` | — |
| N8 | PlayerProfiler | `pp_capture` + `pp_pbp_capture` | 57 + 6 | `cap` | — |
| N9 | FantasyCalc | `fc_forward_capture_raw` *(source `fc_native`, snapshots 2026-06-24 → 2026-08-05)* | 20,043 | `obs` | market overlay |
| N10 | FantasyCalc | `fc_forward_capture_joinable` | 20,043 | **`alt`** | **never added** |
| N11 | **MIXED-SOURCE store** *(V3)* | `fc_snapshots` = DynastyProcess **2,185** (2021-09-08 → 2024-09-08) + FantasyCalc **4,605** (2026-06-12 → 2026-06-24) | 6,790 | `obs` | market overlay |
| N12 | Sleeper | `league_transaction` | 932 | `obs` | **none** *(V4 — corrected)* |
| N13 | Sleeper | `league_transaction_movement` | 1,692 | `obs` *(different grain)* | **none** *(V4 — corrected)* |
| N14 | Sleeper | `league_season_capture` | 4 | `cap` | — |
| **N18** | **Sleeper — league/universe NORMALIZED SNAPSHOT** *(V16 added it; V17 corrected its grain)* | `app/data/league_runtime/runs/<run_id>/snapshot.json`, schema `sleeper_universe_snapshot.v1` | **players 12,209** *(normalized/classified over a UNION of source players + rostered/draft/prospect IDs — **not** raw `get_all_players`)* · **rosters 12** · **users 14** *(list-shaped source components)* · **future_picks 109 — DERIVED**, reconstructed from settings/roster IDs/rounds/traded-pick input · ~~league 5 · draft_state 18 · coverage 10~~ **DICTIONARY-KEY COUNTS, NOT OBSERVATIONS — withdrawn as counts** | **mixed — see cell; NOT uniform `obs`** | **CONSUMED** by the league derivation chain |
| N15 | PFF | manual export payloads | **149** | **`raw-payload count` — NOT `obs`** *(V2)* | **partial — ONE PRECISE LANE** *(V12)*: NCAA `receiving_summary`, scope `REGPO`, seasons 2017–2025 (9 entries in `phase16_wr_manifest.json`, hashes match content-hash filenames) via `scripts/build_college_features.py`. **Not evidence that the other 13 lanes are consumed.** |
| N15b | PFF | internal source rows across 14 league/report lanes | **134,392** | `obs` *(sum; overlap/dedup rule NOT yet stated)* | as N15 |
| N16 | CFBD | `curated/prospects_with_outcomes_v3.csv` | 874 rows | `obs` | **Engine A** (promoted 2026-08-04) |
| N17 | CFBD | `raw/20260802T024342156864Z/` payloads | **1,202** *(manifest `raw_file_count`; dir holds 1,203 JSON = 1,202 payloads + `manifest.json`)* | `cap`/raw | upstream of N16 |

**PlayerProfiler reconciles exactly:** 1,520,009 `obs` + 3,290 `idn` + 63 `cap` = 1,523,362 physical
rows — the figure the prior board carried, now decomposed by grain rather than asserted as a total.

**PFF grain, corrected TWICE in one table — the R5 trap catching its own warning.** The store holds
**459 raw CSVs**, **149 unique payloads**, and **134,392 internal source rows** across **14
league/report lanes** (7 report families × `ncaa`/`nfl`). I warned that 459 is a file count and not an
observation count — **and then labelled 149 as `obs` in the very next column.** 149 is also a file
count. Only N15b is an observation figure, and it is **a raw sum: the overlap/deduplication rule
across lanes is NOT yet stated, so it may not be published as a deduplicated total** (V2, Codex).

**⛔ N17 — MEASURED THE WRONG PATH. My worst error in this table.** I published **810 files** as the
promoted CFBD run's raw payload count. **810 is the file count of `app/data/cfbd_cache/`** — a
different directory entirely, which I ran `find` against and then labelled as
`raw/<run_id>/`. The promoted run pins **`raw_file_count = 1202`** in
`manifest_latest.json`, and its directory holds 1,203 JSON files (1,202 payloads + `manifest.json`).
**This is the same defect shape as the "no raw snapshots exist" error earlier in the session: a
measurement run against one path and reported as a fact about another.** Second instance in one
session; both caught by the independent lane, neither by me (V1, Codex).

**Still owed on Table B-N:** per-stream `bound`/`captured`/`exported` states (R7), refresh cadence,
evidence paths with timestamps, and **the PFF cross-lane overlap/dedup rule before any 134,392
aggregate is treated as a deduplicated observation count**. **No row here is `verified`** — Claude
measured them alone, which R4 makes `measured`, not checked off.

### §3.2 Registry PHYSICAL-state evidence *(Codex V5–V8, all reproduced by Claude)*

**These findings are now carried in the §2.1 rows themselves.** This section is the EVIDENCE behind
those cells, not a correction appendix — *(V13: a correction appendix does not reconcile a stale
canonical row, and leaving the canonical table stale while the fix lived only down here was exactly
the defect Codex flagged).* Two of the four are **provenance defects rather than captures**:

| Registry key | §2.1 said | Physical truth | Note |
| :-- | :-- | :-- | :-- |
| `nfl_data_py` (R1) | UNVERIFIED | **NOT a `nfl_data_py` capture** | **No `nfl_data_py` import exists in the repo.** `scripts/ingest_2026_draft.py` imports **`nflreadpy`**, writes an 80-player JSON, and labels it `nfl_data_py_verified_nfl_draft`. Declared `parquet_snapshot`; actual route is JSON via nflreadpy. **Source-identity/provenance defect — recorded, not opened.** |
| `ras` (R4) | UNVERIFIED | **`fixture_only`** | Adapter defaults to `resources/fixtures/ras_mock.csv`; that fixture is the only RAS data file. No production capture, no schedule. |
| `nflreadpy_qb_context` (R18) | UNVERIFIED | **`live_direct_read`, consumer-triggered** | `fetch_qb_nfl_stats` calls `nfl.load_pbp(seasons)` in memory; `app/services/roster_auditor.py` invokes it for 2024/2023. **No raw snapshot, no governed cache.** Declared `parquet_snapshot`/168h — **a declared freshness does not make it captured.** **NOT its own stream — it is a SECOND CONSUMER of the B18 `pbp` stream** *(V15)*. |
| `nflreadpy_qb_validation` (R20) | pinned study inputs | **`registered_and_pinned; NOT captured`** | `app/data/backtest/qb_validation/raw/` holds **zero files** (verified). The study has not run. **H2 QB rushing remains a registered hypothesis UNDER TEST with no result.** |

**⛔ R18 IS NOT A SIXTH STREAM — CORRECTED *(V15)*.** I rowed it as a sixth undeclared ingestion
stream and said it was "in scope for David's A/B ruling in substance." **Both halves were wrong, and
the second half was the more serious.**

Under **R1** (source ≠ stream ≠ store): Feature Refresh's B18 calls `nfl.load_pbp(seasons)`, and
R18's adapter calls **the same** `nfl.load_pbp(seasons)`. That is **ONE upstream `pbp` dataset stream
with TWO live consumer routes** — Feature Refresh and Roster Auditor — not two ingestion streams.
Recorded as an **additional consumer edge on B18**, plus the R18 registry/provenance mismatch.

**AND IT DOES NOT WIDEN DAVID'S DECISION.** He named **five** streams. R18 belongs to the
*architectural* Option A end-state — its live route should eventually read canonical last-good `pbp`
too — but that is a **second consumer migration with its own parity and control gate, after canonical
`pbp` capture exists**. **A lane must not convert "the architecture implies this" into scope on a
build the principal sized himself.** My "in scope in substance" phrasing did exactly that.

**`exported` for B1–B12 is INDEPENDENTLY VERIFIED *(V11, Codex)*:** `app/data/nflverse_usage/export/nflverse_usage.ready.json` names all 12 materialized streams plus the unresolved-identity companion; **every named Parquet exists and recomputes to the marker's SHA-256**, and the 12 counts sum to **1,491,691**. Pinned at run `nflverse-usage-20260805T1334216901700000`, captured `2026-08-05T13:34:21.690170+00:00`. **This verifies export existence and integrity ONLY — not a consumer for B4–B12, and not any refresh cadence.**
membership in the canonical export as understood, not a probe. Treat as owed, not confirmed.

**`obs` subtotal across the 12 materialized tables: 1,491,691.** Plus `nflverse_capture` **101
`cap`** = 1,491,792 physical rows. `contracts` contributes 0 and has no table.

> **THE v1 ERROR, recorded not smoothed.** v1 published **1,491,792** as the source-row count and
> reported the 101-row gap versus the prior board as an *unexplained discrepancy* — to Codex **and to
> David**. It was neither unexplained nor a discrepancy: **the prior board's 1,491,691 was correct**
> and v1 had added a capture-ledger table to a source-observation total. **My own R2 pin discipline
> was satisfied and still produced a wrong number, because the rule policed measurement and not
> GRAIN. R5 exists because of this.**

**Other grain decompositions, measured:**

| Store | Correct decomposition |
| :-- | :-- |
| `playerprofiler.db` | **1,520,009 `obs`** + 3,290 `idn` + 63 `cap` = 1,523,362 physical |
| `fc_forward_capture.db` | **20,043 `obs`** + 20,043 `alt` (`joinable` is a second representation — **never add**) |
| `league_transactions.db` | **932 `obs`** transactions + 1,692 `obs` movements *(different grain)* + 4 `cap` |

**STREAMS NOW ROWED — this paragraph previously said they were missing and was left standing after
they were added *(V14, and the SAME §5 defect the register exists for)*.** PlayerProfiler,
PFF, CFBD, FantasyCalc and Sleeper are rowed in **§3.1 Table B-N**; the five direct
feature-refresh loaders are rowed as **B15–B19**. **Still genuinely absent:** validation/context
streams, and per-stream `bound`/`captured`/`exported` states on Table B-N.

**The v1 summary "3 consumers / 9 substrate_only / 1 never run" remains WITHDRAWN** — it was
exclusive over an incomplete table. *(Its second stated reason, "B4's consumer state is UNVERIFIED",
is itself now stale: **B4 was resolved** — the canonical `player_snap_count` export has no production
consumer. The withdrawal stands on the first reason alone.)*

---

## §4. Refresh frequencies

### §4.1 Job matrix *(Gemini, Operations & Telemetry — telemetry facts, not a catalog pass)*

**Per-job cadence evidence with paths and timestamps is now durable *(V21)*:**
`docs/agent-ledger/evidence/2026-08-06/layer1_cadence_codex_overnight_v1.md`. The earlier statement
that path/timestamp evidence was **wholly** outstanding is superseded — it is partly landed. What
remains open is **per-STREAM** cadence (R3: a job's cadence is not its upstream stream's).

| Job | JOB cadence (plist) | FRESHNESS policy | `dormant_ok` |
| :-- | :-- | :-- | :-- |
| Sleeper Capture | Daily 09:20 | Daily | `false` |
| FantasyCalc Capture | Daily 09:00 | *(no `report_freshness.json` entry — F5)* | — |
| **nflverse Feature Refresh** | **Daily 09:15** | **Weekly** | **`true`** |
| Model PVO Refresh | Daily 09:30 | Daily | `false` |
| Market Divergence | Daily 09:40 | Daily | `false` |
| What-Changed Report | Daily 09:45 | Daily | `false` |
| Realized Outcome | Weekly Tue 10:00 | Weekly | `true` |
| Offsite Backup | Daily 10:15 | *(no `report_freshness.json` entry — F5)* | — |

> **Gemini has NOT issued a final operational pass.** It supplied telemetry and one valid alarm.
> Evidence paths/timestamps per row are still to be attached (F5).

### §4.2 ⛔ THE CORRECTION — and the most important Layer-1 finding so far

**v1 asserted the Feature Refresh job "covers twelve seasonal streams collectively," and concluded
per-stream cadence might not exist. Both were FALSE.** Independently verified in
`scripts/run_feature_refresh.py`:

- It reads **only the three NGS streams** from the last-good export (`load_nextgen_from_export`).
- It loads **`player_stats`, `rosters`, `snap_counts`, `pbp`, `participation` DIRECTLY from
  `nflreadpy`** — bypassing the canonical store entirely.
- It **never invokes `run_usage_capture`**.
- It **never refreshes** injuries, PFR ×4, ff_opportunity, ftn_charting, or depth_charts.

**And: `rg -ln "run_nflverse_usage_capture" ops/` returns NOTHING — no LaunchAgent calls the
canonical capture runner.**

**⇒ The canonical ingestion store has NO SCHEDULED REFRESH AT ALL. It is manual-only.**
**Stated at the right grain (V2-F3): 13 loader-BOUND StreamSpecs, of which 12 are MATERIALIZED as
source tables holding 1,491,691 `obs` rows; `contracts` is bound but has no table, and the
`nflverse_capture` ledger (101 `cap`) is not a stream.** Nine of the twelve materialized streams are
refreshed by nothing and consumed by nothing.
Meanwhile the daily job pulls five datasets straight from the provider on a **separate** path that is
not in the catalog.

**⚠ SCOPE OF THIS FINDING — QUALIFIED 2026-08-06 (V16), because it was being read too widely.**
The sentence above is true **of `app/data/nflverse_usage.db`** and of nothing else. It must **NEVER**
be paraphrased as *"Layer 1 has no scheduled ingestion."* **N18 is a counter-example this catalog
had missed entirely**: `com.davidleess.dynasty-league-capture` runs **daily at 09:20**, is loaded,
**last exit 0**, has **21 successful runs** (2026-07-16 → 2026-08-05), writes a marker-pinned
snapshot bundle, and **is consumed**. FantasyCalc likewise has a daily capture route (R8). **A
finding scoped to one store is not a finding about the layer**, and the reason it nearly became one
is that the counter-example had no row here to contradict it.

**That is a genuine Layer-1 structural finding and it is exactly what this inventory was ordered to
surface.** It is recorded as a measured fact **at the grain stated above**. **It is not a
recommendation, and no agent may treat it as authority to build, schedule, or re-sequence anything**
— David rules on that.

### §4.3 ⚠ VALID OPS ALARM — offsite backup run FAILED

Reproduced by Gemini, Codex and Claude. **Codex accepts it as a valid five-element alarm.**

| Element | Value |
| :-- | :-- |
| observed value + timestamp | run `20260805T141503Z`, `status: failed`, `sha256_verified: false`, finished `2026-08-05T16:29:23.476095Z` |
| marker path | `app/data/ops/backup_status_latest.json` |
| registered law (predates observation) | `02` §Standing Infrastructure |
| predicate | `status == failed` → **TRUE** |
| paused dependency | none governed |

Last **successful** completion `2026-08-05T03:13:15.645391Z`. **Pauses nothing, authorizes nothing;
manual recovery is David-gated.**

**Withdrawn after challenge — both were relayed to David before verification:**
1. **"Timeout" as mechanism — WITHDRAWN.** Only `upload_failed:<path>` is established.
2. **The `05:13:15Z` / 01:13 EDT staleness crossing — UNVERIFIED, do not repeat as fact.** The
   projection names the scheduled 10:15 run as its clock basis but computes from the prior success's
   *completion* time. Different operands.

---

## §5. Recurring defect register

Kept because the same defect recurred four times in one day and each fix was scoped to its instance:

| # | Instance | Caught by |
| :-- | :-- | :-- |
| 1 | Ledger "NOTHING COMMITTED" / `HEAD=d645933` left standing after `4909d52` | Codex |
| 2 | The fix for (1), asserting a HEAD its own commit invalidated | Codex |
| 3 | Board "Gemini pane is BLOCKED / David must clear it", after Claude unblocked it | Codex |
| 4 | v1 §4 "matrix exists only in the daily ledger", after Claude copied it into this catalog | Codex |

**General rule:** *any state assertion about a condition the author is actively changing must be
re-checked after the change, not merely be true when written.* The earlier narrow form ("a commit
cannot pin its own resulting HEAD") failed to catch (3) and (4) because no commit was involved.

---

## §6. §H — Sources we still need to ingest *(CANNOT BE ANSWERED YET — F7)*

**This is David's direct question and it is NOT answerable from an incomplete universe.** What is
established:

| Gap | Kind |
| :-- | :-- |
| Canonical ingestion has **no scheduled job** | **absent schedule** |
| `contracts` bound but never executed; store table absent | **absent capture** |
| **Nine materialized streams with no production consumer, NAMED (V2-F4):** `snap_counts` · `injuries` · `pfr_pass` · `pfr_rush` · `pfr_rec` · `pfr_def` · `ff_opportunity` · `ftn_charting` · `depth_charts` | **absent consumer** |
| PlayerProfiler 1,520,009 `obs`, no production consumer outside ingestion | **absent consumer** |
| PFF — **partial**, not absent: one family consumed by `build_college_features.py` | **partial consumer** |
| The 20 registry definitions not yet rowed | **unenumerated** |
| Candidate NEW external sources | **NOT ENUMERATED — the core open work** |

---

## §7. Disposition of Codex review v2 *(SHA `d99b3247…`)* — F1–F7 ALL ACCEPTED

| F | Finding | Disposition |
| :-- | :-- | :-- |
| F1 | A/B enumeration incomplete despite `[x]` | **Accepted.** Unchecked; registry's 20 named; missing streams listed in §3. |
| F2 | Source-grain violations | **Accepted.** DynastyProcess re-merged to one source; FantasyCalc/DP store-mixing noted; Sleeper corrected to transactions-only. |
| F3 | Totals mix/double-count grains; 101 delta solved | **Accepted, reproduced.** R5 added; all four decompositions measured; the v1 error recorded in §3. |
| F4 | Feature-refresh semantics false | **Accepted, reproduced.** §4.2 rewritten; surfaced the no-scheduled-refresh finding. |
| F5 | §4 internal conflicts; freshness entries missing | **Accepted.** Heading corrected; missing `report_freshness.json` entries marked; evidence paths still owed. |
| F6 | B6–B9 must be four rows | **Accepted, reproduced.** Split with measured counts; R7 multi-valued state added; 3/9/1 summary withdrawn. |
| F7 | §6 cannot answer David | **Accepted.** Marked unanswerable; PFF corrected to partial. |

**Still owed before a fresh review:** full registry enumeration, non-nflverse stream rows, per-row
evidence paths/timestamps, B4 consumer state.

---

## §8. Change log

| Date | Who | Change |
| :-- | :-- | :-- |
| 2026-08-05 | Claude | v1 created. |
| 2026-08-05 | Codex | NOT CLEAR, seven findings. |
| 2026-08-05 | Claude | **v2 rebuild.** F1–F7 accepted; F3/F4/F6 reproduced first. A/B/C reopened; grain tagging added; feature-refresh semantics corrected. |
| 2026-08-05 | Codex | v2 review — **NOT CLEAR**, four findings (V2-F1..F4). |
| 2026-08-05 | Claude | **v3.** V2-F1..F4 all accepted, none contested. §1 source count 9→**7** (stale after the F2 merge — **fifth** §5 instance). Table B carries all **five** R7 states with disposition as its own column. "13 streams" restated as **13 bound / 12 materialized**. **B4 resolved** from Codex's probe: canonical export has no production consumer; the daily job's direct `load_snap_counts` is a separate provider-read stream — so the nine consumerless streams are now NAMED. `exported` marked column-wide UNVERIFIED pending probes — **superseded by V11**. |
