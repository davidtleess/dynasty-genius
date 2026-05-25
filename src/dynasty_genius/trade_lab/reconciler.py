"""Phase 22 — Trade Lab Roster Reconciler.

Pure-function module: receives universe_pvo and sleeper_snapshot as arguments,
returns a TradeRosterReconciliation. No file I/O, no market data.
"""
from __future__ import annotations

import copy

from pydantic import BaseModel, field_validator

from src.dynasty_genius.models.engine_b_contract import TRADE_PARITY_BAND
from src.dynasty_genius.roster_cut_engine import compute_roster_cut_candidates
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    TradeEvaluation,
    evaluate_trade,
)

# ── Output models ─────────────────────────────────────────────────────────────


class RosterPenaltySummary(BaseModel):
    post_trade_total_players: int
    post_trade_overflow: int
    forced_cut_candidates: list[dict]
    forced_cut_penalty_xvar: float
    penalty_caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class TradeRosterReconciliation(BaseModel):
    base_evaluation: TradeEvaluation
    roster_penalty: RosterPenaltySummary
    adjusted_david_received_value: float
    adjusted_fairness_delta: float
    adjusted_within_parity_band: bool
    adjusted_favors: str
    decision_supported: bool = False
    caveats: list[str]

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cut_summary(candidate, raw_xvar: float | None) -> dict:
    return {
        "sleeper_player_id": candidate.sleeper_player_id,
        "full_name": candidate.full_name,
        "position": candidate.position,
        "cut_priority": candidate.cut_priority,
        "scoring_tier": candidate.scoring_tier,
        "xvar_raw": raw_xvar,
        "xvar_pct": candidate.xvar_pct,
        "ir_compliance_status": candidate.ir_compliance_status,
        "decision_supported": False,
    }


# ── Entry point ───────────────────────────────────────────────────────────────


def reconcile_trade_roster(
    david_assets: list[TradeAsset],
    received_assets: list[TradeAsset],
    universe_pvo: dict,
    sleeper_snapshot: dict,
    david_roster_id: int = 1,
) -> TradeRosterReconciliation:
    """Evaluate a trade against post-trade roster capacity and compute forced-cut penalty.

    side_a = david_assets (sent); side_b = received_assets.
    Penalty is deducted from side_b.side_value — does not interact with consolidation math.
    """
    # Step 0: identify roster-affecting assets (picks don't consume slots)
    players_out = [a.player_id for a in david_assets if not a.is_prospect]
    players_in = [a.player_id for a in received_assets if not a.is_prospect]

    # Step 1: compute post-trade capacity state
    league = sleeper_snapshot["league"]
    settings = league["settings"]
    active_slots = len(league["roster_positions"])
    reserve_slots = int(settings.get("reserve_slots") or 0)
    taxi_slots = int(settings.get("taxi_slots") or 0)
    total_capacity = active_slots + reserve_slots + taxi_slots

    roster = next(r for r in sleeper_snapshot["rosters"] if r["roster_id"] == david_roster_id)
    current_total = len(roster.get("players") or [])

    post_trade_total = current_total - len(players_out) + len(players_in)
    post_trade_overflow = max(0, post_trade_total - total_capacity)

    # Evaluate base trade (side_a = sent, side_b = received)
    base = evaluate_trade(david_assets, received_assets)

    # Step 2: early-return — no overflow, no penalty
    if post_trade_overflow == 0:
        return TradeRosterReconciliation(
            base_evaluation=base,
            roster_penalty=RosterPenaltySummary(
                post_trade_total_players=post_trade_total,
                post_trade_overflow=0,
                forced_cut_candidates=[],
                forced_cut_penalty_xvar=0.0,
                penalty_caveats=[],
            ),
            adjusted_david_received_value=base.side_b.side_value,
            adjusted_fairness_delta=base.fairness_delta,
            adjusted_within_parity_band=base.within_parity_band,
            adjusted_favors=base.favors,
            caveats=base.caveats,
        )

    # Step 3: construct post-trade snapshot (order-preserving, no set-union)
    modified = copy.deepcopy(sleeper_snapshot)
    modified_roster = next(
        r for r in modified["rosters"] if r["roster_id"] == david_roster_id
    )
    out_set = set(players_out)
    modified_roster["players"] = [
        p for p in (modified_roster["players"] or []) if p not in out_set
    ]
    modified_roster["taxi"] = [
        p for p in (modified_roster.get("taxi") or []) if p not in out_set
    ]
    modified_roster["reserve"] = [
        p for p in (modified_roster.get("reserve") or []) if p not in out_set
    ]
    existing_ids = set(modified_roster["players"])
    for pid in players_in:
        if pid not in existing_ids:
            modified_roster["players"].append(pid)
            existing_ids.add(pid)

    # Step 4: run RosterCutEngine on post-trade roster
    post_trade_result = compute_roster_cut_candidates(universe_pvo, modified, david_roster_id)
    forced_cuts = post_trade_result.cut_candidates[:post_trade_overflow]

    # Step 5: compute forced-cut penalty using raw xvar from PVO
    pvo_lookup: dict[str, dict] = {
        p["sleeper_player_id"]: p for p in universe_pvo["players"]
    }
    penalty_xvar = 0.0
    penalty_caveats: list[str] = []
    cut_summaries: list[dict] = []

    for candidate in forced_cuts:
        entry = pvo_lookup.get(candidate.sleeper_player_id, {})
        raw_xvar = (entry.get("valuation") or {}).get("xvar")
        if raw_xvar is not None and raw_xvar > 0:
            penalty_xvar += raw_xvar
        else:
            penalty_caveats.append(
                f"{candidate.full_name} ({candidate.sleeper_player_id}): "
                f"xVAR unavailable ({candidate.scoring_tier}) — excluded from penalty"
            )
        cut_summaries.append(_cut_summary(candidate, raw_xvar))

    # Step 6: compute adjusted evaluation
    # Penalty subtracts from side_b (received); side_a (sent) is unchanged
    adjusted_received_value = max(0.0, base.side_b.side_value - penalty_xvar)
    adjusted_delta = abs(base.side_a.side_value - adjusted_received_value)
    adjusted_max_side = max(base.side_a.side_value, adjusted_received_value)
    adjusted_within_band = (
        adjusted_delta <= TRADE_PARITY_BAND * adjusted_max_side
        if adjusted_max_side > 0
        else True
    )
    if adjusted_within_band:
        adjusted_favors = "neutral"
    elif adjusted_received_value > base.side_a.side_value:
        adjusted_favors = "david"
    else:
        adjusted_favors = "counterparty"

    # Step 7: assemble output
    return TradeRosterReconciliation(
        base_evaluation=base,
        roster_penalty=RosterPenaltySummary(
            post_trade_total_players=post_trade_total,
            post_trade_overflow=post_trade_overflow,
            forced_cut_candidates=cut_summaries,
            forced_cut_penalty_xvar=round(penalty_xvar, 2),
            penalty_caveats=penalty_caveats,
        ),
        adjusted_david_received_value=round(adjusted_received_value, 2),
        adjusted_fairness_delta=round(adjusted_delta, 2),
        adjusted_within_parity_band=adjusted_within_band,
        adjusted_favors=adjusted_favors,
        decision_supported=False,
        caveats=base.caveats + penalty_caveats,
    )
