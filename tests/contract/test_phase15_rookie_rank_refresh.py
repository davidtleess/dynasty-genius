"""Phase 15.1 — 2026 Rookie Rank Refresh contract tests."""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_A_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_A,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _prospect(position: str, pick: int = 10, round_: int = 1, age: float = 22.0) -> tuple:
    identity = PlayerIdentity(
        dg_id=f"test_{position}_{pick}",
        full_name=f"Test {position}",
        position=position,
        is_prospect=True,
        verification_status="VERIFIED_NFL_DRAFT",
    )
    features = {
        "pick": float(pick),
        "round": float(round_),
        "age": age,
        "draft_capital": float(pick),
        "age_at_nfl_entry": age,
    }
    return identity, features


def test_scored_prospect_has_xvar():
    """Scored prospect (pick + age present) has non-null xvar after Phase 15 assembler."""
    identity, features = _prospect("WR")
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is not None
    assert pvo.xvar is not None


def test_xvar_formula_wr():
    """xVAR = (DVS - ENGINE_A_REPLACEMENT_DVS['WR']) * XVAR_LAMBDA_ENGINE_A['WR']."""
    identity, features = _prospect("WR", pick=10, age=22.0)
    pvo = assemble_pvo(identity, features)
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_A["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.01)


def test_xvar_formula_rb():
    """xVAR = (DVS - ENGINE_A_REPLACEMENT_DVS['RB']) * XVAR_LAMBDA_ENGINE_A['RB']."""
    identity, features = _prospect("RB", pick=3, round_=1, age=21.0)
    pvo = assemble_pvo(identity, features)
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["RB"]) * XVAR_LAMBDA_ENGINE_A["RB"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.01)


def test_te_xvar_negative_below_replacement():
    """TE DVS below ENGINE_A_REPLACEMENT_DVS['TE'] (98.8) yields negative xVAR."""
    identity, features = _prospect("TE", pick=16, round_=1, age=22.5)
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is not None
    if pvo.dynasty_value_score < ENGINE_A_REPLACEMENT_DVS["TE"]:
        assert pvo.xvar is not None
        assert pvo.xvar < 0.0, (
            f"TE DVS {pvo.dynasty_value_score} < replacement {ENGINE_A_REPLACEMENT_DVS['TE']} "
            f"but xVAR={pvo.xvar} is non-negative"
        )


def test_pre_model_null_xvar():
    """Prospect with no features (PRE_MODEL) has null DVS and null xvar."""
    identity, _ = _prospect("WR")
    pvo = assemble_pvo(identity, {})
    assert pvo.dynasty_value_score is None
    assert pvo.xvar is None


def test_dvs_engine_a_for_scored_prospect():
    """dvs_engine='A' for scored prospects (non-PRE_MODEL, pick + age present)."""
    identity, features = _prospect("QB", pick=1, round_=1, age=21.0)
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "A"


def test_dvs_pct_null_for_prospects():
    """dvs_pct stays None — reference population is ACTIVE_B veterans, not prospects."""
    identity, features = _prospect("RB", pick=5, age=21.5)
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_pct is None


def test_decision_supported_false():
    """decision_supported=False for all prospect paths."""
    identity, features = _prospect("WR")
    pvo = assemble_pvo(identity, features)
    assert pvo.decision_supported is False


def test_rank_delta_formula():
    """rank_delta = xvar_class_rank - dvs_class_rank; positive = fell, negative = rose."""
    from scripts.refresh_prospect_cards import _compute_ranks

    pvos = [
        {"player_id": "te1", "position": "TE", "dynasty_value_score": 90.0, "xvar": -4.0},
        {"player_id": "rb1", "position": "RB", "dynasty_value_score": 80.0, "xvar": 50.0},
        {"player_id": "wr1", "position": "WR", "dynasty_value_score": 70.0, "xvar": 15.0},
        {"player_id": "pre1", "position": "WR", "dynasty_value_score": None, "xvar": None},
    ]
    result = _compute_ranks(pvos)

    te = next(p for p in result if p["player_id"] == "te1")
    rb = next(p for p in result if p["player_id"] == "rb1")
    pre = next(p for p in result if p["player_id"] == "pre1")

    # DVS ranks: te=1 (90.0), rb=2 (80.0), wr=3 (70.0)
    # xVAR ranks: rb=1 (50.0), wr=2 (15.0), te=3 (-4.0)
    assert te["dvs_class_rank"] == 1
    assert rb["xvar_class_rank"] == 1
    assert te["xvar_class_rank"] == 3
    assert te["rank_delta"] == 2    # 3 - 1 = +2 → fell
    assert rb["rank_delta"] == -1   # 1 - 2 = -1 → rose
    assert pre.get("xvar_class_rank") is None
    assert pre.get("rank_delta") is None
