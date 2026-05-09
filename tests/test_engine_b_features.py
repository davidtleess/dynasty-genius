import pytest
import pandas as pd
from pathlib import Path
from src.dynasty_genius.pipelines.engine_b_features import build_engine_b_features

def test_engine_b_feature_mapping():
    base_dir = Path(__file__).resolve().parents[1]
    raw_path = base_dir / "resources" / "pff_mock"
    identity_path = base_dir / "resources" / "mock_playerprofiler_identity.json"
    
    assert raw_path.exists(), "PFF mock path should exist"
    assert identity_path.exists(), "Identity mock path should exist"
    
    df = build_engine_b_features(str(raw_path), str(identity_path))
    
    # Check shape and essential columns
    assert not df.empty
    assert "dg_id" in df.columns
    assert "snap_share" in df.columns
    assert "target_share" in df.columns
    assert "yards_per_route_run" in df.columns
    
    # Check specific player (Puka Nacua)
    puka = df[df["dg_id"] == "puka_nacua_wr_2001"].iloc[0]
    assert puka["snap_share"] > 0.9
    assert puka["target_share"] > 0.2
    assert puka["yards_per_route_run"] > 2.5
    
    # Check specific player (CMC)
    cmc = df[df["dg_id"] == "christian_mccaffrey_rb_1996"].iloc[0]
    assert cmc["snap_share"] > 0.9
    assert cmc["breakaway_run_pct"] > 0.05
    assert cmc["run_blocking_grade"] > 70


def test_engine_b_feature_mapping_handles_missing_optional_feeds(tmp_path):
    base_dir = Path(__file__).resolve().parents[1]
    identity_path = base_dir / "resources" / "mock_playerprofiler_identity.json"

    df = build_engine_b_features(str(tmp_path), str(identity_path))

    assert df.empty
    assert list(df.columns) == [
        "dg_id", "player_id", "player_name", "position", "team", "season",
        "snap_share", "target_share", "yards_per_route_run",
        "breakaway_run_pct", "run_blocking_grade"
    ]
