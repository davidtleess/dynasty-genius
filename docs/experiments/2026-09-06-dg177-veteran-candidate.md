# DG-177 — A veteran forecast candidate, evaluated with information available at the time

**Date:** 2026-09-06 · **Lane:** Davids-MacBook-Pro-23481 (veteran forecasting seat) · **Branch:** `ticket/DG-177`
from origin/main `ecc260ef` · **Run:** `runs/20260906T133309Z/dg177_veteran_candidate/` · **Report-only.** Nothing served
was trained, promoted, restarted or written. Every input was read-only; every output is inside the run directory.

## 1. What the ticket asked and what was built

DG-162 found the product reads three columns (`ppg_t`, `games_t`, `age`) and that the other features buy little.
It measured that under a walk-forward one season stricter than necessary, and it measured no new football input.
This ticket asks for a reusable, honest evaluation path and one justified feature family tested through it.

Built, with tests written first (47 in `tests/test_dg177_*.py`, two guards mutation-checked):

- `src/dynasty_genius/eval/veteran_candidate.py` — the cutoff rule, a refusal for any training row whose label was
  not final at the forecast (`FutureLabelError`), the feature gate (delegates to the Engine B contract's
  future-season and DG-173 projection bans), the deployed recipe refit inside each window, a paired bootstrap that
  resamples players, skipped folds written as skipped, and run directories that are never overwritten.
- `src/dynasty_genius/eval/opportunity_features.py` — the family: raw realized opportunity per game from the
  warehouse's `ff_opportunity` table (targets, air yards, carries, pass attempts). Its expected-points columns are
  exposed separately as `xfp_*` and named exploratory (§6).
- `scripts/experiments/dg177_veteran_candidate.py` — the runner: five arms plus two exploratory arms per position,
  two cutoff rules, provenance that names the bytes, and a report that prints every fold and every arm.

## 2. The cutoff, and why it is not DG-162's

The label `avg_ppg_t1_t2` for a row with feature season *t* is the mean PPG over *t+1* and *t+2*
(`feature_assembly._calc_avg`), so it is final only when season *t+2* has been played. A forecast made after season
*s* may train on rows with **t + 2 ≤ s**. That is the primary rule here (`labels_known_at_cutoff`), and it is the
same admissibility the deployed trainer encodes as `no_shared_outcome_season` (DG-026) for a single test season —
a test asserts the two definitions agree for every test season used.

DG-162's `earn.py` used `feature_season <= s-3`, i.e. **t + 2 < s**. That forbids a training label season from
being a test *feature* season, which is not a leak: the test row's own outcome seasons (*s+1*, *s+2*) are still
untouched. It costs one training season per fold. Kept here as `window_closed_before_test` so DG-162 can be
reproduced exactly (§3), not used for the new measurement.

⚠ **Finding, not touched:** `src/dynasty_genius/eval/backtest_harness.py` `WalkForwardDriver._build_fold_data`
splits on `feature_season < test_year`. A training row at *s−1* is labelled from *s* and *s+1*; the test row at *s*
is labelled from *s+1* and *s+2*. They share an outcome season. That is the leak DG-026 fixed in the trainer and
did not fix in the harness. Another lane's file; reported to the orchestrator.

## 3. Reproduction of DG-162 §1 — exact

Same strict rule, same 60/10 row minimums, same median imputer and `RidgeCV(cv=5)` on the served grid, pooled
over the same test seasons. Every number matches to the precision DG-162 published:

| pos | n (this / DG-162) | `ppg_t` alone r² | served set r² | Δr² served − 3 columns |
|---|---|---|---|---|
| QB | 95 / 95 | 0.320 / 0.320 | 0.383 / 0.383 | +0.030 / +0.030 |
| RB | 284 / 284 | 0.572 / 0.572 | 0.600 / 0.600 | −0.000 / −0.000 |
| WR | 456 / 456 | 0.623 / 0.623 | 0.661 / 0.661 | +0.010 / +0.010 |
| TE | 244 / 244 | 0.588 / 0.588 | 0.605 / 0.605 | +0.008 / +0.008 |

The harness reproduces the prior work before it says anything new.

## 4. Results under the honest rule

Test seasons 2020–2023; a fold needs 60 training rows. **QB 2020 is skipped** (training on 2018 alone gives 40
eligible rows — 52 in the file, 12 with no observed outcome) and is written as skipped in the artifact. Everything
else is evaluated. Pooled r² by arm; "served set" is the served pickle's feature list for the position:

| arm | QB (n 141, 67 players) | RB (384, 169) | WR (616, 265) | TE (323, 143) |
|---|---:|---:|---:|---:|
| `ppg_t` alone | 0.344 | 0.575 | 0.617 | 0.597 |
| recent production, 3 columns | 0.381 | 0.586 | 0.641 | 0.606 |
| served set (deployed recipe) | 0.412 | 0.593 | 0.653 | 0.620 |
| 3 columns + opportunity | 0.405 | 0.584 | 0.641 | 0.584 |
| served set + opportunity | 0.433 | 0.592 | 0.650 | 0.606 |
| *exploratory:* 3 columns + xFP | 0.362 | 0.585 | 0.642 | 0.611 |
| *exploratory:* served set + xFP | 0.342 | 0.590 | 0.655 | 0.619 |

Paired differences on identical rows, 90% interval from 2,000 player-resampled draws. Δr² unless stated.

**Served set vs 3 columns** (DG-162's question, honest rule):

| pos | Δr² [90%] | ΔRMSE [90%] | detectable? |
|---|---|---|---|
| QB | +0.031 [−0.014, +0.077] | −0.116 [−0.272, +0.052] | no |
| RB | +0.007 [−0.009, +0.022] | −0.030 [−0.094, +0.032] | no |
| WR | +0.012 [+0.003, +0.020] | −0.050 [−0.087, −0.015] | yes, about a hundredth |
| TE | +0.014 [+0.006, +0.024] | −0.042 [−0.070, −0.016] | yes, about a hundredth |

**Opportunity family** — added to 3 columns, and added to the served set:

| pos | 3 col + opp vs 3 col, Δr² [90%] | served + opp vs served, Δr² [90%] | served + opp vs served, ΔSpearman [90%] |
|---|---|---|---|
| QB | +0.025 [−0.012, +0.059] | +0.021 [-0.024, +0.063] | +0.026 [-0.002, +0.052] |
| RB | −0.002 [−0.009, +0.005] | -0.001 [-0.006, +0.005] | +0.001 [-0.003, +0.005] |
| WR | +0.000 [−0.004, +0.004] | -0.003 [-0.008, +0.002] | -0.001 [-0.005, +0.002] |
| TE | −0.022 [−0.076, +0.018] | -0.014 [-0.045, +0.010] | -0.003 [-0.012, +0.007] |

Per fold at QB, served set + opportunity vs 3 columns, Δr²: 2021 −0.019 [−0.163, +0.130] · 2022 +0.091 [+0.038,
+0.143] · 2023 +0.073 [+0.019, +0.136]. Against the 3-column reference the pooled QB result is Δr² +0.052 [−0.001,
+0.106], ΔRMSE −0.197 [−0.384, +0.002], ΔSpearman +0.036 [+0.003, +0.071].

## 5. The reading

1. **DG-162's finding survives the honest cutoff.** The served feature set beats three columns detectably only at
   WR and TE, by about a hundredth of r², and not at QB or RB. Nothing here rehabilitates the usage features.
2. **The opportunity family earns nothing at RB or WR, and the null is bounded, not merely undetected.** At RB the
   family's effect over three columns is between −0.009 and +0.005 r²; at WR between −0.004 and +0.004. Those are
   the widths of the difference, resampling players — "equal to within a hundredth" rather than "we could not tell".
   Added to the served set it takes a little away at both (WR 0.653 → 0.650, TE 0.620 → 0.606).
3. **At TE the family may hurt.** 3 columns + opportunity is −0.022 r² with an interval reaching −0.076; RMSE rises
   0.065. The interval spans zero, so harm is not established, but nothing supports adding it.
4. **QB is the one place with any signal, and over the served set it is not detectable.** Served set +
   opportunity is the best QB arm on every pooled metric, and over *three columns* its Spearman gain excludes zero
   (+0.036 [+0.003, +0.071]). But that bundles the family with the served set's own extra columns. Over the served
   set alone the family is Δr² +0.021 [−0.024, +0.063] and ΔSpearman +0.026 [−0.002, +0.052], carried by the 2022
   fold (+0.121 [+0.043, +0.226]) with 2021 going the other way (−0.075 [−0.202, +0.039]) and 2023 flat (+0.012
   [−0.011, +0.035]). 141 rows, 67 players, three folds. The right description is *a candidate for one follow-up
   under the trainer's leak-free alpha selection*, not an edge and not a promotion case.
5. **The exploratory expected-points columns add nothing the served set does not already have** — over the
   served set they are WR +0.002 [−0.001, +0.004], TE −0.001 [−0.010, +0.009], RB −0.003 [−0.008, +0.002] — and at QB
   they are detectably worse (−0.069 [−0.134, −0.018]; over three columns ΔSpearman −0.027 [−0.053, −0.004]). Since
   they are retrospective (§6) this is reassuring rather than disappointing: the retrospective statistic did not
   smuggle in an advantage, and it is not a candidate.

## 6. What this does not support, and the caveats that travel with the numbers

- **Estimand.** Every arm forecasts E[PPG | the player posted a qualifying season in t+1 or t+2]. Whether he
  returns at all is the availability model's question (the P(plays) half of the served value) and is not measured
  here. A veteran ranking needs both; this increment measures one.
- **"Deployed" means the served pickle's recipe**, a median imputer and `RidgeCV` over the served grid with
  unshuffled 5-fold selection, refit inside each window. The trainer on main now selects alpha on player-clustered
  expanding-time folds (DG-027); the served artifact of 2026-08-31 predates that. Both facts are in the provenance
  block. The alpha selection inside the window is the same for every arm, so it cannot favour one.
- **xFP is retrospective.** nflverse's ffopportunity documentation (read 2026-09-06) says the expected-points model
  "uses xgboost and tidymodels trained on public nflverse data from 2006-2020". That window overlaps feature seasons
  2018–2020 at play level, and the model version behind each warehouse row is not recorded. The `xfp_*` arms are
  therefore labelled exploratory and are not point-in-time evidence. The `opp_*` family carries no fitted weights.
  This distinction was raised by the orchestrator before the run and is the reason the family is raw counts.
- **Sample.** QB trains on 80–169 rows per fold. Intervals of ±0.05 r² are what that sample can say. The 2020 fold
  is skipped for QB only, so QB pools three test seasons where the others pool four.
- **Top-k overlap is coarse** (k = 12 or 24 from the product's own `PRIMARY_NDCG_K`; one hit is 0.04–0.08) and its
  intervals are wide everywhere. Spearman is the ranking metric to read.
- **Population coverage of the family** is 98–100% of training rows per position and season (table in the run
  report). The unjoined 1–2% are median-imputed inside the fold.
- **Third-party projections and rankings never enter an arm.** The gate is the contract's own DG-173 class test;
  a mutation that disables it fails seven tests.

## 7. Reproduce

    cd ~/dg-wt/DG-177
    .venv/bin/python -m pytest -q tests/test_dg177_veteran_candidate.py tests/test_dg177_opportunity_features.py tests/test_dg177_runner.py
    .venv/bin/python scripts/experiments/dg177_veteran_candidate.py --draws 2000      # ~3.5 min, new runs/<utc>/

The run directory holds `results.json` (every arm, fold, delta and the provenance block), `predictions.csv`
(one row per test row per arm — the paired errors), and `report.md`.

## 8. What would come next, if the orchestrator wants it

- QB opportunity under the trainer's leak-free alpha recipe (`select_alpha_leak_free`), same folds, to see whether
  the signal in §5.4 survives honest penalty selection. Engineering, not a football decision.
- Nothing here is a promotion case. The served model is unchanged and should stay so on this evidence.
