# DG-177 — Year-1 and year-2 veteran forecasts on the appearance event

**Date:** 2026-09-06 · **Lane:** Davids-MacBook-Pro-23481 · **Branch:** `ticket/DG-177` · **Run:**
`runs/20260906T145606Z/dg177_annual_forecasts/` · **Report-only.** Labels come from a fresh pull of public nflverse
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

## 3. Historical results (pooled over evaluated folds; Δ = model − training-only baseline, 90% player-resampled intervals)

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

## 4. The reading

1. **The appearance probability is calibrated better than the base rate at every position and horizon except QB
   year 2 with the served list**, where it scores below the base rate (Brier 0.199 vs 0.188) on 118 rows. The
   three-column arm does not have that problem (0.163). Year-1 AUCs sit at 0.72–0.82 on a base rate of 0.82–0.88:
   most players appear, and the model mostly tells the rest apart.
2. **Unconditional season points beat persistence detectably at RB and WR on both horizons** (Δr² +0.03 to +0.10),
   **not detectably at TE**, and **not at QB** — where the served-list year-2 forecast is detectably worse than
   last season's points scaled by retention. A QB's next-but-one season is not something these features forecast
   better than "what he did, discounted".
3. **Games given appearance is where the features do most of their work** (Δr² +0.16 to +0.38 everywhere), which is
   largely the persistence baseline being a constant: any model that reads `games_t` beats a training mean. Read
   those rows as "exposure is forecastable from exposure", not as a modelling achievement.
4. **The three-column set is the exported candidate.** It matched or beat the served list on unconditional points
   in six of eight cells and never lost detectably, and it avoids the QB year-2 failure. That choice was made on
   these same folds — a selection between two arms, stated as such in the manifest — and both arms are exported.

## 5. What this does not support

- **Two arms, chosen on the test folds.** The candidate/comparator choice is a selection effect of the mildest kind
  (two candidates), but it is one; the historical numbers for the chosen arm are not an independent validation.
- **Year 2 rests on two folds** (forecast seasons 2024 and 2025). Intervals are wide and TE year-2 points|appear
  ranges from +0.03 to +0.33.
- **No 2024 feature season.** The tracked training file omits 2024 rows (the assembler's two-season window), so
  the year-1 evaluation has no 2024→2025 fold and the final year-1 fit trains through feature season 2023. A
  rebuild with per-season targets would add it; that is the assembler's change, not this increment's.
- **Bootstrap intervals are conditional on the fitted models** — fit uncertainty, not model or season uncertainty.
- **Clipping.** Negative conditional points are clipped to zero and games to the training range; counts are in
  each fit record. A clipped forecast is a forecast the linear model could not make sensibly.
- **Composition.** `e_points = p × E[points | appear]` holds by construction on identical rows and events. It does
  not by itself make a value; the replacement bar and the posture discount are the ranking lane's.

## 6. Reproduce

    cd ~/dg-wt/DG-177
    .venv/bin/python -m pytest -q tests/test_dg177_annual_outcomes.py tests/test_dg177_annual_forecasts.py tests/test_dg177_annual_runner.py
    .venv/bin/python scripts/experiments/dg177_annual_forecasts.py --draws 2000     # network pull; ~5 min; new runs/<utc>/

Outputs: `annual_forecasts.csv` (candidate arm, 505 rows of the 2025 feature partition, both horizons),
`annual_forecasts_served_features.csv` (comparator arm), `manifest.json` (every typed term above plus shas),
`historical_predictions.csv`, `results.json`, `report.md`, `weekly_stats_snapshot.csv.gz` (the pulled labels).
