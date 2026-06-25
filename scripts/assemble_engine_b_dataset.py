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

import json
import sys
import warnings
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Filter warnings for cleaner output
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.dynasty_genius.audit.te_archetype_taxonomy import (
    derive_te_taxonomy_features,  # noqa: E402
)
from src.dynasty_genius.features.feature_assembly import (
    build_engine_b_features,  # noqa: E402
)
from src.dynasty_genius.models.engine_b_contract import (
    OUTCOME_COLUMN,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
)

OUTPUT_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
TE_ARCHETYPE_RUBRIC_PATH = ROOT / "app" / "data" / "identity" / "te_archetype_rubric_20260516.json"
TE_ELIGIBLE_MANIFEST_PATH = ROOT / "app" / "data" / "identity" / "pff_te_eligible_te_2018_2025_20260516_canonical.json"
SEASONS = list(range(2018, 2026)) # 2018 to 2025 features + outcomes

# Minimal games to reduce noise (Audit Warning 2)
MIN_GAMES_THRESHOLD = 4

ENGINE_B_OUTPUT_COLUMNS = (
    "snap_share_t_minus_1",
    "cpoe",
    "player_id",
    "route_participation",
    "aging_curve_position",
    "ppg_t",
    "depth_chart_position",
    "tprr",
    "total_points_t",
    "ppg_t_minus_2",
    "dakota",
    "air_yards_share",
    "aging_curve_value",
    "target_share_nfl",
    "yprr",
    "epa_per_dropback",
    "dropback_count",
    "team",
    "feature_season",
    "weighted_opportunity",
    "age",
    "is_dual_threat",
    "ppg_t_minus_1",
    "pass_attempts",
    "snap_share",
    "games_t",
    "position",
    OUTCOME_COLUMN,
    "training_eligible",
    "ppg_t_minus_1_available",
    "ppg_t_minus_2_available",
    "snap_share_t_minus_1_available",
    "te_role_is_risk_profile",
)

def _to_pandas(df: Any) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    return pd.DataFrame(df)


def add_te_role_risk_feature(
    df: pd.DataFrame,
    rubric_data: dict[str, Any],
    eligible_data: dict[str, Any],
) -> pd.DataFrame:
    """Add TE-only binary risk profile from the committed redacted rubric artifact.

    Training rows use GSIS `player_id`; the TE rubric is keyed by canonical DG
    player_id. The eligible manifest supplies the deterministic bridge. Missing
    TE labels default to 0 because absence of archetype evidence is not evidence
    of risk. Non-TE rows remain null so the field cannot leak into other models.
    """
    result = df.copy()
    canonical_by_gsis = {
        str(row["gsis_id"]): str(row["player_id"])
        for row in eligible_data.get("eligible", [])
        if row.get("gsis_id") and row.get("player_id")
    }
    risk_by_canonical: dict[str, int] = {}
    for canonical_id, row in rubric_data.get("players", {}).items():
        features = derive_te_taxonomy_features(row)
        role = features.get("fantasy_role_archetype")
        risk_by_canonical[str(canonical_id)] = int(
            role in {"role_risk", "blocking_specialist"}
        )

    def _row_value(row: pd.Series) -> float:
        if row.get("position") != "TE":
            return np.nan
        canonical_id = canonical_by_gsis.get(str(row.get("player_id")))
        if not canonical_id:
            return 0.0
        return float(risk_by_canonical.get(canonical_id, 0))

    result["te_role_is_risk_profile"] = result.apply(_row_value, axis=1)
    return result


def add_te_role_risk_feature_from_files(df: pd.DataFrame) -> pd.DataFrame:
    if not TE_ARCHETYPE_RUBRIC_PATH.exists() or not TE_ELIGIBLE_MANIFEST_PATH.exists():
        result = df.copy()
        result["te_role_is_risk_profile"] = np.nan
        result.loc[result["position"] == "TE", "te_role_is_risk_profile"] = 0.0
        return result

    rubric_data = json.loads(TE_ARCHETYPE_RUBRIC_PATH.read_text(encoding="utf-8"))
    eligible_data = json.loads(TE_ELIGIBLE_MANIFEST_PATH.read_text(encoding="utf-8"))
    return add_te_role_risk_feature(df, rubric_data, eligible_data)

def fetch_and_agg_stats(seasons: list[int], weekly: pd.DataFrame | None = None) -> pd.DataFrame:
    # `weekly` lets a caller inject the player-stats frame (frame-injectable feature
    # assembly / tests); when None, load it from nflreadpy as before.
    if weekly is not None:
        stats_weekly = _to_pandas(weekly)
    else:
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
    # The 11-step feature engineering now lives in
    # feature_assembly.build_engine_b_features (frame-injectable). It applies the shared
    # inference_season_rule and backs feature_assembly.assemble_feature_candidate (the
    # F-feature-refresh seam). This script is the production LOADER: pull the source
    # frames from nflreadpy and delegate the engineering to the shared builder.
    valid_part_seasons = [s for s in SEASONS if s >= 2019]
    read_fns = {
        "player_stats": _to_pandas(nfl.load_player_stats(SEASONS)),
        "rosters": _to_pandas(nfl.load_rosters(SEASONS)),
        "snap_counts": _to_pandas(nfl.load_snap_counts(SEASONS)),
        "pbp": _to_pandas(nfl.load_pbp(SEASONS)),
        "participation": _to_pandas(nfl.load_participation(valid_part_seasons)),
    }
    df_final = build_engine_b_features(read_fns=read_fns, seasons_window=SEASONS)

    print("Verifying governance contract...")
    feature_cols = [c for c in df_final.columns if c != OUTCOME_COLUMN and c != "training_eligible"]
    validate_no_temporal_leakage(feature_cols)
    validate_no_prohibited_features(feature_cols)

    print(f"Saving {len(df_final)} rows to {OUTPUT_PATH}...")
    df_final.to_csv(OUTPUT_PATH, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
