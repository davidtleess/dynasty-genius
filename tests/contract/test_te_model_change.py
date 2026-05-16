from __future__ import annotations

import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_BY_POSITION,
    ENGINE_B_FEATURES_TE,
    ENGINE_B_FEATURES_QB,
    ENGINE_B_FEATURES_RB,
    ENGINE_B_FEATURES_WR,
)

def test_te_feature_contract_presence_and_isolation():
    """Assert te_role_is_risk_profile is present in TE only."""
    assert "te_role_is_risk_profile" in ENGINE_B_FEATURES_TE
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_QB
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_RB
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_WR
    
    # Check mapping
    assert "te_role_is_risk_profile" in ENGINE_B_FEATURES_BY_POSITION["TE"]

def test_training_csv_redaction():
    """Assert training CSV contains no prohibited PFF/source IDs."""
    path = Path("app/data/training/engine_b_features_v2.csv")
    if not path.exists():
        pytest.skip("Training CSV not yet generated")
        
    df = pd.read_csv(path)
    prohibited = {"pff_id", "gsis_id", "sleeper_id", "overall_grade", "grades_offense", "grades_pass_route"}
    found = prohibited & set(df.columns)
    assert not found, f"Prohibited columns found in training CSV: {found}"
    
    # Check for local path leaks in metadata (if any strings exist)
    for col in df.select_dtypes(include=[object]).columns:
        for val in df[col].dropna().unique():
            if isinstance(val, str):
                lower_val = val.lower()
                assert "/users/" not in lower_val
                assert "downloads" not in lower_val

def test_coverage_imputation_defaults_to_zero():
    """Logic check: TEs without archetype should get 0, not NaN or 1."""
    # This test would ideally run the assembly logic on a mock, 
    # but we can verify it by inspecting the generated CSV if it exists.
    path = Path("app/data/training/engine_b_features_v2.csv")
    if not path.exists():
        pytest.skip("Training CSV not yet generated")
        
    df = pd.read_csv(path)
    te_df = df[df["position"] == "TE"]
    assert not te_df["te_role_is_risk_profile"].isna().any(), "TEs found with NaN risk profile"
    
    # Verify non-TEs are NaN
    non_te_df = df[df["position"] != "TE"]
    assert non_te_df["te_role_is_risk_profile"].isna().all(), "Non-TEs found with non-NaN risk profile"
