# DG-165 rookie draft-capital candidate — historical evaluation with information cutoffs

One fit per forecast year T on labels completed by T−1 (the same procedure as final scoring); class T
graded against what happened afterwards, each quantity only where its own label is complete today.
"Training baseline" = the prevalence / mean of that label in the training set at T, carried per row.

## Per-season quantities (season j = 1 is the rookie season)

### season 1

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.840 (0.818, 0.859) | 0.1197 / 0.1708 | 0.3822 / 0.5255 |
| P(appears in season j) | 2005–2025 | 1662 | 0.78 | 0.76 | 0.794 (0.773, 0.816) | 0.1398 / 0.1721 | 0.4351 / 0.5282 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2025 | 1662 | 53.25 | 50.07 | 53.91 / 70.82 | -3.18 |
| E[games] (unconditional) | 2005–2025 | 1662 | 7.65 | 7.19 | 4.83 / 6.05 | -0.46 |
| E[season points | appears] | 2005–2025 | 1296 | 68.29 | 66.28 | 57.77 / 72.59 | -2.01 |
| E[games | appears] | 2005–2025 | 1296 | 9.81 | 9.54 | 4.32 / 4.98 | -0.27 |
| E[ppg | appears] | 2005–2025 | 1296 | 5.69 | 5.62 | 3.89 / 4.72 | -0.07 |
| E[ppg | qualifies] (descriptive) | 2005–2025 | 362 | 11.64 | 11.70 | 3.40 / 3.64 | 0.07 |

Calibration of P(qualifies in season 1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 783 | 0.047 | 0.056 |
| 0.10-0.20 | 294 | 0.144 | 0.143 |
| 0.20-0.35 | 230 | 0.265 | 0.257 |
| 0.35-0.50 | 149 | 0.425 | 0.456 |
| 0.50-0.70 | 106 | 0.604 | 0.660 |
| 0.70-1.00 | 100 | 0.803 | 0.790 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 247 | 0.30 | 0.27 | 0.891 | 0.1191 / 0.2218 |
| RB | 444 | 0.25 | 0.25 | 0.803 | 0.1378 / 0.1937 |
| TE | 302 | 0.10 | 0.11 | 0.849 | 0.0689 / 0.0950 |
| WR | 669 | 0.22 | 0.21 | 0.819 | 0.1309 / 0.1710 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 0.70 | 0.67 |
| 2 | 210 | 0.40 | 0.38 |
| 3 | 236 | 0.21 | 0.22 |
| 4 | 261 | 0.16 | 0.14 |
| 5 | 220 | 0.10 | 0.08 |
| 6 | 257 | 0.04 | 0.05 |
| 7 | 269 | 0.03 | 0.03 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 247 | 56.68 | 45.55 | 63.35 / 87.39 | -11.13 |
| RB | 444 | 64.24 | 60.99 | 59.80 / 79.93 | -3.25 |
| TE | 302 | 34.56 | 35.41 | 35.34 / 45.48 | 0.84 |
| WR | 669 | 53.13 | 51.11 | 52.94 / 66.82 | -2.02 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 145.17 | 124.31 |
| 2 | 210 | 89.59 | 79.14 |
| 3 | 236 | 57.53 | 57.06 |
| 4 | 261 | 44.09 | 43.82 |
| 5 | 220 | 30.72 | 30.42 |
| 6 | 257 | 17.86 | 21.44 |
| 7 | 269 | 10.85 | 13.05 |

Training baseline for P(qualifies) by forecast year: 2005: 0.180, 2006: 0.178, 2007: 0.181, 2008: 0.173, 2009: 0.172, 2010: 0.176, 2011: 0.177, 2012: 0.177, 2013: 0.180, 2014: 0.184, 2015: 0.187, 2016: 0.189, 2017: 0.189, 2018: 0.192, 2019: 0.195, 2020: 0.197, 2021: 0.199, 2022: 0.202, 2023: 0.203, 2024: 0.206, 2025: 0.207

### season 2

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2024 | 1576 | 0.27 | 0.26 | 0.817 (0.796, 0.836) | 0.1425 / 0.1984 | 0.4466 / 0.5863 |
| P(appears in season j) | 2005–2024 | 1576 | 0.76 | 0.74 | 0.777 (0.757, 0.797) | 0.1522 / 0.1843 | 0.4602 / 0.5555 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2024 | 1576 | 66.15 | 63.58 | 67.63 / 84.68 | -2.57 |
| E[games] (unconditional) | 2005–2024 | 1576 | 7.88 | 7.56 | 5.36 / 6.33 | -0.31 |
| E[season points | appears] | 2005–2024 | 1194 | 87.31 | 86.20 | 73.42 / 85.78 | -1.12 |
| E[games | appears] | 2005–2024 | 1194 | 10.40 | 10.20 | 4.74 / 5.15 | -0.19 |
| E[ppg | appears] | 2005–2024 | 1194 | 6.93 | 6.94 | 4.57 / 5.36 | 0.01 |
| E[ppg | qualifies] (descriptive) | 2005–2024 | 429 | 12.66 | 12.81 | 3.92 / 4.02 | 0.15 |

Calibration of P(qualifies in season 2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 581 | 0.054 | 0.067 |
| 0.10-0.20 | 288 | 0.148 | 0.177 |
| 0.20-0.35 | 253 | 0.264 | 0.265 |
| 0.35-0.50 | 150 | 0.423 | 0.460 |
| 0.50-0.70 | 156 | 0.589 | 0.551 |
| 0.70-1.00 | 148 | 0.811 | 0.791 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 233 | 0.35 | 0.35 | 0.889 | 0.1185 / 0.2375 |
| RB | 419 | 0.30 | 0.28 | 0.820 | 0.1466 / 0.2104 |
| TE | 286 | 0.18 | 0.19 | 0.817 | 0.1110 / 0.1521 |
| WR | 638 | 0.27 | 0.26 | 0.767 | 0.1628 / 0.1971 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 0.76 | 0.77 |
| 2 | 199 | 0.47 | 0.50 |
| 3 | 226 | 0.35 | 0.31 |
| 4 | 247 | 0.15 | 0.19 |
| 5 | 210 | 0.16 | 0.11 |
| 6 | 244 | 0.09 | 0.07 |
| 7 | 251 | 0.04 | 0.04 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 233 | 77.38 | 68.63 | 79.27 / 109.71 | -8.75 |
| RB | 419 | 73.56 | 70.65 | 74.67 / 92.37 | -2.91 |
| TE | 286 | 45.07 | 46.14 | 49.75 / 59.22 | 1.06 |
| WR | 638 | 66.63 | 64.91 | 65.05 / 78.37 | -1.72 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 167.52 | 158.92 |
| 2 | 199 | 108.94 | 103.28 |
| 3 | 226 | 82.30 | 73.68 |
| 4 | 247 | 45.69 | 54.86 |
| 5 | 210 | 42.41 | 37.87 |
| 6 | 244 | 24.87 | 25.84 |
| 7 | 251 | 17.42 | 14.22 |

Training baseline for P(qualifies) by forecast year: 2005: 0.250, 2006: 0.246, 2007: 0.247, 2008: 0.250, 2009: 0.243, 2010: 0.248, 2011: 0.248, 2012: 0.254, 2013: 0.256, 2014: 0.254, 2015: 0.251, 2016: 0.253, 2017: 0.251, 2018: 0.248, 2019: 0.254, 2020: 0.257, 2021: 0.258, 2022: 0.260, 2023: 0.259, 2024: 0.261

### season 3

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2023 | 1499 | 0.25 | 0.25 | 0.806 (0.785, 0.829) | 0.1437 / 0.1900 | 0.4468 / 0.5678 |
| P(appears in season j) | 2005–2023 | 1499 | 0.66 | 0.65 | 0.746 (0.726, 0.769) | 0.1882 / 0.2253 | 0.5533 / 0.6429 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2023 | 1499 | 61.82 | 60.28 | 72.48 / 87.07 | -1.54 |
| E[games] (unconditional) | 2005–2023 | 1499 | 6.96 | 6.76 | 5.68 / 6.53 | -0.20 |
| E[season points | appears] | 2005–2023 | 988 | 93.79 | 93.15 | 80.62 / 91.55 | -0.64 |
| E[games | appears] | 2005–2023 | 988 | 10.55 | 10.41 | 4.82 / 5.09 | -0.15 |
| E[ppg | appears] | 2005–2023 | 988 | 7.36 | 7.48 | 5.03 / 5.75 | 0.12 |
| E[ppg | qualifies] (descriptive) | 2005–2023 | 382 | 13.10 | 13.05 | 3.92 / 4.19 | -0.05 |

Calibration of P(qualifies in season 3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 510 | 0.063 | 0.057 |
| 0.10-0.20 | 309 | 0.144 | 0.172 |
| 0.20-0.35 | 273 | 0.267 | 0.271 |
| 0.35-0.50 | 161 | 0.435 | 0.416 |
| 0.50-0.70 | 158 | 0.598 | 0.582 |
| 0.70-1.00 | 88 | 0.774 | 0.761 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 222 | 0.25 | 0.29 | 0.849 | 0.1201 / 0.1866 |
| RB | 400 | 0.29 | 0.24 | 0.798 | 0.1601 / 0.2074 |
| TE | 274 | 0.18 | 0.19 | 0.820 | 0.1132 / 0.1523 |
| WR | 603 | 0.27 | 0.28 | 0.787 | 0.1553 / 0.1967 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 0.69 | 0.70 |
| 2 | 193 | 0.45 | 0.48 |
| 3 | 217 | 0.31 | 0.30 |
| 4 | 231 | 0.19 | 0.19 |
| 5 | 199 | 0.15 | 0.12 |
| 6 | 230 | 0.09 | 0.08 |
| 7 | 244 | 0.03 | 0.05 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 222 | 58.46 | 59.73 | 79.75 / 103.03 | 1.27 |
| RB | 400 | 70.15 | 62.49 | 77.29 / 93.12 | -7.66 |
| TE | 274 | 48.00 | 46.94 | 52.73 / 61.62 | -1.06 |
| WR | 603 | 63.81 | 65.08 | 74.11 / 86.38 | 1.27 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 159.64 | 154.47 |
| 2 | 193 | 101.64 | 101.98 |
| 3 | 217 | 72.58 | 71.58 |
| 4 | 231 | 47.45 | 50.23 |
| 5 | 199 | 38.54 | 33.70 |
| 6 | 230 | 25.61 | 22.40 |
| 7 | 244 | 13.29 | 12.73 |

Training baseline for P(qualifies) by forecast year: 2005: 0.258, 2006: 0.258, 2007: 0.266, 2008: 0.257, 2009: 0.255, 2010: 0.255, 2011: 0.257, 2012: 0.252, 2013: 0.252, 2014: 0.253, 2015: 0.253, 2016: 0.248, 2017: 0.249, 2018: 0.249, 2019: 0.248, 2020: 0.251, 2021: 0.251, 2022: 0.253, 2023: 0.253

### season 4

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2022 | 1419 | 0.24 | 0.24 | 0.796 (0.772, 0.819) | 0.1385 / 0.1802 | 0.4366 / 0.5463 |
| P(appears in season j) | 2005–2022 | 1419 | 0.58 | 0.57 | 0.745 (0.723, 0.767) | 0.2006 / 0.2435 | 0.5873 / 0.6801 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2022 | 1419 | 56.51 | 54.42 | 72.06 / 83.64 | -2.09 |
| E[games] (unconditional) | 2005–2022 | 1419 | 6.29 | 6.09 | 5.80 / 6.56 | -0.20 |
| E[season points | appears] | 2005–2022 | 830 | 96.62 | 96.28 | 81.28 / 89.32 | -0.34 |
| E[games | appears] | 2005–2022 | 830 | 10.76 | 10.73 | 4.79 / 4.99 | -0.03 |
| E[ppg | appears] | 2005–2022 | 830 | 7.75 | 7.84 | 5.13 / 5.67 | 0.09 |
| E[ppg | qualifies] (descriptive) | 2005–2022 | 334 | 13.21 | 13.08 | 4.09 / 4.15 | -0.13 |

Calibration of P(qualifies in season 4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 404 | 0.069 | 0.057 |
| 0.10-0.20 | 435 | 0.141 | 0.136 |
| 0.20-0.35 | 269 | 0.260 | 0.253 |
| 0.35-0.50 | 144 | 0.422 | 0.458 |
| 0.50-0.70 | 97 | 0.585 | 0.670 |
| 0.70-1.00 | 70 | 0.816 | 0.757 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 208 | 0.27 | 0.30 | 0.808 | 0.1407 / 0.1992 |
| RB | 382 | 0.26 | 0.20 | 0.824 | 0.1465 / 0.1923 |
| TE | 259 | 0.17 | 0.18 | 0.782 | 0.1157 / 0.1493 |
| WR | 570 | 0.23 | 0.26 | 0.783 | 0.1426 / 0.1792 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 0.67 | 0.67 |
| 2 | 182 | 0.43 | 0.40 |
| 3 | 203 | 0.24 | 0.25 |
| 4 | 224 | 0.17 | 0.17 |
| 5 | 184 | 0.14 | 0.12 |
| 6 | 218 | 0.07 | 0.09 |
| 7 | 233 | 0.04 | 0.07 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 208 | 59.28 | 59.24 | 84.12 / 99.38 | -0.04 |
| RB | 382 | 62.08 | 55.41 | 76.35 / 88.07 | -6.67 |
| TE | 259 | 46.41 | 40.70 | 55.03 / 64.18 | -5.71 |
| WR | 570 | 56.37 | 58.24 | 71.15 / 82.11 | 1.87 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 144.77 | 140.89 |
| 2 | 182 | 98.91 | 87.90 |
| 3 | 203 | 63.36 | 60.27 |
| 4 | 224 | 45.06 | 44.25 |
| 5 | 184 | 33.09 | 31.57 |
| 6 | 218 | 19.83 | 22.89 |
| 7 | 233 | 14.97 | 15.55 |

Training baseline for P(qualifies) by forecast year: 2005: 0.272, 2006: 0.255, 2007: 0.247, 2008: 0.255, 2009: 0.261, 2010: 0.257, 2011: 0.253, 2012: 0.253, 2013: 0.250, 2014: 0.248, 2015: 0.241, 2016: 0.240, 2017: 0.239, 2018: 0.240, 2019: 0.237, 2020: 0.238, 2021: 0.240, 2022: 0.240

### season 5

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2021 | 1340 | 0.19 | 0.20 | 0.771 (0.743, 0.799) | 0.1308 / 0.1577 | 0.4166 / 0.4957 |
| P(appears in season j) | 2005–2021 | 1340 | 0.49 | 0.48 | 0.739 (0.717, 0.762) | 0.2074 / 0.2504 | 0.6030 / 0.6940 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2021 | 1340 | 48.61 | 47.89 | 72.20 / 82.36 | -0.72 |
| E[games] (unconditional) | 2005–2021 | 1340 | 5.24 | 5.04 | 5.81 / 6.44 | -0.20 |
| E[season points | appears] | 2005–2021 | 651 | 100.06 | 101.54 | 85.82 / 93.06 | 1.47 |
| E[games | appears] | 2005–2021 | 651 | 10.79 | 10.63 | 4.86 / 4.93 | -0.16 |
| E[ppg | appears] | 2005–2021 | 651 | 7.93 | 8.15 | 5.38 / 5.82 | 0.22 |
| E[ppg | qualifies] (descriptive) | 2005–2021 | 260 | 13.60 | 13.67 | 4.13 / 4.19 | 0.06 |

Calibration of P(qualifies in season 5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 415 | 0.071 | 0.055 |
| 0.10-0.20 | 444 | 0.142 | 0.126 |
| 0.20-0.35 | 287 | 0.261 | 0.282 |
| 0.35-0.50 | 113 | 0.415 | 0.434 |
| 0.50-0.70 | 51 | 0.587 | 0.588 |
| 0.70-1.00 | 30 | 0.796 | 0.700 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 199 | 0.24 | 0.26 | 0.852 | 0.1258 / 0.1810 |
| RB | 359 | 0.20 | 0.19 | 0.764 | 0.1358 / 0.1595 |
| TE | 240 | 0.14 | 0.15 | 0.776 | 0.0940 / 0.1258 |
| WR | 542 | 0.20 | 0.20 | 0.720 | 0.1457 / 0.1619 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 0.55 | 0.52 |
| 2 | 171 | 0.32 | 0.31 |
| 3 | 190 | 0.23 | 0.21 |
| 4 | 209 | 0.13 | 0.15 |
| 5 | 172 | 0.10 | 0.12 |
| 6 | 207 | 0.06 | 0.09 |
| 7 | 223 | 0.05 | 0.08 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 199 | 54.99 | 56.57 | 81.95 / 98.89 | 1.58 |
| RB | 359 | 49.24 | 49.47 | 71.04 / 81.00 | 0.24 |
| TE | 240 | 39.95 | 35.86 | 47.68 / 58.98 | -4.09 |
| WR | 542 | 49.70 | 48.99 | 77.94 / 85.41 | -0.70 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 129.35 | 127.28 |
| 2 | 171 | 80.61 | 77.81 |
| 3 | 190 | 58.40 | 52.49 |
| 4 | 209 | 34.10 | 37.72 |
| 5 | 172 | 27.25 | 26.94 |
| 6 | 207 | 18.75 | 19.28 |
| 7 | 223 | 12.71 | 13.48 |

Training baseline for P(qualifies) by forecast year: 2005: 0.255, 2006: 0.254, 2007: 0.238, 2008: 0.239, 2009: 0.237, 2010: 0.238, 2011: 0.230, 2012: 0.225, 2013: 0.222, 2014: 0.213, 2015: 0.208, 2016: 0.211, 2017: 0.211, 2018: 0.209, 2019: 0.207, 2020: 0.207, 2021: 0.205

### season 6

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2020 | 1265 | 0.17 | 0.19 | 0.765 (0.735, 0.794) | 0.1217 / 0.1431 | 0.3926 / 0.4616 |
| P(appears in season j) | 2005–2020 | 1265 | 0.40 | 0.42 | 0.719 (0.695, 0.744) | 0.2071 / 0.2418 | 0.6031 / 0.6768 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2020 | 1265 | 42.76 | 41.23 | 71.38 / 79.69 | -1.53 |
| E[games] (unconditional) | 2005–2020 | 1265 | 4.50 | 4.57 | 5.76 / 6.31 | 0.06 |
| E[season points | appears] | 2005–2020 | 508 | 106.47 | 104.63 | 91.24 / 94.37 | -1.85 |
| E[games | appears] | 2005–2020 | 508 | 11.21 | 11.17 | 4.83 / 4.85 | -0.04 |
| E[ppg | appears] | 2005–2020 | 508 | 8.25 | 8.08 | 5.49 / 5.75 | -0.17 |
| E[ppg | qualifies] (descriptive) | 2005–2020 | 217 | 13.53 | 13.12 | 4.27 / 4.16 | -0.41 |

Calibration of P(qualifies in season 6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 483 | 0.061 | 0.062 |
| 0.10-0.20 | 333 | 0.144 | 0.117 |
| 0.20-0.35 | 236 | 0.263 | 0.220 |
| 0.35-0.50 | 127 | 0.418 | 0.394 |
| 0.50-0.70 | 78 | 0.577 | 0.538 |
| 0.70-1.00 | 8 | 0.766 | 0.500 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 189 | 0.24 | 0.23 | 0.827 | 0.1369 / 0.1835 |
| RB | 340 | 0.17 | 0.20 | 0.738 | 0.1271 / 0.1429 |
| TE | 229 | 0.11 | 0.12 | 0.720 | 0.0981 / 0.1081 |
| WR | 507 | 0.17 | 0.21 | 0.764 | 0.1232 / 0.1441 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 0.50 | 0.48 |
| 2 | 163 | 0.33 | 0.34 |
| 3 | 179 | 0.16 | 0.21 |
| 4 | 197 | 0.14 | 0.15 |
| 5 | 164 | 0.06 | 0.11 |
| 6 | 193 | 0.05 | 0.08 |
| 7 | 214 | 0.05 | 0.06 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 189 | 52.89 | 52.11 | 87.73 / 97.94 | -0.77 |
| RB | 340 | 41.74 | 43.57 | 70.61 / 80.87 | 1.82 |
| TE | 229 | 34.21 | 28.34 | 50.94 / 57.17 | -5.86 |
| WR | 507 | 43.52 | 41.42 | 72.99 / 80.05 | -2.11 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 115.21 | 111.85 |
| 2 | 163 | 78.11 | 64.67 |
| 3 | 179 | 46.80 | 42.94 |
| 4 | 197 | 31.08 | 31.64 |
| 5 | 164 | 21.06 | 23.79 |
| 6 | 193 | 16.62 | 18.24 |
| 7 | 214 | 10.93 | 13.70 |

Training baseline for P(qualifies) by forecast year: 2005: 0.203, 2006: 0.200, 2007: 0.207, 2008: 0.212, 2009: 0.207, 2010: 0.208, 2011: 0.211, 2012: 0.205, 2013: 0.200, 2014: 0.199, 2015: 0.192, 2016: 0.187, 2017: 0.186, 2018: 0.183, 2019: 0.179, 2020: 0.179

## Cumulative quantities (window seasons 1..h)

### h = 1

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.840 (0.821, 0.859) | 0.1197 / 0.1708 | 0.3822 / 0.5255 |
| P(any appearance in 1..h) | 2005–2025 | 1662 | 0.78 | 0.76 | 0.794 (0.773, 0.813) | 0.1398 / 0.1721 | 0.4351 / 0.5282 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2025 | 1662 | 0.22 | 0.21 | 0.35 / 0.41 | -0.01 |

Calibration of P(any qualifying season in 1..1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 783 | 0.047 | 0.056 |
| 0.10-0.20 | 294 | 0.144 | 0.143 |
| 0.20-0.35 | 230 | 0.265 | 0.257 |
| 0.35-0.50 | 149 | 0.425 | 0.456 |
| 0.50-0.70 | 106 | 0.604 | 0.660 |
| 0.70-1.00 | 100 | 0.803 | 0.790 |

### h = 2

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2024 | 1576 | 0.32 | 0.31 | 0.828 (0.810, 0.845) | 0.1488 / 0.2183 | 0.4610 / 0.6284 |
| P(any appearance in 1..h) | 2005–2024 | 1576 | 0.86 | 0.84 | 0.806 (0.784, 0.828) | 0.1017 / 0.1192 | 0.3245 / 0.4027 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2024 | 1576 | 0.49 | 0.47 | 0.61 / 0.76 | -0.02 |

Calibration of P(any qualifying season in 1..2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 445 | 0.062 | 0.074 |
| 0.10-0.20 | 318 | 0.144 | 0.167 |
| 0.20-0.35 | 268 | 0.269 | 0.280 |
| 0.35-0.50 | 163 | 0.415 | 0.417 |
| 0.50-0.70 | 170 | 0.595 | 0.582 |
| 0.70-1.00 | 212 | 0.858 | 0.840 |

### h = 3

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2023 | 1499 | 0.36 | 0.36 | 0.823 (0.804, 0.842) | 0.1584 / 0.2312 | 0.4868 / 0.6550 |
| P(any appearance in 1..h) | 2005–2023 | 1499 | 0.88 | 0.86 | 0.779 (0.755, 0.803) | 0.0963 / 0.1078 | 0.3137 / 0.3740 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2023 | 1499 | 0.74 | 0.72 | 0.86 / 1.09 | -0.02 |

Calibration of P(any qualifying season in 1..3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 241 | 0.075 | 0.066 |
| 0.10-0.20 | 364 | 0.142 | 0.154 |
| 0.20-0.35 | 274 | 0.268 | 0.252 |
| 0.35-0.50 | 196 | 0.416 | 0.439 |
| 0.50-0.70 | 189 | 0.612 | 0.614 |
| 0.70-1.00 | 235 | 0.873 | 0.851 |

### h = 4

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2022 | 1419 | 0.39 | 0.40 | 0.815 (0.795, 0.833) | 0.1665 / 0.2386 | 0.5069 / 0.6702 |
| P(any appearance in 1..h) | 2005–2022 | 1419 | 0.88 | 0.87 | 0.776 (0.751, 0.803) | 0.0966 / 0.1080 | 0.3140 / 0.3752 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2022 | 1419 | 0.96 | 0.95 | 1.09 / 1.40 | -0.02 |

Calibration of P(any qualifying season in 1..4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 60 | 0.078 | 0.033 |
| 0.10-0.20 | 409 | 0.148 | 0.142 |
| 0.20-0.35 | 298 | 0.271 | 0.272 |
| 0.35-0.50 | 223 | 0.423 | 0.417 |
| 0.50-0.70 | 178 | 0.613 | 0.607 |
| 0.70-1.00 | 251 | 0.867 | 0.857 |

### h = 5

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2021 | 1340 | 0.41 | 0.43 | 0.816 (0.796, 0.836) | 0.1679 / 0.2419 | 0.5112 / 0.6768 |
| P(any appearance in 1..h) | 2005–2021 | 1340 | 0.87 | 0.87 | 0.776 (0.750, 0.800) | 0.0986 / 0.1108 | 0.3193 / 0.3832 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2021 | 1340 | 1.15 | 1.15 | 1.30 / 1.67 | -0.00 |

Calibration of P(any qualifying season in 1..5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 21 | 0.089 | 0.000 |
| 0.10-0.20 | 333 | 0.158 | 0.123 |
| 0.20-0.35 | 318 | 0.267 | 0.267 |
| 0.35-0.50 | 232 | 0.424 | 0.397 |
| 0.50-0.70 | 164 | 0.609 | 0.598 |
| 0.70-1.00 | 272 | 0.862 | 0.846 |

### h = 6

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2020 | 1265 | 0.42 | 0.44 | 0.816 (0.795, 0.836) | 0.1692 / 0.2442 | 0.5117 / 0.6815 |
| P(any appearance in 1..h) | 2005–2020 | 1265 | 0.87 | 0.87 | 0.772 (0.748, 0.798) | 0.1019 / 0.1152 | 0.3281 / 0.3985 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2020 | 1265 | 1.32 | 1.33 | 1.52 / 1.94 | 0.01 |

Calibration of P(any qualifying season in 1..6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 15 | 0.088 | 0.000 |
| 0.10-0.20 | 282 | 0.157 | 0.128 |
| 0.20-0.35 | 315 | 0.265 | 0.263 |
| 0.35-0.50 | 222 | 0.427 | 0.378 |
| 0.50-0.70 | 151 | 0.597 | 0.616 |
| 0.70-1.00 | 280 | 0.860 | 0.832 |

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
