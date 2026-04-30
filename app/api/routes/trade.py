from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.services.trade_analyzer import analyze_trade

router = APIRouter(prefix="/trade", tags=["trade"])


class TradeRequest(BaseModel):
    my_assets: list[dict[str, Any]]
    their_assets: list[dict[str, Any]]


@router.post("/analyze")
def analyze(request: TradeRequest) -> dict:
    try:
        return analyze_trade(request.my_assets, request.their_assets)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
