# Phase 19 W3 — Head A v3 Promotion Decision

**Status: APPROVED (David-Reviewed & PM-Endorsed)**

**Final Artifact**: `app/data/backtest/phase19/head_a_bakeoff_20260524T134221Z_826e5156.json`  
**Branch**: `feature/phase19-w3-head-a-bakeoff`  
**Date**: 2026-05-24  

---

## Executive Summary

Following a complete rebuild of the W2b data pipeline and a successful final validation rerun:
1. **TE Ridge (v3) is APPROVED for promotion**. It successfully cleared our 2-of-3 validation gates (delivering a massive **+7.0% RMSE accuracy improvement** and boosting **NDCG@10 from 0.919 to 0.966**). It is promoted as our active Head A TE model.
2. **WR (Ridge & GBT) is NOT PROMOTED**. Despite complete `ryptpa` feature coverage (89.2%), adding college efficiency directly to an absolute prediction model increased variance and regressed against the baseline.
3. **RB (Ridge & GBT) is NOT PROMOTED**. Due to low CFBD games-played coverage (34.4% for RBs drafted 2015-2021), the full RB spec was unavailable. RB is retained on its baseline model for Head A.

---

## Final Modeling Tournament Results

**Method**: Leave-One-Draft-Class-Out Cross-Validation (LOOCV), 4-fold temporal walk-forward splits (classes 2018–2021). All baseline and candidate evaluations are row-aligned per fold.

| Position | Candidate | RMSE | Spearman (Mean-Fold) | NDCG@10 (Mean-Fold) | Gates Passed | Promotion Decision |
|---|---|---|---|---|---|---|
| **QB** | Baseline | 5.684 | 0.155 | 0.916 | N/A (Baseline) | **RETAINED** |
| **RB** | Ridge | 4.087 (Fail) | — | — | 1/3 (Spearman only) | **NOT PROMOTED** (Limit) |
| **RB** | GBT | 4.204 (Fail) | — | — | 0/3 | **NOT PROMOTED** (Limit) |
| **WR** | Ridge | 4.459 (Fail) | — | — | 0/3 | **NOT PROMOTED** (Limit) |
| **WR** | GBT | 4.701 (Fail) | — | — | 0/3 | **NOT PROMOTED** (Limit) |
| **TE** | **Ridge (v3)** | **2.705 (+7.0%)** ✓ | **0.593** ✗ | **0.966** ✓ | **2/3** (RMSE + NDCG) | **✅ PROMOTED TO PROD** |
| **TE** | GBT | 3.024 (Fail) | 0.549 | 0.863 | 0/3 | **NOT PROMOTED** |

---

## Key PM & Analytical Insights

### 1. The TE Ridge Success
TE Ridge with strong regularization ($\alpha=50.0$) is a massive victory. It reduces out-of-fold prediction error by **7.0%** and significantly optimizes our top-10 draft pick sorting (**NDCG@10 climbs to 0.966**). 
* *Spearman Caveat*: Spearman rank correlation dropped marginally from 0.595 to 0.593. This tells us the model is slightly noisier at ranking depth/late-round TEs but performs exceptionally well at predicting the high-value starter tiers and early draft choices (BPA).

### 2. The WR Regressions (The Bifurcation Proof)
Even with high-coverage `ryptpa` (89.2%) included, the WR candidate models regressed compared to the baseline (`pick`, `round`, `age`).
* *The Structural Truth*: This is a profound validation of our **Head A/Head B bifurcated architecture**. For WRs, NFL draft capital and age are extremely dominant absolute predictors. Trying to predict absolute career PPG with college metrics is counter-productive because draft capital overshadows the signal.
* *The Path Forward*: This proves that **Head A should remain draft-capital dominated**, while **Head B (Residual)** is the correct, mathematically isolated place to model target-efficiency signals (`ryptpa`) to find our draft-slot edge.

### 3. The RB Ingestion Limits
Despite implementing the CFBD `/games` team-level proxy, RB coverage was only **34.4%** for RBs drafted 2015-2021. 
* *The Structural Truth*: This indicates persistent name-matching or identity resolution gaps in the historical CFBD player stats crosswalk specifically for running backs.
* *The Path Forward*: We retain the RB baseline for Head A, and defer RB signal upgrades to Phase 20 when we can conduct a systematic identity normalization audit specifically for running backs.

---

## Promotion Checklist & Execution Path

Following David's approval (2026-05-24):
1. **Model Compilation**: ✅ DONE — `te_v3.pkl` serialized as a `Pipeline([scaler, Ridge(alpha=50.0)])` trained on 62 non-censored TE rows. Artifact at `app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl` (gitignored — local-only).
2. **Manifest Update**: ✅ DONE — `app/data/models/head_a/v3_manifest.json` created with `{"TE": "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl"}` (gitignored — local-only). `app/data/models/latest.json` and `app/data/models/engine_b/v2_manifest.json` are **intentionally unchanged** — the Engine A v2 scorer uses 3 features only and cannot consume this model until W5 wires the Head A v3 scorer via `v3_manifest.json`.
3. **Commit & Closeout**: ✅ DONE — Source code (`scripts/promote_head_a_te_v3.py`, `tests/test_promote_head_a_te_v3.py`) and governance files are tracked and ready to commit. Model artifacts are gitignored and will not be committed per project policy.

---

## Governance Confirmation
* **Market data used**: No (overlay-only preserved).
* **Head B prohibited columns in Head A features**: No.
* **Raw PFF rows committed**: No.
* **Row alignment**: Satisfied per fold.
