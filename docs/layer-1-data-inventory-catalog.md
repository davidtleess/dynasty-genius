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

- [ ] **A. Sources** — **REOPENED (F1/F2).** **7** rows enumerated vs **20 machine-registry
      definitions** plus non-registry sources. Incomplete. *(This read "9" until V2-F1: the count was
      written for v1's table and left standing after F2 merged A7/A9 into one DynastyProcess source.
      Fifth instance of the §5 defect — a figure describing a table I had just changed.)*
- [ ] **B. Ingestion streams** — **REOPENED (F1/F6).** Canonical nflverse specs only; missing
      PlayerProfiler, PFF, CFBD, FantasyCalc, Sleeper, the direct feature-refresh loaders, and
      validation/context streams.
- [ ] **C. Refresh frequencies** — **REOPENED (F4/F5).** Job matrix received; stream↔job edges wrong
      in v1 and now corrected; per-stream cadence unresolved.
- [ ] **D. Catalog** · [ ] **E. Player 360** · [ ] **F. Semantic layer + metrics** · [ ] **G. Schemas**
      *(phase B — CLOSED until A–C clear)*
- [ ] **H. Sources we still need to ingest** *(§6 — cannot be answered yet, F7)*
- [ ] **I. Every row independently verified** · [ ] **J. → Layer 2 research opens**

> **v1 marked A and B `[x]`. That was false** — enumeration was partial and the checkmarks asserted
> a completeness that did not exist. Unchecked and reopened.

---

## §2. Table A — SOURCES *(INCOMPLETE — F1)*

**Machine registry: 20 definitions** in `src/dynasty_genius/sources/source_registry.py` —
`campus2canton · cfbd · dynasty_data_lab · dynasty_nerds · fantasycalc · genius_sports · ktc ·
mfl_rookie_adp · nfl_data_py · nfl_nextgen_stats · nflreadpy_qb_context · nflreadpy_qb_validation ·
pff · playerprofiler · ras · rolling_insights · rotoviz · sleeper · sportradar · stats_perform`.
**Each needs a row with its access/loader/capture state, including deferred, fixture-only and
prohibited states. Not yet done.**

| # | Source (provider + dataset family) | Access | Stores | Status |
| :-- | :-- | :-- | :-- | :-- |
| A1 | nflverse via `nflreadpy 0.1.5` | free | `nflverse_usage.db` | partial |
| A2 | PlayerProfiler | **manual, by David** | `playerprofiler.db` | partial |
| A3 | PFF | **manual, by David** | payload files | UNVERIFIED |
| A4 | CFBD | **paid** | `sources/cfbd_foundation/` | UNVERIFIED |
| A5 | FantasyCalc | free | `fc_forward_capture.db` + part of `fc_snapshots.db` | partial |
| A6 | **DynastyProcess** *(ONE source — v1 split it into A7/A9 by loader, F2)* | free, GPL-3.0 repo | pinned `values.csv`; part of `fc_snapshots.db` | partial |
| A7 | Sleeper | free | `league_transactions.db` **(transactions only — v1 claimed league/roster/universe, F2)** | partial |

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

**`exported` is column-wide UNVERIFIED pending per-row export-path evidence** — the ✓ marks reflect
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

**STREAMS NOT YET IN THIS TABLE (F1) — enumeration is the open work:** PlayerProfiler (9 tables),
PFF families, CFBD, FantasyCalc capture, Sleeper capture, the **direct feature-refresh loaders**
(`player_stats`, `rosters`, `snap_counts`, `pbp`, `participation` — pulled straight from `nflreadpy`,
bypassing the canonical store, see §4), and validation/context streams.

**The v1 summary "3 consumers / 9 substrate_only / 1 never run" is WITHDRAWN** — it was exclusive
over an incomplete table, and B4's consumer state is UNVERIFIED.

---

## §4. Refresh frequencies

### §4.1 Job matrix *(Gemini, Operations & Telemetry — telemetry facts, not a catalog pass)*

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

**That is a genuine Layer-1 structural finding and it is exactly what this inventory was ordered to
surface.** It is recorded as a measured fact. **It is not a recommendation, and no agent may treat it
as authority to build, schedule, or re-sequence anything** — David rules on that.

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
| 2026-08-05 | Claude | **v3.** V2-F1..F4 all accepted, none contested. §1 source count 9→**7** (stale after the F2 merge — **fifth** §5 instance). Table B carries all **five** R7 states with disposition as its own column. "13 streams" restated as **13 bound / 12 materialized**. **B4 resolved** from Codex's probe: canonical export has no production consumer; the daily job's direct `load_snap_counts` is a separate provider-read stream — so the nine consumerless streams are now NAMED. `exported` marked column-wide UNVERIFIED pending probes. |
