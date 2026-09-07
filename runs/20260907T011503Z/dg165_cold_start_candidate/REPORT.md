# DG-165 cold-start candidate — drafted players with no rookie-year regular-season record

Population caveat: a draft-population prior for drafted players with no rookie-year regular-season record; not conditioned on remaining on a current roster; direction and size of this mismatch have not been measured.
Selection caveat: selecting a policy on this historical evaluation is retrospective model selection, NOT independent confirmation of the selected policy; both arms are reported at every horizon.
Appearance: P(appear) is the probability of at least one championship-window stat row; it is not a breakout or usefulness probability.

Selection rule: per horizon, on the same paired supported rows: the candidate is selected only if BOTH the paired Brier(appear) difference and the paired RMSE(unconditional points) difference vs B1 have 90% player-cluster bootstrap intervals entirely below zero; otherwise B1's estimate is a baseline_research_candidate with its measured out-of-time error and support; a horizon whose arms are unsupported at the final origin is unsupported

## Per horizon (career years 2–6)

### Horizon 1

Paired supported rows: 210 of 210 test rows (excluded as unsupported: 0).

| arm | n | Brier(appear) | RMSE points | MAE points | bias points |
|---|---|---|---|---|---|
| candidate | 210 | 0.2293 | 24.50 | 12.72 | -2.40 |
| b1 | 210 | 0.2474 | 28.19 | 14.99 | -1.93 |
| b2 | 210 | 0.2323 | 24.52 | 12.69 | -2.61 |

Candidate − B1, 90% player-cluster intervals: Brier -0.0181 [-0.0309, -0.0039]; RMSE points -3.69 [-6.54, -0.53] (RMSE units).
**Selection at this horizon: cold_start_candidate** (both arms reported; this is retrospective model selection).

| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| QB | 57 | 0.1984 | 0.2245 | 17.05 | 21.79 |
| RB | 42 | 0.2347 | 0.2558 | 32.31 | 41.30 |
| TE | 37 | 0.2425 | 0.2698 | 26.83 | 28.48 |
| WR | 74 | 0.2434 | 0.2490 | 22.96 | 22.70 |

| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| 2012 | 15 | 0.2156 | 0.2649 | 37.02 | 42.91 |
| 2013 | 15 | 0.2072 | 0.2311 | 10.87 | 10.82 |
| 2014 | 22 | 0.2108 | 0.2218 | 40.07 | 41.36 |
| 2015 | 16 | 0.1849 | 0.1991 | 17.51 | 17.36 |
| 2016 | 18 | 0.2776 | 0.3294 | 22.18 | 24.26 |
| 2017 | 19 | 0.1776 | 0.1697 | 9.52 | 11.59 |
| 2018 | 20 | 0.2862 | 0.2640 | 23.49 | 22.77 |
| 2019 | 20 | 0.2418 | 0.2678 | 23.56 | 26.56 |
| 2020 | 16 | 0.2479 | 0.2376 | 12.57 | 10.35 |
| 2021 | 11 | 0.2595 | 0.3236 | 19.70 | 15.11 |
| 2022 | 7 | 0.1690 | 0.2066 | 49.08 | 70.08 |
| 2023 | 8 | 0.2556 | 0.2760 | 22.68 | 22.23 |
| 2024 | 12 | 0.2873 | 0.2651 | 8.46 | 9.15 |
| 2025 | 11 | 0.1623 | 0.2233 | 13.96 | 35.47 |

### Horizon 2

Paired supported rows: 199 of 199 test rows (excluded as unsupported: 0).

| arm | n | Brier(appear) | RMSE points | MAE points | bias points |
|---|---|---|---|---|---|
| candidate | 199 | 0.2200 | 36.71 | 18.73 | 0.36 |
| b1 | 199 | 0.2267 | 35.12 | 19.32 | 1.01 |
| b2 | 199 | 0.2202 | 36.30 | 18.32 | -0.10 |

Candidate − B1, 90% player-cluster intervals: Brier -0.0067 [-0.0199, 0.0068]; RMSE points 1.60 [-2.64, 6.61] (RMSE units).
**Selection at this horizon: baseline_research_candidate** (both arms reported; this is retrospective model selection).

| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| QB | 53 | 0.1843 | 0.1961 | 23.13 | 21.40 |
| RB | 41 | 0.2225 | 0.2222 | 50.06 | 52.96 |
| TE | 36 | 0.2562 | 0.2579 | 31.27 | 33.10 |
| WR | 69 | 0.2271 | 0.2366 | 38.44 | 31.10 |

| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| 2012 | 15 | 0.1918 | 0.1855 | 34.97 | 23.06 |
| 2013 | 15 | 0.2244 | 0.2225 | 12.38 | 14.60 |
| 2014 | 22 | 0.3176 | 0.2891 | 55.20 | 56.52 |
| 2015 | 16 | 0.1266 | 0.1501 | 36.97 | 37.40 |
| 2016 | 18 | 0.2147 | 0.2901 | 51.56 | 28.42 |
| 2017 | 19 | 0.2041 | 0.1913 | 22.33 | 20.24 |
| 2018 | 20 | 0.1958 | 0.1673 | 17.72 | 16.14 |
| 2019 | 20 | 0.2845 | 0.2704 | 26.39 | 23.30 |
| 2020 | 16 | 0.1344 | 0.1192 | 14.38 | 12.32 |
| 2021 | 11 | 0.2732 | 0.3312 | 46.32 | 41.41 |
| 2022 | 7 | 0.1770 | 0.2612 | 76.47 | 97.40 |
| 2023 | 8 | 0.2974 | 0.3234 | 39.25 | 41.16 |
| 2024 | 12 | 0.2008 | 0.2212 | 9.12 | 12.66 |

### Horizon 3

Paired supported rows: 187 of 187 test rows (excluded as unsupported: 0).

| arm | n | Brier(appear) | RMSE points | MAE points | bias points |
|---|---|---|---|---|---|
| candidate | 187 | 0.1903 | 38.21 | 18.14 | 0.03 |
| b1 | 187 | 0.1912 | 37.97 | 19.86 | 0.44 |
| b2 | 187 | 0.1820 | 37.43 | 17.49 | -0.84 |

Candidate − B1, 90% player-cluster intervals: Brier -0.0009 [-0.0187, 0.0166]; RMSE points 0.24 [-4.23, 5.73] (RMSE units).
**Selection at this horizon: baseline_research_candidate** (both arms reported; this is retrospective model selection).

| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| QB | 48 | 0.1866 | 0.1892 | 36.84 | 44.19 |
| RB | 38 | 0.1788 | 0.1474 | 44.06 | 40.19 |
| TE | 34 | 0.1952 | 0.2023 | 37.34 | 39.73 |
| WR | 67 | 0.1971 | 0.2118 | 35.97 | 30.12 |

| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| 2012 | 15 | 0.1980 | 0.1669 | 36.29 | 18.43 |
| 2013 | 15 | 0.0669 | 0.0570 | 12.46 | 14.37 |
| 2014 | 22 | 0.2430 | 0.2190 | 62.37 | 62.11 |
| 2015 | 16 | 0.2240 | 0.2210 | 17.64 | 20.22 |
| 2016 | 18 | 0.0943 | 0.1770 | 40.70 | 20.55 |
| 2017 | 19 | 0.1346 | 0.1150 | 19.68 | 19.00 |
| 2018 | 20 | 0.1867 | 0.1712 | 29.89 | 28.84 |
| 2019 | 20 | 0.2627 | 0.2399 | 41.86 | 37.37 |
| 2020 | 16 | 0.0993 | 0.0837 | 15.26 | 13.44 |
| 2021 | 11 | 0.2067 | 0.2507 | 73.87 | 90.14 |
| 2022 | 7 | 0.2597 | 0.3694 | 14.53 | 40.19 |
| 2023 | 8 | 0.4706 | 0.4704 | 24.98 | 30.32 |

### Horizon 4

Paired supported rows: 179 of 179 test rows (excluded as unsupported: 0).

| arm | n | Brier(appear) | RMSE points | MAE points | bias points |
|---|---|---|---|---|---|
| candidate | 179 | 0.1510 | 36.80 | 15.89 | -0.99 |
| b1 | 179 | 0.1504 | 38.98 | 18.81 | -0.03 |
| b2 | 179 | 0.1481 | 36.39 | 15.51 | -1.61 |

Candidate − B1, 90% player-cluster intervals: Brier 0.0006 [-0.0147, 0.0166]; RMSE points -2.18 [-7.24, 3.88] (RMSE units).
**Selection at this horizon: baseline_research_candidate** (both arms reported; this is retrospective model selection).

| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| QB | 46 | 0.1691 | 0.1790 | 29.61 | 36.68 |
| RB | 38 | 0.1542 | 0.1388 | 45.50 | 49.14 |
| TE | 31 | 0.0798 | 0.0948 | 38.28 | 41.71 |
| WR | 64 | 0.1706 | 0.1635 | 34.90 | 31.73 |

| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| 2012 | 15 | 0.1597 | 0.1281 | 34.79 | 20.27 |
| 2013 | 15 | 0.0398 | 0.0368 | 10.43 | 11.66 |
| 2014 | 22 | 0.1993 | 0.1943 | 58.73 | 60.49 |
| 2015 | 16 | 0.1586 | 0.1668 | 22.36 | 23.03 |
| 2016 | 18 | 0.1581 | 0.1805 | 34.89 | 26.90 |
| 2017 | 19 | 0.1190 | 0.1160 | 15.91 | 14.97 |
| 2018 | 20 | 0.1823 | 0.1819 | 14.13 | 14.55 |
| 2019 | 20 | 0.1600 | 0.1360 | 24.75 | 19.15 |
| 2020 | 16 | 0.1347 | 0.1169 | 19.17 | 16.12 |
| 2021 | 11 | 0.1806 | 0.2169 | 77.63 | 88.93 |
| 2022 | 7 | 0.1455 | 0.2043 | 58.02 | 88.48 |

### Horizon 5

Paired supported rows: 172 of 172 test rows (excluded as unsupported: 0).

| arm | n | Brier(appear) | RMSE points | MAE points | bias points |
|---|---|---|---|---|---|
| candidate | 172 | 0.1309 | 32.97 | 12.81 | 0.66 |
| b1 | 172 | 0.1276 | 33.74 | 13.43 | 0.44 |
| b2 | 172 | 0.1185 | 32.33 | 11.99 | -0.53 |

Candidate − B1, 90% player-cluster intervals: Brier 0.0032 [-0.0141, 0.0203]; RMSE points -0.77 [-3.13, 1.91] (RMSE units).
**Selection at this horizon: baseline_research_candidate** (both arms reported; this is retrospective model selection).

| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| QB | 45 | 0.1541 | 0.1627 | 29.85 | 35.26 |
| RB | 36 | 0.1770 | 0.1271 | 26.87 | 22.54 |
| TE | 30 | 0.0931 | 0.0713 | 50.46 | 50.92 |
| WR | 61 | 0.1051 | 0.1298 | 27.00 | 26.79 |

| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |
|---|---|---|---|---|---|
| 2012 | 15 | 0.1962 | 0.1691 | 22.67 | 16.54 |
| 2013 | 15 | 0.0449 | 0.0307 | 10.75 | 9.57 |
| 2014 | 22 | 0.1242 | 0.1115 | 63.76 | 64.40 |
| 2015 | 16 | 0.2571 | 0.2472 | 3.98 | 7.70 |
| 2016 | 18 | 0.0417 | 0.1139 | 20.53 | 20.62 |
| 2017 | 19 | 0.0941 | 0.0620 | 9.17 | 7.01 |
| 2018 | 20 | 0.1088 | 0.0908 | 8.11 | 6.42 |
| 2019 | 20 | 0.2150 | 0.2015 | 21.70 | 19.87 |
| 2020 | 16 | 0.0636 | 0.0619 | 12.50 | 8.69 |
| 2021 | 11 | 0.1831 | 0.2257 | 77.10 | 85.07 |

## Support (recorded before fitting)

70 origin × horizon cells; see support.csv for training rows, appearers, per-position counts and test rows.

## Sidecar

7 candidate rows; estimate classes per horizon: year 1: cold_start_candidate 7; year 2: baseline_research_candidate 7; year 3: baseline_research_candidate 7; year 4: baseline_research_candidate 7; year 5: baseline_research_candidate 7

## Unresolved

77 players remain without a new estimate; see unresolved.csv for the reason and the smallest valid next experiment per player.

## Caveats

- **selection**: selecting a policy on this historical evaluation is retrospective model selection, NOT independent confirmation of the selected policy; both arms are reported at every horizon
- **population**: a draft-population prior for drafted players with no rookie-year regular-season record; not conditioned on remaining on a current roster; direction and size of this mismatch have not been measured
- **appearance**: P(appear) is the probability of at least one championship-window stat row; it is not a breakout or usefulness probability
- **horizons**: each horizon is fitted, evaluated and selected independently; acceptance at one horizon never validates another
- **labels**: a complete season with no artifact row is the producers' shared convention zero (tagged); seasons beyond 2025 are unknown
