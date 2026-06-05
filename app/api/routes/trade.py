from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.trade_analyzer import analyze_trade_pvo
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    TradeEvaluation,
    evaluate_trade,
)
from src.dynasty_genius.trade_lab.reconciler import (
    TradeRosterReconciliation,
    reconcile_trade_roster,
)

_ROOT = Path(__file__).resolve().parents[3]

router = APIRouter(prefix="/trade", tags=["trade"])


class TradeRequest(BaseModel):
    my_assets: list[dict[str, Any]]
    their_assets: list[dict[str, Any]]


class TradeEvaluateRequest(BaseModel):
    side_a: list[TradeAsset]
    side_b: list[TradeAsset]


class TradeReconcileRequest(BaseModel):
    david_assets: list[TradeAsset]     # what David sends
    received_assets: list[TradeAsset]  # what David receives


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


@router.post("/reconcile", response_model=TradeRosterReconciliation)
def reconcile_trade_endpoint(request: TradeReconcileRequest) -> TradeRosterReconciliation:
    """Evaluate a trade with post-trade roster overflow penalty (Forced Cut Penalty)."""
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    # Request body is already typed as list[TradeAsset]; pass through (no Model(**a)).
    return reconcile_trade_roster(
        list(request.david_assets),
        list(request.received_assets),
        universe_pvo,
        sleeper_snapshot,
    )


@router.post("/evaluate", response_model=TradeEvaluation)
def evaluate_trade_endpoint(request: TradeEvaluateRequest) -> TradeEvaluation:
    """Evaluate a multi-asset trade using model-native xVAR parity."""
    return evaluate_trade(list(request.side_a), list(request.side_b))
