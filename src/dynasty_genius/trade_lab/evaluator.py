"""Trade Lab evaluator - xVAR-sum parity with consolidation premium."""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.dynasty_genius.models.engine_b_contract import (
    CONSOLIDATION_FLOOR,
    CONSOLIDATION_KAPPA,
    TRADE_PARITY_BAND,
)
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve, value_pick


class TradeAsset(BaseModel):
    player_id: str
    xvar: Optional[float]
    dvs: Optional[float] = None
    dvs_engine: Optional[str] = None
    position: str
    is_prospect: bool = False
    decision_supported: bool = False
    caveat: Optional[str] = None

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class TradeSide(BaseModel):
    assets: List[TradeAsset]
    xvar_sum: float
    consolidation_factor: float
    side_value: float


class TradeEvaluation(BaseModel):
    side_a: TradeSide
    side_b: TradeSide
    fairness_delta: float
    within_parity_band: bool
    favors: Optional[str]
    favors_xvar_margin: Optional[float]
    decision_supported: bool = False
    caveats: List[str]

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


def _consolidation_factor(n_starter_assets: int) -> float:
    if n_starter_assets <= 1:
        return 1.0
    raw = 1.0 - CONSOLIDATION_KAPPA * (n_starter_assets - 1)
    return max(CONSOLIDATION_FLOOR, raw)


def _evaluate_side(assets: List[TradeAsset]) -> TradeSide:
    starter_xvars = [asset.xvar for asset in assets if asset.xvar is not None and asset.xvar > 0]
    xvar_sum = sum(starter_xvars)
    factor = _consolidation_factor(len(starter_xvars))
    return TradeSide(
        assets=assets,
        xvar_sum=round(xvar_sum, 2),
        consolidation_factor=round(factor, 4),
        side_value=round(xvar_sum * factor, 2),
    )


def evaluate_trade(
    side_a_assets: List[TradeAsset],
    side_b_assets: List[TradeAsset],
) -> TradeEvaluation:
    side_a = _evaluate_side(side_a_assets)
    side_b = _evaluate_side(side_b_assets)
    delta = abs(side_a.side_value - side_b.side_value)
    max_side = max(side_a.side_value, side_b.side_value)
    within_band = delta <= TRADE_PARITY_BAND * max_side if max_side > 0 else True

    favors = "neutral"
    margin = None
    if not within_band:
        favors = "side_a" if side_a.side_value > side_b.side_value else "side_b"
        margin = round(delta, 2)

    caveats: List[str] = []
    for asset in side_a_assets + side_b_assets:
        if asset.caveat and asset.caveat not in caveats:
            caveats.append(asset.caveat)
        if asset.xvar is None:
            caveat = f"{asset.player_id}: unscored (PRE_MODEL) — excluded from trade math"
            if caveat not in caveats:
                caveats.append(caveat)

    return TradeEvaluation(
        side_a=side_a,
        side_b=side_b,
        fairness_delta=round(delta, 2),
        within_parity_band=within_band,
        favors=favors,
        favors_xvar_margin=margin,
        decision_supported=False,
        caveats=caveats,
    )


_PICK_CURVE_PATH = (
    Path(__file__).resolve().parents[3]
    / "app" / "data" / "valuation" / "draft_pick_value_curve_v1.json"
)
_PICK_CURVE_CACHE: Optional[dict] = None
_ROUND_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def _pick_curve() -> dict:
    global _PICK_CURVE_CACHE
    if _PICK_CURVE_CACHE is None:
        _PICK_CURVE_CACHE = load_curve(_PICK_CURVE_PATH)
    return _PICK_CURVE_CACHE


def value_draft_pick(
    round_: int,
    pick_bucket: str,
    position: str,
    age: float = 21.5,
) -> TradeAsset:
    """DEPRECATED — use ``draft_pick_valuation.value_pick``.

    Returns a curve-backed ``TradeAsset``. ``position`` and ``age`` are ignored for
    the value: a dynasty pick's value is position-independent and comes from the
    historical slot curve (Phase 24), not a fake per-position Engine-A prospect.
    """
    warnings.warn(
        "value_draft_pick is deprecated; use draft_pick_valuation.value_pick. "
        "position/age are ignored (pick value is position-independent).",
        DeprecationWarning,
        stacklevel=2,
    )
    tier = f"{pick_bucket}_{_ROUND_ORDINAL.get(round_, '1st')}"
    pv = value_pick(year=0, round_=round_, tier=tier, curve=_pick_curve())
    return TradeAsset(
        player_id=f"pick_{round_}_{pick_bucket}",
        xvar=pv.xvar,
        dvs=None,
        dvs_engine="pick_curve_v1",
        position=position.upper(),
        is_prospect=True,
        decision_supported=False,
        caveat="; ".join(
            ["value_draft_pick deprecated -> draft_pick_valuation.value_pick", *pv.caveats]
        ),
    )
