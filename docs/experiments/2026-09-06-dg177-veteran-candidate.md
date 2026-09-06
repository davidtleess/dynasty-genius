# DG-177 — A veteran forecast candidate, evaluated with information available at the time

**Date:** 2026-09-06 (round 1 corrections applied the same day) · **Lane:** Davids-MacBook-Pro-23481 (veteran
forecasting seat) · **Branch:** `ticket/DG-177` from origin/main `ecc260ef` · **Primary run:**
`runs/20260906T144343Z/dg177_veteran_candidate/` (corrected recipe) · **Pre-correction run kept for the record:**
`runs/20260906T133309Z/` · **Report-only.** Nothing served was trained, promoted, restarted or written. Every input was
read-only; every output is inside a run directory.

## 1. What the ticket asked and what was built

DG-162 found the product reads three columns (`ppg_t`, `games_t`, `age`) and that the other features buy little.
It measured that under a walk-forward one season stricter than necessary, with the served recipe's player-leaky
inner penalty selection, and it measured no new football input. This ticket asks for a reusable, honest evaluation
path and one justified feature family tested through it. Codex's round-1 review then required four corrections,
all applied here (§2).

Built, with tests written first and two guards mutation-checked:

- `src/dynasty_genius/models/label_closure.py` — the ONE label-closure rule (`feature_season + window <= test
  season`) that every walk-forward now shares; `assert_labels_known` refuses an open label.
- `src/dynasty_genius/models/leak_free_tuning.py` — ridge penalty selection on expanding-time inner folds
  clustered on player, with every inner training label closed at its validation season and the imputer fitted
  inside each inner fold. The deployed trainer imports it under its old name.
- `src/dynasty_genius/eval/veteran_candidate.py` — the evaluator: folds, the feature gate (the contract's
  future-season and DG-173 projection bans), two named recipes (§2), paired player-resampled bootstraps against
  two references, top-k aggregated by forecast season, skipped folds written as skipped, run directories never
  overwritten.
- `src/dynasty_genius/eval/opportunity_features.py` — raw realized opportunity per PRODUCT game (§2, item 2);
  the third-party expected-points columns exposed separately as `xfp_*`, named exploratory.
- `scripts/experiments/dg177_veteran_candidate.py` — the runner and its report.
- Corrected inherited splits: `eval/backtest_harness.py` (both mask sites), `models/availability.py`, and the
  trainer's inner selection and pre-split imputation (`scripts/train_engine_b.py`).

## 2. The round-1 corrections, and what each one cost

1. **Label closure everywhere.** The outer rule was already closed here; three inherited paths were not. The
   harness split on `feature_season < test_year` (a row one season before the test year is labelled FROM the test
   year's outcome seasons); the availability walk-forward trained on every earlier season; the trainer's inner
   selection validated on season *v* and trained on *v−1* rows whose labels reach *v+1*, after imputing on the
   whole window. All three now use the shared rule; the trainer's inner folds impute per fold. Tests show an open
   label cannot move the fold it was open for (harness, availability, tuning). **Cost:** the corrected inner
   selection needs a closed validation season inside the training window, i.e. three feature seasons for a
   two-season label. The training file starts in 2018, so the 2020 and 2021 test folds cannot be fitted honestly
   and are written as skipped; **2022 and 2023 are the evaluable folds** for the two-year target.
2. **The denominator is the product's.** The opportunity source holds rows only for weeks with an opportunity —
   fewer than `games_t` on 1,061 of 3,337 joined rows, never more. Rates now divide by `games_t` (all games with a
   stat line, DG-024, untouched); a stat-line game with no source row is an observed zero-opportunity game (3,265
   counted); a season absent from the source is NaN with `opp_source_available = False` (47 rows), never zero.
3. **Annual forecasts on explicit seasonal events** — a separate artifact and contract; see
   `2026-09-06-dg177-annual-forecasts.md` (written when that run completes) and the ticket.
4. **Evaluate as final scoring fits.** Every arm is now fitted with the corrected procedure (`leak_free`: alpha on
   closed, player-clustered inner folds, imputer per inner fold, then a median imputer on the whole training window
   and a Ridge at that alpha). The served 2026-08-31 recipe (RidgeCV, random player-leaky 5-fold) survives only as
   the named arm `deployed_recipe_reproduction`. Top-k overlap is taken within each forecast season and averaged.

## 3. Reproduction of DG-162 §1 — still exact

Under DG-162's stricter rule and the served recipe on every arm, every number matches to the precision published:

| pos | n (this / DG-162) | `ppg_t` alone r² | served set r² | Δr² served − 3 columns |
|---|---|---|---|---|
| QB | 95 / 95 | 0.320 / 0.320 | 0.383 / 0.383 | +0.030 / +0.030 |
| RB | 284 / 284 | 0.572 / 0.572 | 0.600 / 0.600 | −0.000 / −0.000 |
| WR | 456 / 456 | 0.623 / 0.623 | 0.661 / 0.661 | +0.010 / +0.010 |
| TE | 244 / 244 | 0.588 / 0.588 | 0.605 / 0.605 | +0.008 / +0.008 |

## 4. Results under the honest rule and the corrected recipe (folds 2022, 2023)

Pooled r² by arm; "served set" is the served pickle's feature list for the position, fitted `leak_free`:

| arm | QB (n 95, 60 players) | RB (185, 119) | WR (303, 188) | TE (161, 104) |
|---|---:|---:|---:|---:|
| `ppg_t` alone | 0.333 | 0.548 | 0.624 | 0.592 |
| recent production, 3 columns | 0.363 | 0.574 | 0.660 | 0.605 |
| **served set (leak_free)** | 0.416 | 0.601 | 0.679 | 0.625 |
| served set, old recipe (reproduction) | 0.390 | 0.594 | 0.675 | 0.630 |
| 3 columns + opportunity | 0.373 | 0.570 | 0.661 | 0.569 |
| served set + opportunity | 0.416 | 0.595 | 0.679 | 0.589 |
| *exploratory:* 3 columns + xFP | 0.363 | 0.571 | 0.662 | 0.500 |
| *exploratory:* served set + xFP | 0.435 | 0.593 | 0.681 | 0.619 |

Paired differences on identical rows, 90% interval from 2,000 player-resampled draws, Δr²:

| pos | served − 3 columns | served + opportunity − served | old recipe − corrected recipe |
|---|---|---|---|
| QB | +0.052 [+0.015, +0.092] | +0.000 [−0.066, +0.055] | −0.025 [−0.053, +0.004] |
| RB | +0.027 [+0.005, +0.047] | −0.006 [−0.015, +0.002] | −0.007 [−0.017, +0.002] |
| WR | +0.020 [+0.007, +0.032] | +0.000 [−0.002, +0.002] | −0.004 [−0.008, −0.001] |
| TE | +0.020 [−0.007, +0.045] | −0.036 [−0.107, +0.011] | +0.005 [−0.016, +0.027] |

Per fold and per metric (RMSE, MAE, Spearman, top-k by season) are in the run's `report.md` and `results.json`;
`predictions.csv` holds one row per test row per arm.

## 5. The reading — stated as narrowly as the experiment supports

1. **The served feature set earns its place over three columns under the corrected procedure** at QB, RB and WR
   (intervals exclude zero) and by a similar point estimate at TE (interval reaches −0.007). That is a stronger
   statement than DG-162's, and it comes from a different procedure on different folds: DG-162's old-recipe result
   is reproduced exactly (§3), and under the OLD recipe on these same two folds the gain was smaller. Read it as
   "the corrected penalty selection lets the extra columns help", not as a revision of DG-162's measurement.
2. **The tested raw-rate ridge additions showed little gain.** Added to the served set, the four per-game
   opportunity rates change r² by an amount bounded within ±0.015 at RB and ±0.002 at WR, and by an undetectable
   amount at QB and TE (TE's point estimate is negative with a wide interval). **This does not prove opportunity
   information has no value.** It shows that four season-level rates, entered linearly into a ridge that already
   reads a season's PPG and games, add nothing a ridge can use. Weekly structure, nonlinearity, interactions with
   role, or a different estimand were not tested.
3. **The corrected recipe is at least as good as the served one on these folds** (WR detectably, the others
   within a hundredth), while being honest about where its penalty came from.
4. **The exploratory expected-points columns are not a candidate.** They are retrospective (§6). Their apparent
   QB gain over the served set (+0.020 [−0.002, +0.047]) is exactly the kind of number a retrospective statistic
   can produce, and it is not evidence.

## 6. What this does not support, and the caveats that travel with the numbers

- **Estimand.** Every arm forecasts E[two-season mean PPG | the player posted a qualifying season in t+1 or t+2].
  Whether he returns at all is not measured here; the annual artifact (item 3) is where events are explicit.
- **Two folds.** Under the corrected procedure the evaluable history is test seasons 2022 and 2023 — 95 QB rows
  from 60 players up to 303 WR rows from 188. Intervals of ±0.04 r² at QB are what that can say. A longer file,
  not a looser rule, is what would add folds.
- **The bootstrap is conditional on the fitted models.** Resampling players from fixed fits captures sampling
  uncertainty in the comparison; it does not capture model or season uncertainty, and it is not a forecast interval.
- **xFP is retrospective.** nflverse's ffopportunity documentation (read 2026-09-06) says the expected-points model
  "uses xgboost and tidymodels trained on public nflverse data from 2006-2020", overlapping feature seasons
  2018–2020 at play level; the model version behind each row is not recorded. The `opp_*` family carries no fitted
  weights. This distinction was raised by the orchestrator before the first run and is why the family is raw counts.
- **Top-k overlap is coarse** (k = 12 or 24 from `PRIMARY_NDCG_K`; one hit is 0.04–0.08) even when aggregated by
  season. Spearman is the ranking metric to read.
- **Third-party projections and rankings never enter an arm.** The gate is the contract's DG-173 class test; a
  mutation that disables it fails seven tests.
- **Splits reported, not touched (outside the review's named files):** `eval/te_role_risk_experiment.py:82`,
  `eval/qb_v3_walk_forward.py:131` and `eval/te_archetype_bakeoff.py:100` still split on `feature_season <
  test_year`. They are experiment harnesses owned by other tickets; the shared rule is one import away.

## 7. Reproduce

    cd ~/dg-wt/DG-177
    .venv/bin/python -m pytest -q tests/test_label_closure.py tests/test_leak_free_tuning.py \
        tests/test_dg177_veteran_candidate.py tests/test_dg177_opportunity_features.py tests/test_dg177_runner.py
    .venv/bin/python scripts/experiments/dg177_veteran_candidate.py --draws 2000      # ~15 min, new runs/<utc>/

The run directory holds `results.json` (every arm, fold, fit, delta and the provenance block), `predictions.csv`
(one row per test row per arm — the paired errors) and `report.md`.
