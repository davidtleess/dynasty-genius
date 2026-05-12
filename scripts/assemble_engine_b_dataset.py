#!/usr/bin/env python3
"""Engine B Dataset Assembly V2 (Task 5.1 Rerun).

Remediates governance audit blockers and warnings:
1. Populates QB efficiency (EPA, CPOE, DAKOTA) using PBP data.
2. Sources route metrics (YPRR, TPRR, Route Participation) from PBP + Participation.
3. Fixes 2024 outcome logic (inference-only).
4. Populates aging_curve_position.
5. Adds historical PPG indicator columns.
6. Applies minimum games threshold (>=4).
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import nflreadpy as nfl
from dotenv import load_dotenv

# Filter warnings for cleaner output
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_ALLOWED_FEATURES,
    OUTCOME_COLUMN,
    FEATURE_SEASON_COL,
    DUAL_THREAT_RUSHING_THRESHOLD,
    validate_no_temporal_leakage,
    validate_no_prohibited_features
)
from src.dynasty_genius.models.aging_curves import aging_curve_value

OUTPUT_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
SEASONS = list(range(2018, 2026)) # 2018 to 2025 features + outcomes

# Minimal games to reduce noise (Audit Warning 2)
MIN_GAMES_THRESHOLD = 4

def _to_pandas(df: Any) -> pd.DataFrame:
    if df is None: return pd.DataFrame()
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    return pd.DataFrame(df)

def fetch_and_agg_stats(seasons: list[int]) -> pd.DataFrame:
    print(f"Loading player stats for {seasons}...")
    stats_weekly = _to_pandas(nfl.load_player_stats(seasons))
    # Filter to skill positions
    stats_weekly = stats_weekly[stats_weekly["position"].isin(["QB", "RB", "WR", "TE"])]
    
    # Aggregation
    agg_map = {
        "fantasy_points_ppr": ["sum", "mean"],
        "targets": "sum",
        "receptions": "sum",
        "receiving_yards": "sum",
        "rushing_yards": "sum",
        "rushing_tds": "sum",
        "receiving_air_yards": "sum",
        "week": "nunique"
    }
    
    stats_seasonal = stats_weekly.groupby(["player_id", "season", "position"]).agg(agg_map).reset_index()
    stats_seasonal.columns = [
        "player_id", "season", "position", 
        "total_points_t", "ppg_t", "targets_t", "receptions_t",
        "yards_t", "rushing_yards_t", "rushing_tds_t", "air_yards_t", "games_t"
    ]
    
    # Team Aggregates for Shares
    team_stats = stats_weekly.groupby(["team", "season"]).agg({
        "targets": "sum",
        "receiving_air_yards": "sum",
        "receiving_yards": "sum"
    }).reset_index()
    team_stats.columns = ["team", "season", "team_targets", "team_air_yards", "team_yards"]
    
    # Get team for each player-season (most frequent team)
    player_team = stats_weekly.groupby(["player_id", "season"])["team"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None).reset_index()
    
    stats_seasonal = stats_seasonal.merge(player_team, on=["player_id", "season"], how="left")
    stats_seasonal = stats_seasonal.merge(team_stats, on=["team", "season"], how="left")
    
    # Derived Features
    stats_seasonal["target_share_nfl"] = stats_seasonal["targets_t"] / stats_seasonal["team_targets"].replace(0, np.nan)
    stats_seasonal["air_yards_share"] = stats_seasonal["air_yards_t"] / stats_seasonal["team_air_yards"].replace(0, np.nan)
    stats_seasonal["weighted_opportunity"] = (1.5 * stats_seasonal["target_share_nfl"].fillna(0)) + (0.7 * stats_seasonal["air_yards_share"].fillna(0))
    
    return stats_seasonal

def main():
    print("Starting Dataset Assembly V2...")
    
    # 1. Base Stats
    df = fetch_and_agg_stats(SEASONS)
    df.rename(columns={"season": "feature_season"}, inplace=True)
    
    # 2. Minimum Games Filter (Audit Warning 2)
    print(f"Applying min games threshold (>= {MIN_GAMES_THRESHOLD})...")
    df = df[df["games_t"] >= MIN_GAMES_THRESHOLD].copy()
    
    # 3. Add Roster Info (Age, Depth Chart)
    print("Adding roster details...")
    rosters_raw = _to_pandas(nfl.load_rosters(SEASONS))
    rosters_agg = rosters_raw.groupby(["gsis_id", "season"]).agg({
        "birth_date": "first",
        "depth_chart_position": lambda x: x.mode().iloc[0] if not x.mode().empty else None
    }).reset_index()
    rosters_agg["birth_year"] = pd.to_datetime(rosters_agg["birth_date"], errors="coerce").dt.year
    rosters_agg["age"] = rosters_agg["season"] - rosters_agg["birth_year"]
    
    df = df.merge(rosters_agg[["gsis_id", "season", "age", "depth_chart_position"]], 
                  left_on=["player_id", "feature_season"], right_on=["gsis_id", "season"], how="left").drop(columns="season")
    
    # 4. Snap Share
    print("Adding snap share...")
    snaps_raw = _to_pandas(nfl.load_snap_counts(SEASONS))
    snaps_agg = snaps_raw.groupby(["pfr_player_id", "season"])["offense_pct"].mean().reset_index(name="snap_share")
    crosswalk = rosters_raw[["gsis_id", "pfr_id"]].dropna().drop_duplicates()
    snaps_agg = snaps_agg.merge(crosswalk, left_on="pfr_player_id", right_on="pfr_id", how="inner")
    
    df = df.merge(snaps_agg[["gsis_id", "season", "snap_share"]], 
                  left_on=["player_id", "feature_season"], right_on=["gsis_id", "season"], how="left").drop(columns="season")

    # 5. Load PBP once for all advanced metrics (QB Efficiency + Routes)
    print(f"Loading PBP data for {SEASONS} to calculate efficiency and routes...")
    pbp = _to_pandas(nfl.load_pbp(SEASONS))
    
    # 5a. QB Efficiency (Audit Blocker 1)
    print("Calculating QB efficiency (EPA, CPOE, DAKOTA)...")
    # Identify dropbacks
    pbp_qbs = pbp[pbp["qb_dropback"] == 1].copy()
    
    # Group by passer and season
    qb_eff = pbp_qbs.groupby(["passer_player_id", "season"]).agg({
        "epa": "mean",
        "cpoe": "mean",
        "qb_dropback": "sum",
        "pass_attempt": "sum"
    }).reset_index()
    
    qb_eff.columns = ["player_id", "feature_season", "epa_per_dropback", "cpoe", "dropback_count", "pass_attempts"]
    qb_eff["dakota"] = (qb_eff["epa_per_dropback"] * 0.7) + ((qb_eff["cpoe"] / 100.0) * 0.3)
    
    # Merge QB stats only for QBs
    df = df.merge(qb_eff, on=["player_id", "feature_season"], how="left")
    # Mask efficiency for non-QBs to prevent leakage (Audit Blocker 1 requirement)
    qb_cols = ["epa_per_dropback", "cpoe", "dakota", "dropback_count", "pass_attempts"]
    df.loc[df["position"] != "QB", qb_cols] = np.nan

    # 6. Route Metrics (Audit Blocker 2)
    print("Calculating route metrics (YPRR, TPRR)...")
    valid_part_seasons = [s for s in SEASONS if s >= 2019]
    part = _to_pandas(nfl.load_participation(valid_part_seasons))
    
    # Merge PBP with participation
    # Filter PBP to pass plays
    pass_plays = pbp[(pbp["pass_attempt"] == 1) | (pbp["qb_dropback"] == 1)].copy()
    pass_plays = pass_plays.merge(part[["nflverse_game_id", "play_id", "offense_players"]], 
                                  left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "play_id"], how="inner")
    
    # Team pass attempts for denominator (possible routes)
    # Using 'posteam' from PBP as 'team'
    team_pass_att = pass_plays.groupby(["posteam", "season"]).size().reset_index(name="team_pass_attempts_routes")
    team_pass_att.rename(columns={"posteam": "team"}, inplace=True)
    
    # Explode players
    pass_plays["offense_players"] = pass_plays["offense_players"].str.split(";")
    exploded = pass_plays.explode("offense_players")
    exploded = exploded.rename(columns={"offense_players": "player_id", "season": "feature_season"})
    
    # Aggregate routes
    routes = exploded.groupby(["player_id", "feature_season"]).size().reset_index(name="routes_run")
    
    df = df.merge(routes, on=["player_id", "feature_season"], how="left")
    df = df.merge(team_pass_att.rename(columns={"season": "feature_season"}), on=["team", "feature_season"], how="left")
    
    df["route_participation"] = df["routes_run"] / df["team_pass_attempts_routes"].replace(0, np.nan)
    df["yprr"] = df["yards_t"] / df["routes_run"].replace(0, np.nan)
    df["tprr"] = df["targets_t"] / df["routes_run"].replace(0, np.nan)

    # 7. Multi-Year Trends (Audit Warning 1)
    print("Building multi-year trends and indicators...")
    trend_base = df[["player_id", "feature_season", "ppg_t", "snap_share"]].drop_duplicates(subset=["player_id", "feature_season"])
    
    df_t1 = trend_base.copy()
    df_t1["feature_season"] = df_t1["feature_season"] + 1
    df_t1.columns = ["player_id", "feature_season", "ppg_t_minus_1", "snap_share_t_minus_1"]
    
    df_t2 = trend_base[["player_id", "feature_season", "ppg_t"]].copy()
    df_t2["feature_season"] = df_t2["feature_season"] + 2
    df_t2.columns = ["player_id", "feature_season", "ppg_t_minus_2"]
    
    df = df.merge(df_t1, on=["player_id", "feature_season"], how="left")
    df = df.merge(df_t2, on=["player_id", "feature_season"], how="left")
    
    df["ppg_t_minus_1_available"] = df["ppg_t_minus_1"].notna()
    df["ppg_t_minus_2_available"] = df["ppg_t_minus_2"].notna()

    # 8. QB Archetype
    print("Classifying QB archetypes...")
    rushing_hist = df[["player_id", "feature_season", "rushing_yards_t"]].copy()
    r_t1 = rushing_hist.rename(columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_1"})
    r_t1["join_season"] = r_t1["join_season"] + 1
    r_t2 = rushing_hist.rename(columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_2"})
    r_t2["join_season"] = r_t2["join_season"] + 2
    
    df = df.merge(r_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    df = df.merge(r_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    
    df["is_dual_threat"] = (
        (df["rushing_yards_t"] > DUAL_THREAT_RUSHING_THRESHOLD) | 
        (df["rushing_t_minus_1"] > DUAL_THREAT_RUSHING_THRESHOLD) | 
        (df["rushing_t_minus_2"] > DUAL_THREAT_RUSHING_THRESHOLD)
    ).fillna(False)
    
    # 9. Aging Curves (Audit Blocker 4)
    print("Applying aging curves and logging positions...")
    def get_curve_details(row):
        pos = row["position"]
        if pos == "QB":
            pos = "QB_dual_threat" if row["is_dual_threat"] else "QB_pocket"
        try:
            return aging_curve_value(pos, row["age"]), pos
        except:
            return 1.0, pos
            
    curve_results = df.apply(get_curve_details, axis=1)
    df["aging_curve_value"] = [r[0] for r in curve_results]
    df["aging_curve_position"] = [r[1] for r in curve_results]
    
    # 10. Outcome Calculation (Audit Blocker 3)
    print("Calculating outcomes and training eligibility...")
    outcomes = df[["player_id", "feature_season", "ppg_t", "games_t"]].copy()
    o_t1 = outcomes.rename(columns={"feature_season": "join_season", "ppg_t": "ppg_t1", "games_t": "games_t1"})
    o_t1["join_season"] = o_t1["join_season"] - 1
    o_t2 = outcomes.rename(columns={"feature_season": "join_season", "ppg_t": "ppg_t2", "games_t": "games_t2"})
    o_t2["join_season"] = o_t2["join_season"] - 2
    
    df = df.merge(o_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    df = df.merge(o_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    
    def calc_avg(row):
        pts = []
        if row["games_t1"] > 0: pts.append(row["ppg_t1"])
        if row["games_t2"] > 0: pts.append(row["ppg_t2"])
        return np.mean(pts) if pts else np.nan
        
    df[OUTCOME_COLUMN] = df.apply(calc_avg, axis=1)
    
    # Eligibility logic: must have complete 2-year window (unless inactive, but 2026 is unknown)
    # feature_season 2024 needs T+2=2026 which is unknown.
    df["training_eligible"] = df["feature_season"] < 2024
    # Also drop rows with no outcome data at all
    df = df.dropna(subset=[OUTCOME_COLUMN]).copy()
    
    # 11. Final Verification and Saving
    allowed = list(ENGINE_B_ALLOWED_FEATURES) + [OUTCOME_COLUMN, "training_eligible", "ppg_t_minus_1_available", "ppg_t_minus_2_available"]
    for col in allowed:
        if col not in df.columns:
            df[col] = np.nan
            
    df_final = df[allowed].copy()
    
    print("Verifying governance contract...")
    feature_cols = [c for c in df_final.columns if c != OUTCOME_COLUMN and c != "training_eligible"]
    validate_no_temporal_leakage(feature_cols)
    validate_no_prohibited_features(feature_cols)
    
    print(f"Saving {len(df_final)} rows to {OUTPUT_PATH}...")
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
