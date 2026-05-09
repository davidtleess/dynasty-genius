"""Engine B Feature Mapping: Map PFF usage signals to Player Value Object (PVO) structure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from src.dynasty_genius.identity import IdentityResolver, generate_dg_id
from src.dynasty_genius.models.player_identity import PlayerIdentity


PLAYER_KEY_COLUMNS = ["season", "player_id", "player_name", "position", "team"]


def load_identities(mock_path: Path) -> IdentityResolver:
    """Load player identities from mock file for resolution."""
    if not mock_path.exists():
        raise FileNotFoundError(f"Identity mock not found at {mock_path}")
    
    with open(mock_path, "r") as f:
        raw = json.load(f)
        
    identities = [
        PlayerIdentity(
            dg_id=generate_dg_id(p["full_name"], p["position"], p.get("birth_year")),
            full_name=p["full_name"],
            position=p["position"],
            birth_date=p.get("birth_date"),
            nfl_team=p.get("nfl_team"),
            jersey_number=p.get("jersey_number"),
            sleeper_id=p.get("sleeper_id"),
            pff_id=p.get("pff_id"),
            pfr_id=p.get("pfr_id"),
            playerprofiler_id=p.get("playerprofiler_id"),
        )
        for p in raw["players"]
    ]
    return IdentityResolver(identities)


def build_engine_b_features(
    raw_base_path: str,
    identity_mock_path: str,
) -> pd.DataFrame:
    """
    Build Engine B features locally using Pandas.
    Maps SNAP_SHARE, TARGET_SHARE, and YPRR to feature structure anchored by dg_id.
    """
    base = Path(raw_base_path)
    resolver = load_identities(Path(identity_mock_path))
    
    # Load raw mock data
    receiving_path = base / "receiving" / "data.json"
    rushing_path = base / "rushing" / "data.json"
    snaps_path = base / "snaps" / "data.json"
    blocking_path = base / "team_blocking" / "data.json"
    
    receiving_df = pd.read_json(receiving_path) if receiving_path.exists() else pd.DataFrame()
    rushing_df = pd.read_json(rushing_path) if rushing_path.exists() else pd.DataFrame()
    snaps_df = pd.read_json(snaps_path) if snaps_path.exists() else pd.DataFrame()
    blocking_df = pd.read_json(blocking_path) if blocking_path.exists() else pd.DataFrame()
    
    # 1. Weekly to Season Aggregation
    # Receiving: routes_run, receiving_yards, targets, team_targets
    if not receiving_df.empty:
        rec_season = receiving_df.groupby(["season", "player_id", "player_name", "position", "team"]).agg({
            "routes_run": "sum",
            "receiving_yards": "sum",
            "targets": "sum",
            "team_targets": "sum"
        }).reset_index()
        
        rec_season["yards_per_route_run"] = rec_season["receiving_yards"] / rec_season["routes_run"].replace(0, pd.NA)
        rec_season["target_share"] = rec_season["targets"] / rec_season["team_targets"].replace(0, pd.NA)
    else:
        rec_season = pd.DataFrame(
            columns=PLAYER_KEY_COLUMNS + ["yards_per_route_run", "target_share"]
        )
        
    # Rushing: rush_attempts, breakaway_runs, targets, team_targets
    if not rushing_df.empty:
        rush_season = rushing_df.groupby(["season", "player_id", "player_name", "position", "team"]).agg({
            "rush_attempts": "sum",
            "breakaway_runs": "sum",
            "targets": "sum",
            "team_targets": "sum"
        }).reset_index()
        
        rush_season["breakaway_run_pct"] = rush_season["breakaway_runs"] / rush_season["rush_attempts"].replace(0, pd.NA)
        rush_season["target_share"] = rush_season["targets"] / rush_season["team_targets"].replace(0, pd.NA)
    else:
        rush_season = pd.DataFrame(
            columns=PLAYER_KEY_COLUMNS + ["breakaway_run_pct", "target_share"]
        )
        
    # Snaps: offensive_snaps, team_offensive_snaps
    if not snaps_df.empty:
        snap_season = snaps_df.groupby(["season", "player_id", "player_name", "position", "team"]).agg({
            "offensive_snaps": "sum",
            "team_offensive_snaps": "sum"
        }).reset_index()
        
        snap_season["snap_share"] = snap_season["offensive_snaps"] / snap_season["team_offensive_snaps"].replace(0, pd.NA)
    else:
        snap_season = pd.DataFrame(columns=PLAYER_KEY_COLUMNS + ["snap_share"])
        
    # Blocking
    if not blocking_df.empty:
        block_season = blocking_df.groupby(["season", "team"]).agg({
            "run_blocking_grade": "mean"
        }).reset_index()
    else:
        block_season = pd.DataFrame(columns=["season", "team", "run_blocking_grade"])

    # 2. Join Features
    # Start with all unique (season, player_id) combinations from all sources
    all_players = pd.concat(
        [
            rec_season[PLAYER_KEY_COLUMNS],
            rush_season[PLAYER_KEY_COLUMNS],
            snap_season[PLAYER_KEY_COLUMNS],
        ]
    ).drop_duplicates(["season", "player_id"])

    if all_players.empty:
        return pd.DataFrame(
            columns=[
                "dg_id", "player_id", "player_name", "position", "team", "season",
                "snap_share", "target_share", "yards_per_route_run",
                "breakaway_run_pct", "run_blocking_grade"
            ]
        )
    
    features = all_players.merge(
        rec_season[["season", "player_id", "yards_per_route_run", "target_share"]],
        on=["season", "player_id"], how="left"
    )
    
    # Merge rush features, combining target_share if it exists in both
    features = features.merge(
        rush_season[["season", "player_id", "breakaway_run_pct", "target_share"]],
        on=["season", "player_id"], how="left", suffixes=("", "_rush")
    )
    
    if "target_share_rush" in features.columns:
        features["target_share"] = features["target_share"].fillna(features["target_share_rush"])
        features = features.drop(columns=["target_share_rush"])
        
    features = features.merge(
        snap_season[["season", "player_id", "snap_share"]],
        on=["season", "player_id"], how="left"
    )
    
    features = features.merge(
        block_season,
        on=["season", "team"], how="left"
    )
    
    # 3. Identity Linkage: Resolve pff_id to dg_id
    def resolve_to_dg_id(row):
        dg_id = resolver.resolve_pff_id(row["player_id"])
        if not dg_id:
            # Fallback to name resolution
            result = resolver.resolve_by_name(row["player_name"], row["position"], team=row["team"])
            if result and result.verification_status == "VERIFIED":
                return result.candidate_dg_id
        return dg_id

    features["dg_id"] = features.apply(resolve_to_dg_id, axis=1)
    
    # Filter to only resolved rows
    resolved_features = features[features["dg_id"].notnull()].copy()
    
    # Final column ordering and selection
    final_cols = [
        "dg_id", "player_id", "player_name", "position", "team", "season",
        "snap_share", "target_share", "yards_per_route_run",
        "breakaway_run_pct", "run_blocking_grade"
    ]
    
    # NOTE: Sleeper usage signals (like weekly targets/snaps) could be joined here 
    # if a Sleeper stats mock was provided. Current mapping prioritizes PFF as the 
    # Rank 1-2 quantitative source.
    
    return resolved_features[final_cols]


if __name__ == "__main__":
    # Local demo
    import os
    
    base_dir = Path(__file__).resolve().parents[3]
    raw_path = base_dir / "resources" / "pff_mock"
    identity_path = base_dir / "resources" / "mock_playerprofiler_identity.json"
    
    if raw_path.exists() and identity_path.exists():
        df = build_engine_b_features(str(raw_path), str(identity_path))
        print("\n--- Engine B Feature Mapping (Draft) ---")
        print(df.to_string(index=False))
    else:
        print(f"Required paths missing: {raw_path} or {identity_path}")
