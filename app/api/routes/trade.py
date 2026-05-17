from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.trade_analyzer import analyze_trade_pvo
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    evaluate_trade,
)

router = APIRouter(prefix="/trade", tags=["trade"])


class TradeRequest(BaseModel):
    my_assets: list[dict[str, Any]]
    their_assets: list[dict[str, Any]]


class TradeEvaluateRequest(BaseModel):
    side_a: list[dict[str, Any]]
    side_b: list[dict[str, Any]]


@router.post("/analyze")
def analyze(request: TradeRequest) -> dict:
    try:
        return analyze_trade_pvo(request.my_assets, request.their_assets)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/evaluate")
def evaluate_trade_endpoint(request: TradeEvaluateRequest) -> dict:
    """Evaluate a multi-asset trade using model-native xVAR parity."""
    side_a = [TradeAsset(**asset) for asset in request.side_a]
    side_b = [TradeAsset(**asset) for asset in request.side_b]
    result = evaluate_trade(side_a, side_b)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result.dict()
