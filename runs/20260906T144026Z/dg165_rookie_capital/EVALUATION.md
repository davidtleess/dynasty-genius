# DG-165 rookie draft-capital candidate — historical evaluation with information cutoffs

One fit per forecast year T on labels completed by T−1 (the same procedure as final scoring); class T
graded against what happened afterwards, each quantity only where its own label is complete today.
"Training baseline" = the prevalence / mean of that label in the training set at T, carried per row.

## Per-season quantities (season j = 1 is the rookie season)

### season 1

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2025 | 1662 | 0.22 | 0.18 | 0.841 (0.820, 0.860) | 0.1213 / 0.1708 | 0.3864 / 0.5255 |
| P(appears in season j) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.791 (0.770, 0.812) | 0.1411 / 0.1721 | 0.4380 / 0.5282 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2025 | 1662 | 53.25 | 41.57 | 55.21 / 70.82 | -11.68 |
| E[games] (unconditional) | 2005–2025 | 1662 | 7.65 | 6.71 | 4.93 / 6.05 | -0.94 |
| E[season points | appears] | 2005–2025 | 1296 | 68.29 | 55.27 | 58.97 / 72.59 | -13.02 |
| E[games | appears] | 2005–2025 | 1296 | 9.81 | 8.96 | 4.39 / 4.98 | -0.85 |
| E[ppg | appears] | 2005–2025 | 1296 | 5.69 | 4.89 | 3.96 / 4.72 | -0.80 |
| E[ppg | qualifies] (descriptive) | 2005–2025 | 362 | 11.64 | 10.50 | 3.49 / 3.64 | -1.13 |

Calibration of P(qualifies in season 1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 836 | 0.043 | 0.057 |
| 0.10-0.20 | 319 | 0.143 | 0.172 |
| 0.20-0.35 | 216 | 0.270 | 0.333 |
| 0.35-0.50 | 113 | 0.419 | 0.522 |
| 0.50-0.70 | 109 | 0.594 | 0.651 |
| 0.70-1.00 | 69 | 0.792 | 0.826 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 247 | 0.30 | 0.24 | 0.891 | 0.1210 / 0.2218 |
| RB | 444 | 0.25 | 0.22 | 0.799 | 0.1412 / 0.1937 |
| TE | 302 | 0.10 | 0.10 | 0.854 | 0.0686 / 0.0950 |
| WR | 669 | 0.22 | 0.18 | 0.820 | 0.1321 / 0.1710 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 0.70 | 0.63 |
| 2 | 210 | 0.40 | 0.33 |
| 3 | 236 | 0.21 | 0.19 |
| 4 | 261 | 0.16 | 0.12 |
| 5 | 220 | 0.10 | 0.07 |
| 6 | 257 | 0.04 | 0.04 |
| 7 | 269 | 0.03 | 0.02 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 247 | 56.68 | 37.99 | 65.25 / 87.39 | -18.69 |
| RB | 444 | 64.24 | 52.94 | 61.36 / 79.93 | -11.30 |
| TE | 302 | 34.56 | 26.34 | 36.13 / 45.48 | -8.22 |
| WR | 669 | 53.13 | 42.23 | 53.96 / 66.82 | -10.90 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 145.17 | 112.96 |
| 2 | 210 | 89.59 | 69.41 |
| 3 | 236 | 57.53 | 47.58 |
| 4 | 261 | 44.09 | 34.84 |
| 5 | 220 | 30.72 | 22.05 |
| 6 | 257 | 17.86 | 14.41 |
| 7 | 269 | 10.85 | 7.57 |

Training baseline for P(qualifies) by forecast year: 2005: 0.180, 2006: 0.178, 2007: 0.181, 2008: 0.173, 2009: 0.172, 2010: 0.176, 2011: 0.177, 2012: 0.177, 2013: 0.180, 2014: 0.184, 2015: 0.187, 2016: 0.189, 2017: 0.189, 2018: 0.192, 2019: 0.195, 2020: 0.197, 2021: 0.199, 2022: 0.202, 2023: 0.203, 2024: 0.206, 2025: 0.207

### season 2

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2024 | 1576 | 0.27 | 0.25 | 0.818 (0.798, 0.837) | 0.1424 / 0.1984 | 0.4466 / 0.5863 |
| P(appears in season j) | 2005–2024 | 1576 | 0.76 | 0.74 | 0.775 (0.756, 0.796) | 0.1525 / 0.1843 | 0.4606 / 0.5555 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2024 | 1576 | 66.15 | 56.24 | 68.18 / 84.68 | -9.90 |
| E[games] (unconditional) | 2005–2024 | 1576 | 7.88 | 7.38 | 5.38 / 6.33 | -0.50 |
| E[season points | appears] | 2005–2024 | 1194 | 87.31 | 76.25 | 73.95 / 85.78 | -11.06 |
| E[games | appears] | 2005–2024 | 1194 | 10.40 | 9.96 | 4.75 / 5.15 | -0.44 |
| E[ppg | appears] | 2005–2024 | 1194 | 6.93 | 6.22 | 4.60 / 5.36 | -0.71 |
| E[ppg | qualifies] (descriptive) | 2005–2024 | 429 | 12.66 | 12.06 | 3.91 / 4.02 | -0.61 |

Calibration of P(qualifies in season 2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 601 | 0.052 | 0.070 |
| 0.10-0.20 | 298 | 0.144 | 0.161 |
| 0.20-0.35 | 242 | 0.254 | 0.302 |
| 0.35-0.50 | 179 | 0.425 | 0.464 |
| 0.50-0.70 | 139 | 0.609 | 0.633 |
| 0.70-1.00 | 117 | 0.812 | 0.812 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 233 | 0.35 | 0.33 | 0.887 | 0.1193 / 0.2375 |
| RB | 419 | 0.30 | 0.26 | 0.820 | 0.1476 / 0.2104 |
| TE | 286 | 0.18 | 0.18 | 0.821 | 0.1086 / 0.1521 |
| WR | 638 | 0.27 | 0.24 | 0.769 | 0.1625 / 0.1971 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 0.76 | 0.74 |
| 2 | 199 | 0.47 | 0.47 |
| 3 | 226 | 0.35 | 0.28 |
| 4 | 247 | 0.15 | 0.17 |
| 5 | 210 | 0.16 | 0.10 |
| 6 | 244 | 0.09 | 0.06 |
| 7 | 251 | 0.04 | 0.03 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 233 | 77.38 | 62.05 | 80.80 / 109.71 | -15.32 |
| RB | 419 | 73.56 | 63.69 | 75.88 / 92.37 | -9.87 |
| TE | 286 | 45.07 | 38.49 | 49.08 / 59.22 | -6.58 |
| WR | 638 | 66.63 | 57.19 | 65.10 / 78.37 | -9.44 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 167.52 | 149.02 |
| 2 | 199 | 108.94 | 94.50 |
| 3 | 226 | 82.30 | 65.16 |
| 4 | 247 | 45.69 | 47.04 |
| 5 | 210 | 42.41 | 30.73 |
| 6 | 244 | 24.87 | 19.94 |
| 7 | 251 | 17.42 | 10.03 |

Training baseline for P(qualifies) by forecast year: 2005: 0.250, 2006: 0.246, 2007: 0.247, 2008: 0.250, 2009: 0.243, 2010: 0.248, 2011: 0.248, 2012: 0.254, 2013: 0.256, 2014: 0.254, 2015: 0.251, 2016: 0.253, 2017: 0.251, 2018: 0.248, 2019: 0.254, 2020: 0.257, 2021: 0.258, 2022: 0.260, 2023: 0.259, 2024: 0.261

### season 3

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2023 | 1499 | 0.25 | 0.25 | 0.806 (0.785, 0.829) | 0.1436 / 0.1900 | 0.4466 / 0.5678 |
| P(appears in season j) | 2005–2023 | 1499 | 0.66 | 0.65 | 0.747 (0.726, 0.769) | 0.1879 / 0.2253 | 0.5526 / 0.6429 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2023 | 1499 | 61.82 | 57.27 | 72.72 / 87.07 | -4.55 |
| E[games] (unconditional) | 2005–2023 | 1499 | 6.96 | 6.91 | 5.66 / 6.53 | -0.04 |
| E[season points | appears] | 2005–2023 | 988 | 93.79 | 87.83 | 80.71 / 91.55 | -5.96 |
| E[games | appears] | 2005–2023 | 988 | 10.55 | 10.57 | 4.77 / 5.09 | 0.02 |
| E[ppg | appears] | 2005–2023 | 988 | 7.36 | 6.99 | 5.01 / 5.75 | -0.38 |
| E[ppg | qualifies] (descriptive) | 2005–2023 | 382 | 13.10 | 12.55 | 3.92 / 4.19 | -0.55 |

Calibration of P(qualifies in season 3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 542 | 0.062 | 0.059 |
| 0.10-0.20 | 304 | 0.147 | 0.174 |
| 0.20-0.35 | 265 | 0.268 | 0.283 |
| 0.35-0.50 | 160 | 0.440 | 0.450 |
| 0.50-0.70 | 142 | 0.605 | 0.592 |
| 0.70-1.00 | 86 | 0.778 | 0.767 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 222 | 0.25 | 0.29 | 0.849 | 0.1187 / 0.1866 |
| RB | 400 | 0.29 | 0.24 | 0.798 | 0.1613 / 0.2074 |
| TE | 274 | 0.18 | 0.18 | 0.824 | 0.1127 / 0.1523 |
| WR | 603 | 0.27 | 0.27 | 0.788 | 0.1550 / 0.1967 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 0.69 | 0.70 |
| 2 | 193 | 0.45 | 0.46 |
| 3 | 217 | 0.31 | 0.29 |
| 4 | 231 | 0.19 | 0.18 |
| 5 | 199 | 0.15 | 0.11 |
| 6 | 230 | 0.09 | 0.07 |
| 7 | 244 | 0.03 | 0.05 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 222 | 58.46 | 57.10 | 79.71 / 103.03 | -1.36 |
| RB | 400 | 70.15 | 59.68 | 78.06 / 93.12 | -10.47 |
| TE | 274 | 48.00 | 43.52 | 52.16 / 61.62 | -4.47 |
| WR | 603 | 63.81 | 61.98 | 74.35 / 86.38 | -1.83 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 159.64 | 149.53 |
| 2 | 193 | 101.64 | 98.11 |
| 3 | 217 | 72.58 | 67.99 |
| 4 | 231 | 47.45 | 47.25 |
| 5 | 199 | 38.54 | 30.98 |
| 6 | 230 | 25.61 | 20.35 |
| 7 | 244 | 13.29 | 11.20 |

Training baseline for P(qualifies) by forecast year: 2005: 0.258, 2006: 0.258, 2007: 0.266, 2008: 0.257, 2009: 0.255, 2010: 0.255, 2011: 0.257, 2012: 0.252, 2013: 0.252, 2014: 0.253, 2015: 0.253, 2016: 0.248, 2017: 0.249, 2018: 0.249, 2019: 0.248, 2020: 0.251, 2021: 0.251, 2022: 0.253, 2023: 0.253

### season 4

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2022 | 1419 | 0.24 | 0.24 | 0.795 (0.772, 0.819) | 0.1386 / 0.1802 | 0.4376 / 0.5463 |
| P(appears in season j) | 2005–2022 | 1419 | 0.58 | 0.57 | 0.746 (0.725, 0.768) | 0.2003 / 0.2435 | 0.5868 / 0.6801 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2022 | 1419 | 56.51 | 53.28 | 72.13 / 83.64 | -3.23 |
| E[games] (unconditional) | 2005–2022 | 1419 | 6.29 | 6.18 | 5.79 / 6.56 | -0.11 |
| E[season points | appears] | 2005–2022 | 830 | 96.62 | 93.73 | 81.15 / 89.32 | -2.89 |
| E[games | appears] | 2005–2022 | 830 | 10.76 | 10.85 | 4.79 / 4.99 | 0.10 |
| E[ppg | appears] | 2005–2022 | 830 | 7.75 | 7.35 | 5.10 / 5.67 | -0.40 |
| E[ppg | qualifies] (descriptive) | 2005–2022 | 334 | 13.21 | 12.51 | 4.10 / 4.15 | -0.70 |

Calibration of P(qualifies in season 4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 337 | 0.072 | 0.056 |
| 0.10-0.20 | 485 | 0.141 | 0.126 |
| 0.20-0.35 | 281 | 0.260 | 0.246 |
| 0.35-0.50 | 145 | 0.421 | 0.455 |
| 0.50-0.70 | 100 | 0.584 | 0.650 |
| 0.70-1.00 | 71 | 0.818 | 0.761 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 208 | 0.27 | 0.31 | 0.805 | 0.1421 / 0.1992 |
| RB | 382 | 0.26 | 0.21 | 0.823 | 0.1466 / 0.1923 |
| TE | 259 | 0.17 | 0.19 | 0.784 | 0.1155 / 0.1493 |
| WR | 570 | 0.23 | 0.26 | 0.784 | 0.1426 / 0.1792 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 0.67 | 0.67 |
| 2 | 182 | 0.43 | 0.40 |
| 3 | 203 | 0.24 | 0.25 |
| 4 | 224 | 0.17 | 0.18 |
| 5 | 184 | 0.14 | 0.13 |
| 6 | 218 | 0.07 | 0.10 |
| 7 | 233 | 0.04 | 0.07 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 208 | 59.28 | 58.32 | 84.06 / 99.38 | -0.96 |
| RB | 382 | 62.08 | 54.32 | 76.56 / 88.07 | -7.75 |
| TE | 259 | 46.41 | 39.32 | 55.06 / 64.18 | -7.09 |
| WR | 570 | 56.37 | 57.09 | 71.18 / 82.11 | 0.72 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 144.77 | 138.80 |
| 2 | 182 | 98.91 | 86.30 |
| 3 | 203 | 63.36 | 58.83 |
| 4 | 224 | 45.06 | 42.99 |
| 5 | 184 | 33.09 | 30.66 |
| 6 | 218 | 19.83 | 22.30 |
| 7 | 233 | 14.97 | 15.17 |

Training baseline for P(qualifies) by forecast year: 2005: 0.272, 2006: 0.255, 2007: 0.247, 2008: 0.255, 2009: 0.261, 2010: 0.257, 2011: 0.253, 2012: 0.253, 2013: 0.250, 2014: 0.248, 2015: 0.241, 2016: 0.240, 2017: 0.239, 2018: 0.240, 2019: 0.237, 2020: 0.238, 2021: 0.240, 2022: 0.240

### season 5

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2021 | 1340 | 0.19 | 0.23 | 0.779 (0.752, 0.808) | 0.1285 / 0.1577 | 0.4122 / 0.4957 |
| P(appears in season j) | 2005–2021 | 1340 | 0.49 | 0.47 | 0.743 (0.722, 0.766) | 0.2059 / 0.2504 | 0.5997 / 0.6940 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2021 | 1340 | 48.61 | 49.39 | 72.09 / 82.36 | 0.78 |
| E[games] (unconditional) | 2005–2021 | 1340 | 5.24 | 5.28 | 5.78 / 6.44 | 0.04 |
| E[season points | appears] | 2005–2021 | 651 | 100.06 | 105.27 | 85.74 / 93.06 | 5.21 |
| E[games | appears] | 2005–2021 | 651 | 10.79 | 11.24 | 4.79 / 4.93 | 0.45 |
| E[ppg | appears] | 2005–2021 | 651 | 7.93 | 8.02 | 5.34 / 5.82 | 0.09 |
| E[ppg | qualifies] (descriptive) | 2005–2021 | 260 | 13.60 | 12.92 | 4.05 / 4.19 | -0.68 |

Calibration of P(qualifies in season 5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 324 | 0.077 | 0.052 |
| 0.10-0.20 | 471 | 0.142 | 0.100 |
| 0.20-0.35 | 286 | 0.262 | 0.255 |
| 0.35-0.50 | 152 | 0.413 | 0.368 |
| 0.50-0.70 | 66 | 0.590 | 0.545 |
| 0.70-1.00 | 41 | 0.807 | 0.756 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 199 | 0.24 | 0.29 | 0.860 | 0.1241 / 0.1810 |
| RB | 359 | 0.20 | 0.22 | 0.785 | 0.1301 / 0.1595 |
| TE | 240 | 0.14 | 0.17 | 0.775 | 0.0965 / 0.1258 |
| WR | 542 | 0.20 | 0.23 | 0.727 | 0.1432 / 0.1619 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 0.55 | 0.59 |
| 2 | 171 | 0.32 | 0.35 |
| 3 | 190 | 0.23 | 0.23 |
| 4 | 209 | 0.13 | 0.17 |
| 5 | 172 | 0.10 | 0.13 |
| 6 | 207 | 0.06 | 0.10 |
| 7 | 223 | 0.05 | 0.08 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 199 | 54.99 | 58.07 | 81.53 / 98.89 | 3.08 |
| RB | 359 | 49.24 | 50.98 | 70.99 / 81.00 | 1.75 |
| TE | 240 | 39.95 | 37.84 | 47.84 / 58.98 | -2.10 |
| WR | 542 | 49.70 | 50.26 | 77.83 / 85.41 | 0.57 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 129.35 | 129.94 |
| 2 | 171 | 80.61 | 80.61 |
| 3 | 190 | 58.40 | 54.43 |
| 4 | 209 | 34.10 | 39.04 |
| 5 | 172 | 27.25 | 27.95 |
| 6 | 207 | 18.75 | 20.10 |
| 7 | 223 | 12.71 | 13.90 |

Training baseline for P(qualifies) by forecast year: 2005: 0.255, 2006: 0.254, 2007: 0.238, 2008: 0.239, 2009: 0.237, 2010: 0.238, 2011: 0.230, 2012: 0.225, 2013: 0.222, 2014: 0.213, 2015: 0.208, 2016: 0.211, 2017: 0.211, 2018: 0.209, 2019: 0.207, 2020: 0.207, 2021: 0.205

### season 6

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2020 | 1265 | 0.17 | 0.20 | 0.782 (0.751, 0.810) | 0.1182 / 0.1431 | 0.3835 / 0.4616 |
| P(appears in season j) | 2005–2020 | 1265 | 0.40 | 0.41 | 0.735 (0.711, 0.758) | 0.2004 / 0.2418 | 0.5871 / 0.6768 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2020 | 1265 | 42.76 | 43.14 | 71.16 / 79.69 | 0.38 |
| E[games] (unconditional) | 2005–2020 | 1265 | 4.50 | 4.55 | 5.73 / 6.31 | 0.05 |
| E[season points | appears] | 2005–2020 | 508 | 106.47 | 109.41 | 90.43 / 94.37 | 2.93 |
| E[games | appears] | 2005–2020 | 508 | 11.21 | 11.22 | 4.73 / 4.85 | 0.01 |
| E[ppg | appears] | 2005–2020 | 508 | 8.25 | 8.43 | 5.46 / 5.75 | 0.18 |
| E[ppg | qualifies] (descriptive) | 2005–2020 | 217 | 13.53 | 12.78 | 4.18 / 4.16 | -0.75 |

Calibration of P(qualifies in season 6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 441 | 0.067 | 0.050 |
| 0.10-0.20 | 357 | 0.143 | 0.109 |
| 0.20-0.35 | 243 | 0.262 | 0.214 |
| 0.35-0.50 | 141 | 0.414 | 0.397 |
| 0.50-0.70 | 75 | 0.562 | 0.560 |
| 0.70-1.00 | 8 | 0.734 | 0.750 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 189 | 0.24 | 0.24 | 0.831 | 0.1333 / 0.1835 |
| RB | 340 | 0.17 | 0.21 | 0.768 | 0.1203 / 0.1429 |
| TE | 229 | 0.11 | 0.12 | 0.757 | 0.0947 / 0.1081 |
| WR | 507 | 0.17 | 0.21 | 0.770 | 0.1219 / 0.1441 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 0.50 | 0.50 |
| 2 | 163 | 0.33 | 0.34 |
| 3 | 179 | 0.16 | 0.22 |
| 4 | 197 | 0.14 | 0.16 |
| 5 | 164 | 0.06 | 0.11 |
| 6 | 193 | 0.05 | 0.08 |
| 7 | 214 | 0.05 | 0.06 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 189 | 52.89 | 54.35 | 87.20 / 97.94 | 1.47 |
| RB | 340 | 41.74 | 45.41 | 70.36 / 80.87 | 3.67 |
| TE | 229 | 34.21 | 31.25 | 50.69 / 57.17 | -2.95 |
| WR | 507 | 43.52 | 42.80 | 72.93 / 80.05 | -0.73 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 115.21 | 115.36 |
| 2 | 163 | 78.11 | 67.97 |
| 3 | 179 | 46.80 | 45.31 |
| 4 | 197 | 31.08 | 33.43 |
| 5 | 164 | 21.06 | 25.50 |
| 6 | 193 | 16.62 | 19.19 |
| 7 | 214 | 10.93 | 14.13 |

Training baseline for P(qualifies) by forecast year: 2005: 0.203, 2006: 0.200, 2007: 0.207, 2008: 0.212, 2009: 0.207, 2010: 0.208, 2011: 0.211, 2012: 0.205, 2013: 0.200, 2014: 0.199, 2015: 0.192, 2016: 0.187, 2017: 0.186, 2018: 0.183, 2019: 0.179, 2020: 0.179

## Cumulative quantities (window seasons 1..h)

### h = 1

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2025 | 1662 | 0.22 | 0.18 | 0.841 (0.822, 0.860) | 0.1213 / 0.1708 | 0.3864 / 0.5255 |
| P(any appearance in 1..h) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.791 (0.770, 0.810) | 0.1411 / 0.1721 | 0.4380 / 0.5282 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2025 | 1662 | 0.22 | 0.18 | 0.35 / 0.41 | -0.03 |

Calibration of P(any qualifying season in 1..1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 836 | 0.043 | 0.057 |
| 0.10-0.20 | 319 | 0.143 | 0.172 |
| 0.20-0.35 | 216 | 0.270 | 0.333 |
| 0.35-0.50 | 113 | 0.419 | 0.522 |
| 0.50-0.70 | 109 | 0.594 | 0.651 |
| 0.70-1.00 | 69 | 0.792 | 0.826 |

### h = 2

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2024 | 1576 | 0.32 | 0.30 | 0.830 (0.812, 0.846) | 0.1487 / 0.2183 | 0.4606 / 0.6284 |
| P(any appearance in 1..h) | 2005–2024 | 1576 | 0.86 | 0.84 | 0.801 (0.778, 0.823) | 0.1024 / 0.1192 | 0.3265 / 0.4027 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2024 | 1576 | 0.49 | 0.43 | 0.61 / 0.76 | -0.05 |

Calibration of P(any qualifying season in 1..2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 501 | 0.062 | 0.074 |
| 0.10-0.20 | 299 | 0.146 | 0.187 |
| 0.20-0.35 | 291 | 0.273 | 0.302 |
| 0.35-0.50 | 128 | 0.438 | 0.477 |
| 0.50-0.70 | 155 | 0.578 | 0.600 |
| 0.70-1.00 | 202 | 0.843 | 0.847 |

### h = 3

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2023 | 1499 | 0.36 | 0.35 | 0.826 (0.806, 0.844) | 0.1581 / 0.2312 | 0.4847 / 0.6550 |
| P(any appearance in 1..h) | 2005–2023 | 1499 | 0.88 | 0.87 | 0.774 (0.749, 0.798) | 0.0969 / 0.1078 | 0.3150 / 0.3740 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2023 | 1499 | 0.74 | 0.68 | 0.86 / 1.09 | -0.06 |

Calibration of P(any qualifying season in 1..3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 285 | 0.074 | 0.063 |
| 0.10-0.20 | 367 | 0.144 | 0.177 |
| 0.20-0.35 | 259 | 0.271 | 0.274 |
| 0.35-0.50 | 178 | 0.405 | 0.461 |
| 0.50-0.70 | 191 | 0.600 | 0.623 |
| 0.70-1.00 | 219 | 0.869 | 0.858 |

### h = 4

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2022 | 1419 | 0.39 | 0.39 | 0.815 (0.796, 0.834) | 0.1663 / 0.2386 | 0.5057 / 0.6702 |
| P(any appearance in 1..h) | 2005–2022 | 1419 | 0.88 | 0.87 | 0.772 (0.747, 0.799) | 0.0971 / 0.1080 | 0.3148 / 0.3752 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2022 | 1419 | 0.96 | 0.92 | 1.09 / 1.40 | -0.05 |

Calibration of P(any qualifying season in 1..4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 54 | 0.079 | 0.037 |
| 0.10-0.20 | 408 | 0.147 | 0.135 |
| 0.20-0.35 | 320 | 0.271 | 0.278 |
| 0.35-0.50 | 220 | 0.421 | 0.418 |
| 0.50-0.70 | 183 | 0.613 | 0.639 |
| 0.70-1.00 | 234 | 0.867 | 0.863 |

### h = 5

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2021 | 1340 | 0.41 | 0.42 | 0.816 (0.795, 0.835) | 0.1682 / 0.2419 | 0.5113 / 0.6768 |
| P(any appearance in 1..h) | 2005–2021 | 1340 | 0.87 | 0.87 | 0.774 (0.749, 0.799) | 0.0988 / 0.1108 | 0.3192 / 0.3832 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2021 | 1340 | 1.15 | 1.14 | 1.30 / 1.67 | -0.01 |

Calibration of P(any qualifying season in 1..5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 19 | 0.089 | 0.000 |
| 0.10-0.20 | 336 | 0.157 | 0.131 |
| 0.20-0.35 | 335 | 0.265 | 0.257 |
| 0.35-0.50 | 234 | 0.426 | 0.415 |
| 0.50-0.70 | 169 | 0.615 | 0.639 |
| 0.70-1.00 | 247 | 0.867 | 0.854 |

### h = 6

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2020 | 1265 | 0.42 | 0.43 | 0.816 (0.795, 0.836) | 0.1692 / 0.2442 | 0.5116 / 0.6815 |
| P(any appearance in 1..h) | 2005–2020 | 1265 | 0.87 | 0.87 | 0.772 (0.748, 0.798) | 0.1020 / 0.1152 | 0.3277 / 0.3985 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2020 | 1265 | 1.32 | 1.33 | 1.52 / 1.94 | 0.01 |

Calibration of P(any qualifying season in 1..6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 14 | 0.090 | 0.000 |
| 0.10-0.20 | 281 | 0.157 | 0.128 |
| 0.20-0.35 | 332 | 0.263 | 0.265 |
| 0.35-0.50 | 225 | 0.429 | 0.387 |
| 0.50-0.70 | 160 | 0.609 | 0.656 |
| 0.70-1.00 | 253 | 0.864 | 0.842 |

## Not gradable, and why

- forecast_year = 2021, season = 6: NFL season 2026 not complete by 2025; cannot be graded yet
- forecast_year = 2022, season = 5: NFL season 2026 not complete by 2025; cannot be graded yet
- forecast_year = 2022, season = 6: NFL season 2027 not complete by 2025; cannot be graded yet
- forecast_year = 2023, season = 4: NFL season 2026 not complete by 2025; cannot be graded yet
- forecast_year = 2023, season = 5: NFL season 2027 not complete by 2025; cannot be graded yet
- forecast_year = 2023, season = 6: NFL season 2028 not complete by 2025; cannot be graded yet
- forecast_year = 2024, season = 3: NFL season 2026 not complete by 2025; cannot be graded yet
- forecast_year = 2024, season = 4: NFL season 2027 not complete by 2025; cannot be graded yet
- forecast_year = 2024, season = 5: NFL season 2028 not complete by 2025; cannot be graded yet
- forecast_year = 2024, season = 6: NFL season 2029 not complete by 2025; cannot be graded yet
- forecast_year = 2025, season = 2: NFL season 2026 not complete by 2025; cannot be graded yet
- forecast_year = 2025, season = 3: NFL season 2027 not complete by 2025; cannot be graded yet
- forecast_year = 2025, season = 4: NFL season 2028 not complete by 2025; cannot be graded yet
- forecast_year = 2025, season = 5: NFL season 2029 not complete by 2025; cannot be graded yet
- forecast_year = 2025, season = 6: NFL season 2030 not complete by 2025; cannot be graded yet

## Per forecast year

| T | train classes | train rows | test rows | families on a constant fallback |
|---|---|---:|---:|---|
| 2005 | 1999–2004 | 482 | 77 | a_4, a_5, a_6, ppg_6|Q |
| 2006 | 1999–2005 | 559 | 74 | a_5, a_6 |
| 2007 | 1999–2006 | 633 | 80 | a_6 |
| 2008 | 1999–2007 | 713 | 87 | a_6 |
| 2009 | 1999–2008 | 800 | 87 | a_6 |
| 2010 | 1999–2009 | 887 | 78 | a_6 |
| 2011 | 1999–2010 | 965 | 82 | a_6 |
| 2012 | 1999–2011 | 1047 | 77 | a_6 |
| 2013 | 1999–2012 | 1124 | 80 | a_6 |
| 2014 | 1999–2013 | 1204 | 77 | a_6 |
| 2015 | 1999–2014 | 1281 | 79 | a_6 |
| 2016 | 1999–2015 | 1360 | 77 | a_6 |
| 2017 | 1999–2016 | 1437 | 83 | a_6 |
| 2018 | 1999–2017 | 1520 | 83 | a_6 |
| 2019 | 1999–2018 | 1603 | 80 | a_6 |
| 2020 | 1999–2019 | 1683 | 78 | a_6 |
| 2021 | 1999–2020 | 1761 | 75 | a_6 |
| 2022 | 1999–2021 | 1836 | 79 | a_6 |
| 2023 | 1999–2022 | 1915 | 80 | a_6 |
| 2024 | 1999–2023 | 1995 | 77 | a_6 |
| 2025 | 1999–2024 | 2072 | 86 | a_6 |
