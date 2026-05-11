---
baseline_model: pick_round_age
enriched_model: pick_round_age_cfbd_qb
held_out_n: 38
metric_delta_rmse_pct: -0.3532
metric_delta_r2: -1.6981
metric_delta_spearman: -0.1433
improvements_meeting_threshold: 0/3
promotion_warranted: false
cfbd_coverage_pct_qb: 0.9520
cfbd_coverage_none_players: 6
---

# QB CFBD Backtest Report

Generated: 2026-05-11
Methodology matches `backtest_engine_a_cfbd_only.py` (Task 4).

## Setup

- Training QBs : 87
- Holdout QBs  : 38  ⚠️ small — interpret conservatively
- CFBD coverage: 118 FULL, 1 PARTIAL, 6 NONE (95.2% combined)
- Features for Model A: pick, round, age
- Features for Model B: pick, round, age, completion_pct, yards_per_attempt, td_int_ratio, sack_rate, all_purpose_yards, passing_yards_share, ppa, wepa, rushing_yards, rushing_tds

## Results

| Metric    | Model A (baseline) | Model B (+ QB CFBD) | Delta | Threshold | Pass? |
|-----------|-------------------|---------------------|-------|-----------|-------|
| RMSE      | 6.699           | 9.066               | -35.3% reduction | ≥5%   | ✗ |
| R²        | -1.043             | -2.741                 | -1.698            | ≥0.02 | ✗ |
| Spearman  | 0.289       | 0.146           | -0.143      | ≥0.03 | ✗ |

**Metrics meeting threshold:** 0/3
**Promotion gate (≥2/3):** FAIL — promotion NOT warranted

## Null feature counts (imputed to training mean)

  completion_pct: 60 nulls
  yards_per_attempt: 60 nulls
  td_int_ratio: 60 nulls
  sack_rate: 125 nulls
  all_purpose_yards: 16 nulls
  passing_yards_share: 125 nulls
  ppa: 6 nulls
  wepa: 6 nulls
  rushing_yards: 18 nulls
  rushing_tds: 18 nulls

## Interpretation

The enriched QB model does not meet the promotion gate. QB college features remain context_signal only. POSITION_FEATURE_MATRIX["QB"] stays as defined (empty or context-only). Do not promote without David's explicit override.

## Caveats

- Holdout n=38 QBs is below the 50-row threshold used for skill positions.
  Confidence intervals on all metrics are wide. A pass here is directional, not conclusive.
- NONE players (6 FCS/small-program QBs) are imputed to mean — they add
  noise, which slightly biases against the enriched model.
- QB outcome (y24_ppg) has high variance by position nature. Draft capital (pick/round)
  already captures most of the signal for QBs.
