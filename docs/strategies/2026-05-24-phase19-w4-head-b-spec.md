# Phase 19 Workstream 4 Spec: Head B (Market Edge / Residuals) v3 Bake-Off

## Status
**PROPOSED SPECIFICATION** — Awaiting David's approval to transition to W4 execution.

## Objective
Design, implement, and run the Leave-One-Out Cross-Validation (LOOCV) and walk-forward backtest harness to train and evaluate Head B (Market Edge / Residual) models. 

Head B predicts **`residual_ppg`** ($PPG - \text{Expected PPG at draft slot}$) to find players who outperform or underperform their draft capital, using **zero draft-capital inputs**.

---

## 1. Feature Contracts & Prohibitions

To ensure Head B represents a pure "market edge" based on collegiate profiles, it is subject to strict data quarantine:
1. **Banned Columns**: The features `nfl_pick`, `nfl_round`, `pick`, `round`, `expected_ppg_at_pick`, and any derived draft-capital metrics are **strictly prohibited**.
2. **Authorized Features by Position**:
   - **WR**: `final_college_age`, `wr_dominator_final`, `wr_breakout_age`, `wr_market_share_yds`, `wr_yards_per_reception_career`, `ryptpa` *(yprr_college remains dark/quarantined)*.
   - **RB**: `final_college_age`, `rb_final_dominator`, `rb_school_sp_plus` *(rb_scrimmage_ypg and rb_rec_ypg remain dark due to low coverage)*.
   - **TE**: `final_college_age`, `te_ryptpa_final`, `te_yards_per_reception_career`.

---

## 2. Walk-Forward Protocol & Architectures

1. **Splits**: 4-fold temporal walk-forward splits ($\le 2017$ training through $\le 2020$ training).
2. **Target Variable**: `residual_ppg` from `prospects_with_outcomes_v3.csv`.
3. **Censoring**: Exclude `censored_incomplete_arc=1` (draft classes 2022+) from the training sets.
4. **Candidates**:
   - **Ridge Regression**: Alpha sweep `[0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1000.0]`.
   - **Shallow Gradient Boosted Trees (GBT)**: `max_depth=3`, `n_estimators=50` to capture non-linear interaction terms.

---

## 3. Mandatory Validation Gates

To be promoted, a Head B candidate model must satisfy **both** of the following:

### A. Mandatory Gate: Residual $R^2 > 0$
* The model must explain more variance in the residuals than a simple mean-zero model (which represents raw draft-capital expectation). If $R^2 \le 0$, the model is worse than guess-work and is immediately disqualified.

### B. Secondary Gates (Must pass at least 2 of 3)
1. **Within-Tier Pairwise Accuracy**:
   - Measures the percentage of times the model correctly ranks player A over player B when both were drafted in the same pick tier (e.g., within 10 picks of each other).
2. **Top-5 Day 3 Sleeper Precision**:
   - Out of the top-5 highest-predicted Head B players drafted on Day 3 (picks 103+), how many achieved a positive `residual_ppg` ($>0$).
3. **Residual Calibration Monotonicity**:
   - Checks if the predicted residual values are monotonic with actual outcome residuals across binned tiers.

---

## 4. Outlier Sensitivity Gate (Coefficient Drift)

To ensure our models are robust and not driven by a single fluky historic star (e.g., Ja'Marr Chase or Puka Nacua):
1. **LOOO (Leave-One-Outlier-Out) Test**: For each fold, sequentially remove the single player with the largest absolute residual from the training set and refit the model.
2. **Drift Threshold**: Measure the maximum percentage shift in feature coefficients.
3. **Quarantine Penalty**: If any feature's coefficient shifts by **$>25.0\%$**, that feature is flagged as unstable. The script will output `head_b_outlier_sensitivity_report.json` and demote that feature to "Candidate-Quarantined" (penalizing its weights or forcing stronger regularization) to guarantee model stability.

---

## 5. Execution Handoff

David's TMUX cockpit agents (Claude Code, Codex) will execute W4 through the following:

1. **Create `scripts/run_head_b_bakeoff.py`**:
   - Implement the walk-forward residual training loops.
   - Implement the LOOO outlier sensitivity test.
   - Save a gitignored JSON report to `app/data/backtest/phase19/head_b_bakeoff_[timestamp].json`.
2. **Add Unit Tests (`tests/test_head_b_bakeoff.py`)**:
   - Write tests for prohibited column checking, residual $R^2$ calculation, and coefficient drift measurement.
3. **Generate Validation Report**:
   - Write a formal decision memo to `docs/validation/phase19-w4-head-b-promotion-decision.md` detailing the residual results.
