#!/usr/bin/env python3
"""Engine B Dataset Assembly (Task 5.1).

Aggregates NFL player-season features for Seasons T, T-1, T-2
and maps to 2-year average PPG outcome (T+1, T+2).
Enforces Engine B contract and leakage guards.
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

OUTPUT_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v1.csv"
SEASONS = list(range(2018, 2026)) # 2018 to 2025 features + outcomes

def _to_pandas(df: Any) -> pd.DataFrame:
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
        "receiving_air_yards": "sum", # nflreadpy uses receiving_air_yards
        "week": "nunique"
    }
    
    # Add QB specific stats if columns exist
    for col in ["passing_epa", "passing_cpoe", "attempts"]:
        if col in stats_weekly.columns:
            agg_map[col] = "mean" if "epa" in col or "cpoe" in col else "sum"

    stats_seasonal = stats_weekly.groupby(["player_id", "season", "position"]).agg(agg_map).reset_index()
    
    # Flatten columns
    stats_seasonal.columns = [
        "player_id", "season", "position", 
        "total_points_t", "ppg_t", "targets_t", "receptions_t",
        "yards_t", "rushing_yards_t", "rushing_tds_t", "air_yards_t", "games_t",
        "epa_t", "cpoe_t", "attempts_t"
    ]
    
    # Team Aggregates for Shares
    team_stats = stats_weekly.groupby(["team", "season"]).agg({
        "targets": "sum",
        "receiving_air_yards": "sum",
        "receiving_yards": "sum",
        "attempts": "sum"
    }).reset_index()
    team_stats.columns = ["team", "season", "team_targets", "team_air_yards", "team_yards", "team_pass_att"]
    
    # Get team for each player-season (most frequent team)
    player_team = stats_weekly.groupby(["player_id", "season"])["team"].agg(lambda x: x.mode().iloc[0]).reset_index()
    
    stats_seasonal = stats_seasonal.merge(player_team, on=["player_id", "season"], how="left")
    stats_seasonal = stats_seasonal.merge(team_stats, on=["team", "season"], how="left")
    
    # Derived Features
    stats_seasonal["target_share_nfl"] = stats_seasonal["targets_t"] / stats_seasonal["team_targets"].replace(0, np.nan)
    stats_seasonal["air_yards_share"] = stats_seasonal["air_yards_t"] / stats_seasonal["team_air_yards"].replace(0, np.nan)
    stats_seasonal["weighted_opportunity"] = (1.5 * stats_seasonal["target_share_nfl"].fillna(0)) + (0.7 * stats_seasonal["air_yards_share"].fillna(0))
    
    return stats_seasonal

def fetch_and_agg_participation(seasons: list[int]) -> pd.DataFrame:
    print(f"Loading snap counts for {seasons}...")
    # load_snap_counts is usually faster and more reliable for snap share than play-by-play
    snaps = _to_pandas(nfl.load_snap_counts(seasons))
    
    # Aggregation
    snaps_seasonal = snaps.groupby(["pfr_player_id", "season"]).agg({
        "offense_pct": "mean"
    }).reset_index()
    snaps_seasonal.rename(columns={"offense_pct": "snap_share"}, inplace=True)
    
    # Need to bridge pfr_player_id to player_id (gsis)
    # nflreadpy load_rosters has both
    rosters = _to_pandas(nfl.load_rosters(seasons))
    crosswalk = rosters[["gsis_id", "pfr_id"]].dropna().drop_duplicates()
    
    snaps_seasonal = snaps_seasonal.merge(crosswalk, left_on="pfr_player_id", right_on="pfr_id", how="inner")
    snaps_seasonal.rename(columns={"gsis_id": "player_id"}, inplace=True)
    
    return snaps_seasonal[["player_id", "season", "snap_share"]]

def main():
    print("Starting Dataset Assembly...")
    
    # 1. Stats and Demographics
    df = fetch_and_agg_stats(SEASONS)
    print(f"Aggregated stats size: {len(df)}")
    
    # 2. Snaps
    snaps = fetch_and_agg_participation(SEASONS)
    print(f"Aggregated snaps size: {len(snaps)}")
    df = df.merge(snaps, on=["player_id", "season"], how="left")
    df.rename(columns={"season": "feature_season"}, inplace=True)
    
    # 3. Add Roster Info (Age, Depth Chart)
    print("Adding roster details...")
    rosters_raw = _to_pandas(nfl.load_rosters(SEASONS))
    
    # Group rosters to 1 row per (gsis_id, season)
    rosters_agg = rosters_raw.groupby(["gsis_id", "season"]).agg({
        "birth_date": "first",
        "depth_chart_position": lambda x: x.mode().iloc[0] if not x.mode().empty else None
    }).reset_index()
    
    # Calculate Age: season - birth_year
    rosters_agg["birth_year"] = pd.to_datetime(rosters_agg["birth_date"], errors="coerce").dt.year
    rosters_agg["age"] = rosters_agg["season"] - rosters_agg["birth_year"]
    
    df = df.merge(rosters_agg[["gsis_id", "season", "age", "depth_chart_position"]], 
                  left_on=["player_id", "feature_season"], right_on=["gsis_id", "season"], how="left").drop(columns="season")
    
    print(f"Post-roster join size: {len(df)}")
    
    # 4. Multi-Year Trends (T-1, T-2)
    print("Building multi-year trends...")
    # Unique (player_id, feature_season) for trends
    trend_base = df[["player_id", "feature_season", "ppg_t", "snap_share"]].drop_duplicates(subset=["player_id", "feature_season"])
    
    df_t1 = trend_base.copy()
    df_t1["feature_season"] = df_t1["feature_season"] + 1
    df_t1.columns = ["player_id", "feature_season", "ppg_t_minus_1", "snap_share_t_minus_1"]
    
    df_t2 = trend_base[["player_id", "feature_season", "ppg_t"]].copy()
    df_t2["feature_season"] = df_t2["feature_season"] + 2
    df_t2.columns = ["player_id", "feature_season", "ppg_t_minus_2"]
    
    df = df.merge(df_t1, on=["player_id", "feature_season"], how="left")
    df = df.merge(df_t2, on=["player_id", "feature_season"], how="left")
    
    print(f"Post-trend join size: {len(df)}")
    
    # 5. QB Archetype
    print("Classifying QB archetypes...")
    # is_dual_threat if rushing yards > 400 in any of T-2 to T
    # Join historical rushing yards
    rushing_hist = df[["player_id", "feature_season", "rushing_yards_t"]].copy()
    
    rushing_t1 = rushing_hist.rename(columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_1"})
    rushing_t1["join_season"] = rushing_t1["join_season"] + 1
    
    rushing_t2 = rushing_hist.rename(columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_2"})
    rushing_t2["join_season"] = rushing_t2["join_season"] + 2
    
    df = df.merge(rushing_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    df = df.merge(rushing_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    
    df["is_dual_threat"] = (
        (df["rushing_yards_t"] > DUAL_THREAT_RUSHING_THRESHOLD) | 
        (df["rushing_t_minus_1"] > DUAL_THREAT_RUSHING_THRESHOLD) | 
        (df["rushing_t_minus_2"] > DUAL_THREAT_RUSHING_THRESHOLD)
    ).fillna(False)
    
    # 6. Aging Curves
    print("Applying aging curves...")
    def get_curve(row):
        pos = row["position"]
        if pos == "QB":
            pos = "QB_dual_threat" if row["is_dual_threat"] else "QB_pocket"
        try:
            return aging_curve_value(pos, row["age"])
        except:
            return 1.0
            
    df["aging_curve_value"] = df.apply(get_curve, axis=1)
    
    # 7. Outcome Calculation (T+1, T+2)
    print("Calculating outcomes...")
    outcomes = df[["player_id", "feature_season", "ppg_t", "games_t"]].copy()
    
    # Join T+1
    outcomes_t1 = outcomes.rename(columns={"feature_season": "join_season", "ppg_t": "ppg_t1", "games_t": "games_t1"})
    outcomes_t1["join_season"] = outcomes_t1["join_season"] - 1
    
    # Join T+2
    outcomes_t2 = outcomes.rename(columns={"feature_season": "join_season", "ppg_t": "ppg_t2", "games_t": "games_t2"})
    outcomes_t2["join_season"] = outcomes_t2["join_season"] - 2
    
    df = df.merge(outcomes_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    df = df.merge(outcomes_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left").drop(columns="join_season")
    
    # Outcome Average (Exclude Inactive Seasons)
    def calc_avg(row):
        pts = []
        if row["games_t1"] > 0: pts.append(row["ppg_t1"])
        if row["games_t2"] > 0: pts.append(row["ppg_t2"])
        return np.mean(pts) if pts else np.nan
        
    df[OUTCOME_COLUMN] = df.apply(calc_avg, axis=1)
    
    # Drop rows with no outcome
    df_training = df.dropna(subset=[OUTCOME_COLUMN]).copy()
    
    # 8. Final Feature Selection and Validation
    # Map raw names to contract names
    # Note: epa_t -> epa_per_dropback, etc.
    final_rename = {
        "epa_t": "epa_per_dropback",
        "cpoe_t": "cpoe",
        "attempts_t": "pass_attempts",
    }
    df_training.rename(columns=final_rename, inplace=True)
    
    # Filter to allowed columns
    allowed = list(ENGINE_B_ALLOWED_FEATURES) + [OUTCOME_COLUMN]
    # Ensure all exist
    for col in allowed:
        if col not in df_training.columns:
            df_training[col] = np.nan
            
    df_final = df_training[allowed].copy()
    
    # Governance Check
    print("Verifying governance contract...")
    feature_cols = [c for c in df_final.columns if c != OUTCOME_COLUMN]
    validate_no_temporal_leakage(feature_cols)
    validate_no_prohibited_features(feature_cols)
    
    # Save
    print(f"Saving {len(df_final)} rows to {OUTPUT_PATH}...")
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
