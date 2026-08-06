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
      in an appendix.** **Still UNCHECKED:** the declaration fields are independently verified, but
      physical acquisition routes remain unreconciled for Sleeper and FantasyCalc, and the two
      **provenance defects** (R1's `nfl_data_py` mislabel, R18's declared-vs-actual route) remain
      unresolved.
      *(This line previously asserted "six capture-state cells are `UNVERIFIED`" and was left standing
      after V5–V8 resolved four of them — the §5 defect again, in the progress block that is supposed
      to describe the document's own state. **No count is stated here now**; §2.1 is the source of truth.)*
      *(Deliberately carries NO row-count total for the physical table — a count describing a table
      in the same commit that changes it is the §5 defect, instances 5 and 6. Counts come from a
      probe, not from this document.)*
- [ ] **B. Ingestion streams** — Feature Refresh's five direct reads are rowed (B15–B19); Combine
      and schedules are B20–B21; draft-picks / ff-playerids / players are B22–B24; the non-registry
      and multi-consumer gaps are recorded in §2.2; and PlayerProfiler, FantasyCalc, Sleeper, PFF
      and CFBD are rowed by grain in §3.1.
      **Still missing:** complete R7 state columns on Table B-N, resolution of the parallel Sleeper /
      FantasyCalc routes, and final automation classifications. Mixed independent verification
      exists; the table as a whole is not checked off.
- [ ] **C. Refresh frequencies** — source-publish cadence planning is independently CLEAR at the
      pin named in §4.1, but the clocks are not installed jobs and not every canonical stream row
      yet carries its final automation class / job / freshness edge.
- [ ] **D. Catalog** · [ ] **E. Player 360** · [ ] **F. Semantic layer + metrics** · [ ] **G. Schemas**
      *(phase B — CLOSED until A–C clear)*
- [ ] **H. Sources we still need to ingest** — §6 now gives the provisional evidence-backed answer:
      existing-source reconciliation is required; no unconditional new provider is proven. Remains
      unchecked pending fresh verification of the corrected canonical rows.
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

**✅ V26 — the DECLARATION columns are now INDEPENDENTLY VERIFIED.** Codex mechanically matched all
**20** rows' key / role / cache_policy / freshness_hours / failure_behavior against `SOURCE_REGISTRY`
at pinned SHA **`a840d6f7…`**. **This verifies the declarations ONLY** — the `access class` and `capture state`
columns are separate judgements and remain as individually marked.

`role` · `cache_policy` · `freshness_hours` · `failure_behavior` are **registry declarations**, not
observed behaviour. **Capture state is a separate, physical question** and is the last column;
`UNVERIFIED` there means no probe was run this session, per R2.

| # | Registry key | Role | Cache policy | Fresh (h) | On failure | Access class | Capture state (physical) |
| :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| R1 | `nfl_data_py` | model_input + training_label | `parquet_snapshot` | 168 | `use_cached` | free | **NOT a `nfl_data_py` capture — PROVENANCE DEFECT.** No `nfl_data_py` import exists; `ingest_2026_draft.py` uses **nflreadpy**, writes JSON, labels it `nfl_data_py_verified_nfl_draft` *(V5)* |
| R2 | `cfbd` | model_input | `json_cache` | 720 | `skip_enrichment` | **paid** | partial — `sources/cfbd_foundation/`; promoted 2026-08-04 |
| R3 | `playerprofiler` | context_signal | `json_cache` | — | `skip_enrichment` | **manual, by David** | `playerprofiler.db` — 1,520,009 `obs` |
| R4 | `ras` | context_signal | `json_cache` | — | `skip_enrichment` | free | **`fixture_only`** — adapter defaults to `resources/fixtures/ras_mock.csv`, the only RAS data file *(V6)* |
| R5 | `pff` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | 149 raw payloads / **134,392 raw payload-row sum** (no defensible dedup total — §3.3) / 14 league-report lanes; 1 partial consumer, but `yprr_college` is still 0/874 in the active artifact |
| R6 | `rotoviz` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | **fixture-only — no capture** |
| R7 | `campus2canton` | context_signal | `csv_fixture` | — | `skip_enrichment` | **manual export only** | **fixture-only — no capture** |
| R8 | `fantasycalc` | market_overlay | `json_cache` | 24 | `use_cached` | free | **TWO acquisition routes:** daily `fc_forward_capture.db` (20,043 `obs`) plus request-time `app/cache/fantasycalc/market_values.json` / live fallback used by the trade API and market-overlay service |
| R9 | `mfl_rookie_adp` | market_overlay | `json_cache` | 24 | `use_cached` | free | **BLOCKED:** adapter + separated `app/data/valuation` destination built, but current undocumented `ROOKIES=1&IS_MOCK=No` query returns veterans; official rookie-only contract is `IS_KEEPER=R&IS_MOCK=0`. Zero cache, output artifact, or scheduler |
| R10 | `dynasty_data_lab` | market_overlay | `none` | — | `skip_enrichment` | **paid** ($4/1k req) | **deferred — no capture** |
| R11 | `dynasty_nerds` | market_overlay | `none` | — | `skip_enrichment` | no clean API | **deferred — no capture** |
| R12 | `ktc` | market_overlay | `none` | — | `skip_enrichment` | **PROHIBITED** — ToS bars scraping | **none, by rule** |
| R13 | `sleeper` | context_signal | `json_cache` | 1 | `use_cached` | free | **FOUR measured routes, different states:** (a) `app/data/league_runtime/` — scheduled daily 09:20 normalized snapshot, consumed, raw replay unavailable (N18); (b) `league_transactions.db` — manual_only, no consumer; (c) `app/data/research/league_behavior/raw/2026-07-19/` — manual one-time exact endpoint history, replayable + backup-covered (N19); (d) request-time live Roster Auditor calls, no exact capture |
| R14 | `sportradar` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — ~$7,200/yr | **none, by rule** |
| R15 | `genius_sports` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — enterprise | **none, by rule** |
| R16 | `stats_perform` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — enterprise | **none, by rule** |
| R17 | `rolling_insights` | **prohibited_current_phase** | `none` | — | `fail_closed` | **PROHIBITED** — $4,200–7,200/yr | **none, by rule** |
| R18 | `nflreadpy_qb_context` | context_signal | `parquet_snapshot` | 168 | `skip_enrichment` | free | **`live_direct_read`, consumer-triggered** via Roster Auditor; no snapshot, no cache. **A SECOND LIVE CONSUMER OF THE B18 `pbp` STREAM — not its own stream** *(V7/V15)*. Declared `parquet_snapshot` ≠ actual route |
| R19 | `nfl_nextgen_stats` | context_signal | `sqlite_store_with_raw_snapshots` | 168 | `use_cached` | free | **registry declaration covers NGS B1–B3;** the shared canonical adapter/store also binds B4–B13, but those ten families do not thereby gain matching machine source declarations |
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

### §2.2 ⛔ Feature Refresh's five provider reads have no matching machine declaration

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
and source-timestamp/parser-version provenance. **These five reads satisfy none of those.** The
three-lane pressure test selected canonical Layer 1 capture (Option A) as planning direction; that
does not itself authorize implementation or enablement.

**This five-frame list is not the complete external-read universe.** The canonical table now also
rows:

- **B20 Combine** — live input to `scripts/build_w2_features.py`; no replayable capture found.
- **B21 schedules** — future-live input to the loaded Realized Outcome job; current runs gate before
  source access because prediction snapshots are absent. That job is also another `player_stats`
  consumer.
- **B22–B24 draft picks / ff_playerids / players** — mixed-provider production-builder, identity,
  one-time-freeze, backtest, and registered-validation callers. B22 has a hash-pinned 257-row
  nflverse loader payload plus an 80-row projection; B23 is DynastyProcess `db_playerids` fetched
  through nflreadpy and has 12,457-row frozen plus 7,952-row governed identity snapshots; players is
  uncaptured.

Consumer edges are also broader than Feature Refresh: `scripts/assemble_engine_b_dataset.py` loads
all five again; Roster Auditor directly loads B18 PBP; Roster Auditor also makes independent live
Sleeper calls; and FantasyCalc has both forward-capture and request-time acquisition routes.
Counting those callers as new streams would inflate the inventory; omitting them would hide the
parallel-route defect. The target unit is one upstream dataset → one canonical capture → many
declared consumers.

Finally, R19's `nfl_nextgen_stats` declaration names B1–B3, not every family sharing the canonical
adapter/store. B4–B13 still require source-declaration reconciliation. Recorded as measured gaps of
*absent source declaration*, *absent capture*, and *parallel route* — not authority to build,
register, or schedule anything.

### §2.3 Table A-P — PHYSICAL sources present in the repo
*(**PFF and CFBD rows now carry independently verified inventories *(V1/V2/V12)*; A7 carries the V16 route addition.** Remaining rows are Claude-measured.)*

| # | Source (provider + dataset family) | Access | Stores | Status |
| :-- | :-- | :-- | :-- | :-- |
| A1 | nflverse via `nflreadpy 0.1.5` | free | `nflverse_usage.db` + `resources/prospect_fixtures/_frozen_2025/nflverse_draft_picks_2025_pin.json` (257 loader rows, hashed manifest) + `resources/prospect_identity_2026.json` (80-row projection) + retained inactive `app/data/sources/nfl_nextgen_stats/` (8 files / 3,348 KiB, pending retention ruling) | partial; multiple capture/projection states |
| A2 | PlayerProfiler | **manual, by David** | `playerprofiler.db` | partial |
| A3 | PFF | **manual, by David** | `app/data/pff_exports/` | **measured** — 149 payloads / **134,392 raw payload-row sum** (no defensible dedup total, §3.3) / 14 lanes *(V2)*; consumer is ONE lane *(V12)* |
| A4 | CFBD | **paid** | `sources/cfbd_foundation/` | **measured** — promoted run `20260802T024342156864Z`, **1,202** raw payloads, 874 curated rows *(V1)* |
| A5 | FantasyCalc | free | `fc_forward_capture.db` + part of `fc_snapshots.db` + request-time `app/cache/fantasycalc/market_values.json` / live fallback | partial — parallel routes |
| A6 | **DynastyProcess** *(ONE source — v1 split it by loader, F2)* | free, GPL-3.0 repo | pinned `values.csv`; part of `fc_snapshots.db`; `resources/prospect_fixtures/_frozen_2025/ff_playerids_pin.json` (12,457 rows, hashed manifest); `app/data/identity/_runs/ff_playerids_20260516.json` (7,952 rows) | partial |
| A7 | Sleeper | free | `league_transactions.db` + `app/data/league_transactions/raw/` *(20 raw JSON)* + `app/data/league_runtime/` *(daily normalized bundle)* + tracked `app/data/league_snapshots/` seed/archive surface *(12 files)* + `app/data/research/league_behavior/raw/2026-07-19/` *(manual exact endpoint history, backup-covered)* + request-time live Roster Auditor route | partial — routes/surfaces require reconciliation |

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
| B1 | `ngs_passing` | `ngs_passing` | **5,933** | ✓ | ✓ | ✓ | Feature Refresh + Engine B assembly (via canonical export) | ✗ | `existing_consumer` |
| B2 | `ngs_rushing` | `ngs_rushing` | **6,059** | ✓ | ✓ | ✓ | Feature Refresh + Engine B assembly (via canonical export) | ✗ | `existing_consumer` |
| B3 | `ngs_receiving` | `ngs_receiving` | **14,731** | ✓ | ✓ | ✓ | Feature Refresh + Engine B assembly (via canonical export) | ✗ | `existing_consumer` |
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
| B15 | `player_stats` **(direct provider read — §2.2)** | *(none)* | 0 | ✗ | ✗ | ✗ | Feature Refresh; Engine B assembly; draft-prospect collection; future-live Realized Outcome; QB role labels; registered QB-validation loaders | ✗ | **undeclared — see §2.2** |
| B16 | `rosters` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | Feature Refresh; Engine B assembly; QB identity bridge / priors / role labels / v3 validation; registered QB-validation loader | ✗ | **undeclared** |
| B17 | `snap_counts` **(direct provider read — DUPLICATE of B4)** | *(none)* | 0 | ✗ | ✗ | ✗ | Feature Refresh; Engine B assembly; QB role labels | ✗ | **undeclared — parallel route to B4** |
| B18 | `pbp` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | Feature Refresh; Engine B assembly; request-time Roster Auditor; registered QB-validation loader | ✗ | **undeclared** |
| B19 | `participation` **(direct provider read)** | *(none)* | 0 | ✗ | ✗ | ✗ | **09:15 Feature Refresh + Engine B assembly** | ✗ | **undeclared** |
| B20 | `combine` **(active-builder direct read)** | *(none)* | 0 | ✗ | ✗ | ✗ | **`build_w2_features.py` mutates the active training artifact from a live read** | ✗ | **uncaptured existing-source input** |
| B21 | `schedules` **(future-live direct read)** | *(none)* | 0 | ✗ | ✗ | ✗ | **loaded Realized Outcome job; current runs gate before access on absent predictions** | ✗ | **future-live / uncaptured** |
| B22 | nflverse `draft_picks` **(direct / study / identity reads)** | frozen 2025 loader payload + 2026 prospect projection | **257 frozen loader rows + 80 projected rows — different vintages/representations, never add** | ✗ | **✓ parsed loader payload; exact HTTP bytes absent** | ✗ | draft-prospect collection; 2026 draft ingest; TE cohort; prospect bridge; mock draft; 2025 freeze; registered QB-validation loader | ✗ | **capture/provenance reconciliation required** |
| B23 | DynastyProcess `db_playerids` / loader name `ff_playerids` **(identity crosswalk)** | frozen 2025 pin + governed 2026 identity run | **12,457 + 7,952 `idn` rows — different vintages, never add** | ✗ | ✓ | ✗ | production identity infrastructure (`build_universe_pvo_batch.py`, transaction capture, PlayerProfiler, canonical nflverse identity, identity audit, league-intelligence refresh); TE cohort; backtest; freeze; registered QB-validation loader | ✗ | **captured identity input; no DynastyProcess registry declaration** |
| B24 | `players` **(registered QB-validation loader)** | *(none)* | 0 | ✗ | ✗ | ✗ | registered QB-validation study only; study has not run | ✗ | **static-pinned study input, not captured** |

**Point-in-time ceiling for B1–B12:** the 1,019 local raw snapshots have capture dates only
2026-07-31, 08-02, 08-03, and 08-05. Historical-season rows are retrospective coverage, not
historical as-of vintages. `captured = ✓` remains true; pre-2026-07-31 point-in-time history does not.

**Retained inactive NGS representation:** `app/data/sources/nfl_nextgen_stats/` contains eight files
(3,348 KiB) from the withdrawn parallel route. It is retained pending a separate David retention
ruling, is not the active adapter/store, and must not be counted as three additional streams.

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
* Snapshot grain — **CORRECTED BY V17; the flat-count version below it originally stated is
  falsified and is not restated here.** `players` **12,209** are *normalized/classified over a UNION*
  of source players + rostered/draft/prospect IDs — **not** raw `get_all_players`. `rosters` **12**
  and `users` **14** are list-shaped source components. `future_picks` **109** is **DERIVED**.
  **`league`, `draft_state` and `coverage` are DICTIONARIES — their "counts" were dictionary-key
  counts and are withdrawn as observation figures**; `coverage` is a repo-derived report, not a
  source grain at all. See the N18 row in §3.1 for the per-field statement.

**Corrections this forces:**
1. **`app/data/league_runtime` is added to A7's physical stores** — it was not listed.
2. **N12/N13 stay `manual_only` and consumerless.** The 09:20 cadence belongs **only** to N18.
3. **The five derived artifacts** (`coverage`, `provenance`, `roster_cut_report`, `team_posture`,
   `team_value_matrix`) are **downstream outputs of one coherent bundle — NOT five ingested source
   streams.** Counting them as streams would inflate the inventory with our own outputs, which is the
   same error class as counting `model_forward_capture.db` as fuel.
4. **PHYSICAL CAPTURE STATE: `normalized snapshot; RAW ENDPOINT REPLAY UNAVAILABLE` *(V17)*.**
   A normal run makes nine Sleeper requests — drafts discovery, league, rosters, users, traded
   picks, players, NFL state, draft object, and draft picks — and passes them through
   `build_universe_snapshot`; **only the transformed result is written.** The exact endpoint response
   bytes are never retained, and the lineage block hashes players/league/rosters/users/traded-picks
   but not NFL state, draft state, or draft picks. **A marker-pinned normalized bundle is not a raw
   capture.** The player projection also drops `injury_status`, `injury_body_part`,
   `practice_participation`, and `injury_start_date`, retaining only generic source `status`. This
   stream cannot satisfy `01` §Source Adapter Rules' raw-snapshot-before-parsing requirement as it
   stands, and it cannot establish adequate live injury coverage without an in-season test.
5. **This materially qualifies the session's headline finding.** *"The canonical ingestion store has
   NO SCHEDULED REFRESH"* remains true **of `nflverse_usage.db`** — but it must never be read as
   *"Layer 1 has no scheduled ingestion."* **N18 is scheduled, captured, marker-pinned, and
   consumed.** It is the counter-example, and the catalog missed it.

### §3.4 N19's TRANSACTION SLICE measured against N12 — an older alternate capture, NOT N12's provenance layer

**Codex SG1 ranked this the #1 source gap** — four seasons of Sleeper league history captured,
backup-covered, and absent from the catalog. **The store and the omission are both real, and the
canonical N19 row (in Table B-N below) is correct. This section adds the relationship it does not
state**, measured before being written:

| Check | Result |
| :-- | :-- |
| transaction IDs in N19's raw capture | **923** |
| shared with N12 `league_transaction` (932) | **923** |
| **present ONLY in N19** | **0** |
| present only in N12 | **9** — all season 2026 (N12 67 vs N19 58) |

**⇒ N19's TRANSACTION SLICE is a strict subset of N12** — an **older alternate exact capture**, not
new history and not a data gap. N12 was refreshed after the 2026-07-19 capture, hence the 9.

**⛔ SCOPE OF THAT STATEMENT — corrected.** It applies to the **transaction slice ONLY**. N19 also
carries **matchups, league, users, rosters, traded picks, drafts, the draft object, and draft picks**
— all **outside** N12's transaction dataset. **N19 as a whole IS a separate multi-endpoint raw
corpus**; only its transactions are `alt`. *(My first draft generalized "not a separate dataset" over
the entire store. Wrong.)*

**Three consequences:**
1. **`alt` grain — the 923 must NEVER be added to N12's 932.** Same observations in source form. This
   is the `fc_forward_capture_joinable` trap in a new place, and it is the fourth time this catalog
   has had to mark an `alt` to stop a double count.
2. **⛔ N19 IS NOT N12's PROVENANCE LAYER — my lineage claim was WRONG.** N12 has its **own governed
   raw path**, `app/data/league_transactions/raw` (**20 snapshots**), and the capture writes it
   **before** normalization — verified in `src/dynasty_genius/league_transactions.py`:
   `write_raw_snapshot` (L1009) → `normalize_transactions` (L1022) → `store.upsert` (L1029).
   Reproduced independently: selecting the **latest snapshot per season 2023–2026** yields **932
   unique IDs, 932/932 shared with the DB, ZERO either-side-only.**
   **⇒ N12 satisfies `01` §Source Adapter Rules' raw-before-parse requirement — because of its OWN
   raw path, NOT because of N19. N18 still does not.**
   *(How I got it wrong: I found a raw store that overlapped N12 and concluded it WAS the raw layer,
   without checking whether a different one existed. An inference from absence, where the absence was
   my not having looked. Codex named the real path.)*
3. **SG1's ranking should fall for §H purposes.** It is a **cataloging** gap, not a **source** gap.
   **David's §H question asks what sources we still need to ingest; this is not one of them.**

**Also recorded:** this is the **second entire captured store found missing from the inventory**
(after N18), and it is the directory whose `transactions_week_05.json` failed the 2026-08-05 backup.
**We were backing it up without it appearing in the catalog.**

**Not opened:** whether **N19's broader multi-endpoint raw corpus** (matchups, league, users, rosters, traded picks, drafts) should be refreshed forward. *(This read "whether the raw layer should be refreshed forward alongside N12" — but after the lineage correction N19 is explicitly NOT N12's raw layer, so "the raw layer" named a thing this section had just denied. N12's own governed raw path is a separate question and is not raised here.)*

**B15–B19 are streams with production consumers and no canonical capture** — the exact inverse of
B5–B13 (captured, no consumer). `obs = 0` records that **we keep nothing on these routes**, not that
nothing flows. **B17 is the duplicate route to B4** (`player_snap_count`, 253,106 `obs`). Option A
is the selected planning direction: one canonical capture per upstream dataset, then migrate each
consumer behind its own parity/control gate. **B20** is an active-builder input with no replayable
capture; **B21** is future-live and must be canonical before the first prediction-bearing run.
**B22–B24** are existing mixed-provider identity/study dataset families that the prior table
omitted: B22/B24 are nflverse-backed, while B23 is DynastyProcess `db_playerids` transported by
nflreadpy. Their callers mix production builders, one-time freezes, identity work, and a registered
validation study; that classification prevents “every loader exists” from becoming “schedule every
loader.”

### §3.1 Table B-N — NON-NFLVERSE streams
*(F1/F6 blocker. **Mixed verification state *(V21)*: PlayerProfiler/FantasyCalc/Sleeper counts, the CFBD 1,202 figure, the PFF 149/134,392 split (§3.3: no dedup total is defensible) and its one consumer lane are INDEPENDENTLY verified; per-stream R7 states and cadence are not. Table not complete.**)*

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
| N9 | FantasyCalc | `fc_forward_capture_raw` *(source `fc_native`, snapshots 2026-06-24 → 2026-08-05)* | 20,043 | `obs` | **no direct production consumer; source representation for N10** |
| N10 | FantasyCalc | `fc_forward_capture_joinable` | 20,043 | **`alt` — never add to N9** | **scheduled Market Divergence + What-Changed report** (`run_market_divergence_refresh.py`, `what_changed/daily_diff.py`) |
| N11 | **MIXED-SOURCE store** *(V3)* | `fc_snapshots` = DynastyProcess **2,185** (2021-09-08 → 2024-09-08) + FantasyCalc **4,605** (2026-06-12 → 2026-06-24) | 6,790 | `obs` | **optional legacy backtest instrument** (`eval/market_snapshot_store.py`, `run_backtest.py`); not the current overlay source |
| N12 | Sleeper | `league_transaction` | 932 | `obs` | **none** *(V4 — corrected)* |
| N13 | Sleeper | `league_transaction_movement` | 1,692 | `obs` *(different grain)* | **none** *(V4 — corrected)* |
| N14 | Sleeper | `league_season_capture` | 4 | `cap` | — |
| N14b | Sleeper | `app/data/league_transactions/raw/` | **20 JSON files** | `raw-payload`; not added to N12/N13/N14 | upstream exact transaction capture evidence; manual_only |
| N15 | PFF | manual export payloads | **149** | **`raw-payload count` — NOT `obs`** *(V2)* | **partial — ONE PRECISE LANE** *(V12)*: NCAA `receiving_summary`, scope `REGPO`, seasons 2017–2025 (9 entries in `phase16_wr_manifest.json`, hashes match content-hash filenames) via `scripts/build_college_features.py`. **Not evidence that the other 13 lanes are consumed.** |
| N15b | PFF | internal source rows across 14 league/report lanes | **134,392** | `obs` **(raw payload-row sum; NOT proved double-counted — see §3.3)** | as N15 |
| N15c | PFF | output of a **PROPOSED widest-scope file-selection policy** — **not adopted, not canonical** | **106,867** | **policy OUTPUT, not an observation count** *(§3.3 — the subset premise was tested and FAILED)* | as N15 |
| N16 | CFBD + other sources | `curated/prospects_with_outcomes_v3.csv` | 874 rows | **curated multi-source artifact rows — NOT CFBD source `obs`** | callable builders/evaluators exist; current board says no model consumes the corrected CFBD values |
| N17 | CFBD | `raw/20260802T024342156864Z/` payloads | **1,202** *(manifest `raw_file_count`; dir holds 1,203 JSON = 1,202 payloads + `manifest.json`)* | **`raw-payload count` — NOT `obs` or ledger `cap`** | upstream evidence for N16 |
| **N18** | **Sleeper — league/universe NORMALIZED SNAPSHOT** *(V16 added it; V17 corrected its grain)* | `app/data/league_runtime/runs/<run_id>/snapshot.json`, schema `sleeper_universe_snapshot.v1` | **players 12,209** *(normalized/classified over a UNION of source players + rostered/draft/prospect IDs — **not** raw `get_all_players`)* · **rosters 12** · **users 14** *(list-shaped source components)* · **future_picks 109 — DERIVED**, reconstructed from settings/roster IDs/rounds/traded-pick input · ~~league 5 · draft_state 18 · coverage 10~~ **DICTIONARY-KEY COUNTS, NOT OBSERVATIONS — withdrawn as counts** | **mixed — see cell; NOT uniform `obs`** | **direct scripts:** `build_universe_pvo_batch.py`, `run_what_changed_report.py`, `run_roster_capacity_audit.py`, `run_league_transaction_capture.py`; **API:** `league_pulse.py`, `trade.py`, `trade_market.py`; **bundle derivative:** `build_league_opportunity_map.py` |
| **N18b** | **Sleeper — tracked normalized seed/archive surface** | `app/data/league_snapshots/` | **12 files:** 2 active `*_latest.json` fallback aliases + 10 retained timestamped archives | file/representation count; **not source `obs` and not exact endpoint raw** | only the 2 latest aliases are active fallback inputs for `load_production_league_set`; 10 timestamped files are retained archives |
| **N19** | **Sleeper — league-behavior exact endpoint history** | `app/data/research/league_behavior/raw/2026-07-19/` | **172 endpoint envelopes + 1 fetch log**; 2023–2026; 176 logged calls, zero failures | `raw-payload` by endpoint family; **never sum unlike grains**. **Its 923 transaction records are an OLDER ALTERNATE CAPTURE of a strict subset of N12 — `alt`, NEVER added to N12's 932 (§3.4). Its other endpoint families are NOT in N12.** | **none established; manual one-time, replayable, backup-covered.** **NOT N12's provenance layer — that is `app/data/league_transactions/raw` (§3.4)** |

**PlayerProfiler reconciles exactly:** 1,520,009 `obs` + 3,290 `idn` + 63 `cap` = 1,523,362 physical
rows — the figure the prior board carried, now decomposed by grain rather than asserted as a total.

**PFF grain, corrected TWICE in one table — the R5 trap catching its own warning.** Disk holds
**149 raw payload CSVs** and **153 CSVs total**, not 459 raw CSVs. The file-map contains 307 mapping
records; those are not additional stored raw files. The payloads contain **134,392 internal source
rows** across **14 league/report lanes** (7 report families × `ncaa`/`nfl`). Only N15b is an
observation-shaped figure. **I claimed it double-counted 27,525 rows (20.5%). THAT CLAIM IS
WITHDRAWN — the row-level check RAN and FALSIFIED it** (§3.3). The one callable consumer projects
`yprr_college`, but the active 874-row artifact has **0 populated values** — a materialization /
curation gap, not proof of another provider need.

### §3.3 PFF aggregation — **NO DEFENSIBLE DEDUPLICATED TOTAL EXISTS** *(row-level check RAN and FAILED)*

**Status: the §6 blocker is NOT closed, and it is not "awaiting a check" either. The check ran and
the premise failed.**

**What I proposed and what falsified it.** I proposed treating scopes as nested — `REG ⊂ REGPO`,
`POST ⊂ REGPO` — selecting one widest-scope payload per `(league, report, season)`, and reporting
**106,867**, with **134,392** described as double-counting **27,525 rows (20.5%)**.
**Codex ran the row-level comparison I had said was unrun, and it FALSIFIES the subset premise.
I reproduced it independently on `ncaa · receiving_summary · 2017`:**

| Check | Result |
| :-- | :-- |
| `REG` payload rows | 2,079 |
| `REGPO` payload rows | 2,103 |
| **Players ONLY in `REG`** | **1 — `player_id` 55173, lost outright if `REG` is discarded** |
| Shared players | 2,078 |
| **Shared rows whose VALUES DIFFER** | **942** |

Across the full discard set Codex measured **18,006 identical rows, 9,518 shared-player rows differing
in values, and at least one player present only in a discarded payload.**

**⇒ `REG` is NOT a subset of `REGPO`.** Discarding it **loses data**, so:
* **`134,392` is NOT proved double-counted. The "overstates by 27,525 / 20.5%" claim is WITHDRAWN.**
* **`106,867` is NOT canonical and NOT deduplicated.** It may be stated **only** as *the output of a
  proposed widest-scope file-selection policy*, which is **not adopted**.

**Corrections to my own analysis, from Codex P1–P4:**
* **P1** — **20** keys carry multiple **scopes**; **21** carry multiple **payloads**. I reported 21
  scopes, conflating payload-multiplicity with scope-multiplicity.
* **P3** — row-count tie-breaking is **incomplete**: equal-row-count **same-scope** variants differ in
  content, so a count tie does not identify the right file.
* **P4** — **`PRE` is GAME-PHASE-disjoint, not PLAYER-disjoint.** Scope must stay in provenance and in
  the key; it is not a dimension that can be summed away.

**Still true and unchanged:** the repo's `preferred_for_selection` column does not resolve this
(146/149 `True`; overlapping pairs both preferred → 127,842, also not defensible), and the retained
statuses (`superseded_basis_retained` 10 payloads / 21,668 rows, `scope_mismatch_retained` 12 /
1,784, and others) are deliberately-kept payloads.

**What a real rule now requires — THREE separate mechanisms, not one *(P6, Codex; corrects my own
internal contradiction)*.** My first version put **scope in the key** and then called **all 9,518**
differing rows *"conflicts needing a value-conflict policy."* **Those two statements contradict each
other:** if scope is part of the key, then rows differing across scopes are **separate keys, not
conflicts.** Codex's reprobe: **9,515 of the 9,518 are CROSS-SCOPE** (separate keys) and **only 3 are
same-scope variant comparisons** (genuine conflicts). Structurally consistent with the payload
layout — **20** keys carry cross-scope payloads while only **2** carry same-scope duplicates.

| Mechanism | Scope of the problem it solves | Size |
| :-- | :-- | :-- |
| **Raw versioning** — keep every accepted payload version | same-scope duplicate payloads | **2 keys** |
| **Same-scope current-state selection** — choose the current payload among same-scope variants | the only true value conflicts | **3 rows** |
| **Cross-scope aggregation (OPTIONAL)** — a union across `REG`/`POST`/`PRE` if a combined view is ever wanted | distinct keys, **not** deduplication | 20 keys |

**The conflict problem is 3 rows, not 9,518** — and Codex's exhaustive profiling names them exactly:
`receiving_depth · 2017 · REGPO` player IDs **39935** and **48267**, plus
`receiving_summary · 2025 · REG` player ID **198423**.

**PUBLICATION RULE, narrowed *(P8, Codex)*.** An earlier draft said *"nobody should publish an
aggregate PFF observation count"* — **too broad, and it contradicted N15b in this same document**,
which correctly publishes **134,392** as a raw payload-row sum.
* **PUBLISHABLE:** raw-grain aggregation — the 134,392 payload-row sum, labelled as such.
* **NOT PUBLISHABLE:** any **deduplicated or current-state cross-payload total**, until the
  aggregation mechanism above is chosen and stated.
That remaining item is a **design decision, not a measurement gap.**

*(Process note, recorded because it caused a second defect: my edit script used `str.replace`, which
returns the input unchanged when the anchor does not match, and printed a success message
unconditionally — so **§3.3 was never created while six other places cited it** (Codex P5). My
verification grep matched a DIFFERENT edit and I read it as confirmation. **Every edit in the
correcting pass now asserts per-edit application and exits non-zero on any miss.**)*

**⛔ N17 — MEASURED THE WRONG PATH. My worst error in this table.** I published **810 files** as the
promoted CFBD run's raw payload count. **810 is the file count of `app/data/cfbd_cache/`** — a
different directory entirely, which I ran `find` against and then labelled as
`raw/<run_id>/`. The promoted run pins **`raw_file_count = 1202`** in
`manifest_latest.json`, and its directory holds 1,203 JSON files (1,202 payloads + `manifest.json`).
**This is the same defect shape as the "no raw snapshots exist" error earlier in the session: a
measurement run against one path and reported as a fact about another.** Second instance in one
session; both caught by the independent lane, neither by me (V1, Codex).

**Still owed on Table B-N:** complete per-stream `bound`/`captured`/`exported` states (R7), final
automation/job edges, parallel-route dispositions, and **a defensible PFF aggregation rule — see
§3.3, where the scope-nesting premise was TESTED AND FAILED, so no deduplicated PFF total exists**. Several counts and physical
states are independently verified; **the table as a whole is not verified or checked off**.

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
feature-refresh loaders are rowed as **B15–B19**; Combine and schedules are B20–B21. **Still
genuinely incomplete:** final automation classifications, complete R7 states on Table B-N, and
reconciliation of the parallel Sleeper/FantasyCalc consumer routes. Identity/study datasets are now
rowed as B22–B24 rather than left implicit in adapter functions.

**The v1 summary "3 consumers / 9 substrate_only / 1 never run" remains WITHDRAWN** — it was
exclusive over an incomplete table. *(Its second stated reason, "B4's consumer state is UNVERIFIED",
is itself now stale: **B4 was resolved** — the canonical `player_snap_count` export has no production
consumer. The withdrawal stands on the first reason alone.)*

---

## §4. Refresh frequencies

### §4.1 Job matrix *(Gemini, Operations & Telemetry — telemetry facts, not a catalog pass)*

**Per-job cadence evidence with paths and timestamps is durable *(V21)*:**
`docs/agent-ledger/evidence/2026-08-06/layer1_cadence_codex_overnight_v1.md`. Source-publish cadence
planning is independently CLEAR at
`docs/agent-ledger/evidence/2026-08-06/layer1_source_publish_cadence_codex_v1.md`, SHA-256
`2d1fe261b8c88a75091ca48e0951348d64b26bee7696bc28a8abaaa8ff2387fe`. The clocks are planning
targets, not installed jobs. What remains open is reconciliation of every canonical stream to its
automation class, actual job edge, freshness policy, and enablement authority.

The remaining-candidate cadence companion is
`docs/agent-ledger/evidence/2026-08-06/layer1_remaining_candidate_cadence_codex_v1.md`, SHA-256
`af31195ccc6cd99ff8f6fea2db2e3498cf94eb2b7aab7908d5be8582de6b7019`. It pins the upstream
Combine, schedules, draft-picks, and DynastyProcess-player-ID rhythms, proposed conditional local
checks, and the live MFL endpoint-contract blocker. These remain planning evidence, not installed
clocks.

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

> **Gemini supplied telemetry, not a canonical factual pass.** Codex verification found several
> corrections in Gemini's prose (including QB-context cadence, FantasyCalc archive state, and stale
> backup language); only claims reconciled into this catalog or
> `gemini_reports_codex_verification_v1.md` are carried forward.

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
Meanwhile the daily job pulls five datasets straight from the provider on a **separate** path. That
path was absent from v1 and is now explicitly rowed as B15–B19; the route defect remains unresolved.

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

### §4.3 ✅ OPS ALARM — DISCHARGED 2026-08-06 *(was: offsite backup run FAILED)*

> **RESOLVED.** David authorized the recovery (*"i meant RUN IT"*); run **`20260806T024853Z`** completed
> **`sha256_verified: true`**, **zero failures**, 508 files / 2,203,676,656 bytes, finished
> **`2026-08-06T04:52:33.690114Z`**. `latest.json` advanced to that run. **The prior FAILED run prefix
> and all earlier runs remain intact — no delete, rotation or overwrite was constructed.** The alarm's
> predicate (`status == failed`) is now **false**. **The prior failure's cause remains UNDIAGNOSED and
> is not inferred from the successful re-run.**

*(Historical alarm record below, preserved.)*

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

### §4.4 Per-stream automation classification candidate

**Planning only — no proposed-job installation or enablement claim.** Existing installed jobs are
recorded as measured current state; proposed checks remain plans. Every cataloged stream/source group now
has one of the seven automation classes from the independently CLEAR refresh plan. A grouped row
names every member explicitly and groups only shared source/failure boundaries. “Proposed check” is
not “job exists.” `UNVERIFIED` is an explicit inventory value, not permission to guess.

| Catalog IDs / source | Automation class | Upstream publish / change rhythm | Proposed or actual local check | Remaining gate |
| :-- | :-- | :-- | :-- | :-- |
| B1–B3 NGS | `automatic_candidate` | nightly 03:00–05:00 ET in provider-active months | proposed daily 06:15 ET in those months; weekly otherwise | canonical capture is manual; scheduler/marker design + word |
| B4 canonical snap counts | `automatic_candidate` | provider checks 00/06/12/18 UTC in season | proposed daily 07:15 ET in provider-active months; weekly otherwise | ready-export parity and consumer migration |
| B17 duplicate live snap-count route | `automatic_active_health_unverified` | same upstream as B4 | actual daily 09:15 live read | **target state is blocked from separate scheduling**; retire only after B4 parity/control gate |
| B5 nflverse injury archive | `automatic_candidate` | annual/post-hoc; 2025 appeared 2026-03-18 | proposed weekly February–April, then freeze completed season | not current-season injury coverage; Sleeper test first |
| B6–B9 PFR advanced | `automatic_candidate` | daily 07:00 UTC in season | proposed daily 06:15 ET in provider-active months; weekly otherwise | four per-stream markers/counts despite shared orchestrator |
| B10 ff opportunity | `automatic_candidate` | after TNF/Sunday/SNF/MNF windows | proposed daily 06:30 ET in provider-active months; weekly otherwise | canonical job/marker + no-change contract |
| B11 FTN charting | `automatic_candidate` | checked 4× daily; source may lag games 48h | proposed daily 07:15 ET in provider-active months; weekly otherwise | 48h-aware freshness + attribution/retention contract |
| B12 depth charts | `blocked` | daily 07:00 UTC year-round | no automatic capture yet | exact compressed representation + retention ceiling; current JSON is 56.29× source Parquet |
| B13 contracts | `blocked` | daily 07:00 UTC year-round | no scheduled capture | first capture is a separately authorized landing with 12+contracts export reconciliation |
| B14 ff_rankings | `blocked` | source cadence not relevant while use is blocked | none | `blocked_for_use`, no RED / scheduler |
| B15 player stats — current direct-read route | `automatic_active_health_unverified` | nightly plus game windows; Thursday corrections matter | actual daily 09:15 live read | desired Option A canonical-capture route is `automatic_candidate`; all-consumer parity required |
| B16 rosters — current direct-read route | `automatic_active_health_unverified` | daily 07:00 UTC | actual daily 09:15 live read | desired Option A canonical-capture route is `automatic_candidate`; all-consumer parity required |
| B18 PBP — current direct-read route | `automatic_active_health_unverified` | nightly plus game windows | actual daily 09:15 live read | desired Option A canonical-capture route is `automatic_candidate`; Roster Auditor migration separately gated |
| B19 participation — current direct-read route | `automatic_active_health_unverified` | 2023+ postseason-only | actual daily 09:15 live read | desired Option A canonical route is `automatic_candidate` on a weekly February–March / monthly-otherwise clock; must not cap the four current-season streams |
| B20 Combine | `automatic_candidate` | upstream workflow 12:00/17:00 UTC March 3–12 + manual dispatch | proposed one conditional check 20:00 UTC March 3–13 | exact capture, content no-change, builder migration; PFR source clock still unverified |
| B21 schedules | `automatic_candidate` | every 5 minutes during the season | proposed Tuesday 06:15 ET year-round conditional check, before weekly Tuesday 10:00 Realized Outcome | exact source/finality provenance before first prediction-bearing run; no intraday cadence without a named consumer |
| B22 forward draft-picks route | `automatic_candidate` | upstream 05:00 UTC Wednesdays Sep–Feb; additionally daily Feb 1–15 and Apr 23–May 5; manual dispatch possible | proposed 12:00 UTC conditional checks on those days; frozen 2025 pin remains `static_pinned` | exact transport/capture + content no-change; PFR settlement/correction clock still unverified |
| B23 governed DynastyProcess `db_playerids` | `automatic_candidate` | upstream Friday 00:23 UTC + manual dispatch; delivery can lag | proposed Friday 08:15 ET blob-SHA check; one Saturday 08:15 ET retry whenever Friday is unchanged or retrieval fails; frozen 2025 pin remains `static_pinned` | source declaration, exact CSV/commit/blob provenance, forward identity retention; no workflow-status inference from unchanged bytes |
| B24 QB-validation players input | `static_pinned` | registered study input | no refresh | study has not run; automation cannot alter manifest inputs |
| N1–N8 PlayerProfiler | `blocked` | landed store came from human exports; a shadow HTTP POST route exists | no automatic job | automated acquisition remains blocked pending sanctioned-access, legal, and reliability proof |
| N9–N10 FantasyCalc forward | `automatic_active_health_unverified` | fetch-time snapshots; no provider publish timestamp | actual daily 09:00 job | add freshness registration, prove health history, and reconcile the request-time cache/live fallback behind one governed route |
| N11 legacy mixed snapshot archive | `manual_only` | frozen/legacy local archive | none | optional backtest only; do not use as current overlay source |
| N12–N14b Sleeper transactions | `automatic_candidate` | live league events | candidate daily current-season + weekly full-chain reconciliation | cursor/idempotence, call ceiling, marker/freshness, word |
| N18 Sleeper normalized league bundle | `automatic_active_verified` | endpoint state can change daily | actual daily 09:20 job | health basis: registered freshness, 21 consecutive successful runs through 2026-08-05, empty error log, current `ok`/ready markers, loaded job last exit 0; exact raw replay and request-time Roster Auditor reconciliation remain separate quality/route gaps |
| N18b two active `*_latest.json` fallback aliases | `manual_only` | production fallback seeds, not source vintages | no automatic refresh job | consumed by `load_production_league_set`; change only through explicit seed maintenance |
| N18b ten retained timestamped archives | `manual_only` | retained normalized history | none | no recurring use or refresh claim |
| N19 one-time exact endpoint history | `manual_only` | one-time 2023–2026 replay evidence | none | no established consumer; backup-covered; no invented recurring use |
| N15/N15b PFF | `manual_only` | human export | none | manual contract; fix YPRR materialization separately |
| N16/N17 CFBD | `blocked` | paid/event-driven; registry says 720h for historical data | no automatic job | David-approved per-run/month ceiling + canonical-wrapper-only route |
| R4 RAS | `blocked` | no production acquisition | none | governed use + NDA/retention feasibility |
| R6 RotoViz / R7 Campus2Canton | `manual_only` | fixture/manual export contract | none | no sanctioned automated API contract |
| R9 MFL rookie ADP | `blocked` | source result carries a timestamp but mutation cadence is **UNVERIFIED** | none until endpoint contract is repaired; post-repair candidate is weekly pre-Draft, at most daily through Aug 31, weekly Sep–Dec | current adapter query is not rookie-only in live output; correct/re-RED endpoint semantics before any first capture or scheduler |
| A6 DynastyProcess pinned values | `static_pinned` | immutable backtest inputs | no refresh | any forward capture must use separate path/job identity |
| R10 Dynasty Data Lab / R11 Dynasty Nerds | `blocked` | paid / no clean API | none | explicit use, access, cost, destination |
| R12 KTC + R14–R17 enterprise sources | `prohibited` | not applicable | none | current policy/cost/licensing rulings |

**B21 cadence evidence:** nflverse's primary
[Data Update and Availability Schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html#nflverse-gameschedule-data)
states that Game/Schedule data updates every five minutes during the season (accessed 2026-08-06).
The proposed **local** check is Tuesday 06:15 ET year-round, conditional on changed bytes and before
the Tuesday 10:00 Realized Outcome consumer. It remains planning evidence, not an installed job.

**C remains unchecked.** This table completes the current classification pass, but C still needs
independent per-row verification, numeric paid-call ceilings where applicable, and final ownership /
installed-job / freshness edges before it can be checked off.

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

## §6. §H — Sources we still need to ingest *(PROVISIONAL ANSWER; NOT CHECKED OFF)*

**Answer first:** substantial work is required on sources already present in the repo, but the
evidence does **not** prove that Dynasty Genius needs an unconditional new external provider now.
The highest-priority gaps are uncataloged exact bytes, live reads without replayable capture,
parallel acquisition routes, and incomplete materialization from sources we already have.

### Required existing-source reconciliation

| Gap | Kind / minimum honest state |
| :-- | :-- |
| Sleeper league-behavior history — 172 exact endpoint payloads + fetch log, four seasons, backup-covered, previously omitted | **catalog omission** — N19 now rows it; preserve endpoint grains and manual one-time cadence |
| Feature Refresh `player_stats` / `rosters` / `snap_counts` / `pbp` / `participation` | **absent canonical capture** — Option A exact-source capture, independent vintages, atomic bundle, last-good export, then consumer parity |
| NFL Combine used by `build_w2_features.py` | **active-builder live read** — immutable source capture + parser/version provenance before a new vintage reaches the active artifact |
| schedules + Realized Outcome player stats | **future-live uncaptured route** — canonical source vintage/finality before the first prediction-bearing run |
| nflverse draft picks / DynastyProcess `db_playerids` (`ff_playerids`) / nflverse players | **mixed-provider production, identity, freeze, backtest, and validation routes** — reconcile B22's 257-row frozen payload vs 80-row projection, preserve B23's separately pinned 12,457-row and governed 7,952-row identity vintages, and keep B24 uncaptured/static until the registered study runs |
| N18 Sleeper normalized bundle and request-time Roster Auditor | **parallel route + absent exact raw** — exact endpoint capture, explicit projection, consumer migration; in-season injury completeness test |
| FantasyCalc forward store and request-time cache/live fallback | **parallel market acquisition** — one canonical market capture, preserve physical/semantic Engine A/B separation |
| MFL rookie ADP adapter + `SOURCE_REGISTRY` declaration | **source-contract defect** — current undocumented query returns veterans; official rookie-only/no-mock parameters differ, while the machine registry note still calls `ROOKIES=1` documented/rookie-only. Future authorized repair must update adapter + registry declaration/notes + RED controls together before first capture or scheduling |
| PFF NCAA receiving-summary → `yprr_college` | **materialization gap** — source and builder exist, but active coverage is 0/874; reconcile identity/season join before seeking another provider |
| CFBD wrapper vs directly invokable builder | **bypassable canonical route** — the isolated raw+curated wrapper must become the only governed acquisition/promotion path |
| `nflverse_usage.db` | **absent schedule** — 13 bound specs, 12 materialized; `contracts` remains bound/uncaptured and its first scheduled capture is a landing gate |
| Nine materialized canonical streams with no production consumer | **absent consumer** — `snap_counts`, `injuries`, PFR ×4, `ff_opportunity`, `ftn_charting`, `depth_charts`; priority evidence, not a semantic prohibition |
| PlayerProfiler 1,520,009 `obs` | **absent production consumer outside ingestion** |
| R1 `nfl_data_py` mislabel + R18 declared snapshot / actual live PBP | **provenance defects** |
| B4–B13 share the canonical nflverse adapter/store but lack matching machine source declarations under R19 | **absent source declarations** — reconcile each family without pretending the NGS declaration covers it |
| DynastyProcess pinned values and `db_playerids` identity snapshots exist physically but have no `SOURCE_REGISTRY` entry | **absent source declaration** — decide whether explicit static-pinned / identity declarations are required; do not silently inherit FantasyCalc's market-source identity or relabel the nflreadpy client as the provider |
| **PFF has NO defensible deduplicated total.** Scope-nesting was tested at row level and **FAILED**: discarding `REG` loses a player outright and changes 942 shared rows (§3.3). 134,392 is a raw payload-row sum; 106,867 is only a proposed policy output | **absent normalization rule — row-level check RAN and FAILED** |
| Existing nflverse raw history begins 2026-07-31 | **point-in-time ceiling** — forward capture stops further loss; it cannot recreate prior as-of vintages |
| Retained inactive `app/data/sources/nfl_nextgen_stats/` tree | **retention decision outstanding** — preserved duplicate source tree is physically inventoried; do not delete or treat it as the active adapter |
| Sleeper `league_transactions/raw/` + tracked `league_snapshots/` surfaces | **physical-store reconciliation** — 20 raw transaction JSONs and 12 legacy seed/archive files are inventoried separately from the transaction DB and production league set |

### Conditional source acquisition

| Candidate | Current disposition |
| :-- | :-- |
| **Production RAS** | Real acquisition is missing if the narrow governed low/missing-RAS risk/context use remains required. Legal feasibility is unresolved: the provider's database instructions require an NDA and restrict sharing underlying data. Do not treat Combine as the proprietary RAS composite. |
| **Replacement live injury/practice/game-status provider** | Conditional only. First capture Sleeper `/players/nfl` exactly and run a predeclared in-season coverage/freshness test across designation, body part, practice, game status, source timestamp, and identity. Add a provider only if Sleeper fails the floor. |
| **MFL rookie ADP** | Existing registered source with separated descriptive-overlay destination, but adapter query semantics are currently defective and live output is not rookie-only. `blocked` pending correction/re-RED; first-capture priority is not yet the next gate. |

### Not presently justified

- `ff_rankings` / FantasyPros through DynastyProcess remains `blocked_for_use`, no RED.
- KTC scraping remains prohibited and market-overlay only.
- RotoViz / Campus2Canton fixture or manual-export declarations do not establish a production need
  or legal automated route.
- Dynasty Data Lab, Dynasty Nerds, and the enterprise providers remain deferred/prohibited without a
  specific decision, access path, cost, and legal destination.

**Why H remains unchecked:** these findings are now enumerated, but the canonical rows and route
states require a fresh independent re-verification after reconciliation. “No unconditional new
provider proven” is the current answer, not a claim that Layer 1 is complete.

---

## §6A. A-C Closure Matrix

**Purpose.** Replace open-ended row-by-row cycles with **one finite, independently verifiable batch**.
David agreed this sequence 2026-08-06. **Authoring rule:** every cell draws on already-measured
evidence; an unresolved cell stays an explicit closure item.

**No §1 checkbox moves until this matrix is independently verified as a batch.** Nothing here
authorizes code, capture, scheduler/plist changes, consumer migration, provider purchase, Layer 2,
commit, or push.

**Status vocabulary *(M3 — corrected)*.** A-C is an **INVENTORY gate, not a remediation gate.**
A defect can be *inventoried and closed as a fact* while its *fix* stays unauthorized.
* `VERIFIED — inventory closed` — the fact/classification is independently established. **Remediation
  may still be unauthorized; that lives in the Authority Dependency column, not the status.**
* `MEASURED — awaiting review` · `OPEN` — inventory work remains.
* `BLOCKED — needs David` — **only where a missing David ruling prevents the INVENTORY FACT itself
  from being settled.** *(My first draft marked six rows BLOCKED because their REMEDIATION needed
  David — which made Layer 1 inventory completion depend on builds the agreed sequence places AFTER
  A-C. Backwards.)*

**`UNVERIFIED` never satisfies a pass condition *(M4)*.** Per R4, a field is either independently
verified, or explicitly `N/A` / `not scheduled` **with evidence**. An `UNVERIFIED` field keeps its
row `OPEN`. A proposed automation class is **reviewed planning judgment**, not a measured fact.

### A — SOURCES

| Canonical row/cell | Current measured state | Exact unresolved question / defect | Evidence path or probe | Lane | Binary pass condition | Authority dependency | Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **R13 Sleeper — FOUR physical routes** *(M5: my first draft said four and listed three)* | (1) **N18** daily 09:20 normalized snapshot, consumed; (2) **N12/N13** `league_transactions.db`, manual, no consumer, with its own governed raw path **N14b** `app/data/league_transactions/raw`; (3) **N19** one-time multi-endpoint raw corpus; (4) **request-time live Roster Auditor read** (R18 path) | Which route is canonical per dataset, and what is each other route? | §3.4 · N14b (20 snapshots; latest-per-season 932 unique, 932/932 shared, zero either-side-only) · `league_transactions.py` L1009→L1022→L1029 | Claude · Codex | Each Sleeper dataset names exactly ONE canonical route; every other route is labelled with a **reason** from: `alt` · `superseded` · `separate corpus` · **`consumer edge`** · **`acquisition defect`** *(M5 — not every non-canonical route is accurately one of the first three)* | route retirement needs David | **MEASURED — awaiting review** |
| **R8 FantasyCalc — parallel acquisition** | Daily `fc_forward_capture.db` (20,043 `obs`, `fc_native`, 2026-06-24→2026-08-05) **and** request-time `app/cache/fantasycalc/market_values.json` / live fallback in the trade API + market-overlay service | Which is canonical? A request-time live fallback is an ungoverned acquisition path inside a serving surface | §2.1 R8 · N9/N10/N11 | Claude · Codex | One canonical market capture named; the request-time path classified with a reason. **Engine A/B market separation restated and unbroken** | none for the inventory fact | **OPEN** |
| **R1 `nfl_data_py` — source identity** | **No `nfl_data_py` import exists.** `ingest_2026_draft.py` imports **`nflreadpy`**, writes JSON, labels it `nfl_data_py_verified_nfl_draft`; declared `parquet_snapshot` | Registry names a provider the code does not use | V5 · `rg 'import nfl_data_py'` → nothing | Claude · Codex | **The DEFECT is inventoried, dated and classified as a source-identity defect.** *(Fixing the registry is remediation, not inventory)* | **repair needs David; does not block inventory closure** | **VERIFIED — inventory closed** |
| **R18 — declared vs actual provenance** | Declared `parquet_snapshot`/168h; actual is `live_direct_read`, consumer-triggered by `roster_auditor.py` (2024/2023), no snapshot, no cache. **A second live consumer of B18 `pbp`, not its own stream** | Declaration does not describe the physical route | V7 · V15 · `nflreadpy_qb_adapter.py::fetch_qb_nfl_stats` | Claude · Codex | **Defect inventoried; R18 recorded as a consumer edge on B18, not a stream** | **repair + any consumer migration need David; must NOT widen the five-stream Option A scope** | **VERIFIED — inventory closed** |

### B — STREAMS

| Canonical row/cell | Current measured state | Exact unresolved question / defect | Evidence path or probe | Lane | Binary pass condition | Authority dependency | Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **R7 states — ENUMERATED, not a basket** *(M1)*. Canonical stream rows **B1–B24**; Table B-N rows **N1–N11, N12–N14, N14b, N15, N15b, N15c, N16, N17, N18, N18b, N19** *(**N18b** was omitted from the first enumeration while N14b/N15b/N15c were explicitly listed — the same letter-suffix class, one member missed)* | Counts/grains measured; **B1–B12 `exported` independently verified** at run `nflverse-usage-20260805T1334216901700000` (V11). R7 states otherwise incomplete | Each listed row needs all five states: `bound` · `captured` · `exported` · `consumed` · `decision_supported` | §3.1 · V3 · V11 | Claude · Codex | **Every enumerated row ID above carries all five states, each independently verified or explicitly `N/A` with evidence. `UNVERIFIED` leaves the row OPEN** *(M4)* | none for the inventory fact | **OPEN** |
| **Parallel-route relationships — enumerated** | Three pairs: `snap_counts` **B4 ↔ B17**; Sleeper **N18 ↔ N12/N13 ↔ N19 ↔ R18 request-time**; FantasyCalc **N9 ↔ request-time cache** | Each pair needs a canonical route and a classified counterpart | §3.4 · B4/B17 · V15 | Claude · Codex | Every listed pair names its canonical route and classifies the other with a reason from the M5 vocabulary | route retirement needs David | **OPEN** |
| **Final automation classes — the EXACT §4.4 member set** *(M1: "B1–B24" was incomplete)*. §4.4 is the deterministic reference and spans **beyond B-rows**: B1–B24 **plus** N1–N8, N9–N10, N11, N12–N14b, N15/N15b, N16/N17, N18, **N18b (two rows)**, N19, **R4, R6, R7, R9, R10, R11, R12, R14–R17, and A6** | Provisional classes in refresh plan §3; cadence research independently CLEAR at its pin | No canonical stream row carries a FINAL class | refresh plan §1 (seven classes) · cadence artifact + disposition v2 | Claude authors · Gemini facts · Codex reviews | **Every member of the §4.4 set carries exactly one of the seven classes, recorded as reviewed planning judgment — not as a measured fact** *(M4)*. **Membership is resolved from §4.4 itself, not from a copied list here** — a duplicated roster would rot the moment §4.4 gains a row | class ≠ enablement | **OPEN** |
| **B13 `contracts`** | Bound with no table; never executed; zero product-store rows | — | §3.1 B13 | Claude · Codex | **Row states `bound / not captured` and names the landing gate.** Inventory fact is settled | **landing needs a separate David word AND one export covering all twelve prior streams plus contracts** | **VERIFIED — inventory closed** |
| **N18 — absent exact raw capture** | Scheduled 09:20, marker-pinned, consumed, 21 runs. **Normalized only** — eight endpoints pass through `build_universe_snapshot`; raw bytes never retained | Fails `01` raw-snapshot-before-parse | V16 · V17 | Claude · Codex | **Row states `normalized snapshot; raw endpoint replay unavailable`.** Inventory fact settled | **exact-raw capture = step 4(d); needs David** | **VERIFIED — inventory closed** |

### C — CADENCE

| Canonical row/cell | Current measured state | Exact unresolved question / defect | Evidence path or probe | Lane | Binary pass condition | Authority dependency | Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **Cadence fields — ENUMERATED over the EXACT §4.4 member set** *(M1: "B1–B24" omitted every non-nflverse and source-group row)* | Source-publish cadences pinned to primary sources, independently CLEAR; **not yet written onto the canonical rows** | **Each member of the §4.4 set** — B-rows AND the N/R/A rows listed in the automation-classes row above — needs five fields: source-publish cadence · job cadence · freshness expectation · dependency edge · proposed automation class | cadence artifact (CLEAR at pin) + disposition v2 · Gemini job/marker facts · §4.1 | Claude · Gemini facts · Codex | **Every member of the §4.4 set carries all five fields, each independently verified or explicitly `N/A`/`not scheduled` WITH EVIDENCE. `UNVERIFIED` leaves the row OPEN** *(M4)*. **R3 held: job ≠ freshness ≠ stream cadence** | pinning ≠ scheduling | **OPEN** |
| **`nflverse_usage.db` — absent schedule** | 13 bound specs, 12 materialized, 1,491,691 `obs`; **no LaunchAgent invokes the canonical capture runner** | Scoped to this store only — **NOT the layer** (N18 and FantasyCalc are scheduled) | §4.2 · `rg -ln 'run_nflverse_usage_capture' ops/` → nothing | Claude · Codex | **Row states the absent schedule at the correct grain with counter-examples named.** Inventory fact settled | **scheduler = David only** | **VERIFIED — inventory closed** |
| **⏰ CH1 — ANY missing input caps ALL FIVE. ALREADY LIVE** *(M2 — my "harmless" claim was FALSE)* | **Probed 2026-08-06:** `rosters` 2026 **returns 2,930 rows × 36 cols — usable current-season data EXISTS**; `player_stats` 2026 **ConnectionError (404)**; `snap_counts`/`pbp`/`participation` **rejected client-side by the installed nflreadpy (`Season must be between … and 2025`)**. `_load_source` builds all five in ONE dict literal, so `player_stats` raises first and `_resolve_default_source` steps the WHOLE window back to 2025. **The 2,930 roster rows are silently discarded today while the job reports `ok`.** The job has never run in-season (log begins 2026-06-28) | **TRIGGER HAS FIRED.** Restated: **ANY missing input caps all five** — participation is the structurally long-lived case, **not the only cause**. **SECOND FAILURE MODE, from my own probe:** three loaders raise **`ValueError`**, which `_resolve_default_source` **does NOT catch** (it catches `ConnectionError` only, L101). Once `player_stats_2026` publishes while the installed client still caps at 2025, the run **fails hard** instead of stepping down | CH1 · live 2026 probe above · `run_feature_refresh.py::_load_source`, `_resolve_default_source` L99–103 · `feature_refresh.out.log` | Claude · Codex | **A durable control proving NO single missing stream can cap ANY other stream** — covering both the `ConnectionError` step-down path and the uncaught `ValueError` path | **code / consumer-migration word from David.** *(No calendar date asserted; the trigger is source publication and it has already occurred)* | **VERIFIED — inventory closed; REMEDIATION TIME-SENSITIVE** |
| **B19 `participation` cadence** | 2023+ publishes after the postseason only; no in-season updates | Must not be modelled as a daily source | cadence artifact B19 | Claude · Codex | Row carries annual/postseason cadence and an explicit "not daily-current" note | none for the inventory fact | **MEASURED — awaiting review** |

### Option A preparation — the agreed four-step order *(M6; NOT A-C blockers)*

| Step | Item | Pass condition when taken up |
| :-- | :-- | :-- |
| **4(a)** | `snap_counts` consumer migration | Parity proven **at ONE vintage** (205,354 rows value-identical; candidates 2,743 × 39 value-identical). **That experiment is EVIDENCE, not the pass condition** — migration requires a **governed loader plus a durable candidate-equivalence control** |
| **4(b)** | Canonical exact-source capture for **`player_stats`, `rosters`, `pbp`** | Exact source bytes, content-addressed, **prior accepted versions retained when bytes change** (season URLs are mutable — measured) |
| **4(c)** | **`participation` on its own postseason cadence** | Independently versioned acquisition/fallback proving its absence cannot cap the other streams |
| **4(d)** | **N18 exact raw endpoint capture** | Exact endpoint bytes retained before normalization; a separate Sleeper correction |

**Separate non-blocking note — PFF combined-view aggregation.** **Not one of the four steps.**
Explicitly outside the A-C blocking path (David, 2026-08-06): at Layer 1 preserve scope as a key and
keep **134,392** labelled raw-grain. Any combined/current-state policy is later semantic-layer work.

**Why this matrix is not itself a closure.** It enumerates and pins; it decides nothing. `§H` stays
unchecked until the canonical rows are independently re-verified after reconciliation. **H2 QB
rushing remains a registered hypothesis UNDER TEST with no result.**

---

## §6B. Step 1 — SOURCE-ROUTE DISPOSITIONS *(closes the §6A "A" rows)*

**Scope:** the canonical route per dataset, and every parallel route classified with a reason from
the §6A vocabulary — `alt` · `superseded` · `separate corpus` · `consumer edge` · `acquisition
defect`. **Classification only. No route is retired, repaired or migrated by this section.**

### §6B.1 FantasyCalc — canonical + one acquisition defect

| Route | Measured | Disposition |
| :-- | :-- | :-- |
| **`fc_forward_capture.db`** via `scripts/run_fc_forward_capture.py`, daily 09:00 | **20,518 `obs`, 44 snapshot dates 2026-06-24 → 2026-08-06**, carrying `snapshot_date` · `source` (`fc_native`) · `settings_hash` · `retrieved_at` | **CANONICAL** — governed capture with provenance |
| `fetch_with_cache()` (`fantasycalc_adapter`) → `app/cache/fantasycalc/market_values.json`, **live `httpx.get` on miss/expiry**, called at REQUEST TIME by `market_overlay_service.enrich_pvo_list_with_market_overlay` | single **overwritten** file; TTL-gated; never raises, degrades with caveats | **⛔ `acquisition defect`** |

**Why `acquisition defect` and not `alt`:** it acquires from the provider **outside the governed
route, at serving time**, and **what it served is not preserved** — one overwritten file, no vintage.
So the overlay can serve a market value **with no corresponding row in the capture store**, and no
later reader can reconstruct what was shown. *(`alt` would imply a second representation of captured
data; this is uncaptured acquisition.)*

### §6B.2 Sleeper — FOUR routes, three datasets

| Route | Dataset | Disposition |
| :-- | :-- | :-- |
| **N18** `league_runtime/` daily 09:20 normalized snapshot bundle | league/universe state | **CANONICAL for league state** — *carrying its own recorded defect: normalized only, raw endpoint replay unavailable (§3.4 / V17)* |
| **N12/N13** `league_transactions.db` + **N14b** `league_transactions/raw` | transaction history | **CANONICAL for transactions** — and the **only** Sleeper route satisfying `01` raw-before-parse (`write_raw_snapshot` → `normalize` → `upsert`) |
| **N19** `league_behavior/raw/` | transactions **+** matchups/league/users/rosters/traded-picks/drafts | **SPLIT disposition:** its **923 transaction records are `alt`** of N12 (strict subset, §3.4) · its **other endpoint families are a `separate corpus`** not held anywhere else |
| **Roster Auditor request-time reads** — `app/services/roster_auditor.py:9` imports `get_all_players`, `get_leagues`, `get_rosters`, `get_user` from `app.data.sleeper` | league/roster/player universe at serving time | **`consumer edge`** — a serving-path read of the same upstream datasets, **not a fifth ingestion stream** *(the R1 source ≠ stream ≠ store rule, applied as it was for R18/B18)* |

**Two Sleeper routes, opposite provenance quality** — N12 satisfies raw-before-parse; N18, the
*scheduled and consumed* one, does not. The catalog previously implied the reverse.

### §6B.3 Standing grain warning — stores that go stale BY THE CLOCK

**A new staleness class, distinct from the §5 register.** §5 records claims invalidated by an *edit*.
**`fc_forward_capture.db` is a DAILY-GROWING store**: the catalog carried **20,043** as though it
were a fixed property; it is **20,518** today and will differ tomorrow.

**Rule adopted:** a count for a growing store is published **only with an as-of date**, or not at all.
`20,518 obs as of 2026-08-06` is a fact; `20,518 obs` is a claim that decays silently. This applies
to N9/N10 (FantasyCalc), N12/N13 (Sleeper transactions), and N18/N18b — every store with a live
capture job behind it.

---

## §6C. Step 2 (part) — AUTOMATION CLASSES from Gemini's job telemetry

**Scope:** the automation class for every store Gemini's cadence audit covers. **A class is REVIEWED
PLANNING JUDGMENT, not a measured fact** (§6A / M4) — the *evidence* is Gemini's, the *class* is mine
and is Codex's to challenge. Vocabulary is the refresh plan's seven values.

**Evidence:** `docs/agent-ledger/evidence/2026-08-06/gemini_layer1_cadence_audit_response.md`
(plist declarations, `launchctl` loaded state, last observed fire/exit, and whether a job refreshes
the store).

| Store / stream | Gemini's measured job facts | Class *(judgment)* | Why |
| :-- | :-- | :-- | :-- |
| `nflverse_usage.db` (13 bound specs) | no plist · not loaded · no execution logs · **not refreshed by any job** | **`automatic_candidate`** | Technically automatable; **no governed job exists.** Physical state is manual-only — the class records possibility, not a plan |
| Feature Refresh **direct reads** (B15–B19) | job loaded, daily 09:15, last fire `noop` · **streams read in memory, no raw snapshots written** | **`blocked`** | Blocked pending David's A/B architecture ruling — **not** `automatic_active`: the JOB is automated, the STREAMS are not captured. R3: a consumer job's cadence is not its upstream stream's |
| `fc_forward_capture.db` | plist daily 09:00 · **loaded** · success 2026-08-05 13:00 UTC · **appends daily rows** · **freshness config: none found** | **`automatic_active_health_unverified`** | Fires and captures, but **no registered freshness policy**, so health cannot be evidenced from a fire alone |
| `fc_snapshots.db` (legacy) | no plist · no logs · frozen, last modified 2026-05-30 | **`static_pinned`** | A frozen mixed-source archive (§3.1 N11); correct cadence is no refresh |
| `league_transactions.db` | no plist · not loaded · no logs · **run manually only** | **`manual_only`** | Confirms V4 — the 09:20 job never touches it |
| `app/data/league_runtime/` (N18) | plist daily 09:20 · **loaded** · freshness config daily 09:20 · success 2026-08-05 13:20 UTC | **`automatic_active_health_unverified`** | Fires, captures and is consumed, **and** carries a freshness registration — but it is **normalized-only with no raw endpoint replay** (V17), so I will not call it `verified` |
| PlayerProfiler stores | no plist · no logs · **manual file copy only** | **`manual_only`** | Matches R3's `manual, by David` |
| PFF manual export inventory | no plist · no logs · manual reconciliation | **`manual_only`** | Human export is the current contract |
| CFBD foundation promoted store | no plist · no logs · manual script | **`blocked`** | Paid source; needs David's cost/run ruling before any clock (refresh plan §7.2) |
| `nflreadpy_qb_context` (R18) | **⛔ CORRECTED — there is NO roster-capacity job.** Verified: `launchctl list` shows **exactly 8** dynasty jobs and none is `roster-capacity`; `~/Library/LaunchAgents` and `ops/launchd/` each hold the **same 8** plists. **Reads live PBP in memory, no cache/snapshot** | **`blocked`** *(class unchanged)* | **NOT scheduled at all** — an uncaptured live read reached only through a consumer. *(This cell first said "roster-capacity plist weekly Tue 10:00 · loaded", taken from Gemini's cadence audit and NOT verified by me. Gemini's two reports contradict each other and the earlier one is wrong. The class survives; the evidence under it did not.)* |
| QB validation raw path (R20) | no plist · no logs · **study has not run** | **`static_pinned`** | Pinned pre-registered inputs; **automation must be physically unable to overwrite them.** H2 QB rushing remains UNDER TEST with no result |

**Two classes I deliberately did NOT assign `automatic_active_verified`.** Both `fc_forward_capture`
and `league_runtime` fire successfully — but `02`'s own distinction is that **a fire is not health
evidence.** One lacks a freshness registration entirely; the other is normalized-only. **`verified`
has to be earned by evidence of health, not by a green exit code.**

### §6C.1 Freshness registry — verified, and TWO registrations with NO JOB

**Verified independently** from `app/config/report_freshness.json` and `launchctl list`:

| Registered `artifact_id` | cadence | `dormant_ok` | Has a job? |
| :-- | :-- | :-- | :-- |
| `pvo_refresh` | daily | false | ✓ |
| `feature_refresh` | **weekly** | **true** | ✓ — **fires DAILY 09:15. Known mismatch** |
| `what_changed` | daily | false | ✓ |
| **`roster_capacity`** | weekly | false | **⛔ NO JOB EXISTS** |
| **`league_opportunity`** | weekly | false | **⛔ NO JOB EXISTS** |
| `realized_outcome` | weekly | true | ✓ |
| `market_divergence` | daily | false | ✓ |
| `league_capture` | daily | false | ✓ |

**8 registrations · 8 loaded jobs · but they are NOT the same 8.** Two artifacts carry a registered
freshness expectation with **no scheduler behind it** — the inverse of the `feature_refresh`
mismatch, and arguably worse: a staleness policy that can never be satisfied because nothing is
scheduled to satisfy it. **Recorded as a measured fact; not a licence to create either job.**

**GEMINI CONTRADICTION, recorded rather than smoothed:** its earlier cadence audit reported
`com.davidleess.dynasty-roster-capacity` as **loaded**; its later report correctly says
`roster_capacity` has no plist. **The later report is right.** I had already propagated the earlier
claim into the R18 row above before verifying it — corrected there.

**STILL OPEN in step 2:** the R7 states (`bound`/`captured`/`exported`/`consumed`/
`decision_supported`) across the enumerated B and N rows, and automation classes for the §4.4 members
Gemini's audit does not cover. **A fresh Gemini request covering the complete plist set, the full
`report_freshness.json` registry, and every schedule-vs-freshness mismatch is in flight.**

---

## §6D. Step 2 (complete) — R7 STATES for every enumerated stream

**R7 states:** `bound` (a StreamSpec exists) · `captured` (rows in a store) · `exported` ·
`consumed` · `decision_supported`. **`UNVERIFIED` leaves the row OPEN** (§6A / M4) — it is used here
where I have no measurement, never as a soft yes.

**`decision_supported` is ✗ for EVERY row, and that is a governance invariant rather than a
measurement:** `00` §The No-Verdict Line holds every descriptive output at `decision_supported=False`
until a pre-registered validation David ratifies earns otherwise. **No Layer 1 stream has one.** It
is stated once here rather than repeated 40 times.

### Canonical nflverse streams (B1–B14)

`exported` for **B1–B12 is INDEPENDENTLY VERIFIED** (V11: every named Parquet exists and recomputes
to the ready-marker SHA at run `nflverse-usage-20260805T1334216901700000`).

| Row | Stream | bound | captured | exported | consumed |
| :-- | :-- | :-: | :-: | :-: | :-- |
| B1–B3 | `ngs_passing` 5,933 · `ngs_rushing` 6,059 · `ngs_receiving` 14,731 | ✓ | ✓ | ✓ | **✓** feature refresh, via last-good export |
| B4 | `snap_counts` / `player_snap_count` 253,106 | ✓ | ✓ | ✓ | **✗** canonical export has NO production consumer *(V2-F4)*; the daily job's live read is a separate route (B17) |
| B5 | `injuries` 45,337 | ✓ | ✓ | ✓ | ✗ |
| B6–B9 | `pfr_pass` 5,424 · `pfr_rush` 18,461 · `pfr_rec` 35,724 · `pfr_def` 62,345 | ✓ | ✓ | ✓ | ✗ |
| B10 | `ff_opportunity` 47,282 | ✓ | ✓ | ✓ | ✗ |
| B11 | `ftn_charting` 185,215 | ✓ | ✓ | ✓ | ✗ |
| B12 | `depth_charts` 812,074 | ✓ | ✓ | ✓ | ✗ |
| B13 | `contracts` | ✓ | **✗ never run** | ✗ | ✗ |
| B14 | `ff_rankings` | ✗ | ✗ | ✗ | ✗ — `blocked_for_use`, no RED |

**Nine materialized, exported, consumerless streams** — B4–B12. Priority evidence, not a prohibition.

### Direct provider reads (B15–B19) — the inverse shape

| Row | Stream | bound | captured | exported | consumed |
| :-- | :-- | :-: | :-: | :-: | :-- |
| B15–B19 | `player_stats` · `rosters` · `snap_counts` · `pbp` · `participation` | **✗** | **✗** | **✗** | **✓ 09:15 Feature Refresh, live** |

**Consumed but never captured** — the exact inverse of B4–B12, and the object of David's A/B ruling.
**B17 duplicates B4.** *(CH1 now prevents one absent stream capping the rest; that changes failure
behaviour, not capture state.)*

### B20–B24 — UNVERIFIED, and named as such

| Row | Stream | State |
| :-- | :-- | :-- |
| B20 Combine · B21 schedules · B22 draft picks · B23 `ff_playerids` · B24 players | — | **All five R7 states `UNVERIFIED`.** Codex's SG3/§6 records them as live/mixed-provider routes, but I have taken **no per-row measurement**. **These rows keep step 2 OPEN.** Probe: locate each read site, then test store presence and export membership as done for B1–B12 |

### Non-nflverse (Table B-N)

| Rows | bound | captured | exported | consumed |
| :-- | :-: | :-: | :-: | :-- |
| N1–N8 PlayerProfiler (1,520,009 `obs` + 3,290 `idn` + 63 `cap`) | n/a — not StreamSpec-bound | ✓ | ✗ | **✗** none outside ingestion |
| N9/N10 FantasyCalc (20,518 `obs` **as of 2026-08-06**; joinable is `alt`) | n/a | ✓ | ✗ | ✓ market overlay |
| N11 `fc_snapshots` 6,790 (mixed-source) | n/a | ✓ | ✗ | ✓ market overlay |
| N12/N13 + N14b transactions (932 `obs`; raw 20 snapshots) | n/a | ✓ **with raw-before-parse** | ✗ | **✗** *(V4)* |
| N15/N15b/N15c PFF (149 payloads; 134,392 raw-grain) | n/a | ✓ | ✗ | **partial** — ONE lane only *(V12)* |
| N16/N17 CFBD (874 curated; 1,202 raw) | n/a | ✓ | ✗ | ✓ Engine A |
| N18 Sleeper snapshot | n/a | ✓ **normalized only, no raw replay** | ✓ marker-pinned | ✓ league derivation |
| N18b seed/archive aliases | n/a | ✓ | ✗ | ✓ production fallback |
| N19 league-behavior raw | n/a | ✓ | ✗ | ✗ |

**Step 2 is COMPLETE except B20–B24**, which are explicitly `UNVERIFIED` and hold it open.

---

## §7. Disposition of Codex review v2 *(SHA `d99b3247…`)* — F1–F7 ALL ACCEPTED
> **⚠ HISTORICAL RECORD — NOT A LIVE BLOCKER LIST *(V22)*.** This section preserves the v2 review
> and its dispositions as written at the time. **Its "still owed" items — full registry enumeration,
> non-nflverse stream rows, B4's consumer state — have since been COMPLETED** (§2.1, §3.1, and the
> B4 resolution respectively). **The live gap list is §6 and nowhere else.** *(This section was being
> read as current, which is the same correction-without-canonical-reconciliation defect the register
> in §5 exists for — it just happened to a whole section rather than a row.)*

| F | Finding | Disposition |
| :-- | :-- | :-- |
| F1 | A/B enumeration incomplete despite `[x]` | **Accepted.** Unchecked; registry's 20 named; missing streams listed in §3. |
| F2 | Source-grain violations | **Accepted.** DynastyProcess re-merged to one source; FantasyCalc/DP store-mixing noted; Sleeper corrected to transactions-only. |
| F3 | Totals mix/double-count grains; 101 delta solved | **Accepted, reproduced.** R5 added; all four decompositions measured; the v1 error recorded in §3. |
| F4 | Feature-refresh semantics false | **Accepted, reproduced.** §4.2 rewritten; surfaced the no-scheduled-refresh finding. |
| F5 | §4 internal conflicts; freshness entries missing | **Accepted.** Heading corrected; missing `report_freshness.json` entries marked; evidence paths still owed. |
| F6 | B6–B9 must be four rows | **Accepted, reproduced.** Split with measured counts; R7 multi-valued state added; 3/9/1 summary withdrawn. |
| F7 | §6 cannot answer David | **Accepted.** Marked unanswerable; PFF corrected to partial. |

~~**Still owed before a fresh review:** full registry enumeration, non-nflverse stream rows, per-row
evidence paths/timestamps, B4 consumer state.~~
**SUPERSEDED — struck inline rather than left to the section banner.** Registry enumeration → §2.1.
Non-nflverse stream rows → §3.1. B4 consumer state → resolved (canonical export has no production
consumer). Per-job cadence evidence → `layer1_cadence_codex_overnight_v1.md`; **per-STREAM cadence
remains genuinely open** and is carried in §6. *(Found by my own whole-document sweep, not flagged in
V22-V25: a bolded standalone line reads as live no matter what banner sits above it, so it is struck
where it stands.)*

---

## §8. Change log

| Date | Who | Change |
| :-- | :-- | :-- |
| 2026-08-05 | Claude | v1 created. |
| 2026-08-05 | Codex | NOT CLEAR, seven findings. |
| 2026-08-05 | Claude | **v2 rebuild.** F1–F7 accepted; F3/F4/F6 reproduced first. A/B/C reopened; grain tagging added; feature-refresh semantics corrected. |
| 2026-08-05 | Codex | v2 review — **NOT CLEAR**, four findings (V2-F1..F4). |
| 2026-08-05 | Claude | **v3.** V2-F1..F4 all accepted, none contested. §1 source count 9→**7** (stale after the F2 merge — **fifth** §5 instance). Table B carries all **five** R7 states with disposition as its own column. "13 streams" restated as **13 bound / 12 materialized**. **B4 resolved** from Codex's probe: canonical export has no production consumer; the daily job's direct `load_snap_counts` is a separate provider-read stream — so the nine consumerless streams are now NAMED. `exported` marked column-wide UNVERIFIED pending probes — **superseded by V11**. |
| 2026-08-06 | Codex | **v4 reconciliation candidate.** Applied CV1–CV21: added Sleeper exact raw history; Combine/schedules/draft-picks/DynastyProcess-db_playerids/players; expanded consumer and parallel-route edges; inventoried retained NGS + Sleeper raw/archive surfaces; split active seed aliases from archives; bounded R19; corrected CFBD/PFF grains; added N18 endpoint/injury ceiling, point-in-time ceiling, cadence evidence, MFL destination, and §H source-gap answer. Nothing checked off pending fresh independent review. |
| 2026-08-06 | Codex | Added independently researched B20/B22/B23 conditional cadence candidates and blocked R9 after live current-query output proved non-rookie semantics; machine registry declaration included in future repair gate. No scheduler or fix opened. |
