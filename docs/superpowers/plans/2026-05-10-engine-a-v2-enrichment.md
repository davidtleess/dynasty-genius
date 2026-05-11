# Engine A v2 Historical Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the 874-prospect historical training set with college production and athletic signals while enforcing strict governance and leakage guards.

**Architecture:** A modular Python pipeline that performs a left-join on the baseline training CSV. It uses CFBD as the primary auditable anchor (Tier 2) and PlayerProfiler as a secondary enrichment layer (Tier 3). Shared constants live in `src/dynasty_genius/models/engine_a_contract.py`.

**Tech Stack:** Python, Pandas, `httpx`, `cfbd` library.

---

### Task 1: Leakage Guard & Pipeline Skeleton

**Files:**
- Create: `scripts/enrich_training_data.py`
- Create: `tests/test_leakage_scanner.py`

- [ ] **Step 1: Write leakage scanner unit tests**
  Write tests that pass a "dirty" dataframe (containing `ktc_value` or `expert_rank`) and verify the scanner raises `ValueError` and writes `leakage_violation_report.json`.

- [ ] **Step 2: Implement the fail-closed leakage scanner**
  Use `LEAKAGE_REGEX` and `PROHIBITED_COLUMNS` from `engine_a_contract.py`.

```python
def check_leakage(df):
    # Anchored regex check + Prohibited set check
    # Raise ValueError on violation
```

- [ ] **Step 3: Implement Left-Join and Row-Count Check**
  Ensure the pipeline preserves exactly 874 rows from `prospects_with_outcomes.csv`.

- [ ] **Step 4: Verify with Baseline**
  Run: `pytest tests/test_engine_a_v2_feature_contract.py::test_baseline_csv_no_prohibited_columns -v`

- [ ] **Step 5: Commit**
  `git add scripts/enrich_training_data.py tests/test_leakage_scanner.py src/dynasty_genius/models/engine_a_contract.py`
  `git commit -m "feat: fail-closed leakage scanner and pipeline skeleton"`

---

### Task 2: Tier 2 Enrichment (CFBD)

**Pre-conditions:**
- `CFBD_API_KEY` must be present in `.env`.
- `cfbd` library added to `requirements.txt`.

**Files:**
- Modify: `scripts/enrich_training_data.py`
- Create: `app/data/cache/cfbd_cache.json`

- [ ] **Step 1: Implement CFBD extractor with Caching**
  Use the `cfbd` library. Implement the strict fallback key: `name + position + college + season`.
  Store raw API responses in `cfbd_cache.json` to avoid redundant network calls during development.

- [ ] **Step 2: Calculate Auditable Metrics**
  - `dominator_rating`: `(yds_share + td_share) / 2`
  - `receiving_yards_share`: `player_rec_yds / team_rec_yds`
  Populate `source_` sibling columns.

- [ ] **Step 3: Verify Tier 2 Schema**
  Generate a partial enriched CSV and run:
  `pytest tests/test_engine_a_v2_feature_contract.py::test_enriched_csv_dominator_rating_completeness -v`

---

### Task 3: Tier 3 Enrichment (PlayerProfiler)

**Files:**
- Modify: `scripts/enrich_training_data.py`
- Create: `app/data/cache/pp_id_map.json`

- [ ] **Step 1: Implement PP ID Discovery (Slug Resolution)**
  1. Derive slug from `pfr_player_name`.
  2. Resolve internal PP ID via `admin-ajax.php`.
  3. Cache to `pp_id_map.json`.

- [ ] **Step 2: Implement Stats Fetch & Rate Limiting**
  Fetch `target_share`, `breakout_age`, `speed_score`, `yprr`.
  Implement 1-second delay between requests to respect ToS.

- [ ] **Step 3: Implement Median Imputation for YPRR**
  Only for WR/TE pre-2019. Set `imputed_yprr=1`.

- [ ] **Step 4: Verify WR YPRR Completeness**
  Run: `pytest tests/test_engine_a_v2_feature_contract.py::test_enriched_csv_yprr_completeness_wr -v`

---

### Task 4: Scorer Inhibition (TDD)

**Goal:** Enforce `PRE_MODEL` for Engine A v2 features without breaking v1 Rookie Board.

**Files:**
- Modify: `tests/test_engine_a_scorer.py`
- Modify: `src/dynasty_genius/scoring/engine_a.py`

- [ ] **Step 1: Write failing inhibition test**
  Add a test that calls `score_prospect` with `dominator_rating=None` and expects `model_grade='PRE_MODEL'`.

- [ ] **Step 2: Verify test fails**
  Run: `pytest tests/test_engine_a_scorer.py -v`

- [ ] **Step 3: Implement Scorer Versioning & Inhibition**
  Update `score_prospect` to check if v2 features are passed. If `dominator_rating` is missing for skill positions in a v2-context, inhibit scoring.

- [ ] **Step 4: Verify test passes**
  Run: `pytest tests/test_engine_a_scorer.py -v`

---

### Task 5: Final Acceptance & Commitment

- [ ] **Step 1: Run full pipeline**
  Generate `prospects_with_outcomes_v2.csv` and `enrichment_metadata.json`.

- [ ] **Step 2: Final Acceptance Gate**
  Run all contract tests:
  `pytest tests/test_engine_a_v2_feature_contract.py -v`

- [ ] **Step 3: Commit and Track Plan**
  `git add app/data/training/prospects_with_outcomes_v2.csv resources/enrichment_metadata.json docs/superpowers/plans/2026-05-10-engine-a-v2-enrichment.md`
  `git commit -m "feat: completed historical enrichment for Engine A v2"`
