# DG-177 — Years 1 to 5 on a longer basic cohort, and the inference cohort that includes absences

**Date:** 2026-09-06 (round 2, items 5 and 6) · **Lane:** Davids-MacBook-Pro-23481 · **Branch:** `ticket/DG-177` ·
**Run:** `runs/20260906T155259Z/dg177_basic_horizons/` · **Report-only.** Labels and features come from fresh pulls
of public nflverse weekly stats (2005–2025) and the players table, saved with shas; nothing served changed; nothing
shared was written. The run's manifest was finalized from its own outputs after the run refused it for an arm
name the validator did not yet accept; nothing was recomputed and the manifest says so.

## 1. Why a second cohort

The served Engine B file starts in 2018 and requires four stat-row games for a feature row. With a two-season
label and nested selection it supports no evaluable year-2 fold at all (companion report). Years three to five
need a longer closed history, and an inference cohort that keeps a player whose whole 2025 was an absence needs a
row built from what is observed, not a fabricated stat line. This cohort is deliberately plain.

| term | value |
|---|---|
| seasons | 2005–2025 weekly stats; 14,555 feature rows (QB 1,968 · RB 3,821 · WR 5,652 · TE 3,114) |
| features | `ppg_t`, `games_t` (ALL games with a stat line, the DG-024 production definition, untouched), `age`, `ppg_t_minus_1`, `games_t_minus_1`, its availability flag, `ppg_last_observed`, `seasons_since_last_observed`, `seasons_played` |
| cohort rule | a row exists for season t if the player appeared in t or t−1; a whole missed season after an active one is a zero-games row with NaN production; two straight absent seasons leave the cohort |
| position | the season's modal stat-line position; the players table's listing is carried beside it |
| age | season minus birth year from the players table; a missing birth date is a flagged NaN, never a guess |
| labels | REG scope, `fantasy_points_ppr`, event = appeared (≥ 1 stat-row game), horizons 1–5, censoring and unresolved identities as in the annual contract; the source passed the completeness, uniqueness and non-missing-scoring checks (173 placeholder rows dropped and counted; two unattributed stat lines, 6.0 points in 2005 and 3.1 in 2012, dropped under the stated 10-point-per-season tolerance and listed) |
| policy | the same selection policy as the annual handoff (baseline / candidate ridge / bounded blend, chosen per position, horizon and quantity on closed inner folds, applied by the same function final scoring calls) |

## 2. What the closed history supports

Every horizon has enough closed feature seasons to evaluate, but nested selection needs a training window deep
enough for an inner fold whose candidate can itself be fitted, so the evaluable folds shrink with the horizon:
year 1 on 14 folds (forecast seasons 2012–2025), year 2 on 12, year 3 on 9 of 10, year 4 on 5 of 8, **year 5 on 1
of 6** (forecast season 2025 only). Skipped folds are written with the reason. Year 5 therefore has forecasts and
one graded season; it is not unsupported, and it is not well measured either.

## 3. Policy evidence (pooled; Δ = policy − training-only baseline, 90% player-resampled)

| pos | year | folds | P(appear) Brier / base · AUC · base rate | points\|appear Δr² | unconditional points Δr² | ΔRMSE |
|---|---|---|---|---|---|---|
| QB | 1 | 14 | 0.156 / 0.222 · 0.83 · 0.67 | +0.097 [+0.066, +0.129] | +0.054 [+0.033, +0.072] | −4.8 [−6.7, −2.7] |
| QB | 2 | 12 | 0.175 / 0.243 · 0.81 · 0.59 | +0.093 [+0.068, +0.122] | +0.052 [+0.011, +0.083] | −4.1 [−7.1, −0.8] |
| QB | 3 | 9 | 0.183 / 0.250 · 0.80 · 0.52 | +0.150 [+0.088, +0.216] | +0.062 [+0.000, +0.110] | −4.3 [−8.4, −0.0] |
| QB | 4 | 5 | 0.174 / 0.249 · 0.83 · 0.46 | +0.161 [+0.081, +0.260] | +0.099 [+0.024, +0.155] | −6.3 [−11.2, −1.3] |
| QB | 5 | 1 | 0.138 / 0.242 · 0.88 · 0.41 | +0.272 [+0.131, +0.476] | +0.091 [−0.180, +0.245] | −5.2 [−16.8, +7.4] |
| RB | 1 | 14 | 0.136 / 0.238 · 0.88 · 0.61 | +0.126 [+0.090, +0.160] | +0.091 [+0.072, +0.110] | −5.2 [−6.5, −3.8] |
| RB | 2 | 12 | 0.164 / 0.250 · 0.84 · 0.48 | +0.211 [+0.165, +0.262] | +0.137 [+0.102, +0.167] | −6.4 [−8.5, −4.4] |
| RB | 3 | 9 | 0.161 / 0.234 · 0.83 · 0.37 | +0.203 [+0.146, +0.273] | +0.182 [+0.137, +0.216] | −7.5 [−9.8, −4.9] |
| RB | 4 | 5 | 0.146 / 0.209 · 0.84 · 0.29 | +0.157 [+0.044, +0.297] | +0.214 [+0.158, +0.254] | −8.3 [−10.8, −5.1] |
| RB | 5 | 1 | 0.117 / 0.168 · 0.84 · 0.21 | +0.239 [−0.000, +0.508] | +0.261 [+0.048, +0.361] | −9.0 [−15.6, −1.2] |
| WR | 1 | 14 | 0.136 / 0.239 · 0.88 · 0.61 | +0.122 [+0.103, +0.143] | +0.103 [+0.089, +0.116] | −6.4 [−7.6, −5.2] |
| WR | 2 | 12 | 0.155 / 0.250 · 0.85 · 0.48 | +0.160 [+0.133, +0.189] | +0.146 [+0.116, +0.171] | −7.8 [−9.8, −5.7] |
| WR | 3 | 9 | 0.152 / 0.237 · 0.85 · 0.39 | +0.201 [+0.156, +0.249] | +0.202 [+0.161, +0.240] | −9.4 [−12.1, −6.8] |
| WR | 4 | 5 | 0.147 / 0.217 · 0.84 · 0.32 | +0.266 [+0.166, +0.385] | +0.208 [+0.138, +0.262] | −8.1 [−11.4, −4.7] |
| WR | 5 | 1 | 0.140 / 0.186 · 0.83 · 0.24 | +0.671 [+0.320, +1.161] | +0.123 [−0.042, +0.237] | −3.4 [−7.6, +0.9] |
| TE | 1 | 14 | 0.147 / 0.234 · 0.86 · 0.63 | +0.128 [+0.092, +0.174] | +0.056 [+0.037, +0.071] | −2.3 [−3.2, −1.5] |
| TE | 2 | 12 | 0.165 / 0.250 · 0.84 · 0.51 | +0.178 [+0.123, +0.242] | +0.090 [+0.056, +0.118] | −3.2 [−4.6, −1.8] |
| TE | 3 | 9 | 0.167 / 0.241 · 0.83 · 0.41 | +0.214 [+0.141, +0.310] | +0.116 [+0.081, +0.145] | −3.7 [−5.0, −2.3] |
| TE | 4 | 5 | 0.153 / 0.216 · 0.83 · 0.32 | +0.202 [+0.110, +0.322] | +0.177 [+0.132, +0.219] | −5.1 [−6.9, −3.4] |
| TE | 5 | 1 | 0.130 / 0.197 · 0.85 · 0.27 | +0.512 [+0.171, +0.941] | +0.196 [+0.104, +0.275] | −5.0 [−7.6, −2.3] |

Chosen policies, per fold and quantity, are in the manifest and `results.json`; the ridge candidate is chosen for
the appearance probability and for games almost everywhere, and a 0.75 blend with persistence for points at most
positions and horizons.

## 4. The reading

1. **On this cohort the policy beats its training-only baselines detectably at every position for years one to
   four**, on both the appearance probability and unconditional season points, with the margin over persistence
   growing with the horizon because persistence decays badly and the appearance model does the work.
2. **These numbers are not comparable to the annual handoff's.** This cohort admits one-game seasons and whole
   absences, so its base appearance rates are 0.6 rather than 0.8 and its baselines are weaker; the served file's
   population is the ≥ 4-game player. Same event, same scoring, different population; each artifact says which.
3. **Year 5 is one fold.** Its intervals are what one forecast season can say. Do not read year 5 as measured; read
   it as "forecast, graded once".
4. **Absences are observations.** 137 of the 750 inference rows are players whose whole 2025 was an absence after an
   active 2024; they carry NaN production, their last observed rate, and one season since last observed. Tank Dell is
   one of them: appearance probability 0.34 for 2026 and 0.37 for 2027, expected 2026 points 22.9, year-5 appearance
   0.03.

## 5. The eligible universe, reconciled (DG-178's 4,041 rows)

Every row has a forecast or one precise reason, from `universe_reconciliation_detail.csv`:

| status | rows | rostered | meaning |
|---|---|---|---|
| forecast | 740 | 228 | in the 2025 cohort (zero-games rows included) |
| no_gsis_mapping | 1,397 | 1 | no NFL id on the row and none in nflverse's id table (rostered: Matt Hibner, TE) |
| left_cohort_two_absent_seasons | 1,285 | 0 | last stat line 2023 or earlier |
| no_nfl_history | 616 | 44 | an id but never a weekly stat line — the 2026 draft class and never-played players; the rookie lane's domain |
| position_outside_modelled_set | 3 | 1 | a 2025 cohort row whose stat-line position is not QB/RB/WR/TE: Travis Hunter (CB by stat line, DB in Sleeper; nflverse's id table lists WR), Andrew Beck and Connor Heyward (FB) |

The ten rostered players named by DG-178 all map: Lloyd, Brooks, Watson, Aiyuk and Dell are zero-games 2025 rows
with forecasts; James, Royals, Ekeler, Richardson and Kraft appeared in 2025 and have forecasts; Hunter is the
position case above. DG-178's message had swapped two Sleeper ids (9484 is Kraft; Dell is 9502); their universe
file was already right.

## 5b. Calibration, beyond Brier (companion record `dg177_basic_horizons.evaluation_status.json`)

A better Brier score than the base rate is not a calibration proof. From the graded predictions: for years one to
three the reliability slope of a logistic recalibration sits at 0.86–1.24 with expected calibration error of
0.02–0.05 at every position, i.e. the appearance probabilities are used close to their face value; for years four
and five the slope drifts to 1.1–1.6 and the error to 0.05–0.10, so those probabilities are directionally right and
somewhat under-confident. The status record beside the run carries these per position and horizon, together with
the fold counts and the baseline comparison worded from its interval; "supported" there means the closed history
was sufficient to evaluate, never validated.

## 6. What this does not support

- **Comparability with the annual handoff** is by event and scoring only, not by population (§4.2).
- **Year 5** rests on one fold; years 3 and 4 on 9 and 5.
- **Hunter** is unforecast here because his stat-line position is CB. Which position model should forecast a two-way
  player is a modelling choice, stated, not made.
- **Basic features only.** No tracking, opportunity or efficiency columns; that is the point of the cohort, and it
  is also its ceiling.
- **Bootstrap intervals are sampling uncertainty conditional on the fitted models**, not model, selection or season uncertainty, as everywhere in this ticket.

## 7. Reproduce

    cd ~/dg-wt/DG-177
    .venv/bin/python -m pytest -q tests/test_dg177_basic_cohort.py tests/test_dg177_basic_horizons.py tests/test_dg177_universe_reconciliation.py
    .venv/bin/python scripts/experiments/dg177_basic_horizons.py --draws 1000 --universe <DG-178 eligible_universe.csv>

Outputs: `basic_forecasts.csv` (750 rows, years 1–5), `universe_reconciliation.csv` and `_detail.csv`, `manifest.json`,
`results.json`, `historical_predictions.csv` (11 MB, kept on disk and pinned by sha in the manifest), the cohort and
both snapshots.
