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
4. **`wr_rec_tds_per_game_final`**: **DARK** — see Section 4.
5. **`wr_yards_per_reception_career`**:
   - `total_career_rec_yards / total_career_receptions`.

### B. RB Features
1. **`rb_final_dominator`**:
   - Formula: `(player_rush_yds + player_rec_yds) / (team_rush_yds + team_rec_yds)` in the player's final college season.
   - Uses `build_team_rush_lookup` for team rushing total and `build_team_rec_lookup` for team receiving total.
   - If player has no final-season rush data, feature is `_missing="1"`. Player receiving yds defaults to 0 if no receiving data found.
2. **`rb_scrimmage_ypg`**: **DARK** — see Section 4.
3. **`rb_rec_ypg`**: **DARK** — see Section 4.
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

**Games-unavailable (CFBD API limitation)**: The CFBD `/stats/player/season` endpoint returns `LONG, REC, TD, YDS, YPR` for receiving and `CAR, LONG, TD, YDS, YPC` for rushing — it does **not** return a `G` (games played) statType. Confirmed by inspection of cached responses for all 2011–2024 seasons. Any feature requiring games played is therefore permanently dark from this data source.

* **`wr_rec_tds_per_game_final`**: `player_rec_tds / games_played` — games unavailable.
* **`rb_scrimmage_ypg`**: `(rush_yds + rec_yds) / games_played` in final season — games unavailable.
* **`rb_rec_ypg`**: `rec_yds / games_played` in final season — games unavailable.

**Other dark features**:
* **`te_deep_yard_share`**: PFF route-alignment dependent. CFBD does not contain targeted depth-of-target shares.
* **`transfer_portal_flag`**: CFBD portal data only goes back to 2019. Ingesting this would bias the training dataset against 2015–2018 classes. Stays `_missing="1"` for Phase 19.
* **`rb_ras_composite` / `wr_ras_composite` / `te_ras_composite`**: RAS adapter remains mock-only.

## 5. Degraded Provenance Flag

`w2b_cfbd_degraded` is written to every row on every W2b run:
* `"1"` when `--allow-degraded` is active and at least one CFBD batch call failed.
* `"0"` on all successful runs (clears any stale `"1"` from a previous degraded run).

This mirrors the W2 `w2_combine_degraded` flag pattern. A `w2b_cfbd_degraded="1"` row must not be used in W3/W4 bake-offs without explicit acknowledgement.

## 6. Caching Architecture

**Year-batched stats** (`load_player_stats`, `load_sp_ratings`): one JSON file per (year, category) in `app/data/cfbd_cache/`. Re-used on subsequent runs unless `--force-fetch` is passed.

**Team pass attempts** (`fetch_team_pass_attempts`): one JSON file per (school, year) in `app/data/cfbd_cache/tpa_<school>_<year>.json`. The W2b pre-fetch loop checks this cache before making an API call. `--force-fetch` bypasses all caches.

All cache files are gitignored (`app/data/cfbd_cache/`).

---

## 7. Verification Plan

1. **Unit Tests (`tests/test_w2b_cfbd.py`)**: 45 tests covering formula correctness, dark-feature confirmation, degraded flag, TPA cache round-trip, and leakage guard.
2. **Live artifact audit**: 874 rows × 149 cols; WR dominator 89.0%, RB dominator 88.4%, TE RYPTPA 86.2%; all dark features `_missing="1"`; `w2b_cfbd_degraded="0"`; no market/PFF-grade columns present.
