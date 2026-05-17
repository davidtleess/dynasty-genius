"""Phase 15 Trade Lab contract tests - spec sections 5.3, 5.5, 5.6, 5.7, 5.12, 5.13."""
from __future__ import annotations

from typing import Optional

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    CONSOLIDATION_FLOOR,
    CONSOLIDATION_KAPPA,
    TRADE_PARITY_BAND,
)
from src.dynasty_genius.services.market_overlay_service import NOISE_BAND
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    _consolidation_factor,
    evaluate_trade,
    value_draft_pick,
)


def _asset(pos: str, xvar: Optional[float], dvs_engine: str = "B") -> TradeAsset:
    return TradeAsset(
        player_id=f"test_{pos}",
        xvar=xvar,
        dvs=None,
        dvs_engine=dvs_engine,
        position=pos,
    )


def test_sub_replacement_contributes_zero():
    """5.3: xVAR <= 0 contributes 0 to side value."""
    bench = _asset("WR", -5.0)
    starter = _asset("WR", 20.0)
    result = evaluate_trade([bench, starter], [_asset("QB", 25.0)])
    assert result.side_a.xvar_sum == 20.0
    assert result.side_a.consolidation_factor == 1.0


def test_consolidation_factor_1_asset():
    """5.5: 1-starter side: factor = 1.000."""
    assert _consolidation_factor(1) == 1.0


def test_consolidation_factor_2_assets():
    """5.5: 2 starters: factor = 1.0 - 0.04 * 1 = 0.960."""
    assert _consolidation_factor(2) == pytest.approx(0.960)


def test_consolidation_factor_3_assets():
    """5.5: 3 starters: factor = 1.0 - 0.04 * 2 = 0.920."""
    assert _consolidation_factor(3) == pytest.approx(0.920)


def test_consolidation_factor_floor():
    """5.5: 6 starters: factor = max(0.80, 1.0 - 0.04 * 5) = 0.80."""
    assert _consolidation_factor(6) == pytest.approx(CONSOLIDATION_FLOOR)


def test_trade_within_parity_band():
    """5.6: delta=2.0, max=32.0 -> 2.0 <= 0.10 * 32.0 = 3.2."""
    result = evaluate_trade([_asset("WR", 30.0)], [_asset("WR", 32.0)])
    assert result.within_parity_band is True
    assert result.favors == "neutral"


def test_trade_outside_parity_band():
    """5.7: delta=20.0, max=40.0 -> 20.0 > 0.10 * 40.0 = 4.0."""
    result = evaluate_trade([_asset("WR", 20.0)], [_asset("WR", 40.0)])
    assert result.within_parity_band is False
    assert result.favors == "side_b"


def test_draft_pick_uses_engine_a():
    """5.12: Draft pick via value_draft_pick -> dvs_engine == 'A', is_prospect True."""
    pick_asset = value_draft_pick(round_=1, pick_bucket="mid", position="WR", age=21.5)
    assert pick_asset.dvs_engine == "A"
    assert pick_asset.is_prospect is True
    assert pick_asset.decision_supported is False


def test_trade_parity_band_not_noise_band():
    """5.13: TRADE_PARITY_BAND and NOISE_BAND are separate constants."""
    assert TRADE_PARITY_BAND == 0.10
    assert NOISE_BAND == 0.10
    assert CONSOLIDATION_KAPPA == 0.04


def test_decision_supported_false_on_evaluation():
    """TradeEvaluation.decision_supported must always be False."""
    result = evaluate_trade([_asset("WR", 20.0)], [_asset("QB", 25.0)])
    assert result.decision_supported is False
