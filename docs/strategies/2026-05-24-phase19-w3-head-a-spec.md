# Phase 19 Workstream 3 Spec: Head A (Absolute Valuation) v3 Bake-Off

## Status
**PROPOSED SPECIFICATION** — Awaiting David's approval to transition to W3 execution.

## Objective
Design, implement, and run the Leave-One-Out Cross-Validation (LOOCV) and walk-forward temporal backtest harness to train and evaluate Head A (Absolute Rookie Valuation) models against our existing Engine A v2 baseline. 

Head A predicts **best-3-of-first-4-seasons PPR PPG** using pre-NFL metrics. 

---

## 1. Feature Matrices by Position

In strict compliance with `engine_a_contract.py` and the Head B quarantine rules, Head A is authorized to consume draft capital. The active feature matrices for our candidates are:

| Position | Authorized Head A Features |
|---|---|
| **QB** | `nfl_pick`, `nfl_round`, `final_college_age` |
| **RB** | `nfl_pick`, `nfl_round`, `final_college_age`, `rb_final_dominator`, `rb_scrimmage_ypg`, `rb_school_sp_plus`, `rb_rec_ypg` |
| **WR** | `nfl_pick`, `nfl_round`, `final_college_age`, `wr_dominator_final`, `wr_breakout_age`, `wr_market_share_yds`, `wr_yards_per_reception_career`, `ryptpa`, `yprr_college` |
| **TE** | `nfl_pick`, `nfl_round`, `final_college_age`, `te_ryptpa_final`, `te_yards_per_reception_career` |

---

## 2. Candidate Model Architectures

We will compare two structural hypotheses against the current Engine A v2 baseline:

### A. Candidate A: Regularized Linear Ridge
* **Hypothesis**: The relationship between draft capital, age, and college efficiency remains linear under robust regularization.
* **Regularization Grid**: Sweep alpha across `[0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1000.0]`.
* **Scale**: Standardize all feature inputs to zero-mean and unit-variance.

### B. Candidate B: Non-Linear Gradient Boosted Trees (GBT / LightGBM)
* **Hypothesis**: Non-linear tree boundaries can better capture draft capital tiers (first round vs. Day 3 cliffs) and aging curves.
* **Constraints (Anti-Overfitting Rules)**: Because our prospect training sample is relatively small (n=358 for $\le 2021$), the tree model must use highly regularized, shallow hyper-parameters:
  - `max_depth = 3`
  - `learning_rate = 0.05`
  - `n_estimators = 50`
  - `min_child_samples = 5`

---

## 3. Walk-Forward Evaluation Harness

To prevent temporal leakage and evaluate out-of-fold generalization:
1. **Temporal Splits**: Use 4-fold temporal walk-forward splits.
   - **Fold 1**: Train on $\le 2017$ classes; test on $2018$ class.
   - **Fold 2**: Train on $\le 2018$ classes; test on $2019$ class.
   - **Fold 3**: Train on $\le 2019$ classes; test on $2020$ class.
   - **Fold 4**: Train on $\le 2020$ classes; test on $2021$ class.
2. **Censoring Handling**: Exclude any player marked `censored_incomplete_arc=1` (draft classes 2022+) from the training set, as their career outcomes are not yet fully realized.
3. **Out-of-Fold Logging**: Write all validation fold predictions to a gitignored CSV log for residual diagnostics.

---

## 4. Hard Promotion Gates

To replace the baseline and promote a position-specific Head A v3 model to active status, a candidate must clear **at least 2 of 3** metrics in our walk-forward test:

1. **RMSE (Accuracy Gate)**:
   - Must reduce walk-forward RMSE by $\ge 2.0\%$ overall compared to the Engine A v2 baseline.
2. **Spearman Rank Correlation ($\rho$) (Ordinal Gate)**:
   - Must increase within-class rank correlation, proving better Best Player Available (BPA) sorting.
3. **NDCG@10 (Top-10 Sorting Gate)**:
   - Must improve Normalized Discounted Cumulative Gain in the top-10 draft picks, ensuring our early first-round selections are highly optimized.
4. **TE Safety Guard**:
   - If a TE candidate is evaluated, it must not regress TE MAE by $>1.0\%$ compared to baseline.

---

## 5. Required Implementation Steps

David's TMUX cockpit agents (Claude Code, Codex) will build and execute this spec through the following steps:

1. **Create `scripts/run_head_a_bakeoff.py`**:
   - Implements the 4-fold temporal walk-forward harness.
   - Standardizes features and executes Ridge and regularized GBT training loops.
   - Calculates RMSE, Spearman, and NDCG@10 per position.
   - Saves a gitignored JSON report to `app/data/backtest/phase19/head_a_bakeoff_[timestamp].json`.
2. **Add Unit Tests (`tests/test_head_a_bakeoff.py`)**:
   - Write at least 6 unit tests to verify standard scaling, temporal isolation, and gate calculations.
3. **Generate Validation Report**:
   - Write a formal Markdown decision memo to `docs/validation/phase19-w3-head-a-promotion-decision.md` detailing the test results.
   - No model weights (`.pkl`) or manifest routing will be promoted until David approves this report.
