# Phase 19 Workstream 2b Spec: CFBD Player-Level Ingestion and Feature Calculation

## Status
**IMPLEMENTED** — Execution approved. Implementation complete at commit `4c8eeb6` (branch `feature/phase19-w1-head-b-target`). See `docs/agent-ledger/2026-05-23.md` for verified run results.

## Objective
Enrich `prospects_with_outcomes_v3.csv` with player-level CFBD college statistics, team SP+ ratings, and proxy era flags for WR, RB, and TE prospect cohorts (classes 2015–2024).

---

## 1. High-Efficiency API Query Architecture

To protect our CFBD API quota and prevent single-player sequential query failures:
1. **Year-Batched Ingestion**: Instead of querying per-player, the ingestion script (`scripts/build_w2b_cfbd.py`) will perform batched queries by college season (2013–2024):
   - **Receiving Stats**: `GET /stats/player/season?year=YYYY&category=receiving` (12 calls total).
   - **Rushing Stats**: `GET /stats/player/season?year=YYYY&category=rushing` (12 calls total).
   - **SP+ Ratings**: `GET /ratings/sp?year=YYYY` (12 calls total).
2. **Local gitignored Caching**:
   - Raw JSON payloads will be saved locally to `app/data/cfbd_cache/` (e.g., `receiving_2022.json`, `rushing_2022.json`, `sp_ratings_2022.json`).
   - The directory `app/data/cfbd_cache/` is strictly added to `.gitignore`.
3. **Local In-Memory Join**:
   - The script will read `prospects_with_outcomes_v3.csv`.
   - For each prospect, it will locate their matching college stats in the cached JSONs using the standard **Identity Join Protocol**.

---

## 2. Identity Join Protocol

To maintain data integrity and prevent false matches:
* **Match Keys**: Match players deterministically on `(normalized_player_name, normalized_college_name)`.
* **Normalization Map**:
  - Consume `normalize_player_name()` from the core parser to strip punctuation, suffixes (Jr., III), and match case.
  - Consume our expanded `normalize_college_name()` map from `cfbd_receiving_adapter.py` (which includes all 81 deterministic PFR-to-PFF/CFBD aliases).
* **Quarantine Fallback**:
  - If a player transferred or has an unresolved name/school variation, set the feature values to `None` and flag `[feature_name]_missing="1"`.
  - **No fuzzy matching** is allowed in production ingestion.

---

## 3. Specific Feature Calculations

### A. WR Features
1. **`wr_dominator_final`**:
   - Formula: `(yds_share + td_share) / 2` where `yds_share = player_rec_yds / team_rec_yds` and `td_share = player_rec_tds / team_rec_tds` in their final college season.
   - Denominators summed from all players on the same team in that season (via `build_team_rec_lookup` and `build_team_td_lookup`).
   - Falls back to `yds_share` alone if team TD total is zero.
   - Same averaged formula is used for per-season dominator in breakout-age detection.
2. **`wr_breakout_age`**:
   - Age of the player (fitted from draft age) in the earliest season they achieved a ≥20% averaged dominator rating.
3. **`wr_market_share_yds`**:
   - `player_rec_yds / team_rec_yds` in their final college season (yards share only — distinct from `wr_dominator_final`).
4. **`ryptpa`**:
   - `player_rec_yds / team_pass_attempts` in their final college season (same formula as `te_ryptpa_final`).
   - Uses `team_pass_attempts_lookup` prefetched via `fetch_team_pass_attempts`; dark when TPA unavailable.
   - TPA prefetch now covers both TE and WR cohorts.
5. **`wr_rec_tds_per_game_final`**: **DARK** — see Section 4.
6. **`wr_yards_per_reception_career`**:
   - `total_career_rec_yards / total_career_receptions`.
7. **`yprr_college`**: **DARK** — see Section 4.

### B. RB Features
1. **`rb_final_dominator`**:
   - Formula: `(player_rush_yds + player_rec_yds) / (team_rush_yds + team_rec_yds)` in the player's final college season.
   - Uses `build_team_rush_lookup` for team rushing total and `build_team_rec_lookup` for team receiving total.
   - If player has no final-season rush data, feature is `_missing="1"`. Player receiving yds defaults to 0 if no receiving data found.
2. **`rb_scrimmage_ypg`**:
   - `(player_rush_yds + player_rec_yds) / team_games` in the player's final college season.
   - Team games fetched via CFBD `/games` endpoint (regular season); cached individually per (school, year).
   - Dark when no games data available (`team_games_lookup` empty or no entry for this team/year).
   - Source tag: `cfbd_team_games_proxy`.
3. **`rb_rec_ypg`**:
   - `player_rec_yds / team_games` in the player's final college season.
   - Dark when games data or receiving data unavailable.
   - Source tag: `cfbd_team_games_proxy`.
4. **`rb_school_sp_plus`**:
   - The team's overall SP+ rating (`rating` field in `/ratings/sp`) in the player's final college season.

### C. TE Features
1. **`te_ryptpa_final`**:
   - `player_rec_yds / team_pass_attempts` in their final college season.
   - Team pass attempts are fetched via the `/stats/season` endpoint (batched by team and year).
2. **`te_yards_per_reception_career`**:
   - `total_career_rec_yards / total_career_receptions`.

### D. Proxy Era and Declaration Flags
Derived from existing `age_at_draft` and `season` (draft year) in the v3 CSV — **zero external API calls**. These are simplified proxies; `final_college_season` is not a column in the v3 CSV and requires CFBD identity matching to compute exactly.

1. **`final_college_age`**:
   - Formula: `age_at_draft - 1` (proxy; assumes `final_college_season = draft_year - 1`, valid for most players).
   - Source tag: `proxy_age_at_draft`.
2. **`early_declare` / `wr_early_declare`**:
   - Set to `1` if `age_at_draft <= 21.0`, else `0`. Threshold of 21.0 captures sophomores/early juniors.
   - `wr_early_declare` is the same value for WR rows; `_missing="1"` for RB/TE rows.
   - Source tag: `proxy_age_at_draft`.
3. **`covid_eligibility_flag`**:
   - Set to `1` if `draft_year ∈ {2021, 2022}` AND `age_at_draft >= 23.0`, else `0`.
   - Proxy rationale: players who appear unusually old in the 2021/2022 draft likely took the NCAA-granted COVID extra year.
   - Source tag: `proxy_draft_year_age`.

---

## 4. Dark Features (Quarantined)

These features are locked to `_missing="1"` in `prospects_with_outcomes_v3.csv`. The column stubs exist in the CSV (written by W2) but are never populated by W2b.

**Games-unavailable (CFBD `/stats/player/season` limitation)**: The CFBD player-stats endpoint does **not** return a `G` (games played) statType. `rb_scrimmage_ypg` and `rb_rec_ypg` are now computed via the `/games` endpoint team-games proxy (see Section 3B); they are only dark when that proxy is also unavailable.

* **`wr_rec_tds_per_game_final`**: `player_rec_tds / games_played` — games unavailable from player-stats endpoint; no team-games proxy applied for TDs.

**PFF-data-only (permanently dark)**:
* **`yprr_college`**: Yards per route run — requires PFF premium `yprr` field (routes run per season). Not present in CFBD. W2b does not have PFF coverage for 2014–2016 college seasons (only 2017–2023 exist in the PFF export manifest). Permanently `_missing="1"`.
* **`te_deep_yard_share`**: PFF route-alignment dependent. CFBD does not contain targeted depth-of-target shares.

**Other dark features**:
* **`transfer_portal_flag`**: CFBD portal data only goes back to 2019. Ingesting this would bias the training dataset against 2015–2018 classes. Stays `_missing="1"` for Phase 19.
* **`rb_ras_composite` / `wr_ras_composite` / `te_ras_composite`**: RAS adapter remains mock-only.

## 5. Degraded Provenance Flag

`w2b_cfbd_degraded` is written to every row on every W2b run:
* `"1"` when `--allow-degraded` is active and at least one CFBD batch call failed.
* `"0"` on all successful runs (clears any stale `"1"` from a previous degraded run).

This mirrors the W2 `w2_combine_degraded` flag pattern. A `w2b_cfbd_degraded="1"` row must not be used in W3/W4 bake-offs without explicit acknowledgement.

## 6. Caching Architecture

**Year-batched stats** (`load_player_stats`, `load_sp_ratings`): one JSON file per (year, category) in `app/data/cfbd_cache/`. Re-used on subsequent runs unless `--force-fetch` is passed.

**Team pass attempts** (`fetch_team_pass_attempts`): one JSON file per (school, year) in `app/data/cfbd_cache/tpa_<school>_<year>.json`. Pre-fetch loop now covers both TE and WR cohorts. `--force-fetch` bypasses all caches.

**Team games count** (`load_team_games_count`): one JSON file per (school, year) in `app/data/cfbd_cache/games_count_<school>_<year>.json`. Pre-fetch loop covers RB cohort. Mirrors TPA negative-caching pattern (null stored when API returns nothing).

All cache files are gitignored (`app/data/cfbd_cache/`).

---

## 7. Verification Plan

1. **Unit Tests (`tests/test_w2b_cfbd.py`)**: 57 tests covering formula correctness, dark-feature confirmation, games-proxy ypg, WR ryptpa contract column name (`ryptpa` not `wr_ryptpa`), yprr_college permanently dark, games-count cache round-trip, mixed-position CSV column union, degraded flag, TPA cache round-trip, and leakage guard.
2. **Live artifact audit** (post-rebuild 2026-05-24): 874 rows × 155 cols; WR dominator 89.0%, `ryptpa` 85.9% (305/355); `yprr_college` always `_missing="1"`; `rb_scrimmage_ypg`/`rb_rec_ypg` 36.1% (84/233 — games proxy limited by CFBD API cache coverage); TE RYPTPA 86.2%; `w2b_cfbd_degraded="0"`; `wr_ryptpa` absent from headers; no market/PFF-grade columns present.
