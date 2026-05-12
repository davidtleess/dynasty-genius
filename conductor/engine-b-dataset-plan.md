# Engine B Dataset Assembly Plan (Task 5.1)

## Objective
Assemble a training dataset of player-season rows for Engine B, mapping historical NFL production (Season T) to the locked outcome variable (2-year average PPG in T+1 and T+2).

## Contract & Governance
- **Leakage Guards:** Must pass `validate_no_temporal_leakage` and `validate_no_prohibited_features` from `engine_b_contract.py`.
- **Target Audience:** QBs, RBs, WRs, TEs.
- **Output Artifact:** `app/data/training/engine_b_features_v1.csv`

## Feature Engineering Plan

1. **Load Base Data (`nflreadpy`)**:
   - `load_player_stats(seasons)`: Base production (`ppg_t`, `games_t`, `total_points_t`).
   - `load_participation(seasons)`: Advanced usage (`snap_share`, `route_participation`).
   - `load_rosters(seasons)`: Demographics (`age`, `team`, `depth_chart_position`).

2. **Advanced Metrics**:
   - **Target/Air Yards Share**: Derived by dividing player stats by team aggregates per season.
   - **YPRR/TPRR**: Derived from `receiving_yards` or `targets` divided by `routes_run`.
   - **Weighted Opportunity (WOPR)**: Calculated as `(1.5 * Target Share) + (0.7 * Air Yards Share)` [Standard RotoViz formula].

3. **QB Telemetry**:
   - For QBs, leverage the `nflreadpy_qb_adapter` logic (or raw `load_pbp()`) to calculate `epa_per_dropback`, `cpoe`, `dakota`, `dropbacks`, and `pass_attempts`.
   - Flag `is_dual_threat` = `True` if `rushing_yards > 400` in any season `[T-2, T-1, T]`.

4. **Multi-Year Trend Features**:
   - Join `T-1` and `T-2` data onto the `T` row for `ppg_t_minus_1`, `ppg_t_minus_2`, and `snap_share_t_minus_1`.

5. Outcome Calculation (`avg_ppg_t1_t2`)**:
   - Target years: `T+1` and `T+2`.
   - Calculate PPG for both years.
   - **Inactive Season Logic:** Only average seasons where `games > 0`. If a player has 0 games in both `T+1` and `T+2`, the row is dropped from training.
   - **Weighted Opportunity (WOPR):** Calculated as `(1.5 * Target Share) + (0.7 * Air Yards Share)`.


6. **Aging Curves**:
   - Map each row's `age` and `position` (accounting for QB archetype) through `aging_curves.py` to get `aging_curve_value`.

## Next Steps
1. Write `scripts/assemble_engine_b_dataset.py`.
2. Generate `app/data/training/engine_b_features_v1.csv`.
3. Validate against `engine_b_contract.py`.
