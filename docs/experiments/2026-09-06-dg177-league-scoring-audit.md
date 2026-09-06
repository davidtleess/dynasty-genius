# DG-177 — 2025 league scoring component audit (report-only)

**Question.** How far is the research target (`nflverse_default_ppr_championship_window_v1`, the saved
`fantasy_points_ppr` summed over REG weeks 1–17) from David's actual Sleeper league scoring, player-week by player-week,
and which individual scoring keys account for the difference?

**Tool.** `src/dynasty_genius/eval/league_scoring_audit.py` (pure), `scripts/dg177/run_league_scoring_audit.py` (CLI),
`tests/contract/test_league_scoring_audit.py` (71 tests, every rule RED first). Weekly nflverse totals are the authority
for component COUNTS; play-by-play supplies the event grain `(game_id, play_id, event_slot, event_type, player_id)` and
the special-teams / own-vs-opponent / lost split; any disagreement is `unresolved`, never patched. Only individual keys
are credited (`pass_*`, `rush_*`, `rec*`, `fum`, `fum_lost`, `fum_rec_td`, `st_td`, `st_ff`, `st_fum_rec`); team keys
(`ff`, `fum_rec`, `int`, `sack`, `safe`, `blk_kick`, `def_*`, `pts_allow_*`) are never applied to a player and no IDP
setting is inferred from them. Weights are read from the saved league settings (sha `3ffeb558…`), never from constants.
Every input is read once; the bytes hashed into the manifest are the bytes parsed.

**Producer run.** `runs/20260906T220010Z/dg177_league_scoring_audit/` (launch git `4265a36a`, tracked tree clean,
untracked run outputs listed). Sources: DG-165 `identified_weekly.parquet` `6f7c76cc…`, `quarantine.parquet`
`a0f4d9c6…`, nflfastR `pbp_2025.parquet` `5ed293fd…`, league snapshot `league-20260906T130052Z` `ece82e24…`,
`ff_playerids_full.parquet` `5cdeaf1c…`, Sleeper 2025 `matchups_week_01..18.json` (18 files, each hashed) and
`league.json` `d66be804…`. Outputs and their sha256 are in `manifest.json`. Four earlier runs are preserved beside
their notes: `214340Z` FAILED ACCEPTANCE (float sleeper ids resolved nobody; the tool refused, as designed);
`214632Z`, `214808Z` and `215247Z` SUPERSEDED (pre-review guards; the last one called unknown quarantine splits
"nonzero", overwrote original missing values in its quarantine output, compared recovery sides as a sum, counted
missing identity through an overwritable status and omitted unjoinable attributed events from the ledger).

## Ground truth: Sleeper's own points for every rostered player-week

| Population | Player-weeks | Exact | Attributed difference | Absent, zero | Unresolved |
|---|---|---|---|---|---|
| REG weeks 1–18 | 4,723 (314 players, 100% identity) | 3,382 | 8 | 1,330 | 3 |
| Championship weeks 1–17 | 4,458 | 3,215 | 7 | 1,233 | 3 |

"Exact" means Sleeper, research PPR and the computed league points agree within 0.005. Every attributed difference
reconciles to the computed league points within 2e-15. The 1,330 absent-zero rows are resolved identities with no
stat row and 0.0 points; an unresolved identity is never counted absent. One equal duplicate observation (a player on
two rosters in week 18, both 0.0) was collapsed explicitly. The population is rostered player-weeks only; this is not
full-universe proof.

**The eight attributed differences** (ids, never names): four muffed-return or lateral fumbles lost (`fum_lost` −2,
on any play, week 18's included), one fumble-recovery touchdown (`fum_rec_td` +6, no +2), one special-teams forced
fumble plus recovery by the same player (`st_ff` + `st_fum_rec` = +2), one extra lost fumble on a play whose
opponent-ball recovery earned nothing, and one own-team special-teams recovery that earned nothing. Own-team recoveries
on offense (129 rostered player-weeks) earn nothing: `fum_rec` is a team key.

**The three unresolved rows.** Week 6: a −0.5 `source_difference` (research 20.38 vs Sleeper 19.88; root traced it to
a five-yard rushing allocation difference between providers on an aborted snap; no scoring key explains it; it stays
visible). Weeks 11 and 17: two quarterbacks whose weeks include a `slot_capacity`-ambiguous play while their weekly
recovery/forced counts are positive; Sleeper equals research on both, but the special-teams split cannot be verified,
so they are not certified.

## Event ledger and component coverage

1,412 events on 532 fumble plays: 1,391 attributed, 21 ambiguous (19 `slot_capacity` on six plays with more fumbles
than structured slots — root's 2025_17_SEA_CAR/1501 among them — and 2 `st_classifier_conflict` on the blocked
field-goal muff 2025_10_NO_CAR/2504); 0 missing player ids (counted directly, not through the status); 0 attributed
events without a weekly row. `unattributed_events.csv` lists the 21 ambiguous events with a named coverage reason and
reconciles with the manifest's `event_coverage` block. Own and opponent recovery counts are cross-checked separately
against the weekly source, and a week whose split cannot be verified earns no special-teams credit. Twelve weekly
player-weeks are unresolved (10 capacity-ambiguous with split-dependent counts, 1 classifier conflict, 1 weekly
recovery with no play-by-play counterpart); ten of the twelve are defenders.

## Population effect, championship window, league minus research

| Positions | Player-weeks | Nonzero delta | Sum | Range | Unresolved |
|---|---|---|---|---|---|
| QB/RB/WR/TE | 5,687 | 35 | −29.0 | −2 … +6 | 2 |
| other | 11,769 | 67 | +121.0 | −2 … +12 | 10 |

The offensive line is the league-relevant effect: about thirty-five player-weeks and a net −29 points across 601
players, at most 6 points for any player-week. The "other" line is defenders' recovery touchdowns under `fum_rec_td`,
an individual key that would apply but to players this league never starts. The alternative semantics refuted in
preflight (own recoveries at +2) would have added +345 points over 138 offensive players.

## Quarantine re-audit (all 530 rows, every season)

530 rows kept with every original column, value and exception untouched (the arithmetic runs on a separate numeric
frame): 22 from 2025 (18 REG, 4 POST), 508 historical. Verdicts under the league's individual keys: **6 known nonzero**
(the original exceptions, 2001×3, 2003, 2005 +6.0, 2012 +3.1, identical under both formulas), **494 verified zero**,
**30 unknown** (historical rows whose forced-fumble or recovery counts need a special-teams split that unidentified
rows cannot get; `league_points_if_scored` is left empty and only a labelled known-component subtotal is given). 36 rows
cannot be certified inert. Every 2025 quarantined row is verified zero under both formulas. No unknown component
values.

## Exact-league qualification: false

Reasons recorded in the manifest: rostered player-weeks only; three unresolved player-weeks; kicker keys present in the
settings while kickers exist in the source (never scored here, no kicker is rostered). Nothing about labels, forecasts
or outcome artifacts changed; this is evidence for a future "exact-league delta" column, not a re-target.

## Reproduce

```
.venv/bin/python scripts/dg177/run_league_scoring_audit.py \
  --weekly /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/identified_weekly.parquet \
  --quarantine /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/quarantine.parquet \
  --pbp /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/pbp/pbp_2025.parquet \
  --sleeper-season-dir /Users/davidleess/dynasty-genius-product/app/data/research/league_behavior/raw/2026-07-19/season_2025_1183088915091423232 \
  --league-snapshot /Users/davidleess/dynasty-genius-product/app/data/league_runtime/runs/league-20260906T130052Z/snapshot.json \
  --idmap /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/ff_playerids/ff_playerids_full.parquet \
  --season 2025 --out-root runs
```
