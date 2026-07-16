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
from src.dynasty_genius.league_capture import load_production_league_set
from src.dynasty_genius.pvo_source import (
    PvoSourceNotReadyError,
    resolve_pvo_source,
)
from src.dynasty_genius.trade_lab.cross_lane_review import (
    evaluate_cross_lane_manual_review,
)
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve, value_pick
from src.dynasty_genius.trade_lab.evaluator import _PICK_CURVE_PATH, TradeAsset
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
# F-seed-split T4: resolve the PVO pair (verified runtime else committed seed); the seed
# is the absence fallback, a present-but-unverified runtime fails closed (503).
PVO_SEED_PATH = _ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
PVO_SEED_COVERAGE_PATH = (
    _ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)
PVO_RUNTIME_DIR = _ROOT / "app" / "data" / "valuation_runtime"

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
    snapshot_path = load_production_league_set().paths["snapshot.json"]
    try:
        resolved = resolve_pvo_source(
            seed_paths={"pvo": PVO_SEED_PATH, "coverage": PVO_SEED_COVERAGE_PATH},
            runtime_dir=PVO_RUNTIME_DIR,
        )
    except PvoSourceNotReadyError as exc:
        raise HTTPException(
            status_code=503, detail="PVO runtime present but unverified"
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="Required reconciler artifacts not found"
        ) from exc
    if not snapshot_path.exists():
        raise HTTPException(status_code=503, detail="Required reconciler artifacts not found")
    with open(resolved.pvo_path) as f:
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


def _hydrate_model_asset(
    ref: MarketAssetRef, pvo_lookup: dict[str, dict], pick_curve: dict
) -> TradeAsset:
    """Build a model-native TradeAsset with REAL xVAR for the W5b cross-lane delta.

    Distinct from ``_to_trade_asset`` (which leaves xVAR None for cut selection).
    Players price from PVO; exact-slot/round-only picks via ``value_pick``;
    bucket-only picks and any unresolvable ref get xVAR ``None`` — driving the
    fail-closed model-coverage-incomplete path (spec §5 Option A, §3.3).
    """
    if ref.asset_kind == "player":
        entry = pvo_lookup.get(ref.sleeper_id or "", {})
        xvar = (entry.get("valuation") or {}).get("xvar")
        position = (entry.get("player") or {}).get("position") or "UNK"
        return TradeAsset(
            player_id=ref.sleeper_id or ref.player_id or "",
            xvar=xvar,
            position=position,
            is_prospect=False,
        )

    # Pick refs. Bucket-only picks are not priceable (value_pick has no bucket
    # parameter); they fail closed to xVAR None.
    xvar: float | None = None
    if ref.year is not None and ref.round is not None and ref.bucket is None:
        if ref.slot is not None:
            priced = value_pick(
                year=ref.year, round_=ref.round, slot=ref.slot, curve=pick_curve
            )
        else:
            priced = value_pick(year=ref.year, round_=ref.round, curve=pick_curve)
        xvar = priced.xvar
    return TradeAsset(
        player_id=ref.quantity_id or ref.player_id or "",
        xvar=xvar,
        position="",
        is_prospect=True,
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
        sleeper_snapshot=sleeper_snapshot,
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

    # 9. W5b cross-lane manual-review producer. Runs AFTER W3/W4 on a SEPARATE
    #    hydrated model reconcile — the step-3 cut-selection reconcile (xvar=None)
    #    and all market math above are left untouched. Fail-closed: incomplete
    #    coverage (incl. forced-cut gaps / bucket picks) suppresses with a
    #    per-lane caveat instead of emitting on partial evidence.
    pick_curve = load_curve(_PICK_CURVE_PATH)
    hydrated_sent = [_hydrate_model_asset(r, pvo_lookup, pick_curve) for r in sent_refs]
    hydrated_received = [
        _hydrate_model_asset(r, pvo_lookup, pick_curve) for r in received_refs
    ]
    hydrated_recon = reconcile_trade_roster(
        hydrated_sent, hydrated_received, universe_pvo, sleeper_snapshot
    )

    # Model coverage: every traded asset priced AND no forced-cut candidate with a
    # missing raw xVAR (never infer zero).
    model_coverage_complete = all(
        a.xvar is not None for a in hydrated_sent + hydrated_received
    ) and all(
        cut.get("xvar_raw") is not None
        for cut in hydrated_recon.roster_penalty.forced_cut_candidates
    )
    # Market coverage: every traded overlay resolved + valued, no envelope coverage
    # gaps, and no unresolved forced cuts on either priced penalty.
    market_penalties = [
        reconciliation.david_forced_cut_penalty,
        reconciliation.counterparty_forced_cut_penalty,
    ]
    market_coverage_complete = (
        all(
            o.market_value is not None and o.resolution != "unresolved"
            for o in reconciliation.sent_assets + reconciliation.received_assets
        )
        and not reconciliation.coverage_gaps
        and all(
            p is None or p.unresolved_cut_count == 0 for p in market_penalties
        )
    )

    adjusted_model_received = hydrated_recon.adjusted_david_received_value
    adjusted_model_sent = hydrated_recon.base_evaluation.side_a.side_value
    cross_lane = evaluate_cross_lane_manual_review(
        # Range-native, capacity-aware status (§10b) — the deprecated legacy
        # adjusted_favors is base-only and must not feed the cross-lane review.
        model_favors_raw=hydrated_recon.adjusted_favors_status,
        model_coverage_complete=model_coverage_complete,
        model_delta_signed=adjusted_model_received - adjusted_model_sent,
        adjusted_model_sent=adjusted_model_sent,
        adjusted_model_received=adjusted_model_received,
        market_delta_for_david=reconciliation.market_delta_for_david,
        adjusted_market_sent=reconciliation.adjusted_market_sent,
        adjusted_market_received=reconciliation.adjusted_market_received,
        market_coverage_complete=market_coverage_complete,
    )

    w5b_warnings = list(reconciliation.realism_warnings)
    w5b_caveats = list(reconciliation.caveats)
    if cross_lane.warning is not None:
        w5b_warnings.append(cross_lane.warning)
    if cross_lane.suppressed_reason:
        for reason in sorted(cross_lane.suppressed_reason):
            caveat = f"cross_lane_manual_review_suppressed_{reason}"
            if caveat not in w5b_caveats:
                w5b_caveats.append(caveat)
    reconciliation = reconciliation.model_copy(
        update={"realism_warnings": w5b_warnings, "caveats": w5b_caveats}
    )

    return reconciliation
