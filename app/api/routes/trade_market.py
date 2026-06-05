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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
from src.dynasty_genius.trade_lab.evaluator import TradeAsset
from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    TradeMarketReconciliation,
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
    sent_assets: list[MarketAssetRef]
    received_assets: list[MarketAssetRef]
    current_draft_year: int = _DEFAULT_DRAFT_YEAR
    format_key: str = _DEFAULT_FORMAT_KEY
    # W3b: optional double-sided market penalty. When omitted, behavior is the
    # single-sided David reconciliation (status "not_requested").
    counterparty_roster_id: int | None = None


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


def _select_counterparty_penalty(
    counterparty_roster_id: int,
    received_model_assets: list[TradeAsset],
    david_assets: list[TradeAsset],
    universe_pvo: dict,
    sleeper_snapshot: dict,
    pvo_lookup: dict[str, dict],
) -> tuple[str, dict | None, list[str]]:
    """Select the counterparty's forced cuts, model-native and fail-closed (W3b).

    Returns ``(status, penalty_input, caveats)``:
    - unknown roster → ``("unavailable", None, ["counterparty_roster_unknown"])``
    - known roster but a post-trade roster player lacks PVO coverage →
      ``("unavailable", None, ["counterparty_coverage_inadequate"])`` — model-native
      selection would be invalid and we must never fall back to market sorting.
    - otherwise → ``("available", <penalty dict>, [])`` using RosterCutEngine output.

    Selection swaps sides: the counterparty *sends* what David receives and
    *receives* what David sends, evaluated against ``counterparty_roster_id``.
    """
    rosters = sleeper_snapshot.get("rosters", [])
    cp_roster = next(
        (r for r in rosters if r.get("roster_id") == counterparty_roster_id), None
    )
    if cp_roster is None:
        return "unavailable", None, ["counterparty_roster_unknown"]

    # Fail-closed model-coverage gate: every post-trade counterparty roster
    # player eligible for cutting must have a PVO entry. Otherwise model-native
    # selection is not valid and we surface unavailable rather than FC-sorting.
    out_set = {a.player_id for a in received_model_assets if not a.is_prospect}
    players_in = [a.player_id for a in david_assets if not a.is_prospect]
    post_trade_players = [p for p in (cp_roster.get("players") or []) if p not in out_set]
    for pid in players_in:
        if pid not in post_trade_players:
            post_trade_players.append(pid)
    if any(pid not in pvo_lookup for pid in post_trade_players):
        return "unavailable", None, ["counterparty_coverage_inadequate"]

    # Swap sides: counterparty sends David's received, receives David's sent.
    # Fail closed: if the post-trade snapshot cannot be built or RosterCutEngine
    # cannot run (malformed/invalid snapshot, e.g. a protected slot type), degrade
    # to unavailable rather than surfacing a 5xx (spec §385-386, 505). We never
    # fall back to market-sorted selection.
    try:
        cp_recon = reconcile_trade_roster(
            received_model_assets,
            david_assets,
            universe_pvo,
            sleeper_snapshot,
            david_roster_id=counterparty_roster_id,
        )
    except (ValueError, KeyError, StopIteration):
        return "unavailable", None, ["counterparty_coverage_inadequate"]
    cp_penalty = cp_recon.roster_penalty
    penalty_input = {
        "roster_id": counterparty_roster_id,
        "post_trade_overflow": cp_penalty.post_trade_overflow,
        "forced_cut_candidates": cp_penalty.forced_cut_candidates,
    }
    return "available", penalty_input, []


@router.post("/reconcile/market", response_model=TradeMarketReconciliation)
def reconcile_trade_market_endpoint(
    request: MarketReconcileRequest,
) -> TradeMarketReconciliation:
    """Market-overlay reconciliation (FantasyCalc), parallel to the model lane."""
    # 1. Model-native artifacts (503 if missing — required to self-compute cuts).
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    pvo_lookup = {p["sleeper_player_id"]: p for p in universe_pvo.get("players", [])}

    # 2. Market asset refs + model-native trade assets (for cut selection only).
    # Request body is already typed as list[MarketAssetRef]; pass through.
    sent_refs = list(request.sent_assets)
    received_refs = list(request.received_assets)
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

    # 3b. Optional counterparty forced-cut selection (W3b) — model-native and
    #     fail-closed. The market lane only prices the resulting cut set; cut
    #     selection (and the unavailable/unknown determination) happens here.
    cp_status = "not_requested"
    cp_penalty_input: dict | None = None
    cp_caveats: list[str] = []
    if request.counterparty_roster_id is not None:
        cp_status, cp_penalty_input, cp_caveats = _select_counterparty_penalty(
            request.counterparty_roster_id,
            received_model_assets,
            david_assets,
            universe_pvo,
            sleeper_snapshot,
            pvo_lookup,
        )

    # 4. Market data (stale/cold degrades inside the payload, never as a 5xx).
    fc_entries, fc_caveats = _fetch_fantasycalc_entries()
    divergence_artifact = _load_market_divergence_artifact()

    # 5. Price trade + forced cuts at raw FC value (W2 David + W3b counterparty).
    reconciliation = reconcile_trade_market(
        sent_refs,
        received_refs,
        david_roster_penalty,
        fc_entries,
        request.current_draft_year,
        request.format_key,
        counterparty_roster_penalty=cp_penalty_input,
        counterparty_market_penalty_status=cp_status,
        counterparty_caveats=cp_caveats,
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

    return reconciliation
