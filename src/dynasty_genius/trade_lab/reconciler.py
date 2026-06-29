"""Phase 22 — Trade Lab Roster Reconciler.

Pure-function module: receives universe_pvo and sleeper_snapshot as arguments,
returns a TradeRosterReconciliation. No file I/O, no market data.
"""
from __future__ import annotations

import copy
from typing import Literal

from pydantic import BaseModel, field_validator

from src.dynasty_genius.models.engine_b_contract import TRADE_PARITY_BAND
from src.dynasty_genius.roster_capacity.scenario_simulator import (
    simulate_capacity_scenarios,
)
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
    # Legacy GROSS positive-only sum (an absolute-value-leaving display, not the
    # net cost). The depletion-aware net + recovery ranges below are the truth.
    forced_cut_penalty_xvar: float
    penalty_caveats: list[str]
    # Additive (T1): RC-v1 depletion-aware NET value-at-risk + recovery ranges.
    # Default None here for additive legacy-constructor compatibility (a default
    # object carries None ranges with penalty_status="ok"). The invariant
    # "*_range is None only when blocked; unavailable still yields [0, cut_sum]"
    # is enforced on POPULATED reconcile outputs in T2, not on bare constructors.
    forced_cut_value_at_risk_range: tuple[float, float] | None = None
    forced_cut_recovery_range: tuple[float, float] | None = None
    pool_deficits: dict[str, int] = {}
    penalty_status: Literal["ok", "uncertain_pool_unavailable", "blocked"] = "ok"
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class TradeRosterReconciliation(BaseModel):
    base_evaluation: TradeEvaluation
    roster_penalty: RosterPenaltySummary
    # Legacy quantity scalars stay GROSS-derived (conservative, shown alongside
    # the net ranges). adjusted_favors is frozen to base.favors in T3 (§10b).
    adjusted_david_received_value: float
    adjusted_fairness_delta: float
    adjusted_within_parity_band: bool
    adjusted_favors: str
    # Additive (T1): range-native, capacity-aware truth. Default None here for
    # legacy-constructor compatibility; populated reconcile outputs enforce the
    # None-only-when-blocked invariant in T2. adjusted_favors_status carries the
    # honest 4-state answer (incl. uncertain_range_crosses_parity) the legacy
    # enum cannot.
    adjusted_received_value_range: tuple[float, float] | None = None
    adjusted_fairness_delta_range: tuple[float, float] | None = None
    adjusted_favors_status: Literal[
        "neutral", "david", "counterparty", "uncertain_range_crosses_parity"
    ] = "neutral"
    decision_supported: bool = False
    caveats: list[str]

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


# ── Pure range helpers (T1) ─────────────────────────────────────────────────────


def _favors_status(
    received_range: tuple[float, float],
    sent_value: float,
    parity_band: float,
) -> Literal["neutral", "david", "counterparty", "uncertain_range_crosses_parity"]:
    """Capacity-aware favors over the adjusted received RANGE.

    Uses the evaluator's RELATIVE band `delta <= parity_band * max(sent, received)`
    — the threshold varies across the range, so a fixed `sent * band` is wrong.
    `favor(received)` is monotonic in received (counterparty → neutral → david),
    so the two endpoints bound the whole interval: same favor → that state;
    differing → the range straddles parity (`uncertain_range_crosses_parity`).
    """

    def _favor(received: float) -> str:
        delta = abs(sent_value - received)
        if delta <= parity_band * max(sent_value, received):
            return "neutral"
        return "david" if received > sent_value else "counterparty"

    low, high = received_range
    favor_low, favor_high = _favor(low), _favor(high)
    if favor_low == favor_high:
        return favor_low  # type: ignore[return-value]
    return "uncertain_range_crosses_parity"


def _fairness_delta_range(
    sent_value: float, received_range: tuple[float, float]
) -> tuple[float, float]:
    """`abs(sent - received)` over the received interval — NON-MONOTONIC.

    If `sent` lies inside the interval the minimum delta is 0; otherwise it is
    the nearer endpoint. The max is always the farther endpoint.
    """
    low, high = received_range
    if low <= sent_value <= high:
        delta_low = 0.0
    else:
        delta_low = min(abs(sent_value - low), abs(sent_value - high))
    delta_high = max(abs(sent_value - low), abs(sent_value - high))
    return (delta_low, delta_high)


def _recovery_range(
    gross: float, net_range: tuple[float, float]
) -> tuple[float, float]:
    """The waiver recovery the wire provides = gross − net, bound-for-bound."""
    net_low, net_high = net_range
    return (gross - net_high, gross - net_low)


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
    pvo_lookup: dict[str, dict] = {
        p["sleeper_player_id"]: p for p in universe_pvo["players"]
    }

    # Step 2: construct post-trade snapshot (order-preserving, no set-union).
    # The traded-away players are removed from players/taxi/reserve BEFORE the
    # capacity audit, so they are never selected as a cut of their own trade.
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

    # Step 3: RC v1 is the canonical capacity + value-at-risk engine. Always
    # called (legacy post_trade_overflow is only a cross-check); the default
    # scenario clears RC's own total_capacity_cuts_required.
    rc = simulate_capacity_scenarios(
        universe_pvo, modified, david_roster_id, scenarios=None
    )

    # Step 4: corrupt/blocked audit -> blocked surface, no fabricated numbers.
    if rc.status != "ok" or not rc.scenarios:
        return _blocked_reconciliation(
            base, post_trade_total, post_trade_overflow, list(rc.caveats)
        )

    scenario = rc.scenarios[0]
    cut_set = list(scenario.cut_set)
    net_range = scenario.cumulative_value_at_risk
    # Preserve the base trade caveats at the top level (never dropped by the
    # capacity reconcile) + the RC scenario caveats.
    result_caveats = list(base.caveats) + list(scenario.caveats)
    if (
        rc.capacity_health is not None
        and post_trade_overflow != rc.capacity_health.total_capacity_cuts_required
    ):
        result_caveats.append("legacy_overflow_rc_required_cuts_divergence")

    # Step 5: gross (legacy positive-only sum) + per-cut summaries + unvalued
    # detection. A forced cut with no model value would silently UNDER-penalize
    # if treated as 0, so it blocks the net range as incomplete.
    rc_candidate_by_id = {c.sleeper_player_id: c for c in rc.candidates}
    gross = 0.0
    penalty_caveats: list[str] = []
    cut_summaries: list[dict] = []
    unvalued: list[str] = []
    for pid in cut_set:
        entry = pvo_lookup.get(pid, {})
        raw = (entry.get("valuation") or {}).get("xvar")
        player = entry.get("player", {})
        rc_candidate = rc_candidate_by_id.get(pid)
        cut_summaries.append(
            {
                "sleeper_player_id": pid,
                "full_name": (
                    rc_candidate.full_name if rc_candidate else player.get("full_name", pid)
                ),
                "position": (
                    rc_candidate.position if rc_candidate else player.get("position", "UNK")
                ),
                # Forced-review (illegal-reserve / cut_priority 0) is RC's
                # canonical signal; candidate_source supersedes the old engine's
                # ir_compliance_status string.
                "cut_priority": rc_candidate.cut_priority if rc_candidate else None,
                "candidate_source": (
                    rc_candidate.candidate_source if rc_candidate else None
                ),
                "xvar_raw": raw,
                "decision_supported": False,
            }
        )
        if raw is None:
            unvalued.append(pid)
            penalty_caveats.append(f"cut_player_value_unavailable:{pid}")
        elif raw > 0:
            gross += raw
    gross = round(gross, 2)

    if unvalued:
        return TradeRosterReconciliation(
            base_evaluation=base,
            roster_penalty=RosterPenaltySummary(
                post_trade_total_players=post_trade_total,
                post_trade_overflow=post_trade_overflow,
                forced_cut_candidates=cut_summaries,
                forced_cut_penalty_xvar=gross,
                forced_cut_value_at_risk_range=None,
                forced_cut_recovery_range=None,
                pool_deficits=dict(scenario.pool_deficits),
                penalty_status="blocked",
                penalty_caveats=penalty_caveats,
            ),
            adjusted_david_received_value=round(base.side_b.side_value, 2),
            adjusted_fairness_delta=round(base.fairness_delta, 2),
            adjusted_within_parity_band=base.within_parity_band,
            adjusted_favors=base.favors,
            adjusted_received_value_range=None,
            adjusted_fairness_delta_range=None,
            adjusted_favors_status="neutral",
            decision_supported=False,
            caveats=result_caveats,
        )

    # Step 6: net/recovery ranges + status. An unavailable waiver pool is honest
    # uncertainty, not a precise zero. Best/worst-case recovery is conditional on
    # winning the waiver claim.
    recovery_range = _recovery_range(gross, net_range)
    is_unavailable = any("waiver_range_unavailable" in c for c in scenario.caveats)
    penalty_status = "uncertain_pool_unavailable" if is_unavailable else "ok"
    penalty_caveats.append(
        "best_case_recovery: low bound assumes the top available waiver claim"
    )
    penalty_caveats.append(
        "worst_case_recovery: high bound assumes the bottom of the top-K tier"
    )

    # Range-native adjusted view (the capacity-aware truth, via the T1 helpers).
    net_low, net_high = net_range
    adjusted_received_range = (
        base.side_b.side_value - net_high,
        base.side_b.side_value - net_low,
    )
    adjusted_fairness_delta_range = _fairness_delta_range(
        base.side_a.side_value, adjusted_received_range
    )
    adjusted_favors_status = _favors_status(
        adjusted_received_range, base.side_a.side_value, TRADE_PARITY_BAND
    )

    # Legacy gross-derived scalars (conservative; adjusted_favors frozen in T3).
    adjusted_received_value = max(0.0, base.side_b.side_value - gross)
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

    return TradeRosterReconciliation(
        base_evaluation=base,
        roster_penalty=RosterPenaltySummary(
            post_trade_total_players=post_trade_total,
            post_trade_overflow=post_trade_overflow,
            forced_cut_candidates=cut_summaries,
            forced_cut_penalty_xvar=gross,
            forced_cut_value_at_risk_range=net_range,
            forced_cut_recovery_range=recovery_range,
            pool_deficits=dict(scenario.pool_deficits),
            penalty_status=penalty_status,
            penalty_caveats=penalty_caveats,
        ),
        adjusted_david_received_value=round(adjusted_received_value, 2),
        adjusted_fairness_delta=round(adjusted_delta, 2),
        adjusted_within_parity_band=adjusted_within_band,
        adjusted_favors=adjusted_favors,
        adjusted_received_value_range=adjusted_received_range,
        adjusted_fairness_delta_range=adjusted_fairness_delta_range,
        adjusted_favors_status=adjusted_favors_status,
        decision_supported=False,
        caveats=result_caveats,
    )


def _blocked_reconciliation(
    base: TradeEvaluation,
    post_trade_total: int,
    post_trade_overflow: int,
    caveats: list[str],
) -> TradeRosterReconciliation:
    """A blocked capacity audit yields no fabricated numbers — ranges stay None.

    Base trade caveats are preserved at the top level even on the blocked path.
    """
    return TradeRosterReconciliation(
        base_evaluation=base,
        roster_penalty=RosterPenaltySummary(
            post_trade_total_players=post_trade_total,
            post_trade_overflow=post_trade_overflow,
            forced_cut_candidates=[],
            forced_cut_penalty_xvar=0.0,
            forced_cut_value_at_risk_range=None,
            forced_cut_recovery_range=None,
            pool_deficits={},
            penalty_status="blocked",
            penalty_caveats=[],
        ),
        adjusted_david_received_value=round(base.side_b.side_value, 2),
        adjusted_fairness_delta=round(base.fairness_delta, 2),
        adjusted_within_parity_band=base.within_parity_band,
        adjusted_favors=base.favors,
        adjusted_received_value_range=None,
        adjusted_fairness_delta_range=None,
        adjusted_favors_status="neutral",
        decision_supported=False,
        caveats=list(base.caveats) + list(caveats),
    )
