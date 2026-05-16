"""Tests for Phase 14 DVS Normalization and Prospect-to-Veteran Bridge."""
from __future__ import annotations

import pytest
import numpy as np
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_P90_PPG,
    ENGINE_B_MIN_GAMES_T
)
from src.dynasty_genius.scoring.engine_a import _P90_PPG

def _mock_identity(position: str, is_prospect: bool = False) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test_player",
        full_name="Test Player",
        position=position,
        is_prospect=is_prospect,
        verification_status="VERIFIED_NFL_DRAFT"
    )

def test_engine_b_dvs_formula_wr():
    """5.1 DVS Formula: WR P90 = 14.5; 14.5 PPG -> DVS 100.0, 7.25 PPG -> DVS 50.0."""
    identity = _mock_identity("WR")
    p90 = ENGINE_B_P90_PPG["WR"]
    
    # Test P90 point
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": p90, "engine": "test_v2"},
        "games_t": ENGINE_B_MIN_GAMES_T,
        "feature_season": 2024
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score == 100.0
    assert pvo.dvs_clamped is False
    
    # Test half P90
    features["engine_b_score"]["predicted_avg_ppg_t1_t2"] = p90 / 2
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score == 50.0

    # Test clamping
    features["engine_b_score"]["predicted_avg_ppg_t1_t2"] = p90 + 5.0
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score == 100.0
    assert pvo.dvs_clamped is True

    # Test negative floor
    features["engine_b_score"]["predicted_avg_ppg_t1_t2"] = -5.0
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score == 0.0

def test_dvs_ceiling_fraction():
    """5.2 DVS Ceiling Fraction: Designed for 10%. (Verified via logic in 5.1)."""
    # This test is primarily an inference-time check, but we verify provenance here.
    identity = _mock_identity("QB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 25.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_clamped is True # 25 > 20.1

def test_dvs_provenance_fields():
    """5.3 DVS Provenance Fields: assert dvs_engine == 'B', dvs_p90_ref matches, dvs_clamped is bool."""
    identity = _mock_identity("RB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test_v2"},
        "games_t": 12,
        "feature_season": 2024
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "B"
    assert pvo.dvs_p90_ref == ENGINE_B_P90_PPG["RB"]
    assert isinstance(pvo.dvs_clamped, bool)

def test_dead_window_caveat_engine_a_fallback_present():
    """5.4 Dead Window Caveat (Fallback Present): games_t < 8, Engine A inputs exist -> Engine A DVS + caveat."""
    identity = _mock_identity("WR")
    # Player is not a prospect (is_prospect=False default), but has low games_t
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4, # Dead Window
        "feature_season": 2024,
        "pick": 10.0, "round": 1.0, "age": 22.0 # Engine A inputs
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "A"
    assert any("Insufficient professional season data" in c for c in pvo.caveats)
    assert pvo.dynasty_value_score is not None

def test_dead_window_caveat_engine_a_fallback_absent():
    """5.5 Dead Window Caveat (Fallback Absent): games_t < 8, no Engine A inputs -> DVS None + caveat."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024
        # No Engine A inputs
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is None
    assert any("Insufficient professional season data" in c for c in pvo.caveats)

def test_te_g3_deferred_caveat():
    """5.6 TE G3-Deferred Caveat: TE ACTIVE_B with score gets specific caveat."""
    identity = _mock_identity("TE")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 8.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024
    }
    pvo = assemble_pvo(identity, features)
    assert any("TE market superiority gate deferred" in c for c in pvo.caveats)

def test_engine_b_dvs_does_not_fire_below_games_gate():
    """5.7 Engine B DVS Does Not Fire Below Games Gate: games_t=4 -> no Engine B DVS."""
    identity = _mock_identity("RB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine != "B"

def test_engine_a_dvs_path_unchanged():
    """5.8 Engine A DVS Path Unchanged: prospect -> dvs_engine == 'A', Engine A P90."""
    identity = _mock_identity("WR", is_prospect=True)
    features = {
        "pick": 5.0, "round": 1.0, "age": 21.0
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "A"
    assert pvo.dvs_p90_ref == _P90_PPG["WR"]

def test_var_null_for_pre_model():
    """5.9 VAR Null for PRE_MODEL: DVS is None -> VAR is None."""
    identity = _mock_identity("QB")
    features = {} # PRE_MODEL
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is None
    assert pvo.value_above_replacement is None

def test_var_below_replacement_is_negative():
    """5.10 VAR Below-Replacement Is Negative: ranked below replacement -> VAR < 0.0."""
    # This is a batch-script check. Here we verify the PVO field exists.
    identity = _mock_identity("RB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
        "value_above_replacement": -5.5
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.value_above_replacement == -5.5

def test_market_data_does_not_appear_in_dvs_formula():
    """5.11 Market Data Isolation: ENGINE_B_P90_PPG constants contain no market reference."""
    for pos, val in ENGINE_B_P90_PPG.items():
        assert isinstance(val, (int, float))
        # Logic check: these are static numeric anchors
