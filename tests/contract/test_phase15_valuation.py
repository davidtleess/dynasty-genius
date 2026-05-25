"""Tests for Phase 15 Cross-Positional Architecture and Bayesian Bridge."""
from __future__ import annotations

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_P90_PPG,
    ENGINE_B_REPLACEMENT_DVS,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _mock_identity(position: str, is_prospect: bool = False) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test_player",
        full_name="Test Player",
        position=position,
        is_prospect=is_prospect,
        verification_status="VERIFIED_NFL_DRAFT"
    )

def test_xvar_rank_preservation_within_position():
    """Task 1.3: Verify xVAR rank == DVS rank within position."""
    identity = _mock_identity("WR")
    p90 = ENGINE_B_P90_PPG["WR"]
    repl = ENGINE_B_REPLACEMENT_DVS["WR"]
    
    # Higher DVS must yield higher xVAR
    features_low = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024
    }
    features_high = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024
    }
    
    pvo_low = assemble_pvo(identity, features_low)
    pvo_high = assemble_pvo(identity, features_high)
    
    assert pvo_high.dynasty_value_score > pvo_low.dynasty_value_score
    assert pvo_high.xvar > pvo_low.xvar

def test_xvar_scarcity_multiplier():
    """Task 1.3: Verify QB scarcity multiplier (QB > WR at same DVS parity)."""
    # A QB at DVS 80 and a WR at DVS 80
    qb_identity = _mock_identity("QB")
    wr_identity = _mock_identity("WR")
    
    # Calculate PPG that gives exactly DVS 80
    qb_ppg = 0.80 * ENGINE_B_P90_PPG["QB"]
    wr_ppg = 0.80 * ENGINE_B_P90_PPG["WR"]
    
    features_qb = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": qb_ppg, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024
    }
    features_wr = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": wr_ppg, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024
    }
    
    pvo_qb = assemble_pvo(qb_identity, features_qb)
    pvo_wr = assemble_pvo(wr_identity, features_wr)
    
    assert pvo_qb.dynasty_value_score == 80.0
    assert pvo_wr.dynasty_value_score == 80.0
    
    # xVAR = (DVS - DVS_repl) * Λ
    # qb_xvar = (80 - 64.2) * 1.386 = 21.90
    # wr_xvar = (80 - 60.6) * 1.000 = 19.40
    assert pvo_qb.xvar > pvo_wr.xvar
    assert pvo_qb.xvar_anchor == "WR"

def test_bayesian_bridge_monotonicity():
    """Task 2.2: DVS moves smoothly as games_t increases from 1 to 8."""
    identity = _mock_identity("WR")
    # Low Engine A prior (50), High Engine B likelihood (90)
    features = {
        "pick": 50.0, "round": 3.0, "age": 22.0, # Yields approx DVS 50
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 13.0, "engine": "test_v2"}, # 13/14.5 -> DVS 89.7
        "feature_season": 2024
    }
    
    prev_dvs = 0.0
    for n in range(1, 9):
        features["games_t"] = n
        pvo = assemble_pvo(identity, features)
        dvs = pvo.dynasty_value_score
        assert dvs is not None
        if n > 1:
            assert dvs >= prev_dvs # Monotonicity toward Engine B
        prev_dvs = dvs
        
    # At game 8, Engine B becomes 100% weight in logic? 
    # No, w_B = n/(n+k). At game 8, w_B = 8/13 = 61.5% in the blend logic.
    # WAIT! My implementation of games_t < 8 uses blend. At games_t >= 8, it uses PURE Engine B.
    # So there is still a small jump at 8, but it's much smaller than the 0 -> 100 jump.
    # Actually, at game 7, weight is 7/12 = 58%.
    # Let's check the transition.
    features["games_t"] = 7
    dvs_7 = assemble_pvo(identity, features).dynasty_value_score
    features["games_t"] = 8
    dvs_8 = assemble_pvo(identity, features).dynasty_value_score
    # jump is (Pure B) - (58% B + 42% A) = 42% * (B - A)
    # Compared to original Phase 14 jump of 100% * (B - A).
    # Discontinuity is reduced by ~60%.
    assert abs(dvs_8 - dvs_7) < 20.0 # Sanity check on jump size
