# DRAFT — EDGE-H1-00 evidence pull — descriptive only, decision_supported=false, not yet cockpit-reviewed

- Ticket: EDGE-H1-00 (read-only Sleeper league-history evidence pull), David-authorized 2026-07-19.
- League: "Redzone Champions League" — 12-team dynasty (type 2), Superflex (1 QB + SUPER_FLEX slot), PPR (rec = 1.0), FAAB waivers (waiver_type 2, budget 100).
- Current league_id: `1314363401744416768` (2026). Chain walked via `previous_league_id`: 2026 → 2025 `1183088915091423232` → 2024 `1049152209134424064` → 2023 `912589367620100096` (chain terminates; 2023 is the startup season).
- Raw snapshots: `app/data/research/league_behavior/raw/2026-07-19/` — 172 endpoint snapshot files + `fetch_log.json` (173 files, ~2.3 MB). Every snapshot is wrapped `{fetched_at_utc, endpoint_url, payload}`.
- Fetch integrity: final run = 176 HTTP GETs to `api.sleeper.app/v1` only, 0 failures (see `fetch_log.json`). One earlier run attempt aborted on a LOCAL environment error (venv Python missing a CA trust store: `SSL: CERTIFICATE_VERIFY_FAILED` on the first call, no data retrieved); rerun with `certifi` completed cleanly. This was a client-environment failure, not a Sleeper endpoint failure.
- Register: everything below is descriptive counting over the raw payloads. No signal here is validated; no claim of edge is made. Thin samples are flagged inline.

---

## 1. Manager-identity continuity across seasons (reported first — gates everything else)

Method: compared `owner_id` per `roster_id` from each season's `rosters.json`, mapped to `display_name` via `users.json`.

- 2023 → 2024: 11/12 rosters kept the same owner `user_id`. Changed: roster 3 (`jpope2`, user `727609206567428096` → `MDEF`, user `1049829521757237248`).
- 2024 → 2025: 11/12 same. Changed: roster 2 (`Khargreav9`, `978702566609444864` → `jgil96`, `1124744818174812160`).
- 2025 → 2026: 11/12 same. Changed: roster 11 (`mjbaynes29`, `928767555920064512` → `jkazzz`, `1005290797896036352`).
- 9 of the 12 current owners have held the same roster continuously since the 2023 startup. `roster_id` numbering is stable across all four seasons (each replacement owner inherited the departing owner's roster_id).
- Dleess (David) = user `827345221493850112`, roster 1, team "Woodbury Riders", present all four seasons.
- Co-owner records exist: roster 7 (`jspagnola`) has co-owner `606970046656348160` in all four seasons; roster 3 had co-owner `69206560064552960` in 2023 only; roster 11 (`jkazzz`) has co-owner `1262112427034546176` in 2026. Transactions attribute to the roster, not to which co-owner acted (identity-mapping ambiguity, see §4).

Consequence: per-manager longitudinal series are clean for 9 managers over 3 completed seasons; rosters 2, 3, and 11 each have an ownership break and must be split at the break for any per-manager series.

## 2. Coverage matrix

Per-season snapshot coverage (all counts = payload rows actually on disk):

| Endpoint | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| league object | 1 | 1 | 1 | 1 (status `in_season`) |
| users | 12 | 12 | 12 | 12 |
| rosters | 12 | 12 | 12 | 12 |
| matchups, weeks 1–18 | 12 rows/wk, all 18 wks played | same | same | 12 rows/wk returned, all `points` 0.0 (no 2026 games yet — stubs, not results) |
| transactions (all statuses, weeks 1–18 buckets) | 243 | 323 | 299 | 58 (all in bucket 1) |
| drafts | 1 (startup snake, 18 rds) | 1 (rookie linear, 3 rds) | 1 (rookie linear, 3 rds) | 1 (rookie linear, 3 rds) |
| draft picks | 216 | 36 | 36 | 36 |
| traded_picks | 47 | 24 | 28 | 26 |

Nothing requested was unobtainable: every endpoint returned HTTP 200 for every season in the chain. There is no league history before 2023 (the 2023 league object has `previous_league_id = null`).

Playoff structure: `playoff_week_start = 15` in all seasons; weeks 15–18 matchup rows exist and are scored, but not every roster appears in a paired `matchup_id` in those weeks (196 of 216 possible manager-weeks per completed season are paired head-to-head rows; the rest are unpaired/consolation-structure rows).

Timestamp semantics observed:

- Transactions carry `created` and `status_updated` as epoch **milliseconds** (UTC). Observed ranges: 2023 season ledger spans 2023-07-26 → 2023-12-31; 2024 spans 2024-02-13 → 2025-01-01; 2025 spans 2025-01-13 → 2026-01-01; 2026 spans 2026-01-09 → 2026-06-07 (fetch date 2026-07-19).
- Transactions carry `leg` = week bucket 1–18. **All offseason transactions bucket into leg 1** (2023: 58, 2024: 130, 2025: 131, 2026: 58 rows in bucket 1). `leg` is therefore only a calendar week in-season; month-level analysis below uses `status_updated`.
- Transaction `status` is `complete` or `failed`; **failed waiver claims are retained with their `settings.waiver_bid`**, so losing FAAB bids are visible (accepted-trade history only — offered-but-declined trades are NOT in the API).
- Waiver rows carry `settings.waiver_bid` (FAAB dollars) and `waiver_budget` context; trade rows carry `draft_picks` legs and `consenter_ids`.
- Drafts carry `start_time` epoch ms. Matchup payloads carry **no timestamps** (week index only). Draft picks carry player metadata (name, position, team) inline.

Transaction type totals (all statuses): 2023 — 136 waiver / 95 free_agent / 12 trade; 2024 — 143 / 165 / 11 (+4 commissioner); 2025 — 200 / 86 / 9 (+4 commissioner); 2026-to-date — 17 / 32 / 7 (+2 commissioner).

## 3. Candidate-signal viability reads (strictly factual)

Definitions used throughout: "moves" = completed `waiver` + `free_agent` transactions; "trades" = completed `trade` transactions; manager labels are Sleeper display names; Dleess = David.

### (a) Lineup efficiency — starters-vs-bench proxy only

Optimal-lineup computation was NOT performed. Matchup payloads contain per-player points (`players_points`) and `starters_points`, and the league object contains scoring settings — but matchup payloads carry **no position/slot eligibility**. Computing an optimal lineup would require joining the separate `/players/nfl` dump and assuming today's position designations applied in past seasons. Per ticket instruction, the weaker available proxy is reported instead: bench points = Σ`players_points` − Σ`starters_points`, per manager per week, summed over the 18 played weeks. This proxy does not respect slot eligibility (bench QB points are not necessarily startable), so it is an upper-bound-style activity/depth measure, not "points left on the bench by a legal swap."

League-wide bench points per manager-week: 2023 range 49.1 (Dleess) to 92.8 (jspagnola); 2024 range 36.0 (Dseidman) to 87.3 (Dleess); 2025 range 39.0 (Dseidman) to 72.7 (jspagnola; Dleess 71.1).

Selected season totals (starters / bench, 18 weeks):

| Manager | 2023 | 2024 | 2025 |
|---|---|---|---|
| Dleess | 1956.6 / 884.3 | 1130.6 / 1571.5 | 1455.7 / 1280.3 |
| jspagnola | 1992.1 / 1670.3 | 2595.1 / 1308.5 | 2631.6 / 1308.7 |
| Dseidman | 1937.0 / 913.0 | 2037.4 / 647.6 | 1750.5 / 702.7 |
| jspringe88 | 1817.6 / 1051.1 | 2601.2 / 807.4 | 1996.3 / 1095.2 |

Two managers' benches out-pointed their starting lineups in a season: Dleess 2024 (bench 1571.5 vs starters 1130.6) and jlillian80 2023 (1513.1 vs 1462.2). Full per-manager table computable from the raw files.

### (b) Activity timing — moves by manager by month

Method: completed waiver+free_agent transactions, attributed to every roster on the transaction, bucketed by `status_updated` month (UTC). Full 12×month matrices are derivable from raw; observed shape in numbers:

- League-wide completed moves per season: 2023: 153 adds / 126 drops worth of transactions (see (f)); monthly activity in 2023 runs Aug–Dec only (startup year).
- Managers with zero moves in multiple consecutive months while the season ran (observable activity cliffs, raw): kgelardi 2023 recorded first move in October (0 in Aug–Sep); Dseidman 2023 first move in October; Khargreav9 2023: 3 moves all season (Oct–Nov only), 2024: 9, concentrated Sep–Dec; mjbaynes29 2025: 5 moves total, none after September; kgelardi 2025: 3 moves total.
- Highest monthly single-manager counts: rzalika 2024-10: 18 moves; Dleess 2025-10: 11; jspringe88 2024-10: 10.
- Offseason activity exists in every year (e.g., 2024-02 through 2024-05: 4–7 moves/month for several managers; 2025-05: 9 moves by Dleess and 9 by rkissane).

### (c) Trade network

Completed trades: 2023: 12, 2024: 11, 2025: 9, 2026 through 2026-06-07: 7. Trades including draft-pick legs: 9/12, 10/11, 8/9, 7/7 respectively.

Repeat pairs within a season: 2023 MJLeess318<>jspagnola ×2; 2024 Dleess<>MDEF ×3. All other pairs appear once per season. Dleess trade counts: 4 (2023), 5 (2024), 2 (2025), 1 (2026 to date); 2024 partner concentration: 3 of Dleess's 5 trades were with MDEF. Managers with ≤1 trade across 2023–2025 combined: Dseidman (1, in 2024), Khargreav9 (0 in 2023–24 while active). Full pair lists per season are in the raw analysis and reproducible from `transactions_week_*.json`.

### (d) Post-loss vs post-win move rate

Method (exact): for each completed season, head-to-head results were derived from matchup payloads — two rosters sharing a `matchup_id` in a week, higher `points` = W (no ties observed; unpaired weeks excluded, giving 196 of 216 manager-weeks per season). For each manager-week (rid, w) with a result, the count of completed waiver+free_agent transactions with that roster in `roster_ids` and `leg == w+1` was attributed to "after_win" or "after_loss." Week-18 results contribute no following week. Offseason leg-1 bucketing does not contaminate this because only legs 2–18 are counted as "next week."

| Season | After loss: mgr-wks / moves / rate | After win: mgr-wks / moves / rate |
|---|---|---|
| 2023 | 98 / 71 / 0.724 | 98 / 65 / 0.663 |
| 2024 | 98 / 77 / 0.786 | 98 / 71 / 0.724 |
| 2025 | 98 / 48 / 0.490 | 98 / 58 / 0.592 |
| Pooled | 294 / 196 / 0.667 | 294 / 194 / 0.660 |

League-level pooled rates are near-identical (0.667 vs 0.660). Direction is not consistent across seasons (2023–24 loss>win, 2025 win>loss). Per-manager cells are thin (2–16 manager-weeks per cell per season); the largest per-manager season gaps observed: jpope2 2023: 1.400 after loss vs 0.364 after win (5 vs 11 wks); rkissane 2023: 0.125 vs 1.000 (8 vs 8); jspringe88 2024: 0.333 vs 1.000 (3 vs 13); rkissane 2025: 0.667 vs 0.200 (12 vs 5). At these sample sizes single-week clusters move the rate materially; no stability claim is made.

### (e) FAAB spend curves

Budget 100/season. Method: completed `waiver` transactions' `settings.waiver_bid`, summed per manager (and by `status_updated` month); failed claims counted separately.

Total FAAB spent (of 100) per completed season:

| Manager | 2023 | 2024 | 2025 |
|---|---|---|---|
| jspagnola | 100 | 55 | 61 |
| kgelardi | 60 | 99 | 3 |
| MDEF (from 2024) | — | 100 | 9 |
| MJLeess318 | 25 | 55 | 30 |
| Dleess | 48 | 8 | 25 |
| mjbaynes29 | 49 | 3 | 0 |
| jspringe88 | 0 | 10 | 32 |
| rkissane | 15 | 13 | 15 |
| Khargreav9 (thru 2024) | 10 | 35 | — |
| jgil96 (from 2025) | — | — | 15 |
| rzalika | 0 | 0 | 0 |
| jlillian80 | 0 | 0 | 0 |
| Dseidman | 0 | 0 | 0 |

- Three managers (rzalika, jlillian80, Dseidman) spent $0 FAAB in all three completed seasons while still winning claims at $0 (rzalika won 16 claims in 2024 and 27 in 2025 at $0 bids).
- Late-season concentration occurs: jspagnola bid $80 of his $100 in Nov 2023 and $36 in Dec 2024; MDEF bid $80 in Dec 2024; kgelardi $60 in Sep 2024.
- Failed (outbid/insufficient) claims per season league-wide: 53 (2023), 48 (2024), 74 (2025). Highest individual: jpope2 17 failed vs 12 won (2023); rzalika 15 failed (2024) and 22 failed (2025), all at $0.

### (f) Add/drop churn

Completed waiver+free_agent player adds / drops per season (league totals): 2023: 153 / 126; 2024: 186 / 208; 2025: 138 / 168; 2026 to 06-07: 13 / 44 (2026 drops include roster-trim activity with no matching adds; commissioner transactions excluded throughout). Highest-churn manager-seasons: rzalika 2024 (46 adds / 49 drops) and 2025 (30/27). Lowest (full-season participants): Dseidman 2023 (3/1), mjbaynes29 2025 (1/4), kgelardi 2025 (2/1). Dleess: 17/13 (2023), 21/20 (2024), 22/25 (2025).

### (g) Draft-pick posture

Source: each season's `traded_picks` end-state (picks whose current `owner_id` ≠ original `roster_id`). This is a point-in-time ownership displacement count, NOT a gross trade-flow log — `previous_owner_id` records only the last hop, and rows age out as drafts complete. Counts by manager (own future picks held elsewhere / other managers' picks held), per season snapshot:

- 2023 (47 rows, incl. 36 startup-draft-pick rows): jspagnola 20 away / 20 held; jpope2 19 / 18; Dleess 2 / 5.
- 2024 (24 rows, seasons 2024–2027): MDEF 6 away; kgelardi 5 away; Dleess 2 away / 9 held (most others'-picks held in the league).
- 2025 (28 rows, 2025–2027): kgelardi 6 away; MDEF 5; jspagnola 5; Dleess 1 away / 10 held (most in league).
- 2026 (26 rows, 2026–2028): MDEF 5 away; MJLeess318 4; jspagnola 4; Dleess 0 away / 8 held (most in league).

Dleess is the largest net holder of other managers' picks in every snapshot from 2024 onward (net +7, +9, +8) while having 0–2 own picks displaced.

Drafts: 2023 startup snake, 18 rounds, 216 picks (start 2023-08-06 UTC); rookie drafts 2024/2025/2026, linear, 3 rounds, 36 picks each (starts 2024-05-11, 2025-05-03, 2026-05-11 UTC). Rookie-draft slot orders are in each `draft_*.json` (`draft_order`/`slot_to_roster_id`).

## 4. Named limitations

1. **History depth**: 3 completed seasons + 1 in-progress. The 2023 season is a startup year (18-round snake, Aug–Dec ledger only) and is structurally different from 2024–25.
2. **Sample sizes**: per-manager per-season cells are small everywhere — e.g., post-result cells of 2–16 manager-weeks, trade counts of 0–5 per manager-season, FAAB ledgers of 1–27 winning claims. League-level pooled numbers (294 manager-weeks per condition) are the only cells above ~100 observations.
3. **What the public API cannot see**: league chat/DMs, trade offers that were declined or countered (only *accepted* trades appear), pending/vetoed states beyond final status, waiver claims never submitted, app logins/page views, and any off-platform communication. "Activity" here means executed transactions only.
4. **Identity ambiguity**: three roster-ownership breaks (rosters 2, 3, 11) split those longitudinal series; co-owned rosters (7 in all seasons; 3 in 2023; 11 in 2026) cannot be attributed to an individual human; `MJLeess318`'s team name changed ("All Gas No Brake" 2023–24 → "Free Kelly" 2025–26) — same `user_id` throughout.
5. **Proxy weakness (lineup)**: starters-vs-bench points is not points-above-optimal; it ignores slot eligibility and roster-slot composition, and whether reserve-slot players appear in `players_points` was not independently verified.
6. **Leg-1 bucketing**: offseason transactions all carry `leg = 1`, so week-indexed analyses are valid only for in-season legs 2–18; calendar analyses use `status_updated` (UTC — late-Sunday US activity can land on the next UTC day/month at the margin).
7. **Ledger boundaries**: each season's transaction ledger begins when the season's league object was created (mid-Jan to mid-Feb); Jan/early-Feb activity may sit in the prior season's ledger (e.g., 2024-12/2025-01 rows appear under the 2024 league).
8. **traded_picks is end-state**: it under-counts managers whose traded picks have since conveyed or aged out, and the last-hop `previous_owner_id` hides intermediate hops.
9. **Fetch environment**: one aborted first run due to a local CA-trust error (no payloads written); the recorded `fetch_log.json` covers the successful run (176 calls, 0 failures).

All quantities above are recomputable from the raw snapshots alone; no external data entered this report. decision_supported=false.
