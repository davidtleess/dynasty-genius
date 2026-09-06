# DG-177 league scoring component audit — season 2025

Settings sha `3ffeb5582924…` · individual keys credited ['fum', 'fum_lost', 'fum_rec_td', 'pass_2pt', 'pass_int', 'pass_td', 'pass_yd', 'rec', 'rec_2pt', 'rec_td', 'rec_yd', 'rush_2pt', 'rush_td', 'rush_yd', 'st_ff', 'st_fum_rec', 'st_td'] · team keys never applied ['blk_kick', 'def_st_ff', 'def_st_fum_rec', 'def_st_td', 'def_td', 'ff', 'fum_rec', 'int', 'pts_allow_0', 'pts_allow_14_20', 'pts_allow_1_6', 'pts_allow_21_27', 'pts_allow_28_34', 'pts_allow_35p', 'pts_allow_7_13', 'sack', 'safe'] · launch git `634ddf11` dirty=True

## Coverage (rostered Sleeper player-weeks vs weekly source)

- weekly REG player-weeks 18522 (championship weeks 1–17: 17456)
- Sleeper player-weeks 4723 (championship: 4458), players 314; identity resolved 314 / unmapped 0 / ambiguous 0; equal duplicate observations collapsed 1, conflicting 0
- all REG weeks: exact 3382 · attributed difference 8 · absent-zero 1330 · unresolved 3
- championship weeks 1–17: exact 3215 · attributed difference 7 · absent-zero 1233 · unresolved 3
- reconciliation unresolved by reason: {'component_attribution_unresolved': 2, 'source_difference': 1}
- component weeks unresolved by reason: {'event_ambiguous_or_missing_id': 11, 'pbp_event_count_disagrees_with_weekly': 1}
- rostered player-weeks only; not full-universe proof
- event ledger: {'events_total': 1412, 'unique_plays': 532, 'status_counts': {'ambiguous': 21, 'attributed': 1391}, 'ambiguity_counts': {'slot_capacity': 19, 'st_classifier_conflict': 2}, 'events_missing_player_id': 0, 'events_not_joinable_to_weekly': 0, 'player_weeks_with_problem_events': 2, 'player_weeks_unresolved': 12}
- quarantine re-audit (ALL rows, every season): {'rows_total': 530, 'audit_season_rows': 22, 'audit_season_reg_rows': 18, 'audit_season_post_rows': 4, 'historical_rows': 508, 'original_nonzero_ppr_rows': 6, 'nonzero_under_league_keys_rows': 36, 'st_split_unknown_rows': 30, 'unknown_component_value_rows': 0}

## Exact-league qualification: False

- rostered player-weeks only; not full-universe proof
- unresolved_player_weeks: 3
- kicker_keys_unsupported_for_present_kickers

## Differences vs research PPR (attributed) and unresolved rows (ids, never names)

 week sleeper_id    gsis_id  sleeper_points  research_ppr  league_points  diff_vs_research  diff_vs_league             unresolved_reason            reconciliation_reason                status
    1       4983 00-0034827            8.60         10.60           8.60     -2.000000e+00   -1.776357e-15                                                                attributed_difference
    1       9494 00-0038976            2.20          4.20           2.20     -2.000000e+00    0.000000e+00                                                                attributed_difference
    6      11560 00-0039918           19.88         20.38          20.38     -5.000000e-01   -5.000000e-01                                              source_difference            unresolved
    9       9500 00-0038997           15.70         17.70          15.70     -2.000000e+00    0.000000e+00                                                                attributed_difference
   11       6804 00-0036264           17.66         17.66          17.66      0.000000e+00    0.000000e+00 event_ambiguous_or_missing_id component_attribution_unresolved            unresolved
   13      12540 00-0040705           -0.10          1.90          -0.10     -2.000000e+00   -1.387779e-16                                                                attributed_difference
   13      12544 00-0040238            2.00          0.00           2.00      2.000000e+00    0.000000e+00                                                                attributed_difference
   14       6904 00-0036389            0.40          2.40           0.40     -2.000000e+00    5.551115e-16                                                                attributed_difference
   15      12474 00-0040583           10.80          4.80          10.80      6.000000e+00    0.000000e+00                                                                attributed_difference
   17       4943 00-0034869            6.08          6.08           6.08      1.776357e-15    1.776357e-15 event_ambiguous_or_missing_id component_attribution_unresolved            unresolved
   18      12526 00-0040124           10.50         12.50          10.50     -2.000000e+00    0.000000e+00                                                                attributed_difference

## Championship-window population deltas (all weekly rows, weeks 1–17; league − research)

- offensive positions (QB/RB/WR/TE): player-weeks 5687, nonzero delta 35, sum -29.0, min -2.0 max 6.000000000000001, unresolved 2
- other positions: player-weeks 11769, nonzero delta 67, sum 121.0, min -2.0 max 12.0, unresolved 10
- recovery touchdowns by defenders would score under the individual key fum_rec_td, but this league starts no defender; the offensive line is the league-relevant effect
