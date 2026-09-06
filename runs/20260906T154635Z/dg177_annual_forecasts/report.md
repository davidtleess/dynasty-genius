# DG-177 — year-1 / year-2 forecast candidates on the appearance event

Scope `REG` · scoring `fantasy_points_ppr` · event: appeared: >= 1 stat-row game in the season · exposure: games: weeks with a weekly stat row in scope · horizons [1, 2] · git `e8fc30713985d77398bd4e797da3835acebb2d65`

Alignment of the pulled ALL-games points with the training file's `total_points_t` on the same player-seasons: 3384 rows, 100.0% within 0.01, max abs diff 0.000.


## QB · year1 · arm `served_features` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 52 | 47 / 43 | skipped — observed train rows 52 < minimum 60 |
| 2020 | 2021 | [2018, 2019] | 99 | 56 / 47 | evaluated |
| 2021 | 2022 | [2018, 2019, 2020] | 155 | 57 / 52 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 212 | 58 / 50 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 270 | 60 / 54 | evaluated |

P(appear): Brier 0.101 vs baseline 0.107 · AUC 0.740 · base rate 0.879 · mean predicted 0.862 · n 231

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 89.259 | 92.106 | -2.847 [-6.930, +1.537] | 0.477 | +0.034 [-0.017, +0.092] | +0.016 [-0.006, +0.039] | -0.042 [-0.083, +0.042] |
| games | appear | 4.500 | 5.685 | -1.185 [-1.603, -0.795] | 0.371 | +0.375 [+0.267, +0.484] | +0.563 [+0.417, +0.682] | +0.333 [+0.083, +0.417] |
| points (unconditional) | 91.370 | 91.850 | -0.481 [-4.837, +3.869] | 0.466 | +0.006 [-0.049, +0.056] | +0.027 [+0.001, +0.055] | -0.021 [-0.062, +0.062] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2020→2021: Brier 0.129 / 0.135; points|appear ΔRMSE +2.542 [-8.147, +13.785]; alpha points 10, games 1
- 2021→2022: Brier 0.078 / 0.085; points|appear ΔRMSE -4.321 [-12.001, +3.393]; alpha points 50, games 10
- 2022→2023: Brier 0.099 / 0.119; points|appear ΔRMSE -4.951 [-10.163, +0.484]; alpha points 200, games 100
- 2023→2024: Brier 0.098 / 0.092; points|appear ΔRMSE -3.658 [-11.650, +5.793]; alpha points 100, games 200

## QB · year1 · arm `recent_production_3col` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 52 | 47 / 43 | skipped — observed train rows 52 < minimum 60 |
| 2020 | 2021 | [2018, 2019] | 99 | 56 / 47 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2021 | 2022 | [2018, 2019, 2020] | 155 | 57 / 52 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 212 | 58 / 50 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 270 | 60 / 54 | evaluated |

Evidence = the SELECTION POLICY (chosen on closed inner folds): {"2021": {"p_appear": "blend_0.5", "points_given_appear": "blend_0.5", "games_given_appear": "candidate"}, "2022": {"p_appear": "blend_0.5", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}, "2023": {"p_appear": "blend_0.5", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}}


P(appear): Brier 0.091 vs baseline 0.099 · AUC 0.769 · base rate 0.891 · mean predicted 0.850 · n 175

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 92.365 | 94.959 | -2.594 [-5.275, +0.316] | 0.411 | +0.034 [-0.004, +0.075] | +0.010 [-0.003, +0.024] | +0.000 [-0.028, +0.056] |
| games | appear | 4.608 | 5.625 | -1.017 [-1.498, -0.583] | 0.324 | +0.331 [+0.202, +0.470] | +0.547 [+0.376, +0.689] | +0.306 [+0.056, +0.417] |
| points (unconditional) | 90.299 | 91.547 | -1.248 [-3.103, +0.762] | 0.451 | +0.015 [-0.009, +0.041] | +0.012 [-0.002, +0.026] | +0.000 [-0.028, +0.056] |

Exploratory (plain candidate arm, not evidence for the policy): unconditional points Δr² +0.012 [-0.025, +0.046], P Brier 0.091


Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2021→2022: Brier 0.083 / 0.085; points|appear ΔRMSE -3.965 [-7.345, -0.362]; alpha points 0.1, games 10 · policy {'p_appear': 'blend_0.5', 'points_given_appear': 'blend_0.5', 'games_given_appear': 'candidate'}
- 2022→2023: Brier 0.107 / 0.119; points|appear ΔRMSE -3.229 [-7.861, +1.387]; alpha points 0.1, games 0.1 · policy {'p_appear': 'blend_0.5', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}
- 2023→2024: Brier 0.084 / 0.092; points|appear ΔRMSE -0.749 [-6.128, +5.562]; alpha points 0.1, games 1 · policy {'p_appear': 'blend_0.5', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}

## QB · year2 · arm `served_features` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 52 | 56 / 42 | skipped — observed train rows 52 < minimum 60 |
| 2021 | 2023 | [2018, 2019] | 99 | 57 / 47 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | 2024 | [2018, 2019, 2020] | 155 | 58 / 44 | evaluated |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 212 | 60 / 45 | evaluated |

P(appear): Brier 0.199 vs baseline 0.188 · AUC 0.640 · base rate 0.754 · mean predicted 0.846 · n 118

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 95.595 | 93.540 | +2.055 [-2.118, +6.347] | 0.399 | -0.026 [-0.074, +0.028] | -0.021 [-0.052, +0.010] | -0.042 [-0.083, +0.083] |
| games | appear | 4.479 | 5.533 | -1.054 [-1.623, -0.514] | 0.346 | +0.344 [+0.182, +0.507] | +0.490 [+0.295, +0.659] | +0.292 [+0.042, +0.500] |
| points (unconditional) | 96.201 | 89.618 | +6.584 [+0.826, +12.083] | 0.387 | -0.081 [-0.161, -0.010] | -0.033 [-0.098, +0.031] | -0.042 [-0.125, +0.083] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2022→2024: Brier 0.199 / 0.185; points|appear ΔRMSE +1.309 [-3.904, +6.220]; alpha points 10, games 10
- 2023→2025: Brier 0.200 / 0.191; points|appear ΔRMSE +3.047 [-3.424, +9.898]; alpha points 200, games 500

## QB · year2 · arm `recent_production_3col` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 52 | 56 / 42 | skipped — observed train rows 52 < minimum 60 |
| 2021 | 2023 | [2018, 2019] | 99 | 57 / 47 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2022 | 2024 | [2018, 2019, 2020] | 155 | 58 / 44 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020]) |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 212 | 60 / 45 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020, 2021]) |

No fold evaluable.


## RB · year1 · arm `served_features` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 123 | 119 / 104 | skipped — leak_free alpha selection for points_year1: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 1; seasons present: [np.int64(2018)]) |
| 2020 | 2021 | [2018, 2019] | 242 | 136 / 111 | evaluated |
| 2021 | 2022 | [2018, 2019, 2020] | 378 | 131 / 112 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 509 | 132 / 104 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 641 | 119 / 99 | evaluated |

P(appear): Brier 0.125 vs baseline 0.146 · AUC 0.779 · base rate 0.822 · mean predicted 0.835 · n 518

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 65.223 | 69.713 | -4.490 [-7.297, -1.836] | 0.503 | +0.071 [+0.029, +0.118] | +0.006 [-0.014, +0.026] | +0.021 [-0.010, +0.094] |
| games | appear | 4.730 | 5.340 | -0.610 [-0.766, -0.450] | 0.213 | +0.216 [+0.164, +0.266] | +0.529 [+0.421, +0.623] | +0.115 [-0.021, +0.208] |
| points (unconditional) | 63.600 | 65.670 | -2.070 [-4.020, -0.088] | 0.513 | +0.032 [+0.001, +0.061] | +0.017 [-0.003, +0.036] | +0.031 [-0.021, +0.083] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2020→2021: Brier 0.126 / 0.151; points|appear ΔRMSE -3.251 [-7.498, +0.877]; alpha points 10, games 1000
- 2021→2022: Brier 0.123 / 0.125; points|appear ΔRMSE -6.602 [-12.726, -0.634]; alpha points 50, games 1000
- 2022→2023: Brier 0.135 / 0.170; points|appear ΔRMSE -1.904 [-7.347, +3.930]; alpha points 100, games 1000
- 2023→2024: Brier 0.115 / 0.140; points|appear ΔRMSE -6.529 [-14.027, +1.005]; alpha points 50, games 1000

## RB · year1 · arm `recent_production_3col` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 123 | 119 / 104 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2020 | 2021 | [2018, 2019] | 242 | 136 / 111 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2021 | 2022 | [2018, 2019, 2020] | 378 | 131 / 112 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 509 | 132 / 104 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 641 | 119 / 99 | evaluated |

Evidence = the SELECTION POLICY (chosen on closed inner folds): {"2021": {"p_appear": "candidate", "points_given_appear": "candidate", "games_given_appear": "candidate"}, "2022": {"p_appear": "candidate", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}, "2023": {"p_appear": "candidate", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}}


P(appear): Brier 0.116 vs baseline 0.145 · AUC 0.812 · base rate 0.825 · mean predicted 0.833 · n 382

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 67.163 | 71.392 | -4.230 [-7.254, -1.225] | 0.495 | +0.066 [+0.019, +0.118] | +0.013 [-0.004, +0.028] | +0.014 [-0.014, +0.083] |
| games | appear | 4.713 | 5.402 | -0.689 [-0.884, -0.487] | 0.233 | +0.241 [+0.176, +0.304] | +0.450 [+0.335, +0.548] | +0.167 [-0.028, +0.208] |
| points (unconditional) | 63.146 | 66.693 | -3.547 [-5.227, -1.819] | 0.539 | +0.053 [+0.028, +0.079] | +0.032 [+0.019, +0.048] | +0.028 [-0.014, +0.083] |

Exploratory (plain candidate arm, not evidence for the policy): unconditional points Δr² +0.053 [+0.020, +0.086], P Brier 0.116


Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2021→2022: Brier 0.103 / 0.125; points|appear ΔRMSE -2.839 [-7.390, +2.023]; alpha points 0.1, games 200 · policy {'p_appear': 'candidate', 'points_given_appear': 'candidate', 'games_given_appear': 'candidate'}
- 2022→2023: Brier 0.130 / 0.170; points|appear ΔRMSE -5.255 [-9.729, -0.512]; alpha points 0.1, games 200 · policy {'p_appear': 'candidate', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}
- 2023→2024: Brier 0.115 / 0.140; points|appear ΔRMSE -4.578 [-11.562, +2.101]; alpha points 0.1, games 200 · policy {'p_appear': 'candidate', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}

## RB · year2 · arm `served_features` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 123 | 136 / 90 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | 2023 | [2018, 2019] | 242 | 131 / 82 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | 2024 | [2018, 2019, 2020] | 378 | 132 / 81 | evaluated |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 509 | 119 / 81 | evaluated |

P(appear): Brier 0.184 vs baseline 0.232 · AUC 0.773 · base rate 0.645 · mean predicted 0.667 · n 251

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 81.127 | 83.899 | -2.772 [-7.602, +2.183] | 0.380 | +0.043 [-0.032, +0.128] | +0.028 [-0.015, +0.069] | +0.042 [-0.021, +0.167] |
| games | appear | 4.972 | 5.420 | -0.448 [-0.643, -0.256] | 0.140 | +0.162 [+0.096, +0.230] | +0.466 [+0.293, +0.629] | +0.188 [+0.021, +0.312] |
| points (unconditional) | 72.282 | 77.034 | -4.751 [-8.010, -1.773] | 0.433 | +0.077 [+0.030, +0.128] | +0.049 [+0.011, +0.088] | +0.000 [-0.042, +0.146] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2022→2024: Brier 0.198 / 0.244; points|appear ΔRMSE -10.159 [-18.413, -1.779]; alpha points 0.1, games 1000
- 2023→2025: Brier 0.170 / 0.217; points|appear ΔRMSE +4.303 [-2.858, +11.995]; alpha points 1, games 1000

## RB · year2 · arm `recent_production_3col` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 123 | 136 / 90 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2021 | 2023 | [2018, 2019] | 242 | 131 / 82 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2022 | 2024 | [2018, 2019, 2020] | 378 | 132 / 81 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020]) |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 509 | 119 / 81 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020, 2021]) |

No fold evaluable.


## WR · year1 · arm `served_features` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 192 | 189 / 148 | skipped — leak_free alpha selection for points_year1: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 1; seasons present: [np.int64(2018)]) |
| 2020 | 2021 | [2018, 2019] | 381 | 197 / 167 | evaluated |
| 2021 | 2022 | [2018, 2019, 2020] | 578 | 204 / 168 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 782 | 194 / 153 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 976 | 191 / 160 | evaluated |

P(appear): Brier 0.131 vs baseline 0.146 · AUC 0.787 · base rate 0.824 · mean predicted 0.823 · n 786

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 56.475 | 60.032 | -3.557 [-5.738, -1.315] | 0.587 | +0.054 [+0.019, +0.091] | +0.011 [-0.002, +0.024] | +0.031 [-0.021, +0.083] |
| games | appear | 4.504 | 5.014 | -0.511 [-0.644, -0.373] | 0.190 | +0.194 [+0.144, +0.240] | +0.462 [+0.377, +0.537] | +0.104 [-0.000, +0.198] |
| points (unconditional) | 53.920 | 56.745 | -2.825 [-4.675, -0.961] | 0.619 | +0.041 [+0.015, +0.067] | +0.020 [+0.009, +0.032] | +0.042 [-0.021, +0.094] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2020→2021: Brier 0.116 / 0.134; points|appear ΔRMSE -1.780 [-5.050, +1.547]; alpha points 10, games 50
- 2021→2022: Brier 0.166 / 0.146; points|appear ΔRMSE -5.951 [-13.194, +0.294]; alpha points 100, games 200
- 2022→2023: Brier 0.135 / 0.167; points|appear ΔRMSE -0.869 [-4.895, +3.065]; alpha points 100, games 200
- 2023→2024: Brier 0.105 / 0.137; points|appear ΔRMSE -5.556 [-8.821, -2.276]; alpha points 200, games 500

## WR · year1 · arm `recent_production_3col` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 192 | 189 / 148 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2020 | 2021 | [2018, 2019] | 381 | 197 / 167 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2021 | 2022 | [2018, 2019, 2020] | 578 | 204 / 168 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 782 | 194 / 153 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 976 | 191 / 160 | evaluated |

Evidence = the SELECTION POLICY (chosen on closed inner folds): {"2021": {"p_appear": "blend_0.5", "points_given_appear": "blend_0.75", "games_given_appear": "blend_0.75"}, "2022": {"p_appear": "blend_0.75", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}, "2023": {"p_appear": "blend_0.75", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}}


P(appear): Brier 0.119 vs baseline 0.150 · AUC 0.828 · base rate 0.817 · mean predicted 0.803 · n 589

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 54.469 | 57.735 | -3.266 [-5.427, -1.275] | 0.615 | +0.048 [+0.017, +0.086] | +0.013 [+0.005, +0.022] | +0.028 [-0.014, +0.083] |
| games | appear | 4.456 | 5.034 | -0.578 [-0.712, -0.444] | 0.214 | +0.217 [+0.172, +0.262] | +0.526 [+0.440, +0.604] | +0.083 [+0.014, +0.236] |
| points (unconditional) | 52.509 | 54.658 | -2.149 [-3.315, -0.917] | 0.636 | +0.030 [+0.013, +0.048] | +0.022 [+0.013, +0.032] | +0.028 [-0.028, +0.069] |

Exploratory (plain candidate arm, not evidence for the policy): unconditional points Δr² +0.032 [+0.009, +0.054], P Brier 0.118


Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2021→2022: Brier 0.130 / 0.146; points|appear ΔRMSE -4.566 [-10.430, +0.436]; alpha points 0.1, games 0.1 · policy {'p_appear': 'blend_0.5', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'blend_0.75'}
- 2022→2023: Brier 0.124 / 0.167; points|appear ΔRMSE -0.139 [-3.187, +2.917]; alpha points 0.1, games 0.1 · policy {'p_appear': 'blend_0.75', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}
- 2023→2024: Brier 0.104 / 0.137; points|appear ΔRMSE -4.619 [-7.106, -2.115]; alpha points 0.1, games 0.1 · policy {'p_appear': 'blend_0.75', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}

## WR · year2 · arm `served_features` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 192 | 197 / 135 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | 2023 | [2018, 2019] | 381 | 204 / 126 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | 2024 | [2018, 2019, 2020] | 578 | 194 / 128 | evaluated |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 782 | 191 / 135 | evaluated |

P(appear): Brier 0.184 vs baseline 0.217 · AUC 0.749 · base rate 0.683 · mean predicted 0.677 · n 385

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 62.262 | 67.914 | -5.652 [-8.291, -3.046] | 0.504 | +0.094 [+0.047, +0.149] | +0.020 [-0.011, +0.054] | +0.042 [-0.042, +0.125] |
| games | appear | 4.524 | 4.958 | -0.435 [-0.644, -0.231] | 0.168 | +0.168 [+0.094, +0.240] | +0.397 [+0.273, +0.513] | +0.146 [+0.021, +0.312] |
| points (unconditional) | 57.196 | 62.345 | -5.149 [-8.793, -1.339] | 0.540 | +0.087 [+0.024, +0.137] | +0.036 [+0.003, +0.071] | +0.062 [-0.062, +0.125] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2022→2024: Brier 0.190 / 0.225; points|appear ΔRMSE -5.485 [-9.596, -1.205]; alpha points 1, games 0.1
- 2023→2025: Brier 0.178 / 0.209; points|appear ΔRMSE -5.817 [-9.583, -1.772]; alpha points 0.1, games 200

## WR · year2 · arm `recent_production_3col` (k = 24)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 192 | 197 / 135 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2021 | 2023 | [2018, 2019] | 381 | 204 / 126 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2022 | 2024 | [2018, 2019, 2020] | 578 | 194 / 128 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020]) |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 782 | 191 / 135 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020, 2021]) |

No fold evaluable.


## TE · year1 · arm `served_features` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 105 | 102 / 88 | skipped — leak_free alpha selection for points_year1: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 1; seasons present: [np.int64(2018)]) |
| 2020 | 2021 | [2018, 2019] | 207 | 102 / 82 | evaluated |
| 2021 | 2022 | [2018, 2019, 2020] | 309 | 109 / 86 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 418 | 105 / 88 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 523 | 99 / 84 | evaluated |

P(appear): Brier 0.135 vs baseline 0.148 · AUC 0.754 · base rate 0.819 · mean predicted 0.830 · n 415

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 40.653 | 44.017 | -3.364 [-5.481, -1.300] | 0.577 | +0.073 [+0.028, +0.121] | +0.004 [-0.009, +0.019] | +0.063 [-0.042, +0.104] |
| games | appear | 4.000 | 4.713 | -0.713 [-0.863, -0.560] | 0.276 | +0.281 [+0.228, +0.334] | +0.582 [+0.470, +0.679] | +0.104 [-0.083, +0.229] |
| points (unconditional) | 40.375 | 41.311 | -0.936 [-2.094, +0.222] | 0.575 | +0.020 [-0.005, +0.046] | +0.020 [-0.001, +0.039] | +0.062 [-0.021, +0.104] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2020→2021: Brier 0.130 / 0.158; points|appear ΔRMSE -4.190 [-9.871, +1.601]; alpha points 10, games 1000
- 2021→2022: Brier 0.170 / 0.167; points|appear ΔRMSE -1.651 [-6.018, +2.751]; alpha points 10, games 500
- 2022→2023: Brier 0.137 / 0.136; points|appear ΔRMSE -2.214 [-7.318, +2.659]; alpha points 50, games 500
- 2023→2024: Brier 0.099 / 0.130; points|appear ΔRMSE -5.088 [-9.797, -0.640]; alpha points 50, games 500

## TE · year1 · arm `recent_production_3col` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2019 | 2020 | [2018] | 105 | 102 / 88 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2020 | 2021 | [2018, 2019] | 207 | 102 / 82 | skipped — policy selection for year 1: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2021 | 2022 | [2018, 2019, 2020] | 309 | 109 / 86 | evaluated |
| 2022 | 2023 | [2018, 2019, 2020, 2021] | 418 | 105 / 88 | evaluated |
| 2023 | 2024 | [2018, 2019, 2020, 2021, 2022] | 523 | 99 / 84 | evaluated |

Evidence = the SELECTION POLICY (chosen on closed inner folds): {"2021": {"p_appear": "blend_0.75", "points_given_appear": "candidate", "games_given_appear": "candidate"}, "2022": {"p_appear": "candidate", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}, "2023": {"p_appear": "candidate", "points_given_appear": "blend_0.75", "games_given_appear": "candidate"}}


P(appear): Brier 0.125 vs baseline 0.145 · AUC 0.796 · base rate 0.824 · mean predicted 0.826 · n 313

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 39.589 | 42.077 | -2.488 [-4.196, -0.680] | 0.590 | +0.053 [+0.015, +0.094] | +0.001 [-0.013, +0.014] | +0.083 [-0.028, +0.083] |
| games | appear | 3.960 | 4.745 | -0.784 [-0.951, -0.613] | 0.301 | +0.304 [+0.248, +0.361] | +0.602 [+0.493, +0.700] | +0.000 [-0.139, +0.250] |
| points (unconditional) | 39.421 | 40.091 | -0.670 [-1.898, +0.597] | 0.586 | +0.014 [-0.012, +0.043] | +0.018 [+0.003, +0.036] | +0.083 [-0.028, +0.111] |

Exploratory (plain candidate arm, not evidence for the policy): unconditional points Δr² +0.012 [-0.016, +0.042], P Brier 0.124


Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2021→2022: Brier 0.138 / 0.167; points|appear ΔRMSE -0.640 [-5.803, +5.023]; alpha points 0.1, games 200 · policy {'p_appear': 'blend_0.75', 'points_given_appear': 'candidate', 'games_given_appear': 'candidate'}
- 2022→2023: Brier 0.128 / 0.136; points|appear ΔRMSE -2.846 [-7.609, +1.323]; alpha points 0.1, games 200 · policy {'p_appear': 'candidate', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}
- 2023→2024: Brier 0.109 / 0.130; points|appear ΔRMSE -3.730 [-6.981, -0.760]; alpha points 0.1, games 200 · policy {'p_appear': 'candidate', 'points_given_appear': 'blend_0.75', 'games_given_appear': 'candidate'}

## TE · year2 · arm `served_features` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 105 | 102 / 63 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | 2023 | [2018, 2019] | 207 | 109 / 71 | skipped — leak_free alpha selection for points_year2: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | 2024 | [2018, 2019, 2020] | 309 | 105 / 72 | evaluated |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 418 | 99 / 76 | evaluated |

P(appear): Brier 0.156 vs baseline 0.202 · AUC 0.800 · base rate 0.725 · mean predicted 0.666 · n 204

| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |
|---|---:|---:|---|---:|---|---|---|
| points | appear | 46.304 | 53.483 | -7.179 [-12.242, -2.689] | 0.482 | +0.173 [+0.059, +0.331] | +0.020 [-0.016, +0.053] | +0.125 [-0.042, +0.167] |
| games | appear | 4.068 | 4.743 | -0.675 [-0.918, -0.435] | 0.261 | +0.265 [+0.182, +0.350] | +0.539 [+0.384, +0.677] | +0.167 [-0.042, +0.375] |
| points (unconditional) | 45.070 | 46.233 | -1.162 [-3.234, +1.182] | 0.482 | +0.027 [-0.030, +0.073] | -0.007 [-0.050, +0.035] | +0.042 [-0.042, +0.125] |

Per fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:

- 2022→2024: Brier 0.166 / 0.216; points|appear ΔRMSE -7.723 [-13.638, -2.059]; alpha points 10, games 500
- 2023→2025: Brier 0.144 / 0.188; points|appear ΔRMSE -6.622 [-13.961, +0.050]; alpha points 10, games 500

## TE · year2 · arm `recent_production_3col` (k = 12)

| test season | forecast season | train seasons | train obs | test obs / appeared | status |
|---|---|---|---:|---|---|
| 2020 | 2022 | [2018] | 105 | 102 / 63 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018]) |
| 2021 | 2023 | [2018, 2019] | 207 | 109 / 71 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019]) |
| 2022 | 2024 | [2018, 2019, 2020] | 309 | 105 / 72 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020]) |
| 2023 | 2025 | [2018, 2019, 2020, 2021] | 418 | 99 / 76 | skipped — policy selection for year 2: no inner validation season with closed training rows and a fittable candidate (seasons present: [2018, 2019, 2020, 2021]) |

No fold evaluable.


## Final forecasts exported (inference partition)

Candidate arm `recent_production_3col` — The exported candidate is the SELECTION POLICY over {baseline, recent_production_3col ridge, bounded blend}, chosen per position, horizon and quantity on closed inner folds inside the training window and applied by the same function final scoring calls; its outer-fold score is the evidence. recent_production_3col is the candidate arm because it matched or beat served_features on unconditional points in six of eight cells in round 1 and never lost detectably (that was a comparison on outer folds, so served_features stays an exploratory comparison, exported beside the candidate, not part of the policy space).

Feature season 2025; rows 505 ({'QB': 62, 'RB': 127, 'TE': 109, 'WR': 207}); identity {'resolved': 505}; players with no 2025 feature row receive no forecast (reason `no_feature_row`), never 0.

