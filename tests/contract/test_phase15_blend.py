"""Phase 15 Bayesian blend contract tests - spec sections 5.8, 5.9, 5.10."""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import DVS_BLEND_K
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _mock_identity(position: str) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_blend_weight_monotonicity_wr():
    """5.8: WR k_pos=5 -> w_B at games=1 < games=4 < games=7."""
    k = DVS_BLEND_K["WR"]
    w1 = 1 / (1 + k)
    w4 = 4 / (4 + k)
    w7 = 7 / (7 + k)
    assert w1 < w4 < w7
    assert w1 == pytest.approx(1 / 6, rel=1e-3)
    assert w4 == pytest.approx(4 / 9, rel=1e-3)
    assert w7 == pytest.approx(7 / 12, rel=1e-3)


def test_blend_dvs_engine_when_both_present():
    """5.9: 1 <= games_t <= 7 with Engine A and B inputs -> dvs_engine='blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        "pick": 10.0,
        "round": 1.0,
        "age": 22.0,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "blend"
    assert pvo.dvs_blend_weight_b is not None
    expected_w = 4 / (4 + DVS_BLEND_K["WR"])
    assert pvo.dvs_blend_weight_b == pytest.approx(expected_w, rel=1e-3)


def test_blend_single_engine_fallback():
    """5.10: Dead Window with no Engine A inputs -> dvs_engine != 'blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine != "blend"
    assert pvo.dynasty_value_score is None
