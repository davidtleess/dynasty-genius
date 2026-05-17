"""Phase 15 xVAR contract tests - spec sections 5.1, 5.2, 5.4, 5.11."""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_A_REPLACEMENT_DVS,
    ENGINE_B_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_A,
    XVAR_LAMBDA_ENGINE_B,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _mock_identity(position: str, is_prospect: bool = False) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        is_prospect=is_prospect,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_xvar_formula_wr():
    """5.1: WR DVS=100, replacement=60.6, lambda=1.000 -> xVAR=39.4."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    expected_xvar = round(
        (100.0 - ENGINE_B_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_B["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected_xvar, abs=0.1)
    assert pvo.xvar_anchor == "WR"


def test_xvar_formula_qb_higher_than_wr_at_same_dvs():
    """5.1: QB lambda > WR lambda, so QB xVAR exceeds WR xVAR at same DVS."""
    wr_pvo = assemble_pvo(
        _mock_identity("WR"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
            "games_t": 10,
            "feature_season": 2024,
        },
    )
    qb_pvo = assemble_pvo(
        _mock_identity("QB"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 20.1, "engine": "test_v2"},
            "games_t": 10,
            "feature_season": 2024,
        },
    )
    assert qb_pvo.xvar is not None and wr_pvo.xvar is not None
    assert qb_pvo.xvar > wr_pvo.xvar


def test_engine_a_lambda_applied_for_prospect():
    """5.2: WR prospect uses Engine A replacement and lambda."""
    identity = _mock_identity("WR", is_prospect=True)
    pvo = assemble_pvo(identity, {"pick": 5.0, "round": 1.0, "age": 21.0})
    assert pvo.dvs_engine == "A"
    assert pvo.xvar_anchor == "WR"
    assert pvo.xvar is not None and pvo.dynasty_value_score is not None
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["WR"])
        * XVAR_LAMBDA_ENGINE_A["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.1)


def test_xvar_ceiling_bound_when_clamped():
    """5.4: dvs_clamped=True -> xvar_ceiling_bound=True."""
    identity = _mock_identity("QB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 30.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_clamped is True
    assert pvo.xvar_ceiling_bound is True


def test_te_xvar_computable_decision_supported_false():
    """5.11: TE has computable xVAR but decision_supported=False."""
    identity = _mock_identity("TE")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 9.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.xvar is not None
    assert pvo.decision_supported is False
    assert any("TE market superiority gate deferred" in caveat for caveat in pvo.caveats)
