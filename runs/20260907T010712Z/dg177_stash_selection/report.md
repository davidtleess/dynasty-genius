# DG-177 stash-selection evaluation — historical low-production candidate screen on frozen out-of-fold forecasts and DG-179 outcomes; not a waiver backtest (no point-in-time ownership source); no breakout probability; budgets are declared scenarios

Definitions `stash_selection_definitions_v3` sha `fbcf1a05e061…` · nonproduction=False · launch git `d7bc8315` (tracked dirty=False) · conditional on realized origins and the fixed frozen fits

## Cohort (drafted early-career not-yet-contributor screen)

- ledger rows 10228 over origins [2011, 2024]; primary candidates 1800; ledger exclusions {'draft_year_outside_1_3': 4082, 'no_verified_draft_class': 3327, 'prior_contribution': 1019}; draft conflicts 1, invalid draft ids 1774
- summed t+2/t+3 test rows 1147 (563 players; origins [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]); exclusions {'missing_forecast': 384, 'open_season': 269, 'missing_bar': 0}; repeated players 606
- bars primary {'QB': 37, 'RB': 45, 'WR': 71, 'TE': 21} strict {'QB': 24, 'RB': 36, 'WR': 48, 'TE': 12}; short panels primary 0 strict 0
- panel caveat: contribution bars come from the basic-cohort positional panel (players who appeared in that season or the one before), with each player-season's position assigned from that season's stat lines (modal, with the same-season roster fallback), not from today's listing; the panel covers 2005-2025, so every origin and target season used here is inside it

## Primary test: summed t+2/t+3 (pooled over origin × position cells)

| ordering | n | Spearman | AUC | hits@2 | misses@2 | busts@2 | points@2 | points/slot@2 |
|---|---|---|---|---|---|---|---|---|
| rank_future_sum | 1147 | 0.483 | 0.778 | 27.0 | 139.0 | 15.0 | 10319 | 143.322 |
| rank_future_year1 | 1147 | 0.459 | 0.766 | 26.0 | 140.0 | 19.0 | 9905 | 137.568 |
| rank_origin_points | 1147 | 0.430 | 0.739 | 27.0 | 139.0 | 16.0 | 9885 | 137.292 |
| rank_draft | 1147 | 0.301 | 0.688 | 26.5 | 139.5 | 19.0 | 9915 | 137.705 |
| rank_persistence | 1147 | 0.440 | 0.744 | 33.0 | 133.0 | 14.0 | 10263 | 142.543 |

### Paired differences, future minus comparator (joint support; 90% player-cluster intervals; draws requested/finite)

- rank_future_sum_minus_rank_origin_points: Spearman +0.053 [+0.025, +0.079] (joint cells 36, excluded 0, draws 1000/1000); AUC +0.039 [+0.017, +0.056]; hits@2 +0.0 [-8.0, +7.0]; points@2 +434 [-1903, +2956] (draws 1000/1000; frozen fixed-budget selection on the original cells; player-cluster bootstrap of paired per-player contributions; each draw sums the original number of clusters so totals are on the original scale)
- rank_future_sum_minus_rank_draft: Spearman +0.182 [+0.109, +0.248] (joint cells 36, excluded 0, draws 1000/1000); AUC +0.090 [+0.033, +0.147]; hits@2 +0.5 [-10.5, +10.5]; points@2 +404 [-2926, +3527] (draws 1000/1000; frozen fixed-budget selection on the original cells; player-cluster bootstrap of paired per-player contributions; each draw sums the original number of clusters so totals are on the original scale)
- rank_future_sum_minus_rank_persistence: Spearman +0.043 [+0.019, +0.065] (joint cells 36, excluded 0, draws 1000/1000); AUC +0.034 [+0.013, +0.052]; hits@2 -6.0 [-15.0, +3.0]; points@2 +56 [-2880, +2863] (draws 1000/1000; frozen fixed-budget selection on the original cells; player-cluster bootstrap of paired per-player contributions; each draw sums the original number of clusters so totals are on the original scale)
- rank_future_sum_minus_rank_future_year1: Spearman +0.024 [+0.011, +0.037] (joint cells 36, excluded 0, draws 1000/1000); AUC +0.012 [+0.002, +0.021]; hits@2 +1.0 [-4.0, +6.0]; points@2 +414 [-847, +1667] (draws 1000/1000; frozen fixed-budget selection on the original cells; player-cluster bootstrap of paired per-player contributions; each draw sums the original number of clusters so totals are on the original scale)

### No-record-as-unknown bounds at budget 2 (same fractional weights)

- rank_future_sum: hits lower 27.0, upper 53.0, boundary ties 0
- rank_future_year1: hits lower 26.0, upper 56.0, boundary ties 0
- rank_origin_points: hits lower 27.0, upper 51.0, boundary ties 0
- rank_draft: hits lower 26.5, upper 58.0, boundary ties 2
- rank_persistence: hits lower 33.0, upper 55.0, boundary ties 0

## Strict-bar label sensitivity (cohort fixed)

- rank_future_sum: Spearman 0.483, AUC 0.796, hits@2 22.0, points/slot@2 143.322
- rank_future_year1: Spearman 0.459, AUC 0.785, hits@2 21.0, points/slot@2 137.568
- rank_origin_points: Spearman 0.430, AUC 0.768, hits@2 24.0, points/slot@2 137.292
- rank_draft: Spearman 0.301, AUC 0.735, hits@2 19.5, points/slot@2 137.705
- rank_persistence: Spearman 0.440, AUC 0.769, hits@2 23.0, points/slot@2 142.543

## Immediate help (year 1) — separate analysis

- rank_future_sum: Spearman 0.551, AUC 0.832, hits@2 42.0, points/slot@2 76.932
- rank_future_year1: Spearman 0.551, AUC 0.832, hits@2 42.0, points/slot@2 76.932
- rank_origin_points: Spearman 0.520, AUC 0.802, hits@2 37.0, points/slot@2 70.868
- rank_draft: Spearman 0.313, AUC 0.713, hits@2 35.5, points/slot@2 64.178
- rank_persistence: Spearman 0.534, AUC 0.819, hits@2 41.0, points/slot@2 74.286

## Exploratory secondary: summed years 2–5 — ONE ORIGIN ONLY ([2020]); rows 132; exclusions {'missing_forecast': 1124, 'open_season': 544, 'missing_bar': 0}

- rank_future_sum: Spearman 0.513, AUC 0.780, hits@2 3.0
- rank_future_year1: Spearman 0.489, AUC 0.757, hits@2 3.0
- rank_origin_points: Spearman 0.481, AUC 0.725, hits@2 2.0
- rank_draft: Spearman 0.312, AUC 0.693, hits@2 2.0
- rank_persistence: Spearman 0.491, AUC 0.749, hits@2 4.0

## Claims not made
- historical low-production candidate screen on frozen out-of-fold forecasts and DG-179 outcomes; not a waiver backtest (no point-in-time ownership source); no breakout probability; budgets are declared scenarios
- the selection policy was chosen historically on these folds; this is a retrospective frozen-policy evaluation, not an untouched confirmation
- the frozen year-5 horizon exists for origin 2020 only (one-origin evidence)
