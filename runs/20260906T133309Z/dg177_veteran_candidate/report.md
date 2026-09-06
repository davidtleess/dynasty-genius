# DG-177 — veteran forecast candidate, evaluated at the cutoff

Rule: `labels_known_at_cutoff` · reference arms: ['recent_production_3col', 'deployed_recipe'] · test seasons: [2020, 2021, 2022, 2023] · git: `ecc260ef2b7740f66bf199059b0606d215ed6e43`

Deltas are metric(arm) − metric(reference) on identical rows, 90% interval from a bootstrap that resamples players. RMSE lower is better; r², Spearman and top-k overlap higher is better.


## QB (k = 12)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 40 / 40 | 43 / 43 | skipped — train rows 40 < minimum 60 |
| 2021 | [2018, 2019] | 80 / 49 | 46 / 46 | evaluated |
| 2022 | [2018, 2019, 2020] | 123 / 59 | 46 / 46 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 169 / 71 | 49 / 49 | evaluated |

**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 141 | 4.718 | 3.566 | 0.344 | 0.647 | 0.500 |
| `recent_production_3col` | 141 | 4.583 | 3.476 | 0.381 | 0.668 | 0.417 |
| `deployed_recipe` | 141 | 4.468 | 3.450 | 0.412 | 0.678 | 0.500 |
| `recent_production_3col+opportunity` | 141 | 4.491 | 3.408 | 0.405 | 0.668 | 0.667 |
| `deployed_recipe+opportunity` | 141 | 4.386 | 3.405 | 0.433 | 0.703 | 0.667 |
| `exploratory:recent_production_3col+xfp` | 141 | 4.651 | 3.565 | 0.362 | 0.641 | 0.417 |
| `exploratory:deployed_recipe+xfp` | 141 | 4.724 | 3.663 | 0.342 | 0.642 | 0.417 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.134 [-0.139, +0.410] | -0.037 [-0.116, +0.039] | -0.021 [-0.079, +0.031] | +0.083 [-0.083, +0.250] | 67 |
| `deployed_recipe` | -0.116 [-0.272, +0.052] | +0.031 [-0.014, +0.077] | +0.010 [-0.018, +0.039] | +0.083 [-0.167, +0.250] | 67 |
| `recent_production_3col+opportunity` | -0.092 [-0.222, +0.044] | +0.025 [-0.012, +0.059] | +0.000 [-0.025, +0.023] | +0.250 [-0.083, +0.333] | 67 |
| `deployed_recipe+opportunity` | -0.197 [-0.384, +0.002] | +0.052 [-0.001, +0.106] | +0.036 [+0.003, +0.071] | +0.250 [-0.083, +0.333] | 67 |
| `exploratory:recent_production_3col+xfp` | +0.068 [-0.041, +0.193] | -0.018 [-0.052, +0.012] | -0.027 [-0.053, -0.004] | +0.000 [-0.167, +0.167] | 67 |
| `exploratory:deployed_recipe+xfp` | +0.140 [-0.092, +0.392] | -0.038 [-0.110, +0.026] | -0.025 [-0.074, +0.022] | +0.000 [-0.250, +0.167] | 67 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | +0.056 [-0.019, +0.148] | -0.019 [-0.163, +0.130] | -0.170 [-0.331, -0.007] | -0.051 [-0.144, +0.061] | -0.039 [-0.169, +0.116] | +0.052 [-0.041, +0.181] |
| 2022 | -0.031 [-0.153, +0.069] | +0.091 [+0.038, +0.143] | -0.053 [-0.215, +0.076] | -0.009 [-0.040, +0.021] | +0.009 [-0.112, +0.130] | +0.003 [-0.068, +0.058] |
| 2023 | +0.061 [+0.021, +0.109] | +0.073 [+0.019, +0.136] | +0.058 [+0.021, +0.103] | -0.004 [-0.016, +0.006] | -0.070 [-0.187, +0.035] | +0.023 [-0.009, +0.055] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.250 [-0.067, +0.575] | -0.068 [-0.163, +0.017] | -0.031 [-0.088, +0.019] | +0.000 [-0.167, +0.167] | 67 |
| `recent_production_3col` | +0.116 [-0.052, +0.272] | -0.031 [-0.077, +0.014] | -0.010 [-0.039, +0.018] | -0.083 [-0.250, +0.167] | 67 |
| `recent_production_3col+opportunity` | +0.024 [-0.153, +0.197] | -0.006 [-0.057, +0.039] | -0.010 [-0.042, +0.022] | +0.167 [-0.083, +0.254] | 67 |
| `deployed_recipe+opportunity` | -0.081 [-0.245, +0.087] | +0.021 [-0.024, +0.063] | +0.026 [-0.002, +0.052] | +0.167 [-0.083, +0.250] | 67 |
| `exploratory:recent_production_3col+xfp` | +0.184 [-0.006, +0.379] | -0.049 [-0.107, +0.002] | -0.037 [-0.074, -0.002] | -0.083 [-0.250, +0.083] | 67 |
| `exploratory:deployed_recipe+xfp` | +0.256 [+0.069, +0.472] | -0.069 [-0.134, -0.018] | -0.035 [-0.078, +0.000] | -0.083 [-0.333, +0.083] | 67 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | skipped | skipped | skipped | skipped | skipped | skipped |
| 2021 | -0.075 [-0.202, +0.039] | -0.226 [-0.410, -0.079] | -0.107 [-0.239, +0.001] | -0.095 [-0.271, +0.066] | -0.056 [-0.148, +0.019] | -0.004 [-0.128, +0.113] |
| 2022 | +0.121 [+0.043, +0.226] | -0.023 [-0.107, +0.054] | +0.022 [-0.077, +0.138] | +0.039 [-0.128, +0.234] | +0.031 [-0.069, +0.153] | +0.033 [-0.067, +0.134] |
| 2023 | +0.012 [-0.011, +0.035] | -0.002 [-0.010, +0.005] | -0.065 [-0.117, -0.019] | -0.131 [-0.250, -0.030] | -0.061 [-0.109, -0.021] | -0.037 [-0.084, +0.003] |

## RB (k = 24)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 91 / 91 | 100 / 100 | evaluated |
| 2021 | [2018, 2019] | 193 / 116 | 99 / 99 | evaluated |
| 2022 | [2018, 2019, 2020] | 293 / 139 | 95 / 95 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 392 / 158 | 90 / 90 | evaluated |

**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 384 | 3.474 | 2.744 | 0.575 | 0.763 | 0.417 |
| `recent_production_3col` | 384 | 3.430 | 2.744 | 0.586 | 0.766 | 0.375 |
| `deployed_recipe` | 384 | 3.400 | 2.688 | 0.593 | 0.773 | 0.417 |
| `recent_production_3col+opportunity` | 384 | 3.436 | 2.746 | 0.584 | 0.769 | 0.417 |
| `deployed_recipe+opportunity` | 384 | 3.402 | 2.692 | 0.592 | 0.773 | 0.375 |
| `exploratory:recent_production_3col+xfp` | 384 | 3.431 | 2.743 | 0.585 | 0.764 | 0.458 |
| `exploratory:deployed_recipe+xfp` | 384 | 3.412 | 2.697 | 0.590 | 0.769 | 0.417 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.044 [-0.017, +0.102] | -0.011 [-0.026, +0.004] | -0.003 [-0.016, +0.010] | +0.042 [-0.125, +0.125] | 169 |
| `deployed_recipe` | -0.030 [-0.094, +0.032] | +0.007 [-0.009, +0.022] | +0.007 [-0.001, +0.015] | +0.042 [-0.083, +0.125] | 169 |
| `recent_production_3col+opportunity` | +0.006 [-0.022, +0.035] | -0.002 [-0.009, +0.005] | +0.003 [-0.002, +0.008] | +0.042 [-0.083, +0.083] | 169 |
| `deployed_recipe+opportunity` | -0.028 [-0.095, +0.037] | +0.007 [-0.010, +0.022] | +0.008 [-0.000, +0.016] | +0.000 [-0.083, +0.125] | 169 |
| `exploratory:recent_production_3col+xfp` | +0.002 [-0.020, +0.023] | -0.000 [-0.005, +0.005] | -0.001 [-0.006, +0.003] | +0.083 [-0.083, +0.125] | 169 |
| `exploratory:deployed_recipe+xfp` | -0.018 [-0.085, +0.045] | +0.004 [-0.012, +0.019] | +0.004 [-0.005, +0.013] | +0.042 [-0.125, +0.167] | 169 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | -0.012 [-0.045, +0.018] | -0.005 [-0.035, +0.024] | -0.025 [-0.064, +0.013] | -0.001 [-0.018, +0.020] | +0.021 [-0.018, +0.071] | +0.006 [-0.015, +0.026] |
| 2021 | -0.009 [-0.031, +0.007] | -0.016 [-0.033, -0.002] | -0.008 [-0.031, +0.011] | -0.003 [-0.013, +0.006] | -0.012 [-0.040, +0.013] | -0.015 [-0.025, -0.004] |
| 2022 | +0.015 [-0.013, +0.038] | +0.011 [-0.020, +0.036] | +0.014 [-0.013, +0.037] | -0.001 [-0.007, +0.006] | -0.034 [-0.063, -0.007] | -0.003 [-0.014, +0.006] |
| 2023 | +0.030 [+0.004, +0.057] | +0.031 [+0.003, +0.059] | +0.030 [+0.004, +0.057] | +0.002 [-0.003, +0.007] | -0.015 [-0.040, +0.006] | +0.004 [-0.005, +0.012] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.075 [+0.000, +0.151] | -0.018 [-0.036, -0.000] | -0.010 [-0.024, +0.004] | +0.000 [-0.125, +0.083] | 169 |
| `recent_production_3col` | +0.030 [-0.032, +0.094] | -0.007 [-0.022, +0.009] | -0.007 [-0.015, +0.001] | -0.042 [-0.125, +0.083] | 169 |
| `recent_production_3col+opportunity` | +0.037 [-0.018, +0.094] | -0.009 [-0.022, +0.005] | -0.004 [-0.011, +0.004] | +0.000 [-0.125, +0.083] | 169 |
| `deployed_recipe+opportunity` | +0.002 [-0.019, +0.025] | -0.001 [-0.006, +0.005] | +0.001 [-0.003, +0.005] | -0.042 [-0.083, +0.083] | 169 |
| `exploratory:recent_production_3col+xfp` | +0.032 [-0.036, +0.101] | -0.008 [-0.023, +0.009] | -0.008 [-0.017, +0.000] | +0.042 [-0.125, +0.125] | 169 |
| `exploratory:deployed_recipe+xfp` | +0.012 [-0.008, +0.032] | -0.003 [-0.008, +0.002] | -0.003 [-0.008, +0.001] | +0.000 [-0.083, +0.083] | 169 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | +0.007 [-0.011, +0.024] | -0.013 [-0.030, +0.005] | +0.012 [-0.019, +0.045] | +0.033 [-0.010, +0.085] | +0.012 [-0.018, +0.045] | +0.019 [-0.014, +0.050] |
| 2021 | -0.007 [-0.017, +0.004] | +0.001 [-0.007, +0.010] | +0.006 [-0.010, +0.026] | -0.003 [-0.033, +0.030] | +0.009 [-0.007, +0.031] | -0.006 [-0.026, +0.020] |
| 2022 | -0.004 [-0.014, +0.004] | -0.001 [-0.009, +0.007] | -0.016 [-0.042, +0.016] | -0.049 [-0.082, -0.015] | -0.015 [-0.038, +0.013] | -0.018 [-0.039, +0.006] |
| 2023 | +0.001 [-0.004, +0.006] | +0.000 [-0.004, +0.003] | -0.028 [-0.056, -0.000] | -0.045 [-0.075, -0.018] | -0.030 [-0.057, -0.004] | -0.026 [-0.050, -0.004] |

## WR (k = 24)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 145 / 145 | 160 / 160 | evaluated |
| 2021 | [2018, 2019] | 294 / 184 | 153 / 153 | evaluated |
| 2022 | [2018, 2019, 2020] | 454 / 220 | 148 / 148 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 607 / 251 | 155 / 155 | evaluated |

**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 616 | 3.167 | 2.570 | 0.617 | 0.768 | 0.583 |
| `recent_production_3col` | 616 | 3.068 | 2.453 | 0.641 | 0.781 | 0.625 |
| `deployed_recipe` | 616 | 3.017 | 2.393 | 0.653 | 0.788 | 0.625 |
| `recent_production_3col+opportunity` | 616 | 3.067 | 2.447 | 0.641 | 0.781 | 0.625 |
| `deployed_recipe+opportunity` | 616 | 3.029 | 2.398 | 0.650 | 0.787 | 0.583 |
| `exploratory:recent_production_3col+xfp` | 616 | 3.064 | 2.451 | 0.642 | 0.781 | 0.625 |
| `exploratory:deployed_recipe+xfp` | 616 | 3.009 | 2.390 | 0.655 | 0.788 | 0.583 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.100 [+0.023, +0.171] | -0.024 [-0.040, -0.006] | -0.013 [-0.025, -0.002] | -0.042 [-0.208, +0.000] | 265 |
| `deployed_recipe` | -0.050 [-0.087, -0.015] | +0.012 [+0.003, +0.020] | +0.007 [+0.002, +0.013] | +0.000 [-0.083, +0.083] | 265 |
| `recent_production_3col+opportunity` | -0.001 [-0.018, +0.016] | +0.000 [-0.004, +0.004] | +0.000 [-0.002, +0.003] | +0.000 [-0.083, +0.042] | 265 |
| `deployed_recipe+opportunity` | -0.038 [-0.082, +0.003] | +0.009 [-0.001, +0.019] | +0.006 [+0.000, +0.012] | -0.042 [-0.125, +0.083] | 265 |
| `exploratory:recent_production_3col+xfp` | -0.004 [-0.015, +0.008] | +0.001 [-0.002, +0.004] | +0.000 [-0.002, +0.002] | +0.000 [-0.083, +0.042] | 265 |
| `exploratory:deployed_recipe+xfp` | -0.059 [-0.097, -0.023] | +0.014 [+0.005, +0.022] | +0.007 [+0.002, +0.013] | -0.042 [-0.125, +0.083] | 265 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | +0.001 [-0.005, +0.007] | -0.001 [-0.015, +0.015] | +0.005 [-0.003, +0.014] | -0.001 [-0.010, +0.008] | -0.009 [-0.043, +0.026] | -0.003 [-0.014, +0.009] |
| 2021 | +0.014 [-0.009, +0.036] | +0.008 [-0.018, +0.031] | +0.014 [-0.009, +0.037] | -0.002 [-0.004, -0.001] | -0.016 [-0.050, +0.022] | +0.002 [-0.003, +0.008] |
| 2022 | +0.029 [+0.014, +0.046] | +0.034 [+0.019, +0.052] | +0.033 [+0.018, +0.051] | +0.005 [+0.002, +0.008] | -0.017 [-0.042, +0.008] | +0.003 [-0.000, +0.007] |
| 2023 | +0.003 [-0.013, +0.019] | -0.004 [-0.025, +0.015] | +0.002 [-0.016, +0.019] | +0.002 [-0.004, +0.007] | -0.053 [-0.080, -0.027] | -0.001 [-0.008, +0.005] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.150 [+0.070, +0.227] | -0.035 [-0.052, -0.018] | -0.021 [-0.033, -0.009] | -0.042 [-0.167, +0.000] | 265 |
| `recent_production_3col` | +0.050 [+0.015, +0.087] | -0.012 [-0.020, -0.003] | -0.007 [-0.013, -0.002] | +0.000 [-0.083, +0.083] | 265 |
| `recent_production_3col+opportunity` | +0.049 [+0.010, +0.088] | -0.011 [-0.020, -0.002] | -0.007 [-0.013, -0.001] | +0.000 [-0.125, +0.083] | 265 |
| `deployed_recipe+opportunity` | +0.012 [-0.007, +0.033] | -0.003 [-0.008, +0.002] | -0.001 [-0.005, +0.002] | -0.042 [-0.083, +0.042] | 265 |
| `exploratory:recent_production_3col+xfp` | +0.047 [+0.010, +0.085] | -0.011 [-0.019, -0.003] | -0.007 [-0.013, -0.001] | +0.000 [-0.083, +0.083] | 265 |
| `exploratory:deployed_recipe+xfp` | -0.008 [-0.018, +0.003] | +0.002 [-0.001, +0.004] | +0.000 [-0.002, +0.002] | -0.042 [-0.083, +0.042] | 265 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | -0.002 [-0.013, +0.010] | +0.004 [-0.002, +0.010] | -0.001 [-0.013, +0.008] | -0.010 [-0.044, +0.024] | -0.001 [-0.007, +0.005] | -0.004 [-0.013, +0.005] |
| 2021 | -0.006 [-0.018, +0.004] | +0.000 [-0.001, +0.002] | -0.016 [-0.040, +0.007] | -0.030 [-0.066, +0.011] | -0.014 [-0.036, +0.009] | -0.012 [-0.037, +0.014] |
| 2022 | +0.005 [+0.001, +0.009] | +0.004 [-0.000, +0.008] | -0.024 [-0.040, -0.009] | -0.046 [-0.070, -0.023] | -0.029 [-0.046, -0.014] | -0.026 [-0.042, -0.010] |
| 2023 | -0.008 [-0.017, +0.001] | -0.001 [-0.007, +0.005] | -0.002 [-0.018, +0.015] | -0.057 [-0.086, -0.025] | -0.003 [-0.019, +0.013] | -0.004 [-0.020, +0.012] |

## TE (k = 12)

| test season | train seasons | train rows / players | test rows / players | status |
|---|---|---|---|---|
| 2020 | [2018] | 79 / 79 | 79 / 79 | evaluated |
| 2021 | [2018, 2019] | 167 / 106 | 83 / 83 | evaluated |
| 2022 | [2018, 2019, 2020] | 246 / 116 | 82 / 82 | evaluated |
| 2023 | [2018, 2019, 2020, 2021] | 329 / 140 | 79 / 79 | evaluated |

**Pooled over evaluated folds**

| arm | n | RMSE | MAE | r² | Spearman | top-k overlap |
|---|---:|---:|---:|---:|---:|---:|
| `ppg_only` | 323 | 2.364 | 1.877 | 0.597 | 0.764 | 0.333 |
| `recent_production_3col` | 323 | 2.336 | 1.851 | 0.606 | 0.776 | 0.333 |
| `deployed_recipe` | 323 | 2.294 | 1.831 | 0.620 | 0.783 | 0.333 |
| `recent_production_3col+opportunity` | 323 | 2.401 | 1.848 | 0.584 | 0.776 | 0.250 |
| `deployed_recipe+opportunity` | 323 | 2.337 | 1.837 | 0.606 | 0.780 | 0.250 |
| `exploratory:recent_production_3col+xfp` | 323 | 2.322 | 1.832 | 0.611 | 0.780 | 0.333 |
| `exploratory:deployed_recipe+xfp` | 323 | 2.297 | 1.819 | 0.619 | 0.787 | 0.333 |

**Difference vs `recent_production_3col`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.029 [-0.034, +0.086] | -0.010 [-0.030, +0.012] | -0.012 [-0.031, +0.006] | +0.000 [-0.083, +0.083] | 143 |
| `deployed_recipe` | -0.042 [-0.070, -0.016] | +0.014 [+0.006, +0.024] | +0.007 [-0.000, +0.016] | +0.000 [-0.083, +0.250] | 143 |
| `recent_production_3col+opportunity` | +0.065 [-0.051, +0.215] | -0.022 [-0.076, +0.018] | -0.000 [-0.012, +0.011] | -0.083 [-0.250, +0.083] | 143 |
| `deployed_recipe+opportunity` | +0.001 [-0.075, +0.087] | -0.000 [-0.030, +0.025] | +0.005 [-0.007, +0.017] | -0.083 [-0.250, +0.167] | 143 |
| `exploratory:recent_production_3col+xfp` | -0.014 [-0.036, +0.009] | +0.005 [-0.003, +0.013] | +0.004 [-0.001, +0.011] | +0.000 [-0.083, +0.000] | 143 |
| `exploratory:deployed_recipe+xfp` | -0.039 [-0.067, -0.013] | +0.013 [+0.005, +0.023] | +0.011 [+0.003, +0.020] | +0.000 [-0.167, +0.083] | 143 |

**Per fold, Δr² vs `recent_production_3col` [90%]**

| test season | `deployed_recipe` | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | +0.001 [-0.000, +0.002] | +0.004 [-0.033, +0.030] | +0.001 [-0.010, +0.009] | +0.000 [-0.010, +0.008] | -0.005 [-0.034, +0.021] | +0.002 [-0.035, +0.029] |
| 2021 | +0.003 [-0.008, +0.011] | +0.015 [-0.013, +0.048] | +0.006 [-0.007, +0.019] | +0.005 [-0.004, +0.017] | +0.001 [-0.039, +0.047] | -0.058 [-0.215, +0.047] |
| 2022 | +0.018 [+0.002, +0.036] | +0.001 [-0.033, +0.036] | +0.020 [+0.001, +0.042] | +0.007 [-0.010, +0.028] | -0.021 [-0.055, +0.015] | -0.000 [-0.045, +0.044] |
| 2023 | +0.036 [+0.006, +0.067] | -0.021 [-0.133, +0.055] | +0.027 [+0.000, +0.058] | +0.007 [-0.010, +0.028] | -0.013 [-0.048, +0.026] | -0.037 [-0.122, +0.020] |

**Difference vs `deployed_recipe`, pooled**

| arm | ΔRMSE [90%] | Δr² [90%] | ΔSpearman [90%] | Δtop-k [90%] | clusters |
|---|---|---|---|---|---:|
| `ppg_only` | +0.070 [+0.005, +0.131] | -0.024 [-0.045, -0.002] | -0.020 [-0.040, -0.000] | +0.000 [-0.167, +0.083] | 143 |
| `recent_production_3col` | +0.042 [+0.016, +0.070] | -0.014 [-0.024, -0.006] | -0.007 [-0.016, +0.000] | +0.000 [-0.250, +0.083] | 143 |
| `recent_production_3col+opportunity` | +0.107 [-0.016, +0.262] | -0.036 [-0.092, +0.006] | -0.008 [-0.021, +0.004] | -0.083 [-0.333, +0.083] | 143 |
| `deployed_recipe+opportunity` | +0.043 [-0.030, +0.129] | -0.014 [-0.045, +0.010] | -0.003 [-0.012, +0.007] | -0.083 [-0.250, +0.083] | 143 |
| `exploratory:recent_production_3col+xfp` | +0.028 [-0.008, +0.069] | -0.009 [-0.022, +0.003] | -0.003 [-0.012, +0.005] | +0.000 [-0.333, +0.083] | 143 |
| `exploratory:deployed_recipe+xfp` | +0.003 [-0.024, +0.029] | -0.001 [-0.010, +0.009] | +0.004 [-0.004, +0.011] | +0.000 [-0.250, +0.000] | 143 |

**Per fold, Δr² vs `deployed_recipe` [90%]**

| test season | `deployed_recipe+opportunity` | `exploratory:deployed_recipe+xfp` | `exploratory:recent_production_3col+xfp` | `ppg_only` | `recent_production_3col` | `recent_production_3col+opportunity` |
|---|---|---|---|---|---|---|
| 2020 | +0.003 [-0.033, +0.029] | +0.000 [-0.010, +0.008] | -0.000 [-0.011, +0.007] | -0.005 [-0.035, +0.020] | -0.001 [-0.002, +0.000] | +0.001 [-0.035, +0.028] |
| 2021 | +0.012 [-0.013, +0.045] | +0.003 [-0.005, +0.013] | +0.002 [-0.009, +0.019] | -0.002 [-0.040, +0.046] | -0.003 [-0.011, +0.008] | -0.060 [-0.215, +0.045] |
| 2022 | -0.017 [-0.058, +0.021] | +0.002 [-0.015, +0.020] | -0.010 [-0.036, +0.016] | -0.039 [-0.077, +0.000] | -0.018 [-0.036, -0.002] | -0.018 [-0.072, +0.029] |
| 2023 | -0.058 [-0.165, +0.007] | -0.009 [-0.035, +0.021] | -0.030 [-0.059, +0.004] | -0.050 [-0.082, -0.013] | -0.036 [-0.067, -0.006] | -0.074 [-0.158, -0.012] |

## Reproduction of DG-162 §1 under its stricter rule

Rule `window_closed_before_test`; DG-162's published values from `~/dg-build/tickets/DG-162-what-the-model-actually-reads.md §1`.

| pos | n (this run / DG-162) | ppg_only r² (this / DG-162) | deployed r² (this / DG-162) | Δr² deployed−3col (this / DG-162) |
|---|---|---|---|---|
| QB | 95 / 95 | 0.320 / 0.320 | 0.383 / 0.383 | 0.030 / 0.030 |
| RB | 284 / 284 | 0.572 / 0.572 | 0.600 / 0.600 | -0.000 / -0.000 |
| WR | 456 / 456 | 0.623 / 0.623 | 0.661 / 0.661 | 0.010 / 0.010 |
| TE | 244 / 244 | 0.588 / 0.588 | 0.605 / 0.605 | 0.008 / 0.008 |

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
- git_head: `"ecc260ef2b7740f66bf199059b0606d215ed6e43"`
- git_branch: `"ticket/DG-177"`
- worktree: `{"ticket": "DG-177", "branch": "ticket/DG-177", "base": "origin/main", "shared_readonly": [".venv", "app/cache", "app/data/cfbd_cache", "app/data/identity", "app/data/nflverse_usage", "app/data/nflverse_usage.db", "app/data/model_forward_capture.db", "app/data/market_divergence_history.db", "app/data/playerprofiler.db", "app/data/fc_forward_capture.db", "app/data/fc_snapshots.db", "app/data/league_transactions.db", "app/data/league_transactions", "app/data/pff_exports", "app/data/footballguys", "app/data/sources", "app/data/backtest", "frontend/node_modules", "app/data/models"], "writable_copies": [], "ticket_file": "/Users/davidleess/dg-build/tickets/DG-177-veteran-forecast-candidate-with-historical-cutoffs.md"}`
- warehouse: `{"path": "/Users/davidleess/dg-wt/DG-177/app/data/nflverse_usage.db", "resolved": "/Users/davidleess/dynasty-genius-product/app/data/nflverse_usage.db", "bytes": 16347369472, "modified_utc": "2026-09-05T10:15:36.867655+00:00", "sha256": "not computed \u2014 multi-GB store; identified by path, size, mtime and table facts", "modified_at_open_utc": "2026-09-05T10:15:36.867655+00:00", "changed_during_run": false, "table": "ff_opportunity", "rows": 47282, "seasons": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"], "season_ingested_range": ["2018", "2025"], "source_era": ["ffopportunity_v1"]}`
- served_models: `{"QB": {"version": "engine_b_v2_qb", "path": "app/data/models/engine_b/runs/20260831T204458Z/qb_v2.pkl"}, "RB": {"version": "engine_b_v2_rb", "path": "app/data/models/engine_b/runs/20260831T204458Z/rb_v2.pkl"}, "WR": {"version": "engine_b_v2_wr", "path": "app/data/models/engine_b/runs/20260831T204458Z/wr_v2.pkl"}, "TE": {"version": "engine_b_v2_te", "path": "app/data/models/engine_b/runs/20260831T204458Z/te_v2.pkl"}}`
- notes: `["xfp_* columns are nflverse ffopportunity expected points, a third-party fitted model. Its documentation (https://ffopportunity.ffverse.com/, read 2026-09-06) says it \"uses xgboost and tidymodels trained on public nflverse data from 2006-2020\"; the model version behind each warehouse row is not recorded. That window overlaps feature seasons 2018-2020 at play level, so arms using them are labelled exploratory and are not point-in-time evidence.", "opp_* columns are raw per-game counts from the feature season only."]`
- versions: `{"python": "3.14.7", "scikit-learn": "1.8.0", "pandas": "3.0.5", "numpy": "2.5.2", "scipy": "1.17.1"}`
