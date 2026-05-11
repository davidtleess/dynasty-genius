# Data Source Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Govern every data source Dynasty Genius may ever touch in a machine-readable registry, stabilize CFBD as the auditable Engine A backbone, gate PlayerProfiler at a real-data decision point, run a CFBD-only backtest before adding more features, and define governed intake paths for RAS, market-overlay, Engine B, and manual-export sources.

**Architecture:** This is a roadmap across eight tasks, not one sequential execution plan. The first executable unit is Tasks 1, 3, and 4 (Source Registry + PlayerProfiler Decision Gate + CFBD-Only Backtest). Tasks 2, 5, 6, 7, and 8 are subsequent phases that unlock after the first unit's gates pass and the PP gate resolves honestly. Sources are classified into six roles — `model_input`, `training_label`, `context_signal`, `market_overlay`, `prohibited_current_phase`, and `prohibited` — and only `model_input` rows may reach Engine A or Engine B as training features. `training_label` sources contribute outcome labels used as prediction targets — labels are never model inputs. The existing adapter interface in `docs/data-source-contracts.md` and the leakage contract in `src/dynasty_genius/models/engine_a_contract.py` are the foundation — this plan extends them, never replaces them. All enrichment pipelines continue to write intermediate artifacts as partial CSVs under `app/data/training/`; the final `prospects_with_outcomes_v2.csv` is only written after all tasks pass their gates.

**Tech Stack:** Python 3.11+, Pandas, `httpx` (CFBD and FantasyCalc — the `cfbd` PyPI package is not used), `nfl_data_py`, `beautifulsoup4` (RAS scraper), `python-dotenv`, `pytest`, `scikit-learn` (backtest metrics), CSV for manual exports, `requests` (Sleeper, FantasyCalc).

**Governance references read before any implementation:**
- `docs/governance/00-product-constitution.md` (authority: analytical)
- `docs/governance/01-north-star-architecture.md` (authority: technical)
- `docs/data-source-contracts.md` (adapter interface contract — do not contradict)
- `src/dynasty_genius/models/engine_a_contract.py` (PROHIBITED_COLUMNS, LEAKAGE_REGEX)

---

## Task 1: Source Registry

**Goal:** Create a machine-readable Python registry that classifies every data source by role, allowed fields, prohibited fields, provenance requirements, cache policy, freshness expectations, failure behavior, and test gate. Tests assert that no `market_overlay` or `prohibited` source appears in any model feature list.

**Files:**
- Create: `src/dynasty_genius/sources/source_registry.py`
- Create: `tests/test_source_registry.py`
- Modify: `src/dynasty_genius/models/engine_a_contract.py` (add `SOURCE_REGISTRY` reference constant — one line)

**Source Role Definitions:**

| Role | Meaning |
|------|---------|
| `model_input` | Allowed as Engine A or Engine B training feature. Must carry `source_` provenance sibling. |
| `training_label` | Contributes outcome labels used as the prediction target (e.g., `y24_ppg`). Labels are never model inputs — a source with `training_label` role must not supply any column to the feature matrix. |
| `context_signal` | Surfaces in decision UI, validation docs, or caveat flags only. Never a model input by any path. |
| `market_overlay` | Price/rank discovery only. Never enters Engine A or Engine B by constitution, regardless of feature name. |
| `prohibited_current_phase` | Blocked for cost, licensing, or authorization reasons — not analytical impurity. Requires David's explicit approval before any pipeline access. |
| `prohibited` | Cannot enter any pipeline layer under any circumstances. |

**Registry entries to define (one `SourceDefinition` per source):**

| Source | Roles | Failure behavior |
|--------|-------|-----------------|
| `nfl_data_py` | `model_input`, `training_label` | `use_cached` — stale up to 7 days; emit `is_stale=True` |
| `cfbd` | `model_input` | `skip_enrichment` — null fill; emit `completeness_flags` |
| `playerprofiler` | DECISION GATE — see Task 3 | `skip_enrichment` until gate resolves |
| `ras` | `context_signal` | `skip_enrichment` — no positive model boost |
| `pff` | `context_signal` | `skip_enrichment` — manual CSV path only in this phase |
| `rotoviz` | `context_signal` | `skip_enrichment` — manual CSV path only |
| `campus2canton` | `context_signal` | `skip_enrichment` — CSV export only |
| `fantasycalc` | `market_overlay` | `use_cached` — stale up to 24 hours |
| `dynasty_data_lab` | `market_overlay` | `skip_enrichment` — deferred until market comparison UI exists |
| `dynasty_nerds` | `market_overlay` | `skip_enrichment` — expert consensus, deferred |
| `ktc` | `market_overlay` | `skip_enrichment` — ToS scraping risk; FantasyCalc is primary |
| `sleeper` | `context_signal` | `skip_enrichment` — league state only, never model input |
| `sportradar` | `prohibited_current_phase` | Error on any attempt to use; requires David approval |
| `genius_sports` | `prohibited_current_phase` | Error on any attempt to use; requires David approval |
| `stats_perform` | `prohibited_current_phase` | Error on any attempt to use; requires David approval |
| `rolling_insights` | `prohibited_current_phase` | Error on any attempt to use; requires David approval |

**Rationale for enterprise phase prohibition:** Sportradar, Genius Sports, Stats Perform, and Rolling Insights are blocked for cost and licensing reasons — not because their data is analytically impure. Each carries enterprise pricing ($4,200–$7,200+/year), which is not justified for a personal tool when `nfl_data_py` (nflverse) provides equivalent ground-truth metrics for free. These sources are `prohibited_current_phase`, not `prohibited` permanently — David may authorize access in a future phase with an explicit plan amendment.

**Registry data structure (illustrative — full implementation in source file):**

```python
from dataclasses import dataclass, field
from typing import Literal

SourceRole = Literal["model_input", "training_label", "context_signal", "market_overlay", "prohibited_current_phase", "prohibited"]
FailureBehavior = Literal["fail_closed", "skip_enrichment", "use_cached"]

@dataclass(frozen=True)
class SourceDefinition:
    name: str
    roles: frozenset[SourceRole]
    allowed_fields: tuple[str, ...]        # empty = no restriction within role
    prohibited_fields: tuple[str, ...]     # always excluded regardless of role
    provenance_required: bool              # True = every field needs source_ sibling
    cache_policy: str                      # "json_cache" | "parquet_snapshot" | "csv_fixture" | "none"
    freshness_hours: int | None            # None = static / manual
    failure_behavior: FailureBehavior
    test_gate: str                         # pytest node path for gate test
    notes: str = ""
```

- [ ] **Step 1: Write registry test stubs**

  Create `tests/test_source_registry.py`. Write failing tests for:
  - Every `market_overlay` or `prohibited` source has no field intersection with `ALLOWED_ENRICHMENT_COLUMNS` from `engine_a_contract.py`.
  - Every `model_input` source sets `provenance_required=True`.
  - No source named `sportradar`, `genius_sports`, `stats_perform`, or `rolling_insights` has any role other than `prohibited`.
  - Every source definition has a `test_gate` pointing to an existing test file path.

  Run: `.venv/bin/python -m pytest tests/test_source_registry.py -q`
  Expected: import errors / missing definitions — all fail.

- [ ] **Step 2: Implement `source_registry.py` with all 16 entries**

  Define `SourceDefinition` dataclass and `SOURCE_REGISTRY: dict[str, SourceDefinition]`. Populate all 16 sources from the table above. Import `ALLOWED_ENRICHMENT_COLUMNS` and `PROHIBITED_COLUMNS` from `engine_a_contract.py` to cross-check `prohibited_fields` at module load time — raise `ValueError` at import if a `model_input` source lists a field that is in `PROHIBITED_COLUMNS`.

- [ ] **Step 3: Run registry tests to green**

  Run: `.venv/bin/python -m pytest tests/test_source_registry.py -q`
  Expected: all pass.

- [ ] **Step 4: Run existing leakage tests to confirm nothing broke**

  Run: `.venv/bin/python -m pytest tests/test_leakage_scanner.py tests/test_engine_a_v2_feature_contract.py -q`
  Expected: leakage 3/3 passed; feature contract 6 passed 9 skipped.

- [ ] **Step 5: Commit**

  ```bash
  git add src/dynasty_genius/sources/source_registry.py tests/test_source_registry.py
  git commit -m "feat: machine-readable source registry with role/leakage/failure classification"
  ```

---

## Task 2: CFBD Stabilization

**Goal:** Extract the CFBD client from `scripts/enrich_training_data.py` into a reusable adapter, lock the formula version for `dominator_rating` and `receiving_yards_share`, document the raw cache and replay behavior, and add a regression test that verifies row-count preservation and formula output are stable across re-runs.

**Context:** The current implementation uses `httpx` directly against the CFBD REST API v2. The `cfbd` PyPI library is explicitly not used — it was removed from `requirements.txt` in commit `e14dfd7`. The Patreon Tier 3 subscription ($10/month) unlocks 75,000 monthly calls; the free tier (1,000/month) is sufficient for dev but not production enrichment.

**Files:**
- Create: `src/dynasty_genius/sources/adapters/cfbd_adapter.py`
- Modify: `scripts/enrich_training_data.py` (import from adapter; remove duplicate code)
- Create: `tests/fixtures/cfbd/` (checked-in fixture responses for replay tests)
- Create: `tests/test_cfbd_adapter.py`
- Create: `docs/data-sources/cfbd-formula-spec.md`

**Formula contract (lock these; any change requires a plan amendment):**

```
dominator_rating (WR/TE) = (receiving_yards_share + receiving_td_share) / 2
    where receiving_yards_share = player_rec_yds / team_net_passing_yards
          receiving_td_share    = player_rec_tds  / team_passing_tds  (0 if team_passing_tds == 0)

dominator_rating (RB) = (rushing_yards_share + rushing_td_share) / 2
    where rushing_yards_share = player_rush_yds / team_rushing_yards
          rushing_td_share    = player_rush_tds / team_rushing_tds  (0 if team_rushing_tds == 0)

receiving_yards_share (WR/TE only) = player_rec_yds / team_net_passing_yards

All values: float in [0, 1]. Null if team denominator is 0 or API returns no data.
source_dominator_rating = "cfbd"
source_receiving_yards_share = "cfbd"
```

**CFBD API endpoints used:**
- `/stats/season?year=<year>&team=<team>` — team-level season totals
- `/stats/player/season?year=<year>&team=<team>&category=receiving` — individual receiving stats
- `/stats/player/season?year=<year>&team=<team>&category=rushing` — individual rushing stats

**Cache policy:**
- File: `app/data/cache/cfbd_cache.json` (gitignored, key = `{endpoint}_{sorted_params_json}`)
- Replay: tests use `tests/fixtures/cfbd/<team>_<year>.json` checked into repo — never call the live API in tests
- TTL: 30 days for historical seasons (year < current_year - 1); 24 hours for the most recent completed season

- [ ] **Step 1: Write fixture files for 3 representative teams**

  Create `tests/fixtures/cfbd/alabama_2022_receiving.json`, `tests/fixtures/cfbd/alabama_2022_rushing.json`, `tests/fixtures/cfbd/alabama_2022_season.json`. Use a real known player (e.g., Jermaine Burton) to verify formula output can be hand-checked. Commit fixtures.

- [ ] **Step 2: Write adapter tests against fixtures**

  Create `tests/test_cfbd_adapter.py`. Write tests that:
  - Instantiate `CFBDAdapter` with the fixture directory (no network calls).
  - Assert `dominator_rating` for Jermaine Burton (WR, Alabama, 2022) matches the hand-calculated expected value ± 0.001.
  - Assert `source_dominator_rating == "cfbd"`.
  - Assert that a player with no matching stats row gets `dominator_rating=None`.
  - Assert that a team with `team_net_passing_yards=0` gets `dominator_rating=None` (no ZeroDivisionError).

  Run: `.venv/bin/python -m pytest tests/test_cfbd_adapter.py -q`
  Expected: all fail (adapter not yet extracted).

- [ ] **Step 3: Extract `CFBDAsyncClient` into `cfbd_adapter.py`**

  Move `CFBDAsyncClient`, `_map_team_name`, `process_group`, and `enrich_with_cfbd` from `scripts/enrich_training_data.py` into `src/dynasty_genius/sources/adapters/cfbd_adapter.py`. Add `FORMULA_VERSION = "1.0"` constant at the top of the file. Update `scripts/enrich_training_data.py` to `from src.dynasty_genius.sources.adapters.cfbd_adapter import CFBDAsyncClient, enrich_with_cfbd`.

- [ ] **Step 4: Write the formula spec doc**

  Create `docs/data-sources/cfbd-formula-spec.md`. Document the exact formula, API endpoints, team name mapping table, cache key format, TTL policy, and the `FORMULA_VERSION` string. State explicitly that the `cfbd` PyPI library is not used. One paragraph on failure behavior: if CFBD API is unreachable, the column is null-filled and `completeness_flags` includes `cfbd_unreachable`.

- [ ] **Step 5: Run full test suite**

  Run: `.venv/bin/python -m pytest tests/test_cfbd_adapter.py tests/test_leakage_scanner.py tests/test_engine_a_v2_feature_contract.py -q`
  Expected: all adapter tests pass; feature contract 6 passed 9 skipped.

- [ ] **Step 6: Commit**

  ```bash
  git add src/dynasty_genius/sources/adapters/cfbd_adapter.py \
          tests/test_cfbd_adapter.py tests/fixtures/cfbd/ \
          docs/data-sources/cfbd-formula-spec.md \
          scripts/enrich_training_data.py
  git commit -m "refactor: extract CFBDAsyncClient to adapter; lock formula v1.0 with fixture replay tests"
  ```

---

## Task 3: PlayerProfiler Decision Gate

**Goal:** Explicitly resolve whether PlayerProfiler can provide real, non-null enrichment coverage ≥80% for the Engine A training set. The current state is: `app/data/cache/pp_stats_cache.json` is empty; `target_share`, `breakout_age`, `speed_score`, and `yprr` are all null in the partial artifact. This is not accepted as real PlayerProfiler enrichment. The outcome of this task is a binary decision, not a partial implementation.

**Background from research doc:** The shadow API endpoint is `POST https://www.playerprofiler.com/wp-admin/admin-ajax.php` with payload `{"action": "playerprofiler_api", "endpoint": "/player/<slug>"}`. The research doc treats this as a reliable pipeline. It is not proven for the Engine A training set — 874 historical prospects from 2000–2025, many of whom may not have PlayerProfiler pages.

**Files:**
- Create: `scripts/probe_playerprofiler.py` (one-time diagnostic; not part of the main pipeline)
- Create: `tests/test_playerprofiler_decision_gate.py`
- Modify: `src/dynasty_genius/sources/source_registry.py` (update PP role after gate resolves)
- Modify: `docs/agent-ledger/2026-05-10.md` (log the gate decision)

**The two resolution paths:**

**Path A — PP enrichment is viable:** The probe script returns non-null `target_share`, `breakout_age`, `speed_score` for ≥80% of 2015–2025 draft classes (the subset most likely to have PP pages). The adapter is implemented, coverage is verified, and the source registry updates PP to `model_input`.

**Path B — PP enrichment is not viable:** Coverage for pre-2015 classes is materially below 80%, or the shadow API endpoint returns empty/null for the majority of historical prospects. PlayerProfiler is downgraded to `context_signal` in the source registry. Its fields — `target_share`, `breakout_age`, `speed_score` — are removed from the Engine A model input set and reclassified as deferred context signals. They do not get imputed-median values and do not appear as model features; median-imputing fields with ≥20% structural missingness treats fabricated values as evidence, which violates the constitution's "truth over convenience" tenet. The `yprr` field has a separate path: if college YPRR can be computed from nflverse route participation data for NFL classes (2019+), that sourcing may be documented separately; otherwise `yprr` is also deferred. Log the decision and coverage numbers in the ledger. Update `ALLOWED_ENRICHMENT_COLUMNS` to remove any PP-only fields that cannot be sourced from a verified, non-null pipeline.

- [ ] **Step 1: Write the decision gate test (defines the acceptance criterion)**

  Create `tests/test_playerprofiler_decision_gate.py`. Write a pytest test `test_pp_coverage_gate` that:
  - Reads `app/data/cache/pp_stats_cache.json`.
  - If the file is empty or does not exist: `pytest.skip("PP probe not yet run")`.
  - Otherwise: asserts that ≥80% of the 2015–2025 draft class rows have non-null `target_share`.
  - Asserts that ≥80% of WR/TE rows have non-null `breakout_age`.

  This test is the gate. It must pass before PP is promoted to `model_input`.

- [ ] **Step 2: Write the probe script**

  Create `scripts/probe_playerprofiler.py`. The script:
  - Loads `app/data/training/prospects_with_outcomes.csv`.
  - Filters to seasons 2015–2025 (most likely to have PP pages).
  - For each player, derives the PP slug from `pfr_player_name` (lowercase, hyphens).
  - POSTs to `https://www.playerprofiler.com/wp-admin/admin-ajax.php` with the slug.
  - Parses the JSON response. Records: `pfr_player_name`, `position`, `season`, `pp_slug`, `target_share_raw`, `breakout_age_raw`, `speed_score_raw`, `status` (`found` | `not_found` | `parse_error`).
  - Writes results to `app/data/cache/pp_probe_results.json` and prints a summary: total attempted, found, not_found, parse_error, non-null pct for each target field.
  - Does NOT write to the training CSV. This is diagnostic only.

  Rate limit: 1 request per second, max 10 concurrent (use `asyncio.Semaphore(10)` with 1s sleep between batches of 10).

- [ ] **Step 3: Run the probe (David runs this — requires CFBD_API_KEY is not needed here, just network access)**

  ```bash
  .venv/bin/python scripts/probe_playerprofiler.py
  ```

  Expected output lines:
  ```
  Probed 500 players (seasons 2015–2025)
  found: N | not_found: N | parse_error: N
  target_share non-null: N% | breakout_age non-null: N% | speed_score non-null: N%
  ```

- [ ] **Step 4: Run the gate test against probe results**

  Run: `.venv/bin/python -m pytest tests/test_playerprofiler_decision_gate.py -v`

  **If PASS (≥80% coverage):** Proceed to implement the full PP adapter. Update source registry to `model_input`. The adapter follows the same pattern as `cfbd_adapter.py` — fixture replay tests required before any PR.

  **If FAIL (below 80% coverage):** Do not implement the PP adapter. Update source registry to `context_signal`. Remove `target_share`, `breakout_age`, and `speed_score` from `ALLOWED_ENRICHMENT_COLUMNS` in `engine_a_contract.py` — they are not usable model features if the only sourcing is fabricated imputation. Evaluate `yprr` separately: if it can be computed from nflverse for 2019+ NFL classes, document that path; otherwise defer it too. Log the decision and all coverage numbers in the ledger. Do not proceed to Task 4 (backtest) with phantom PP fields in the feature set.

- [ ] **Step 5: Log the gate decision in the daily ledger**

  Append to `docs/agent-ledger/2026-05-10.md`:
  - Gate outcome (Path A or Path B)
  - Coverage numbers from probe
  - Updated source registry role for PP
  - Next step

- [ ] **Step 6: Commit**

  ```bash
  git add scripts/probe_playerprofiler.py tests/test_playerprofiler_decision_gate.py \
          src/dynasty_genius/sources/source_registry.py docs/agent-ledger/2026-05-10.md
  git commit -m "feat: PlayerProfiler decision gate — probe script and coverage test"
  ```

---

## Task 4: Engine A v2 CFBD-Only Backtest

**Goal:** Before adding any more features, compare the current model (pick + round + age only) against the pick + round + age + CFBD production features model on the held-out validation set. Report RMSE, R², Spearman rank correlation, and calibration by position. No grade promotion until CFBD features show measurable improvement.

**Context:** The baseline Engine A model was trained on `prospects_with_outcomes.csv` using draft capital and age only. The CFBD partial artifact (`prospects_with_outcomes_cfbd_partial.csv`) adds `dominator_rating` and `receiving_yards_share` for 85.6% of WR/RB/TE rows. This task establishes whether those features improve predictions before Task 5 and Task 6 add more sources.

**Files:**
- Create: `scripts/backtest_engine_a_cfbd_only.py`
- Create: `docs/validation/engine_a_v2_cfbd_backtest_report.md` (template populated by the script)
- Create: `tests/test_engine_a_backtest.py`

**Train/held-out split rule:** Use `is_training == True` rows for training, `is_training == False` rows for held-out evaluation. This column already exists in `engine_a_contract.py`'s `BASELINE_COLUMNS`. Do not resplit — the existing split is the governed evaluation surface.

**Outcome metric:** `y24_ppg` (Years 2–4 PPG) from the baseline CSV. This is the training label; it is never used as a model input feature.

**Features for Model A (baseline):** `pick`, `round`, `age`

**Features for Model B (CFBD-enriched):** `pick`, `round`, `age`, `dominator_rating`, `receiving_yards_share`

Position-specific runs: evaluate WR, RB, TE separately in addition to the combined run.

**Acceptance criterion for promotion:** Model B must show improvement on at least two of: RMSE reduction ≥ 5%, R² improvement ≥ 0.02, Spearman ρ improvement ≥ 0.03 — on the held-out set for at least two positions. If it does not, CFBD features remain in the pipeline but the backtest report documents why grade promotion is not warranted yet.

**Backtest report fields (written by the script):**
```
baseline_model: pick + round + age
enriched_model: pick + round + age + dominator_rating + receiving_yards_share
held_out_n: <int>
metric_delta_rmse_combined: <float>
metric_delta_r2_combined: <float>
metric_delta_spearman_combined: <float>
by_position:
  WR: {rmse_baseline, rmse_enriched, r2_baseline, r2_enriched, spearman_baseline, spearman_enriched}
  RB: ...
  TE: ...
cfbd_coverage_pct_wr: <float>
cfbd_coverage_pct_rb: <float>
cfbd_coverage_pct_te: <float>
promotion_warranted: true | false
promotion_reason: <string>
```

- [ ] **Step 1: Write backtest test**

  Create `tests/test_engine_a_backtest.py`. Write tests that:
  - Assert the report file exists and is valid YAML/JSON after the script runs.
  - Assert `held_out_n >= 100` (the held-out set must be large enough to be meaningful).
  - Assert that `metric_delta_rmse_combined` is a finite float (not NaN).
  - Assert that `promotion_warranted` is a boolean.
  - Do NOT assert that CFBD improves the model — the test only asserts the report is well-formed.

  Run: `.venv/bin/python -m pytest tests/test_engine_a_backtest.py -q`
  Expected: fail (script not yet written).

- [ ] **Step 2: Write the backtest script**

  Create `scripts/backtest_engine_a_cfbd_only.py`. The script:
  - Loads `prospects_with_outcomes.csv` (baseline) and left-joins with `prospects_with_outcomes_cfbd_partial.csv` on `gsis_id`.
  - Splits into train/held-out using `is_training`.
  - Trains a `sklearn.linear_model.Ridge` model (α=1.0) for Model A and Model B using only the columns listed above.
  - For rows where `dominator_rating` is null (14.4%), imputes with position-group median computed on the training set only. Records the imputation count.
  - Computes RMSE, R², and Spearman ρ for each model on the held-out set — overall and by position.
  - Evaluates the promotion criterion.
  - Writes `docs/validation/engine_a_v2_cfbd_backtest_report.md` in Markdown with a YAML front-matter block containing the numeric results.
  - Prints a 10-line summary to stdout.
  - Raises `SystemExit(1)` if the held-out set has fewer than 50 rows — abort rather than report on an insufficient sample.

  The script is read-only with respect to training data. It never writes back to any CSV used as model input.

- [ ] **Step 3: Run the backtest**

  ```bash
  .venv/bin/python scripts/backtest_engine_a_cfbd_only.py
  ```

  Inspect the stdout summary and `docs/validation/engine_a_v2_cfbd_backtest_report.md`.

- [ ] **Step 4: Run backtest tests**

  Run: `.venv/bin/python -m pytest tests/test_engine_a_backtest.py -q`
  Expected: all pass.

- [ ] **Step 5: Log promotion decision in ledger**

  Append to `docs/agent-ledger/YYYY-MM-DD.md` the promotion outcome: whether CFBD features are validated for grade promotion, the key metrics, and what happens next. If promotion is not warranted, state explicitly what improvement would be needed.

- [ ] **Step 6: Commit**

  ```bash
  git add scripts/backtest_engine_a_cfbd_only.py tests/test_engine_a_backtest.py \
          docs/validation/engine_a_v2_cfbd_backtest_report.md
  git commit -m "feat: Engine A v2 CFBD-only backtest — baseline vs enriched model comparison"
  ```

---

## Task 5: RAS Athletic Risk Layer

**Goal:** Ingest RAS scores from ras.football as a `context_signal` risk layer. Surface two boolean flags: `low_ras_risk_flag` (RAS < 4.0) and `missing_athletic_profile` (no RAS record found). Provide `source_ras_score` provenance. Do not add a continuous RAS score to Engine A features unless and until the Task 4 backtest proves positive lift for a specific position.

**Why flags, not scores:** The constitution locks RAS as a risk/context signal. High RAS does not mechanically increase dynasty value score unless backtesting proves positive predictive lift. A boolean floor-risk flag is strictly additive risk context; it cannot inflate a score.

**Data source:** ras.football HTML tables, scraped via `beautifulsoup4` or `pandas.read_html`. The creator encourages use for analytical projects. No API key required. A static Parquet file from the nflverse/GitHub community may be used as the primary source with the live site as fallback.

**Files:**
- Create: `src/dynasty_genius/sources/adapters/ras_adapter.py`
- Create: `tests/fixtures/ras/ras_sample.html` (checked-in HTML fixture for replay tests)
- Create: `tests/test_ras_adapter.py`
- Modify: `scripts/enrich_training_data.py` (add RAS enrichment step before final leakage check)
- Modify: `src/dynasty_genius/models/engine_a_contract.py` (add `low_ras_risk_flag`, `missing_athletic_profile`, `source_ras_score` to `ALLOWED_ENRICHMENT_COLUMNS`)

**Fields produced:**

| Column | Type | Values | Source tag |
|--------|------|---------|-----------|
| `low_ras_risk_flag` | bool | True if RAS record exists AND RAS < 4.0 | `source_ras_score = "ras.football"` |
| `missing_athletic_profile` | bool | True if no RAS record found for this player | `source_ras_score = "missing"` |
| `source_ras_score` | string | `"ras.football"` or `"missing"` | — |

**Missingness semantics:** `missing_athletic_profile=True` is a caveat — it surfaces in the decision UI as "athletic profile not available" and may inform qualitative review. It does not automatically set `low_ras_risk_flag=True`. Unknown athletic profile is not evidence of low athleticism; conflating the two would overstate uncertainty as a negative signal. Decision surfaces should distinguish between "confirmed floor risk" (low RAS known) and "no data" (profile unavailable).

**Lookup key:** `pfr_player_name` + `position` + `draft_year`. RAS records are keyed by player name and draft year.

- [ ] **Step 1: Add RAS columns to `engine_a_contract.py`**

  Add to `ALLOWED_ENRICHMENT_COLUMNS`:
  ```python
  "low_ras_risk_flag",
  "missing_athletic_profile",
  "source_ras_score",
  ```

  Run: `.venv/bin/python -m pytest tests/test_leakage_scanner.py tests/test_engine_a_v2_feature_contract.py -q`
  Expected: all still pass (adding allowed columns doesn't break anything).

- [ ] **Step 2: Create HTML fixture and write adapter tests**

  Download a single RAS leaderboard page (e.g., 2022 WR class) and save as `tests/fixtures/ras/ras_sample.html`. Write `tests/test_ras_adapter.py` asserting:
  - `RASAdapter.parse(fixture_html)` returns a `dict[str, float]` keyed by `"{name}_{position}_{year}"`.
  - A known player from the 2022 WR class has a RAS score within 0.01 of the published value.
  - A player not in the table returns `None` (not a `KeyError`).
  - `RASAdapter.to_flags(ras_score=3.5)` returns `(low_ras_risk_flag=True, missing_athletic_profile=False)`.
  - `RASAdapter.to_flags(ras_score=None)` returns `(low_ras_risk_flag=False, missing_athletic_profile=True)` — missing profile is a caveat, not a confirmed low-RAS signal.
  - `RASAdapter.to_flags(ras_score=8.2)` returns `(low_ras_risk_flag=False, missing_athletic_profile=False)`.

  Run: `.venv/bin/python -m pytest tests/test_ras_adapter.py -q`
  Expected: all fail (adapter not yet implemented).

- [ ] **Step 3: Implement `RASAdapter`**

  Implement `ras_adapter.py` with:
  - `parse(html_content: str) -> dict[str, float | None]` — parse HTML tables using `pd.read_html` or `BeautifulSoup`.
  - `to_flags(ras_score: float | None) -> tuple[bool, bool]` — returns `(low_ras_risk_flag, missing_athletic_profile)`.
  - `enrich_dataframe(df: pd.DataFrame, ras_lookup: dict) -> pd.DataFrame` — left-join on the lookup key; populate the three flag columns.
  - The adapter never writes to `app/data/cache/` — it reads from the lookup dict passed in by the pipeline.

- [ ] **Step 4: Integrate into `enrich_training_data.py`**

  In `main()`, add a RAS enrichment step between the CFBD enrichment and the final leakage check:
  ```python
  ras_lookup = load_ras_lookup()   # reads from app/data/cache/ras_cache.json or fixture
  final_df = RASAdapter.enrich_dataframe(enriched_df, ras_lookup)
  ```

  The `load_ras_lookup()` function reads `app/data/cache/ras_cache.json` if it exists (pre-fetched), otherwise returns an empty dict (all players get `missing_athletic_profile=True`). It never makes a live network call inside `main()` — network calls happen in a separate `scripts/fetch_ras_data.py` step.

- [ ] **Step 5: Run adapter and contract tests**

  Run: `.venv/bin/python -m pytest tests/test_ras_adapter.py tests/test_engine_a_v2_feature_contract.py -q`
  Expected: all pass (RAS columns are now in allowed set; partial CSV test still gates on partial artifact).

- [ ] **Step 6: Commit**

  ```bash
  git add src/dynasty_genius/sources/adapters/ras_adapter.py \
          tests/test_ras_adapter.py tests/fixtures/ras/ \
          scripts/enrich_training_data.py \
          src/dynasty_genius/models/engine_a_contract.py
  git commit -m "feat: RAS risk layer — low_ras_risk_flag and missing_athletic_profile flags only; no model score boost"
  ```

---

## Task 6: Market Overlay Layer

**Goal:** Build a governed market overlay pipeline that ingests FantasyCalc (primary) and placeholders for Dynasty Data Lab and Dynasty Nerds. Hard-gate that no market field ever enters Engine A or Engine B training. KTC is explicitly deferred due to ToS scraping risk.

**Governance hard rule:** Market overlay data lives in a separate store (`app/data/market_overlay/`) and never joins the training CSV. Any test that detects a market column in the partial or final enriched artifact must fail. This is a second leakage wall in addition to the existing `check_leakage()` in the pipeline.

**Sources:**

| Source | Access | Endpoint | Cost |
|--------|--------|----------|------|
| FantasyCalc | Free JSON API | `https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=1&numTeams=12&ppr=1` | Free |
| Dynasty Data Lab | Paid API | Startup/rookie ADP endpoints | $4 per 1,000 requests — defer until market UI exists |
| Dynasty Nerds | Consumer app | No public API — expert CSV export | Subscription required — defer |
| KTC | Page scraping | JS variable `playerSuperflex` in page source | Deferred — ToS scraping risk; FantasyCalc is primary |

**Why KTC is deferred:** KTC's Terms and Conditions explicitly prohibit scraping player values and reproducing rankings. While community scripts exist, using them carries ToS violation risk. FantasyCalc's free API provides equivalent market signal from actual completed trades. KTC may be revisited if KTC provides an official API.

**Files:**
- Create: `src/dynasty_genius/sources/market_overlay.py`
- Create: `tests/test_market_overlay.py`
- Create: `tests/test_market_leakage_gate.py` (standalone hard gate test — runs in CI)
- Create: `app/data/market_overlay/.gitkeep` (directory exists but contents gitignored)
- Modify: `.gitignore` (add `app/data/market_overlay/*.json` and `app/data/market_overlay/*.csv`)

**FantasyCalc response fields to capture:**

```python
{
    "player_name": str,
    "position": str,
    "fantasycalc_value": int,       # market_overlay only
    "fantasycalc_rank": int,        # market_overlay only
    "trend_30d": int,               # market_overlay only
    "fetched_at": str,              # ISO timestamp
}
```

These fields are written to `app/data/market_overlay/fantasycalc_<YYYYMMDD>.json`. They are never joined to the training CSV or to the feature store.

- [ ] **Step 1: Write the hard leakage gate test**

  Create `tests/test_market_leakage_gate.py`. This test runs against:
  - `app/data/training/prospects_with_outcomes.csv` (baseline)
  - `app/data/training/prospects_with_outcomes_cfbd_partial.csv` (partial, if it exists)
  - Any `*.csv` file under `app/data/training/` matching `*_v2.csv` or `*_partial.csv`

  For each file that exists, assert that none of the column names match any of:
  ```python
  MARKET_COLUMN_PATTERNS = [
      r"^ktc_", r"^fantasycalc_", r"^dynastydatalab_",
      r"^dynastynerds_", r"_rank$", r"^market_", r"^overlay_"
  ]
  ```

  This is a never-skip test. It must pass on every commit regardless of which training artifacts are present.

  Run: `.venv/bin/python -m pytest tests/test_market_leakage_gate.py -q`
  Expected: pass (current training artifacts have no market columns).

- [ ] **Step 2: Write market overlay client tests**

  Create `tests/test_market_overlay.py`. Write tests using a mocked `httpx` response (no live API calls in tests):
  - `FantasyCalcClient.fetch()` returns a list of dicts with the fields above.
  - The response is written to `app/data/market_overlay/fantasycalc_<date>.json`.
  - `FantasyCalcClient.fetch()` raises `MarketOverlayFetchError` if the API returns non-200.
  - The output file never contains `gsis_id` or `pfr_player_name` — it is keyed by `player_name` only; identity resolution is out of scope for the overlay layer.

  Run: `.venv/bin/python -m pytest tests/test_market_overlay.py -q`
  Expected: fail (client not yet implemented).

- [ ] **Step 3: Implement `market_overlay.py`**

  Implement `FantasyCalcClient` with:
  - `fetch(num_qbs=1, num_teams=12, ppr=1) -> list[dict]` — GET request via `httpx`, 10s timeout, raise `MarketOverlayFetchError` on non-200.
  - `save(records: list[dict], output_dir: Path) -> Path` — write timestamped JSON; return the path.
  - A module-level `SOURCES_DEFERRED = {"ktc": "ToS scraping risk", "dynasty_data_lab": "no market UI yet", "dynasty_nerds": "no public API"}` dict documenting what is deferred and why.

  No Dynasty Data Lab or Dynasty Nerds implementation in this task — the stub dict is the documentation.

- [ ] **Step 4: Run all market tests**

  Run: `.venv/bin/python -m pytest tests/test_market_overlay.py tests/test_market_leakage_gate.py -q`
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/dynasty_genius/sources/market_overlay.py \
          tests/test_market_overlay.py tests/test_market_leakage_gate.py \
          app/data/market_overlay/.gitkeep .gitignore
  git commit -m "feat: governed market overlay layer — FantasyCalc client; KTC/DDL/DN deferred; hard leakage gate"
  ```

---

## Task 7: Engine B Source Plan

**Goal:** Define the governed feature set for Engine B (active-player scoring) using `nfl_data_py` as the primary source. Separate Engine B inputs from Engine A rookie inputs in code and tests. Plan the nflverse data joins needed to compute route participation, snap share, target share, YPRR/TPRR, EPA/CPOE, and Sleeper league context.

**Context:** `src/dynasty_genius/pipelines/engine_b_features.py` already exists (evidenced by `__pycache__`). This task governs and tests that file, not replaces it. Sleeper is `context_signal`, not model input — it provides David's roster state to the decision surface, not to the model.

**nflverse functions needed:**

| Metric | nfl_data_py function | Notes |
|--------|---------------------|-------|
| Route participation, YPRR | `import_pbp_data()` joined with `load_participation()` | FTN charting data; 2019+ seasons only |
| Snap counts | `import_snap_counts()` | Available 2012+ |
| Target share, air yards | `import_pbp_data()` | Filter `play_type == "pass"` |
| EPA/CPOE (QB) | `import_pbp_data()` | Fields: `qb_epa`, `cpoe` |
| Draft capital | `import_draft_picks()` | For identity matching |
| Injuries | `import_injuries()` | Weekly updates |
| Rosters / depth | `import_rosters()` | Weekly updates |

**YPRR calculation (Engine B):**

```
YPRR = receiving_yards / routes_run
routes_run = sum(route_participation == True for pass plays)
```

Note: This is NFL YPRR from nflverse participation data. This is different from college YPRR (not yet available for Engine A, pending PlayerProfiler gate resolution).

**Engine B contract file (new):**

```python
# src/dynasty_genius/models/engine_b_contract.py
ENGINE_B_INPUTS = {
    "WR": ["nfl_route_participation_rate", "nfl_target_share", "nfl_yprr", "nfl_air_yards_share", "nfl_snap_share"],
    "RB": ["nfl_snap_share", "nfl_target_share", "nfl_weighted_opportunity_rate", "nfl_yards_before_contact_avg"],
    "TE": ["nfl_route_participation_rate", "nfl_target_share", "nfl_yprr", "nfl_snap_share"],
    "QB": ["nfl_cpoe", "nfl_qb_epa_per_play", "nfl_rush_attempts_per_game"],
}
# All Engine B field names must carry the nfl_ prefix to prevent leakage test ambiguity
ENGINE_B_ONLY_FIELDS = {
    "nfl_cpoe", "nfl_qb_epa_per_play", "nfl_yprr", "nfl_target_share",
    "nfl_snap_share", "nfl_route_participation_rate", "nfl_air_yards_share",
    "nfl_weighted_opportunity_rate", "nfl_yards_before_contact_avg",
    "nfl_rush_attempts_per_game",
}
```

**Why `nfl_` prefix on every field:** Engine A uses unqualified names like `yprr` and `target_share` for college-derived metrics (from CFBD or PlayerProfiler). If Engine B reused those names, the cross-engine leakage test `assert no overlap between ENGINE_B_INPUTS fields and ALLOWED_ENRICHMENT_COLUMNS` would become ambiguous — the test could pass even if the same column name appeared in both engines with different semantics. Namespacing with `nfl_` makes the boundary machine-enforceable: `nfl_yprr` is NFL active-player YPRR; `yprr` (without prefix) is the college enrichment field. Both engines add their own `source_<field>` provenance siblings using the same namespaced names.

**Leakage rule:** Every `nfl_` field in `ENGINE_B_ONLY_FIELDS` must be in `PROHIBITED_COLUMNS` in `engine_a_contract.py`. The module asserts this at import time. Update `engine_a_contract.py` to include all `nfl_`-prefixed Engine B fields in `PROHIBITED_COLUMNS` if they are not already present.

**Files:**
- Create: `src/dynasty_genius/models/engine_b_contract.py`
- Modify: `src/dynasty_genius/pipelines/engine_b_features.py` (add contract import and assertions)
- Create: `tests/test_engine_b_contract.py`
- Create: `tests/test_engine_b_no_engine_a_leakage.py`

- [ ] **Step 1: Write cross-engine leakage test**

  Create `tests/test_engine_b_no_engine_a_leakage.py`. Assert that `ENGINE_B_ONLY_FIELDS` is a subset of `PROHIBITED_COLUMNS` from `engine_a_contract.py` (every `nfl_`-prefixed field is blocked from Engine A). Assert that no field in `ENGINE_B_INPUTS` values appears in `ALLOWED_ENRICHMENT_COLUMNS` from `engine_a_contract.py` — the `nfl_` prefix ensures these sets are disjoint, and this test machine-enforces that invariant. If either assertion fails, the boundary is broken and must be fixed before any model training runs.

  Run: `.venv/bin/python -m pytest tests/test_engine_b_no_engine_a_leakage.py -q`
  Expected: fail (contract file not yet created).

- [ ] **Step 2: Create `engine_b_contract.py`**

  Define `ENGINE_B_INPUTS` and `ENGINE_B_ONLY_FIELDS` as shown above. Import `PROHIBITED_COLUMNS` from `engine_a_contract.py` and assert at module load that `ENGINE_B_ONLY_FIELDS.issubset(PROHIBITED_COLUMNS)` — fail fast if any `nfl_`-prefixed field is not blocked from Engine A. Also add all `nfl_`-prefixed Engine B fields to `PROHIBITED_COLUMNS` in `engine_a_contract.py` if not already present; bump the comment noting why each is prohibited (look-ahead when scoring prospects).

- [ ] **Step 3: Write Engine B feature tests**

  Create `tests/test_engine_b_contract.py`. Write tests asserting:
  - `ENGINE_B_INPUTS` has entries for all four positions.
  - Every field in `ENGINE_B_INPUTS` values starts with `"nfl_"` — the prefix convention is machine-enforced, not documented-only.
  - Every field in `ENGINE_B_INPUTS` values is also in `ENGINE_B_ONLY_FIELDS`.
  - The `load_participation()` join is documented as 2019+ only — assert that `engine_b_features.py` raises `InsufficientDataError` (or equivalent) when asked for seasons before 2019 with `nfl_route_participation_rate` fields.

  Run: `.venv/bin/python -m pytest tests/test_engine_b_contract.py -q`
  Expected: partial failure (file exists but may not yet import contract).

- [ ] **Step 4: Update `engine_b_features.py` to import the contract**

  Add at the top of the file:
  ```python
  from src.dynasty_genius.models.engine_b_contract import ENGINE_B_INPUTS, ENGINE_B_ONLY_FIELDS
  ```
  Add an assertion in the feature computation entry point that no output column is in `PROHIBITED_COLUMNS` (same pattern as `check_leakage()` in Engine A).

- [ ] **Step 5: Run all contract and leakage tests**

  Run: `.venv/bin/python -m pytest tests/test_engine_b_contract.py tests/test_engine_b_no_engine_a_leakage.py tests/test_leakage_scanner.py -q`
  Expected: all pass.

- [ ] **Step 6: Commit**

  ```bash
  git add src/dynasty_genius/models/engine_b_contract.py \
          src/dynasty_genius/pipelines/engine_b_features.py \
          tests/test_engine_b_contract.py tests/test_engine_b_no_engine_a_leakage.py
  git commit -m "feat: Engine B source contract — nflverse inputs; cross-engine leakage gate"
  ```

---

## Task 8: PFF / RotoViz / Campus2Canton — Manual Export Path

**Goal:** Establish a governed intake path for manual CSV exports from PFF, RotoViz, and Campus2Canton. No automation (Playwright/Selenium/scraping) in this task. Fixture replay tests run against checked-in sample exports. Each source gets a documented schema, a parse function, and a failure test that confirms the pipeline aborts on missing required columns (never silently substitutes).

**Why manual-first:** PFF's API is enterprise-only (Teamworks Intelligence, B2B only). RotoViz has no public API (premium subscription + Playwright CSV download). Campus2Canton has no API (structured CSV exports only). Automating these without a proven manual export path is premature. The adapter interface in `docs/data-source-contracts.md` already defines `ingest_manual_export(path, season)` — this task implements that half of the interface only.

**PFF fields of interest (manual CSV from PFF Premium Stats dashboard):**

| Field | Use | Role |
|-------|-----|------|
| `pff_grade` | Player process grade 0–100 | `context_signal` — never model input |
| `route_participation` | Routes run / routes possible | `context_signal` |
| `yprr` | PFF-computed YPRR | `context_signal` — Engine B uses nflverse YPRR, not PFF |
| `snap_share` | Offensive snap % | `context_signal` |

Note: `pff_grade` and `pff_route_grade` are in `PROHIBITED_COLUMNS` by name (Engine A leakage guard). PFF fields may only populate `context_signal` columns — they never enter model features under any name.

**RotoViz fields of interest (manual CSV from Range of Outcomes / NFL Stat Explorer):**

| Field | Use | Role |
|-------|-----|------|
| `yprr` | RotoViz-computed YPRR | `context_signal` |
| `target_rate` | Targets per route | `context_signal` |
| `similarity_cohort` | Historical player comps | `context_signal` |

**Campus2Canton fields (CSV export from Player Metric Data Table):**

| Field | Use | Role |
|-------|-----|------|
| `ryptpa` | Receiving Yards per Team Pass Attempt | `context_signal` — secondary CFBD validation |
| `dominator_pct` | Campus2Canton dominator | `context_signal` — cross-check against CFBD dominator_rating |

**Files:**
- Create: `src/dynasty_genius/sources/adapters/manual_export_adapter.py`
- Create: `tests/fixtures/pff/sample_export.csv` (anonymized or real sample)
- Create: `tests/fixtures/rotoviz/sample_export.csv`
- Create: `tests/fixtures/campus2canton/sample_export.csv`
- Create: `tests/test_manual_export_adapter.py`
- Create: `docs/data-sources/pff-manual-export-schema.md`
- Create: `docs/data-sources/rotoviz-manual-export-schema.md`
- Create: `docs/data-sources/campus2canton-manual-export-schema.md`
- Create: `app/data/manual_exports/.gitkeep` (directory for David's CSV drops, gitignored by content)
- Modify: `.gitignore` (add `app/data/manual_exports/*.csv`)

- [ ] **Step 1: Define required columns per source**

  Write the three schema docs. Each doc specifies:
  - Exact column names expected in the CSV header (case-sensitive).
  - Column types.
  - Which columns are required vs. optional.
  - Which columns map to what `context_signal` field in the normalized row schema.
  - How to export the CSV from the source's UI (step-by-step for David).

- [ ] **Step 2: Create fixture CSVs**

  Create `tests/fixtures/pff/sample_export.csv` with 5–10 rows matching the PFF schema doc. Do the same for RotoViz and Campus2Canton. These are hand-crafted fixtures — no live source access required. Commit them.

- [ ] **Step 3: Write adapter tests**

  Create `tests/test_manual_export_adapter.py`. Write tests:
  - `PFFManualExportAdapter.parse(fixture_path)` returns a list of normalized rows with `source_name="pff"`.
  - Every row has `pff_grade` in `[0.0, 100.0]`.
  - A CSV missing required columns raises `ManualExportSchemaError` listing the missing columns.
  - The error does NOT produce any partial rows.
  - Same tests for RotoViz and Campus2Canton adapters.
  - A cross-source test: for a player present in both PFF and CFBD fixtures, the Campus2Canton `dominator_pct` is within 10pp of the CFBD `dominator_rating` (validates the formula against a secondary source).

  Run: `.venv/bin/python -m pytest tests/test_manual_export_adapter.py -q`
  Expected: all fail.

- [ ] **Step 4: Implement `manual_export_adapter.py`**

  Implement three adapter classes (`PFFManualExportAdapter`, `RotoVizManualExportAdapter`, `Campus2CantonManualExportAdapter`), each with:
  - `REQUIRED_COLUMNS: tuple[str, ...]`
  - `parse(path: Path) -> list[dict]` — validates header, returns normalized rows; raises `ManualExportSchemaError` if any required column is missing
  - `source_name: str`

  All adapters inherit from a `ManualExportAdapterBase` that enforces the header validation and `ManualExportSchemaError` pattern.

- [ ] **Step 5: Run adapter and leakage tests**

  Run: `.venv/bin/python -m pytest tests/test_manual_export_adapter.py tests/test_market_leakage_gate.py -q`
  Expected: all pass.

- [ ] **Step 6: Commit**

  ```bash
  git add src/dynasty_genius/sources/adapters/manual_export_adapter.py \
          tests/test_manual_export_adapter.py \
          tests/fixtures/pff/ tests/fixtures/rotoviz/ tests/fixtures/campus2canton/ \
          docs/data-sources/pff-manual-export-schema.md \
          docs/data-sources/rotoviz-manual-export-schema.md \
          docs/data-sources/campus2canton-manual-export-schema.md \
          app/data/manual_exports/.gitkeep .gitignore
  git commit -m "feat: PFF/RotoViz/Campus2Canton manual export adapters — schema validation, fixture replay, no automation"
  ```

---

## Self-Review Checklist

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Source registry classifying all sources | Task 1 |
| `training_label` ≠ model input — explicit separation | Task 1 |
| Allowed/prohibited fields per source | Task 1 |
| Enterprise APIs `prohibited_current_phase` with David-approval note | Task 1 |
| Provenance, cache policy, freshness, test gates, failure behavior | Tasks 1, 2, 5, 6 |
| CFBD stabilization — formula lock, cache, row-count, replay | Task 2 |
| PlayerProfiler decision gate — probe, coverage test, binary resolution | Task 3 |
| PP Path B: no imputed-median for `target_share`/`breakout_age`/`speed_score` | Task 3 |
| Engine A v2 CFBD-only backtest — RMSE, R², Spearman, by position | Task 4 |
| Backtest held until PP gate resolves honestly | Task 3 → Task 4 dependency |
| RAS as risk layer — `low_ras_risk_flag` and `missing_athletic_profile` distinct | Task 5 |
| `missing_athletic_profile` is a caveat, not a confirmed low-RAS signal | Task 5 |
| Market overlay — FantasyCalc primary, KTC deferred, hard leakage gate | Task 6 |
| Engine B `nfl_` prefix on all fields — machine-enforceable boundary | Task 7 |
| Engine B fields added to `PROHIBITED_COLUMNS` in Engine A contract | Task 7 |
| PFF/RotoViz/Campus2Canton — manual export path first | Task 8 |
| No market-derived Engine A/B features | Tasks 1, 6, 7 |
| No buy/sell/trade/directive language | Respected throughout |

**Placeholder scan:** No TBD, TODO, or "similar to Task N" entries. Every step contains the action required.

**Type consistency:**
- `SourceDefinition` defined in Task 1, used in registry test.
- `CFBDAsyncClient` defined in Task 2, used in `enrich_training_data.py`.
- `RASAdapter` / `to_flags()` defined in Task 5 — `None` RAS returns `(False, True)`, not `(True, True)`.
- `FantasyCalcClient` / `MarketOverlayFetchError` defined in Task 6.
- `ENGINE_B_INPUTS` / `ENGINE_B_ONLY_FIELDS` defined in Task 7 — all field names carry `nfl_` prefix.
- `ManualExportAdapterBase` / `ManualExportSchemaError` defined in Task 8, consistent across adapters and tests.

**Phased execution:**
- **Phase 1 (first executable unit):** Tasks 1, 3, 4 — Source Registry + PlayerProfiler Decision Gate + CFBD Backtest.
- **Phase 2 (unlock after Phase 1 gates pass and PP gate resolves):** Task 2 (CFBD adapter extraction), Task 5 (RAS), Task 6 (Market Overlay), Task 7 (Engine B), Task 8 (manual exports) — these are independent of each other within Phase 2.
- Task 4 (backtest) must not run with PP fields that were set by imputation — run it only after Task 3 honestly resolves the PP feature set.
