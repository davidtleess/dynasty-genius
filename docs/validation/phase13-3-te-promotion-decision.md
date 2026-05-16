# Phase 13.3 TE Promotion Decision

**Date:** 2026-05-16  
**Status:** PROMOTED  
**Model:** TE v3 (`te_v3.pkl`)  
**Alpha:** 100.0  
**Features:** Baseline + `te_role_is_risk_profile`

## 1. Backtest Results
The model was evaluated using the Phase 10/11 walk-forward backtest harness (2020-2023 folds).

| Metric | Result | Target | Pass |
| :--- | :--- | :--- | :--- |
| **G1 (Rank Correlation)** | 0.48 Kendall τ (mean) | >= 0.40 | **PASS** |
| **G1 (CI Stability)** | 4/4 folds >= 0.20 | 3/4 folds | **PASS** |
| **G2 (RMSE Stability)** | 12.3% Max Dev | <= 25.0% | **PASS** |
| **G3 (Market)** | N/A (Deferred) | N/A | **DEFERRED** |

## 2. Naive Holdout (2022-2023)
- RMSE: 2.634
- R²: 0.479
- Spearman: 0.743

## 3. Justification
The inclusion of the `te_role_is_risk_profile` feature, combined with increased regularization (alpha 100.0), has successfully stabilized the TE model. The model comfortably cleared the G1 rank correlation threshold (0.48 vs 0.40) and demonstrated high stability across folds (12.3% deviation).

As a result, TE is being promoted from `EXPERIMENTAL` to `ACTIVE_B`.

## 4. Operational Changes
- `app/data/models/engine_b/v2_manifest.json` updated to point to `te_v3.pkl`.
- `src/dynasty_genius/models/engine_b_contract.py` updated to remove TE from `ENGINE_B_EXPERIMENTAL_POSITIONS`.
- `te_role_is_risk_profile` added to the production TE feature contract.
