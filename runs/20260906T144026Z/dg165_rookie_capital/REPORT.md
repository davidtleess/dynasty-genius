# DG-165 — draft-capital rookie candidate: the record

Run `runs/20260906T144026Z/dg165_rookie_capital` · git `9a6a7a4b` · model `dg165_rookie_capital_v2_hazard` · RESEARCH CANDIDATE — not served, not promoted, not merged

Every number below is rendered from `evaluation.json`, `manifest.json` and `rookie_scores_*.csv`; the prose
in `NOTES.md` interprets and carries no statistics of its own.

## Definitions

- **qualifying_season**: finished at or above the bar rank for the position by regular-season PPR total; bar = {'QB': 37, 'RB': 45, 'WR': 71, 'TE': 21}; tie-robust N-th largest (canonical DG-164 cells)
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
| season 1: P(qualifies) | 2005–2025 | 1662 | 0.22 | 0.18 | 0.841 (0.820, 0.860) | 0.1213 / 0.1708 | 0.3864 / 0.5255 |
| season 1: P(appears) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.791 (0.770, 0.812) | 0.1411 / 0.1721 | 0.4380 / 0.5282 |
| season 2: P(qualifies) | 2005–2024 | 1576 | 0.27 | 0.25 | 0.818 (0.798, 0.837) | 0.1424 / 0.1984 | 0.4466 / 0.5863 |
| season 2: P(appears) | 2005–2024 | 1576 | 0.76 | 0.74 | 0.775 (0.756, 0.796) | 0.1525 / 0.1843 | 0.4606 / 0.5555 |
| season 3: P(qualifies) | 2005–2023 | 1499 | 0.25 | 0.25 | 0.806 (0.785, 0.829) | 0.1436 / 0.1900 | 0.4466 / 0.5678 |
| season 3: P(appears) | 2005–2023 | 1499 | 0.66 | 0.65 | 0.747 (0.726, 0.769) | 0.1879 / 0.2253 | 0.5526 / 0.6429 |
| season 4: P(qualifies) | 2005–2022 | 1419 | 0.24 | 0.24 | 0.795 (0.772, 0.819) | 0.1386 / 0.1802 | 0.4376 / 0.5463 |
| season 4: P(appears) | 2005–2022 | 1419 | 0.58 | 0.57 | 0.746 (0.725, 0.768) | 0.2003 / 0.2435 | 0.5868 / 0.6801 |
| season 5: P(qualifies) | 2005–2021 | 1340 | 0.19 | 0.23 | 0.779 (0.752, 0.808) | 0.1285 / 0.1577 | 0.4122 / 0.4957 |
| season 5: P(appears) | 2005–2021 | 1340 | 0.49 | 0.47 | 0.743 (0.722, 0.766) | 0.2059 / 0.2504 | 0.5997 / 0.6940 |
| season 6: P(qualifies) | 2005–2020 | 1265 | 0.17 | 0.20 | 0.782 (0.751, 0.810) | 0.1182 / 0.1431 | 0.3835 / 0.4616 |
| season 6: P(appears) | 2005–2020 | 1265 | 0.40 | 0.41 | 0.735 (0.711, 0.758) | 0.2004 / 0.2418 | 0.5871 / 0.6768 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| season 1: E[season points] (unconditional; 0 without appearance) | 2005–2025 | 1662 | 53.25 | 41.57 | 55.21 / 70.82 | -11.68 |
| season 1: E[games] (unconditional) | 2005–2025 | 1662 | 7.65 | 6.71 | 4.93 / 6.05 | -0.94 |
| season 1: E[ppg | qualifies] (descriptive) | 2005–2025 | 362 | 11.64 | 10.50 | 3.49 / 3.64 | -1.13 |
| season 2: E[season points] (unconditional; 0 without appearance) | 2005–2024 | 1576 | 66.15 | 56.24 | 68.18 / 84.68 | -9.90 |
| season 2: E[games] (unconditional) | 2005–2024 | 1576 | 7.88 | 7.38 | 5.38 / 6.33 | -0.50 |
| season 2: E[ppg | qualifies] (descriptive) | 2005–2024 | 429 | 12.66 | 12.06 | 3.91 / 4.02 | -0.61 |
| season 3: E[season points] (unconditional; 0 without appearance) | 2005–2023 | 1499 | 61.82 | 57.27 | 72.72 / 87.07 | -4.55 |
| season 3: E[games] (unconditional) | 2005–2023 | 1499 | 6.96 | 6.91 | 5.66 / 6.53 | -0.04 |
| season 3: E[ppg | qualifies] (descriptive) | 2005–2023 | 382 | 13.10 | 12.55 | 3.92 / 4.19 | -0.55 |
| season 4: E[season points] (unconditional; 0 without appearance) | 2005–2022 | 1419 | 56.51 | 53.28 | 72.13 / 83.64 | -3.23 |
| season 4: E[games] (unconditional) | 2005–2022 | 1419 | 6.29 | 6.18 | 5.79 / 6.56 | -0.11 |
| season 4: E[ppg | qualifies] (descriptive) | 2005–2022 | 334 | 13.21 | 12.51 | 4.10 / 4.15 | -0.70 |
| season 5: E[season points] (unconditional; 0 without appearance) | 2005–2021 | 1340 | 48.61 | 49.39 | 72.09 / 82.36 | 0.78 |
| season 5: E[games] (unconditional) | 2005–2021 | 1340 | 5.24 | 5.28 | 5.78 / 6.44 | 0.04 |
| season 5: E[ppg | qualifies] (descriptive) | 2005–2021 | 260 | 13.60 | 12.92 | 4.05 / 4.19 | -0.68 |
| season 6: E[season points] (unconditional; 0 without appearance) | 2005–2020 | 1265 | 42.76 | 43.14 | 71.16 / 79.69 | 0.38 |
| season 6: E[games] (unconditional) | 2005–2020 | 1265 | 4.50 | 4.55 | 5.73 / 6.31 | 0.05 |
| season 6: E[ppg | qualifies] (descriptive) | 2005–2020 | 217 | 13.53 | 12.78 | 4.18 / 4.16 | -0.75 |

Cumulative:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| h = 1: P(any qualifying season in 1..h) | 2005–2025 | 1662 | 0.22 | 0.18 | 0.841 (0.822, 0.860) | 0.1213 / 0.1708 | 0.3864 / 0.5255 |
| h = 1: P(any appearance in 1..h) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.791 (0.770, 0.810) | 0.1411 / 0.1721 | 0.4380 / 0.5282 |
| h = 2: P(any qualifying season in 1..h) | 2005–2024 | 1576 | 0.32 | 0.30 | 0.830 (0.812, 0.846) | 0.1487 / 0.2183 | 0.4606 / 0.6284 |
| h = 2: P(any appearance in 1..h) | 2005–2024 | 1576 | 0.86 | 0.84 | 0.801 (0.778, 0.823) | 0.1024 / 0.1192 | 0.3265 / 0.4027 |
| h = 3: P(any qualifying season in 1..h) | 2005–2023 | 1499 | 0.36 | 0.35 | 0.826 (0.806, 0.844) | 0.1581 / 0.2312 | 0.4847 / 0.6550 |
| h = 3: P(any appearance in 1..h) | 2005–2023 | 1499 | 0.88 | 0.87 | 0.774 (0.749, 0.798) | 0.0969 / 0.1078 | 0.3150 / 0.3740 |
| h = 4: P(any qualifying season in 1..h) | 2005–2022 | 1419 | 0.39 | 0.39 | 0.815 (0.796, 0.834) | 0.1663 / 0.2386 | 0.5057 / 0.6702 |
| h = 4: P(any appearance in 1..h) | 2005–2022 | 1419 | 0.88 | 0.87 | 0.772 (0.747, 0.799) | 0.0971 / 0.1080 | 0.3148 / 0.3752 |
| h = 5: P(any qualifying season in 1..h) | 2005–2021 | 1340 | 0.41 | 0.42 | 0.816 (0.795, 0.835) | 0.1682 / 0.2419 | 0.5113 / 0.6768 |
| h = 5: P(any appearance in 1..h) | 2005–2021 | 1340 | 0.87 | 0.87 | 0.774 (0.749, 0.799) | 0.0988 / 0.1108 | 0.3192 / 0.3832 |
| h = 6: P(any qualifying season in 1..h) | 2005–2020 | 1265 | 0.42 | 0.43 | 0.816 (0.795, 0.836) | 0.1692 / 0.2442 | 0.5116 / 0.6815 |
| h = 6: P(any appearance in 1..h) | 2005–2020 | 1265 | 0.87 | 0.87 | 0.772 (0.748, 0.798) | 0.1020 / 0.1152 | 0.3277 / 0.3985 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| h = 1: E[qualifying seasons in 1..h] | 2005–2025 | 1662 | 0.22 | 0.18 | 0.35 / 0.41 | -0.03 |
| h = 2: E[qualifying seasons in 1..h] | 2005–2024 | 1576 | 0.49 | 0.43 | 0.61 / 0.76 | -0.05 |
| h = 3: E[qualifying seasons in 1..h] | 2005–2023 | 1499 | 0.74 | 0.68 | 0.86 / 1.09 | -0.06 |
| h = 4: E[qualifying seasons in 1..h] | 2005–2022 | 1419 | 0.96 | 0.92 | 1.09 / 1.40 | -0.05 |
| h = 5: E[qualifying seasons in 1..h] | 2005–2021 | 1340 | 1.15 | 1.14 | 1.30 / 1.67 | -0.01 |
| h = 6: E[qualifying seasons in 1..h] | 2005–2020 | 1265 | 1.32 | 1.33 | 1.52 / 1.94 | 0.01 |

## Sensitivity: unresolved identities labelled zero instead of unknown

| quantity | default (unknown excluded) | sensitivity arm (zero) | difference |
|---|---:|---:|---:|
| annual[1].p_qual_year.auc | 0.8412 | 0.8425 | 0.0013 |
| annual[1].p_qual_year.brier | 0.1213 | 0.1204 | -0.0009 |
| annual[3].p_qual_year.auc | 0.8063 | 0.8077 | 0.0015 |
| annual[1].e_points_year.rmse | 55.2088 | 55.0477 | -0.1611 |
| annual[3].e_points_year.rmse | 72.7176 | 72.4838 | -0.2338 |
| horizon[5].p_qual_h.auc | 0.8158 | 0.8166 | 0.0008 |
| horizon[5].e_qual_seasons_h.rmse | 1.3013 | 1.2958 | -0.0055 |

Largest absolute change in a 2026 score under the sensitivity arm:

| column | max abs change | player |
|---|---:|---|
| e_points_year2 | 1.8786 | Barion Brown |
| e_points_year3 | 1.7946 | CJ Williams |
| e_points_year4 | 1.6342 | CJ Williams |
| e_points_year5 | 1.5326 | CJ Williams |
| e_points_year6 | 1.3080 | CJ Williams |
| e_points_year1 | 1.1679 | Barion Brown |
| e_games_year2 | 0.3798 | CJ Williams |
| e_games_year1 | 0.3341 | CJ Williams |
| e_games_year3 | 0.3100 | CJ Williams |
| e_games_year4 | 0.2637 | CJ Williams |
| e_games_year5 | 0.2073 | CJ Williams |
| e_games_year6 | 0.1679 | CJ Williams |

## Scored class, first rows (see `ROOKIES_*.md`)

| pick | round | name | position | team | age_at_draft | identity_status | coverage_status | P(A y1) | E[pts y1] | E[games y1] | P(Q y1) | E[ppg|Q y1] | P(A y3) | E[pts y3] | P(Q y3) | P(A by 6) | P(Q_6) | E[N_6] | E[N_6] 90% fit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Fernando Mendoza | QB | LVR | 22 | resolved | scored | 0.98 | 181 | 12.7 | 0.89 | 13.7 | 0.98 | 212 | 0.87 | 1.00 | 0.99 | 5.10 | 4.77–5.35 |
| 3 | 1 | Jeremiyah Love | RB | ARI | 21 | resolved | scored | 0.98 | 233 | 14.5 | 0.89 | 16.0 | 0.99 | 240 | 0.87 | 1.00 | 1.00 | 5.26 | 4.94–5.46 |
| 4 | 1 | Carnell Tate | WR | TEN | 21 | resolved | scored | 0.99 | 172 | 14.3 | 0.79 | 12.5 | 0.98 | 193 | 0.83 | 1.00 | 0.96 | 4.74 | 4.33–5.05 |
| 8 | 1 | Jordyn Tyson | WR | NOR | 22 | resolved | scored | 0.99 | 146 | 13.6 | 0.71 | 11.8 | 0.97 | 166 | 0.76 | 1.00 | 0.91 | 4.15 | 3.80–4.49 |
| 13 | 1 | Ty Simpson | QB | LAR | 23 | resolved | scored | 0.93 | 102 | 9.3 | 0.64 | 12.2 | 0.88 | 123 | 0.58 | 1.00 | 0.91 | 3.40 | 3.08–3.78 |
| 16 | 1 | Kenyon Sadiq | TE | NYJ | 21 | resolved | scored | 0.99 | 99 | 13.2 | 0.51 | 9.7 | 0.97 | 131 | 0.74 | 1.00 | 0.95 | 3.77 | 3.43–4.14 |
| 20 | 1 | Makai Lemon | WR | PHI | 22 | resolved | scored | 0.98 | 114 | 12.8 | 0.59 | 11.1 | 0.94 | 139 | 0.66 | 1.00 | 0.85 | 3.43 | 3.22–3.71 |
| 24 | 1 | KC Concepcion | WR | CLE | 21 | resolved | scored | 0.97 | 110 | 12.9 | 0.59 | 11.0 | 0.94 | 141 | 0.67 | 1.00 | 0.86 | 3.49 | 3.28–3.75 |
| 30 | 1 | Omar Cooper Jr. | WR | NYJ | 22 | resolved | scored | 0.97 | 100 | 12.5 | 0.54 | 10.7 | 0.92 | 127 | 0.61 | 1.00 | 0.82 | 3.08 | 2.90–3.34 |
| 32 | 1 | Jadarian Price | RB | SEA | 22 | resolved | scored | 0.97 | 127 | 12.9 | 0.67 | 12.4 | 0.93 | 145 | 0.66 | 1.00 | 0.93 | 3.44 | 3.21–3.71 |
| 33 | 2 | De'Zhaun Stribling | WR | SFO | 23 | resolved | scored | 0.96 | 91 | 11.4 | 0.40 | 10.7 | 0.89 | 108 | 0.49 | 0.99 | 0.68 | 2.41 | 2.20–2.67 |
| 39 | 2 | Denzel Boston | WR | CLE | 22 | resolved | scored | 0.95 | 88 | 11.4 | 0.39 | 10.6 | 0.89 | 110 | 0.50 | 0.99 | 0.70 | 2.48 | 2.32–2.69 |

