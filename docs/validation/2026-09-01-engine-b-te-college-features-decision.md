---
decision_date: 2026-09-01
ticket: DG-125
candidate_features: [te_ryptpa_final, te_yards_per_reception_career]
target_engine: engine_b
target_position: TE
baseline_model: te_v2 (16 features, run 20260831T204458Z)
join_coverage_pct_engine_b_te_rows: 0.506
validation_design: walk-forward by season, expanding window, 4 folds
pooled_out_of_fold_n: 323
distinct_players: 143
spearman_baseline: 0.7741
spearman_with_college: 0.7794
spearman_delta: 0.0053
bootstrap_ci_95: [-0.0091, 0.0202]
bootstrap_p_better: 0.771
promotion_warranted: false
---

# Engine B tight end: CFBD college features tested and NOT promoted

David ruled on 2026-09-01: bring the CFBD college columns into the Engine B TE feature set
"and let an honest ablation decide." It decided. This record exists so the reject carries
lineage rather than becoming a thing someone re-proposes in six months.

## First, a correction to the premise

The work was commissioned on my claim that the 2026-08-31 retrain moved TE off a head
carrying college features. **That claim was false.** There are two different artifacts named
`te_v3`:

| artifact | college signal | affected by the retrain |
|---|---|---|
| `app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl` | yes — Engine A prospect head | **no**, untouched |
| `app/data/models/engine_b/runs/20260626T165649Z/te_v3.pkl` | **none** — 14 Engine B features | replaced |

The Engine B te_v3 that was replaced never had college features. Measured:

    te_v3 (replaced) : 14 features
    te_v2 (serving)  : 16 features
    LOST   : NOTHING
    GAINED : ngs_avg_cushion, ngs_avg_separation   -> strict superset

`te_ryptpa_final` and `te_yards_per_reception_career` appear nowhere in the Engine B
contract or assembler; they are Engine A fields. The sentence in `58d3b20c`'s message
claiming the retrain "drops its two CFBD college features" is wrong and is corrected here.

A second premise was also wrong: `ENGINE_A_PROHIBITED_IN_B` does **not** block these two
fields. It prohibits by exact name (dominator_rating, completion_pct, pick, round, …), and
neither candidate is in the set. `validate_no_prohibited_features` and
`validate_no_temporal_leakage` both pass on them. No governance change was needed.

## Coverage

Joining `prospects_with_outcomes_v3.csv` to the Engine B TE population on `gsis_id`:
421 of 731 TE player-seasons match (57.6%), and within the training-eligible rows
**248 of 490 carry a college value (50.6%)**. Half the population would be imputed.

## Result

Walk-forward by season, expanding window, RidgeCV, identical pipeline both arms:

| test season | n_train | n_test | RMSE base | RMSE +college | rho base | rho +college | both better |
|---|---|---|---|---|---|---|---|
| 2020 | 167 | 79 | 2.5613 | 2.5506 | 0.7318 | 0.7475 | yes |
| 2021 | 246 | 83 | 2.0758 | 2.0580 | 0.7853 | 0.7982 | yes |
| 2022 | 329 | 82 | 2.3112 | 2.2715 | 0.7845 | 0.7887 | yes |
| 2023 | 411 | 79 | 2.1940 | 2.2041 | 0.7673 | 0.7648 | no |

**3 of 4 folds improved both error and ranking — and that is exactly why the fold count is
not the instrument.** A 4-fold sign test is the design this project has already been burned
by; it cannot reach significance and it reads 3/4 as encouraging.

Paired bootstrap of the rank-correlation DIFFERENCE, clustered on player (a player recurs
across seasons, so unclustered draws would overstate precision), 4,000 draws on 323 pooled
out-of-fold rows from 143 distinct players:

    Spearman delta  +0.0053
    95% CI          [-0.0091, +0.0202]      <- contains zero
    P(better)       77.1%

**Not established.** Directionally positive, consistently so, and indistinguishable from
zero at this sample. A single pooled 2022+2023 holdout run before the walk-forward also
disagreed with it on the ranking metric (rho fell by 0.0085), so the sign of the effect is
not even robust to the evaluation design.

## Decision

**Not promoted.** Two candidate features, 50.6% coverage, an effect of +0.005 Spearman whose
interval spans zero. The honest reading is that the box score a tight end has already
produced in the NFL dominates what he did in college, which is the same conclusion a prior
WR bakeoff reached against these same candidates.

**What would change the answer:** better coverage (half the population is currently
imputed), or a target the college data is better placed to explain — a pre-debut player has
no NFL box score at all, so this signal is far more likely to earn its place in the Engine A
prospect path or in an availability model than in a veteran points regression.

**Do not re-propose without new evidence of one of those two things.** The candidates have
now been tested twice.
