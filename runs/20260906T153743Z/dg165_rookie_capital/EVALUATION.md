# DG-165 rookie draft-capital candidate — historical evaluation with information cutoffs

One fit per forecast year T on labels completed by T−1 (the same procedure as final scoring); class T
graded against what happened afterwards, each quantity only where its own label is complete today.
"Training baseline" = the prevalence / mean of that label in the training set at T, carried per row.

## Per-season quantities (season j = 1 is the rookie season)

### season 1

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.841 (0.819, 0.859) | 0.1196 / 0.1708 | 0.3822 / 0.5255 |
| P(appears in season j) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.793 (0.772, 0.814) | 0.1403 / 0.1721 | 0.4364 / 0.5282 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2025 | 1662 | 53.25 | 50.22 | 53.89 / 70.82 | -3.03 |
| E[games] (unconditional) | 2005–2025 | 1662 | 7.65 | 7.18 | 4.83 / 6.05 | -0.47 |
| E[season points | appears] | 2005–2025 | 1296 | 68.29 | 66.59 | 57.73 / 72.59 | -1.70 |
| E[games | appears] | 2005–2025 | 1296 | 9.81 | 9.55 | 4.32 / 4.98 | -0.26 |
| E[ppg | appears] | 2005–2025 | 1296 | 5.69 | 5.64 | 3.89 / 4.72 | -0.05 |
| E[ppg | qualifies] (descriptive) | 2005–2025 | 362 | 11.64 | 11.76 | 3.39 / 3.64 | 0.12 |

Calibration of P(qualifies in season 1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 787 | 0.045 | 0.057 |
| 0.10-0.20 | 296 | 0.144 | 0.155 |
| 0.20-0.35 | 225 | 0.264 | 0.244 |
| 0.35-0.50 | 152 | 0.418 | 0.454 |
| 0.50-0.70 | 109 | 0.604 | 0.688 |
| 0.70-1.00 | 93 | 0.810 | 0.774 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 247 | 0.30 | 0.26 | 0.890 | 0.1189 / 0.2218 |
| RB | 444 | 0.25 | 0.25 | 0.806 | 0.1377 / 0.1937 |
| TE | 302 | 0.10 | 0.11 | 0.847 | 0.0691 / 0.0950 |
| WR | 669 | 0.22 | 0.20 | 0.820 | 0.1308 / 0.1710 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 0.70 | 0.67 |
| 2 | 210 | 0.40 | 0.37 |
| 3 | 236 | 0.21 | 0.22 |
| 4 | 261 | 0.16 | 0.14 |
| 5 | 220 | 0.10 | 0.08 |
| 6 | 257 | 0.04 | 0.05 |
| 7 | 269 | 0.03 | 0.02 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 247 | 56.68 | 45.68 | 63.32 / 87.39 | -11.01 |
| RB | 444 | 64.24 | 61.08 | 59.84 / 79.93 | -3.16 |
| TE | 302 | 34.56 | 35.66 | 35.20 / 45.48 | 1.10 |
| WR | 669 | 53.13 | 51.27 | 52.89 / 66.82 | -1.86 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 209 | 145.17 | 124.55 |
| 2 | 210 | 89.59 | 79.25 |
| 3 | 236 | 57.53 | 57.25 |
| 4 | 261 | 44.09 | 43.96 |
| 5 | 220 | 30.72 | 30.53 |
| 6 | 257 | 17.86 | 21.60 |
| 7 | 269 | 10.85 | 13.17 |

Training baseline for P(qualifies) by forecast year: 2005: 0.180, 2006: 0.178, 2007: 0.181, 2008: 0.173, 2009: 0.172, 2010: 0.176, 2011: 0.177, 2012: 0.177, 2013: 0.180, 2014: 0.184, 2015: 0.187, 2016: 0.189, 2017: 0.189, 2018: 0.192, 2019: 0.195, 2020: 0.197, 2021: 0.199, 2022: 0.202, 2023: 0.203, 2024: 0.206, 2025: 0.207

### season 2

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2024 | 1576 | 0.27 | 0.26 | 0.818 (0.798, 0.836) | 0.1420 / 0.1984 | 0.4458 / 0.5863 |
| P(appears in season j) | 2005–2024 | 1576 | 0.76 | 0.74 | 0.776 (0.756, 0.796) | 0.1523 / 0.1843 | 0.4600 / 0.5555 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2024 | 1576 | 66.15 | 63.94 | 67.58 / 84.68 | -2.20 |
| E[games] (unconditional) | 2005–2024 | 1576 | 7.88 | 7.54 | 5.37 / 6.33 | -0.33 |
| E[season points | appears] | 2005–2024 | 1194 | 87.31 | 86.70 | 73.33 / 85.78 | -0.61 |
| E[games | appears] | 2005–2024 | 1194 | 10.40 | 10.20 | 4.75 / 5.15 | -0.20 |
| E[ppg | appears] | 2005–2024 | 1194 | 6.93 | 6.97 | 4.57 / 5.36 | 0.04 |
| E[ppg | qualifies] (descriptive) | 2005–2024 | 429 | 12.66 | 12.83 | 3.92 / 4.02 | 0.17 |

Calibration of P(qualifies in season 2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 578 | 0.052 | 0.067 |
| 0.10-0.20 | 287 | 0.148 | 0.171 |
| 0.20-0.35 | 254 | 0.264 | 0.260 |
| 0.35-0.50 | 161 | 0.424 | 0.478 |
| 0.50-0.70 | 158 | 0.593 | 0.551 |
| 0.70-1.00 | 138 | 0.813 | 0.804 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 233 | 0.35 | 0.34 | 0.888 | 0.1186 / 0.2375 |
| RB | 419 | 0.30 | 0.27 | 0.820 | 0.1461 / 0.2104 |
| TE | 286 | 0.18 | 0.19 | 0.819 | 0.1100 / 0.1521 |
| WR | 638 | 0.27 | 0.26 | 0.768 | 0.1622 / 0.1971 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 0.76 | 0.76 |
| 2 | 199 | 0.47 | 0.50 |
| 3 | 226 | 0.35 | 0.31 |
| 4 | 247 | 0.15 | 0.19 |
| 5 | 210 | 0.16 | 0.11 |
| 6 | 244 | 0.09 | 0.06 |
| 7 | 251 | 0.04 | 0.03 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 233 | 77.38 | 68.95 | 79.36 / 109.71 | -8.43 |
| RB | 419 | 73.56 | 70.99 | 74.70 / 92.37 | -2.57 |
| TE | 286 | 45.07 | 46.41 | 49.40 / 59.22 | 1.33 |
| WR | 638 | 66.63 | 65.35 | 64.98 / 78.37 | -1.28 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 199 | 167.52 | 160.13 |
| 2 | 199 | 108.94 | 103.76 |
| 3 | 226 | 82.30 | 74.13 |
| 4 | 247 | 45.69 | 55.05 |
| 5 | 210 | 42.41 | 37.96 |
| 6 | 244 | 24.87 | 25.98 |
| 7 | 251 | 17.42 | 14.33 |

Training baseline for P(qualifies) by forecast year: 2005: 0.250, 2006: 0.246, 2007: 0.247, 2008: 0.250, 2009: 0.243, 2010: 0.248, 2011: 0.248, 2012: 0.254, 2013: 0.256, 2014: 0.254, 2015: 0.251, 2016: 0.253, 2017: 0.251, 2018: 0.248, 2019: 0.254, 2020: 0.257, 2021: 0.258, 2022: 0.260, 2023: 0.259, 2024: 0.261

### season 3

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2023 | 1499 | 0.25 | 0.25 | 0.806 (0.785, 0.829) | 0.1438 / 0.1900 | 0.4469 / 0.5678 |
| P(appears in season j) | 2005–2023 | 1499 | 0.66 | 0.65 | 0.742 (0.721, 0.764) | 0.1898 / 0.2253 | 0.5565 / 0.6429 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2023 | 1499 | 61.82 | 59.87 | 72.61 / 87.07 | -1.94 |
| E[games] (unconditional) | 2005–2023 | 1499 | 6.96 | 6.68 | 5.71 / 6.53 | -0.28 |
| E[season points | appears] | 2005–2023 | 988 | 93.79 | 92.90 | 80.72 / 91.55 | -0.89 |
| E[games | appears] | 2005–2023 | 988 | 10.55 | 10.32 | 4.84 / 5.09 | -0.23 |
| E[ppg | appears] | 2005–2023 | 988 | 7.36 | 7.48 | 5.03 / 5.75 | 0.12 |
| E[ppg | qualifies] (descriptive) | 2005–2023 | 382 | 13.10 | 13.02 | 3.93 / 4.19 | -0.08 |

Calibration of P(qualifies in season 3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 506 | 0.060 | 0.051 |
| 0.10-0.20 | 303 | 0.143 | 0.182 |
| 0.20-0.35 | 270 | 0.266 | 0.248 |
| 0.35-0.50 | 172 | 0.427 | 0.442 |
| 0.50-0.70 | 162 | 0.596 | 0.574 |
| 0.70-1.00 | 86 | 0.770 | 0.756 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 222 | 0.25 | 0.28 | 0.849 | 0.1199 / 0.1866 |
| RB | 400 | 0.29 | 0.24 | 0.796 | 0.1612 / 0.2074 |
| TE | 274 | 0.18 | 0.19 | 0.823 | 0.1126 / 0.1523 |
| WR | 603 | 0.27 | 0.29 | 0.788 | 0.1552 / 0.1967 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 0.69 | 0.69 |
| 2 | 193 | 0.45 | 0.47 |
| 3 | 217 | 0.31 | 0.30 |
| 4 | 231 | 0.19 | 0.19 |
| 5 | 199 | 0.15 | 0.12 |
| 6 | 230 | 0.09 | 0.08 |
| 7 | 244 | 0.03 | 0.05 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 222 | 58.46 | 59.31 | 80.23 / 103.03 | 0.85 |
| RB | 400 | 70.15 | 62.23 | 77.25 / 93.12 | -7.92 |
| TE | 274 | 48.00 | 46.23 | 53.01 / 61.62 | -1.76 |
| WR | 603 | 63.81 | 64.71 | 74.17 / 86.38 | 0.91 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 185 | 159.64 | 154.13 |
| 2 | 193 | 101.64 | 102.45 |
| 3 | 217 | 72.58 | 71.00 |
| 4 | 231 | 47.45 | 49.29 |
| 5 | 199 | 38.54 | 32.93 |
| 6 | 230 | 25.61 | 21.86 |
| 7 | 244 | 13.29 | 12.67 |

Training baseline for P(qualifies) by forecast year: 2005: 0.258, 2006: 0.258, 2007: 0.266, 2008: 0.257, 2009: 0.255, 2010: 0.255, 2011: 0.257, 2012: 0.252, 2013: 0.252, 2014: 0.253, 2015: 0.253, 2016: 0.248, 2017: 0.249, 2018: 0.249, 2019: 0.248, 2020: 0.251, 2021: 0.251, 2022: 0.253, 2023: 0.253

### season 4

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2022 | 1419 | 0.24 | 0.23 | 0.796 (0.773, 0.819) | 0.1388 / 0.1802 | 0.4367 / 0.5463 |
| P(appears in season j) | 2005–2022 | 1419 | 0.58 | 0.57 | 0.741 (0.718, 0.763) | 0.2024 / 0.2435 | 0.5927 / 0.6801 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2022 | 1419 | 56.51 | 54.29 | 72.15 / 83.64 | -2.22 |
| E[games] (unconditional) | 2005–2022 | 1419 | 6.29 | 6.10 | 5.82 / 6.56 | -0.19 |
| E[season points | appears] | 2005–2022 | 830 | 96.62 | 96.43 | 81.25 / 89.32 | -0.19 |
| E[games | appears] | 2005–2022 | 830 | 10.76 | 10.77 | 4.79 / 4.99 | 0.01 |
| E[ppg | appears] | 2005–2022 | 830 | 7.75 | 7.87 | 5.12 / 5.67 | 0.12 |
| E[ppg | qualifies] (descriptive) | 2005–2022 | 334 | 13.21 | 13.06 | 4.10 / 4.15 | -0.14 |

Calibration of P(qualifies in season 4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 437 | 0.068 | 0.062 |
| 0.10-0.20 | 404 | 0.144 | 0.146 |
| 0.20-0.35 | 272 | 0.265 | 0.257 |
| 0.35-0.50 | 134 | 0.424 | 0.440 |
| 0.50-0.70 | 102 | 0.587 | 0.647 |
| 0.70-1.00 | 70 | 0.803 | 0.757 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 208 | 0.27 | 0.29 | 0.810 | 0.1436 / 0.1992 |
| RB | 382 | 0.26 | 0.20 | 0.822 | 0.1471 / 0.1923 |
| TE | 259 | 0.17 | 0.18 | 0.783 | 0.1156 / 0.1493 |
| WR | 570 | 0.23 | 0.26 | 0.785 | 0.1420 / 0.1792 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 0.67 | 0.66 |
| 2 | 182 | 0.43 | 0.40 |
| 3 | 203 | 0.24 | 0.25 |
| 4 | 224 | 0.17 | 0.17 |
| 5 | 184 | 0.14 | 0.12 |
| 6 | 218 | 0.07 | 0.09 |
| 7 | 233 | 0.04 | 0.06 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 208 | 59.28 | 57.71 | 84.95 / 99.38 | -1.57 |
| RB | 382 | 62.08 | 54.67 | 76.26 / 88.07 | -7.41 |
| TE | 259 | 46.41 | 40.67 | 55.07 / 64.18 | -5.74 |
| WR | 570 | 56.37 | 58.99 | 71.07 / 82.11 | 2.62 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 175 | 144.77 | 140.04 |
| 2 | 182 | 98.91 | 88.83 |
| 3 | 203 | 63.36 | 60.14 |
| 4 | 224 | 45.06 | 43.67 |
| 5 | 184 | 33.09 | 31.09 |
| 6 | 218 | 19.83 | 22.84 |
| 7 | 233 | 14.97 | 15.79 |

Training baseline for P(qualifies) by forecast year: 2005: 0.272, 2006: 0.255, 2007: 0.247, 2008: 0.255, 2009: 0.261, 2010: 0.257, 2011: 0.253, 2012: 0.253, 2013: 0.250, 2014: 0.248, 2015: 0.241, 2016: 0.240, 2017: 0.239, 2018: 0.240, 2019: 0.237, 2020: 0.238, 2021: 0.240, 2022: 0.240

### season 5

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2021 | 1340 | 0.19 | 0.20 | 0.772 (0.745, 0.800) | 0.1306 / 0.1577 | 0.4151 / 0.4957 |
| P(appears in season j) | 2005–2021 | 1340 | 0.49 | 0.48 | 0.733 (0.711, 0.756) | 0.2096 / 0.2504 | 0.6104 / 0.6940 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2021 | 1340 | 48.61 | 47.85 | 72.31 / 82.36 | -0.77 |
| E[games] (unconditional) | 2005–2021 | 1340 | 5.24 | 5.11 | 5.83 / 6.44 | -0.13 |
| E[season points | appears] | 2005–2021 | 651 | 100.06 | 100.62 | 85.99 / 93.06 | 0.56 |
| E[games | appears] | 2005–2021 | 651 | 10.79 | 10.60 | 4.85 / 4.93 | -0.19 |
| E[ppg | appears] | 2005–2021 | 651 | 7.93 | 8.09 | 5.40 / 5.82 | 0.16 |
| E[ppg | qualifies] (descriptive) | 2005–2021 | 260 | 13.60 | 13.68 | 4.11 / 4.19 | 0.08 |

Calibration of P(qualifies in season 5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 449 | 0.068 | 0.051 |
| 0.10-0.20 | 420 | 0.142 | 0.133 |
| 0.20-0.35 | 282 | 0.261 | 0.298 |
| 0.35-0.50 | 104 | 0.416 | 0.433 |
| 0.50-0.70 | 57 | 0.583 | 0.579 |
| 0.70-1.00 | 28 | 0.785 | 0.679 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 199 | 0.24 | 0.26 | 0.850 | 0.1260 / 0.1810 |
| RB | 359 | 0.20 | 0.18 | 0.771 | 0.1344 / 0.1595 |
| TE | 240 | 0.14 | 0.14 | 0.779 | 0.0951 / 0.1258 |
| WR | 542 | 0.20 | 0.20 | 0.720 | 0.1456 / 0.1619 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 0.55 | 0.52 |
| 2 | 171 | 0.32 | 0.30 |
| 3 | 190 | 0.23 | 0.20 |
| 4 | 209 | 0.13 | 0.15 |
| 5 | 172 | 0.10 | 0.11 |
| 6 | 207 | 0.06 | 0.09 |
| 7 | 223 | 0.05 | 0.07 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 199 | 54.99 | 54.87 | 82.15 / 98.89 | -0.12 |
| RB | 359 | 49.24 | 49.23 | 71.15 / 81.00 | -0.00 |
| TE | 240 | 39.95 | 35.63 | 48.12 / 58.98 | -4.32 |
| WR | 542 | 49.70 | 49.76 | 77.92 / 85.41 | 0.06 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 168 | 129.35 | 125.31 |
| 2 | 171 | 80.61 | 77.88 |
| 3 | 190 | 58.40 | 52.60 |
| 4 | 209 | 34.10 | 37.94 |
| 5 | 172 | 27.25 | 27.33 |
| 6 | 207 | 18.75 | 19.70 |
| 7 | 223 | 12.71 | 13.67 |

Training baseline for P(qualifies) by forecast year: 2005: 0.255, 2006: 0.254, 2007: 0.238, 2008: 0.239, 2009: 0.237, 2010: 0.238, 2011: 0.230, 2012: 0.225, 2013: 0.222, 2014: 0.213, 2015: 0.208, 2016: 0.211, 2017: 0.211, 2018: 0.209, 2019: 0.207, 2020: 0.207, 2021: 0.205

### season 6

Probabilities:

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(qualifies in season j) | 2005–2020 | 1265 | 0.17 | 0.18 | 0.767 (0.737, 0.796) | 0.1209 / 0.1431 | 0.3903 / 0.4616 |
| P(appears in season j) | 2005–2020 | 1265 | 0.40 | 0.42 | 0.722 (0.697, 0.746) | 0.2067 / 0.2418 | 0.6023 / 0.6768 |

Levels:

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[season points] (unconditional; 0 without appearance) | 2005–2020 | 1265 | 42.76 | 41.67 | 71.70 / 79.69 | -1.09 |
| E[games] (unconditional) | 2005–2020 | 1265 | 4.50 | 4.62 | 5.79 / 6.31 | 0.12 |
| E[season points | appears] | 2005–2020 | 508 | 106.47 | 104.45 | 91.31 / 94.37 | -2.02 |
| E[games | appears] | 2005–2020 | 508 | 11.21 | 11.16 | 4.84 / 4.85 | -0.05 |
| E[ppg | appears] | 2005–2020 | 508 | 8.25 | 8.07 | 5.49 / 5.75 | -0.19 |
| E[ppg | qualifies] (descriptive) | 2005–2020 | 217 | 13.53 | 13.05 | 4.33 / 4.16 | -0.48 |

Calibration of P(qualifies in season 6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 496 | 0.059 | 0.062 |
| 0.10-0.20 | 336 | 0.141 | 0.119 |
| 0.20-0.35 | 229 | 0.262 | 0.231 |
| 0.35-0.50 | 140 | 0.419 | 0.414 |
| 0.50-0.70 | 61 | 0.579 | 0.557 |
| 0.70-1.00 | 3 | 0.729 | 0.333 |

P(qualifies in season j) — slices:

by position:

| position | n | prevalence | mean predicted | AUC | Brier model / baseline |
|---|---:|---:|---:|---:|---|
| QB | 189 | 0.24 | 0.22 | 0.808 | 0.1405 / 0.1835 |
| RB | 340 | 0.17 | 0.19 | 0.740 | 0.1251 / 0.1429 |
| TE | 229 | 0.11 | 0.11 | 0.736 | 0.0941 / 0.1081 |
| WR | 507 | 0.17 | 0.20 | 0.764 | 0.1230 / 0.1441 |

by round:

| round | n | actual rate | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 0.50 | 0.46 |
| 2 | 163 | 0.33 | 0.32 |
| 3 | 179 | 0.16 | 0.21 |
| 4 | 197 | 0.14 | 0.14 |
| 5 | 164 | 0.06 | 0.10 |
| 6 | 193 | 0.05 | 0.08 |
| 7 | 214 | 0.05 | 0.05 |

E[season points] (unconditional; 0 without appearance) — slices:

by position:

| position | n | mean actual | mean predicted | RMSE model / baseline | bias |
|---|---:|---:|---:|---|---:|
| QB | 189 | 52.89 | 52.29 | 88.36 / 97.94 | -0.59 |
| RB | 340 | 41.74 | 43.99 | 71.28 / 80.87 | 2.24 |
| TE | 229 | 34.21 | 28.51 | 51.06 / 57.17 | -5.69 |
| WR | 507 | 43.52 | 42.09 | 73.01 / 80.05 | -1.43 |

by round:

| round | n | mean actual | mean predicted |
|---|---:|---:|---:|
| 1 | 155 | 115.21 | 111.07 |
| 2 | 163 | 78.11 | 65.87 |
| 3 | 179 | 46.80 | 44.06 |
| 4 | 197 | 31.08 | 32.62 |
| 5 | 164 | 21.06 | 24.42 |
| 6 | 193 | 16.62 | 18.30 |
| 7 | 214 | 10.93 | 13.58 |

Training baseline for P(qualifies) by forecast year: 2005: 0.203, 2006: 0.200, 2007: 0.207, 2008: 0.212, 2009: 0.207, 2010: 0.208, 2011: 0.211, 2012: 0.205, 2013: 0.200, 2014: 0.199, 2015: 0.192, 2016: 0.187, 2017: 0.186, 2018: 0.183, 2019: 0.179, 2020: 0.179

## Cumulative quantities (window seasons 1..h)

### h = 1

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2025 | 1662 | 0.22 | 0.21 | 0.841 (0.822, 0.859) | 0.1196 / 0.1708 | 0.3822 / 0.5255 |
| P(any appearance in 1..h) | 2005–2025 | 1662 | 0.78 | 0.75 | 0.793 (0.772, 0.812) | 0.1403 / 0.1721 | 0.4364 / 0.5282 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2025 | 1662 | 0.22 | 0.21 | 0.35 / 0.41 | -0.01 |

Calibration of P(any qualifying season in 1..1):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 787 | 0.045 | 0.057 |
| 0.10-0.20 | 296 | 0.144 | 0.155 |
| 0.20-0.35 | 225 | 0.264 | 0.244 |
| 0.35-0.50 | 152 | 0.418 | 0.454 |
| 0.50-0.70 | 109 | 0.604 | 0.688 |
| 0.70-1.00 | 93 | 0.810 | 0.774 |

### h = 2

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2024 | 1576 | 0.32 | 0.31 | 0.829 (0.811, 0.846) | 0.1486 / 0.2183 | 0.4608 / 0.6284 |
| P(any appearance in 1..h) | 2005–2024 | 1576 | 0.86 | 0.84 | 0.804 (0.782, 0.826) | 0.1021 / 0.1192 | 0.3258 / 0.4027 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2024 | 1576 | 0.49 | 0.47 | 0.61 / 0.76 | -0.02 |

Calibration of P(any qualifying season in 1..2):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 455 | 0.058 | 0.070 |
| 0.10-0.20 | 309 | 0.146 | 0.175 |
| 0.20-0.35 | 271 | 0.271 | 0.280 |
| 0.35-0.50 | 157 | 0.416 | 0.420 |
| 0.50-0.70 | 174 | 0.588 | 0.580 |
| 0.70-1.00 | 210 | 0.851 | 0.843 |

### h = 3

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2023 | 1499 | 0.36 | 0.36 | 0.825 (0.806, 0.844) | 0.1576 / 0.2312 | 0.4848 / 0.6550 |
| P(any appearance in 1..h) | 2005–2023 | 1499 | 0.88 | 0.86 | 0.776 (0.752, 0.801) | 0.0968 / 0.1078 | 0.3150 / 0.3740 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2023 | 1499 | 0.74 | 0.71 | 0.86 / 1.09 | -0.03 |

Calibration of P(any qualifying season in 1..3):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 268 | 0.073 | 0.067 |
| 0.10-0.20 | 328 | 0.142 | 0.165 |
| 0.20-0.35 | 277 | 0.268 | 0.242 |
| 0.35-0.50 | 196 | 0.417 | 0.439 |
| 0.50-0.70 | 196 | 0.609 | 0.602 |
| 0.70-1.00 | 234 | 0.868 | 0.855 |

### h = 4

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2022 | 1419 | 0.39 | 0.40 | 0.817 (0.797, 0.835) | 0.1658 / 0.2386 | 0.5052 / 0.6702 |
| P(any appearance in 1..h) | 2005–2022 | 1419 | 0.88 | 0.86 | 0.773 (0.748, 0.799) | 0.0971 / 0.1080 | 0.3155 / 0.3752 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2022 | 1419 | 0.96 | 0.94 | 1.09 / 1.40 | -0.02 |

Calibration of P(any qualifying season in 1..4):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 81 | 0.077 | 0.074 |
| 0.10-0.20 | 399 | 0.144 | 0.135 |
| 0.20-0.35 | 279 | 0.272 | 0.280 |
| 0.35-0.50 | 224 | 0.424 | 0.406 |
| 0.50-0.70 | 186 | 0.610 | 0.624 |
| 0.70-1.00 | 250 | 0.862 | 0.848 |

### h = 5

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2021 | 1340 | 0.41 | 0.42 | 0.816 (0.796, 0.836) | 0.1677 / 0.2419 | 0.5106 / 0.6768 |
| P(any appearance in 1..h) | 2005–2021 | 1340 | 0.87 | 0.87 | 0.772 (0.747, 0.797) | 0.0991 / 0.1108 | 0.3208 / 0.3832 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2021 | 1340 | 1.15 | 1.14 | 1.30 / 1.67 | -0.01 |

Calibration of P(any qualifying season in 1..5):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 41 | 0.087 | 0.024 |
| 0.10-0.20 | 338 | 0.153 | 0.145 |
| 0.20-0.35 | 291 | 0.266 | 0.254 |
| 0.35-0.50 | 221 | 0.422 | 0.389 |
| 0.50-0.70 | 176 | 0.598 | 0.614 |
| 0.70-1.00 | 273 | 0.857 | 0.835 |

### h = 6

| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | Brier model / training baseline | log loss model / baseline |
|---|---|---:|---:|---:|---|---|---|
| P(any qualifying season in 1..h) | 2005–2020 | 1265 | 0.42 | 0.43 | 0.818 (0.797, 0.838) | 0.1682 / 0.2442 | 0.5097 / 0.6815 |
| P(any appearance in 1..h) | 2005–2020 | 1265 | 0.87 | 0.86 | 0.769 (0.744, 0.794) | 0.1024 / 0.1152 | 0.3297 / 0.3985 |

| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |
|---|---|---:|---:|---:|---|---:|
| E[qualifying seasons in 1..h] | 2005–2020 | 1265 | 1.32 | 1.31 | 1.52 / 1.94 | -0.01 |

Calibration of P(any qualifying season in 1..6):

| predicted bin | n | mean predicted | actual |
|---|---:|---:|---:|
| 0.00-0.10 | 29 | 0.087 | 0.034 |
| 0.10-0.20 | 297 | 0.153 | 0.141 |
| 0.20-0.35 | 288 | 0.265 | 0.253 |
| 0.35-0.50 | 213 | 0.424 | 0.371 |
| 0.50-0.70 | 163 | 0.592 | 0.650 |
| 0.70-1.00 | 275 | 0.854 | 0.829 |

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
| 2005 | 1999–2004 | 482 | 77 | a_4|s0, a_5|s0, a_6|s0, ppg_6|Q, q_3|s0, q_4|s0, q_5|s0, q_6|s0, q_6|s1 |
| 2006 | 1999–2005 | 559 | 74 | a_5|s0, a_6|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0, q_6|s1 |
| 2007 | 1999–2006 | 633 | 80 | a_6|s0, q_3|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2008 | 1999–2007 | 713 | 87 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2009 | 1999–2008 | 800 | 87 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2010 | 1999–2009 | 887 | 78 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2011 | 1999–2010 | 965 | 82 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2012 | 1999–2011 | 1047 | 77 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2013 | 1999–2012 | 1124 | 80 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2014 | 1999–2013 | 1204 | 77 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2015 | 1999–2014 | 1281 | 79 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2016 | 1999–2015 | 1360 | 77 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2017 | 1999–2016 | 1437 | 83 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2018 | 1999–2017 | 1520 | 83 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2019 | 1999–2018 | 1603 | 80 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2020 | 1999–2019 | 1683 | 78 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2021 | 1999–2020 | 1761 | 75 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2022 | 1999–2021 | 1836 | 79 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2023 | 1999–2022 | 1915 | 80 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2024 | 1999–2023 | 1995 | 77 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
| 2025 | 1999–2024 | 2072 | 86 | a_6|s0, q_4|s0, q_5|s0, q_6|s0 |
