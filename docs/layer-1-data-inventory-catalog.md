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
      in an appendix.** **Still UNCHECKED — but the gate has moved *(Q2)*.** The Sleeper and
      FantasyCalc acquisition routes are **no longer unreconciled: §6B dispositions every one of them**
      (canonical named per dataset; each parallel route classified, including two `acquisition
      defect`s). That work is **authored and awaiting independent review — which is not the same as
      missing.** The real remaining gate is Codex's verification of §6B. The two **provenance defects**
      (R1's `nfl_data_py` mislabel, R18's declared-vs-actual route) are **inventoried and closed as
      facts**; their repair is remediation needing David's word and does not gate this checkbox.
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
      **Restated *(Q2)* — none of this is missing any more.** Complete R7 states for every enumerated
      row are in **§6D**; the parallel Sleeper / FantasyCalc routes are dispositioned in **§6B**; final
      automation classes for the exact §4.4 member set are in **§6C/§6E**. **All of it is
      `MEASURED — awaiting review`, authored by the implementing lane.** The gate is therefore
      **independent verification under R4**, not authorship — specifically Codex reruns of the
      B20–B24 / N14 probes and of the corrected N9/N10, N11 and N16/N17 consumer states.
- [ ] **C. Refresh frequencies** — source-publish cadence planning is independently CLEAR at the
      pin named in §4.1 **for the nflverse B-rows only** — *that pin never covered Sleeper or
      PlayerProfiler* — and **§6E now carries all five fields for every §4.4 member** *(Q2)*. **ONE
      gate keeps this open *(L1 — corrected)*: the open source-publish fields below**, plus any
      outstanding independent-review gate.
      **⛳ THE OPEN SET IS FIVE FIELDS, NOT TWO *(branch-(b) ruling, 2026-08-07)*:**
      **N1–N8 · N19 · N18 · N12/N13 · N14b.** `continuous`/event-driven is admissible **only on
      independent verification — the label is not evidence for itself**, so N18's and N12/N13's
      long-standing descriptive values never satisfied M4, and **N14b inherits N12**. **N14 proper is
      an evidenced `N/A`** and is *satisfied*, not open.
      **FIELDS vs CLOCKS — the distinction is load-bearing, and the CLOCK count was WRONG:** these
      remain **five §4.4 member FIELDS**, but the `N1–N8` member is a **GROUP, not one clock** —
      it decomposes into **FIVE distinct PlayerProfiler upstream REPORT FAMILIES**, so the true count
      is **EIGHT provider clocks, not four** *(corrected 2026-08-07; the earlier "four" counted the
      whole `N1–N8` group as a single clock)*:
      **PlayerProfiler — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) ·
      N5 medical history · N6 Data Analysis/player-season** · **Sleeper — N19 · N18 · N12/N13**.
      **NOT independent clocks:** **N7** `pp_identity_bridge` is **derived from the ROSTER export and
      inherits N2** (`playerprofiler_roster.py:594` writes it under `stream=ROSTER_STREAM`; gamelog
      `:365` and pbp `:310` only read it and refuse when empty) · **N14b inherits N12** · **N8**
      `pp_capture`/`pp_pbp_capture` is **OUR capture ledger, an EVIDENCED `N/A` under the same M4 limb
      as N14** — satisfied, not open.
      **The MEMBER-FIELD count is unchanged at five; only the clock decomposition is corrected.**
      *(This item read "**the two source-publish fields remain unresolved** — N1–N8 PlayerProfiler and
      N19's Sleeper endpoint families *(Q1)*". **Self-found while sweeping F2's claim class: the
      primary progress surface was still reporting two.** K2 exists precisely to stop a summary
      surface drifting from the section it summarises, and it had drifted again.)*
      **BOUNDARY, NOT A GATE:** the clocks here are **planning targets, not installed jobs**.
      *(This previously read as a second closure gate. It is not one: §6A permits a field to be
      verified **or** explicitly `N/A`/`not scheduled` WITH EVIDENCE, its authority column says
      **pinning ≠ scheduling**, and M3 separates inventory closure from remediation. Making
      installation a gate would put A-C behind **scheduler enablement that the agreed sequence places
      AFTER inventory closure** — backwards, and the same inversion M3 already corrected once.)*
      **Characterised 2026-08-07, not closed *(K2)*:** the two ORIGINAL fields stay **OPEN** — **N1–N8 unmeasurable from held evidence** pending an adequate governed series; **N19 has a measured, bounded, NORMALIZED observed-change rhythm that is NOT a publish cadence** and does not cover the N19-only families. **The other three (N18, N12/N13, N14b) were opened by the branch-(b) ruling above.**
      **Under M4 ANY ONE open field alone holds this checkbox** *(read "either one" while only two were named)*.
      **Route note, stated with its object:** repeat manual exports are the identified route to a
      **bounded descriptive observed-change series** for N1–N8 under current sanctioned capability —
      **not a route to M4 closure**. A **direct provider, support-channel or subscriber-facing
      declaration remains possible and untried.** The public-documentation route was tried
      2026-08-07 and is negative **for the inspected pages only**.
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
| R8 | `fantasycalc` | market_overlay | `json_cache` | 24 | `use_cached` | free | **TWO acquisition routes:** daily `fc_forward_capture.db` (**20,518 `obs` as of 2026-08-06**, measured 22:23 ET; 44 snapshot dates 2026-06-24 → 2026-08-06) plus request-time `app/cache/fantasycalc/market_values.json` / live fallback used by the trade API and market-overlay service |
| R9 | `mfl_rookie_adp` | market_overlay | `json_cache` | 24 | `use_cached` | free | **BLOCKED:** adapter + separated `app/data/valuation` destination built, but current undocumented `ROOKIES=1&IS_MOCK=No` query returns veterans; official rookie-only contract is `IS_KEEPER=R&IS_MOCK=0`. Zero cache, output artifact, or scheduler |
| R10 | `dynasty_data_lab` | market_overlay | `none` | — | `skip_enrichment` | **paid** ($4/1k req) | **deferred — no capture** |
| R11 | `dynasty_nerds` | market_overlay | `none` | — | `skip_enrichment` | no clean API | **deferred — no capture** |
| R12 | `ktc` | market_overlay | `none` | — | `skip_enrichment` | **PROHIBITED** — ToS bars scraping | **none, by rule** |
| R13 | `sleeper` | context_signal | `json_cache` | 1 | `use_cached` | free | **FOUR measured routes, different states:** (a) `app/data/league_runtime/` — scheduled daily 09:20 normalized snapshot, consumed, raw replay unavailable (N18); (b) `league_transactions.db` — **manually run / unscheduled** *(Q3 sweep: a FOURTH site carrying the stale `manual_only` token, in the §2.1 registry row. Codex named R13 in §6A and N14b in §3.1; this one was found by grepping the whole document for the concept rather than fixing only the two cited)*, no consumer; (c) `app/data/research/league_behavior/raw/2026-07-19/` — manual one-time exact endpoint history, replayable + backup-covered (N19); (d) request-time live Roster Auditor calls, no exact capture |
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
daily store, **20,518 rows as of 2026-08-06**), **R13 `sleeper`** (`scripts/run_league_transaction_capture.py`, durable
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
- **B21 schedules** — canonical source capture landed 2026-08-09 at
  `app/data/sources/nflverse_schedules` (7,548 rows × 46 columns; 272 rows for season 2026; raw SHA
  `eeea1f47644c…`; schema SHA `9bbd6413bc4c…`). The loaded Realized Outcome job remains a separate
  direct-read consumer and current runs gate before source access because prediction snapshots are
  absent. Consumer migration and terminal-finality evidence are not implied by the capture.
- **N20 CFBD FBS schedules** — one paid, season-scoped canonical capture landed 2026-08-09 at
  `app/data/sources/cfbd_fbs_schedules` from exact query
  `year=2026&seasonType=both&classification=fbs`: 888 rows × 34 fields, raw SHA
  `76f0af56c903…`, schema SHA `0a87d5754e30…`, one check / one content vintage / one accounted
  request. All 888 returned games are `regular`; 761 are FBS-vs-FBS and 127 FBS-vs-FCS. No
  scheduler or consumer is implied by this source landing.
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
| A4 | CFBD | **paid** | `sources/cfbd_foundation/` + `sources/cfbd_fbs_schedules/` | **measured** — foundation promoted run `20260802T024342156864Z`, **1,202** raw payloads, 874 curated rows *(V1)*; separately, one canonical 2026 FBS `games` payload with **888 source rows**, one check/vintage/request *(2026-08-09)* |
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

Measured 2026-08-05, read-only, at commit `2a42759` — **AS OF THAT DATE. Superseded 2026-08-08: all 13 are now materialized (`contracts` captured) and the store holds 1,588,713 `obs` (+103 capture-ledger rows = 1,588,816 physical). The dated figures below are preserved as the measurement they were, not rewritten.** **13 loader-bound StreamSpecs; 12 materialized
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
| B21 | `schedules` **(canonical capture + separate future-live direct read)** | `app/data/sources/nflverse_schedules` | **7,548** | ✗ | ✓ | ✗ | **loaded Realized Outcome job still reads the provider directly; current runs gate before access on absent predictions** | ✗ | `substrate_only` — canonical raw/vintage/marker landed; consumer migration and finality remain separate |
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
2. **N12/N13 stay consumerless.** The 09:20 cadence belongs **only** to N18. ~~and `manual_only`~~ — **class assertion struck (R2):** §§4.4/6C/6E now carry `automatic_candidate`, because no human export is involved, only an absent scheduler. **Consumerless is unchanged and is the point this correction was making.**
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
capture; **B21 is now canonical-captured** but its future-live consumer has not been migrated, and
the source still cannot prove terminal finality.
**B22–B24** are existing mixed-provider identity/study dataset families that the prior table
omitted: B22/B24 are nflverse-backed, while B23 is DynastyProcess `db_playerids` transported by
nflreadpy. Their callers mix production builders, one-time freezes, identity work, and a registered
validation study; that classification prevents “every loader exists” from becoming “schedule every
loader.”

### §3.1 Table B-N — NON-NFLVERSE streams
*(F1/F6 blocker. **Mixed verification state *(V21, restated Q2)*: PlayerProfiler/FantasyCalc/Sleeper counts, the CFBD 1,202 figure, the PFF 149/134,392 split (§3.3: no dedup total is defensible) and its one consumer lane are INDEPENDENTLY verified. **Per-stream R7 states and cadence are now AUTHORED — §6D and §6E — and awaiting independent review, not absent.** Table not checked off: the gate is R4 verification plus the two **OPEN** source clocks — **N1–N8 unmeasurable from held evidence; N19 has a measured bounded normalized observed-change rhythm that is NOT a publish cadence** *(K2)*.**)*

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
| N9 | FantasyCalc | `fc_forward_capture_raw` *(source `fc_native`, snapshots 2026-06-24 → 2026-08-05)* | 20,043 **as of 2026-08-05** | `obs` | **no direct production consumer; source representation for N10** |
| N10 | FantasyCalc | `fc_forward_capture_joinable` | 20,043 **as of 2026-08-05** *(T3 — as-of made explicit rather than the number rewritten: this table is a dated 2026-08-05 measurement at commit `2a42759`. Current value is 20,518 as of 2026-08-06)* | **`alt` — never add to N9** | **scheduled Market Divergence + What-Changed report** (`run_market_divergence_refresh.py`, `what_changed/daily_diff.py`) |
| N11 | **MIXED-SOURCE store** *(V3)* | `fc_snapshots` = DynastyProcess **2,185** (2021-09-08 → 2024-09-08) + FantasyCalc **4,605** (2026-06-12 → 2026-06-24) | 6,790 | `obs` | **optional legacy backtest instrument** (`eval/market_snapshot_store.py`, `run_backtest.py`); not the current overlay source |
| N12 | Sleeper | `league_transaction` | 932 | `obs` | **none** *(V4 — corrected)* |
| N13 | Sleeper | `league_transaction_movement` | 1,692 | `obs` *(different grain)* | **none** *(V4 — corrected)* |
| N14 | Sleeper | `league_season_capture` | 4 | `cap` | — |
| N14b | Sleeper | `app/data/league_transactions/raw/` | **20 JSON files** | `raw-payload`; not added to N12/N13/N14 | **N12's governed raw-before-parse layer (§3.4)** — `write_raw_snapshot` → `normalize` → `upsert`; no separate downstream reader *(Q3: this cell ended in the class token `manual_only`, which both contradicts §§4.4/6C/6E's `automatic_candidate` and puts an automation class in a consumer-state cell — the V2-F2 defect again)* |
| N15 | PFF | manual export payloads | **149** | **`raw-payload count` — NOT `obs`** *(V2)* | **partial — ONE PRECISE LANE** *(V12)*: NCAA `receiving_summary`, scope `REGPO`, seasons 2017–2025 (9 entries in `phase16_wr_manifest.json`, hashes match content-hash filenames) via `scripts/build_college_features.py`. **Not evidence that the other 13 lanes are consumed.** |
| N15b | PFF | internal source rows across 14 league/report lanes | **134,392** | `obs` **(raw payload-row sum; NOT proved double-counted — see §3.3)** | as N15 |
| N15c | PFF | output of a **PROPOSED widest-scope file-selection policy** — **not adopted, not canonical** | **106,867** | **policy OUTPUT, not an observation count** *(§3.3 — the subset premise was tested and FAILED)* | as N15 |
| N16 | CFBD + other sources | `curated/prospects_with_outcomes_v3.csv` | 874 rows | **curated multi-source artifact rows — NOT CFBD source `obs`** | callable builders/evaluators exist; current board says no model consumes the corrected CFBD values |
| N17 | CFBD | `raw/20260802T024342156864Z/` payloads | **1,202** *(manifest `raw_file_count`; dir holds 1,203 JSON = 1,202 payloads + `manifest.json`)* | **`raw-payload count` — NOT `obs` or ledger `cap`** | upstream evidence for N16 |
| **N18** | **Sleeper — league/universe NORMALIZED SNAPSHOT** *(V16 added it; V17 corrected its grain)* | `app/data/league_runtime/runs/<run_id>/snapshot.json`, schema `sleeper_universe_snapshot.v1` | **players 12,209** *(normalized/classified over a UNION of source players + rostered/draft/prospect IDs — **not** raw `get_all_players`)* · **rosters 12** · **users 14** *(list-shaped source components)* · **future_picks 109 — DERIVED**, reconstructed from settings/roster IDs/rounds/traded-pick input · ~~league 5 · draft_state 18 · coverage 10~~ **DICTIONARY-KEY COUNTS, NOT OBSERVATIONS — withdrawn as counts** | **mixed — see cell; NOT uniform `obs`** | **direct scripts:** `build_universe_pvo_batch.py`, `run_what_changed_report.py`, `run_roster_capacity_audit.py`, `run_league_transaction_capture.py`; **API:** `league_pulse.py`, `trade.py`, `trade_market.py`; **bundle derivative:** `build_league_opportunity_map.py` |
| **N18b** | **Sleeper — tracked normalized seed/archive surface** | `app/data/league_snapshots/` | **12 files:** 2 active `*_latest.json` fallback aliases + 10 retained timestamped archives | file/representation count; **not source `obs` and not exact endpoint raw** | only the 2 latest aliases are active fallback inputs for `load_production_league_set`; 10 timestamped files are retained archives |
| **N19** | **Sleeper — league-behavior exact endpoint history** | `app/data/research/league_behavior/raw/2026-07-19/` | **172 endpoint envelopes + 1 fetch log**; 2023–2026; 176 logged calls, zero failures | `raw-payload` by endpoint family; **never sum unlike grains**. **Its 923 transaction records are an OLDER ALTERNATE CAPTURE of a strict subset of N12 — `alt`, NEVER added to N12's 932 (§3.4). Its other endpoint families are NOT in N12.** | **none established; manual one-time, replayable, backup-covered.** **NOT N12's provenance layer — that is `app/data/league_transactions/raw` (§3.4)** |
| **N20** | **CFBD — FBS season schedules (`GET /games`)** | `app/data/sources/cfbd_fbs_schedules/` | **888** 2026 games; one 655,068-byte raw payload / one check / one content vintage / one request; raw SHA `76f0af56c903…`; schema SHA `0a87d5754e30…` | `obs` at provider-game grain; raw/check/vintage/capture identities are retained separately and never added to 888 | **none** — source substrate only; no scheduler, cadence input, feature/model use, or consumer wiring |

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

**~~Still owed on Table B-N: complete per-stream `bound`/`captured`/`exported` states (R7), final
automation/job edges, parallel-route dispositions, and a defensible PFF aggregation rule.~~ STRUCK
*(U1)* — every clause had stopped being true:**

1. **R7 states — authored.** §6D carries all five for every enumerated row. They await **review**, not
   authorship.
2. **Automation / job / freshness edges — authored.** §4.4 (**whole-table CLEAR at its PRIOR pin; its N19 cell has since been edited and awaits the fresh review named in §6F.6 — the current bytes are NOT cleared** *(L2)*), §6C and
   §6E. ~~Only **two source clocks remain OPEN: N1–N8 PlayerProfiler and N19's Sleeper endpoint
   families**~~ **— RETIRED, NOT MERELY CORRECTED *(F3)*. That live premise was FALSE and appending
   the true count beside it left this summary carrying two answers.** The current state follows,
   **characterised 2026-08-07, not closed *(K2)*:** **FIVE source-publish fields OPEN — N1–N8 · N19 · N18 · N12/N13 · N14b** *(branch-(b) ruling, 2026-08-07; this read "both source-publish fields OPEN" while only two were known — self-found while sweeping F2's claim class across the live summary surfaces K2 reconciled)*; **N1–N8 unmeasurable from held evidence** pending an adequate governed series; **N19 has a measured, bounded, NORMALIZED observed-change rhythm that is NOT a publish cadence** and does not cover the N19-only families; **N18 and N12/N13 carried descriptive `continuous` values that were never independently verified, and N14b inherits N12** — **N14 proper stays an evidenced `N/A`**, satisfied rather than open. **⛳ The `N1–N8` field is a GROUP covering FIVE distinct PlayerProfiler upstream report families — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (one family) · N5 medical · N6 player-season — so the true provider-clock count is EIGHT, not four; the MEMBER-FIELD count stays five. N7 is derived from the roster export and inherits N2; N8 is OUR capture ledger and an evidenced `N/A` like N14. Neither is an independent provider family**.
3. **Parallel-route dispositions — authored.** §6B names one canonical route per dataset and
   classifies every other, including two `acquisition defect`s.
4. **PFF aggregation is not a Table B-N gate at all.** §6A places combined-view aggregation
   **outside the A-C blocking path** (David, 2026-08-06) as later semantic-layer work. §3.3 stands on
   its own: the scope-nesting premise was **tested and FAILED**, so **no deduplicated PFF total
   exists** and the raw-grain **134,392** is publishable only when labelled.

**The table is still NOT checked off, and the real gate is:** independent R4 verification of the
authored states, plus the **OPEN source-publish fields** *(this said "those **two** OPEN source clocks" — the count leaked into the surrounding sentence and had to be swept there too)* — **FIVE source-publish fields OPEN — N1–N8 · N19 · N18 · N12/N13 · N14b** *(branch-(b) ruling, 2026-08-07; this read "both source-publish fields OPEN" while only two were known — self-found while sweeping F2's claim class across the live summary surfaces K2 reconciled)*; **N1–N8 unmeasurable from held evidence** pending an adequate governed series; **N19 has a measured, bounded, NORMALIZED observed-change rhythm that is NOT a publish cadence** and does not cover the N19-only families; **N18 and N12/N13 carried descriptive `continuous` values that were never independently verified, and N14b inherits N12** — **N14 proper stays an evidenced `N/A`**, satisfied rather than open. **⛳ The `N1–N8` field is a GROUP covering FIVE distinct PlayerProfiler upstream report families — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (one family) · N5 medical · N6 player-season — so the true provider-clock count is EIGHT, not four; the MEMBER-FIELD count stays five. N7 is derived from the roster export and inherits N2; N8 is OUR capture ledger and an evidenced `N/A` like N14. Neither is an independent provider family** *(K2)*. *(This paragraph recreated T1 outside
the sites swept in round 5 — the fourth generation of one defect: a true statement left standing
after the work it described was done.)*

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

**`exported` for B1–B12 is INDEPENDENTLY VERIFIED *(V11, Codex; AS OF 2026-08-05 — the 2026-08-08 run additionally exported `contracts`, so B13 is now exported too)*:** `app/data/nflverse_usage/export/nflverse_usage.ready.json` names all 12 materialized streams plus the unresolved-identity companion; **every named Parquet exists and recomputes to the marker's SHA-256**, and the 12 counts sum to **1,491,691**. Pinned at run `nflverse-usage-20260805T1334216901700000`, captured `2026-08-05T13:34:21.690170+00:00`. **This verifies export existence and integrity ONLY — not a consumer for B4–B12, and not any refresh cadence.**

**`obs` subtotal across the 12 materialized tables: 1,491,691** *(AS OF 2026-08-05. Superseded 2026-08-08: 13 source tables, 1,588,713 `obs` (+103 ledger rows = 1,588,816 physical), after `contracts` was captured. Preserved as the dated measurement it was.)*. Plus `nflverse_capture` **101
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
| `fc_forward_capture.db` | **20,518 `obs` as of 2026-08-06** + 20,518 `alt` (`joinable` is a second representation — **never add**) *(T3: this cell published a bare `20,043`, violating §6B.3's own as-of rule. Re-measured 2026-08-06 22:23 ET: both tables 20,518, 44 snapshot dates)* |
| `league_transactions.db` | **932 `obs`** transactions + 1,692 `obs` movements *(different grain)* + 4 `cap` |

**STREAMS NOW ROWED — this paragraph previously said they were missing and was left standing after
they were added *(V14, and the SAME §5 defect the register exists for)*.** PlayerProfiler,
PFF, CFBD, FantasyCalc and Sleeper are rowed in **§3.1 Table B-N**; the five direct
feature-refresh loaders are rowed as **B15–B19**; Combine and schedules are B20–B21. Identity/study
datasets are now rowed as **B22–B24** rather than left implicit in adapter functions.
**~~Still genuinely incomplete: final automation classifications, complete R7 states on Table B-N,
and reconciliation of the parallel Sleeper/FantasyCalc consumer routes.~~ STRUCK *(T1)*.** All three
are **authored and awaiting independent review** — classes in §6C/§6E, R7 states in §6D, routes in
§6B. **This paragraph is the second generation of the very defect it was written to record**: it was
added to correct a stale "streams are missing" claim, and then itself went stale when the work it
called incomplete was done. The open gate is **R4 verification plus the OPEN source-publish fields**
*(this said "the two OPEN source clocks (N1–N8, N19)" — same leak, swept here too)* — **FIVE source-publish fields OPEN — N1–N8 · N19 · N18 · N12/N13 · N14b** *(branch-(b) ruling, 2026-08-07; this read "both source-publish fields OPEN" while only two were known — self-found while sweeping F2's claim class across the live summary surfaces K2 reconciled)*; **N1–N8 unmeasurable from held evidence** pending an adequate governed series; **N19 has a measured, bounded, NORMALIZED observed-change rhythm that is NOT a publish cadence** and does not cover the N19-only families; **N18 and N12/N13 carried descriptive `continuous` values that were never independently verified, and N14b inherits N12** — **N14 proper stays an evidenced `N/A`**, satisfied rather than open. **⛳ The `N1–N8` field is a GROUP covering FIVE distinct PlayerProfiler upstream report families — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (one family) · N5 medical · N6 player-season — so the true provider-clock count is EIGHT, not four; the MEMBER-FIELD count stays five. N7 is derived from the roster export and inherits N2; N8 is OUR capture ledger and an evidenced `N/A` like N14. Neither is an independent provider family** *(K2)*. Nothing here is missing.

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
| B21 schedules | `automatic_candidate` | every 5 minutes during the season | **one unscheduled canonical check landed 2026-08-09 07:39 ET**; proposed Tuesday 06:15 ET year-round conditional check, before weekly Tuesday 10:00 Realized Outcome | raw/source provenance and replay now evidenced; `finality_capability=unverified`; no scheduler or intraday cadence without a named consumer |
| B22 forward draft-picks route | `automatic_candidate` | upstream 05:00 UTC Wednesdays Sep–Feb; additionally daily Feb 1–15 and Apr 23–May 5; manual dispatch possible | proposed 12:00 UTC conditional checks on those days; frozen 2025 pin remains `static_pinned` | exact transport/capture + content no-change; PFR settlement/correction clock still unverified |
| B23 governed DynastyProcess `db_playerids` | `automatic_candidate` | upstream Friday 00:23 UTC + manual dispatch; delivery can lag | proposed Friday 08:15 ET blob-SHA check; one Saturday 08:15 ET retry whenever Friday is unchanged or retrieval fails; frozen 2025 pin remains `static_pinned` | source declaration, exact CSV/commit/blob provenance, forward identity retention; no workflow-status inference from unchanged bytes |
| B24 QB-validation players input | `static_pinned` | registered study input | no refresh | study has not run; automation cannot alter manifest inputs |
| N1–N8 PlayerProfiler **— GROUPED ROW; DECOMPOSED 2026-08-07. It spans FIVE upstream report families PLUS a derived table PLUS our own ledger, so no single value in this row can be honest for all members** *(same class as the `N12–N14b` decomposition: a grouped row whose range crosses a provider stream, a derived artifact, and our capture ledger)*. **FAMILIES (each its own upstream clock, all UNVERIFIED): N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history · N6 Data Analysis/player-season.** **N7 `pp_identity_bridge` — DERIVED from the roster export, INHERITS N2, not an independent family.** **N8 `pp_capture` + `pp_pbp_capture` — OUR capture ledger, EVIDENCED `N/A` under the same M4 limb as N14; it is NOT an upstream family and must not be read as one while grouped here.** | `blocked` | **MIXED — this cell has no single honest value; decomposed 2026-08-07 *(F1)*.** **UNVERIFIED, each its own upstream clock: N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history · N6 Data Analysis/player-season.** **N7 `pp_identity_bridge` — INHERITS N2** (derived from the roster export). **N8 `pp_capture` + `pp_pbp_capture` — EVIDENCED `N/A`**, our capture ledger, satisfied not open. *(The decomposition previously sat only in the Catalog IDs cell while this canonical rhythm cell still carried one blanket acquisition description — a canonical field must carry one answer.)* **Acquisition state, which is a different dimension:** landed store came from human exports; ~~a shadow HTTP POST route exists~~ — *(L3)* **both unsanctioned shadow HTTP routes were RETIRED 2026-08-07** (`probe_playerprofiler.py` and `enrich_training_data.py`, the latter carrying a spoofed browser User-Agent). The class stays `blocked` because **no SANCTIONED automated acquisition exists**, and any future automated route still needs sanctioned-access / legal / reliability proof | no automatic job | automated acquisition remains blocked pending sanctioned-access, legal, and reliability proof |
| N9–N10 FantasyCalc forward | `automatic_active_health_unverified` | fetch-time snapshots; no provider publish timestamp | actual daily 09:00 job | add freshness registration, prove health history, and reconcile the request-time cache/live fallback behind one governed route |
| N11 legacy mixed snapshot archive | **`blocked`** *(R1 — **BOTH prior values were wrong.** `manual_only` was wrong: `scripts/snapshot_fantasycalc.py` performs a live FantasyCalc HTTP fetch and appends with no human export. My `static_pinned` was **also** wrong and is withdrawn: three executable writers still default to this path, so the store is **not physically immutable**. The named blocker is `use`/`route` — the legacy collector is **superseded by design** by `run_fc_forward_capture.py`, and scheduling any writer would recreate the parallel market-acquisition defect §6B.1 records)* | frozen/legacy local archive **by declaration only — see the declared-vs-physical gap in §6F** | none | optional backtest only; do not use as current overlay source. **`static_pinned` is the DESIRED state; its pass condition is physical write immunity, which is remediation needing David's word — not a measured fact today** |
| N12–N14b Sleeper transactions | `automatic_candidate` | **DECOMPOSED — this grouped row does NOT share one upstream state** *(branch-(b), 2026-08-07 — **third** edit to a previously CLEARed §4.4 cell; see §6E)*. **N12 / N13 / N14b: `UNVERIFIED`** — the cell read `live league events`, never independently verified, and the label is not evidence for itself; provider-stamped `created_at`/`status_updated_at` make event-driven **plausible, not verified**, and cannot distinguish event-driven from periodic **publication**. **N14: `N/A` — EVIDENCED**, our own capture ledger, a *satisfied* field under M4's second limb. *(F3 — a blanket `UNVERIFIED` across the group silently overwrote N14's evidenced `N/A` and put this canonical table in contradiction with §6E. **The group's own range is the defect: it spans a provider stream and our own ledger.**)* | candidate daily current-season + weekly full-chain reconciliation | cursor/idempotence, call ceiling, marker/freshness, word |
| N18 Sleeper normalized league bundle | `automatic_active_verified` | **UNVERIFIED as a PUBLISH rhythm** *(branch-(b), 2026-08-07 — **fourth** edit to a previously CLEARed §4.4 cell; see §6E)*. Read `endpoint state can change daily`, which is an **observed-change** statement, not a publish cadence — **this column's own title merges the two clocks R3 keeps separate, and that merge is how an unverified value read as settled.** The observed-change side is measured (21 off-season intervals, §6E); the **publish** side is unverified. **The `automatic_active_verified` class is unaffected — it rests on job health, not on the upstream clock** | actual daily 09:20 job | health basis: registered freshness, 21 consecutive successful runs through 2026-08-05, empty error log, current `ok`/ready markers, loaded job last exit 0; exact raw replay and request-time Roster Auditor reconciliation remain separate quality/route gaps |
| N18b two active `*_latest.json` fallback aliases | `manual_only` | production fallback seeds, not source vintages | no automatic refresh job | consumed by `load_production_league_set`; change only through explicit seed maintenance |
| N18b ten retained timestamped archives | `manual_only` | retained normalized history | none | no recurring use or refresh claim |
| N19 one-time exact endpoint history *(upstream clock corrected T2)* | **`blocked`** *(Q4 — changed from `manual_only`; the SECOND edit to a previously CLEARed §4.4 cell, this one requested by the reviewer. Its `fetch_log` records **176 direct Sleeper API calls, zero failures** — an API route, not a human export, so `manual_only` is definitionally wrong. The named blocker is **use**: no recurring use has been decided. **Distinct from N12/N13's `automatic_candidate`**, which has a decided purpose and merely lacks a scheduler)* | **SOURCE-PUBLISH cadence UNVERIFIED** — *(K2: this cell said the upstream change rhythm was **unmeasured**, which is now false. A bounded **normalized observed-change rhythm IS measured** — §6E's N19 row — but an observed-change rhythm is **not** a publish cadence (R3), so this field stays UNVERIFIED. **Editing this cell retires its earlier whole-table §4.4 CLEAR pin and needs fresh review of the changed cell.**)* *(T2: this column held "one-time 2023–2026 replay evidence", which is OUR local pull history, not the source's rhythm — the same R3 defect already accepted for §6E, surviving in the canonical table. **LOCAL CAPTURE EVIDENCE, kept and moved here:** one-time 2023–2026 replay, 176 logged calls, zero failures)* | none | no established consumer; backup-covered; no invented recurring use. **If David names a recurring use, the API route may become `automatic_candidate`** |
| N15/N15b PFF | `manual_only` | human export | none | **manual contract — ACQUISITION UNCHANGED, INTAKE ADDED 2026-08-08.** A human still downloads the subscriber export; no automated acquisition, provider contact, or scheduler exists, and the job column stays `none`. What is new is an **operator-callable intake/indexer**: `scripts/run_pff_intake.py` (`--batch-manifest <sidecar>` for a new drop, `--backfill-existing` to index payloads already held). Provenance is **declared in the sidecar, never inferred** from filenames. **Persistence:** the content-addressed private raw tree is unchanged and was verified byte-identical with untouched mtimes across the backfill; a new **private SQLite METADATA ledger** (`app/data/pff_exports/pff_metadata.db`, metadata only — no paid payload rows) indexes **149 payloads / 307 offering mappings / 7 families / 12 schemas / all 6 governed statuses**, 0 hash mismatches, 0 unresolved, replay idempotent. **Status:** the daily controller now reports this route COMPLETE (`entry_status.ok=True`) and its freshness from the **newest declared SOURCE retrieval time**, not our index time — `2026-08-01T09:23:59.950822-04:00` (exact, not rounded), `manual_due`, ≈6.74d at review. **Layer 1 selects nothing:** no REG/REGPO basis, no duplicate-vintage winner, no status filtering, no cross-family or cross-schema flattening — §3.3's finding that no deduplicated total is defensible is *reinforced*, not retired. **Our local daily target is NOT a provider publication cadence** (R3); the A-C publication-cadence fields remain **OPEN**. YPRR materialization is unchanged and still separate. *(Codex GREEN CLEAR — `docs/agent-ledger/evidence/2026-08-08/pff_layer1_intake_green_clear_codex_v1.md`.)* |
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

**Answer first:** substantial work is required on sources already present in the repo, and one
explicitly named paid source was omitted from prior versions of this canonical answer:
**Footballguys has zero code, zero stored data, and zero acquisition route.** David named it in his
paid-source Layer 1 target and again on 2026-08-08. The highest-priority gaps also include
uncataloged exact bytes, live reads without replayable capture, parallel acquisition routes, and
incomplete materialization from sources we already have.

### Required existing-source reconciliation

| Gap | Kind / minimum honest state |
| :-- | :-- |
| Sleeper league-behavior history — 172 exact endpoint payloads + fetch log, four seasons, backup-covered, previously omitted | **catalog omission** — N19 now rows it; preserve endpoint grains and manual one-time cadence |
| Feature Refresh `player_stats` / `rosters` / `snap_counts` / `pbp` / `participation` | **absent canonical capture** — Option A exact-source capture, independent vintages, atomic bundle, last-good export, then consumer parity |
| NFL Combine used by `build_w2_features.py` | **active-builder live read** — immutable source capture + parser/version provenance before a new vintage reaches the active artifact |
| schedules + Realized Outcome player stats | **schedule capture landed; consumer route still direct and finality unverified** — migrate only behind a separate parity/finality gate before the first prediction-bearing run |
| nflverse draft picks / DynastyProcess `db_playerids` (`ff_playerids`) / nflverse players | **mixed-provider production, identity, freeze, backtest, and validation routes** — reconcile B22's 257-row frozen payload vs 80-row projection, preserve B23's separately pinned 12,457-row and governed 7,952-row identity vintages, and keep B24 uncaptured/static until the registered study runs |
| N18 Sleeper normalized bundle and request-time Roster Auditor | **parallel route + absent exact raw** — exact endpoint capture, explicit projection, consumer migration; in-season injury completeness test |
| FantasyCalc forward store and request-time cache/live fallback | **parallel market acquisition** — one canonical market capture, preserve physical/semantic Engine A/B separation |
| MFL rookie ADP adapter + `SOURCE_REGISTRY` declaration | **source-contract defect** — current undocumented query returns veterans; official rookie-only/no-mock parameters differ, while the machine registry note still calls `ROOKIES=1` documented/rookie-only. Future authorized repair must update adapter + registry declaration/notes + RED controls together before first capture or scheduling |
| PFF NCAA receiving-summary → `yprr_college` | **materialization gap** — source and builder exist, but active coverage is 0/874; reconcile identity/season join before seeking another provider |
| CFBD wrapper vs directly invokable builder | **bypassable canonical route** — the isolated raw+curated wrapper must become the only governed acquisition/promotion path |
| `nflverse_usage.db` | **absent schedule STILL — no scheduler was installed** *(2026-08-08: a runnable CONTROLLER now exists, `scripts/run_layer1_daily_control.py`, and was invoked MANUALLY under David's word; installing a LaunchAgent remains a separate David-gated machine change and has NOT been done)*. **13 bound specs, ALL 13 NOW MATERIALIZED** — `contracts` captured 2026-08-08, so "12 materialized" and "contracts remains bound/uncaptured" are WITHDRAWN as measured-false. Its first capture is a landing gate |
| Nine materialized canonical streams with no production consumer | **absent consumer** — `snap_counts`, `injuries`, PFR ×4, `ff_opportunity`, `ftn_charting`, `depth_charts`; priority evidence, not a semantic prohibition |
| PlayerProfiler 1,520,009 `obs` | **absent production consumer outside ingestion** |
| R1 `nfl_data_py` mislabel + R18 declared snapshot / actual live PBP | **provenance defects** |
| B4–B13 share the canonical nflverse adapter/store but lack matching machine source declarations under R19 | **absent source declarations** — reconcile each family without pretending the NGS declaration covers it |
| DynastyProcess pinned values and `db_playerids` identity snapshots exist physically but have no `SOURCE_REGISTRY` entry | **absent source declaration** — decide whether explicit static-pinned / identity declarations are required; do not silently inherit FantasyCalc's market-source identity or relabel the nflreadpy client as the provider |
| **PFF has NO defensible deduplicated total.** Scope-nesting was tested at row level and **FAILED**: discarding `REG` loses a player outright and changes 942 shared rows (§3.3). 134,392 is a raw payload-row sum; 106,867 is only a proposed policy output | **absent normalization rule — row-level check RAN and FAILED** |
| **Footballguys paid subscription** | **catalog + acquisition omission** — David explicitly named the source; the repo has no adapter, raw export, store, marker, or consumer. Current official surfaces advertise downloadable projections and subscriber rankings/statistics tools. Inventory David's authenticated export surfaces, retain the first source-authentic export, then register each actual report family and its observed change clock. Strategy/article citations are not source ingestion. |
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
| **R13 Sleeper — FOUR physical routes** *(M5: my first draft said four and listed three)* | (1) **N18** daily 09:20 normalized snapshot, consumed; (2) **N12/N13** `league_transactions.db`, **manually run / unscheduled** *(Q3 — this said `manual`, which reads as the `manual_only` class §§4.4/6C/6E no longer assign; the physical fact is an absent scheduler, not a human-fed access path)*, no consumer, with its own governed raw path **N14b** `app/data/league_transactions/raw`; (3) **N19** one-time multi-endpoint raw corpus; (4) **request-time live Roster Auditor read** (R18 path) | Which route is canonical per dataset, and what is each other route? | §3.4 · N14b (20 snapshots; latest-per-season 932 unique, 932/932 shared, zero either-side-only) · `league_transactions.py` L1009→L1022→L1029 | Claude · Codex | Each Sleeper dataset names exactly ONE canonical route; every other route is labelled with a **reason** from: `alt` · `superseded` · `separate corpus` · **`consumer edge`** · **`acquisition defect`** *(M5 — not every non-canonical route is accurately one of the first three)* | route retirement needs David | **MEASURED — awaiting review** |
| **R8 FantasyCalc — parallel acquisition** | Daily `fc_forward_capture.db` (**20,518 `obs` as of 2026-08-06**, `fc_native`, 2026-06-24→2026-08-06) **and** request-time `app/cache/fantasycalc/market_values.json` / live fallback in the trade API + market-overlay service | Which is canonical? A request-time live fallback is an ungoverned acquisition path inside a serving surface | §2.1 R8 · N9/N10/N11 | Claude · Codex | One canonical market capture named; the request-time path classified with a reason. **Engine A/B market separation restated and unbroken** | none for the inventory fact | **MEASURED — awaiting review** *(§6B.1: canonical named, request-time route classed `acquisition defect`)* |
| **R1 `nfl_data_py` — source identity** | **No `nfl_data_py` import exists.** `ingest_2026_draft.py` imports **`nflreadpy`**, writes JSON, labels it `nfl_data_py_verified_nfl_draft`; declared `parquet_snapshot` | Registry names a provider the code does not use | V5 · `rg 'import nfl_data_py'` → nothing | Claude · Codex | **The DEFECT is inventoried, dated and classified as a source-identity defect.** *(Fixing the registry is remediation, not inventory)* | **repair needs David; does not block inventory closure** | **VERIFIED — inventory closed** |
| **R18 — declared vs actual provenance** | Declared `parquet_snapshot`/168h; actual is `live_direct_read`, consumer-triggered by `roster_auditor.py` (2024/2023), no snapshot, no cache. **A second live consumer of B18 `pbp`, not its own stream** | Declaration does not describe the physical route | V7 · V15 · `nflreadpy_qb_adapter.py::fetch_qb_nfl_stats` | Claude · Codex | **Defect inventoried; R18 recorded as a consumer edge on B18, not a stream** | **repair + any consumer migration need David; must NOT widen the five-stream Option A scope** | **VERIFIED — inventory closed** |

### B — STREAMS

| Canonical row/cell | Current measured state | Exact unresolved question / defect | Evidence path or probe | Lane | Binary pass condition | Authority dependency | Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **R7 states — ENUMERATED, not a basket** *(M1)*. Canonical stream rows **B1–B24**; Table B-N rows **N1–N11, N12–N14, N14b, N15, N15b, N15c, N16, N17, N18, N18b, N19** *(**N18b** was omitted from the first enumeration while N14b/N15b/N15c were explicitly listed — the same letter-suffix class, one member missed)* | Counts/grains measured; **B1–B12 `exported` independently verified** at run `nflverse-usage-20260805T1334216901700000` (V11). **~~R7 states otherwise incomplete~~ — STRUCK *(T1)*: §6D now carries all five states for every enumerated row, `MEASURED — awaiting review`. Authored is not incomplete** | Each listed row needs all five states: `bound` · `captured` · `exported` · `consumed` · `decision_supported` | §3.1 · V3 · V11 | Claude · Codex | **Every enumerated row ID above carries all five states, each independently verified or explicitly `N/A` with evidence. `UNVERIFIED` leaves the row OPEN** *(M4)* | none for the inventory fact | **MEASURED — awaiting review** *(§6D: every enumerated row now carries five states; **B20–B24 and N14 measured by the authoring lane 2026-08-06 and NOT independently verified**, so the row cannot read VERIFIED)* |
| **Parallel-route relationships — enumerated** | Three pairs: `snap_counts` **B4 ↔ B17**; Sleeper **N18 ↔ N12/N13 ↔ N19 ↔ R18 request-time**; FantasyCalc **N9 ↔ request-time cache** | Each pair needs a canonical route and a classified counterpart | §3.4 · B4/B17 · V15 | Claude · Codex | Every listed pair names its canonical route and classifies the other with a reason from the M5 vocabulary | route retirement needs David | **MEASURED — awaiting review** *(§6B.1/§6B.2: all three pairs classified; Roster Auditor carries `consumer edge` + `acquisition defect`)* |
| **Final automation classes — the EXACT §4.4 member set** *(M1: "B1–B24" was incomplete)*. §4.4 is the deterministic reference and spans **beyond B-rows**: B1–B24 **plus** N1–N8, N9–N10, N11, N12–N14b, N15/N15b, N16/N17, N18, **N18b (two rows)**, N19, **R4, R6, R7, R9, R10, R11, R12, R14–R17, and A6** | Provisional classes in refresh plan §3; cadence research independently CLEAR at its pin. **§6C/§6E now carry a final class for every §4.4 member** | **~~No canonical stream row carries a FINAL class~~ — STRUCK *(T1)*.** The open question is **independent verification of those classes**, not their absence | refresh plan §1 (seven classes) · cadence artifact + disposition v2 | Claude authors · Gemini facts · Codex reviews | **Every member of the §4.4 set carries exactly one of the seven classes, recorded as reviewed planning judgment — not as a measured fact** *(M4)*. **Membership is resolved from §4.4 itself, not from a copied list here** — a duplicated roster would rot the moment §4.4 gains a row | class ≠ enablement | **MEASURED — awaiting review** *(§6C/§6E reconciled to §4.4 as the single canonical table; **TWO §4.4 cells have now been edited — N11 (§6F.2 R1) and N19 (§6F.3 Q4)** — both disclosed. **T1: this said "one" and went stale in the same round that made the second edit.** §4.4's original CLEAR pin therefore no longer describes §4.4)* |
| **B13 `contracts`** | **✅ CAPTURED AND EXPORTED 2026-08-08 — this cell's prior text "Bound with no table; never executed; zero product-store rows" is WITHDRAWN AS MEASURED-FALSE.** First materialization on the authorized free controller run: **97,022 product-store rows** across **two snapshot vintages** (48,511 each; accumulation across distinct `snapshot_id`s is documented `apply_snapshot` behaviour, not duplication — the two vintages' row content hashes IDENTICALLY, verified independently of the store). Exported: `contracts.parquet` 97,022 × 31 in run `nflverse-usage-20260808T0357281958710000`, named in that run's manifest, with the ready marker advanced to it. **32,620 contracts rows appear in `unresolved_identity.parquet`, all with non-null `snapshot_id`** — the exact condition that killed the 02:28 export before the schema repair | — | §3.1 B13 | Claude · Codex | ~~**Row states `bound / not captured` and names the landing gate.**~~ **RETIRED 2026-08-08 (F2) — a pass condition requiring `not captured` cannot stand beside a captured row.** New pass condition: **the row states `captured / exported` with its measured rows and run id.** Inventory fact is settled | ~~landing needs a separate David word AND one export covering all twelve prior streams plus contracts~~ **DISCHARGED 2026-08-08 (F2): David gave the word (*"run it once codex clears"*), and the run exported all 13 streams in one manifest. Remaining David-gated: scheduler install, retention policy.** | **VERIFIED — inventory closed** |
| **N18 — absent exact raw capture** | Scheduled 09:20, marker-pinned, consumed, 21 runs. **Normalized only** — eight endpoints pass through `build_universe_snapshot`; raw bytes never retained | Fails `01` raw-snapshot-before-parse | V16 · V17 | Claude · Codex | **Row states `normalized snapshot; raw endpoint replay unavailable`.** Inventory fact settled | **exact-raw capture = step 4(d); needs David** | **VERIFIED — inventory closed** |

### C — CADENCE

| Canonical row/cell | Current measured state | Exact unresolved question / defect | Evidence path or probe | Lane | Binary pass condition | Authority dependency | Status |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **Cadence fields — ENUMERATED over the EXACT §4.4 member set** *(M1: "B1–B24" omitted every non-nflverse and source-group row)* | **The nflverse B-row** source-publish cadences are pinned to primary sources, independently CLEAR, and **written onto the canonical rows in §6E** *(T1 — this cell said "not yet written" after §6E wrote them)*. **⚠ SELF-FOUND 2026-08-07 — the scope word "nflverse B-row" is NEW and load-bearing.** This clause read *"Source-publish cadences pinned to primary sources, independently CLEAR"* with **no scope**, which was true of the nflverse pins it described and became **misleading the moment branch (b) opened five non-nflverse fields** — leaving this cell asserting blanket CLEAR pinning in one column while naming five open fields in another. **The independently CLEAR cadence artifact never pinned a Sleeper or PlayerProfiler publication rhythm**, so it never covered those rows. *(Same class as the defects this catalog keeps recording: a claim true when written, left standing unqualified after the fact changed.)* | **Each member of the §4.4 set** — B-rows AND the N/R/A rows listed in the automation-classes row above — needs five fields: source-publish cadence · job cadence · freshness expectation · dependency edge · proposed automation class | cadence artifact (CLEAR at pin) + disposition v2 · Gemini job/marker facts · §4.1 | Claude · Gemini facts · Codex | **Every member of the §4.4 set carries all five fields, each independently verified or explicitly `N/A`/`not scheduled` WITH EVIDENCE. `UNVERIFIED` leaves the row OPEN** *(M4)*. **R3 held: job ≠ freshness ≠ stream cadence** | pinning ≠ scheduling | **OPEN** — **narrowed:** every §4.4 member now carries all five fields except the open source-publish set named below. ~~*(SUPERSEDED 2026-08-07 — this read "except **TWO unmeasured source clocks — N1–N8 PlayerProfiler AND N19's Sleeper endpoint families**", with a Q1 note that the cell had once named only N1–N8. **That two-clock statement is now FALSE and is struck rather than left standing beside its own correction** — appending a correction to a live false premise leaves the cell with two answers, which is F2. The Q1 lesson it carried survives verbatim below.)*~~ **Q1's lesson, retained because it applies to this cell TWICE over: *"a closure matrix that under-reports its own open items is worse than no matrix."*** Under M4 **any one** open field alone keeps this row OPEN. **2026-08-07: the TWO ORIGINAL clocks are CHARACTERISED rather than blank** *(scoped — "both clocks" now under-describes the open set, F2)* — N1–N8 as `UNMEASURABLE from held evidence`, and N19 with a measured off-season observed-change rhythm the reviewer **ruled insufficient** for this field. **On today's sanctioned capability, repeat manual exports are the identified route to a bounded DESCRIPTIVE observed-change series for N1–N8 — NOT a route to M4 closure** *(F4: this read "closable … only by David supplying repeat manual exports", which named an object it could not deliver and excluded a route that is still open)*. **A direct provider, support-channel or subscriber-facing declaration remains a possible route to a cadence declaration and is untried**; automated acquisition stays `blocked pending` proof, not proven impossible (K3). **Neither characterisation moves this cell.** **⛳ 2026-08-07, SECOND EDIT — THIS CELL WAS UNDER-REPORTING ITS OWN OPEN SET AND NOW NAMES FIVE ROWS, NOT TWO.** Codex ruled **branch (b)** (`docs/agent-ledger/evidence/2026-08-07/ac_clock_closure_contract_asymmetry_review_codex_v2.md`, `da04727b…`): **`continuous`/event-driven is admissible ONLY on independent verification — the label is not evidence for itself.** The independently CLEAR cadence artifact pins nflverse clocks and **never pinned a Sleeper publication rhythm**, so **N18 `continuous league state` and N12/N13 `continuous league events` are ALSO source-publish `UNVERIFIED`**, and **N14b inherits N12's clock and cannot be stronger than it**. **N14 proper remains an evidenced `N/A`** — it is our own capture ledger, not a provider source. **OPEN SOURCE-PUBLISH FIELDS: N1–N8 · N19 · N18 · N12/N13 · N14b.** **⛳ DECOMPOSED 2026-08-07 — the MEMBER-FIELD count stays FIVE; the CLOCK count was wrong.** `N1–N8` is a **GROUP**, not one clock: it covers **FIVE distinct PlayerProfiler upstream REPORT FAMILIES — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history · N6 Data Analysis/player-season**. With Sleeper's N19, N18 and N12/N13 that is **EIGHT provider clocks, not four** *(the earlier "four" counted the whole group as one)*. **N7** is **derived from the ROSTER export and inherits N2** — not a sixth family; **N8** `pp_capture`/`pp_pbp_capture` is **OUR capture ledger and an EVIDENCED `N/A` under the same M4 limb as N14** — satisfied, not open, and it must not be counted in a provider bucket. **This decomposition closes nothing; all five member fields remain OPEN.** *(Q1 caught this cell under-reporting once already; it did so again, in the opposite direction — the earlier fix added N19 while leaving three sibling Sleeper rows passing on a value that had never been verified. **The asymmetry was found by asking why one row was held to a standard its siblings were not.**)* **Separately measured 2026-08-07 and it CLOSES NO CELL:** the provider-documentation route — which supplied every B-row clock — was tried on both original clocks for the first time and is **negative for both**, bounded to the searches run: no server-side publication cadence on the inspected public Sleeper API page (its rate-limit and once-daily language is **client-polling guidance**, a different clock under R3), and no PlayerProfiler publish-cadence statement found in public search. **This forecloses the inspected-public-page route ONLY** — a direct provider answer or subscriber-facing material could still supply a declaration. |
| **`nflverse_usage.db` — absent schedule** | **UPDATED 2026-08-08:** 13 bound specs, **ALL 13 MATERIALIZED** *(was "12 materialized" — `contracts` captured 2026-08-08)*, **1,588,713 `obs`** *(was 1,491,691)* **plus capture ledgers `nflverse_capture` 101 + `nflverse_snapshot_capture` 2 = 1,588,816 physical rows** *(F1: I first reported 1,588,816 as `obs`; that is the PHYSICAL total and conflates source observations with our own capture ledgers)*; **STILL no LaunchAgent invokes the canonical capture runner** — a runnable controller now exists and was invoked MANUALLY under David's word; **scheduler installation remains David-gated and was NOT done** | Scoped to this store only — **NOT the layer** (N18 and FantasyCalc are scheduled) | §4.2 · `rg -ln 'run_nflverse_usage_capture' ops/` → nothing | Claude · Codex | **Row states the absent schedule at the correct grain with counter-examples named.** Inventory fact settled | **scheduler = David only** | **VERIFIED — inventory closed** |
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
| **N19** `league_behavior/raw/` | transactions **+** matchups/league/users/rosters/traded-picks/drafts | **SPLIT disposition:** its **923 transaction records are `alt`** of N12 (strict subset, §3.4) · its **other endpoint families are a `separate corpus`** — the **only exact historical endpoint representation** of those families *(F3 — narrowed)* |
| **Roster Auditor request-time reads** — `app/services/roster_auditor.py:9` imports `get_all_players`, `get_leagues`, `get_rosters`, `get_user` from `app.data.sleeper` | league/roster/player universe at serving time | **`consumer edge` + ⛔ `acquisition defect`** *(F2 — both, and the second is the load-bearing one)* — topologically it is a serving-path read of the same upstream datasets and **not a fifth ingestion stream** *(the R1 source ≠ stream ≠ store rule, applied as it was for R18/B18)*; **governance-wise `app.data.sleeper._get` performs live `httpx.AsyncClient.get` calls at request time, so it acquires provider data outside the canonical captures and preserves no exact bytes** — the same defect class as the FantasyCalc request-time route |

**Two Sleeper routes, opposite provenance quality** — N12 satisfies raw-before-parse; N18, the
*scheduled and consumed* one, does not. The catalog previously implied the reverse.

### §6B.3 Standing grain warning — stores that go stale BY THE CLOCK

**A new staleness class, distinct from the §5 register.** §5 records claims invalidated by an *edit*.
**`fc_forward_capture.db` is a DAILY-GROWING store**: the catalog carried **20,043** as though it
were a fixed property; it is **20,518 as of 2026-08-06** and will differ tomorrow. *(Self-found in
the T3 sweep: this sentence originally said "it is 20,518 **today**" — a decaying word, in the very
sentence that states the rule against decaying counts.)*

**Rule adopted:** a count for a growing store is published **only with an as-of date**, or not at all.
`20,518 obs as of 2026-08-06` is a fact; `20,518 obs` is a claim that decays silently.

**Membership — corrected *(F7)*.** The rule is triggered by **an installed job that writes to the
store**, not by the store being interesting. Verified against §6C.1 and `launchctl list`:

| Store | Installed job writing to it? | Rule applies? |
| :-- | :-- | :-- |
| N9/N10 `fc_forward_capture.db` | ✓ daily 09:00, loaded | **✓ as-of date required** |
| N18 `app/data/league_runtime/` | ✓ daily 09:20, loaded | **✓ as-of date required** |
| N12/N13/N14/N14b Sleeper transactions | **✗ no plist, no job** — run manually | **✗** — its counts change only when someone runs it |
| N18b `app/data/league_snapshots/` | **✗ no job** — seed/archive maintenance only | **✗** |

*(My first version named N12/N13 and N18b as having "a live capture job behind it". They do not, and
the same catalog says so. The **rule is sound and stays**; its claimed membership was wrong and the
reason given for it was false.)*

---

## §6C. Step 2 (part) — AUTOMATION CLASSES from Gemini's job telemetry

**Scope:** the automation class for every store Gemini's cadence audit covers. **A class is REVIEWED
PLANNING JUDGMENT, not a measured fact** (§6A / M4) — the *evidence* is Gemini's, the *class* is mine
and is Codex's to challenge. Vocabulary is the refresh plan's seven values.

> **⛳ ONE CANONICAL CLASSIFICATION — §4.4 IS IT *(F1)*.** This section does **not** hold a second
> answer. Where my first version disagreed with §4.4, **§4.4 governs and the cells below were changed
> to match it**; the one place I concluded §4.4 itself was wrong is edited **there**, not contradicted
> here, and is disclosed in §6F. **The rule that produced the defect, stated so it does not recur:**
> **a capture-quality or provenance gap never rewrites an operational-state class.** They are
> different axes and now sit in different columns. A stream can be operationally healthy and
> provenance-poor at the same time — N18 is exactly that, and calling it `health_unverified` for a
> raw-replay gap measured the wrong axis.

**Evidence:** `docs/agent-ledger/evidence/2026-08-06/gemini_layer1_cadence_audit_response.md`
(plist declarations, `launchctl` loaded state, last observed fire/exit, and whether a job refreshes
the store).

| Store / stream | Gemini's measured job facts | Class *(judgment; = §4.4)* | Why | Quality / route gap — **recorded, does NOT change the class** |
| :-- | :-- | :-- | :-- | :-- |
| `nflverse_usage.db` (13 bound specs) | no plist · not loaded · no execution logs · **not refreshed by any job** | **`automatic_candidate`** | Technically automatable; **no governed job exists.** Physical state is manual-only — the class records possibility, not a plan | raw history begins 2026-07-31 only (point-in-time ceiling, §3) |
| Feature Refresh **direct reads** (B15–B19) — the **CURRENT** route | job loaded, daily 09:15, last fire `noop` · **streams read in memory, no raw snapshots written** | **`automatic_active_health_unverified`** *(was `blocked` — corrected, F1)* | The route **is running today** on a loaded daily job. Its health is unproven (`feature_refresh` is registered **weekly** while the job fires **daily**), so `health_unverified`, not `verified` | **no raw capture, no replay**; the **desired Option A canonical-capture route is separately `automatic_candidate`** — that is the TARGET state, and calling the running route `blocked` collapsed current into target |
| `fc_forward_capture.db` | plist daily 09:00 · **loaded** · success 2026-08-05 13:00 UTC · **appends daily rows** · **freshness config: none found** | **`automatic_active_health_unverified`** | Fires and captures, but **no registered freshness policy**, so health cannot be evidenced from a fire alone | parallel request-time acquisition route (§6B.1 `acquisition defect`) |
| `fc_snapshots.db` (legacy) | no plist · no logs · last modified 2026-05-30. **`com.davidleess.dynasty-fc-snapshot` does NOT write it** — the plist targets `run_fc_forward_capture.py` → `fc_forward_capture.db` (verified by reading the plist) | **`blocked`** *(R1 — my `static_pinned` is WITHDRAWN)* | **Dormant is not immutable.** Three runnable writers default to `app/data/fc_snapshots.db`: `scripts/snapshot_fantasycalc.py:31,91-107` *(live FantasyCalc HTTP + append)* · `scripts/ingest_market_archive.py:161` *(manual CSV)* · `scripts/backfill_market_archive.py:38,88-105`. So it is neither `static_pinned` nor `manual_only`; the blocker is that the route is **superseded** and scheduling it would recreate a parallel market acquisition path | mixed-source store (DynastyProcess + FantasyCalc); never a current overlay source. **⛔ DECLARED-vs-PHYSICAL GAP:** the committed plist comment calls this store *"a frozen, read-only archive"* while three scripts can write it today |
| `league_transactions.db` (N12–N14b) | no plist · not loaded · no logs · **run manually only** | **`automatic_candidate`** *(was `manual_only` — corrected, F1)* | Confirms V4 — the 09:20 job never touches it. But `manual_only` means **the access path needs a human**; this is an ordinary API capture that simply **has no scheduler**, which is the definition of `automatic_candidate` | cursor/idempotence, call ceiling, marker and freshness all undesigned |
| `app/data/league_runtime/` (N18) | plist daily 09:20 · **loaded** · freshness config daily 09:20 · success 2026-08-05 13:20 UTC | **`automatic_active_verified`** *(was `automatic_active_health_unverified` — corrected, F1)* | Operational health is **independently evidenced**: registered freshness, current `ok` status marker, current ready pointer, 22 successful runs, empty error log, loaded job last exit 0 | **normalized-only; no raw endpoint replay** (V17) and a parallel request-time Roster Auditor route (§6B.2). **Both are real and neither is an operational-health fact** |
| PlayerProfiler stores (N1–N8) | no plist · no logs · **manual file copy only** | **`blocked`** *(was `manual_only` — corrected, F1)* | ~~A shadow HTTP route exists, so this is not a source whose only contract is a human export~~ — *(L3)* **both unsanctioned shadow HTTP routes were RETIRED 2026-08-07** (`probe_playerprofiler.py` and `enrich_training_data.py`, the latter carrying a spoofed browser User-Agent). The class stays `blocked` because **no SANCTIONED automated acquisition exists**, and any future automated route still needs sanctioned-access / legal / reliability proof. **The F1 distinction from PFF survives on different ground:** PFF's contract is a human export with no automated route to sanction; PlayerProfiler's automated route is a governance question that remains open, not a settled absence | landed store came from human exports; no production consumer outside ingestion |
| PFF manual export inventory (N15/N15b) | no plist · no logs · manual reconciliation | **`manual_only`** | Human export **is** the current contract — there is no sanctioned automated route to be blocked from | `yprr_college` materialization gap (0/874); no defensible deduplicated total (§3.3) |
| CFBD foundation promoted store (N16/N17) | no plist · no logs · manual script | **`blocked`** | Paid source; needs David's cost/run ruling before any clock (refresh plan §7.2) | the isolated wrapper is bypassable by direct builder execution |
| `nflreadpy_qb_context` (R18) | **⛔ CORRECTED — there is NO roster-capacity job.** Verified: `launchctl list` shows **exactly 8** dynasty jobs and none is `roster-capacity`; `~/Library/LaunchAgents` and `ops/launchd/` each hold the **same 8** plists. **Reads live PBP in memory, no cache/snapshot** | **`blocked`** *(class unchanged)* | **NOT scheduled at all** — an uncaptured live read reached only through a consumer. *(This cell first said "roster-capacity plist weekly Tue 10:00 · loaded", taken from Gemini's cadence audit and NOT verified by me. Gemini's two reports contradict each other and the earlier one is wrong. The class survives; the evidence under it did not.)* | **not a stream** — a consumer edge on B18 (§6A). Declared `parquet_snapshot`/168h against an actual live read |
| QB validation raw path (R20) | no plist · no logs · **study has not run** | **`static_pinned`** | Pinned pre-registered inputs; **automation must be physically unable to overwrite them.** H2 QB rushing remains UNDER TEST with no result | — |

**Two rows are outside §4.4's member set** and are classified here as additions, not as competing
answers: **R18** (a consumer edge, not a stream) and **R20** (the study input path; §4.4 carries the
same substance as B24). Everything else above is now byte-for-byte the §4.4 class.

**What `verified` still has to earn.** `fc_forward_capture` fires successfully and is still
`health_unverified`, because `02`'s own distinction is that **a fire is not health evidence** — it
has no registered freshness policy at all. N18 clears that bar on evidence, not on a green exit code.
**Neither statement says anything about capture quality**, and that separation is the F1 repair.

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

**STATUS OF STEP 2, restated against what actually exists *(F6 — this paragraph previously said the
R7 states were still open and a fresh Gemini request was "in flight", while §§6D/6E below already
carried the work. Two live sections describing the same work in opposite states is a defect, not a
sequencing note)*:** Gemini's follow-up **arrived and is verified above** (§6C.1 is its product — the
eight registrations, the two with no job, and the corrected `roster_capacity` contradiction).
R7 states are in **§6D**; automation classes for every §4.4 member are in **§6E**. What remains open
in step 2 is named in §6D's closing paragraph and nowhere else.

---

## §6D. Step 2 — R7 STATES for every enumerated stream *(title corrected: it was "(complete)" while its own body said open — F6)*

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
| B14 | `ff_rankings` | ✗ | ✗ | ✗ | ✗ *(its `blocked_for_use` landing disposition is a SEPARATE column and is carried in Table B §3 — repeating it in a state cell here reproduced the exact V2-F2 defect §3 warns about; found by my own sweep, not raised in the review)* |

**Nine materialized, exported, consumerless streams** — B4–B12. Priority evidence, not a prohibition.

### Direct provider reads (B15–B19) — the inverse shape

| Row | Stream | bound | captured | exported | consumed |
| :-- | :-- | :-: | :-: | :-: | :-- |
| B15–B19 | `player_stats` · `rosters` · `snap_counts` · `pbp` · `participation` | **✗** | **✗** | **✗** | **✓ 09:15 Feature Refresh, live** |

**Consumed but never captured** — the exact inverse of B4–B12, and the object of David's A/B ruling.
**B17 duplicates B4.** *(CH1 now prevents one absent stream capping the rest; that changes failure
behaviour, not capture state.)*

### B20–B24 — MEASURED 2026-08-06, per cell *(F4 — "all five UNVERIFIED" was too broad and is withdrawn)*

**Why the old cell was wrong on two counts.** (1) `decision_supported` was never unknown — it is ✗ by
the governance invariant stated at the head of this section, for every Layer 1 row. (2) Table B
already carried Codex-measured states for these rows; erasing them into one unknown **destroyed
measurement rather than recording its absence.** The repair is per-cell probing, which is what the
row demanded and what has now been run.

**Probes run by Claude, 2026-08-06 — each rerunnable:**
`bound` = a `StreamSpec` in `src/dynasty_genius/nflverse_usage.py` (measured: **13 specs, none of
these five**) · `captured` = a table in `app/data/nflverse_usage.db` (**12 tables, none of these
five**) plus a search for any other physical store · `exported` = membership of `files` in
`app/data/nflverse_usage/export/nflverse_usage.ready.json` (**12 entries, none of these five**) ·
`consumed` = `rg` for each loader symbol across `src/ scripts/ app/ eval/`.

| Row | bound | captured | exported | consumed | dec_sup |
| :-- | :-: | :-- | :-: | :-- | :-: |
| B20 `combine` | ✗ | **✗ no exact/raw/canonical SOURCE capture or replay store** *(R4 — the prior cell said "no store of any kind", which is false: `scripts/build_w2_features.py:520-524` live-loads Combine, `:597-605` merges the derived values into each row, and `:637-647` rewrites `V3_CSV`. **Derived Combine values ARE persisted in the active training artifact**; what is absent is any capture of the source bytes)* | ✗ | **✓** `scripts/build_w2_features.py:523` `nflreadpy.load_combine(COMBINE_YEARS)` — a **live read that mutates the active training artifact** | ✗ |
| B21 `schedules` | ✗ | **✓ canonical content-addressed store** — `app/data/sources/nflverse_schedules`: 517,546 raw bytes, SHA `eeea1f47644c…`, 7,548 × 46, one check/one vintage, 272 season-2026 rows, ready marker and idempotent replay; `finality_capability=unverified` | ✗ | **✓** `scripts/run_realized_outcome_scoring.py:342` (loaded weekly job; current runs gate before access on absent predictions) · declared in `capture/outcome_forward_capture_store.py:22` as the finality source; this consumer is not yet migrated to the canonical store | ✗ |
| B22 `draft_picks` | ✗ | **✓ as a tracked frozen pin, NOT as a stream store** — `resources/prospect_fixtures/_frozen_2025/nflverse_draft_picks_2025_pin.json`, **257 rows**, `release_tag: live_nflverse_release`. **Exact HTTP bytes absent** | ✗ | **✓** `scripts/ingest_2026_draft.py:28` · `eval/backtest_mock_draft.py:219` · `scripts/assemble_te_identity_cohort.py:51` · `scripts/freeze_2025_prospect_sources.py` | ✗ |
| B23 `ff_playerids` | ✗ | **✓ TWO separate vintages, never added** — frozen pin `resources/prospect_fixtures/_frozen_2025/ff_playerids_pin.json` **12,457 rows** · governed run `app/data/identity/_runs/ff_playerids_20260516.json` **7,952 entries** | ✗ | **✓** production identity infrastructure — `league_transactions.py:220` via `build_universe_pvo_batch._load_ff_playerids` · `eval/backtest_harness.py:205` · `scripts/run_identity_audit.py` · `scripts/assemble_te_identity_cohort.py` | ✗ |
| B24 `players` | ✗ | ✗ | ✗ | **✓ one site only** — `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py:454` `nfl.load_players()`, the registered QB-validation loader. **The study has not run; H2 QB rushing remains UNDER TEST with no result** | ✗ |

**Status of these five rows: `MEASURED — awaiting review`, not `VERIFIED`.** Under R4 the measuring
lane is not the verifying lane. The probes above are Claude's; **they are stated so Codex can rerun
each one**, and the rows stay open until it does. **Two findings the probes produced that were not in
the prior text:** B22 and B23 are `captured` — the earlier blanket ✗ was wrong — and both frozen pins
live under **`resources/prospect_fixtures/`**, a tracked repo fixture path, not under `app/data/`.

### Non-nflverse (Table B-N)

| Rows | bound | captured | exported | consumed |
| :-- | :-: | :-: | :-: | :-- |
| N1–N8 PlayerProfiler (1,520,009 `obs` + 3,290 `idn` + 63 `cap`) | n/a — not StreamSpec-bound | ✓ | ✗ | **✗** none outside ingestion |
| N9/N10 FantasyCalc (20,518 `obs` **as of 2026-08-06**; joinable is `alt`) | n/a | ✓ | ✗ | **✓ — but NOT the market overlay.** *(Self-found while probing Q5, and Codex did not raise it: the same wrong label sat on this row too.)* Measured consumers are the **scheduled Market Divergence + What-Changed reports** — `scripts/run_market_divergence_refresh.py`, `what_changed/daily_diff.py`. **`market_overlay_service.py:192-193` reads `fetch_with_cache()`**, the request-time adapter — so the overlay surface is served by the §6B.1 `acquisition defect` route and **not** by this governed store |
| N11 `fc_snapshots` 6,790 (mixed-source) | n/a | ✓ | ✗ | **✓ optional legacy backtest / market-comparison harness — NOT the market overlay** *(Q5)*. Measured: `scripts/run_backtest.py:35,178` via `--market-store` into the walk-forward driver, and `eval/backtest_harness.py:50,500`. **No app or service consumes `MarketSnapshotStore`**; `ingest_market_archive.py` is a WRITER, not a consumer |
| N12/N13 + N14b transactions (932 `obs`; raw 20 snapshots) | n/a | ✓ **with raw-before-parse** | ✗ | **✗** *(V4)* |
| **N14 `league_season_capture`** *(F4 — omitted from this table while it sat in the enumerated set)* | n/a | ✓ **4 `cap` rows** — measured 2026-08-06 in `app/data/league_transactions.db`; columns `league_id, season, status, legs_attempted, legs_with_activity, legs_empty, transactions_total, movements_total, coverage_json, failure_reason, content_hash, ingested_at` | ✗ | **✗** — an **ingestion capture ledger**, written by N12's own capture run. Not a dataset with a downstream reader, and **never added to N12/N13** (different grain) |
| N15/N15b/N15c PFF (149 payloads; 134,392 raw-grain) | n/a | ✓ | ✗ | **partial** — ONE lane only *(V12)* |
| N16/N17 CFBD (874 curated; 1,202 raw) | n/a | ✓ | ✗ | **⚠ NOT "✓ Engine A" — corrected *(F4)*.** The curated CSV **is Engine A's declared training-input path**, and the promoted corrected values are physically live in it (2026-08-04). What is **not** proved is that any model consumes them: no retrain or deployment followed promotion. Named callable consumers: `run_phase20_bakeoff.py` *(non-promoting evaluator)*, `build_w2_features.py` / `build_w2b_cfbd.py` / `build_head_b_targets.py` *(builders that mutate the artifact)*. **Bakeoff and model/feature use remain DEFERRED (live board).** State: **`consumed by callable builders/evaluators; production-model consumption UNPROVED`** |
| N18 Sleeper snapshot | n/a | ✓ **normalized only, no raw replay** | ✓ marker-pinned | ✓ league derivation |
| N18b seed/archive aliases | n/a | ✓ | ✗ | ✓ production fallback |
| N19 league-behavior raw | n/a | ✓ | ✗ | ✗ |
| N20 CFBD FBS schedules (888 `obs`; one raw/check/vintage/request) | n/a | ✓ **exact raw bytes + content-addressed vintage + marker + replay** | ✗ | ✗ |

**STEP 2 IS NOT COMPLETE.** *(The prior line read "COMPLETE except B20–B24" — F4. It was false on its
own terms before the B20–B24 work even started, because two of its rows were wrong and one was
missing.)* Every enumerated row now carries all five states. **What holds step 2 open:**

1. **B20–B24 are `MEASURED — awaiting review`**, not verified. R4 requires the verifying lane to be
   the non-measuring one.
2. **N16/N17's consumer state changed** from an asserted `✓ Engine A` to `production-model
   consumption UNPROVED`. That correction has not been independently checked.
3. **N14 is newly rowed** and its `cap` grain has not been reviewed.

**Nothing here moves a §1 checkbox.**

---

## §6E. Step 3 — CADENCE, five separate fields per stream

**R3 held throughout: source-publish cadence ≠ job cadence ≠ freshness expectation.** Three clocks,
never merged. **Sources:** source-publish from Codex's cadence artifact (independently CLEAR at its
pin); job cadence and freshness from Gemini's telemetry, **verified by me** in §6C.1; dependency
edges and proposed class are the binding lanes'.

### Canonical nflverse streams

| Stream | SOURCE-publish cadence | JOB cadence | FRESHNESS expectation | Dependency edge | Proposed class |
| :-- | :-- | :-- | :-- | :-- | :-- |
| B1–B3 NGS | nightly ~03:00–05:00 ET in season | **none** — no job invokes the canonical capture | **none registered** | consumed by 09:15 job **via last-good export** | `automatic_candidate` |
| B4 snap_counts | provider checks 00/06/12/18 UTC in season | **none** | none registered | canonical export **unconsumed**; B17 duplicates it live | `automatic_candidate` |
| B5 injuries | **no established live feed** — 2025 archive appeared only 2026-03-18, post-postseason | **none** | none registered | none | `automatic_candidate` *(was `blocked` — F1)*. **The archive is schedulable; what is missing is current-season COVERAGE, which is a fitness question, not a scheduling blocker.** Sleeper completeness test first |
| B6–B9 PFR advanced | daily 07:00 UTC in season | **none** | none registered | none | `automatic_candidate` |
| B10 ff_opportunity | after TNF / Sunday / SNF / MNF windows, Jan–Feb + Sep–Dec | **none** | none registered | none | `automatic_candidate` |
| B11 ftn_charting | provider checks 4×/day; charting may lag a game **up to 48h** | **none** | none registered | none | `automatic_candidate` — freshness ceiling **must** allow the 48h lag |
| B12 depth_charts | daily 07:00 UTC **year-round** | **none** | none registered | none | **`blocked`** *(was `automatic_candidate` — F1)*. **The only stream producing a new vintage daily, year-round**, and the current JSON representation is **56.29× the source Parquet** — a named STORAGE blocker, which is `blocked` by definition. Needs an exact compressed representation + retention ceiling |
| B13 contracts | `rotc` workflow daily 07:00 UTC | **none — never run** | none registered | first capture **IS** the product-store landing | **`blocked`** *(was `automatic_candidate, landing-gated` — F1)*. A named **authority** blocker: first capture is a separately authorized landing requiring one export covering all twelve prior streams plus contracts |
| B14 ff_rankings | n/a | none | none | none | `blocked` |

### Direct provider reads (B15–B19)

**Class column corrected throughout *(F1)*.** These routes are **running today**; `blocked` described
the state Option A would replace them with, not the state they are in. **Current** and **target** are
now separate columns, because collapsing them is exactly what the review caught.

| Stream | SOURCE-publish | JOB cadence | FRESHNESS | Dependency edge | CURRENT class | TARGET (Option A) class |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| B15 player_stats | nightly after game days + **Thursday** stat-correction pass | **daily 09:15** *(the JOB, not the stream)* | registered **weekly**, `dormant_ok: true` — **MISMATCH with a daily fire** | read live inside derivation | `automatic_active_health_unverified` | `automatic_candidate` — canonical capture; all-consumer parity |
| B16 rosters | daily 07:00 UTC | daily 09:15 | as above | as above | `automatic_active_health_unverified` | `automatic_candidate` — canonical capture; all-consumer parity |
| B17 snap_counts | 00/06/12/18 UTC | daily 09:15 | as above | **duplicates B4** | `automatic_active_health_unverified` | **retire** — B4 is canonical; retire only after the parity/equivalence control |
| B18 pbp | nightly + game windows; **Thursday cleanest** after corrections | daily 09:15 | as above | **two consumers** — Feature Refresh + Roster Auditor (R18) | `automatic_active_health_unverified` | `automatic_candidate`; Roster Auditor migration separately gated |
| B19 participation | **2023+ postseason ONLY; no in-season updates** | daily 09:15 | as above | as above | `automatic_active_health_unverified` | `automatic_candidate` **on its own weekly-Feb–Mar / monthly clock** — **a daily read cannot make annual data fresher, and its absence must not cap the other four** |

**Why `health_unverified` and not `verified`:** the job fires daily while `feature_refresh` is
registered **weekly** with `dormant_ok: true`, so no registered policy evidences the health of a daily
route. **Why not `blocked`:** nothing prevents these routes from running — they ran at 09:15 today.

### B20–B24 — cadence *(F5: source-publish cadence must not be blank because R7 states await review — R3 keeps the clocks separate)*

Source-publish clocks below are from the **independently CLEAR** remaining-candidate cadence artifact
(`layer1_remaining_candidate_cadence_codex_v1.md`) and §4.4. **Every local check is a proposal; no job
exists.**

| Stream | SOURCE-publish | JOB cadence | FRESHNESS | Dependency edge | Proposed class |
| :-- | :-- | :-- | :-- | :-- | :-- |
| B20 combine | upstream workflow 12:00/17:00 UTC **March 3–12** + manual dispatch | **none** | none registered | **`build_w2_features.py` mutates the active training artifact from this live read** | `automatic_candidate` — proposed ONE conditional check 20:00 UTC March 3–13 |
| B21 schedules | **every 5 minutes during the season** | **none; one manual canonical check landed 2026-08-09 07:39 ET** | ready marker records the first check; no recurring freshness policy registered | loaded Tuesday 10:00 Realized Outcome consumer, not yet migrated | `automatic_candidate` — proposed Tuesday 06:15 ET year-round, ahead of that consumer. **No intraday cadence without a named consumer** |
| B22 draft_picks | upstream 05:00 UTC Wednesdays Sep–Feb; additionally daily Feb 1–15 and Apr 23–May 5 | **none** | none registered | frozen 2025 pin feeds study/backtest paths | `automatic_candidate` for the forward route — proposed 12:00 UTC on those days. **The frozen pin stays `static_pinned`** |
| B23 `ff_playerids` | upstream Friday 00:23 UTC + manual dispatch; delivery can lag | **none** | none registered | **production identity infrastructure** | `automatic_candidate` for the forward route — proposed Friday 08:15 ET blob-SHA check + one Saturday retry. **Both existing vintages stay `static_pinned`** |
| B24 players | registered study input | **none** | none registered | registered QB-validation loader only | `static_pinned` — **automation must be physically unable to alter a pre-registered manifest input** |

### Non-nflverse and source groups

**Membership is now the EXACT §4.4 member set *(F5)*.** The prior table omitted N14, N14b, N18b's two
rows, N19 and N15b. Each omitted row is added below with the same five fields, or an explicit
evidence-backed `n/a`.

| Stream / group | SOURCE-publish | JOB cadence | FRESHNESS | Dependency edge | Proposed class |
| :-- | :-- | :-- | :-- | :-- | :-- |
| N9/N10 FantasyCalc | continuous provider; **no provider publish timestamp** | **daily 09:00, loaded** | **none registered** | N10 `alt` feeds Market Divergence + What-Changed | `automatic_active_health_unverified` |
| N18 Sleeper snapshot | **UNVERIFIED** *(2026-08-07, branch-(b) ruling)*. **This cell read `continuous league state` and that value was never independently verified** — the CLEAR cadence artifact pins nflverse clocks and pinned no Sleeper publication rhythm. **The label is not evidence for itself (M4).** Sharpened by the row's own shape: N18 is a **heterogeneous normalized bundle** — league, rosters, users, traded picks, drafts, global player map — so **one blanket clock hides endpoint-specific clocks**, and the player-map endpoint separately carries only **client-polling** guidance (once-daily), which under R3 is not a publish cadence. **The daily job cadence and registered freshness are unaffected and remain verified; only the SOURCE-publish field is open.** | **daily 09:20, loaded** | **daily, registered** | consumed by 7+ scripts/APIs | **`automatic_active_verified`** *(was `health_unverified` — F1; the raw-replay gap is a QUALITY defect and is carried in §6C's quality column, not in this class)* |
| **N18b — 2 active `*_latest.json` aliases** *(F5 — added)* | **n/a** — production fallback seeds, not a source vintage | **none** | none registered | inputs to `load_production_league_set` | `manual_only` — change only by explicit seed maintenance |
| **N18b — 10 retained timestamped archives** *(F5 — added)* | **n/a** — retained normalized history | **none** | none registered | none | `manual_only` — no recurring use or refresh claim |
| N12/N13 transactions | **UNVERIFIED** *(2026-08-07, branch-(b) ruling)*. **This cell read `continuous league events`, never independently verified.** Event-driven semantics are **plausible and likely the cheapest of the three to evidence** — the records carry provider-stamped `created_at` / `status_updated_at` (`league_transaction`, 932 rows, both columns non-null) — but **plausibility does not satisfy M4**. **And those timestamps CANNOT close this field:** provider *event* time cannot distinguish event-driven from periodic **publication** (a periodic publisher can expose records carrying the same irregular original-event times), and event→visibility latency is unmeasured. They are **bounded record-semantics evidence, not a closure path**. | **none** | none registered | none *(V4)* | **`automatic_candidate`** *(was `manual_only` — F1; no human export is involved, only an absent scheduler)* |
| **N14 `league_season_capture`** *(F5 — added)* | **`N/A` — EVIDENCED, and expressly CONFIRMED under the 2026-08-07 branch-(b) ruling.** A capture ledger **we** write, not a provider source, so it has no source-publish clock to verify. **It does NOT join the four Sleeper rows opened by that ruling** — an evidenced `N/A` is a satisfied field under M4, not an unverified one, and the distinction is the whole point of M4's second limb. | **none** *(written by N12's manual capture run)* | none registered | internal to the N12 capture | `automatic_candidate` — inherits N12's clock exactly; **never its own** |
| **N14b `league_transactions/raw/`** *(F5 — added)* | **UNVERIFIED — INHERITED** *(2026-08-07, branch-(b) ruling)*. Same upstream as N12, therefore **it inherits N12's clock and cannot be stronger than it**. It read as settled only because the row it inherits from did. | **none** | none registered | **N12's governed raw-before-parse layer (§3.4)** | `automatic_candidate` — inherits N12's clock |
| **N19 league-behavior raw** *(F5 · R3 · characterised 2026-08-07)* | **UNVERIFIED — and it STAYS unverified.** **What IS now measured**, from `docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_measurement_claude_v1.md` (CLEAR at `1e33ba1d…`): over **21 consecutive off-season intervals** of N18's daily snapshots of the same upstream, `players` changed **21/21**, `rosters` **9/21**, `draft_state` **6/21**, `users` **0/21**. **`league` appears 21/21 but the ONLY key that ever changes is `daily_waivers_last_ran`** — a Sleeper counter; league configuration did not change once. **THIS IS AN OBSERVED-CHANGE RHYTHM, NOT A SOURCE-PUBLISH CADENCE, and the reviewer ruled it does NOT satisfy §6A** (R3: different dimensions). It measures the **normalized** snapshot, so the evidence is asymmetric — a change proves an input changed; no-change proves **nothing** about raw endpoint stability. Window is **entirely off-season**. **N19-only families (matchups, per-endpoint drafts/traded-picks) have NO series at all.** *(This cell read `n/a — one-time 2023–2026 exact endpoint replay`. That describes OUR capture history, not the SOURCE's rhythm — the R3 confusion the catalog exists to prevent. These families are **expected**, by record semantics, to reflect live league events)*. **⚠ TWO CORRECTIONS HERE, F5 — AND THE SECOND IS A DEFECT I INTRODUCED WHILE FIXING THE FIRST.** (i) This clause read *"The families demonstrably change on live league events"*. **"Demonstrably" is unearned at the publication dimension** — this row states in the same breath that **the N19-only families (matchups, per-endpoint drafts, traded picks) have NO series at all**, so nothing has been demonstrated for them; what remains is an expectation from **record semantics, which earns no cadence fact**. (ii) The clause originally leaned on N18's cell as a settled comparison; my first repair kept the lean and merely annotated it as stale — **the stale cross-reference surviving in a new form**, which is exactly what the reviewer warned against. **Both the claim and the lean are removed, not annotated.** *(Class: L3 — a change whose consequence lands in a different cell — with a second pass showing that annotating a bad reference is not the same as retiring it.)* | **none** | none registered | no established consumer; backup-covered | **`blocked`** *(Q4 — was `manual_only`)* — a named **use** blocker: no recurring use decided. **Manually initiating the first HTTP pull does not make an API access path `manual_only`.** Recording an upstream rhythm invents **no** local job, cadence or use. **⛳ 2026-08-07 — THE PROVIDER-DOCUMENTATION ROUTE WAS TRIED AND IS NEGATIVE, and it CLOSES NOTHING.** The inspected public Sleeper API page carries **no server-side publication cadence for any endpoint family**; what it carries is **client-polling guidance** (`under 1000 API calls per minute`; players `once per day at most`), which under **R3 is a different clock** and must never be written into this column. **Bounded:** this forecloses the inspected-public-page route as of 2026-08-07 — **a direct provider answer or subscriber-facing material could still supply a declaration**, and neither has been tried |
| N15 PFF | manual export | none | none registered | one lane consumed (`build_college_features.py`) | `manual_only` |
| **N15b PFF internal source rows** *(F5 — added)* | **n/a** — a decomposition of N15's payloads, not a separate acquisition | **none** | none registered | as N15 | `manual_only` — **inherits N15 exactly; it has no clock of its own** |
| N16/N17 CFBD | paid HTTP; 720h registry freshness | none | 720h registered | callable builders/evaluators; production-model consumption unproved (§6D) | `blocked` — needs David's cost/run ruling |
| N1–N8 PlayerProfiler | **DECOMPOSED — READ THIS FIRST *(F1)*; this row has no single value.** **UNVERIFIED, five upstream report families each with its own clock: N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history · N6 Data Analysis/player-season.** **N7 INHERITS N2** — derived from the roster export, not an independent family. **N8 `pp_capture` + `pp_pbp_capture` — EVIDENCED `N/A`** under the same M4 limb as N14, satisfied rather than open. *(This cell opened with a blanket UNVERIFIED and carved N8 out only later; the canonical field now leads with the decomposed states.)* **The five upstream-family clocks are UNVERIFIED and now known to be UNMEASURABLE from held evidence — this applies to the five FAMILIES, not to N7 or N8** *(characterised 2026-08-07; `docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_measurement_claude_v1.md` (CLEAR at `1e33ba1d…`))*. The store holds **one CONTENT vintage per canonical stream** across **≥7 evidenced executions**; the only repeat observations are **three pairs spaced 33s / 100s / 396s** — **present but non-diagnostic**, too few and too narrowly spaced to infer a recurring rhythm. **Held observations are INSUFFICIENT; an adequate governed observation series must be CREATED.** That requires **David supplying repeat manual subscriber exports** — the governed access path is his own export button, and as of 2026-08-07 **no automated retrieval path exists in the repo at all** (both legacy scripted routes retired). | none | none registered | none outside ingestion | **`blocked`** *(was `manual_only` — F1; automation is blocked pending sanctioned-access/legal/reliability proof, which is a stronger statement than "a human exports it")*. **⛳ THIS ROW IS A GROUP AND IS DECOMPOSED (2026-08-07):** its UNVERIFIED source-publish state covers **FIVE distinct upstream report families — N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history · N6 Data Analysis/player-season** — each with its own clock. **N7 is DERIVED from the roster export and INHERITS N2** (`playerprofiler_roster.py:594` writes it under `stream=ROSTER_STREAM`; `playerprofiler_gamelog.py:365` and `playerprofiler_pbp.py:310` only `SELECT` from it and refuse when empty), **not a sixth family**. **N8 `pp_capture` + `pp_pbp_capture` is OUR capture ledger — an EVIDENCED `N/A` under the same M4 limb as N14**, satisfied rather than open. **A single-family answer cannot close this grouped field. Explicit family-level coverage for all five families is required, however many replies or documents supply it; one authoritative reply or document may cover several or all five.** *(F2 repair: an earlier phrasing read "five families need five answers", which over-specified the mechanism when the contract is the coverage.)*. **⛳ 2026-08-07 — PROVIDER-DOCUMENTATION ROUTE TRIED, NEGATIVE, CLOSES NOTHING.** No PlayerProfiler publish-cadence statement was found in public search — **bounded to that search's width**, so a subscriber help centre or a direct provider answer could still carry one. **This STRENGTHENS rather than replaces the existing state:** the cheaper route is now positively tried instead of merely untried. **STATED WITH ITS OBJECT, because the object is what makes it true or false (F4):** under current sanctioned capability, **repeat manual exports are the identified route to a bounded DESCRIPTIVE observed-change series — NOT a route to M4 closure**, since manual retrieval yields observed-change evidence and never source-publish cadence. **A direct provider answer, support channel, or subscriber-facing material remains a possible route to a DECLARATION, and is untried.** *(This read "remains the only *identified* route — which is itself not a closure path", which asserted "only" and then denied its object in the same breath, and wrote off a declaration route this very row shows is still open — the Q3 framing returning in new clothing.)* **A CLEARed pilot protocol now exists** (`playerprofiler_player_season_pilot_protocol_claude_v5.md`, `18cca65c…`; CLEAR `3a77ae9d…`) and is **NOT RUNNABLE** — it depends on a shared preparation+digest extraction that does not exist and is unauthorized |
| **N11 `fc_snapshots`** *(R1 — split out of the `static_pinned` group)* | **n/a** — a dormant legacy archive, not a live provider route | **none** *(the `fc-snapshot` plist writes `fc_forward_capture.db`, not this)* | none registered | optional legacy backtest instrument only | **`blocked`** — superseded route; three writers still default here, so it is **not** physically immutable |
| R20 QB validation · A6 DynastyProcess pins | n/a | none | none registered | pinned study / backtest inputs | `static_pinned` |
| R4 `ras` · R6 RotoViz · R7 Campus2Canton | n/a | none | none registered | none | R4 `blocked` *(no production acquisition; NDA unresolved)* · R6/R7 `manual_only` / fixture-only |
| R9 MFL rookie ADP | public API, 24h registry; **mutation cadence UNVERIFIED** | none | 24h registered | separated descriptive-overlay destination exists; never Engine A/B | `blocked` — adapter query defect returns veterans |
| R10/R11 · R12 KTC · R14–R17 enterprise | n/a | none | none registered | none | `prohibited` / deferred |

### ⛔ Two registrations with NO job — carried from §6C.1

`roster_capacity` and `league_opportunity` hold registered freshness expectations with **no scheduler
behind them**. A staleness policy nothing can satisfy. **Not a licence to create either job.**

**STILL OPEN in step 3 *(narrowed — F5)*:**

- ~~source-publish cadence for **B20–B24** (their R7 states are `UNVERIFIED`, so a cadence claim would
  rest on nothing)~~ **WITHDRAWN.** Two separate things were merged: an R7 state and a source clock
  are different dimensions (R3), and B20–B23's clocks were **already independently CLEAR** in the
  remaining-candidate cadence artifact. They are now written above. **Blanking a measured field
  because a different field is unverified is the same defect as asserting one that isn't measured.**
- **N1–N8 PlayerProfiler source-publish cadence remains UNVERIFIED — and is now characterised as
  UNMEASURABLE from held evidence** *(`docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_measurement_claude_v1.md` (CLEAR at `1e33ba1d…`))*. **The distinction is load-bearing:** "unmeasured"
  implies someone need only look; **"unmeasurable" means the HELD OBSERVATIONS ARE INSUFFICIENT and
  an ADEQUATE GOVERNED SERIES must be created.** *(K1 — this read "the observation series does not
  exist and must be created", which **reinstated the source artifact's WITHDRAWN F1 premise** and
  contradicted the N1–N8 row nineteen lines above. **Three repeat observations DO exist** — the
  33s/100s/396s pairs. I retyped a corrected claim from memory instead of copying its corrected form,
  and the correction did not travel with it.)* **STATED WITH ITS OBJECT *(F4 residual — repaired 2026-08-07)*: under current
  sanctioned capability, repeat manual exports supplied by David are the identified route to a
  BOUNDED DESCRIPTIVE OBSERVED-CHANGE SERIES — NOT a route to M4 closure**, because manual retrieval
  observes endpoint state at our retrieval times and never publication. **A direct provider,
  support-channel or subscriber-facing declaration remains a possible route to a cadence declaration
  and is untried.** No analysis substitutes for either, and **no automated route exists in the repo
  today.** *(This bullet read "On current capability and governance it can be **closed only by**
  David supplying repeat manual exports" — **the exact defeated closure claim, still live 27 lines
  below the row that had already been repaired.** It survived my sweep because I searched the
  phrasing I had fixed — "only identified route" — instead of the CLAIM CLASS in its other wordings.
  Searching for your own corrected string only ever finds what you already corrected.)* *(K3 — qualified. That is a statement about **today's**
  sanctioned capability, NOT a proof that a future sanctioned route is impossible: the evidence says
  automated acquisition is **blocked pending** sanctioned-access/legal/reliability proof. No build is
  authorised here.)*
- **N19's upstream cadence remains UNVERIFIED.** An **observed-change rhythm is now measured** and
  written onto its row, but the reviewer **ruled it does not satisfy §6A**: a change rhythm is not a
  source-publish cadence, and the N19-only families have no series. **Characterising a clock is not
  closing it, and this row is the place that distinction is easiest to lose.**
- **⛳ THREE MORE SOURCE-PUBLISH FIELDS ARE OPEN — N18, N12/N13, N14b** *(added 2026-08-07 under the
  branch-(b) ruling, `ac_clock_closure_contract_asymmetry_review_codex_v2.md` `da04727b…`)*.
  **`continuous`/event-driven is admissible only on independent verification; the label is not
  evidence for itself.** The CLEAR cadence artifact pins nflverse clocks and **never pinned a Sleeper
  publication rhythm**, so all three carried values that had never been verified. **N14b inherits N12
  and cannot be stronger. N14 proper stays an evidenced `N/A`** — our own capture ledger, a satisfied
  field under M4's second limb, not an unverified one.
  **THE OPEN SOURCE-PUBLISH SET IS NOW FIVE MEMBER FIELDS: N1–N8 · N19 · N18 · N12/N13 · N14b.**
  **⛳ AND `N1–N8` IS A GROUP, DECOMPOSED 2026-08-07 — FIVE PlayerProfiler upstream REPORT FAMILIES:**
  **N1 gamelog · N2 roster/weekly · N3+N4 play-by-play (ONE family, two tables) · N5 medical history ·
  N6 Data Analysis/player-season.** With N19, N18 and N12/N13 that is **EIGHT provider clocks — the
  earlier "four" counted this whole group as a single clock.** **N7 is DERIVED from the roster export
  and inherits N2** (written by `playerprofiler_roster.py:594` under `stream=ROSTER_STREAM`; gamelog
  `:365` and pbp `:310` only read it and refuse when empty) — **not a sixth family.** **N8
  `pp_capture`/`pp_pbp_capture` is OUR capture ledger — an EVIDENCED `N/A` under the same M4 limb as
  N14**, satisfied rather than open, and wrongly readable as part of a provider bucket while grouped.
  **The member-field count is unchanged; nothing closes; A-C remains OPEN.**
  *(**How this was missed and then found:** the earlier repair added N19 to this list while three
  sibling Sleeper rows kept passing on the same unverified basis. It surfaced only by asking **why one
  row was held to a standard its siblings were not** — not by re-reading the list. Q1 had already
  caught this cell under-reporting once; **this is the same defect in the opposite direction**, and it
  is the reason a closure matrix must be audited against its own criterion rather than against its
  own prose.)*
- **Every proposed class in this section is planning judgment awaiting Codex's review**, not a
  measured fact (§6A / M4), and **no clock here is an installed job.**

---

## §6F. Disposition — Codex steps 1–3 batch review, all seven accepted

**Review artifact:** `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_batch_review_codex_v1.md`
SHA-256 `830d993cf24bb187578496d415d951e6301dd0941f773756aa45ff1f71f569ec`
**Catalog state reviewed:** `363c2609a9e7561416cd20e48bec2105c10b569d343a8e55bca5a387484a8b45`
**Verdict received:** NOT CLEAR.

> **⚠ TWO DIFFERENT F1–F7 SETS EXIST IN THIS DOCUMENT.** These are the **steps 1–3 batch** findings.
> §7's F1–F7 are a **different, older, closed** review (v2, SHA `d99b3247…`). Same letters, unrelated
> content. Cite by section, never by bare "F3".

**Nothing was contested. All seven are accepted and repaired at source** — the review's instruction
was to reconcile the canonical tables rather than append another correction layer, so there is no
"corrections" appendix; each fix is in the cell that was wrong.

| # | Finding | Repair, and where |
| :-- | :-- | :-- |
| **F1** | Automation classes in §§6C/6E contradict the governing plan and canonical §4.4 — a second, conflicting answer | **§4.4 is declared the single canonical table** (banner in §6C). Corrected to match it: **N18 → `automatic_active_verified`** · **B15–B19 → `automatic_active_health_unverified`** (current) with a separate TARGET column · **N12/N13/N14/N14b → `automatic_candidate`** · **N1–N8 → `blocked`** · **B5 → `automatic_candidate`** · **B12, B13 → `blocked`**. **§6C gained a quality/route-gap column** so a provenance defect can never again rewrite an operational-state class |
| **F2** | Roster Auditor is an **acquisition defect**, not merely a consumer edge | §6B.2 now reads **`consumer edge` + `acquisition defect`**, with `app.data.sleeper._get`'s live `httpx` call named as the reason and the FantasyCalc parallel drawn |
| **F3** | N19's uniqueness claim overstates the measurement | §6B.2 narrowed to *"the only exact historical endpoint representation of those families"*. The phrase "not held anywhere else" is deleted from the document |
| **F4** | §6D not complete; N14 missing; B20–B24 over-blanked; N16/N17 consumer state wrong | **N14 rowed and measured** (4 `cap` rows, columns listed) · **B20–B24 probed per cell** and now carry measured states · **N16/N17 corrected** to `production-model consumption UNPROVED` · the "COMPLETE except B20–B24" claim **withdrawn** and replaced with the three named reasons step 2 stays open |
| **F5** | §6E does not cover the exact §4.4 member set; B20–B24 cadence wrongly blanked | **N14, N14b, N18b (both rows), N19, N15b added** with all five fields · **B20–B24 cadence written** from the already-CLEAR cadence artifact · R4 split out of the RotoViz/Campus2Canton group to its canonical `blocked` |
| **F6** | §6C's live prose stale against §§6D/6E; §6D titled "complete" while its body said open | §6C's closing paragraph rewritten to the true status (**Gemini's follow-up arrived and is §6C.1**) · §6D's title corrected |
| **F7** | The growing-store rule names stores with no live capture job | Rule kept; **membership table added** — N9/N10 and N18 qualify (jobs verified loaded); **N12/N13 and N18b do not** |

### Three contradictions I found beyond the review

The review named four §4.4 conflicts (B5, B12, B13, N1–N8) and said "one canonical classification must
survive" without ruling which. Reconciling them exhaustively surfaced three more it did not list:

1. **N11 `fc_snapshots`** — §4.4 `manual_only` vs §6C/§6E `static_pinned`. I ruled `static_pinned` and
   edited §4.4. **That ruling was WRONG and is withdrawn — see §6F.2 R1.** Both candidate values were
   wrong and the class is now **`blocked`**. Flagging the edit for challenge is precisely what surfaced
   it, which is the argument for flagging rather than editing quietly.
2. **N12/N13** — the `manual_only` label confused *"a human runs it"* with *"a human is required"*.
   **`manual_only` is about the access path; `automatic_candidate` is about the absent scheduler.**
   That distinction was the root of two of the review's four named conflicts as well.
3. **R4 RAS** — §6E grouped it with RotoViz/Campus2Canton as `manual_only`/fixture-only; §4.4 has it
   `blocked` (no production acquisition, NDA unresolved). Corrected to `blocked`.

### Deliberately NOT done

- **No §1 checkbox moved.** A–C remains open.
- **B20–B24 are `MEASURED`, not `VERIFIED`** — measured by the authoring lane, so R4 keeps them open
  until Codex reruns the probes.
- **Nothing was repaired that the inventory merely records.** The MFL adapter defect, the R1/R18
  registry mismatches, the `feature_refresh` weekly/daily mismatch and the two jobless freshness
  registrations are all still **inventory facts awaiting David's word**, not work items taken up here.

### §6F.2 Second round — Codex fresh-pin recheck, R1–R5

**Review artifact:** `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_recheck_codex_v2.md`
SHA-256 `71dfd83a34f5cd11ec4f8e085a7bdeba73c66080f4e65fe9d43301c3cb0e2eef`
**Catalog state reviewed:** `d92b6d0c…` · **Verdict:** NOT CLEAR, five residuals.
**All five accepted. None contested.** R1, R3 and R4 were each reproduced against the code before
acceptance rather than taken on the reviewer's word.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **R1** | N11 is not `static_pinned` — three executable writers still default to `app/data/fc_snapshots.db` | **ACCEPTED, reproduced.** `snapshot_fantasycalc.py:31,91-107` (live FC HTTP + append), `ingest_market_archive.py:161`, `backfill_market_archive.py:38,88-105` all default to that path. **My `static_pinned` is withdrawn.** Reclassified **`blocked`** in §4.4, §6C and §6E — the named blocker is `use`/`route`: the collector is superseded by design and scheduling any writer recreates the §6B.1 parallel-acquisition defect. **`static_pinned` is recorded as the DESIRED state with physical write immunity as its pass condition** |
| **R2** | Stale `manual_only` for N12/N13 in the §3 corrections list | **ACCEPTED.** Class assertion struck in place; **consumerless preserved**, since that was the correction's actual point |
| **R3** | N19's SOURCE-publish cell held a local capture fact | **ACCEPTED, and it is worse than a blank.** `n/a — one-time replay` describes OUR capture history, not the upstream rhythm. Set to **`UNVERIFIED`** and **N19 added to the step-3 open list** |
| **R4** | B20 "no store of any kind" is false | **ACCEPTED, reproduced.** `build_w2_features.py:520-524` live-loads Combine, `:597-605` merges derived values, `:637-647` rewrites `V3_CSV`. Corrected to **no exact/raw/canonical SOURCE capture**, with derived values persisted in the active training artifact |
| **R5** | Reported diffstat `+286/-78` does not match the repo | **ACCEPTED — my arithmetic error, and the mechanism is worth naming.** I read `git diff --stat`'s single number (**total changed lines**) as insertions, and took `-78` from a **four-file** summary while attributing it to one file. Corrected in the ledger, **cited against a pin**, and taken from `git diff --numstat` — never from `--stat` |

**A new finding the R1 probe produced, which neither lane had.** The committed plist
`ops/launchd/com.davidleess.dynasty-fc-snapshot.plist` documents the legacy store as *"a frozen,
read-only archive"* — while three runnable scripts default to writing it. That is a
**declared-vs-physical gap**, the same defect class as R1 `nfl_data_py` and R18's declared
`parquet_snapshot`. **Recorded, not repaired:** closing it means repointing or refusing those default
paths, which is remediation needing David's word.

**Reading that plist also settled the fact the class depended on:** it runs
`run_fc_forward_capture.py` against `fc_forward_capture.db`. **No installed job writes
`fc_snapshots.db`** — so the store is dormant, and **dormant is not immutable.** That distinction is
the whole of R1, and it is why "nothing writes it in practice" was not good enough.

---

### §6F.3 Third round — Codex recheck, Q1–Q5

**Review artifact:** `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_recheck_codex_v3.md`
SHA-256 `bd068fb39a757b532034f5072360044b1baa7c899b5c803e27c1fccd3fa9e9ac`
**Catalog state reviewed:** `ff25c9c8…` · **Verdict:** NOT CLEAR, five reconciliation findings.
**All five accepted, none contested.** Q4 and Q5 were probed against the code before acceptance.

**N11's class was confirmed by the reviewer at `blocked`** — the third answer for that cell, and the
one that survived a round it was explicitly invited to fail.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **Q1** | §6A's cadence row named only N1–N8 while §6E had opened N19 | **ACCEPTED.** Both unmeasured source clocks now named in the closure cell. **A closure matrix that under-reports its own open items is worse than no matrix** — it was reporting N19 settled while the section it summarises said otherwise |
| **Q2** | §1 and §3's live prose still called work "missing" that §§6B/6D/6E now contain | **ACCEPTED.** Restated at both sites: the work is **authored and awaiting independent review, which is not missing**. The checkboxes stay open, but the stated gate is now the true one — **R4 verification plus the two named unmeasured clocks** — not authorship |
| **Q3** | Stale class tokens: R13 said `manual`; N14b's consumer cell ended in `manual_only` | **ACCEPTED — and a FOURTH site found by sweep.** §2.1's own R13 registry row also carried `manual_only`; it was fixed too. Two cited, three existed after N14b, four in total. R13 → *manually run / unscheduled* (a physical fact, not a class). N14b's cell → its **raw-before-parse role**. The N14b case was also **an automation class sitting in a consumer-state cell — the V2-F2 defect a third time**, which is why §3's warning is worth keeping |
| **Q4** | N19 is not `manual_only` | **ACCEPTED, probed.** Its `fetch_log` records **176 direct Sleeper API calls, zero failures** — an API route, not a human export. Reclassified **`blocked`** in §4.4 and §6E; the named blocker is **use** (no recurring use decided). **This is the SECOND edit to a previously CLEARed §4.4 cell** — requested by the reviewer this time, and disclosed on the same terms as the first. **§6C carries no N19 row**, verified, so nothing there needed reconciling |
| **Q5** | §6D's N11 `consumed = market overlay` contradicts the canonical row and the code | **ACCEPTED, reproduced.** Measured consumers are `run_backtest.py:35,178` via `--market-store` and `eval/backtest_harness.py:50,500`. **No app or service consumes `MarketSnapshotStore`**, and `ingest_market_archive.py` is a WRITER. Corrected to the optional legacy backtest/market-comparison harness |

### The finding Q5's probe produced — same label, different row, not raised by either lane

**§6D's N9/N10 cell carried the identical wrong label**, and nobody had flagged it. Measured:

- N9/N10's real consumers are the **scheduled Market Divergence + What-Changed reports**
  (`scripts/run_market_divergence_refresh.py`, `what_changed/daily_diff.py`) — exactly what the
  canonical §3.1 N10 row already said.
- **`market_overlay_service.py:192-193` calls `fetch_with_cache()`** — the request-time adapter.

**So the market-overlay surface is served by the ungoverned request-time route and NOT by the governed
capture store.** That is §6B.1's `acquisition defect` restated as a *consumer* fact rather than an
acquisition one, and it makes the defect materially worse than first recorded: the governed daily
capture is not what the overlay shows David. **Recorded, not repaired** — routing the overlay onto the
governed store is a consumer migration needing David's word.

**Why one wrong label appeared on two adjacent rows:** "FantasyCalc data" was treated as one thing, so
whatever consumed *any* of it was written onto *all* of it. The canonical §3.1 rows had it right the
whole time; the summary table did not inherit them.

---

### §6F.4 Fourth round — Codex recheck, T1–T3

**Review artifact:** `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_recheck_codex_v4.md`
SHA-256 `7ad5718a90d51dc9ddb87f552b1d7cbaeaf4573ba651ce1c41dad4a420b938e3`
**Catalog state reviewed:** `0080e46e…` · **Verdict:** NOT CLEAR, three residuals.
**All three accepted, none contested.** T3 was re-measured against the live database first.

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **T1** | Closure surfaces still stale: §3's "genuinely incomplete" paragraph, three pre-authoring §6A cells, and an "one §4.4 cell edited" count that this round made two | **ACCEPTED, all four sites.** Restated as **authored-awaiting-independent-review**; only genuinely `UNVERIFIED` cells stay open; checkboxes untouched. The edited-cell count is now **two (N11, N19)**, with the consequence stated: **§4.4's original CLEAR pin no longer describes §4.4** |
| **T2** | §4.4's N19 upstream-rhythm column held "one-time 2023–2026 replay evidence" | **ACCEPTED.** Upstream field → **`UNVERIFIED`**; the one-time replay + 176 logged calls **retained as local capture evidence in the same cell**, labelled as such. `blocked` stands |
| **T3** | Live `20,043` counts violate §6B.3's own as-of rule | **ACCEPTED, re-measured.** `app/data/fc_forward_capture.db` at **2026-08-06 22:23 ET: 20,518 raw + 20,518 joinable, 44 snapshot dates, 2026-06-24 → 2026-08-06** |

**T1's paragraph is the defect eating its own tail.** The §3 paragraph struck here was itself written
to correct a stale "streams are missing" claim — and then went stale when the work *it* called
incomplete got done. **Second generation of the same defect, in the sentence recording the first.**
That is the §5 register's whole thesis, and it is why the register stays.

### T3's sweep found five sites, not three

Codex named three. Grepping the whole document for the number found **five**, and they needed
**different** treatment — which is the reason to sweep rather than patch the cited ones:

| Site | Kind | Treatment |
| :-- | :-- | :-- |
| §2.1 R8 physical state · the built-route summary · §3's grain decomposition · §6A's R8 "current measured state" | **live current-state claims** | **Updated** to `20,518 as of 2026-08-06` |
| §3.1 N10 canonical row | **a dated historical measurement** (§3.1 is pinned to 2026-08-05 at commit `2a42759`) | **NOT rewritten** — the as-of was made explicit instead, per the reviewer's "do not rewrite historical measurements silently" |

**And a sixth, self-found: §6B.3's own rule sentence read "it is 20,518 today."** *Today* is a decaying
word, in the sentence that states the rule against decaying counts. Replaced with an as-of date.
**A rule stated in violation of itself is not a rule anybody can follow.**

---

### §6F.5 Fifth round — §4.4 whole-table CLEAR, and U1

**Review artifact:** `docs/agent-ledger/evidence/2026-08-06/ac_steps_1_3_recheck_codex_v5.md`
SHA-256 `935f7926957568484bad4cf19da5f1bee76ab4a437f02e5c61a10a629b91916a`
**Catalog state reviewed:** `0d6a1ea4…`

**✅ §4.4 IS INDEPENDENTLY CLEAR at that pin.** Codex ran a **whole-table** review rather than another
delta pass — 35 grouped rows, every class value valid against the seven definitions, member surface
present, **N11 and N19 both correctly `blocked`**, N19's upstream clock correctly `UNVERIFIED`. **The
superseded original §4.4 pin no longer carries review weight.** *(I raised the concern that a delta
chain could not certify a table whose bytes had changed twice; the reviewer ruled on it by doing the
whole-table pass. Recorded because asking for a harder review than the one on offer is the cheap half
of this cycle.)*

**T1–T3 CLOSED.** Artifact verdict **NOT CLEAR on one finding.**

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **U1** | §3.1's "Still owed on Table B-N" paragraph is pre-authoring state | **ACCEPTED.** Struck and replaced with the four clause-by-clause corrections and **the real gate named**: independent R4 verification plus the two unmeasured source clocks. The table stays **not checked off** |

**U1's fourth clause was wrong in a different way from the other three.** R7 states, automation edges
and route dispositions had been *authored*; **PFF aggregation was never a Table B-N gate** — §6A puts
combined-view aggregation outside the A-C blocking path (David, 2026-08-06). Listing it as "still
owed" did not just go stale, it **contradicted a boundary David set**. Three of the four clauses
decayed; the fourth was never true here.

### Whole-document sweep for this defect class — run, and the result stated

**Grep over the full document** for `Still owed` · `Still missing` · `Still genuinely` · `not yet
written` · `remain(s) unreconciled` · `otherwise incomplete` · `in flight` · `no canonical … carries`
· `not complete`. **Eleven hits. U1 was the only live one.** The rest are:

- already struck or repaired in earlier rounds (§1 A, §3's T1 paragraph, the two §6A cells);
- **genuinely open and accurate** — §6E's "STILL OPEN in step 3" (the two unmeasured clocks);
- **historical quotations** inside correction notes and the §7 banner, which must keep their original
  wording to remain auditable.

**Stated so the next round need not rediscover it:** after this repair there is **no remaining live
pre-authoring state claim in this document** that the sweep can find. That is a claim about a
mechanical grep over named patterns — not a guarantee that no such sentence exists in a form the
patterns miss.

---

### §6F.6 Clock-characterisation edit — Codex review, K1–K3

**Review:** `docs/agent-ledger/evidence/2026-08-07/ac_clock_characterisation_catalog_review_codex_v7.md`
SHA-256 `57a3e51c9578f2514237264efaba9e18ab3bb42c6e9dea989d14b7c0e83ff03f`
**All three accepted, none contested.**

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **K1** | The step-3 list **reinstated the source artifact's WITHDRAWN F1 premise** — "the observation series does not exist" | **ACCEPTED.** Three repeat observations **do** exist (33s/100s/396s). Corrected to *held observations are insufficient; an adequate governed series must be created* — the form the N1–N8 row **nineteen lines above already had**. **The catalog contradicted itself because I retyped a corrected claim from memory instead of copying its corrected form** |
| **K2** | Canonical/summary reconciliation incomplete — six live surfaces still reduced both clocks to "unmeasured" | **ACCEPTED, all six.** §4.4's N19 cell, §1 C, §3.1's header, Table B-N's two status paragraphs, and the current-state summary now carry one compact common state. **Historical disposition rows deliberately left unedited**, per the reviewer's scope |
| **K3** | "only by David supplying repeat manual exports" overstates the evidence | **ACCEPTED.** Qualified to **today's sanctioned capability**: no automated route exists in the repo now, but the evidence says automated acquisition is **`blocked pending`** sanctioned-access/legal/reliability proof — **not proven impossible.** No build authorised |

**⚠ K1 IS THE SEVENTH INSTANCE OF ONE DEFECT TODAY, AND THE FIRST TO TRAVEL BETWEEN DOCUMENTS.** Every
earlier instance was a stale claim left standing *in place*. This one was **a claim already corrected
in one artifact, reintroduced into another because it was retyped from memory rather than copied.**
The register in §5 records staleness; **this is a distinct mechanism — correction failing to travel
with the idea — and it is recorded here rather than folded into the existing entry.**

**Editing §4.4's N19 cell retires that cell's earlier whole-table CLEAR pin** and requires fresh review
of the changed cell. Stated here rather than left for a reader to infer.

**Unchanged: both source-publish fields stay OPEN, neither clock closes, no §1 checkbox moved.**

---

### §6F.7 Clock-characterisation recheck — Codex, L1–L3

**Review:** `docs/agent-ledger/evidence/2026-08-07/ac_clock_characterisation_catalog_recheck_codex_v8.md`
SHA-256 `29d0a88a704b6b67825dbd1e8ebb63e2c175d592c654beb64e14f8e80459682a`
**K1–K3 confirmed repaired.** **All three of L1–L3 accepted, none contested.**

| # | Finding | Disposition |
| :-- | :-- | :-- |
| **L1** | §1 C named "clocks are proposals, not installed jobs" as a **second closure gate** | **ACCEPTED.** Demoted to a **boundary**. It was never a gate: §6A permits `N/A`/`not scheduled` **with evidence**, its authority column says **pinning ≠ scheduling**, and M3 separates inventory closure from remediation. **As written it put A-C behind scheduler enablement that the agreed sequence places AFTER inventory closure** — the same inversion M3 corrected once already |
| **L2** | "§4.4 (whole-table CLEAR at this pin)" contradicts the two rows saying the N19 edit **retires** that pin | **ACCEPTED.** Now reads: whole-table CLEAR at its **prior** pin; the N19 cell has since been edited and **the current bytes are NOT cleared**, awaiting the review §6F.6 names. **A document may not certify itself mid-review** |
| **L3** | Two live present-tense rows still said a shadow PP HTTP route **exists** | **ACCEPTED.** Both retired 2026-08-07 and struck in place. **Class stays `blocked`** — on the correct ground that **no SANCTIONED automated acquisition exists**, not that no code does |

**L3 is a defect I created and did not sweep for.** Retiring the two routes this morning made these
two catalog rows false, and **I landed that change without grepping the catalog for claims it
invalidated.** The post-fix sweep discipline exists precisely for a fix whose blast radius lands in a
different document from the fix. **Eighth instance of the day's defect family; the second to cross a
document boundary — and unlike K1, this one crossed by a code change rather than a retyped sentence.**

**Unchanged: both source-publish fields OPEN, neither clock closes, no §1 checkbox moved.**

---

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
| 2026-08-06 | Codex | **Steps 1–3 batch review — NOT CLEAR**, seven findings (§6F). |
| 2026-08-06 | Claude | **Steps 1–3 repair.** All seven accepted, none contested, repaired at source per §6F. §4.4 declared the single canonical classification table; §§6C/6E reconciled to it and a quality/route-gap column added so provenance defects cannot rewrite operational state. B20–B24 and N14 **probed per cell** and now carry measured R7 states (B22/B23 are `captured` as tracked frozen pins — the prior blanket ✗ was wrong). N16/N17 corrected to `production-model consumption UNPROVED`. §6E membership extended to the exact §4.4 set. **One canonical edit made against a previously CLEARed §4.4 cell (N11), flagged in §6F for challenge — and the flag worked: the recheck falsified it (§6F.2 R1).** No checkbox moved. |
| 2026-08-06 | Codex | **Fresh-pin recheck — NOT CLEAR**, five residuals R1–R5 (§6F.2). |
| 2026-08-06 | Claude | **R1–R5 repair.** All five accepted, none contested; R1/R3/R4 reproduced against the code first. **N11 reclassified `blocked`** — my `static_pinned` withdrawn, because three runnable writers still default to `fc_snapshots.db` and dormant is not immutable. N19's source clock corrected from a local-capture `n/a` to `UNVERIFIED` and added to the step-3 open list. B20's "no store of any kind" corrected — derived Combine values ARE persisted in the active training artifact. Stale N12/N13 class assertion struck in §3. Diffstat reporting corrected to `--numstat`, pin-scoped. **New finding from the R1 probe: the committed `fc-snapshot` plist declares the legacy store "frozen, read-only" while three scripts can write it — a declared-vs-physical gap, recorded not repaired.** No checkbox moved. |
| 2026-08-06 | Codex | **Round-3 recheck — NOT CLEAR**, five reconciliation findings Q1–Q5 (§6F.3). N11 `blocked` confirmed. |
| 2026-08-06 | Claude | **Q1–Q5 repair.** All five accepted, none contested; Q4/Q5 probed first. **N19 reclassified `blocked`** (176 direct API calls in its fetch log — an API route, not a human export; the blocker is `use`) — the second edit to a previously CLEARed §4.4 cell, reviewer-requested. §6A's closure cell now names **both** unmeasured source clocks. §1/§3 live prose restated from "missing" to **authored-awaiting-review**, with the true gate named. Stale `manual`/`manual_only` class tokens removed from R13 and N14b. **N11 and — self-found — N9/N10 consumer labels corrected: neither feeds the market overlay; `market_overlay_service.py:192-193` reads the request-time adapter, so the overlay is served by the ungoverned route and not by the governed capture store.** Recorded, not repaired. No checkbox moved. |
| 2026-08-06 | Codex | **Round-4 recheck — NOT CLEAR**, three residuals T1–T3 (§6F.4). |
| 2026-08-06 | Claude | **T1–T3 repair.** All three accepted, none contested; T3 re-measured against the live DB (**20,518 + 20,518, 44 dates, 2026-08-06 22:23 ET**). §3's "genuinely incomplete" paragraph and three §6A cells restated to authored-awaiting-review; edited-§4.4-cell count corrected from one to **two (N11, N19)** with the consequence that §4.4's original CLEAR pin no longer describes it. §4.4's N19 upstream column corrected from local pull history to `UNVERIFIED`, replay evidence retained as local capture evidence. **T3 swept to five sites, not the three cited — four live claims updated, one dated historical measurement given an explicit as-of rather than rewritten — plus a sixth self-found: §6B.3's own rule said "20,518 today", a decaying word inside the rule against decaying counts.** No checkbox moved. |
| 2026-08-06 | Codex | **Round-5 verdict — §4.4 WHOLE-TABLE CLEAR** at pin `0d6a1ea4…` (35 grouped rows; N11/N19 `blocked` confirmed; superseded original §4.4 pin retired). Artifact **NOT CLEAR on U1**. |
| 2026-08-06 | Claude | **U1 repair.** §3.1's "Still owed on Table B-N" paragraph struck and replaced clause by clause, with the real gate named (R4 verification + the two unmeasured source clocks); the table stays unchecked. **Its PFF clause was never a Table B-N gate — §6A places combined-view aggregation outside the A-C blocking path per David, so that clause contradicted a boundary rather than merely decaying.** Whole-document grep for the defect class run: eleven hits, U1 the only live one. No checkbox moved. |
| 2026-08-07 | Claude | **Both open source clocks characterised, neither closed.** Wrote the independently CLEARed open-clocks evidence (`1e33ba1d…`) onto the N19 and N1–N8 rows in §6E, the step-3 open list, and §6A's cadence cell. N1–N8 is now `UNMEASURABLE from held evidence` — one content vintage per stream, three repeat observations spaced 33–396s, non-diagnostic — closable **only by David supplying repeat manual exports**, with no automated route left in the repo after the 2026-08-07 retirement of both legacy scripted routes. N19 carries a measured off-season observed-change rhythm (`players` 21/21 · `rosters` 9/21 · `draft_state` 6/21 · `users` 0/21; `league`'s apparent 21/21 is **only** `daily_waivers_last_ran`) which the reviewer **ruled is not a source-publish cadence**. **A-C remains OPEN on both clocks. No §1 checkbox moved.** |
| 2026-08-07 | Codex | **Clock-characterisation edit NOT CLEAR**, three findings K1–K3 (§6F.6). |
| 2026-08-07 | Claude | **K1–K3 repair.** K1: withdrawn F1 premise reinstated in the step-3 list and corrected to *held observations insufficient / adequate governed series must be created* — the seventh instance of the day's defect and the first to travel BETWEEN documents by being retyped from memory. K2: six live canonical/summary surfaces reconciled to one compact common state; historical disposition rows left unedited per scope. K3: "only by David" qualified to today's sanctioned capability — automated acquisition is `blocked pending` proof, not proven impossible. **Editing §4.4's N19 cell retires that cell's earlier whole-table CLEAR pin.** Both clocks remain OPEN; no checkbox moved. |
| 2026-08-07 | Codex | **Recheck NOT CLEAR**, three residual live-state defects L1–L3 (§6F.7). |
| 2026-08-07 | Claude | **L1–L3 repair.** L1: "not installed jobs" demoted from a closure gate to a boundary — as a gate it put A-C behind scheduler enablement the agreed sequence places after inventory closure. L2: §4.4 no longer certifies its own current bytes as CLEAR while its N19 cell awaits review. L3: two rows still claiming a live shadow PP HTTP route struck — **both routes were retired by my own commit this morning and I did not sweep the catalog for claims that invalidated.** Both clocks remain OPEN; no checkbox moved. |
| 2026-08-07 | Claude | **A-C closure-contract reconciliation — THE OPEN SET GREW FROM TWO CLOCKS TO FIVE FIELDS.** David's word: *"reconcile the catalog and board."* Codex ruled **branch (b)** (`da04727b…`): **`continuous`/event-driven is admissible only on independent verification — the label is not evidence for itself.** The CLEAR cadence artifact pins nflverse clocks and **never pinned a Sleeper publication rhythm**, so **N18 `continuous league state` and N12/N13 `continuous league events` were carrying values that had never been verified**, and **N14b inherits N12**. Reconciled in §6A's C cell, §6E's N18/N12-N13/N14b/N14 rows, §6E's step-3 open list, and **§4.4's N12–N14b and N18 upstream cells — the THIRD and FOURTH edits to previously CLEARed §4.4 cells, which retires those cells' pin.** §4.4's column title *"Upstream publish / change rhythm"* is flagged: **it merges the two clocks R3 keeps separate, and that merge is how an unverified value read as settled.** **N14 proper CONFIRMED an evidenced `N/A`** — our capture ledger, a satisfied field under M4's second limb, not an unverified one. **Separately: the provider-documentation route — which supplied every B-row clock — was tried on both original clocks for the FIRST time and is NEGATIVE for both, and closes nothing**: no server-side cadence on the inspected public Sleeper page (its rate-limit/once-daily language is **client-polling guidance**, a different clock under R3), and no PlayerProfiler statement in public search. **Bounded to the searches run — a direct provider answer or subscriber material could still supply a declaration.** **How the asymmetry was found: by asking why ONE row was held to a standard its siblings were not** — Q1 had caught this cell under-reporting once already, and this is the same defect in the opposite direction. **ALL FIVE FIELDS REMAIN OPEN. No §1 checkbox moved.** |
| 2026-08-07 | Claude | **PlayerProfiler provider-scope decomposition — the CLOCK count was wrong; the MEMBER-FIELD count was right.** David: *"ok drive this through claude and codex with a reasonable role for gemini too."* `N1–N8` was carried as **one** source-publish field and therefore, implicitly, **one clock**. It is a **GROUP spanning FIVE distinct PlayerProfiler upstream report families** — **N1** gamelog · **N2** roster/weekly · **N3+N4** play-by-play (ONE family, two tables) · **N5** medical history · **N6** Data Analysis/player-season — **plus a DERIVED table and OUR OWN LEDGER.** With Sleeper's N19, N18 and N12/N13 the true count is **EIGHT provider clocks, not four**; the **five §4.4 member fields are unchanged**. **N7** `pp_identity_bridge` is **derived from the ROSTER export and inherits N2** — verified at `playerprofiler_roster.py:594` (`apply_block(table=BRIDGE_TABLE, stream=ROSTER_STREAM, block="bridge")`), with `playerprofiler_gamelog.py:365` and `playerprofiler_pbp.py:310` only `SELECT`ing from it and refusing when empty; *(a first pass claimed three modules WRITE it — a substring grep counting references as writes, withdrawn)*. **N8** `pp_capture` + `pp_pbp_capture` is **OUR capture ledger and an EVIDENCED `N/A` under the same M4 limb as N14** — the **F3 class again: a grouped label absorbing a member that is satisfied, not open.** Reconciled across §1, the three §3 live summaries, §4.4's grouped row, §6A's C cell, §6E's N1–N8 row and the step-3 list; §6F sections and prior change-log rows keep their historical wording. **Consequence for closure: a single question about one report family CANNOT close this row — explicit FAMILY-LEVEL COVERAGE for all five is required, however many replies or documents supply it** *(F2 — an earlier phrasing read "five families need five answers", over-specifying the MECHANISM when the contract is the COVERAGE; one authoritative reply may cover several or all five)*, which is also why the parked provider draft's "Covers N1–N8" was false. **ALL FIVE MEMBER FIELDS REMAIN OPEN. A-C remains OPEN. No §1 checkbox moved.** |
| 2026-08-08 | Claude | **B13 `contracts` CAPTURED AND EXPORTED.** *(F3: this first read "the first new external stream this program has landed by agent-built ingestion" — FALSE and withdrawn. Twelve nflverse streams were already agent-built and materialized. The accurate claim is narrower: **the first stream landed by this daily-control work**, and the last of the 13 bound specs to materialize.)* David's word: *"run it once codex clears"*, after a 3-of-3 cockpit alignment and a Codex GREEN CLEAR. A runnable daily control plane now exists (`src/dynasty_genius/sources/daily_control.py` + `scripts/run_layer1_daily_control.py`): one manifest naming **all 20 sources** with connect method, ingest command, destination, success marker, refresh class and staleness; a read-only preflight; and an executor that isolates per-source failure. **Measured on the authorized free run:** `contracts` **97,022** product-store rows across two snapshot vintages (48,511 each — accumulation across distinct `snapshot_id`s is documented `apply_snapshot` behaviour; the two vintages' row content hashes IDENTICALLY, verified independently of the store, so this is retention, NOT duplication). `contracts.parquet` 97,022 × 31 exported; ready marker advanced `…20260805T1334…` → `…20260808T0357…`; 14 manifest files; `unresolved_identity.parquet` 259,861 rows carrying the exact ordered ten-column all-`String` schema, of which **32,620 contracts rows with non-null `snapshot_id`** — the exact condition that killed the 02:28 export. **A REAL DEFECT WAS FOUND BY THE FIRST LIVE RUN AND FIXED:** `pl.DataFrame(...)` inferred the unresolved frame's types from a bounded window, so a late non-null `snapshot_id` could not be appended; replaced with an explicit schema, plus loud cleanup of partial run directories and a last-good freshness fallback so a failed run no longer reports `unknown` when the prior success is on disk. **STILL OPEN, unchanged:** all five A-C provider source-publish fields (N1–N8 · N19 · N18 · N12/N13 · N14b). **The controller's `daily` target is OUR local refresh obligation and is NOT a provider cadence claim** — R3 holds. **No scheduler installed, no paid route, no provider contact, no manual route touched. No §1 checkbox moved.** |
| 2026-08-08 | Claude | **PFF Layer 1 intake/backfill reconciliation — ONE live row only (N15/N15b §route).** **ACQUISITION UNCHANGED and still MANUAL:** a human downloads the subscriber export; no automated fetch, provider contact, scheduler, paid call, or network path exists, and the automatic-job column stays `none`. **ADDED:** an operator-callable intake/indexer (`scripts/run_pff_intake.py`, `src/dynasty_genius/sources/pff_intake.py`) with sidecar-DECLARED provenance (never inferred from filenames); a private SQLite **metadata** ledger (no paid payload rows); and daily-control status — the route now reports `entry_status.ok=True` with freshness from the newest declared **source** retrieval time `2026-08-01T09:23:59.950822-04:00` (exact), `manual_due`. **Aggregate acceptance:** 149 payloads / 307 offering mappings / 7 families / 12 schemas / all 6 governed statuses / 0 mismatches / 0 unresolved / replay idempotent; the raw archive stayed byte-identical with unchanged mtimes and the governed inventory/coverage/map artifacts were not rewritten. **NO SELECTION:** no REG/REGPO basis, no duplicate-vintage winner, no status filtering, no cross-family or cross-schema flattening — **§3.3's finding that no deduplicated total is defensible is REINFORCED, not retired** (an independent measurement here found a REGPO-only basis drops 1 player present only in REG). **NO CADENCE OR CHECKBOX MOVEMENT:** our local daily target is not a provider publication cadence (R3), and the **A-C publication-cadence fields remain OPEN**. No consumer rewiring; the YPRR 0/874 materialization gap is unchanged and separate. **Historical rows above are not rewritten.** *(Codex GREEN CLEAR: `docs/agent-ledger/evidence/2026-08-08/pff_layer1_intake_green_clear_codex_v1.md`.)* |
| 2026-08-09 | Codex | **B21 schedules first canonical capture.** One sanctioned provider retrieval landed the global nflverse Parquet offering in `app/data/sources/nflverse_schedules`: 517,546 raw bytes, SHA `eeea1f47644c…`, 7,548 × 46, 272 season-2026 rows, schema SHA `9bbd6413bc4c…`, one check/one content vintage, ready marker, sanitized delivery provenance, zero duplicate `game_id`, and replay with no new identity. The capture truthfully declares `finality_capability=unverified`; it does not migrate the Realized Outcome consumer, prove a game terminal, or install a scheduler. |
| 2026-08-09 | Codex | **N20 CFBD FBS schedules first canonical capture.** Exactly one paid `GET /games?year=2026&seasonType=both&classification=fbs` request landed 655,068 exact raw bytes (SHA `76f0af56c903…`) in `app/data/sources/cfbd_fbs_schedules`: 888 source games × 34 fields, schema SHA `0a87d5754e30…`, one check/one content vintage/one success ledger event, remaining-call telemetry 73,014, zero duplicate IDs, and zero rows outside the requested season/FBS scope. The 127 FBS-vs-FCS games are retained because CFBD's FBS competition filter includes non-FBS opponents. Replay minted no identity or request. No scheduler, cadence input, consumer, feature, or model use is implied. |
