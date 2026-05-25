"""Phase 23 W5a — Trade Lab market overlay endpoint.

`POST /api/trade/reconcile/market` is the market-side sibling of the
model-native `/api/trade/reconcile`. It self-computes the Phase 22 forced-cut
set from model artifacts, then prices the trade and those cuts at raw
FantasyCalc value, attaches arbitrage divergence context (W3) and advisory
realism warnings (W4). Market values never feed the model; this lane only
reads model output to price it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
from src.dynasty_genius.trade_lab.evaluator import TradeAsset
from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    attach_competitive_realism_warnings,
    attach_market_divergence_context,
    load_market_divergence_artifact,
    reconcile_trade_market,
)
from src.dynasty_genius.trade_lab.reconciler import reconcile_trade_roster

_ROOT = Path(__file__).resolve().parents[3]

_DEFAULT_FORMAT_KEY = "dynasty_sf_ppr"
_DEFAULT_DRAFT_YEAR = 2026
_DIVERGENCE_SIGMA = 0.25
_REALISM_GAMMA = 0.15
_REALISM_PSI = 0.25

router = APIRouter(prefix="/trade", tags=["trade-market"])


class MarketReconcileRequest(BaseModel):
    sent_assets: list[dict[str, Any]]
    received_assets: list[dict[str, Any]]
    current_draft_year: int = _DEFAULT_DRAFT_YEAR
    format_key: str = _DEFAULT_FORMAT_KEY


def _load_reconcile_artifacts() -> tuple[dict, dict]:
    """Load model-native artifacts. 503 if absent — W5a self-computes Phase 22 cuts."""
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


def _fetch_fantasycalc_entries() -> tuple[list[dict], list[str]]:
    """Fetch FantasyCalc entries + caveats. Never raises (stale/cold → caveats)."""
    return fetch_with_cache()


def _load_market_divergence_artifact() -> dict:
    """Load the Phase 17.4 divergence artifact, or an empty payload if absent."""
    path = _ROOT / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"
    if not path.exists():
        return {"players": []}
    return load_market_divergence_artifact(path)


def _to_trade_asset(ref: MarketAssetRef, pvo_lookup: dict[str, dict]) -> TradeAsset:
    """Build a model-native TradeAsset for forced-cut selection only.

    xVAR is left None — cut selection reads xVAR from `universe_pvo` directly,
    not from these assets. Picks/prospects are flagged so they do not consume a
    roster slot in the capacity math.
    """
    entry = pvo_lookup.get(ref.sleeper_id or "", {})
    position = (entry.get("player") or {}).get("position") or "UNK"
    return TradeAsset(
        player_id=ref.sleeper_id or ref.player_id or "",
        xvar=None,
        position=position,
        is_prospect=(ref.asset_kind != "player"),
    )


@router.post("/reconcile/market")
def reconcile_trade_market_endpoint(request: MarketReconcileRequest) -> dict:
    """Market-overlay reconciliation (FantasyCalc), parallel to the model lane."""
    # 1. Model-native artifacts (503 if missing — required to self-compute cuts).
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    pvo_lookup = {p["sleeper_player_id"]: p for p in universe_pvo.get("players", [])}

    # 2. Market asset refs + model-native trade assets (for cut selection only).
    sent_refs = [MarketAssetRef(**a) for a in request.sent_assets]
    received_refs = [MarketAssetRef(**a) for a in request.received_assets]
    david_assets = [_to_trade_asset(r, pvo_lookup) for r in sent_refs]
    received_model_assets = [_to_trade_asset(r, pvo_lookup) for r in received_refs]

    # 3. Model-native reconciler -> forced-cut set (selection stays market-blind).
    roster_recon = reconcile_trade_roster(
        david_assets, received_model_assets, universe_pvo, sleeper_snapshot
    )
    roster_penalty = roster_recon.roster_penalty
    david_roster_penalty = {
        "roster_id": 1,
        "post_trade_overflow": roster_penalty.post_trade_overflow,
        "forced_cut_candidates": roster_penalty.forced_cut_candidates,
    }

    # 4. Market data (stale/cold degrades inside the payload, never as a 5xx).
    fc_entries, fc_caveats = _fetch_fantasycalc_entries()
    divergence_artifact = _load_market_divergence_artifact()

    # 5. Price trade + forced cuts at raw FC value (W2).
    reconciliation = reconcile_trade_market(
        sent_refs,
        received_refs,
        david_roster_penalty,
        fc_entries,
        request.current_draft_year,
        request.format_key,
    )

    # 6. Attach arbitrage divergence context to traded assets (W3).
    enriched_sent = attach_market_divergence_context(
        reconciliation.sent_assets, divergence_artifact, _DIVERGENCE_SIGMA
    )
    enriched_received = attach_market_divergence_context(
        reconciliation.received_assets, divergence_artifact, _DIVERGENCE_SIGMA
    )
    reconciliation = reconciliation.model_copy(
        update={"sent_assets": enriched_sent, "received_assets": enriched_received}
    )

    # 7. Advisory competitive-realism warnings (W4).
    reconciliation = attach_competitive_realism_warnings(
        reconciliation, gamma=_REALISM_GAMMA, psi=_REALISM_PSI
    )

    # 8. Surface FantasyCalc fetch caveats (stale/unavailable) on the envelope.
    merged_caveats = list(reconciliation.caveats)
    for caveat in fc_caveats:
        if caveat not in merged_caveats:
            merged_caveats.append(caveat)
    reconciliation = reconciliation.model_copy(update={"caveats": merged_caveats})

    return reconciliation.model_dump()
