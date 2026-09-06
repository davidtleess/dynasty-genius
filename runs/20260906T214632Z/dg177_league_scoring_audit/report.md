# DG-177 league scoring component audit — season 2025

Settings sha `3ffeb5582924…` · individual keys credited ['fum', 'fum_lost', 'fum_rec_td', 'pass_2pt', 'pass_int', 'pass_td', 'pass_yd', 'rec', 'rec_2pt', 'rec_td', 'rec_yd', 'rush_2pt', 'rush_td', 'rush_yd', 'st_ff', 'st_fum_rec', 'st_td'] · team keys never applied ['blk_kick', 'def_st_ff', 'def_st_fum_rec', 'def_st_td', 'def_td', 'ff', 'fum_rec', 'int', 'pts_allow_0', 'pts_allow_14_20', 'pts_allow_1_6', 'pts_allow_21_27', 'pts_allow_28_34', 'pts_allow_35p', 'pts_allow_7_13', 'sack', 'safe'] · launch git `7005665d` dirty=True

## Coverage (rostered Sleeper player-weeks vs weekly source)

- weekly REG player-weeks 18522 (championship weeks 1–17: 17456)
- Sleeper player-weeks 4723 (championship: 4458), players 314; identity resolved 314 / unmapped 0 / ambiguous 0; equal duplicate observations collapsed 1, conflicting 0
- all REG weeks: exact 3384 · attributed difference 8 · absent-zero 1330 · unresolved 1
- championship weeks 1–17: exact 3217 · attributed difference 7 · absent-zero 1233 · unresolved 1
- reconciliation unresolved by reason: {'source_difference': 1}
- component weeks unresolved by reason: {'event_ambiguous_or_missing_id': 2}
- rostered player-weeks only; not full-universe proof

## Exact-league qualification: False

- rostered player-weeks only; not full-universe proof
- unresolved_player_weeks: 1
- kicker_keys_unsupported_for_present_kickers

## Differences vs research PPR (attributed) and unresolved rows (ids, never names)

 week sleeper_id    gsis_id  sleeper_points  research_ppr  league_points  diff_vs_research  diff_vs_league unresolved_reason reconciliation_reason                status
    1       4983 00-0034827            8.60         10.60           8.60              -2.0   -1.776357e-15                                         attributed_difference
    1       9494 00-0038976            2.20          4.20           2.20              -2.0    0.000000e+00                                         attributed_difference
    6      11560 00-0039918           19.88         20.38          20.38              -0.5   -5.000000e-01                       source_difference            unresolved
    9       9500 00-0038997           15.70         17.70          15.70              -2.0    0.000000e+00                                         attributed_difference
   13      12540 00-0040705           -0.10          1.90          -0.10              -2.0   -1.387779e-16                                         attributed_difference
   13      12544 00-0040238            2.00          0.00           2.00               2.0    0.000000e+00                                         attributed_difference
   14       6904 00-0036389            0.40          2.40           0.40              -2.0    5.551115e-16                                         attributed_difference
   15      12474 00-0040583           10.80          4.80          10.80               6.0    0.000000e+00                                         attributed_difference
   18      12526 00-0040124           10.50         12.50          10.50              -2.0    0.000000e+00                                         attributed_difference

## Championship-window population deltas (all weekly rows, weeks 1–17; league − research)

- player-weeks with a nonzero delta: 102 of 17456; sum 92.0; min -2.0 max 12.0
- weekly rows unresolved in the window: 2
