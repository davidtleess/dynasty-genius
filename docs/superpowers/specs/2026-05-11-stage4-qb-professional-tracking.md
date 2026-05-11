# Stage 4 QB Professional Tracking — Context, Research, and Open Questions

**Written:** 2026-05-11  
**Purpose:** Brief Gemini and Codex on the full context for Stage 4 before any implementation work begins. This document is a planning input, not an execution plan. No code should be written until the open questions at the end are resolved with David.

---

## 1. What We Have Built So Far

### Dynasty Genius in brief
A personal dynasty fantasy football decision system for one user (David) in a Superflex PPR league. The system produces continuous valuations for every relevant NFL player (QB/RB/WR/TE), separating the signal into layers: model-predicted production, market context, roster fit, counterarguments, and missing-data flags. It never collapses these into a single mystery number.

### Engine A — Rookie / Pre-NFL Forecast (current)
Engine A predicts NFL dynasty value (`y24_ppg` — average PPG over years 2-4) from pre-NFL signals only. Features may only be derived from college data and draft events. NFL performance data of any kind is a leakage defect in Engine A.

**Current Engine A feature matrix:**
- All positions: `pick`, `round`, `age`
- WR/TE: `dominator_rating`, `receiving_yards_share`
- RB: `dominator_rating`
- QB: `completion_pct`, `yards_per_attempt`, `td_int_ratio`, `sack_rate`, `all_purpose_yards`, `passing_yards_share`, `ppa`, `wepa`, `rushing_yards`, `rushing_tds`
  - Note: QB college features are registered in the contract but **NOT promoted to model inputs** — backtest FAIL (0/3 metrics, see below).

**QB college feature backtest result (2026-05-11):**
- Model A (pick/round/age): RMSE 6.699, R² -1.043, Spearman 0.289
- Model B (+10 QB CFBD college features): RMSE 9.066, R² -2.741, Spearman 0.146
- Result: FAIL (0/3). QB scores today on pick/round/age only.
- Key data quality issue: sack_rate and passing_yards_share had 125/126 nulls due to team stats endpoint name mismatch (college_team fix now applied; backtest not yet re-run).

**What is delivered and merged (PR #17):**
- `src/dynasty_genius/adapters/cfbd_qb_adapter.py` — CFBD QB adapter (10 features via httpx)
- `resources/cfbd_qb_id_map.json` — 126 QB ID map, 95.2% combined coverage
- `tests/test_cfbd_qb_adapter.py` — 16 passing tests + 2 skipped integration tests
- `docs/validation/qb_cfbd_backtest_report.md` — full gate report

---

## 2. The QB Research Framework (Approved 2026-05-11)

This is David's approved analytical framework for QB valuation. It is the intellectual foundation that Stage 4 should eventually operationalize.

### Draft Capital (the dominant signal)
- R1/R2 picks: 70% weight
- R3 picks: 50% weight
- R4-7 picks: 30% weight
- Draft capital already captures most predictive signal in the pre-NFL era (Engine A).

### Bifurcated Aging Curves
- Pocket passers: career cliff at age 33
- Dual-threat QBs: career cliff at age 29 (rushing attrition accelerates decline)
- Display as context warnings in the UI only — not model law per the product constitution.

### The Konami Code (Rushing Value)
- Rushing yards is the stickiest QB stat across college-to-pro transitions: R²=0.5674
- Rushing ability is explicitly valued in the dynasty context — dual-threat QBs carry a durable floor.

### Categorical Bust Filters (display-only, not model inputs)
- **P2S% threshold**: passing yards share in college; low P2S% is a bust signal
- **TD/INT ratio threshold**: below 0.7 → bust flag
- **All-purpose yards flag**: above 3,700 yards in final college season → upside flag
- These are display annotations, not features that enter the model.

### Professional Tracking Metrics (Stage 4 scope)
These metrics belong to the active-NFL era. They are **Engine B features**, not Engine A.
- **EPA (Expected Points Added)**: per-dropback efficiency, neutralizes volume bias
- **CPOE (Completion Percentage Over Expectation)**: accuracy above/below air-yards-adjusted expectation, removes easy-completion bias
- **DAKOTA**: composite passing efficiency metric (EPA/play + CPOE hybrid), R²≈0.72 vs. future performance across multiple seasons; the most predictive single QB efficiency metric in the literature

These three metrics are how the research framework distinguishes elite-but-undervalued QBs from high-volume-but-inefficient QBs — the core of the professional tracking layer.

---

## 3. The Architecture Boundary: Engine A vs. Engine B

This is the most important question Stage 4 must answer before any implementation begins.

### The Hard Rule (from system-design.md)
> "Engines are separate. Their feature pipelines do not share columns. A pre-NFL feature leaking into Engine B's training is a leakage defect."

Engine A inputs: **pre-NFL only** — draft capital, age at entry, college stats.  
Engine B inputs: **active NFL only** — usage, efficiency, multi-year production trends, age curve state, team context. No rookie pre-NFL features.

### Where EPA/CPOE/DAKOTA sit
EPA, CPOE, and DAKOTA are derived from NFL play-by-play data. They are unambiguously Engine B features. A QB with 1 NFL season has 1 year of EPA data. A QB with 0 NFL seasons has none. These metrics cannot be backfilled from college data.

### The implication for "Stage 4"
If Stage 4 = "add EPA/CPOE/DAKOTA to QB valuation," then Stage 4 is not an enrichment extension of Engine A. It is the beginning of **Engine B** — a fundamentally different model with a different training set, different outcome variable, and a different feature pipeline.

The agent-execution-plan.md defines Engine B as **Phase 6**, which requires:
- Phase 4 (Engine A feature expansion) closed — partially done
- Phase 5 (fitted aging curves) closed — not started

**Engine B is not the next sprint. It is 2-3 phases away per the formal roadmap.**

---

## 4. What nflreadpy Provides

nflreadpy (v0.1.5, installed, nflverse successor to nfl_data_py) exposes:

| Function | Relevant for Stage 4? |
|---|---|
| `load_pbp(seasons)` | Yes — play-by-play contains raw `epa` column per play; CPOE must be derived or aggregated |
| `load_player_stats(seasons)` | Yes — season-level passing stats (attempts, yards, TDs, INTs); may include EPA aggregates |
| `load_pfr_advstats(seasons)` | Yes — PFR advanced stats (DAKOTA lives here in some nflverse versions) |
| `load_nextgen_stats(seasons)` | Maybe — NGS aggressiveness, air yards; less relevant for efficiency |
| `load_ftn_charting(seasons)` | Maybe — FTN charting data; useful for sack context |
| `load_rosters(seasons)` | Yes — player identity resolution (gsis_id, position) |
| `load_draft_picks(seasons)` | Already in use via Engine A |

**Key data characteristics:**
- nflreadpy returns Polars DataFrames (not pandas). Pipeline code must handle this.
- PBP data is large (~250MB+ per season). Season-level aggregation should happen at load time, not in memory.
- CPOE is a play-level field in PBP; must be averaged per QB per season (weighted by dropbacks).
- DAKOTA is not a native nflreadpy column — it must be derived: approximately `(EPA/dropback × 0.7) + (CPOE × 0.3)` normalized. Exact formula varies by publication; the Ben Baldwin / nflfastR formulation is the reference.
- Source registry key is `"nfl_data_py"` (unchanged from nfl_data_py migration; `role = model_input`).

---

## 5. Data Availability and Training Set Constraints

For Engine B QB modeling, the training set would be:
- Active NFL QBs with ≥ 1 full season of NFL play-by-play data
- Outcome variable: something forward-looking (e.g., next-season PPG, or 2-year average PPG after year T)
- Feature year T → outcome year T+1 (no leakage)

**Population constraint:** Engine A trains on 125 QBs (draft classes 2015–2023, outcome-window closed). Engine B would need a different cohort — all QBs with sufficient NFL snaps across seasons covered by nflreadpy PBP (1999–2025). This is a larger population but a different modeling challenge (predicting continuation vs. predicting emergence).

**Outcome variable is unresolved:** `y24_ppg` (Engine A's outcome) is a rookie-era production measure. Engine B needs a different target. Options:
1. Next-season fantasy PPG (simple, but noisy)
2. Next-2-year average PPG (reduces noise, delays signal)
3. Age-curve-adjusted expected production (requires fitted curves — Phase 5)

---

## 6. Open Questions — Require David's Decision Before Any Code

These must be answered before Gemini or Codex can be given an implementation prompt.

### Q1: Is Stage 4 Engine B, or a display-only layer?

**Option A — Engine B (full model):** Build a separate Ridge model trained on NFL EPA/CPOE data. Predicts future QB production for active players. This is Phase 6 per the roadmap. Requires Phase 5 (aging curves) first. 3-5 agent sessions minimum.

**Option B — Display annotations only (no new model):** Fetch EPA/CPOE for every active QB from nflreadpy, store them as `context_signal` fields (not model inputs), and surface them as display cards on the rookie board and roster auditor. No new model training. No backtest required. 1 agent session. This is the path of least resistance and highest near-term product value.

**Option C — Hybrid:** Build the data pipeline and display layer now (Option B), explicitly designing the schema to be promotable to Engine B features later. Defers model training until aging curves exist.

**Recommendation from architecture:** Option C. The display layer is the highest-value near-term deliverable. David can see live EPA/CPOE for every QB on his roster and every prospect immediately. The Engine B model can be trained once aging curves exist.

---

### Q2: What is the outcome variable for Engine B QB?

If we go Option A or C (eventually train a model), what are we predicting?
- Next-season PPG?
- 2-year average PPG?
- Something age-adjusted?

This determines the training set structure and cannot be changed once training begins without starting over.

---

### Q3: Which QBs does Stage 4 cover?

- Only QBs already on David's roster?
- All active QBs with ≥ 1 NFL season?
- All QBs in the training data with NFL play time?

The answer determines data volume, fetch time, and API call budget.

---

### Q4: Polars vs. Pandas

nflreadpy returns Polars DataFrames. The rest of the codebase uses pandas. Options:
- Convert at the boundary (`.to_pandas()` immediately after load) — simplest, some memory overhead
- Adopt Polars for the new pipeline — cleaner long-term but diverges from existing code style

---

### Q5: Should the QB college backtest be re-run with the college_team fix?

The Codex fix (college_team param) should significantly reduce nulls on sack_rate and passing_yards_share. Re-running the backtest might produce different results. It might still fail, or it might pass 1-2 metrics. The question is whether this is worth David's time and API calls before committing to Stage 4 architecture.

---

## 7. What Gemini and Codex Should NOT Do Until Q1 Is Answered

- Do not write any Engine B training code
- Do not add EPA/CPOE to `POSITION_FEATURE_MATRIX` — they are not Engine A features
- Do not modify `engine_a_contract.py` for EPA/CPOE
- Do not build a training pipeline before the outcome variable is defined
- Do not assume nflreadpy returns pandas DataFrames

---

## 8. Suggested Delegation Once Q1 Is Resolved

**If Option B or C (display layer first):**

Codex task: Build `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`
- `fetch_qb_nfl_stats(gsis_id, seasons) -> dict` returning EPA/dropback, CPOE, DAKOTA, dropback_count, pass_att
- Source key: `"nfl_data_py"` (existing registry entry, `model_input` role — but these features will be tagged `context_signal` in the QB position matrix until Engine B promotion)
- TDD: write tests first; mock nflreadpy load functions; test None semantics (no snaps → None, not 0.0)
- Register new context columns in `engine_a_contract.py` under `PLAYERPROFILER_CONTEXT_COLUMNS` or a new `NFL_CONTEXT_COLUMNS` set

Gemini task: Build the QB identity bridge — map `pfr_player_name` / gsis_id between Engine A training data and nflreadpy roster data. Produce `resources/nflreadpy_qb_id_map.json` with coverage stats. Gate: ≥80% combined coverage on active/recent QBs.

**If Option A (full Engine B):**
This requires a separate planning session. Do not delegate to Codex or Gemini until Phase 5 (aging curves) scope is defined.
