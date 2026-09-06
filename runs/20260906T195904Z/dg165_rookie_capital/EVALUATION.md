# DG-165 rookie draft-capital candidate — historical evaluation with information cutoffs

One fit per forecast year T on labels completed by T−1 (the same procedure as final scoring); class T
graded against what happened afterwards, each quantity only where its own label is complete today.
"Training baseline" = the prevalence / mean of that label in the training set at T, carried per row.

## Per-season quantities (season j = 1 is the rookie season)

### season 1

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2025 | 1438 | 0.22 | 0.21 | 0.849 (0.828, 0.868) | 0.1182 / 0.1732 | 0.3775 / 0.5316 |
| P(appears in season j) | 2008–2025 | 1438 | 0.79 | 0.77 | 0.807 (0.783, 0.830) | 0.1315 / 0.1693 | 0.4136 / 0.5225 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2025 | 1438 | 51.76 | 49.80 | 51.57 / 68.61 | -1.96 |
| E[games] (unconditional) | 2008–2025 | 1438 | 7.44 | 7.04 | 4.54 / 5.74 | -0.39 |
| E[season points | appears] | 2008–2025 | 1132 | 65.75 | 64.58 | 55.12 / 69.87 | -1.17 |
| E[games | appears] | 2008–2025 | 1132 | 9.45 | 9.18 | 4.06 / 4.69 | -0.27 |
| E[ppg | appears] | 2008–2025 | 1132 | 5.63 | 5.62 | 3.83 / 4.76 | -0.01 |
| E[ppg | qualifies] (descriptive) | 2008–2025 | 318 | 11.89 | 12.26 | 3.37 / 3.60 | 0.37 |

Calibration of P(qualifies in season 1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 685 | 0.044 | 0.054 |
| 0.10-0.20 | 233 | 0.145 | 0.133 |
| 0.20-0.35 | 208 | 0.266 | 0.274 |
| 0.35-0.50 | 133 | 0.421 | 0.481 |
| 0.50-0.70 | 103 | 0.608 | 0.660 |
| 0.70-1.00 | 76 | 0.796 | 0.803 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 210 | 0.33 | 0.28 | 0.906 | 0.1136 / 0.2415 |
| RB | 387 | 0.26 | 0.23 | 0.822 | 0.1370 / 0.1952 |
| TE | 265 | 0.09 | 0.11 | 0.865 | 0.0603 / 0.0880 |
| WR | 576 | 0.22 | 0.21 | 0.811 | 0.1339 / 0.1729 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 0.73 | 0.67 |
| 2 | 182 | 0.43 | 0.39 |
| 3 | 200 | 0.21 | 0.24 |
| 4 | 228 | 0.16 | 0.14 |
| 5 | 194 | 0.11 | 0.08 |
| 6 | 231 | 0.03 | 0.04 |
| 7 | 228 | 0.03 | 0.02 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 210 | 57.85 | 48.19 | 61.72 / 87.36 | -9.65 |
| RB | 387 | 60.53 | 57.39 | 56.50 / 75.79 | -3.14 |
| TE | 265 | 33.21 | 35.98 | 34.21 / 44.26 | 2.77 |
| WR | 576 | 52.18 | 51.65 | 50.66 / 64.87 | -0.53 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 144.37 | 123.61 |
| 2 | 182 | 89.52 | 79.74 |
| 3 | 200 | 56.87 | 58.51 |
| 4 | 228 | 42.79 | 44.33 |
| 5 | 194 | 30.25 | 30.81 |
| 6 | 231 | 16.13 | 20.89 |
| 7 | 228 | 9.43 | 12.53 |

Training baseline for P(qualifies) by forecast year: 2008: 0.164, 2009: 0.165, 2010: 0.168, 2011: 0.169, 2012: 0.168, 2013: 0.170, 2014: 0.176, 2015: 0.182, 2016: 0.184, 2017: 0.183, 2018: 0.185, 2019: 0.189, 2020: 0.191, 2021: 0.194, 2022: 0.197, 2023: 0.198, 2024: 0.202, 2025: 0.202

### season 2

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2024 | 1352 | 0.28 | 0.27 | 0.827 (0.807, 0.847) | 0.1416 / 0.2014 | 0.4420 / 0.5927 |
| P(appears in season j) | 2008–2024 | 1352 | 0.77 | 0.75 | 0.775 (0.752, 0.797) | 0.1485 / 0.1799 | 0.4510 / 0.5458 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2024 | 1352 | 64.59 | 62.85 | 65.45 / 82.56 | -1.74 |
| E[games] (unconditional) | 2008–2024 | 1352 | 7.65 | 7.46 | 5.08 / 6.00 | -0.19 |
| E[season points | appears] | 2008–2024 | 1036 | 84.29 | 83.81 | 70.49 / 83.68 | -0.47 |
| E[games | appears] | 2008–2024 | 1036 | 9.98 | 9.96 | 4.43 / 4.83 | -0.02 |
| E[ppg | appears] | 2008–2024 | 1036 | 6.98 | 7.00 | 4.63 / 5.53 | 0.02 |
| E[ppg | qualifies] (descriptive) | 2008–2024 | 377 | 12.88 | 13.07 | 4.06 / 4.20 | 0.20 |

Calibration of P(qualifies in season 2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 475 | 0.055 | 0.057 |
| 0.10-0.20 | 236 | 0.149 | 0.165 |
| 0.20-0.35 | 228 | 0.266 | 0.254 |
| 0.35-0.50 | 148 | 0.422 | 0.480 |
| 0.50-0.70 | 143 | 0.596 | 0.587 |
| 0.70-1.00 | 122 | 0.810 | 0.803 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 196 | 0.37 | 0.34 | 0.903 | 0.1115 / 0.2436 |
| RB | 362 | 0.30 | 0.28 | 0.817 | 0.1491 / 0.2108 |
| TE | 249 | 0.17 | 0.21 | 0.853 | 0.1020 / 0.1486 |
| WR | 545 | 0.28 | 0.27 | 0.774 | 0.1656 / 0.2042 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 165 | 0.76 | 0.76 |
| 2 | 171 | 0.52 | 0.52 |
| 3 | 190 | 0.39 | 0.34 |
| 4 | 214 | 0.15 | 0.21 |
| 5 | 184 | 0.17 | 0.12 |
| 6 | 218 | 0.08 | 0.07 |
| 7 | 210 | 0.03 | 0.04 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 196 | 79.07 | 65.71 | 80.25 / 112.16 | -13.36 |
| RB | 362 | 70.55 | 70.39 | 71.42 / 88.39 | -0.16 |
| TE | 249 | 42.56 | 46.45 | 46.82 / 56.63 | 3.89 |
| WR | 545 | 65.49 | 64.31 | 62.62 / 75.70 | -1.18 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 165 | 165.60 | 152.81 |
| 2 | 171 | 109.20 | 102.28 |
| 3 | 190 | 83.12 | 74.52 |
| 4 | 214 | 44.15 | 55.58 |
| 5 | 184 | 41.93 | 38.86 |
| 6 | 218 | 24.15 | 26.62 |
| 7 | 210 | 14.79 | 15.53 |

Training baseline for P(qualifies) by forecast year: 2008: 0.264, 2009: 0.253, 2010: 0.258, 2011: 0.256, 2012: 0.262, 2013: 0.265, 2014: 0.261, 2015: 0.258, 2016: 0.260, 2017: 0.257, 2018: 0.254, 2019: 0.261, 2020: 0.262, 2021: 0.264, 2022: 0.266, 2023: 0.264, 2024: 0.267

### season 3

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2023 | 1275 | 0.26 | 0.24 | 0.812 (0.789, 0.833) | 0.1449 / 0.1943 | 0.4494 / 0.5772 |
| P(appears in season j) | 2008–2023 | 1275 | 0.67 | 0.64 | 0.746 (0.723, 0.771) | 0.1871 / 0.2225 | 0.5532 / 0.6371 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2023 | 1275 | 60.21 | 56.38 | 69.31 / 84.08 | -3.83 |
| E[games] (unconditional) | 2008–2023 | 1275 | 6.79 | 6.38 | 5.36 / 6.17 | -0.41 |
| E[season points | appears] | 2008–2023 | 851 | 90.21 | 87.44 | 76.38 / 88.07 | -2.77 |
| E[games | appears] | 2008–2023 | 851 | 10.17 | 9.93 | 4.44 / 4.71 | -0.24 |
| E[ppg | appears] | 2008–2023 | 851 | 7.36 | 7.37 | 5.04 / 5.84 | 0.01 |
| E[ppg | qualifies] (descriptive) | 2008–2023 | 336 | 13.20 | 13.41 | 4.05 / 4.29 | 0.21 |

Calibration of P(qualifies in season 3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 457 | 0.059 | 0.061 |
| 0.10-0.20 | 248 | 0.143 | 0.181 |
| 0.20-0.35 | 226 | 0.266 | 0.279 |
| 0.35-0.50 | 151 | 0.429 | 0.450 |
| 0.50-0.70 | 134 | 0.602 | 0.642 |
| 0.70-1.00 | 59 | 0.748 | 0.780 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 185 | 0.26 | 0.26 | 0.865 | 0.1109 / 0.1923 |
| RB | 343 | 0.31 | 0.26 | 0.794 | 0.1642 / 0.2146 |
| TE | 237 | 0.18 | 0.18 | 0.815 | 0.1141 / 0.1532 |
| WR | 510 | 0.28 | 0.26 | 0.787 | 0.1586 / 0.2004 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 151 | 0.71 | 0.67 |
| 2 | 165 | 0.46 | 0.47 |
| 3 | 181 | 0.36 | 0.30 |
| 4 | 198 | 0.17 | 0.19 |
| 5 | 173 | 0.16 | 0.11 |
| 6 | 204 | 0.10 | 0.07 |
| 7 | 203 | 0.03 | 0.04 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 185 | 60.35 | 52.77 | 77.74 / 103.28 | -7.58 |
| RB | 343 | 68.03 | 62.56 | 73.28 / 89.51 | -5.46 |
| TE | 237 | 44.91 | 45.18 | 49.26 / 57.71 | 0.27 |
| WR | 510 | 62.01 | 58.74 | 71.26 / 82.88 | -3.27 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 151 | 159.64 | 142.04 |
| 2 | 165 | 98.26 | 97.76 |
| 3 | 181 | 74.93 | 68.32 |
| 4 | 198 | 44.24 | 48.04 |
| 5 | 173 | 37.65 | 32.29 |
| 6 | 204 | 24.86 | 21.27 |
| 7 | 203 | 12.53 | 12.35 |

Training baseline for P(qualifies) by forecast year: 2008: 0.276, 2009: 0.271, 2010: 0.272, 2011: 0.272, 2012: 0.263, 2013: 0.262, 2014: 0.262, 2015: 0.260, 2016: 0.254, 2017: 0.255, 2018: 0.256, 2019: 0.255, 2020: 0.258, 2021: 0.258, 2022: 0.260, 2023: 0.263

### season 4

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2022 | 1195 | 0.24 | 0.23 | 0.809 (0.783, 0.834) | 0.1357 / 0.1803 | 0.4267 / 0.5467 |
| P(appears in season j) | 2008–2022 | 1195 | 0.59 | 0.56 | 0.738 (0.713, 0.761) | 0.2036 / 0.2422 | 0.5962 / 0.6774 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2022 | 1195 | 53.82 | 51.07 | 68.72 / 80.33 | -2.76 |
| E[games] (unconditional) | 2008–2022 | 1195 | 6.04 | 5.66 | 5.56 / 6.22 | -0.38 |
| E[season points | appears] | 2008–2022 | 707 | 90.98 | 92.59 | 76.78 / 85.95 | 1.61 |
| E[games | appears] | 2008–2022 | 707 | 10.21 | 10.18 | 4.52 / 4.72 | -0.02 |
| E[ppg | appears] | 2008–2022 | 707 | 7.63 | 7.86 | 5.17 / 5.84 | 0.23 |
| E[ppg | qualifies] (descriptive) | 2008–2022 | 281 | 13.35 | 13.60 | 4.21 / 4.29 | 0.25 |

Calibration of P(qualifies in season 4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 380 | 0.065 | 0.058 |
| 0.10-0.20 | 343 | 0.144 | 0.140 |
| 0.20-0.35 | 212 | 0.260 | 0.283 |
| 0.35-0.50 | 119 | 0.420 | 0.429 |
| 0.50-0.70 | 94 | 0.587 | 0.681 |
| 0.70-1.00 | 47 | 0.787 | 0.766 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 171 | 0.26 | 0.28 | 0.864 | 0.1241 / 0.1946 |
| RB | 325 | 0.25 | 0.21 | 0.815 | 0.1474 / 0.1892 |
| TE | 222 | 0.18 | 0.18 | 0.784 | 0.1197 / 0.1530 |
| WR | 477 | 0.24 | 0.24 | 0.793 | 0.1394 / 0.1820 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 141 | 0.68 | 0.64 |
| 2 | 154 | 0.45 | 0.40 |
| 3 | 167 | 0.27 | 0.24 |
| 4 | 191 | 0.16 | 0.17 |
| 5 | 158 | 0.13 | 0.12 |
| 6 | 192 | 0.07 | 0.09 |
| 7 | 192 | 0.03 | 0.06 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 171 | 56.99 | 49.92 | 82.27 / 98.86 | -7.07 |
| RB | 325 | 58.19 | 53.59 | 71.80 / 83.46 | -4.60 |
| TE | 222 | 43.82 | 41.49 | 53.18 / 61.49 | -2.33 |
| WR | 477 | 54.37 | 54.21 | 67.64 / 78.48 | -0.16 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 141 | 137.97 | 126.40 |
| 2 | 154 | 98.86 | 85.16 |
| 3 | 167 | 65.52 | 58.56 |
| 4 | 191 | 42.16 | 43.14 |
| 5 | 158 | 30.95 | 30.98 |
| 6 | 192 | 19.11 | 22.33 |
| 7 | 192 | 10.88 | 15.01 |

Training baseline for P(qualifies) by forecast year: 2008: 0.261, 2009: 0.268, 2010: 0.262, 2011: 0.260, 2012: 0.259, 2013: 0.256, 2014: 0.253, 2015: 0.244, 2016: 0.244, 2017: 0.243, 2018: 0.243, 2019: 0.240, 2020: 0.240, 2021: 0.242, 2022: 0.242

### season 5

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2021 | 1116 | 0.19 | 0.20 | 0.776 (0.749, 0.805) | 0.1307 / 0.1565 | 0.4142 / 0.4929 |
| P(appears in season j) | 2008–2021 | 1116 | 0.50 | 0.47 | 0.729 (0.703, 0.753) | 0.2131 / 0.2508 | 0.6216 / 0.6948 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2021 | 1116 | 46.64 | 44.21 | 69.69 / 79.36 | -2.44 |
| E[games] (unconditional) | 2008–2021 | 1116 | 5.07 | 4.83 | 5.58 / 6.12 | -0.24 |
| E[season points | appears] | 2008–2021 | 556 | 93.62 | 95.81 | 82.26 / 89.86 | 2.19 |
| E[games | appears] | 2008–2021 | 556 | 10.17 | 10.32 | 4.66 / 4.74 | 0.15 |
| E[ppg | appears] | 2008–2021 | 556 | 7.82 | 8.11 | 5.49 / 5.96 | 0.29 |
| E[ppg | qualifies] (descriptive) | 2008–2021 | 215 | 13.85 | 13.24 | 4.53 / 4.38 | -0.61 |

Calibration of P(qualifies in season 5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 405 | 0.063 | 0.052 |
| 0.10-0.20 | 320 | 0.143 | 0.131 |
| 0.20-0.35 | 219 | 0.270 | 0.315 |
| 0.35-0.50 | 98 | 0.423 | 0.408 |
| 0.50-0.70 | 57 | 0.598 | 0.579 |
| 0.70-1.00 | 17 | 0.799 | 0.588 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 162 | 0.23 | 0.24 | 0.861 | 0.1201 / 0.1775 |
| RB | 302 | 0.19 | 0.17 | 0.768 | 0.1360 / 0.1564 |
| TE | 203 | 0.14 | 0.14 | 0.792 | 0.0969 / 0.1252 |
| WR | 449 | 0.20 | 0.22 | 0.724 | 0.1463 / 0.1632 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 134 | 0.53 | 0.53 |
| 2 | 143 | 0.35 | 0.33 |
| 3 | 154 | 0.25 | 0.22 |
| 4 | 176 | 0.11 | 0.15 |
| 5 | 146 | 0.10 | 0.11 |
| 6 | 181 | 0.07 | 0.08 |
| 7 | 182 | 0.04 | 0.06 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 162 | 53.45 | 44.17 | 80.72 / 97.83 | -9.28 |
| RB | 302 | 46.85 | 46.90 | 67.39 / 76.83 | 0.05 |
| TE | 203 | 36.77 | 35.95 | 45.39 / 56.25 | -0.82 |
| WR | 449 | 48.51 | 46.15 | 75.72 / 82.46 | -2.37 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 134 | 123.80 | 114.34 |
| 2 | 143 | 82.22 | 72.81 |
| 3 | 154 | 59.94 | 49.53 |
| 4 | 176 | 30.01 | 36.07 |
| 5 | 146 | 26.94 | 26.09 |
| 6 | 181 | 18.71 | 18.79 |
| 7 | 182 | 10.32 | 13.28 |

Training baseline for P(qualifies) by forecast year: 2008: 0.233, 2009: 0.235, 2010: 0.236, 2011: 0.226, 2012: 0.225, 2013: 0.224, 2014: 0.213, 2015: 0.206, 2016: 0.209, 2017: 0.209, 2018: 0.206, 2019: 0.204, 2020: 0.205, 2021: 0.204

### season 6

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2008–2020 | 1041 | 0.17 | 0.16 | 0.770 (0.740, 0.802) | 0.1212 / 0.1436 | 0.3896 / 0.4629 |
| P(appears in season j) | 2008–2020 | 1041 | 0.40 | 0.38 | 0.700 (0.672, 0.727) | 0.2136 / 0.2431 | 0.6207 / 0.6793 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2008–2020 | 1041 | 40.52 | 36.42 | 70.00 / 76.52 | -4.10 |
| E[games] (unconditional) | 2008–2020 | 1041 | 4.27 | 4.14 | 5.54 / 5.97 | -0.12 |
| E[season points | appears] | 2008–2020 | 418 | 100.91 | 99.90 | 87.43 / 90.64 | -1.01 |
| E[games | appears] | 2008–2020 | 418 | 10.63 | 11.09 | 4.54 / 4.55 | 0.47 |
| E[ppg | appears] | 2008–2020 | 418 | 8.15 | 7.94 | 5.56 / 5.86 | -0.21 |
| E[ppg | qualifies] (descriptive) | 2008–2020 | 179 | 13.61 | 13.16 | 4.60 / 4.03 | -0.45 |

Calibration of P(qualifies in season 6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 504 | 0.055 | 0.060 |
| 0.10-0.20 | 234 | 0.140 | 0.162 |
| 0.20-0.35 | 167 | 0.258 | 0.263 |
| 0.35-0.50 | 88 | 0.408 | 0.466 |
| 0.50-0.70 | 44 | 0.580 | 0.545 |
| 0.70-1.00 | 4 | 0.740 | 0.500 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 152 | 0.22 | 0.21 | 0.847 | 0.1274 / 0.1751 |
| RB | 283 | 0.16 | 0.16 | 0.722 | 0.1244 / 0.1386 |
| TE | 192 | 0.11 | 0.12 | 0.748 | 0.0930 / 0.1058 |
| WR | 414 | 0.19 | 0.17 | 0.756 | 0.1297 / 0.1530 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 121 | 0.47 | 0.45 |
| 2 | 135 | 0.37 | 0.29 |
| 3 | 143 | 0.20 | 0.18 |
| 4 | 164 | 0.11 | 0.12 |
| 5 | 138 | 0.07 | 0.09 |
| 6 | 167 | 0.05 | 0.06 |
| 7 | 173 | 0.03 | 0.04 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 152 | 50.01 | 39.74 | 86.71 / 97.16 | -10.27 |
| RB | 283 | 38.71 | 40.14 | 69.73 / 75.83 | 1.44 |
| TE | 192 | 30.17 | 29.98 | 49.01 / 54.61 | -0.19 |
| WR | 414 | 43.07 | 35.64 | 71.58 / 77.09 | -7.43 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 121 | 105.54 | 99.90 |
| 2 | 135 | 79.78 | 60.12 |
| 3 | 143 | 50.87 | 39.08 |
| 4 | 164 | 26.86 | 28.58 |
| 5 | 138 | 22.06 | 21.27 |
| 6 | 167 | 16.18 | 15.19 |
| 7 | 173 | 7.02 | 11.34 |

Training baseline for P(qualifies) by forecast year: 2008: 0.223, 2009: 0.211, 2010: 0.212, 2011: 0.215, 2012: 0.208, 2013: 0.200, 2014: 0.199, 2015: 0.191, 2016: 0.185, 2017: 0.184, 2018: 0.181, 2019: 0.178, 2020: 0.178

## Cumulative quantities (window seasons 1..h)

### h = 1

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2025 | 1438 | 0.22 | 0.21 | 0.849 (0.828, 0.868) | 0.1182 / 0.1732 | 0.3775 / 0.5316 |
| P(any appearance in 1..h) | 2008–2025 | 1438 | 0.79 | 0.77 | 0.807 (0.784, 0.829) | 0.1315 / 0.1693 | 0.4136 / 0.5225 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2025 | 1438 | 0.22 | 0.21 | 0.34 / 0.42 | -0.01 |

Calibration of P(any qualifying season in 1..1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 685 | 0.044 | 0.054 |
| 0.10-0.20 | 233 | 0.145 | 0.133 |
| 0.20-0.35 | 208 | 0.266 | 0.274 |
| 0.35-0.50 | 133 | 0.421 | 0.481 |
| 0.50-0.70 | 103 | 0.608 | 0.660 |
| 0.70-1.00 | 76 | 0.796 | 0.803 |

### h = 2

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2024 | 1352 | 0.33 | 0.32 | 0.844 (0.825, 0.862) | 0.1435 / 0.2211 | 0.4463 / 0.6343 |
| P(any appearance in 1..h) | 2008–2024 | 1352 | 0.87 | 0.86 | 0.821 (0.796, 0.845) | 0.0919 / 0.1114 | 0.2988 / 0.3834 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2024 | 1352 | 0.50 | 0.48 | 0.60 / 0.77 | -0.02 |

Calibration of P(any qualifying season in 1..2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 351 | 0.060 | 0.060 |
| 0.10-0.20 | 275 | 0.143 | 0.164 |
| 0.20-0.35 | 232 | 0.268 | 0.246 |
| 0.35-0.50 | 156 | 0.414 | 0.423 |
| 0.50-0.70 | 159 | 0.592 | 0.635 |
| 0.70-1.00 | 179 | 0.851 | 0.860 |

### h = 3

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2023 | 1275 | 0.37 | 0.37 | 0.836 (0.818, 0.855) | 0.1541 / 0.2332 | 0.4738 / 0.6591 |
| P(any appearance in 1..h) | 2008–2023 | 1275 | 0.89 | 0.87 | 0.790 (0.760, 0.819) | 0.0874 / 0.0997 | 0.2927 / 0.3527 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2023 | 1275 | 0.76 | 0.71 | 0.85 / 1.10 | -0.04 |

Calibration of P(any qualifying season in 1..3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 213 | 0.077 | 0.042 |
| 0.10-0.20 | 277 | 0.143 | 0.152 |
| 0.20-0.35 | 248 | 0.270 | 0.254 |
| 0.35-0.50 | 177 | 0.421 | 0.446 |
| 0.50-0.70 | 171 | 0.614 | 0.661 |
| 0.70-1.00 | 189 | 0.868 | 0.878 |

### h = 4

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2022 | 1195 | 0.40 | 0.40 | 0.824 (0.802, 0.843) | 0.1636 / 0.2399 | 0.4983 / 0.6729 |
| P(any appearance in 1..h) | 2008–2022 | 1195 | 0.89 | 0.88 | 0.782 (0.753, 0.816) | 0.0867 / 0.0970 | 0.2904 / 0.3454 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2022 | 1195 | 0.98 | 0.94 | 1.08 / 1.41 | -0.05 |

Calibration of P(any qualifying season in 1..4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 79 | 0.080 | 0.025 |
| 0.10-0.20 | 285 | 0.146 | 0.133 |
| 0.20-0.35 | 250 | 0.265 | 0.284 |
| 0.35-0.50 | 201 | 0.418 | 0.383 |
| 0.50-0.70 | 173 | 0.605 | 0.642 |
| 0.70-1.00 | 207 | 0.861 | 0.860 |

### h = 5

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2021 | 1116 | 0.41 | 0.42 | 0.824 (0.802, 0.845) | 0.1651 / 0.2432 | 0.5029 / 0.6794 |
| P(any appearance in 1..h) | 2008–2021 | 1116 | 0.89 | 0.88 | 0.784 (0.753, 0.815) | 0.0881 / 0.0993 | 0.2943 / 0.3513 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2021 | 1116 | 1.17 | 1.13 | 1.29 / 1.68 | -0.04 |

Calibration of P(any qualifying season in 1..5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 42 | 0.082 | 0.048 |
| 0.10-0.20 | 258 | 0.152 | 0.147 |
| 0.20-0.35 | 241 | 0.265 | 0.253 |
| 0.35-0.50 | 190 | 0.421 | 0.368 |
| 0.50-0.70 | 171 | 0.602 | 0.608 |
| 0.70-1.00 | 214 | 0.860 | 0.879 |

### h = 6

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2008–2020 | 1041 | 0.42 | 0.43 | 0.823 (0.799, 0.844) | 0.1666 / 0.2451 | 0.5041 / 0.6834 |
| P(any appearance in 1..h) | 2008–2020 | 1041 | 0.88 | 0.88 | 0.776 (0.740, 0.806) | 0.0917 / 0.1023 | 0.3049 / 0.3587 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2008–2020 | 1041 | 1.34 | 1.28 | 1.51 / 1.94 | -0.06 |

Calibration of P(any qualifying season in 1..6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 40 | 0.082 | 0.050 |
| 0.10-0.20 | 229 | 0.151 | 0.157 |
| 0.20-0.35 | 227 | 0.267 | 0.256 |
| 0.35-0.50 | 176 | 0.422 | 0.369 |
| 0.50-0.70 | 164 | 0.598 | 0.616 |
| 0.70-1.00 | 205 | 0.860 | 0.878 |

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
| 2008 | 2001–2007 | 558 | 87 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2009 | 2001–2008 | 645 | 87 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2010 | 2001–2009 | 732 | 78 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2011 | 2001–2010 | 810 | 82 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2012 | 2001–2011 | 892 | 77 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2013 | 2001–2012 | 969 | 80 | a_5|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2014 | 2001–2013 | 1049 | 77 | q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2015 | 2001–2014 | 1126 | 79 | q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2016 | 2001–2015 | 1205 | 77 | q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2017 | 2001–2016 | 1282 | 83 | q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2018 | 2001–2017 | 1365 | 83 | q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2019 | 2001–2018 | 1448 | 80 | q_4|s0, q_5|s0, q_6|s0 |
| 2020 | 2001–2019 | 1528 | 78 | q_4|s0, q_5|s0, q_6|s0 |
| 2021 | 2001–2020 | 1606 | 75 | q_4|s0, q_5|s0, q_6|s0 |
| 2022 | 2001–2021 | 1681 | 79 | q_4|s0, q_5|s0, q_6|s0 |
| 2023 | 2001–2022 | 1760 | 80 | q_4|s0, q_5|s0, q_6|s0 |
| 2024 | 2001–2023 | 1840 | 77 | q_4|s0, q_5|s0, q_6|s0 |
| 2025 | 2001–2024 | 1917 | 86 | q_4|s0, q_5|s0, q_6|s0 |
