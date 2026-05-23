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
   - Formula: Average of `(player_rec_yards / team_pass_yards)` and `(player_rec_tds / team_pass_tds)` in their final college season.
   - Denominators are derived by summing the stats of all players on the same team in that season.
2. **`wr_breakout_age`**:
   - Age of the player (fitted from draft age) in the earliest season they achieved a $\ge 20\%$ dominator rating.
3. **`wr_market_share_yds`**:
   - `player_rec_yards / team_pass_yards` in their final college season.
4. **`wr_rec_tds_per_game_final`**:
   - `player_rec_tds / games_played` in their final college season.
5. **`wr_yards_per_reception_career`**:
   - `total_career_rec_yards / total_career_receptions`.

### B. RB Features
1. **`rb_final_dominator`**:
   - Formula: `(player_rush_yds + player_rec_yds) / (team_rush_yds + team_pass_yds)` in their final college season.
2. **`rb_scrimmage_ypg`**:
   - `(player_rush_yds + player_rec_yds) / games_played` in their final college season.
3. **`rb_rec_ypg`**:
   - `player_rec_yds / games_played` in their final college season.
4. **`rb_school_sp_plus`**:
   - The team's overall SP+ rating (`overall` field in `/ratings/sp`) in the player's final college season.

### C. TE Features
1. **`te_ryptpa_final`**:
   - `player_rec_yds / team_pass_attempts` in their final college season.
   - Team pass attempts are fetched via the `/stats/season` endpoint (batched by team and year).
2. **`te_yards_per_reception_career`**:
   - `total_career_rec_yards / total_career_receptions`.

### D. Proxy Era and Declaration Flags
Derived mathematically from existing `age_at_draft`, `draft_year`, and `final_college_season` in the v3 CSV—requiring **zero external API calls**:
1. **`final_college_age`**:
   - Formula: `age_at_draft - (draft_year - final_college_season)`.
2. **`early_declare` / `wr_early_declare`**:
   - Set to `1` if `final_college_age <= 21.4` (capturing declaring juniors/sophomores), else `0`.
3. **`covid_eligibility_flag`**:
   - Set to `1` if the player played in the `2020` college season and had $\ge 5$ years of college play, else `0`.

---

## 4. Dark Features (Quarantined)

These features cannot be constructed from CFBD and are locked to `_missing="1"` or `None` in `prospects_with_outcomes_v3.csv`:
* **`te_deep_yard_share`**: PFF route-alignment dependent. CFBD does not contain targeted depth-of-target shares.
* **`transfer_portal_flag`**: CFBD portal data only goes back to 2019. Ingesting this would bias the training dataset against 2015–2018 classes. This stays `None` and `transfer_portal_missing="1"` for Phase 19.
* **`rb_ras_composite` / `wr_ras_composite` / `te_ras_composite`**: Locked to `None` and `ras_missing="1"` (RAS adapter remains mock-only).

---

## 5. Verification Plan

1. **Unit Tests (`tests/test_w2b_cfbd.py`)**:
   - Pin expected dominator calculations with standard mock statistics.
   - Pin proxy flag mathematics.
2. **Feature Contract Tests**:
   - Verify all new columns exist in `prospects_with_outcomes_v3.csv`.
   - Verify `HEAD_B_PROHIBITED_COLUMNS` strictly excludes `pick`, `round`, and derived draft capital from Head B training inputs.
