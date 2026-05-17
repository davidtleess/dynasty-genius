"""Trade Lab evaluator - xVAR-sum parity with consolidation premium."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from src.dynasty_genius.models.engine_b_contract import (
    CONSOLIDATION_FLOOR,
    CONSOLIDATION_KAPPA,
    ENGINE_A_REPLACEMENT_DVS,
    TRADE_PARITY_BAND,
    XVAR_ANCHOR_POSITION,
    XVAR_LAMBDA_ENGINE_A,
)
from src.dynasty_genius.scoring.engine_a import score_prospect


class TradeAsset(BaseModel):
    player_id: str
    xvar: Optional[float]
    dvs: Optional[float] = None
    dvs_engine: Optional[str] = None
    position: str
    is_prospect: bool = False
    decision_supported: bool = False
    caveat: Optional[str] = None


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
            caveat = f"{asset.player_id}: unscored (PRE_MODEL) - excluded from trade math"
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


def value_draft_pick(
    round_: int,
    pick_bucket: str,
    position: str,
    age: float = 21.5,
) -> TradeAsset:
    """Score a draft pick through Engine A. Market data is not used."""
    slot_map = {"early": 3.0, "mid": 6.5, "late": 10.5}
    pick = slot_map.get(pick_bucket, 6.5)
    pos_upper = position.upper()
    result = score_prospect(pos_upper, pick, float(round_), age)
    dvs = result.get("dynasty_value_score") if result else None
    repl = ENGINE_A_REPLACEMENT_DVS.get(pos_upper, 0.0)
    lambda_ = XVAR_LAMBDA_ENGINE_A.get(pos_upper, 1.0)
    xvar_val = round((dvs - repl) * lambda_, 2) if dvs is not None else None
    return TradeAsset(
        player_id=f"pick_{round_}_{pick_bucket}_{pos_upper}",
        xvar=xvar_val,
        dvs=dvs,
        dvs_engine="A",
        position=pos_upper,
        is_prospect=True,
        decision_supported=False,
        caveat=(
            f"Draft pick estimate: round={round_}, bucket={pick_bucket}, "
            f"position={pos_upper}, age={age}, anchor={XVAR_ANCHOR_POSITION}"
        ),
    )
