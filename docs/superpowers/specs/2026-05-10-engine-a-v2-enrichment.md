# Design Spec: Engine A v2 Data Foundation (Historical Enrichment)

**Version:** 1.0.1  
**Status:** Approved (Pending Commit)  
**Date:** 2026-05-10  
**Target:** 874 Historical Prospects (2015–2025)

## 1. Mission
Transition Engine A from a simple `pick/round/age` model into a durable, feature-rich valuation engine by enriching the historical training set with college production and athletic signals. This work is governed by the "Do it Right" principle, prioritizing auditable data lineage and zero market leakage.

## 2. Feature Registry & Position Mapping

Every row in the enriched CSV (`prospects_with_outcomes_v2.csv`) must adhere to this position-aware input matrix. Any feature marked `—` for a position must be `NaN` (no imputation).

| Position | dominator_rating | receiving_yards_share | target_share | breakout_age | speed_score | yprr |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WR** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (impute pre-2019) |
| **RB** | ✓ | ✓ | — | ✓ | ✓ | — |
| **TE** | ✓ | ✓ | ✓ | ✓ | — | ✓ (impute pre-2019) |
| **QB** | — | — | — | — | — | — |

### 2.1 Feature Definitions

| Field | Role | Tier | Source | Derivation | Provenance Column |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dominator_rating` | Input | 2 | CFBD | (yds_share + td_share) / 2 | `source_dominator_rating` |
| `receiving_yards_share` | Input | 2 | CFBD | player_rec_yds / team_rec_yds | `source_receiving_yards_share` |
| `target_share` | Input | 3 | PlayerProfiler | Actual Target % (External) | `source_target_share` |
| `breakout_age` | Input | 3 | PlayerProfiler | External | `source_breakout_age` |
| `speed_score` | Input | 3 | PlayerProfiler | External | `source_speed_score` |
| `yprr` | Input | 3 | PlayerProfiler | External | `source_yprr` |
| `y24_ppg` | Label | 1 | Baseline CSV | Historical NFL Outcome | — |

## 3. Governance & Leakage Guards

### 3.1 Fail-Closed Protocol (Non-Negotiable)
The enrichment pipeline must implement a strict scanning gate. If any prohibited column or keyword is detected, the run must **FAIL CLOSED**.
*   **Whitelisted Basis:** Only columns in `BASELINE_COLUMNS` or `ALLOWED_ENRICHMENT_COLUMNS` are permitted.
*   **Regex Scan (Anchored):** `^ktc_`, `^adp`, `_rank$`, `^expert`, `^market_`, `^value_`, `^consensus`.
*   **Action on Violation:** Stop run immediately; write `leakage_violation_report.json` detailing offending columns; do NOT overwrite `prospects_with_outcomes_v2.csv`.

### 3.2 Feature/Label Separation
Post-NFL production stats (e.g., `y2_points`, `total_points`, `y24_ppg`) are strictly **Target Labels** for training. They must never be registered as input features for prospect scoring.

## 4. Data Lineage & Provenance

### 4.1 Metadata Schema
Every enrichment data column must have a `source_<field>` sibling column.
*   **Allowed Values:** `cfbd`, `playerprofiler`, `nfl_data_py`, `imputed_median`, or prefixed `manual_...`, `college_pff_...`.
*   **Imputation Flag:** `imputed_yprr` must be set to `1` when `yprr` is filled via median imputation.
*   **Artifact Metadata:** The final CSV must be accompanied by an `enrichment_metadata.json` capturing the `source_timestamp` and `formula_version` for the entire run.

### 4.2 Join Contract
*   **Join Strategy:** Left join to preserve the 874-row baseline exactly.
*   **Primary Key:** `gsis_id`.
*   **Fallback Key (Strict):** `pfr_player_name` + `position` + `college` + `season`.
*   **Failure Mode:** If the fallback key results in a duplicate/ambiguous match, the enrichment for that row must remain `NaN` and be logged in a `join_ambiguity_report.json`.

## 5. Missingness & Inhibition Policy
*   **Missingness:** Adhere to the completeness thresholds in `test_engine_a_v2_feature_contract.py` (80% Dominator, 95% WR YPRR).
*   **Scoring Inhibition:** If `dominator_rating` is missing for a skill position row, Engine A must mark the resulting card as `PRE_MODEL`. This is a deliberate policy to ensure minimum signal thresholds for model-based valuation.

## 6. Acceptance Criteria
*   Enriched CSV passes all checks in `tests/test_engine_a_v2_feature_contract.py`.
*   Zero `PROHIBITED_COLUMNS` present in the final artifact.
*   Exact row-count parity (874 rows).
*   Spec is committed to the repository before implementation begins.
