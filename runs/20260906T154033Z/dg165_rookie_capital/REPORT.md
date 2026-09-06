# DG-165 — draft-capital rookie candidate: the record

Run `runs/20260906T154033Z/dg165_rookie_capital` · git `cd9bc693` · model `dg165_rookie_capital_v3_chain` · policy `inner_menu` · arm `dg165_rookie_capital_v3_chain:inner_menu:trend` · RESEARCH CANDIDATE — not served, not promoted, not merged

Every number below is rendered from `evaluation.json`, `manifest.json` and `rookie_scores_*.csv`; the prose
in `NOTES.md` interprets and carries no statistics of its own.

## Definitions

- **qualifying_season**: finished at or above the bar rank for the position by regular-season PPR total; bar = {'QB': 37, 'RB': 45, 'WR': 71, 'TE': 21}; tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance
- **appearance**: at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); a player without a stat row scored zero fantasy points that season
- **season_points**: regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance
- **games**: weeks with a weekly stat row, exactly 0 without an appearance
- **identity_unresolved**: no gsis_id in nflverse draft picks and no match in the players table or 1999-2025 rosters by draft key or name+year; labels NaN, never zero, except in the named sensitivity arm
- **scoring_scope**: regular season only; PPR as in nflverse weekly player stats
- **exposure_definition**: stat-row games (weeks with a weekly stat row)
- **ppg_denominator**: REG-season PPR points / stat-row games — NOT the served all-games denominator (DG-024); reconcile, do not absorb
- **seasons**: NFL season j = 1 is the rookie season = forecast_year; E[N_h] counts qualifying seasons in 1..h

- **forecast cutoff**: 2026-09-01 (pre-season 2026, after the NFL draft) · **label window**: labels through NFL season 2025; NFL season j = 1 is the rookie season = 2026

## Cohort

| item | value |
|---|---:|
| seasons | [1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] |
| skill_rows | 2238 |
| with_gsis_id | 2130 |
| without_gsis_id | 108 |
| resolution_of_missing_ids | {'players:name+year': 55, 'unresolved': 45, 'rosters:entry_year+draft_number': 4, 'players:draft_year+pick': 4} |
| unresolved_kept_with_nan_labels | 45 |
| duplicate_gsis_dropped | 0 |
| missing_age | 108 |
| rows | 2238 |

## Headline out-of-time results

Per season (see `EVALUATION.md` for every quantity, slice and calibration table):

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| season 1: P(qualifies) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.841 (0.819, 0.859) | 0.1196 / 0.1708 | 0.3822 / 0.5255 |
| season 1: P(appears) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.793 (0.772, 0.814) | 0.1403 / 0.1721 | 0.4364 / 0.5282 |
| season 2: P(qualifies) | 2005–2024 | 1576 | 0.27 | 0.26 | 0.818 (0.798, 0.836) | 0.1420 / 0.1984 | 0.4458 / 0.5863 |
| season 2: P(appears) | 2005–2024 | 1576 | 0.76 | 0.74 | 0.776 (0.756, 0.796) | 0.1523 / 0.1843 | 0.4600 / 0.5555 |
| season 3: P(qualifies) | 2005–2023 | 1499 | 0.25 | 0.25 | 0.806 (0.785, 0.829) | 0.1438 / 0.1900 | 0.4469 / 0.5678 |
| season 3: P(appears) | 2005–2023 | 1499 | 0.66 | 0.65 | 0.742 (0.721, 0.764) | 0.1898 / 0.2253 | 0.5565 / 0.6429 |
| season 4: P(qualifies) | 2005–2022 | 1419 | 0.24 | 0.23 | 0.796 (0.773, 0.819) | 0.1388 / 0.1802 | 0.4367 / 0.5463 |
| season 4: P(appears) | 2005–2022 | 1419 | 0.58 | 0.57 | 0.741 (0.718, 0.763) | 0.2024 / 0.2435 | 0.5927 / 0.6801 |
| season 5: P(qualifies) | 2005–2021 | 1340 | 0.19 | 0.20 | 0.772 (0.745, 0.800) | 0.1306 / 0.1577 | 0.4151 / 0.4957 |
| season 5: P(appears) | 2005–2021 | 1340 | 0.49 | 0.48 | 0.733 (0.711, 0.756) | 0.2096 / 0.2504 | 0.6104 / 0.6940 |
| season 6: P(qualifies) | 2005–2020 | 1265 | 0.17 | 0.18 | 0.767 (0.737, 0.796) | 0.1209 / 0.1431 | 0.3903 / 0.4616 |
| season 6: P(appears) | 2005–2020 | 1265 | 0.40 | 0.42 | 0.722 (0.697, 0.746) | 0.2067 / 0.2418 | 0.6023 / 0.6768 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| season 1: E[season points] (unconditional; 0 without appearance) | 2005–2025 | 1662 | 53.25 | 50.22 | 53.89 / 70.82 | -3.03 |
| season 1: E[games] (unconditional) | 2005–2025 | 1662 | 7.65 | 7.18 | 4.83 / 6.05 | -0.47 |
| season 1: E[ppg | qualifies] (descriptive) | 2005–2025 | 362 | 11.64 | 11.76 | 3.39 / 3.64 | 0.12 |
| season 2: E[season points] (unconditional; 0 without appearance) | 2005–2024 | 1576 | 66.15 | 63.94 | 67.58 / 84.68 | -2.20 |
| season 2: E[games] (unconditional) | 2005–2024 | 1576 | 7.88 | 7.54 | 5.37 / 6.33 | -0.33 |
| season 2: E[ppg | qualifies] (descriptive) | 2005–2024 | 429 | 12.66 | 12.83 | 3.92 / 4.02 | 0.17 |
| season 3: E[season points] (unconditional; 0 without appearance) | 2005–2023 | 1499 | 61.82 | 59.87 | 72.61 / 87.07 | -1.94 |
| season 3: E[games] (unconditional) | 2005–2023 | 1499 | 6.96 | 6.68 | 5.71 / 6.53 | -0.28 |
| season 3: E[ppg | qualifies] (descriptive) | 2005–2023 | 382 | 13.10 | 13.02 | 3.93 / 4.19 | -0.08 |
| season 4: E[season points] (unconditional; 0 without appearance) | 2005–2022 | 1419 | 56.51 | 54.29 | 72.15 / 83.64 | -2.22 |
| season 4: E[games] (unconditional) | 2005–2022 | 1419 | 6.29 | 6.10 | 5.82 / 6.56 | -0.19 |
| season 4: E[ppg | qualifies] (descriptive) | 2005–2022 | 334 | 13.21 | 13.06 | 4.10 / 4.15 | -0.14 |
| season 5: E[season points] (unconditional; 0 without appearance) | 2005–2021 | 1340 | 48.61 | 47.85 | 72.31 / 82.36 | -0.77 |
| season 5: E[games] (unconditional) | 2005–2021 | 1340 | 5.24 | 5.11 | 5.83 / 6.44 | -0.13 |
| season 5: E[ppg | qualifies] (descriptive) | 2005–2021 | 260 | 13.60 | 13.68 | 4.11 / 4.19 | 0.08 |
| season 6: E[season points] (unconditional; 0 without appearance) | 2005–2020 | 1265 | 42.76 | 41.67 | 71.70 / 79.69 | -1.09 |
| season 6: E[games] (unconditional) | 2005–2020 | 1265 | 4.50 | 4.62 | 5.79 / 6.31 | 0.12 |
| season 6: E[ppg | qualifies] (descriptive) | 2005–2020 | 217 | 13.53 | 13.05 | 4.33 / 4.16 | -0.48 |

Cumulative:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| h = 1: P(any qualifying season in 1..h) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.841 (0.822, 0.859) | 0.1196 / 0.1708 | 0.3822 / 0.5255 |
| h = 1: P(any appearance in 1..h) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.793 (0.772, 0.812) | 0.1403 / 0.1721 | 0.4364 / 0.5282 |
| h = 2: P(any qualifying season in 1..h) | 2005–2024 | 1576 | 0.32 | 0.31 | 0.829 (0.811, 0.846) | 0.1486 / 0.2183 | 0.4608 / 0.6284 |
| h = 2: P(any appearance in 1..h) | 2005–2024 | 1576 | 0.86 | 0.84 | 0.804 (0.782, 0.826) | 0.1021 / 0.1192 | 0.3258 / 0.4027 |
| h = 3: P(any qualifying season in 1..h) | 2005–2023 | 1499 | 0.36 | 0.36 | 0.825 (0.806, 0.844) | 0.1576 / 0.2312 | 0.4848 / 0.6550 |
| h = 3: P(any appearance in 1..h) | 2005–2023 | 1499 | 0.88 | 0.86 | 0.776 (0.752, 0.801) | 0.0968 / 0.1078 | 0.3150 / 0.3740 |
| h = 4: P(any qualifying season in 1..h) | 2005–2022 | 1419 | 0.39 | 0.40 | 0.817 (0.797, 0.835) | 0.1658 / 0.2386 | 0.5052 / 0.6702 |
| h = 4: P(any appearance in 1..h) | 2005–2022 | 1419 | 0.88 | 0.86 | 0.773 (0.748, 0.799) | 0.0971 / 0.1080 | 0.3155 / 0.3752 |
| h = 5: P(any qualifying season in 1..h) | 2005–2021 | 1340 | 0.41 | 0.42 | 0.816 (0.796, 0.836) | 0.1677 / 0.2419 | 0.5106 / 0.6768 |
| h = 5: P(any appearance in 1..h) | 2005–2021 | 1340 | 0.87 | 0.87 | 0.772 (0.747, 0.797) | 0.0991 / 0.1108 | 0.3208 / 0.3832 |
| h = 6: P(any qualifying season in 1..h) | 2005–2020 | 1265 | 0.42 | 0.43 | 0.818 (0.797, 0.838) | 0.1682 / 0.2442 | 0.5097 / 0.6815 |
| h = 6: P(any appearance in 1..h) | 2005–2020 | 1265 | 0.87 | 0.86 | 0.769 (0.744, 0.794) | 0.1024 / 0.1152 | 0.3297 / 0.3985 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| h = 1: E[qualifying seasons in 1..h] | 2005–2025 | 1662 | 0.22 | 0.21 | 0.35 / 0.41 | -0.01 |
| h = 2: E[qualifying seasons in 1..h] | 2005–2024 | 1576 | 0.49 | 0.47 | 0.61 / 0.76 | -0.02 |
| h = 3: E[qualifying seasons in 1..h] | 2005–2023 | 1499 | 0.74 | 0.71 | 0.86 / 1.09 | -0.03 |
| h = 4: E[qualifying seasons in 1..h] | 2005–2022 | 1419 | 0.96 | 0.94 | 1.09 / 1.40 | -0.02 |
| h = 5: E[qualifying seasons in 1..h] | 2005–2021 | 1340 | 1.15 | 1.14 | 1.30 / 1.67 | -0.01 |
| h = 6: E[qualifying seasons in 1..h] | 2005–2020 | 1265 | 1.32 | 1.31 | 1.52 / 1.94 | -0.01 |

## Sensitivity: unresolved identities labelled zero instead of unknown

| quantity | default (unknown excluded) | sensitivity arm (zero) | difference |
|---|---:|---:|---:|
| annual[1].p_qual_year.auc | 0.8408 | 0.8421 | 0.0013 |
| annual[1].p_qual_year.brier | 0.1196 | 0.1186 | -0.0011 |
| annual[3].p_qual_year.auc | 0.8057 | 0.8066 | 0.0009 |
| annual[1].e_points_year.rmse | 53.8869 | 53.7147 | -0.1722 |
| annual[3].e_points_year.rmse | 72.6129 | 72.2611 | -0.3518 |
| horizon[5].p_qual_h.auc | 0.8164 | 0.8154 | -0.0010 |
| horizon[5].e_qual_seasons_h.rmse | 1.3012 | 1.2963 | -0.0049 |

Largest absolute change in a 2026 score under the sensitivity arm:

| column | max abs change | player |
|---|---:|---|
| e_points_year1 | 2.3225 | Carson Beck |
| e_points_year2 | 1.6157 | Cole Payton |
| e_points_year3 | 1.3416 | Carson Beck |
| e_points_year4 | 1.1346 | Cole Payton |
| e_points_year6 | 1.0160 | Cole Payton |
| e_points_year5 | 0.8905 | Carson Beck |
| e_games_year1 | 0.2323 | Carson Beck |
| e_games_year3 | 0.2294 | Dallen Bentley |
| e_games_year2 | 0.2092 | Dallen Bentley |
| e_games_year4 | 0.1443 | Dallen Bentley |
| e_games_year5 | 0.1361 | Dallen Bentley |
| e_games_year6 | 0.0923 | Cole Payton |

## Model policy and exploratory comparison

Declared policy: **inner_menu** — independent of the policy choice: the policy was declared before the outer loop and selects, if at all, only inside each training window

- `plain`: exploratory comparison against the declared policy; not an independent confirmation and never used to reassign the canonical evidence

Paired bootstrap of the difference (exploratory − policy), same test rows resampled once per replicate:

| exploratory arm | quantity | metric | policy | exploratory | difference (90% CI) | reading |
|---|---|---|---:|---:|---|---|
| plain | p_qual_year1 | brier | 0.1196 | 0.1211 | 0.0015 (0.0001, 0.0029) | positive difference favours the policy |
| plain | p_qual_year1 | log_loss | 0.3822 | 0.3860 | 0.0038 (-0.0003, 0.0078) | positive difference favours the policy |
| plain | p_qual_year1 | auc | 0.8408 | 0.8416 | 0.0008 (-0.0025, 0.0041) | negative difference favours the policy |
| plain | p_appear_year1 | brier | 0.1403 | 0.1411 | 0.0008 (-0.0004, 0.0019) | positive difference favours the policy |
| plain | e_points_year1 | rmse | 53.8869 | 55.2088 | 1.3219 (0.7895, 1.8065) | positive difference favours the policy |
| plain | p_qual_year3 | brier | 0.1438 | 0.1434 | -0.0004 (-0.0011, 0.0003) | positive difference favours the policy |
| plain | e_points_year3 | rmse | 72.6129 | 72.7615 | 0.1487 (-0.0999, 0.3894) | positive difference favours the policy |

Variant chosen inside each training window by the policy: 2005: plain, 2006: plain, 2007: plain, 2008: trend, 2009: plain, 2010: trend_qb_r1, 2011: plain, 2012: plain, 2013: plain, 2014: trend, 2015: trend, 2016: trend, 2017: trend, 2018: trend, 2019: trend, 2020: trend_qb_r1, 2021: trend, 2022: trend, 2023: trend, 2024: trend, 2025: trend

## Recent-era QB / first-round calibration assessment (no correction applied)

| position | band | era | season | n | appearance bias (90%) | conditional points bias among appearers (90%) | unconditional points bias (90%) |
|---|---|---|---|---:|---|---|---|
| QB | R1 | 2005-15 | 1 | 29 | -0.037 (-0.080, 0.023) | -55.6 (-82.6, -29.3) | -57.0 (-83.1, -32.7) |
| QB | R1 | 2005-15 | 2 | 29 | -0.056 (-0.070, -0.044) | -22.2 (-46.6, 2.4) | -29.1 (-54.4, -4.3) |
| QB | R1 | 2016-25 | 1 | 35 | 0.021 (-0.037, 0.100) | -23.4 (-50.1, -0.1) | -19.9 (-42.0, 5.1) |
| QB | R1 | 2016-25 | 2 | 33 | -0.019 (-0.025, -0.015) | -23.1 (-56.5, 11.4) | -26.4 (-59.6, 7.6) |
| QB | all | 2005-15 | 1 | 128 | -0.008 (-0.071, 0.054) | -25.8 (-39.7, -13.3) | -16.8 (-25.3, -7.9) |
| QB | all | 2005-15 | 2 | 128 | 0.042 (-0.018, 0.100) | -15.8 (-31.8, -0.9) | -9.1 (-19.8, 0.7) |
| QB | all | 2016-25 | 1 | 119 | 0.013 (-0.050, 0.077) | -8.8 (-23.1, 5.0) | -4.8 (-13.9, 4.4) |
| QB | all | 2016-25 | 2 | 105 | -0.014 (-0.076, 0.045) | -9.1 (-30.5, 11.6) | -7.6 (-22.4, 6.1) |
| RB | R1 | 2005-15 | 1 | 26 | -0.038 (-0.046, -0.030) | -9.1 (-36.1, 16.5) | -14.0 (-40.8, 11.8) |
| RB | R1 | 2005-15 | 2 | 26 | -0.054 (-0.061, -0.047) | 29.3 (-0.5, 58.0) | 18.3 (-12.7, 45.7) |
| RB | R1 | 2016-25 | 1 | 14 | 0.052 (-0.023, 0.192) | -34.6 (-63.8, -8.0) | -24.0 (-58.0, 10.5) |
| RB | R1 | 2016-25 | 2 | 12 | -0.017 (-0.020, -0.015) | -17.4 (-57.9, 24.5) | -20.8 (-65.9, 22.1) |
| RB | all | 2005-15 | 1 | 229 | -0.045 (-0.087, 0.001) | -4.1 (-12.1, 3.9) | -5.7 (-12.1, 1.1) |
| RB | all | 2005-15 | 2 | 229 | -0.009 (-0.050, 0.035) | 0.8 (-9.3, 10.9) | -2.4 (-10.1, 5.6) |
| RB | all | 2016-25 | 1 | 215 | -0.079 (-0.117, -0.044) | 5.7 (-1.6, 12.9) | -0.4 (-6.9, 6.0) |
| RB | all | 2016-25 | 2 | 190 | -0.027 (-0.071, 0.019) | -0.9 (-11.7, 9.8) | -2.8 (-12.0, 5.8) |
| WR | R1 | 2005-15 | 1 | 42 | 0.050 (-0.000, 0.121) | -22.6 (-39.1, -5.1) | -14.6 (-31.0, 2.5) |
| WR | R1 | 2005-15 | 2 | 42 | -0.019 (-0.045, 0.029) | -11.6 (-30.9, 8.8) | -14.3 (-34.0, 7.8) |
| WR | R1 | 2016-25 | 1 | 43 | 0.010 (-0.014, 0.057) | -5.7 (-25.0, 15.5) | -2.2 (-23.8, 19.0) |
| WR | R1 | 2016-25 | 2 | 39 | -0.023 (-0.025, -0.021) | 18.0 (-1.1, 38.3) | 14.3 (-4.7, 32.3) |
| WR | all | 2005-15 | 1 | 347 | -0.002 (-0.038, 0.030) | -5.9 (-11.4, -0.8) | -5.3 (-9.7, -0.9) |
| WR | all | 2005-15 | 2 | 347 | -0.026 (-0.061, 0.006) | -7.7 (-14.7, -0.2) | -7.7 (-13.8, -2.3) |
| WR | all | 2016-25 | 1 | 322 | -0.049 (-0.079, -0.018) | 4.8 (-1.3, 10.5) | 1.8 (-3.6, 7.2) |
| WR | all | 2016-25 | 2 | 291 | -0.015 (-0.050, 0.020) | 9.4 (2.3, 16.8) | 6.4 (0.5, 12.7) |
| TE | R1 | 2005-15 | 1 | 9 | -0.030 (-0.039, -0.022) | -16.9 (-39.6, 3.3) | -18.8 (-40.4, 2.0) |
| TE | R1 | 2005-15 | 2 | 9 | -0.046 (-0.055, -0.037) | 2.3 (-23.6, 30.5) | -2.9 (-29.4, 26.4) |
| TE | R1 | 2016-25 | 1 | 11 | -0.011 (-0.015, -0.008) | -33.9 (-58.0, -8.6) | -35.0 (-60.9, -9.4) |
| TE | R1 | 2016-25 | 2 | 9 | -0.025 (-0.032, -0.019) | 12.9 (-7.3, 38.4) | 9.6 (-10.1, 33.9) |
| TE | all | 2005-15 | 1 | 161 | 0.003 (-0.048, 0.057) | -1.9 (-7.3, 2.7) | -1.5 (-5.5, 2.3) |
| TE | all | 2005-15 | 2 | 161 | -0.035 (-0.087, 0.016) | -3.6 (-12.4, 4.2) | -5.3 (-11.5, 0.9) |
| TE | all | 2016-25 | 1 | 141 | 0.008 (-0.035, 0.058) | 5.8 (-0.9, 12.0) | 4.1 (-1.7, 9.4) |
| TE | all | 2016-25 | 2 | 125 | -0.037 (-0.084, 0.015) | 14.0 (6.4, 20.8) | 9.9 (3.4, 16.7) |

## Scored class, first rows (see `ROOKIES_*.md`)

| pick | round | name | position | team | age_at_draft | identity_status | coverage_status | P(A y1) | E[pts y1] | E[games y1] | P(Q y1) | E[ppg|Q y1] | P(A y3) | E[pts y3] | P(Q y3) | P(A by 6) | P(Q_6) | E[N_6] | E[N_6] 90% fit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Fernando Mendoza | QB | LVR | 22 | resolved | scored | 0.99 | 203 | 14.2 | 0.93 | 15.2 | 0.98 | 223 | 0.88 | 1.00 | 0.99 | 5.06 | 4.68–5.32 |
| 3 | 1 | Jeremiyah Love | RB | ARI | 21 | resolved | scored | 0.99 | 265 | 16.5 | 0.95 | 18.1 | 1.00 | 255 | 0.87 | 1.00 | 1.00 | 5.23 | 4.81–5.48 |
| 4 | 1 | Carnell Tate | WR | TEN | 21 | resolved | scored | 0.99 | 196 | 15.9 | 0.88 | 14.2 | 0.98 | 205 | 0.86 | 1.00 | 0.97 | 4.90 | 4.48–5.16 |
| 8 | 1 | Jordyn Tyson | WR | NOR | 22 | resolved | scored | 0.99 | 170 | 15.2 | 0.81 | 13.6 | 0.97 | 179 | 0.80 | 1.00 | 0.93 | 4.36 | 3.98–4.69 |
| 13 | 1 | Ty Simpson | QB | LAR | 23 | resolved | scored | 0.95 | 125 | 10.9 | 0.75 | 13.8 | 0.92 | 138 | 0.62 | 1.00 | 0.91 | 3.60 | 3.23–4.06 |
| 16 | 1 | Kenyon Sadiq | TE | NYJ | 21 | resolved | scored | 0.99 | 119 | 14.5 | 0.60 | 11.0 | 0.98 | 142 | 0.74 | 1.00 | 0.94 | 3.84 | 3.41–4.25 |
| 20 | 1 | Makai Lemon | WR | PHI | 22 | resolved | scored | 0.99 | 137 | 14.4 | 0.70 | 12.7 | 0.95 | 152 | 0.70 | 1.00 | 0.87 | 3.60 | 3.32–3.91 |
| 24 | 1 | KC Concepcion | WR | CLE | 21 | resolved | scored | 0.98 | 131 | 14.2 | 0.68 | 12.5 | 0.95 | 153 | 0.70 | 1.00 | 0.87 | 3.61 | 3.35–3.91 |
| 30 | 1 | Omar Cooper Jr. | WR | NYJ | 22 | resolved | scored | 0.98 | 122 | 14.0 | 0.63 | 12.3 | 0.94 | 139 | 0.65 | 1.00 | 0.82 | 3.21 | 2.94–3.52 |
| 32 | 1 | Jadarian Price | RB | SEA | 22 | resolved | scored | 0.98 | 151 | 14.5 | 0.76 | 14.2 | 0.95 | 159 | 0.69 | 1.00 | 0.93 | 3.52 | 3.25–3.80 |
| 33 | 2 | De'Zhaun Stribling | WR | SFO | 23 | resolved | scored | 0.97 | 115 | 13.0 | 0.53 | 12.4 | 0.91 | 121 | 0.56 | 1.00 | 0.73 | 2.73 | 2.41–3.07 |
| 39 | 2 | Denzel Boston | WR | CLE | 22 | resolved | scored | 0.97 | 109 | 12.9 | 0.51 | 12.2 | 0.90 | 122 | 0.55 | 1.00 | 0.73 | 2.73 | 2.48–3.03 |

