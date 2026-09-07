# DG-177 — stash-selection evaluation (historical low-production candidate screen, report-only)

**Question.** Can the frozen future-production ordering find later contributors among drafted early-career players who
had not yet contributed, better than current production, draft capital or production persistence can? This is a
historical low-production candidate screen on frozen out-of-fold forecasts and DG-179 outcomes. It is not a waiver
backtest (no point-in-time ownership source exists), produces no breakout probability, and its budgets are declared
scenarios, not David's bench allocation.

**Producer run.** `runs/20260907T010712Z/dg177_stash_selection/` (production: bindings passed; launch git `d7bc8315`,
tracked tree clean, untracked run outputs listed). Definitions `stash_selection_definitions_v3` sha `fbcf1a05…` were
frozen before any result (v1 my proposal, v2 root's amendments, v3 root's follow-up; kept as history). Sources bound to
the accepted producers: history `f4fe6644…`, cohort `46e1fc01…`, outcomes `199a48be…`, DG-179 manifest `d3812d0d…`
(target `049d2229…`, last complete season 2025), draft picks `6be2a640…` (declared by its own hash), bindings
`04dae02e…`. Output hashes are in `manifest.json`. Tool: `src/dynasty_genius/eval/stash_selection.py`,
`scripts/dg177/run_stash_selection.py`, `tests/contract/test_stash_selection.py` (52 tests, every rule RED first).

## Cohort and denominators

Origins 2011–2024, 10,228 cohort rows. Primary cohort = verified draft class c ≤ t with 1 ≤ t − c + 1 ≤ 3 and no season
in c..t at or above the deep-roster bar (QB 37 / RB 45 / WR 71 / TE 21, from the full positional panel; absent row =
convention zero). Ledger exclusions: 4,082 outside draft years 1–3, 3,327 without a verified draft class, 1,019 prior
contributors; 1 conflicting draft id excluded with a reason; 1,774 foreign ids in the draft source's gsis column
disclosed. 1,800 primary candidates. The summed t+2/t+3 test needs both frozen horizons and both closed seasons:
1,147 rows over origins 2014–2022 (563 players, 386 of them at more than one origin; the candidate ledger itself has 832 unique players, 606 at more than one origin); 384 excluded as `missing_forecast`
(origins 2011–2013 have no frozen year-3 rows), 269 as `open_season` (origins 2023–2024), 0 as `missing_bar`. No short
panel at either bar. Contributors (appeared AND ≥ the later season's bar in t+2 or t+3): 166 of 1,147 (14.5%); by
position QB 10, RB 53, TE 36, WR 67. 663 rows have a no-record season inside their window.

## Primary test: summed t+2/t+3, pooled over 36 origin × position cells

| ordering | Spearman | AUC | hits@2 | misses@2 | busts@2 | points/slot@2 |
|---|---|---|---|---|---|---|
| frozen future (policy y2+y3) | 0.483 | 0.778 | 27.0 | 139.0 | 15.0 | 143.3 |
| frozen year 1 (help now) | 0.459 | 0.766 | 26.0 | 140.0 | 19.0 | 137.6 |
| origin window points | 0.430 | 0.739 | 27.0 | 139.0 | 16.0 | 137.3 |
| draft pick | 0.301 | 0.688 | 26.5 | 139.5 | 19.0 | 137.7 |
| persistence comparator | 0.440 | 0.744 | 33.0 | 133.0 | 14.0 | 142.5 |

**Paired differences, future minus comparator** (joint support, 36 of 36 cells; player-cluster bootstrap, 1,000 of
1,000 draws finite, seed 20260906; conditional on realized origins and the fixed frozen fits):

| comparator | Δ Spearman | Δ AUC | Δ hits@2 | Δ points@2 |
|---|---|---|---|---|
| origin window points | +0.053 [+0.025, +0.079] | +0.039 [+0.017, +0.056] | +0.0 [−8, +7] | +434 [−1903, +2956] |
| draft pick | +0.182 [+0.109, +0.248] | +0.090 [+0.033, +0.147] | +0.5 [−10.5, +10.5] | +404 [−2926, +3527] |
| persistence | +0.043 [+0.019, +0.065] | +0.034 [+0.013, +0.052] | −6.0 [−15, +3] | +56 [−2880, +2863] |
| frozen year 1 | +0.024 [+0.011, +0.037] | +0.012 [+0.002, +0.021] | +1.0 [−4, +6] | +414 [−847, +1667] |

**Reading.** As an ordering of later production, the frozen future forecast beats every comparator: all four rank
intervals exclude zero, the largest gap being over draft capital. As a fixed-budget shortlist it does not: at two
stashes per position per origin season (72 slots) it finds 27 later contributors, the same as origin production, and
six fewer than the persistence comparator, with every hit interval spanning zero; points captured differ by a few
hundred over 72 slots inside intervals of thousands. Budget sensitivity says the same: at one slot 12 vs 13 (origin) and
15 (persistence); at three slots 42 vs 37 and 41, difference to origin +5 [−2, +12]. Fifteen of the 72 future picks
never appeared in either window season. Per origin season the hit counts swing by one to three in either direction;
no season is decisive. By position the rank advantage holds at RB, WR and TE (AUC 0.79 / 0.79 / 0.77); at QB the
cohort is thin (92 rows, 10 contributors) and draft capital orders it better (AUC 0.84 vs 0.68, 6 vs 3 hits), which is
one origin-season's worth of evidence, not a rule. At WR the persistence comparator captures more hits (13 vs 7).

**No-record-as-unknown bounds** at budget 2 (same fractional weights): future hits 27 lower / 53 upper; origin 27 / 51;
draft 26.5 / 58; persistence 33 / 55. Twenty-six of the future ordering's 72 slot-weights sit on windows with a
no-record season and no known positive, so the hit counts above are lower bounds under the artifact's zero convention.

**Strict-bar sensitivity** (cohort fixed, bars QB 24 / RB 36 / WR 48 / TE 12): the same ordering of orderings
(future 0.483 / 0.796, origin 0.430 / 0.768, draft 0.301 / 0.735, persistence 0.440 / 0.769); hits@2 22 future vs 24
origin, 23 persistence.

**Immediate help, year 1** (1,800 rows, separate analysis): frozen year-1 forecast Spearman 0.551 / AUC 0.832, 42 hits
at budget 2 and 76.9 points per slot, against origin production 0.520 / 0.802 / 37 / 70.9, persistence 0.534 / 0.819 /
41 / 74.3 and draft 0.313 / 0.713 / 35.5 / 64.2.

**Exploratory secondary, summed years 2–5 (the app's Future 2027–2030 window): ONE ORIGIN ONLY (2020), 132 rows.**
Future 0.513 / 0.780 with 3 hits at budget 2; origin 0.481 / 0.725 / 2; persistence 0.491 / 0.749 / 4. One-origin
evidence; no claim rests on it.

## Concise truthful UI wording for the available-players screen

"Future = the frozen model's expected championship-window points for 2027 and 2028 (and the named later years where
shown). On a 2014–2022 historical screen of drafted, early-career players who had not yet reached a deep-roster bar, this
ordering ranked their later production better than current production, draft slot or production persistence; at two
stashes per position per season it found about the same number of later contributors as those simpler orderings (27 of
72 picks, differences within noise). This is not a waiver backtest and not a breakout probability. P(appears) is the
chance of any game in that season, not the chance of becoming useful."

## Disclosures added after root's read (metadata only; companion `dg177_stash_selection.manifest.corrected.json` beside the run)

- **Retrospective position-source risk.** The bars use each player-season's FROZEN stat-line position (modal, with the
  same-season roster fallback). Those frozen assignments can themselves carry later-role corrections in the source (an
  independent transition review found 12 historic stat-line/roster conflicts), so roles are not contemporaneously
  verified. The exact frozen forecast values and role assignments are preserved as they are; definitions v4 carries this
  wording for future runs with no other change.
- **Deployment.** `nonproduction=False` means only that the accepted bindings held. Nothing was deployed, promoted or
  served; this is a report-only research run.
- **Binding guard.** At launch the CLI did not compare the captured outcome-manifest bytes to the bindings; this run's
  manifest records the accepted DG-179 manifest `d3812d0d…` in its sources, so the results stand. The guard and its
  metadata-only-mutation test were added afterwards.
- **What the numbers support.** A broader-pool ordering improvement, retrospectively; the chosen two-per-position-per-origin
  shortlist has no demonstrated edge (future 27 hits = origin 27; help-now 26; persistence 33; paired hit and point
  intervals cross zero). No proved stash-pickup strategy and no breakout badge follow from this. Root authors the final
  UI copy after numeric acceptance; the wording above is a proposal.

## Not claimed

Waiver or availability backtest; calibrated breakout probability; David's optimal allocation; NFL experience from
observed-history seasons (the exploratory observed-history stratum was not run in this release); an untouched
confirmation — the selection policy was chosen historically on these folds; future-season, ranking-selection or
model-fit uncertainty — the bootstrap conditions on realized origins and the fixed frozen fits.

## Reproduce

```
.venv/bin/python scripts/dg177/run_stash_selection.py \
  --history runs/20260906T195728Z/dg177_basic_horizons/historical_predictions.csv \
  --cohort runs/20260906T195728Z/dg177_basic_horizons/basic_cohort.csv.gz \
  --outcomes /Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/outcomes.csv \
  --outcomes-manifest /Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/manifest.json \
  --draft /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/draft_picks/draft_picks_full.parquet \
  --definitions docs/experiments/stash_selection_definitions_v3.json \
  --bindings docs/experiments/stash_selection_bindings_v1.json --out-root runs
```
