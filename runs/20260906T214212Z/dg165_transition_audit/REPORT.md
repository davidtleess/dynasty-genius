# DG-165 rookie → veteran transition audit

Same realized target on both sides: `049d2229c4ba06ee…` (nflverse_default_ppr_championship_window_v1).

This is an audit of two frozen forecasts on one realized target; no correction, blend, uplift, youth bonus, market input, added feature or refit is proposed here.

## Experience 1 (the veteran forecast has 1 more season(s) of NFL information)

Paired rows: n = 885 over draft classes 2011–2024.

| forecast | RMSE | MAE | bias | Brier(appear) | calib slope |
|---|---|---|---|---|---|
| rookie | 71.4 | 53.5 | -5.0 | 0.114 | 1.04 |
| veteran | 62.3 | 44.0 | -9.9 | 0.101 | 1.16 |

Paired difference (veteran − rookie): mean squared error -1227.4 [90% player-bootstrap -1590.2, -857.2]; mean absolute error -9.6 [-11.6, -7.6]; veteran closer on 61.1% of rows; classes where the veteran side is better: 13 of 14.

The interval is conditional on both frozen fits and the realized seasons; player-sampling variability only — not model, not selection, not season uncertainty, and not a forecast interval.

| draft position | n | rookie RMSE | veteran RMSE | rookie MAE | veteran MAE | rookie bias | veteran bias |
|---|---|---|---|---|---|---|---|
| QB | 102 | 102.7 | 95.8 | 76.3 | 67.9 | -35.8 | -39.2 |
| RB | 255 | 76.2 | 68.7 | 57.5 | 48.9 | -2.2 | -5.2 |
| TE | 158 | 46.4 | 40.2 | 34.8 | 30.3 | 6.2 | -2.6 |
| WR | 370 | 66.2 | 52.9 | 52.5 | 39.8 | -3.2 | -8.1 |

| draft class (temporal fold) | n | mean sq err diff | mean abs err diff |
|---|---|---|---|
| 2011 | 66 | -708.4 | -5.2 |
| 2012 | 62 | -2290.5 | -14.9 |
| 2013 | 55 | -1910.8 | -13.7 |
| 2014 | 58 | -1593.5 | -11.6 |
| 2015 | 59 | -735.3 | -1.9 |
| 2016 | 58 | -1409.2 | -9.1 |
| 2017 | 62 | -92.2 | -3.5 |
| 2018 | 62 | 202.7 | 2.0 |
| 2019 | 64 | -1368.5 | -11.3 |
| 2020 | 66 | -1447.2 | -10.9 |
| 2021 | 68 | -1938.3 | -17.6 |
| 2022 | 71 | -1990.4 | -12.6 |
| 2023 | 68 | -939.6 | -7.3 |
| 2024 | 66 | -933.5 | -15.2 |

| thin history (veteran games_t <= 4 in the feature season) | n | rookie RMSE | veteran RMSE |
|---|---|---|---|
| False | 723 | 74.9 | 64.9 |
| True | 162 | 53.2 | 48.8 |

Coverage of the WHOLE modelling cohort (2083 players) at this experience — paired rows are not all drafted players:

- paired: 885
- no_veteran_row_no_window_appearance: 210
- no_veteran_row_despite_window_appearance: 7
- veteran_row_without_rookie_forecast: 0
- label_unknown: 0
- outside_overlap_classes: 946
- identity_unresolved: 35
- raw source population excluded before modelling (documented in the rookie run): 155

Flags: veteran rows without a window appearance 14; draft/role position disagreements 16.

## Experience 2 (the veteran forecast has 2 more season(s) of NFL information)

Paired rows: n = 976 over draft classes 2010–2023.

| forecast | RMSE | MAE | bias | Brier(appear) | calib slope |
|---|---|---|---|---|---|
| rookie | 73.9 | 54.0 | -6.8 | 0.175 | 1.04 |
| veteran | 54.8 | 38.1 | 2.4 | 0.142 | 1.01 |

Paired difference (veteran − rookie): mean squared error -2461.8 [90% player-bootstrap -2984.6, -1957.0]; mean absolute error -15.9 [-18.4, -13.6]; veteran closer on 64.9% of rows; classes where the veteran side is better: 14 of 14.

The interval is conditional on both frozen fits and the realized seasons; player-sampling variability only — not model, not selection, not season uncertainty, and not a forecast interval.

| draft position | n | rookie RMSE | veteran RMSE | rookie MAE | veteran MAE | rookie bias | veteran bias |
|---|---|---|---|---|---|---|---|
| QB | 124 | 89.8 | 66.1 | 60.2 | 46.4 | -9.4 | 18.8 |
| RB | 264 | 77.1 | 59.1 | 59.1 | 41.9 | -8.1 | 1.2 |
| TE | 183 | 53.2 | 44.6 | 38.0 | 31.1 | -2.5 | -3.2 |
| WR | 405 | 74.5 | 52.3 | 56.1 | 36.2 | -7.1 | 0.7 |

| draft class (temporal fold) | n | mean sq err diff | mean abs err diff |
|---|---|---|---|
| 2010 | 68 | -1127.2 | -3.7 |
| 2011 | 72 | -2143.5 | -12.1 |
| 2012 | 67 | -3604.6 | -18.6 |
| 2013 | 65 | -596.9 | -4.3 |
| 2014 | 63 | -1596.8 | -12.9 |
| 2015 | 70 | -640.2 | -12.1 |
| 2016 | 60 | -3300.8 | -18.1 |
| 2017 | 70 | -4828.9 | -25.6 |
| 2018 | 74 | -2177.2 | -13.2 |
| 2019 | 71 | -2477.6 | -18.8 |
| 2020 | 74 | -3498.7 | -22.1 |
| 2021 | 71 | -2294.6 | -21.5 |
| 2022 | 77 | -2546.8 | -21.1 |
| 2023 | 74 | -3445.5 | -17.1 |

| thin history (veteran games_t <= 4 in the feature season) | n | rookie RMSE | veteran RMSE |
|---|---|---|---|
| False | 703 | 83.0 | 61.6 |
| True | 273 | 42.4 | 31.2 |

Coverage of the WHOLE modelling cohort (2083 players) at this experience — paired rows are not all drafted players:

- paired: 976
- no_veteran_row_no_window_appearance: 118
- no_veteran_row_despite_window_appearance: 8
- veteran_row_without_rookie_forecast: 0
- label_unknown: 0
- outside_overlap_classes: 946
- identity_unresolved: 35
- raw source population excluded before modelling (documented in the rookie run): 155

Flags: veteran rows without a window appearance 16; draft/role position disagreements 19.

## Experience 3 (the veteran forecast has 3 more season(s) of NFL information)

Paired rows: n = 915 over draft classes 2009–2022.

| forecast | RMSE | MAE | bias | Brier(appear) | calib slope |
|---|---|---|---|---|---|
| rookie | 74.9 | 53.8 | -8.3 | 0.205 | 1.06 |
| veteran | 52.3 | 36.2 | 3.5 | 0.137 | 0.95 |

Paired difference (veteran − rookie): mean squared error -2873.0 [90% player-bootstrap -3468.2, -2314.7]; mean absolute error -17.6 [-20.2, -15.0]; veteran closer on 67.0% of rows; classes where the veteran side is better: 14 of 14.

The interval is conditional on both frozen fits and the realized seasons; player-sampling variability only — not model, not selection, not season uncertainty, and not a forecast interval.

| draft position | n | rookie RMSE | veteran RMSE | rookie MAE | veteran MAE | rookie bias | veteran bias |
|---|---|---|---|---|---|---|---|
| QB | 112 | 98.8 | 61.3 | 67.6 | 41.2 | -17.9 | 9.0 |
| RB | 246 | 78.6 | 55.5 | 58.0 | 40.6 | -11.1 | 1.5 |
| TE | 184 | 56.0 | 41.9 | 38.5 | 28.5 | -5.2 | -0.4 |
| WR | 373 | 72.1 | 51.7 | 54.3 | 35.5 | -5.1 | 5.0 |

| draft class (temporal fold) | n | mean sq err diff | mean abs err diff |
|---|---|---|---|
| 2009 | 64 | -838.0 | -8.1 |
| 2010 | 64 | -3128.8 | -14.0 |
| 2011 | 71 | -2897.2 | -21.0 |
| 2012 | 64 | -4017.7 | -24.0 |
| 2013 | 64 | -1496.4 | -9.1 |
| 2014 | 59 | -1247.2 | -12.2 |
| 2015 | 66 | -2059.1 | -12.7 |
| 2016 | 56 | -4591.4 | -22.2 |
| 2017 | 67 | -4626.9 | -23.3 |
| 2018 | 72 | -2655.9 | -13.8 |
| 2019 | 65 | -2938.7 | -19.8 |
| 2020 | 67 | -2887.1 | -20.6 |
| 2021 | 64 | -3123.0 | -21.1 |
| 2022 | 72 | -3669.0 | -23.7 |

| thin history (veteran games_t <= 4 in the feature season) | n | rookie RMSE | veteran RMSE |
|---|---|---|---|
| False | 612 | 84.5 | 59.5 |
| True | 303 | 49.9 | 33.1 |

Coverage of the WHOLE modelling cohort (2083 players) at this experience — paired rows are not all drafted players:

- paired: 915
- no_veteran_row_no_window_appearance: 183
- no_veteran_row_despite_window_appearance: 10
- veteran_row_without_rookie_forecast: 0
- label_unknown: 0
- outside_overlap_classes: 940
- identity_unresolved: 35
- raw source population excluded before modelling (documented in the rookie run): 155

Flags: veteran rows without a window appearance 9; draft/role position disagreements 17.

## Veteran population at the overlap feature seasons, by draft status

- experience 1, drafted_other_position: 102 rows
- experience 1, drafted_skill_outside_cohort: 78 rows
- experience 1, drafted_skill_paired: 885 rows
- experience 1, drafted_skill_unpaired: 5838 rows
- experience 1, no_draft_record: 3325 rows
- experience 2, drafted_other_position: 102 rows
- experience 2, drafted_skill_outside_cohort: 78 rows
- experience 2, drafted_skill_paired: 976 rows
- experience 2, drafted_skill_unpaired: 5747 rows
- experience 2, no_draft_record: 3325 rows
- experience 3, drafted_other_position: 102 rows
- experience 3, drafted_skill_outside_cohort: 78 rows
- experience 3, drafted_skill_paired: 915 rows
- experience 3, drafted_skill_unpaired: 5808 rows
- experience 3, no_draft_record: 3325 rows

_experience is computed from the draft table for drafted players only; rows without a draft record carry no experience (DG-177 seasons_played is left-censored at 2005)_

## Caveats

- **rookie_policy_menu**: the rookie producer's policy menu was refined after inspecting the historical years, so its historical evaluation is a retrospective evaluation with forecast cutoffs enforced, not untouched independent confirmation; this audit inherits that caveat for the rookie side
- **rookie_evidence_status_verbatim**: {"inner_menu": "retrospective historical evaluation with forecast cutoffs enforced; the policy selects, if at all, only inside each training window, but the policy menu itself was refined after inspecting these historical years, so this is not untouched independent confirmation", "plain": "exploratory comparison against the declared policy on the same retrospective evaluation; never used to reassign the canonical evidence"}
- **bootstrap**: both frozen fits and the realized seasons; player-sampling variability only — not model, not selection, not season uncertainty, and not a forecast interval
- **role**: DG-177's basic cohort trusts the offensive STATLINE position and its weekly snapshot carries historic role disagreements with the roster source (e.g. Jordan Matthews 2014 TE vs WR, Logan Thomas 2014 TE vs QB, N'Keal Harry 2019 TE vs WR, Cordarrelle Patterson 2013 RB vs WR). The audit keeps draft_position and veteran_position as attributes, never joins on position, and counts disagreements; equal targets do not prove historic role integrity. No role repair and no refit in this scope.
- **window**: veteran_row_without_window_appearance flags a veteran feature row whose games_t counts stat lines outside the championship window (final regular-season week or postseason) while the window label records no appearance. Those rows are VALID paired evidence — the feature window and the label window differ by design — and are flagged, never rejected.
