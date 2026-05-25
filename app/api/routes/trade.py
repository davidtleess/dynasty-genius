from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.trade_analyzer import analyze_trade_pvo
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    evaluate_trade,
)
from src.dynasty_genius.trade_lab.reconciler import reconcile_trade_roster

_ROOT = Path(__file__).resolve().parents[3]

router = APIRouter(prefix="/trade", tags=["trade"])


class TradeRequest(BaseModel):
    my_assets: list[dict[str, Any]]
    their_assets: list[dict[str, Any]]


class TradeEvaluateRequest(BaseModel):
    side_a: list[dict[str, Any]]
    side_b: list[dict[str, Any]]


class TradeReconcileRequest(BaseModel):
    david_assets: list[dict[str, Any]]    # what David sends
    received_assets: list[dict[str, Any]] # what David receives


def _load_reconcile_artifacts() -> tuple[dict, dict]:
    pvo_path = _ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
    snapshot_path = (
        _ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json"
    )
    if not pvo_path.exists() or not snapshot_path.exists():
        raise HTTPException(status_code=503, detail="Required reconciler artifacts not found")
    with open(pvo_path) as f:
        universe_pvo = json.load(f)
    with open(snapshot_path) as f:
        sleeper_snapshot = json.load(f)
    return universe_pvo, sleeper_snapshot


@router.post("/analyze")
def analyze(request: TradeRequest) -> dict:
    try:
        return analyze_trade_pvo(request.my_assets, request.their_assets)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/reconcile")
def reconcile_trade_endpoint(request: TradeReconcileRequest) -> dict:
    """Evaluate a trade with post-trade roster overflow penalty (Forced Cut Penalty)."""
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    david_assets = [TradeAsset(**a) for a in request.david_assets]
    received_assets = [TradeAsset(**a) for a in request.received_assets]
    result = reconcile_trade_roster(david_assets, received_assets, universe_pvo, sleeper_snapshot)
    return result.dict()


@router.post("/evaluate")
def evaluate_trade_endpoint(request: TradeEvaluateRequest) -> dict:
    """Evaluate a multi-asset trade using model-native xVAR parity."""
    side_a = [TradeAsset(**asset) for asset in request.side_a]
    side_b = [TradeAsset(**asset) for asset in request.side_b]
    result = evaluate_trade(side_a, side_b)
    return result.dict()
