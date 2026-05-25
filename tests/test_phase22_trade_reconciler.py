"""Phase 22 — Trade Lab Roster Reconciler TDD tests (12 tests, W1).

RED  → reconciler.py does not exist yet; all 12 must fail on import.
GREEN → after reconciler.py + evaluator.py coercion-lock are in place.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.trade_lab.evaluator import TradeAsset, TradeEvaluation, TradeSide
from src.dynasty_genius.trade_lab.reconciler import (
    reconcile_trade_roster,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_STANDARD_POSITIONS = ["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"] + ["BN"] * 14  # 20 slots
_STANDARD_SETTINGS = {
    "reserve_slots": 4,
    "reserve_allow_out": 0,
    "reserve_allow_doubtful": 0,
    "reserve_allow_sus": 0,
    "reserve_allow_na": 0,
    "reserve_allow_cov": 0,
    "reserve_allow_dnr": 0,
    "taxi_slots": 2,
    "taxi_years": 1,
    "taxi_allow_vets": 0,
    "taxi_deadline": 4,
}


def _make_snapshot(
    player_ids: list[str],
    *,
    taxi_ids: list[str] | None = None,
    reserve_ids: list[str] | None = None,
    roster_id: int = 1,
    roster_positions: list[str] | None = None,
    settings: dict | None = None,
) -> dict:
    pos = roster_positions if roster_positions is not None else _STANDARD_POSITIONS
    s = settings if settings is not None else dict(_STANDARD_SETTINGS)
    return {
        "league": {
            "roster_positions": pos,
            "settings": s,
        },
        "rosters": [
            {
                "roster_id": roster_id,
                "players": list(player_ids),
                "taxi": list(taxi_ids or []),
                "reserve": list(reserve_ids or []),
            }
        ],
    }


def _make_pvo_player(
    pid: str,
    *,
    position: str = "WR",
    age: float = 24.0,
    years_exp: int = 2,
    sleeper_status: str = "Active",
    xvar_pct: float | None = 50.0,
    dvs: float | None = 50.0,
    xvar: float | None = 15.0,
    engine_path: str = "ENGINE_B",
) -> dict:
    return {
        "sleeper_player_id": pid,
        "player": {
            "full_name": f"Player {pid}",
            "position": position,
            "age": age,
            "years_exp": years_exp,
            "sleeper_status": sleeper_status,
        },
        "valuation": {
            "xvar_percentile_overall": xvar_pct,
            "dynasty_value_score": dvs,
            "xvar": xvar,
            "engine_path": engine_path,
        },
    }


def _make_pvo(players: list[dict]) -> dict:
    return {"players": players}


def _asset(player_id: str, *, xvar: float | None = 15.0, position: str = "WR", is_prospect: bool = False) -> TradeAsset:
    return TradeAsset(player_id=player_id, xvar=xvar, position=position, is_prospect=is_prospect)


def _count_ds_true(obj: object) -> int:
    if isinstance(obj, dict):
        here = 1 if obj.get("decision_supported") is True else 0
        return here + sum(_count_ds_true(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_ds_true(item) for item in obj)
    return 0


# ── Tests 11, 12 — coercion-lock on existing Trade Lab models ────────────────

def test_trade_asset_decision_supported_coerced_false():
    """TradeAsset must coerce decision_supported=True → False."""
    asset = TradeAsset(player_id="p1", xvar=10.0, position="WR", decision_supported=True)
    assert asset.decision_supported is False


def test_trade_evaluation_decision_supported_coerced_false():
    """TradeEvaluation must coerce decision_supported=True → False."""
    side = TradeSide(assets=[], xvar_sum=0.0, consolidation_factor=1.0, side_value=0.0)
    result = TradeEvaluation(
        side_a=side,
        side_b=side,
        fairness_delta=0.0,
        within_parity_band=True,
        favors="neutral",
        favors_xvar_margin=None,
        decision_supported=True,
        caveats=[],
    )
    assert result.decision_supported is False


# ── Tests 1–10 — reconciler pure function ────────────────────────────────────

def test_balanced_trade_no_overflow():
    """1-for-1 at exact capacity → overflow=0, penalty=0.0."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo([_make_pvo_player(pid) for pid in pids] + [_make_pvo_player("P_new")])
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    result = reconcile_trade_roster([_asset("P0")], [_asset("P_new")], pvo, snapshot)

    assert result.roster_penalty.post_trade_overflow == 0
    assert result.roster_penalty.forced_cut_penalty_xvar == 0.0
    assert result.roster_penalty.forced_cut_candidates == []


def test_one_for_two_at_capacity_overflows():
    """1-for-2 at capacity → overflow=1, one forced-cut candidate."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid) for pid in pids]
        + [_make_pvo_player("PA"), _make_pvo_player("PB")]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert result.roster_penalty.post_trade_overflow == 1
    assert len(result.roster_penalty.forced_cut_candidates) == 1


def test_two_for_one_no_overflow():
    """2-for-1 (David consolidates) → overflow=0, penalty=0.0."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo([_make_pvo_player(pid) for pid in pids] + [_make_pvo_player("P_new")])
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    result = reconcile_trade_roster([_asset("P0"), _asset("P1")], [_asset("P_new")], pvo, snapshot)

    assert result.roster_penalty.post_trade_overflow == 0
    assert result.roster_penalty.forced_cut_penalty_xvar == 0.0


def test_picks_excluded_from_headcount():
    """is_prospect=True assets don't consume roster slots — only player assets count."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo([_make_pvo_player(pid) for pid in pids] + [_make_pvo_player("P_new")])
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    # Send 1 player + 1 pick, receive 1 player + 2 picks: net roster change = 0 → no overflow
    result = reconcile_trade_roster(
        [_asset("P0"), _asset("pick_1_mid_WR", is_prospect=True)],
        [_asset("P_new"), _asset("pick_2_early_RB", is_prospect=True), _asset("pick_3_late_QB", is_prospect=True)],
        pvo,
        snapshot,
    )

    assert result.roster_penalty.post_trade_overflow == 0


def test_penalty_equals_top_n_cut_xvar():
    """overflow=2 → penalty = sum of the two lowest-xvar_pct active players' raw xVAR."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    # Give each player a distinct xvar_pct and raw xvar so the top-2 cuts are predictable.
    # P0 is sent away. Remaining pool after trade: P1-P19 + PA/PB/PC.
    # P1 (xvar_pct=15, xvar=6) and P2 (xvar_pct=20, xvar=7) are the two lowest → cuts.
    pvo_players = []
    for i, pid in enumerate(pids):
        pvo_players.append(_make_pvo_player(pid, xvar_pct=float(10 + i * 5), xvar=float(5 + i)))
    for extra in ("PA", "PB", "PC"):
        pvo_players.append(_make_pvo_player(extra, xvar_pct=80.0, xvar=20.0))
    pvo = _make_pvo(pvo_players)
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    # 1-for-3 → post_trade = 20 - 1 + 3 = 22, overflow = 2
    result = reconcile_trade_roster(
        [_asset("P0")],
        [_asset("PA"), _asset("PB"), _asset("PC")],
        pvo,
        snapshot,
    )

    assert result.roster_penalty.post_trade_overflow == 2
    assert len(result.roster_penalty.forced_cut_candidates) == 2
    # P0 gone; P1 (xvar=6) and P2 (xvar=7) are the two cheapest remaining
    assert result.roster_penalty.forced_cut_penalty_xvar == pytest.approx(6.0 + 7.0)


def test_forced_compliance_player_surfaces_in_penalty():
    """ILLEGAL_RESERVE player appears first in forced_cut_candidates at cut_priority=0."""
    # 18 active slots + 1 reserve slot = 19 capacity
    # P_ir on reserve with status "Active" while reserve_allow_out=1 → ILLEGAL_RESERVE
    positions_18 = ["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"] + ["BN"] * 12
    settings = dict(
        _STANDARD_SETTINGS,
        reserve_slots=1,
        reserve_allow_out=1,
        taxi_slots=0,
    )
    pids_active = [f"P{i}" for i in range(18)]
    pid_ir = "P_ir"
    all_pids = pids_active + [pid_ir]  # 19 players, capacity=19

    pvo = _make_pvo(
        [_make_pvo_player(pid) for pid in pids_active]
        + [_make_pvo_player(pid_ir, sleeper_status="Active")]
        + [_make_pvo_player("P_new")]
    )
    snapshot = _make_snapshot(
        all_pids,
        reserve_ids=[pid_ir],
        roster_positions=positions_18,
        settings=settings,
    )

    # Send nothing, receive 1 → total=20, capacity=19, overflow=1
    result = reconcile_trade_roster([], [_asset("P_new")], pvo, snapshot)

    assert result.roster_penalty.post_trade_overflow == 1
    first_cut = result.roster_penalty.forced_cut_candidates[0]
    assert first_cut["sleeper_player_id"] == pid_ir
    assert first_cut["cut_priority"] == 0
    assert first_cut["ir_compliance_status"] == "ILLEGAL_RESERVE"


def test_pre_model_penalty_candidate_caveat():
    """PRE_MODEL candidate with no xVAR → penalty stays 0.0, caveat added.

    Both players are PRE_MODEL (Tier D). The engine's stable sort preserves insertion
    order, so PA (from the original roster) appears first and is cut with priority=1.
    PA has no raw xvar → penalty=0.0; caveat names PA as excluded from penalty.
    """
    # 1 active slot, 1 pre-existing PRE_MODEL player, receive 1 more PRE_MODEL → overflow=1
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo([
        _make_pvo_player("PA", xvar=None, xvar_pct=None, engine_path="PRE_MODEL"),
        _make_pvo_player("PB", xvar=None, xvar_pct=None, engine_path="PRE_MODEL"),
    ])
    snapshot = _make_snapshot(["PA"], roster_positions=["QB"], settings=settings)

    result = reconcile_trade_roster([], [_asset("PB")], pvo, snapshot)

    # post_trade_total=2, capacity=1 → overflow=1; PA surfaces as cut (stable sort, first in list)
    assert result.roster_penalty.post_trade_overflow == 1
    assert result.roster_penalty.forced_cut_penalty_xvar == 0.0
    assert len(result.roster_penalty.penalty_caveats) == 1
    assert "PA" in result.roster_penalty.penalty_caveats[0]


def test_adjusted_value_less_than_base_when_penalty_nonzero():
    """adjusted_david_received_value < base.side_b.side_value when penalty > 0."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    # 1-for-2 → overflow=1
    result = reconcile_trade_roster(
        [_asset("P0", xvar=25.0)],
        [_asset("PA", xvar=15.0), _asset("PB", xvar=12.0)],
        pvo,
        snapshot,
    )

    assert result.roster_penalty.post_trade_overflow == 1
    assert result.adjusted_david_received_value < result.base_evaluation.side_b.side_value


def test_no_overflow_adjusted_equals_base():
    """Zero penalty → adjusted_david_received_value equals base.side_b.side_value exactly."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo([_make_pvo_player(pid) for pid in pids] + [_make_pvo_player("P_new")])
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    result = reconcile_trade_roster(
        [_asset("P0", xvar=20.0)],
        [_asset("P_new", xvar=25.0)],
        pvo,
        snapshot,
    )

    assert result.roster_penalty.post_trade_overflow == 0
    assert result.adjusted_david_received_value == result.base_evaluation.side_b.side_value


def test_decision_supported_false_throughout():
    """Recursive walk of .dict() output: zero decision_supported=True anywhere."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid) for pid in pids]
        + [_make_pvo_player("PA"), _make_pvo_player("PB")]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    # overflow=1 exercises forced_cut_candidates in output
    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert _count_ds_true(result.dict()) == 0
