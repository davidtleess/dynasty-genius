# DG-177 — veteran forecast candidate, evaluated at the cutoff

Rule: `labels_known_at_cutoff` · reference arms: ['recent_production_3col', 'deployed_recipe'] · test seasons: [2020, 2021, 2022, 2023] · git: `e680e48b57a0a4eaff882bad270ac01b3f509190`

Recipe: `leak_free` for every arm except ['deployed_recipe_reproduction'] (`deployed_reproduction`).

Deltas are metric(arm) − metric(reference) on identical rows, 90% interval from a bootstrap that resamples players. RMSE lower is better; r², Spearman and top-k overlap higher is better.


## QB (k = 12)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 40 / 40 | 43 / 43 | skipped — train rows 40 < minimum 60 |
| 2021 | [2018, 2019] | 80 / 49 | 46 / 46 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | [2018, 2019, 2020] | 123 / 59 | 46 / 46 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 169 / 71 | 49 / 49 | evaluated |

Alpha selected per fold for the reference arms: 2022: {'recent_production_3col': 200.0, 'deployed_recipe': 10.0} · 2023: {'recent_production_3col': 500.0, 'deployed_recipe': 500.0}


**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 95 | 4.915 | 3.751 | 0.333 | 0.634 | 0.542 |
| `recent_production_3col` | 95 | 4.802 | 3.580 | 0.363 | 0.648 | 0.625 |
| `deployed_recipe` | 95 | 4.601 | 3.384 | 0.416 | 0.674 | 0.625 |
| `recent_production_3col+opportunity` | 95 | 4.767 | 3.590 | 0.373 | 0.646 | 0.542 |
| `deployed_recipe+opportunity` | 95 | 4.599 | 3.444 | 0.416 | 0.674 | 0.542 |
| `exploratory:recent_production_3col+xfp` | 95 | 4.806 | 3.617 | 0.363 | 0.648 | 0.583 |
| `exploratory:deployed_recipe+xfp` | 95 | 4.523 | 3.343 | 0.435 | 0.698 | 0.625 |
| `deployed_recipe_reproduction` | 95 | 4.699 | 3.532 | 0.390 | 0.654 | 0.583 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.113 [-0.225, +0.440] | -0.030 [-0.121, +0.061] | -0.014 [-0.078, +0.048] | -0.083 [-0.208, +0.083] | 60 |
| `deployed_recipe` | -0.201 [-0.347, -0.055] | +0.052 [+0.015, +0.092] | +0.026 [-0.004, +0.060] | +0.000 [-0.083, +0.083] | 60 |
| `recent_production_3col+opportunity` | -0.036 [-0.264, +0.196] | +0.009 [-0.058, +0.067] | -0.002 [-0.040, +0.036] | -0.083 [-0.125, +0.083] | 60 |
| `deployed_recipe+opportunity` | -0.203 [-0.507, +0.122] | +0.053 [-0.037, +0.129] | +0.026 [-0.019, +0.071] | -0.083 [-0.125, +0.083] | 60 |
| `exploratory:recent_production_3col+xfp` | +0.003 [-0.053, +0.062] | -0.001 [-0.016, +0.015] | +0.000 [-0.012, +0.013] | -0.042 [-0.083, +0.042] | 60 |
| `exploratory:deployed_recipe+xfp` | -0.279 [-0.387, -0.165] | +0.072 [+0.043, +0.107] | +0.050 [+0.022, +0.085] | +0.000 [-0.083, +0.042] | 60 |
| `deployed_recipe_reproduction` | -0.103 [-0.286, +0.105] | +0.027 [-0.028, +0.079] | +0.006 [-0.038, +0.051] | -0.042 [-0.125, +0.083] | 60 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | +0.036 [-0.038, +0.108] | +0.013 [-0.181, +0.155] | -0.018 [-0.132, +0.077] | +0.091 [+0.053, +0.144] | +0.004 [-0.028, +0.043] | +0.022 [-0.109, +0.154] | -0.023 [-0.170, +0.086] |
| 2023 | +0.065 [+0.027, +0.109] | +0.082 [+0.024, +0.150] | +0.061 [+0.021, +0.109] | +0.058 [+0.021, +0.103] | -0.004 [-0.016, +0.006] | -0.069 [-0.189, +0.038] | +0.033 [-0.021, +0.082] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.314 [-0.056, +0.676] | -0.083 [-0.181, +0.015] | -0.040 [-0.099, +0.020] | -0.083 [-0.208, +0.083] | 60 |
| `recent_production_3col` | +0.201 [+0.055, +0.347] | -0.052 [-0.092, -0.015] | -0.026 [-0.060, +0.004] | +0.000 [-0.083, +0.083] | 60 |
| `recent_production_3col+opportunity` | +0.166 [-0.046, +0.386] | -0.043 [-0.112, +0.012] | -0.028 [-0.069, +0.011] | -0.083 [-0.125, +0.083] | 60 |
| `deployed_recipe+opportunity` | -0.002 [-0.229, +0.229] | +0.000 [-0.066, +0.055] | +0.000 [-0.030, +0.029] | -0.083 [-0.083, +0.083] | 60 |
| `exploratory:recent_production_3col+xfp` | +0.205 [+0.035, +0.383] | -0.053 [-0.100, -0.009] | -0.026 [-0.059, +0.004] | -0.042 [-0.125, +0.083] | 60 |
| `exploratory:deployed_recipe+xfp` | -0.078 [-0.166, +0.010] | +0.020 [-0.002, +0.047] | +0.024 [+0.005, +0.049] | +0.000 [-0.042, +0.042] | 60 |
| `deployed_recipe_reproduction` | +0.098 [-0.016, +0.203] | -0.025 [-0.053, +0.004] | -0.020 [-0.040, +0.001] | -0.042 [-0.083, +0.042] | 60 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | -0.022 [-0.170, +0.089] | -0.054 [-0.124, +0.012] | +0.056 [+0.006, +0.118] | -0.032 [-0.119, +0.066] | -0.013 [-0.167, +0.153] | -0.036 [-0.108, +0.038] | -0.059 [-0.202, +0.053] |
| 2023 | +0.017 [-0.016, +0.049] | -0.004 [-0.014, +0.007] | -0.007 [-0.018, +0.005] | -0.069 [-0.119, -0.026] | -0.135 [-0.258, -0.028] | -0.065 [-0.109, -0.027] | -0.032 [-0.090, +0.018] |

## RB (k = 24)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 91 / 91 | 100 / 100 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | [2018, 2019] | 193 / 116 | 99 / 99 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | [2018, 2019, 2020] | 293 / 139 | 95 / 95 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 392 / 158 | 90 / 90 | evaluated |

Alpha selected per fold for the reference arms: 2022: {'recent_production_3col': 100.0, 'deployed_recipe': 200.0} · 2023: {'recent_production_3col': 10.0, 'deployed_recipe': 10.0}


**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 185 | 3.777 | 2.980 | 0.548 | 0.763 | 0.729 |
| `recent_production_3col` | 185 | 3.665 | 2.939 | 0.574 | 0.780 | 0.771 |
| `deployed_recipe` | 185 | 3.549 | 2.820 | 0.601 | 0.790 | 0.771 |
| `recent_production_3col+opportunity` | 185 | 3.681 | 2.958 | 0.570 | 0.777 | 0.750 |
| `deployed_recipe+opportunity` | 185 | 3.577 | 2.846 | 0.595 | 0.788 | 0.750 |
| `exploratory:recent_production_3col+xfp` | 185 | 3.681 | 2.962 | 0.571 | 0.779 | 0.771 |
| `exploratory:deployed_recipe+xfp` | 185 | 3.582 | 2.860 | 0.593 | 0.789 | 0.771 |
| `deployed_recipe_reproduction` | 185 | 3.581 | 2.847 | 0.594 | 0.789 | 0.750 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.112 [+0.033, +0.184] | -0.026 [-0.046, -0.007] | -0.017 [-0.032, -0.001] | -0.042 [-0.062, +0.042] | 119 |
| `deployed_recipe` | -0.116 [-0.214, -0.020] | +0.027 [+0.005, +0.047] | +0.011 [-0.000, +0.022] | +0.000 [-0.042, +0.062] | 119 |
| `recent_production_3col+opportunity` | +0.017 [-0.015, +0.050] | -0.004 [-0.012, +0.003] | -0.003 [-0.008, +0.003] | -0.021 [-0.042, +0.021] | 119 |
| `deployed_recipe+opportunity` | -0.088 [-0.199, +0.017] | +0.020 [-0.004, +0.044] | +0.008 [-0.004, +0.021] | -0.021 [-0.042, +0.062] | 119 |
| `exploratory:recent_production_3col+xfp` | +0.016 [-0.002, +0.034] | -0.004 [-0.008, +0.001] | -0.001 [-0.006, +0.004] | +0.000 [-0.042, +0.042] | 119 |
| `exploratory:deployed_recipe+xfp` | -0.083 [-0.180, +0.010] | +0.019 [-0.003, +0.041] | +0.009 [-0.002, +0.022] | +0.000 [-0.042, +0.062] | 119 |
| `deployed_recipe_reproduction` | -0.084 [-0.186, +0.012] | +0.019 [-0.003, +0.041] | +0.010 [-0.002, +0.021] | -0.021 [-0.042, +0.062] | 119 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | +0.014 [-0.014, +0.036] | +0.008 [-0.027, +0.036] | +0.014 [-0.014, +0.036] | +0.011 [-0.016, +0.033] | -0.003 [-0.009, +0.003] | -0.035 [-0.065, -0.009] | -0.007 [-0.021, +0.005] |
| 2023 | +0.038 [+0.014, +0.063] | +0.032 [+0.006, +0.059] | +0.024 [-0.002, +0.053] | +0.027 [+0.002, +0.054] | -0.004 [-0.010, +0.001] | -0.018 [-0.045, +0.005] | -0.001 [-0.009, +0.006] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.228 [+0.128, +0.321] | -0.053 [-0.076, -0.031] | -0.027 [-0.046, -0.010] | -0.042 [-0.062, +0.042] | 119 |
| `recent_production_3col` | +0.116 [+0.020, +0.214] | -0.027 [-0.047, -0.005] | -0.011 [-0.022, +0.000] | +0.000 [-0.062, +0.042] | 119 |
| `recent_production_3col+opportunity` | +0.133 [+0.051, +0.218] | -0.030 [-0.048, -0.012] | -0.013 [-0.024, -0.003] | -0.021 [-0.062, +0.042] | 119 |
| `deployed_recipe+opportunity` | +0.028 [-0.008, +0.065] | -0.006 [-0.015, +0.002] | -0.002 [-0.010, +0.005] | -0.021 [-0.021, +0.021] | 119 |
| `exploratory:recent_production_3col+xfp` | +0.132 [+0.032, +0.231] | -0.030 [-0.051, -0.008] | -0.012 [-0.023, -0.000] | +0.000 [-0.062, +0.062] | 119 |
| `exploratory:deployed_recipe+xfp` | +0.033 [+0.005, +0.063] | -0.007 [-0.014, -0.001] | -0.001 [-0.006, +0.004] | +0.000 [-0.021, +0.021] | 119 |
| `deployed_recipe_reproduction` | +0.032 [-0.010, +0.078] | -0.007 [-0.017, +0.002] | -0.001 [-0.007, +0.004] | -0.021 [-0.021, +0.042] | 119 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | -0.006 [-0.019, +0.005] | +0.000 [+0.000, +0.000] | -0.003 [-0.007, +0.001] | -0.017 [-0.042, +0.014] | -0.049 [-0.082, -0.015] | -0.014 [-0.036, +0.014] | -0.020 [-0.042, +0.004] |
| 2023 | -0.007 [-0.018, +0.003] | -0.014 [-0.032, +0.005] | -0.011 [-0.023, -0.000] | -0.043 [-0.066, -0.019] | -0.057 [-0.085, -0.029] | -0.038 [-0.063, -0.014] | -0.039 [-0.062, -0.018] |

## WR (k = 24)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 145 / 145 | 160 / 160 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | [2018, 2019] | 294 / 184 | 153 / 153 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | [2018, 2019, 2020] | 454 / 220 | 148 / 148 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 607 / 251 | 155 / 155 | evaluated |

Alpha selected per fold for the reference arms: 2022: {'recent_production_3col': 0.1, 'deployed_recipe': 50.0} · 2023: {'recent_production_3col': 0.1, 'deployed_recipe': 50.0}


**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 303 | 3.148 | 2.585 | 0.624 | 0.776 | 0.625 |
| `recent_production_3col` | 303 | 2.997 | 2.441 | 0.660 | 0.795 | 0.646 |
| `deployed_recipe` | 303 | 2.910 | 2.324 | 0.679 | 0.805 | 0.646 |
| `recent_production_3col+opportunity` | 303 | 2.992 | 2.430 | 0.661 | 0.796 | 0.688 |
| `deployed_recipe+opportunity` | 303 | 2.909 | 2.322 | 0.679 | 0.806 | 0.625 |
| `exploratory:recent_production_3col+xfp` | 303 | 2.985 | 2.426 | 0.662 | 0.795 | 0.688 |
| `exploratory:deployed_recipe+xfp` | 303 | 2.900 | 2.314 | 0.681 | 0.805 | 0.646 |
| `deployed_recipe_reproduction` | 303 | 2.928 | 2.355 | 0.675 | 0.805 | 0.646 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.151 [+0.067, +0.233] | -0.035 [-0.054, -0.016] | -0.019 [-0.035, -0.002] | -0.021 [-0.104, +0.062] | 188 |
| `deployed_recipe` | -0.088 [-0.144, -0.032] | +0.020 [+0.007, +0.032] | +0.010 [+0.002, +0.020] | +0.000 [-0.042, +0.063] | 188 |
| `recent_production_3col+opportunity` | -0.005 [-0.014, +0.004] | +0.001 [-0.001, +0.003] | +0.001 [-0.001, +0.003] | +0.042 [-0.021, +0.042] | 188 |
| `deployed_recipe+opportunity` | -0.088 [-0.145, -0.031] | +0.020 [+0.007, +0.033] | +0.011 [+0.002, +0.021] | -0.021 [-0.042, +0.063] | 188 |
| `exploratory:recent_production_3col+xfp` | -0.012 [-0.023, -0.002] | +0.003 [+0.000, +0.005] | +0.000 [-0.002, +0.002] | +0.042 [+0.000, +0.042] | 188 |
| `exploratory:deployed_recipe+xfp` | -0.098 [-0.154, -0.042] | +0.022 [+0.010, +0.035] | +0.011 [+0.002, +0.021] | +0.000 [-0.042, +0.083] | 188 |
| `deployed_recipe_reproduction` | -0.069 [-0.120, -0.018] | +0.015 [+0.004, +0.027] | +0.010 [+0.002, +0.019] | +0.000 [-0.043, +0.063] | 188 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | +0.036 [+0.020, +0.053] | +0.038 [+0.022, +0.056] | +0.029 [+0.013, +0.045] | +0.038 [+0.022, +0.056] | +0.002 [-0.001, +0.004] | -0.016 [-0.042, +0.009] | +0.001 [-0.001, +0.002] |
| 2023 | +0.004 [-0.014, +0.021] | +0.002 [-0.017, +0.020] | +0.003 [-0.014, +0.018] | +0.006 [-0.012, +0.023] | +0.003 [-0.001, +0.008] | -0.054 [-0.081, -0.027] | +0.001 [-0.003, +0.005] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.239 [+0.149, +0.329] | -0.055 [-0.075, -0.035] | -0.029 [-0.047, -0.012] | -0.021 [-0.104, +0.021] | 188 |
| `recent_production_3col` | +0.088 [+0.032, +0.144] | -0.020 [-0.032, -0.007] | -0.010 [-0.020, -0.002] | +0.000 [-0.063, +0.042] | 188 |
| `recent_production_3col+opportunity` | +0.083 [+0.029, +0.137] | -0.019 [-0.031, -0.007] | -0.009 [-0.019, -0.000] | +0.042 [-0.062, +0.062] | 188 |
| `deployed_recipe+opportunity` | -0.000 [-0.011, +0.010] | +0.000 [-0.002, +0.002] | +0.001 [-0.001, +0.003] | -0.021 [-0.021, +0.021] | 188 |
| `exploratory:recent_production_3col+xfp` | +0.076 [+0.021, +0.130] | -0.017 [-0.030, -0.005] | -0.010 [-0.020, -0.001] | +0.042 [-0.062, +0.062] | 188 |
| `exploratory:deployed_recipe+xfp` | -0.010 [-0.022, +0.001] | +0.002 [-0.000, +0.005] | +0.000 [-0.002, +0.002] | +0.000 [+0.000, +0.042] | 188 |
| `deployed_recipe_reproduction` | +0.019 [+0.003, +0.036] | -0.004 [-0.008, -0.001] | +0.000 [-0.003, +0.003] | +0.000 [-0.021, +0.021] | 188 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | +0.002 [+0.000, +0.004] | -0.007 [-0.013, -0.002] | +0.002 [-0.001, +0.004] | -0.034 [-0.051, -0.017] | -0.052 [-0.078, -0.028] | -0.036 [-0.053, -0.020] | -0.035 [-0.053, -0.019] |
| 2023 | -0.002 [-0.006, +0.002] | -0.001 [-0.006, +0.004] | +0.003 [-0.001, +0.007] | -0.000 [-0.017, +0.018] | -0.058 [-0.088, -0.026] | -0.004 [-0.021, +0.014] | -0.002 [-0.019, +0.015] |

## TE (k = 12)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 79 / 79 | 79 / 79 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018)]) |
| 2021 | [2018, 2019] | 167 / 106 | 83 / 83 | skipped — leak_free alpha selection: alpha cannot be selected without leakage: no expanding-time fold survives with the player held out and labels closed (window 2; seasons present: [np.int64(2018), np.int64(2019)]) |
| 2022 | [2018, 2019, 2020] | 246 / 116 | 82 / 82 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 329 / 140 | 79 / 79 | evaluated |

Alpha selected per fold for the reference arms: 2022: {'recent_production_3col': 0.1, 'deployed_recipe': 1.0} · 2023: {'recent_production_3col': 0.1, 'deployed_recipe': 1.0}


**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 161 | 2.369 | 1.821 | 0.592 | 0.754 | 0.583 |
| `recent_production_3col` | 161 | 2.332 | 1.777 | 0.605 | 0.774 | 0.500 |
| `deployed_recipe` | 161 | 2.271 | 1.793 | 0.625 | 0.775 | 0.583 |
| `recent_production_3col+opportunity` | 161 | 2.436 | 1.805 | 0.569 | 0.765 | 0.583 |
| `deployed_recipe+opportunity` | 161 | 2.378 | 1.814 | 0.589 | 0.770 | 0.583 |
| `exploratory:recent_production_3col+xfp` | 161 | 2.623 | 1.826 | 0.500 | 0.743 | 0.500 |
| `exploratory:deployed_recipe+xfp` | 161 | 2.291 | 1.756 | 0.619 | 0.769 | 0.542 |
| `deployed_recipe_reproduction` | 161 | 2.257 | 1.742 | 0.630 | 0.785 | 0.583 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.037 [-0.048, +0.123] | -0.013 [-0.041, +0.018] | -0.020 [-0.051, +0.009] | +0.083 [-0.042, +0.125] | 104 |
| `deployed_recipe` | -0.061 [-0.134, +0.021] | +0.020 [-0.007, +0.045] | +0.002 [-0.018, +0.020] | +0.083 [-0.083, +0.125] | 104 |
| `recent_production_3col+opportunity` | +0.104 [-0.034, +0.265] | -0.036 [-0.096, +0.012] | -0.009 [-0.029, +0.008] | +0.083 [-0.125, +0.125] | 104 |
| `deployed_recipe+opportunity` | +0.046 [-0.108, +0.243] | -0.016 [-0.089, +0.038] | -0.004 [-0.026, +0.016] | +0.083 [-0.125, +0.125] | 104 |
| `exploratory:recent_production_3col+xfp` | +0.291 [-0.043, +0.818] | -0.105 [-0.323, +0.016] | -0.031 [-0.103, +0.012] | +0.000 [-0.083, +0.083] | 104 |
| `exploratory:deployed_recipe+xfp` | -0.041 [-0.109, +0.030] | +0.014 [-0.010, +0.039] | -0.005 [-0.030, +0.018] | +0.042 [-0.125, +0.125] | 104 |
| `deployed_recipe_reproduction` | -0.075 [-0.125, -0.023] | +0.025 [+0.008, +0.043] | +0.011 [-0.005, +0.027] | +0.083 [-0.083, +0.125] | 104 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | +0.010 [-0.022, +0.048] | -0.002 [-0.044, +0.044] | +0.016 [+0.000, +0.034] | -0.001 [-0.040, +0.046] | -0.204 [-0.630, +0.020] | -0.013 [-0.047, +0.023] | -0.027 [-0.079, +0.021] |
| 2023 | +0.031 [-0.012, +0.070] | -0.031 [-0.152, +0.052] | +0.035 [+0.005, +0.066] | +0.030 [-0.003, +0.066] | +0.003 [-0.012, +0.022] | -0.013 [-0.047, +0.026] | -0.045 [-0.138, +0.019] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.098 [-0.006, +0.197] | -0.033 [-0.066, +0.002] | -0.022 [-0.054, +0.010] | +0.000 [-0.083, +0.125] | 104 |
| `recent_production_3col` | +0.061 [-0.021, +0.134] | -0.020 [-0.045, +0.007] | -0.002 [-0.020, +0.018] | -0.083 [-0.125, +0.083] | 104 |
| `recent_production_3col+opportunity` | +0.165 [-0.003, +0.347] | -0.056 [-0.121, +0.001] | -0.010 [-0.035, +0.012] | +0.000 [-0.125, +0.083] | 104 |
| `deployed_recipe+opportunity` | +0.106 [-0.034, +0.297] | -0.036 [-0.107, +0.011] | -0.005 [-0.018, +0.007] | +0.000 [-0.083, +0.083] | 104 |
| `exploratory:recent_production_3col+xfp` | +0.352 [-0.021, +0.874] | -0.125 [-0.345, +0.007] | -0.033 [-0.104, +0.018] | -0.083 [-0.125, +0.083] | 104 |
| `exploratory:deployed_recipe+xfp` | +0.019 [-0.040, +0.079] | -0.006 [-0.025, +0.014] | -0.006 [-0.024, +0.009] | -0.042 [-0.083, +0.083] | 104 |
| `deployed_recipe_reproduction` | -0.015 [-0.082, +0.048] | +0.005 [-0.016, +0.027] | +0.010 [-0.005, +0.025] | +0.000 [-0.083, +0.125] | 104 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `deployed_recipe_reproduction` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | skipped | skipped | skipped | skipped | skipped | skipped | skipped |
| 2022 | -0.012 [-0.053, +0.026] | +0.006 [-0.031, +0.037] | -0.011 [-0.039, +0.014] | -0.214 [-0.643, +0.023] | -0.023 [-0.061, +0.015] | -0.010 [-0.048, +0.022] | -0.038 [-0.106, +0.026] |
| 2023 | -0.062 [-0.176, +0.006] | +0.004 [-0.021, +0.031] | -0.001 [-0.025, +0.027] | -0.028 [-0.068, +0.018] | -0.044 [-0.091, +0.009] | -0.031 [-0.070, +0.012] | -0.077 [-0.172, +0.002] |

## Reproduction of DG-162 §1 under its stricter rule

Rule `window_closed_before_test`; DG-162's published values from `~/dg-build/tickets/DG-162-what-the-model-actually-reads.md §1`.

| pos | n (this run / DG-162) | ppg_only r² (this / DG-162) | deployed r² (this / DG-162) | Δr² deployed−3col (this / DG-162) |
|---|---|---|---|---|
| QB | 95 / 95 | 0.320 / 0.320 | 0.383 / 0.383 | 0.030 / 0.030 |
| RB | 284 / 284 | 0.572 / 0.572 | 0.600 / 0.600 | -0.000 / -0.000 |
| WR | 456 / 456 | 0.623 / 0.623 | 0.661 / 0.661 | 0.010 / 0.010 |
| TE | 244 / 244 | 0.588 / 0.588 | 0.605 / 0.605 | 0.008 / 0.008 |

## Opportunity denominator

Rates divide by `games_t (all games with a stat line, DG-024)`. Rows 3384, joined 3337, unavailable (NaN, never zero) 47; 1061 joined rows had fewer source weeks than product games, and 3265 zero-opportunity games were counted in the denominator rather than dropped.


## Opportunity family coverage (training rows joined to a season aggregate)

| pos | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2025 |
|---|---|---|---|---|---|---|---|
| QB | 52/52 | 47/47 | 56/56 | 57/57 | 58/58 | 60/60 | 62/62 |
| RB | 120/123 | 118/119 | 133/136 | 128/131 | 130/132 | 116/119 | 126/127 |
| TE | 105/105 | 102/102 | 102/102 | 108/109 | 104/105 | 99/99 | 108/109 |
| WR | 188/192 | 185/189 | 193/197 | 199/204 | 192/194 | 188/191 | 201/207 |

## Provenance

- `training_csv`: `/Users/davidleess/dg-wt/DG-177/app/data/training/engine_b_features_v2.csv` · 951839 bytes · modified 2026-09-06T13:11:06.525573+00:00 · sha256 `64a106f2f15d1752…`
- `engine_b_manifest`: `/Users/davidleess/dg-wt/DG-177/app/data/models/engine_b/v2_manifest.json` · 275 bytes · modified 2026-08-31T20:44:58.143979+00:00 · sha256 `916677c19a43b2bf…`
- `served_qb_pickle`: `/Users/davidleess/dg-wt/DG-177/app/data/models/engine_b/runs/20260831T204458Z/qb_v2.pkl` · 1924 bytes · modified 2026-09-06T13:11:06.516774+00:00 · sha256 `fbb3617be59bc112…`
- `served_rb_pickle`: `/Users/davidleess/dg-wt/DG-177/app/data/models/engine_b/runs/20260831T204458Z/rb_v2.pkl` · 1780 bytes · modified 2026-09-06T13:11:06.516817+00:00 · sha256 `03f67f7c8417e16e…`
- `served_wr_pickle`: `/Users/davidleess/dg-wt/DG-177/app/data/models/engine_b/runs/20260831T204458Z/wr_v2.pkl` · 1816 bytes · modified 2026-09-06T13:11:06.517174+00:00 · sha256 `e1cbb125d5dd66bb…`
- `served_te_pickle`: `/Users/davidleess/dg-wt/DG-177/app/data/models/engine_b/runs/20260831T204458Z/te_v2.pkl` · 1816 bytes · modified 2026-09-06T13:11:06.516865+00:00 · sha256 `84f05d61e83ba019…`
- git_head: `"e680e48b57a0a4eaff882bad270ac01b3f509190"`
- git_branch: `"ticket/DG-177"`
- worktree: `{"ticket": "DG-177", "branch": "ticket/DG-177", "base": "origin/main", "shared_readonly": [".venv", "app/cache", "app/data/cfbd_cache", "app/data/identity", "app/data/nflverse_usage", "app/data/nflverse_usage.db", "app/data/model_forward_capture.db", "app/data/market_divergence_history.db", "app/data/playerprofiler.db", "app/data/fc_forward_capture.db", "app/data/fc_snapshots.db", "app/data/league_transactions.db", "app/data/league_transactions", "app/data/pff_exports", "app/data/footballguys", "app/data/sources", "app/data/backtest", "frontend/node_modules", "app/data/models"], "writable_copies": [], "ticket_file": "/Users/davidleess/dg-build/tickets/DG-177-veteran-forecast-candidate-with-historical-cutoffs.md"}`
- warehouse: `{"path": "/Users/davidleess/dg-wt/DG-177/app/data/nflverse_usage.db", "resolved": "/Users/davidleess/dynasty-genius-product/app/data/nflverse_usage.db", "bytes": 16347369472, "modified_utc": "2026-09-05T10:15:36.867655+00:00", "sha256": "not computed \u2014 multi-GB store; identified by path, size, mtime and table facts", "modified_at_open_utc": "2026-09-05T10:15:36.867655+00:00", "changed_during_run": false, "table": "ff_opportunity", "rows": 47282, "seasons": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"], "season_ingested_range": ["2018", "2025"], "source_era": ["ffopportunity_v1"]}`
- served_models: `{"QB": {"version": "engine_b_v2_qb", "path": "app/data/models/engine_b/runs/20260831T204458Z/qb_v2.pkl"}, "RB": {"version": "engine_b_v2_rb", "path": "app/data/models/engine_b/runs/20260831T204458Z/rb_v2.pkl"}, "WR": {"version": "engine_b_v2_wr", "path": "app/data/models/engine_b/runs/20260831T204458Z/wr_v2.pkl"}, "TE": {"version": "engine_b_v2_te", "path": "app/data/models/engine_b/runs/20260831T204458Z/te_v2.pkl"}}`
- notes: `["xfp_* columns are nflverse ffopportunity expected points, a third-party fitted model. Its documentation (https://ffopportunity.ffverse.com/, read 2026-09-06) says it \"uses xgboost and tidymodels trained on public nflverse data from 2006-2020\"; the model version behind each warehouse row is not recorded. That window overlaps feature seasons 2018-2020 at play level, so arms using them are labelled exploratory and are not point-in-time evidence.", "opp_* columns are raw counts from the feature season only, per PRODUCT game (games_t, all games with a stat line, DG-024); source weeks missing from a joined season are observed zero-opportunity games; an absent season is NaN, never zero."]`
- versions: `{"python": "3.14.7", "scikit-learn": "1.8.0", "pandas": "3.0.5", "numpy": "2.5.2", "scipy": "1.17.1"}`
