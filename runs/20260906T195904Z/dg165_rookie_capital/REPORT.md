# DG-165 — draft-capital rookie candidate: the record

Run `runs/20260906T195904Z/dg165_rookie_capital` · git `32d0d717` · model `dg165_rookie_capital_v3_chain` · policy `inner_menu` · arm `dg165_rookie_capital_v3_chain:inner_menu:trend` · RESEARCH CANDIDATE — not served, not promoted, not merged

Every number below is rendered from `evaluation.json`, `manifest.json` and `rookie_scores_*.csv`; the prose
in `NOTES.md` interprets and carries no statistics of its own.

## Definitions

- **qualifying_season**: finished at or above the bar rank for the position by league-window points (Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021; earlier windows are a modelling convention, not a claim about David's historical league settings. POST records do not contribute outcomes.); bar = {'QB': 37, 'RB': 45, 'WR': 71, 'TE': 21}; tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance; cohort players are ranked at their DRAFT role every season, others at their weekly-stats position
- **appearance**: at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); a player without a stat row scored zero fantasy points that season
- **season_points**: regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance
- **games**: weeks with a weekly stat row, exactly 0 without an appearance
- **identity_unresolved**: no gsis_id in nflverse draft picks and no match in the players table or 1999-2025 rosters by draft key or name+year; labels NaN, never zero, except in the named sensitivity arm
- **scoring_scope**: championship window: Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021; earlier windows are a modelling convention, not a claim about David's historical league settings. POST records do not contribute outcomes.; scoring preset nflverse_default_ppr_championship_window_v1; league_scoring_exact=False — nflverse default-PPR championship-window research outcomes; exact-league scoring is unsupported pending complete attribution of lost-fumble scope, fum_rec_td, st_ff and st_fum_rec; nothing missing is fabricated as zero
- **scoring_preset**: nflverse_default_ppr_championship_window_v1
- **league_scoring_exact**: False
- **target_identity**: 049d2229c4ba06eececba66a083a777142f85ff0f459b0499912f49fa0ca3c6a
- **coverage_status**: qualified_research_game_complete_identified_rows
- **qualification_note**: coverage_status 'qualified_research_game_complete_identified_rows' means admitted game ids match the source and the exact unattributed-row quarantine is disclosed; it is NOT proof of perfect individual stats and must not be read as complete individual data
- **exposure_definition**: unique stat_record weeks within the outcome window
- **ppg_denominator**: league-window points / league-window stat-row games — NOT the served all-games denominator (DG-024); reconcile, do not absorb
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
| season 1: P(qualifies) | 2008–2025 | 1438 | 0.22 | 0.21 | 0.849 (0.828, 0.868) | 0.1182 / 0.1732 | 0.3775 / 0.5316 |
| season 1: P(appears) | 2008–2025 | 1438 | 0.79 | 0.77 | 0.807 (0.783, 0.830) | 0.1315 / 0.1693 | 0.4136 / 0.5225 |
| season 2: P(qualifies) | 2008–2024 | 1352 | 0.28 | 0.27 | 0.827 (0.807, 0.847) | 0.1416 / 0.2014 | 0.4420 / 0.5927 |
| season 2: P(appears) | 2008–2024 | 1352 | 0.77 | 0.75 | 0.775 (0.752, 0.797) | 0.1485 / 0.1799 | 0.4510 / 0.5458 |
| season 3: P(qualifies) | 2008–2023 | 1275 | 0.26 | 0.24 | 0.812 (0.789, 0.833) | 0.1449 / 0.1943 | 0.4494 / 0.5772 |
| season 3: P(appears) | 2008–2023 | 1275 | 0.67 | 0.64 | 0.746 (0.723, 0.771) | 0.1871 / 0.2225 | 0.5532 / 0.6371 |
| season 4: P(qualifies) | 2008–2022 | 1195 | 0.24 | 0.23 | 0.809 (0.783, 0.834) | 0.1357 / 0.1803 | 0.4267 / 0.5467 |
| season 4: P(appears) | 2008–2022 | 1195 | 0.59 | 0.56 | 0.738 (0.713, 0.761) | 0.2036 / 0.2422 | 0.5962 / 0.6774 |
| season 5: P(qualifies) | 2008–2021 | 1116 | 0.19 | 0.20 | 0.776 (0.749, 0.805) | 0.1307 / 0.1565 | 0.4142 / 0.4929 |
| season 5: P(appears) | 2008–2021 | 1116 | 0.50 | 0.47 | 0.729 (0.703, 0.753) | 0.2131 / 0.2508 | 0.6216 / 0.6948 |
| season 6: P(qualifies) | 2008–2020 | 1041 | 0.17 | 0.16 | 0.770 (0.740, 0.802) | 0.1212 / 0.1436 | 0.3896 / 0.4629 |
| season 6: P(appears) | 2008–2020 | 1041 | 0.40 | 0.38 | 0.700 (0.672, 0.727) | 0.2136 / 0.2431 | 0.6207 / 0.6793 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| season 1: E[season points] (unconditional; 0 without appearance) | 2008–2025 | 1438 | 51.76 | 49.80 | 51.57 / 68.61 | -1.96 |
| season 1: E[games] (unconditional) | 2008–2025 | 1438 | 7.44 | 7.04 | 4.54 / 5.74 | -0.39 |
| season 1: E[ppg | qualifies] (descriptive) | 2008–2025 | 318 | 11.89 | 12.26 | 3.37 / 3.60 | 0.37 |
| season 2: E[season points] (unconditional; 0 without appearance) | 2008–2024 | 1352 | 64.59 | 62.85 | 65.45 / 82.56 | -1.74 |
| season 2: E[games] (unconditional) | 2008–2024 | 1352 | 7.65 | 7.46 | 5.08 / 6.00 | -0.19 |
| season 2: E[ppg | qualifies] (descriptive) | 2008–2024 | 377 | 12.88 | 13.07 | 4.06 / 4.20 | 0.20 |
| season 3: E[season points] (unconditional; 0 without appearance) | 2008–2023 | 1275 | 60.21 | 56.38 | 69.31 / 84.08 | -3.83 |
| season 3: E[games] (unconditional) | 2008–2023 | 1275 | 6.79 | 6.38 | 5.36 / 6.17 | -0.41 |
| season 3: E[ppg | qualifies] (descriptive) | 2008–2023 | 336 | 13.20 | 13.41 | 4.05 / 4.29 | 0.21 |
| season 4: E[season points] (unconditional; 0 without appearance) | 2008–2022 | 1195 | 53.82 | 51.07 | 68.72 / 80.33 | -2.76 |
| season 4: E[games] (unconditional) | 2008–2022 | 1195 | 6.04 | 5.66 | 5.56 / 6.22 | -0.38 |
| season 4: E[ppg | qualifies] (descriptive) | 2008–2022 | 281 | 13.35 | 13.60 | 4.21 / 4.29 | 0.25 |
| season 5: E[season points] (unconditional; 0 without appearance) | 2008–2021 | 1116 | 46.64 | 44.21 | 69.69 / 79.36 | -2.44 |
| season 5: E[games] (unconditional) | 2008–2021 | 1116 | 5.07 | 4.83 | 5.58 / 6.12 | -0.24 |
| season 5: E[ppg | qualifies] (descriptive) | 2008–2021 | 215 | 13.85 | 13.24 | 4.53 / 4.38 | -0.61 |
| season 6: E[season points] (unconditional; 0 without appearance) | 2008–2020 | 1041 | 40.52 | 36.42 | 70.00 / 76.52 | -4.10 |
| season 6: E[games] (unconditional) | 2008–2020 | 1041 | 4.27 | 4.14 | 5.54 / 5.97 | -0.12 |
| season 6: E[ppg | qualifies] (descriptive) | 2008–2020 | 179 | 13.61 | 13.16 | 4.60 / 4.03 | -0.45 |

Cumulative:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| h = 1: P(any qualifying season in 1..h) | 2008–2025 | 1438 | 0.22 | 0.21 | 0.849 (0.828, 0.868) | 0.1182 / 0.1732 | 0.3775 / 0.5316 |
| h = 1: P(any appearance in 1..h) | 2008–2025 | 1438 | 0.79 | 0.77 | 0.807 (0.784, 0.829) | 0.1315 / 0.1693 | 0.4136 / 0.5225 |
| h = 2: P(any qualifying season in 1..h) | 2008–2024 | 1352 | 0.33 | 0.32 | 0.844 (0.825, 0.862) | 0.1435 / 0.2211 | 0.4463 / 0.6343 |
| h = 2: P(any appearance in 1..h) | 2008–2024 | 1352 | 0.87 | 0.86 | 0.821 (0.796, 0.845) | 0.0919 / 0.1114 | 0.2988 / 0.3834 |
| h = 3: P(any qualifying season in 1..h) | 2008–2023 | 1275 | 0.37 | 0.37 | 0.836 (0.818, 0.855) | 0.1541 / 0.2332 | 0.4738 / 0.6591 |
| h = 3: P(any appearance in 1..h) | 2008–2023 | 1275 | 0.89 | 0.87 | 0.790 (0.760, 0.819) | 0.0874 / 0.0997 | 0.2927 / 0.3527 |
| h = 4: P(any qualifying season in 1..h) | 2008–2022 | 1195 | 0.40 | 0.40 | 0.824 (0.802, 0.843) | 0.1636 / 0.2399 | 0.4983 / 0.6729 |
| h = 4: P(any appearance in 1..h) | 2008–2022 | 1195 | 0.89 | 0.88 | 0.782 (0.753, 0.816) | 0.0867 / 0.0970 | 0.2904 / 0.3454 |
| h = 5: P(any qualifying season in 1..h) | 2008–2021 | 1116 | 0.41 | 0.42 | 0.824 (0.802, 0.845) | 0.1651 / 0.2432 | 0.5029 / 0.6794 |
| h = 5: P(any appearance in 1..h) | 2008–2021 | 1116 | 0.89 | 0.88 | 0.784 (0.753, 0.815) | 0.0881 / 0.0993 | 0.2943 / 0.3513 |
| h = 6: P(any qualifying season in 1..h) | 2008–2020 | 1041 | 0.42 | 0.43 | 0.823 (0.799, 0.844) | 0.1666 / 0.2451 | 0.5041 / 0.6834 |
| h = 6: P(any appearance in 1..h) | 2008–2020 | 1041 | 0.88 | 0.88 | 0.776 (0.740, 0.806) | 0.0917 / 0.1023 | 0.3049 / 0.3587 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| h = 1: E[qualifying seasons in 1..h] | 2008–2025 | 1438 | 0.22 | 0.21 | 0.34 / 0.42 | -0.01 |
| h = 2: E[qualifying seasons in 1..h] | 2008–2024 | 1352 | 0.50 | 0.48 | 0.60 / 0.77 | -0.02 |
| h = 3: E[qualifying seasons in 1..h] | 2008–2023 | 1275 | 0.76 | 0.71 | 0.85 / 1.10 | -0.04 |
| h = 4: E[qualifying seasons in 1..h] | 2008–2022 | 1195 | 0.98 | 0.94 | 1.08 / 1.41 | -0.05 |
| h = 5: E[qualifying seasons in 1..h] | 2008–2021 | 1116 | 1.17 | 1.13 | 1.29 / 1.68 | -0.04 |
| h = 6: E[qualifying seasons in 1..h] | 2008–2020 | 1041 | 1.34 | 1.28 | 1.51 / 1.94 | -0.06 |

## Sensitivity: unresolved identities labelled zero instead of unknown

| quantity | default (unknown excluded) | sensitivity arm (zero) | difference |
|---|---:|---:|---:|
| annual[1].p_qual_year.auc | 0.8489 | 0.8499 | 0.0010 |
| annual[1].p_qual_year.brier | 0.1182 | 0.1176 | -0.0006 |
| annual[3].p_qual_year.auc | 0.8115 | 0.8115 | 0.0000 |
| annual[1].e_points_year.rmse | 51.5667 | 51.3611 | -0.2057 |
| annual[3].e_points_year.rmse | 69.3073 | 69.1845 | -0.1228 |
| horizon[5].p_qual_h.auc | 0.8240 | 0.8233 | -0.0007 |
| horizon[5].e_qual_seasons_h.rmse | 1.2864 | 1.2849 | -0.0015 |

Largest absolute change in a 2026 score under the sensitivity arm:

| column | max abs change | player |
|---|---:|---|
| e_points_year1 | 2.0116 | Carson Beck |
| e_points_year2 | 1.5494 | Cade Klubnik |
| e_points_year3 | 1.1572 | Carson Beck |
| e_points_year4 | 1.0539 | Cade Klubnik |
| e_points_year6 | 0.9477 | Cade Klubnik |
| e_points_year5 | 0.7705 | Cade Klubnik |
| e_games_year1 | 0.2018 | Carson Beck |
| e_games_year2 | 0.1631 | Dallen Bentley |
| e_games_year3 | 0.1625 | Dallen Bentley |
| e_games_year4 | 0.0967 | Dallen Bentley |
| e_games_year5 | 0.0919 | Dallen Bentley |
| e_games_year6 | 0.0830 | Cole Payton |

## Model policy and exploratory comparison

Declared policy: **inner_menu** — evidence status: retrospective historical evaluation with forecast cutoffs enforced; the policy selects, if at all, only inside each training window, but the policy menu itself was refined after inspecting these historical years, so this is not untouched independent confirmation

- `plain`: exploratory comparison against the declared policy on the same retrospective evaluation; never used to reassign the canonical evidence

Paired bootstrap of the difference (exploratory − policy), same test rows resampled once per replicate:

| exploratory arm | quantity | metric | policy | exploratory | difference (90% CI) | reading |
|---|---|---|---:|---:|---|---|
| plain | p_qual_year1 | brier | 0.1182 | 0.1203 | 0.0021 (0.0004, 0.0039) | positive difference favours the policy |
| plain | p_qual_year1 | log_loss | 0.3775 | 0.3831 | 0.0056 (0.0008, 0.0107) | positive difference favours the policy |
| plain | p_qual_year1 | auc | 0.8489 | 0.8506 | 0.0017 (-0.0017, 0.0050) | negative difference favours the policy |
| plain | p_appear_year1 | brier | 0.1315 | 0.1331 | 0.0016 (0.0000, 0.0032) | positive difference favours the policy |
| plain | e_points_year1 | rmse | 51.5667 | 52.8425 | 1.2757 (0.7130, 1.7816) | positive difference favours the policy |
| plain | p_qual_year3 | brier | 0.1449 | 0.1442 | -0.0007 (-0.0015, 0.0001) | positive difference favours the policy |
| plain | e_points_year3 | rmse | 69.3073 | 69.2619 | -0.0454 (-0.2745, 0.1830) | positive difference favours the policy |

Variant chosen inside each training window by the policy: 2008: plain, 2009: plain, 2010: trend_qb_r1, 2011: plain, 2012: plain, 2013: trend_qb_r1, 2014: trend, 2015: trend, 2016: trend, 2017: trend, 2018: trend, 2019: trend, 2020: trend, 2021: trend_qb_r1, 2022: trend, 2023: trend_qb_r1, 2024: trend_qb_r1, 2025: trend

## Recent-era QB / first-round calibration assessment (no correction applied)

| position | band | era | season | n | appearance bias (90%) | conditional points bias among appearers (90%) | unconditional points bias (90%) |
|---|---|---|---|---:|---|---|---|
| QB | R1 | 2005-15 | 1 | 21 | -0.074 (-0.094, -0.055) | -70.2 (-97.2, -43.8) | -76.2 (-104.9, -50.0) |
| QB | R1 | 2005-15 | 2 | 21 | -0.041 (-0.056, -0.029) | -49.6 (-76.0, -23.1) | -54.3 (-81.2, -26.0) |
| QB | R1 | 2016-25 | 1 | 35 | 0.040 (-0.025, 0.125) | -17.6 (-40.1, 4.4) | -11.6 (-36.8, 11.4) |
| QB | R1 | 2016-25 | 2 | 33 | -0.015 (-0.019, -0.010) | -22.8 (-54.1, 9.5) | -25.2 (-60.1, 6.9) |
| QB | all | 2005-15 | 1 | 91 | 0.019 (-0.050, 0.084) | -35.7 (-53.9, -18.4) | -20.6 (-30.4, -11.0) |
| QB | all | 2005-15 | 2 | 91 | 0.046 (-0.019, 0.114) | -31.8 (-51.3, -12.5) | -17.3 (-29.5, -6.2) |
| QB | all | 2016-25 | 1 | 119 | 0.045 (-0.023, 0.105) | -6.9 (-20.1, 6.5) | -1.3 (-10.9, 7.4) |
| QB | all | 2016-25 | 2 | 105 | -0.025 (-0.088, 0.036) | -12.9 (-31.1, 4.6) | -9.9 (-24.2, 3.9) |
| RB | R1 | 2005-15 | 1 | 17 | -0.038 (-0.045, -0.030) | -4.9 (-35.3, 24.2) | -9.5 (-39.3, 18.3) |
| RB | R1 | 2005-15 | 2 | 17 | -0.027 (-0.032, -0.023) | 20.0 (-15.5, 49.8) | 15.6 (-20.4, 47.9) |
| RB | R1 | 2016-25 | 1 | 14 | 0.055 (-0.018, 0.197) | -34.9 (-60.4, -7.8) | -24.2 (-54.4, 11.8) |
| RB | R1 | 2016-25 | 2 | 12 | -0.013 (-0.016, -0.010) | -15.4 (-54.3, 23.0) | -17.6 (-55.4, 21.4) |
| RB | all | 2005-15 | 1 | 172 | -0.062 (-0.106, -0.017) | -4.7 (-13.0, 3.7) | -6.8 (-14.1, 0.1) |
| RB | all | 2005-15 | 2 | 172 | -0.067 (-0.110, -0.019) | 5.9 (-4.9, 15.9) | -0.3 (-8.9, 8.3) |
| RB | all | 2016-25 | 1 | 215 | -0.035 (-0.070, 0.004) | 2.3 (-4.2, 9.1) | -0.2 (-6.4, 6.4) |
| RB | all | 2016-25 | 2 | 190 | 0.006 (-0.039, 0.050) | -0.9 (-10.6, 9.7) | -0.0 (-9.1, 8.8) |
| WR | R1 | 2005-15 | 1 | 29 | 0.080 (0.008, 0.184) | -30.1 (-48.6, -12.0) | -17.4 (-40.9, 5.3) |
| WR | R1 | 2005-15 | 2 | 29 | -0.002 (-0.039, 0.066) | -22.4 (-47.9, 2.2) | -22.2 (-46.1, 1.4) |
| WR | R1 | 2016-25 | 1 | 43 | -0.017 (-0.019, -0.015) | -1.7 (-20.0, 17.2) | -3.9 (-23.8, 16.0) |
| WR | R1 | 2016-25 | 2 | 39 | -0.024 (-0.026, -0.023) | 13.5 (-5.1, 29.8) | 9.8 (-8.3, 27.9) |
| WR | all | 2005-15 | 1 | 254 | -0.002 (-0.043, 0.039) | -6.4 (-12.3, -0.9) | -5.1 (-10.2, -0.4) |
| WR | all | 2005-15 | 2 | 254 | -0.009 (-0.048, 0.029) | -10.9 (-19.1, -2.8) | -9.4 (-16.1, -3.7) |
| WR | all | 2016-25 | 1 | 322 | -0.031 (-0.061, -0.001) | 5.8 (0.6, 11.2) | 3.1 (-1.8, 7.8) |
| WR | all | 2016-25 | 2 | 291 | -0.011 (-0.048, 0.026) | 8.6 (1.8, 15.6) | 6.0 (0.1, 11.7) |
| TE | R1 | 2005-15 | 1 | 5 | -0.032 (-0.042, -0.023) | -16.5 (-39.0, 13.7) | -18.7 (-49.3, 11.2) |
| TE | R1 | 2005-15 | 2 | 5 | -0.042 (-0.053, -0.032) | 9.4 (-36.5, 60.9) | 4.7 (-41.1, 56.6) |
| TE | R1 | 2016-25 | 1 | 11 | -0.016 (-0.019, -0.012) | -31.6 (-55.7, -6.7) | -33.1 (-61.1, -7.1) |
| TE | R1 | 2016-25 | 2 | 9 | -0.031 (-0.039, -0.023) | 9.1 (-8.8, 30.6) | 5.4 (-13.8, 28.8) |
| TE | all | 2005-15 | 1 | 124 | -0.027 (-0.087, 0.032) | 3.1 (-2.3, 8.4) | 2.0 (-2.3, 6.3) |
| TE | all | 2005-15 | 2 | 124 | -0.051 (-0.109, 0.012) | 1.9 (-7.4, 10.5) | -0.8 (-8.1, 6.0) |
| TE | all | 2016-25 | 1 | 141 | 0.008 (-0.035, 0.055) | 4.9 (-1.4, 10.4) | 3.4 (-1.7, 8.6) |
| TE | all | 2016-25 | 2 | 125 | -0.035 (-0.083, 0.010) | 12.7 (5.2, 20.2) | 8.5 (1.8, 14.9) |

## Scored class, first rows (see `ROOKIES_*.md`)

| pick | round | name | position | team | age_at_draft | identity_status | coverage_status | P(A y1) | E[pts y1] | E[games y1] | P(Q y1) | E[ppg|Q y1] | P(A y3) | E[pts y3] | P(Q y3) | P(A by 6) | P(Q_6) | E[N_6] | E[N_6] 90% fit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Fernando Mendoza | QB | LVR | 22 | resolved | scored | 0.99 | 196 | 13.3 | 0.92 | 15.7 | 0.98 | 212 | 0.86 | 1.00 | 0.99 | 5.01 | 4.64–5.28 |
| 3 | 1 | Jeremiyah Love | RB | ARI | 21 | resolved | scored | 0.99 | 253 | 15.3 | 0.95 | 18.2 | 0.99 | 248 | 0.87 | 1.00 | 1.00 | 5.20 | 4.72–5.44 |
| 4 | 1 | Carnell Tate | WR | TEN | 21 | resolved | scored | 0.99 | 182 | 14.4 | 0.84 | 14.4 | 0.98 | 183 | 0.84 | 1.00 | 0.95 | 4.80 | 4.35–5.14 |
| 8 | 1 | Jordyn Tyson | WR | NOR | 22 | resolved | scored | 0.99 | 158 | 14.0 | 0.78 | 13.6 | 0.97 | 161 | 0.78 | 1.00 | 0.92 | 4.29 | 3.95–4.65 |
| 13 | 1 | Ty Simpson | QB | LAR | 23 | resolved | scored | 0.95 | 122 | 10.4 | 0.78 | 13.8 | 0.89 | 128 | 0.62 | 1.00 | 0.93 | 3.65 | 3.31–4.04 |
| 16 | 1 | Kenyon Sadiq | TE | NYJ | 21 | resolved | scored | 0.99 | 113 | 13.7 | 0.59 | 11.1 | 0.97 | 134 | 0.75 | 1.00 | 0.93 | 3.94 | 3.55–4.33 |
| 20 | 1 | Makai Lemon | WR | PHI | 22 | resolved | scored | 0.99 | 128 | 13.4 | 0.69 | 12.7 | 0.94 | 138 | 0.70 | 1.00 | 0.86 | 3.62 | 3.33–3.94 |
| 24 | 1 | KC Concepcion | WR | CLE | 21 | resolved | scored | 0.98 | 123 | 13.4 | 0.66 | 12.6 | 0.94 | 139 | 0.69 | 1.00 | 0.85 | 3.62 | 3.32–3.92 |
| 30 | 1 | Omar Cooper Jr. | WR | NYJ | 22 | resolved | scored | 0.98 | 115 | 13.2 | 0.64 | 12.3 | 0.93 | 127 | 0.65 | 1.00 | 0.82 | 3.27 | 2.99–3.57 |
| 32 | 1 | Jadarian Price | RB | SEA | 22 | resolved | scored | 0.98 | 144 | 13.8 | 0.78 | 13.9 | 0.94 | 154 | 0.74 | 1.00 | 0.94 | 3.60 | 3.30–3.92 |
| 33 | 2 | De'Zhaun Stribling | WR | SFO | 23 | resolved | scored | 0.98 | 107 | 12.2 | 0.53 | 12.1 | 0.89 | 109 | 0.55 | 1.00 | 0.72 | 2.73 | 2.45–3.11 |
| 39 | 2 | Denzel Boston | WR | CLE | 22 | resolved | scored | 0.97 | 103 | 12.1 | 0.50 | 12.1 | 0.89 | 111 | 0.54 | 1.00 | 0.72 | 2.73 | 2.47–3.06 |

