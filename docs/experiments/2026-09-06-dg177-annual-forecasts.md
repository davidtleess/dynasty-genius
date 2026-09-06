# DG-177 — Year-1 and year-2 veteran forecasts on the appearance event

**Date:** 2026-09-06 · **Lane:** Davids-MacBook-Pro-23481 · **Branch:** `ticket/DG-177` · **Run:**
`runs/20260906T154635Z/dg177_annual_forecasts/` (canonical, round 2) · **Report-only.** The round-1 run
`20260906T145606Z` is superseded; its tables are kept at the end of this report as a labelled historical comparator
and nothing in the main narrative rests on them. Codex's review of the canonical run (2026-09-06): provisional
research-input pass, not validation, not promotion. Labels come from a fresh pull of public nflverse
weekly player stats saved in the run directory with its sha; nothing served changed; nothing shared was written.
Review round 1, item 3, and the contract agreed with DG-178 the same morning.

## 1. The target, typed

| term | value |
|---|---|
| scope | regular season (`season_type == REG`) — a separately named target; DG-024's all-games `ppg_t` is untouched and stays the feature |
| scoring | nflverse weekly `fantasy_points_ppr`, the same column the assembler sums for the served feature. Alignment check: summing it over REG+POST reproduces the training file's `total_points_t` on all 3,384 rows, max difference 6e-14 |
| exposure | `games_j` = weeks with a weekly stat row in scope |
| event | A_j = appeared: `games_j >= 1` |
| quantities | `p_appear_year{j}`, `e_points_year{j}_given_appear`, `e_games_year{j}_given_appear`, `e_points_year{j} = p × e`, `e_games_year{j} = p × e`, all on the same rows and event |
| horizons | j = 1, 2 only; longer horizons are unsupported because they are unmeasured |
| clock | features through the feature season; a year-j label trains only when `feature_season + j <= last complete season` (2025) |
| zeros and blanks | a zero-appearance season is 0 games / 0 points with A_j false; an unfinished season is censored (NaN, flagged); an identity the source never saw is `unresolved_in_source` (NaN); a player without a 2025 feature row gets no forecast, reason `no_feature_row`, never 0 |

## 2. What was fitted, and how

Per position and horizon: an appearance classifier (median imputer, scaler, logistic regression; no hyper-parameter,
preprocessing on training rows only) and two ridges on rows that appeared — season points and games — with the
penalty chosen by the corrected leak-free selector at window j and the imputer fitted inside each inner fold, then a
median imputer on the whole training window and a Ridge at that penalty. Points below zero are clipped to zero and
games to the training range; the counts clipped are in each fit's record. Two feature arms: the served position
feature list, and the three-column recent-production set (`ppg_t`, `games_t`, `age`).

Baselines are training-only: the training appearance rate; last season's all-games points scaled by the training
window's aggregate retention ratio; the training mean of games among those who appeared.

Evaluation walks forward by feature season (2019–2023 for j = 1, 2020–2023 for j = 2). A fold whose training window
cannot support the leak-free selection is skipped with the reason: for j = 1 the 2019 fold (one training season) at
every position, plus QB 2019 on the 60-row floor; for j = 2 the 2020 and 2021 folds everywhere. Every exported
quantity is graded against its own label; top-k is averaged within forecast seasons.

## 3. The canonical result: the selection policy on run `20260906T154635Z`

The round-1 artifact chose its exported arm on the same outer folds it reported, nested arm names where
positions belong in its manifest, and filled missing weekly points with zero on the pull. Round 2 replaces all three:

- **Source completeness before "no row means no game".** `validate_weekly_source` proves every pulled season is
  present with its full regular-season week range and a credible player count, that (player, season, week, type)
  is unique, and that no scoring value or identity is missing; the pull no longer fills anything. The one shape it
  admits is nflverse's per-week placeholder row (no id, no position, zero points): 173 such rows over 2018–2025,
  dropped and counted in the manifest. An unattributed row that carries points is refused.
- **One explicit selection policy.** For each position, horizon and quantity (appearance probability, points given
  appearance, games given appearance) the policy is chosen from {training-only baseline, three-column ridge,
  blend at 0.25/0.5/0.75} on closed inner folds inside the training window — the ridge refit leak-free inside each
  inner fold, the baseline recomputed on inner training rows — and applied by the same function final scoring calls.
  Its outer-fold score is the evidence; the plain candidate and the served-feature arm remain exploratory.
- **The manifest** keeps arms and positions at their own levels, carries input and output hashes, the scoring arm,
  the source facts and the chosen policies, and is validated structurally before it is written.

**Policy evidence, year 1 (folds 2021–2023; Δ = policy − training-only baseline, 90% player-resampled):**

| pos | P(appear) Brier / base · AUC | unconditional points Δr² | ΔRMSE | policies chosen (2021 / 2022 / 2023, P · points · games) |
|---|---|---|---|---|
| QB | 0.091 / 0.099 · 0.77 | +0.015 [−0.009, +0.041] | −1.2 [−3.1, +0.8] | blend .5 · blend .5 · cand / blend .5 · blend .75 · cand / blend .5 · blend .75 · cand |
| RB | 0.116 / 0.145 · 0.81 | +0.053 [+0.028, +0.079] | −3.5 [−5.2, −1.8] | cand · cand · cand / cand · blend .75 · cand / cand · blend .75 · cand |
| WR | 0.119 / 0.150 · 0.83 | +0.030 [+0.013, +0.048] | −2.1 [−3.3, −0.9] | blend .5 · blend .75 · blend .75 / blend .75 · blend .75 · cand / blend .75 · blend .75 · cand |
| TE | 0.125 / 0.145 · 0.80 | +0.014 [−0.012, +0.043] | −0.7 [−1.9, +0.6] | blend .75 · cand · cand / cand · blend .75 · cand / cand · blend .75 · cand |

The 2020 fold is lost to nested selection (its training window holds no closed inner fold with a fittable
candidate). **Year 2 has no evaluable fold at any position on this file** for the same reason one season deeper;
the year-2 quantities are exported with their policy chosen on the full closed window (recorded in the manifest)
and are ungraded here. That is not a claim of beating or failing the baseline. The longer basic cohort (§ the
companion report) is where year 2 and beyond are graded.

## 4. The reading (canonical run)

1. **Year 1, folds 2021–2023.** The policy's unconditional season points beat the training-only persistence
   baseline within the reported 90% interval at RB (+0.053 [+0.028, +0.079] r²) and WR (+0.030 [+0.013, +0.048]);
   at QB (+0.015 [−0.009, +0.041]) and TE (+0.014 [−0.012, +0.043]) the interval includes zero and the result is
   inconclusive. The appearance probability has a lower historical Brier score than the base rate at all four positions; that is
   a point comparison without an interval and not a calibration proof, and the companion status record carries expected calibration error and reliability
   slope/intercept computed from the graded predictions.
2. **Year 2: zero evaluated policy folds** at every position on this file. The year-2 quantities are exported with
   their policy chosen on the full closed window and are ungraded here. That is a statement about the evaluable
   history of the 2018-based file, not about the forecast's quality either way. The basic-cohort report grades year 2.
3. **The policy chose a 0.75 blend with persistence for points at most positions and the ridge for games** (manifest
   `selection_policy.chosen`); where it picks the baseline that is model selection on closed inner folds, not a discount.

## 5. What this does not support

- **"Supported" means the closed history was sufficient to evaluate; it never means validated.** The
  machine-readable status beside the run (`dg177_annual_forecasts.evaluation_status.json`) names each horizon
  `evaluated`, `no_evaluated_policy_fold` or `unsupported`, and words the baseline comparison from its interval.
- **Bootstrap intervals are sampling uncertainty conditional on the fitted models** — players resampled from fixed
  fits. They are not model, selection or season uncertainty, and not forecast intervals.
- **Three folds for year 1, none for year 2.** A longer file, not a looser rule, is what adds folds; the basic
  cohort is that file.
- **No 2024 feature season** in the tracked training file (the assembler's two-season window), so year 1 has no
  2024→2025 fold and the final fits train through feature season 2023.
- **Composition** (`e_points = p × E[points | appear]`) holds by construction on identical rows and events. It does
  not by itself make a value.

## 6. Reproduce

    cd ~/dg-wt/DG-177
    .venv/bin/python -m pytest -q tests/test_dg177_annual_outcomes.py tests/test_dg177_annual_forecasts.py tests/test_dg177_annual_runner.py
    .venv/bin/python scripts/experiments/dg177_annual_forecasts.py --draws 2000     # network pull; ~5 min; new runs/<utc>/

Outputs: `annual_forecasts.csv` (candidate arm, 505 rows of the 2025 feature partition, both horizons),
`annual_forecasts_served_features.csv` (comparator arm), `manifest.json` (every typed term above plus shas),
`historical_predictions.csv`, `results.json`, `report.md`, `weekly_stats_snapshot.csv.gz` (the pulled labels).

## Appendix — round-1 comparator (run `20260906T145606Z`, SUPERSEDED): per-arm outer-fold scores under the old exported-arm choice

These tables are the round-1 measurement (both arms scored on outer folds; the exported arm was chosen on those same folds). They are retained for comparison only. **They are not the canonical evidence and the sentences that used to accompany them ("both horizons beat persistence", "year 2 rests on two folds") are withdrawn**: under the canonical procedure year 2 has zero evaluated policy folds on this file.


**Year 1** (forecast seasons 2021–2024):

| pos | arm | P(appear) Brier model / base · AUC · base rate | points\|appear Δr² | games\|appear Δr² | unconditional points Δr² | unconditional ΔRMSE |
|---|---|---|---|---|---|---|
| QB | served | 0.101 / 0.107 · 0.74 · 0.88 | +0.034 [−0.017, +0.092] | +0.375 [+0.267, +0.484] | +0.006 [−0.049, +0.056] | −0.5 [−4.8, +3.9] |
| QB | 3 columns | 0.102 / 0.107 · 0.72 · 0.88 | +0.025 [−0.021, +0.076] | +0.371 [+0.260, +0.481] | +0.013 [−0.022, +0.049] | −1.1 [−4.1, +1.9] |
| RB | served | 0.125 / 0.146 · 0.78 · 0.82 | +0.071 [+0.029, +0.118] | +0.216 [+0.164, +0.266] | +0.032 [+0.001, +0.061] | −2.1 [−4.0, −0.1] |
| RB | 3 columns | 0.118 / 0.146 · 0.80 · 0.82 | +0.069 [+0.028, +0.115] | +0.227 [+0.171, +0.281] | +0.055 [+0.031, +0.079] | −3.6 [−5.2, −1.9] |
| WR | served | 0.131 / 0.146 · 0.79 · 0.82 | +0.054 [+0.019, +0.091] | +0.194 [+0.144, +0.240] | +0.041 [+0.015, +0.067] | −2.8 [−4.7, −1.0] |
| WR | 3 columns | 0.119 / 0.146 · 0.82 · 0.82 | +0.041 [+0.009, +0.078] | +0.198 [+0.150, +0.243] | +0.030 [+0.008, +0.051] | −2.0 [−3.5, −0.5] |
| TE | served | 0.135 / 0.148 · 0.75 · 0.82 | +0.073 [+0.028, +0.121] | +0.281 [+0.228, +0.334] | +0.020 [−0.005, +0.046] | −0.9 [−2.1, +0.2] |
| TE | 3 columns | 0.128 / 0.148 · 0.79 · 0.82 | +0.070 [+0.026, +0.120] | +0.276 [+0.224, +0.329] | +0.020 [−0.003, +0.047] | −0.9 [−2.0, +0.1] |

**Year 2** (forecast seasons 2024–2025; two folds):

| pos | arm | P(appear) Brier model / base · AUC · base rate | points\|appear Δr² | games\|appear Δr² | unconditional points Δr² | unconditional ΔRMSE |
|---|---|---|---|---|---|---|
| QB | served | 0.199 / 0.188 · 0.64 · 0.75 | −0.026 [−0.074, +0.028] | +0.344 [+0.182, +0.507] | −0.081 [−0.161, −0.010] | +6.6 [+0.8, +12.1] |
| QB | 3 columns | 0.163 / 0.188 · 0.75 · 0.75 | −0.022 [−0.087, +0.046] | +0.363 [+0.202, +0.520] | −0.030 [−0.091, +0.027] | +2.5 [−2.1, +7.4] |
| RB | served | 0.184 / 0.232 · 0.77 · 0.65 | +0.043 [−0.032, +0.128] | +0.162 [+0.096, +0.230] | +0.077 [+0.030, +0.128] | −4.8 [−8.0, −1.8] |
| RB | 3 columns | 0.171 / 0.232 · 0.81 · 0.65 | +0.039 [−0.039, +0.132] | +0.158 [+0.105, +0.213] | +0.085 [+0.044, +0.127] | −5.3 [−7.8, −2.7] |
| WR | served | 0.184 / 0.217 · 0.75 · 0.68 | +0.094 [+0.047, +0.149] | +0.168 [+0.094, +0.240] | +0.087 [+0.024, +0.137] | −5.1 [−8.8, −1.3] |
| WR | 3 columns | 0.165 / 0.217 · 0.79 · 0.68 | +0.111 [+0.054, +0.178] | +0.162 [+0.101, +0.223] | +0.097 [+0.049, +0.137] | −5.8 [−8.7, −2.7] |
| TE | served | 0.156 / 0.202 · 0.80 · 0.73 | +0.173 [+0.059, +0.331] | +0.265 [+0.182, +0.350] | +0.027 [−0.030, +0.073] | −1.2 [−3.2, +1.2] |
| TE | 3 columns | 0.164 / 0.202 · 0.79 · 0.73 | +0.152 [+0.027, +0.323] | +0.255 [+0.179, +0.330] | +0.041 [−0.015, +0.088] | −1.8 [−3.9, +0.6] |

Per fold, calibration bins and every other metric are in the run's `results.json` and `report.md`;
`historical_predictions.csv` holds one row per graded test row per arm and horizon.

