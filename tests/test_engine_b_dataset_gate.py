"""Engine B Dataset Governance Gate.

Automates the audit checks requested by Claude to prevent regressions in Task 5.1.
Enforces data integrity for QB efficiency, route metrics, outcome completeness, and aging curves.
"""
from __future__ import annotations

import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_V2 = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"

@pytest.fixture
def df():
    if not DATASET_V2.exists():
        pytest.skip(f"Dataset {DATASET_V2} not found.")
    return pd.read_csv(DATASET_V2)

def test_qb_efficiency_metrics_populated(df):
    """BLOCKER 1: Verify QB efficiency is populated for QBs and masked for others."""
    qbs = df[df["position"] == "QB"]
    non_qbs = df[df["position"] != "QB"]
    
    eff_cols = ["epa_per_dropback", "cpoe", "dakota", "dropback_count"]
    
    for col in eff_cols:
        # At least some QBs should have data (not all, but most)
        # Note: EPA/CPOE might be null for very small samples even if games >= 4? 
        # But for 4+ games, they should have dropbacks.
        null_pct = qbs[col].isna().mean()
        assert null_pct < 0.2, f"Too many nulls in {col} for QBs: {null_pct:.1%}"
        
        # Non-QBs MUST be 100% null for these columns
        assert non_qbs[col].isna().all(), f"Leakage: Non-QBs have values in {col}"

def test_receiver_route_metrics_populated(df):
    """BLOCKER 2: Verify WR/TE route metrics are populated for 2019+."""
    # Note: 2018 will be null as participation data starts 2019
    receivers = df[(df["position"].isin(["WR", "TE"])) & (df["feature_season"] >= 2019)]
    
    route_cols = ["yprr", "tprr", "route_participation"]
    
    for col in route_cols:
        null_pct = receivers[col].isna().mean()
        assert null_pct < 0.2, f"Too many nulls in {col} for 2019+ receivers: {null_pct:.1%}"

def test_outcome_completeness_gate(df):
    """BLOCKER 3: Verify 2024 rows are not training_eligible."""
    rows_2024 = df[df["feature_season"] == 2024]
    assert not rows_2024["training_eligible"].any(), "2024 rows must not be training_eligible (missing T+2)."
    
    rows_pre_2024 = df[df["feature_season"] < 2024]
    assert rows_pre_2024["training_eligible"].all(), "Pre-2024 rows should be training_eligible."

def test_aging_curve_position_populated(df):
    """BLOCKER 4: Verify aging_curve_position is logged."""
    assert df["aging_curve_position"].notna().all(), "aging_curve_position contains nulls."
    
    # Check QB archetypes
    dual_threats = df[df["is_dual_threat"] == True]
    if not dual_threats.empty:
        assert (dual_threats[dual_threats["position"] == "QB"]["aging_curve_position"] == "QB_dual_threat").all()

def test_minimum_games_filter(df):
    """WARNING 2: Verify minimum games filter (>=4) is applied."""
    assert (df["games_t"] >= 4).all(), f"Dataset contains rows with < 4 games. Min found: {df['games_t'].min()}"

def test_historical_indicators_present(df):
    """WARNING 1: Verify historical ppg indicators exist."""
    assert "ppg_t_minus_1_available" in df.columns
    assert "ppg_t_minus_2_available" in df.columns

    # Check that they match the data
    assert (df["ppg_t_minus_1_available"] == df["ppg_t_minus_1"].notna()).all()


def test_qb_efficiency_internal_consistency(df):
    """No QB row may have epa_per_dropback present but cpoe or dakota null.

    EPA and CPOE come from the same PBP source join. If EPA resolved,
    CPOE must also resolve; if it didn't, the row is internally inconsistent
    and must be dropped rather than carried as partial signal.
    """
    qbs = df[df["position"] == "QB"]
    has_epa = qbs["epa_per_dropback"].notna()
    cpoe_null = qbs["cpoe"].isna()
    dakota_null = qbs["dakota"].isna()
    inconsistent = qbs[has_epa & (cpoe_null | dakota_null)]
    assert inconsistent.empty, (
        f"{len(inconsistent)} QB row(s) have EPA but missing CPOE/DAKOTA:\n"
        + inconsistent[["player_id", "feature_season", "epa_per_dropback", "cpoe", "dakota"]].to_string()
    )
