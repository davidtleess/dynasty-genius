"""Phase 22 — Trade Lab Roster Reconciler TDD tests (12 tests, W1).

RED  → reconciler.py does not exist yet; all 12 must fail on import.
GREEN → after reconciler.py + evaluator.py coercion-lock are in place.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.roster_capacity.models import (
    CapacityAuditResult,
    CapacityHealth,
    ScenarioResult,
)
from src.dynasty_genius.trade_lab import reconciler
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    TradeEvaluation,
    TradeSide,
)
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


def _capacity_health(*, required_cuts: int) -> CapacityHealth:
    return CapacityHealth(
        total_players=21,
        total_capacity=20,
        total_capacity_cuts_required=required_cuts,
        active_slot_overflow=0,
        by_slot_class={"active": 20, "reserve": 0, "taxi": 0},
        reserve_unrestricted=False,
    )


def _rc_result(
    *,
    net_range: tuple[float, float],
    cut_set: list[str] | None = None,
    caveats: list[str] | None = None,
    pool_deficits: dict[str, int] | None = None,
    required_cuts: int = 1,
) -> CapacityAuditResult:
    return CapacityAuditResult(
        status="ok",
        capacity_health=_capacity_health(required_cuts=required_cuts),
        candidates=[],
        scenarios=[
            ScenarioResult(
                cut_set=list(cut_set or ["P1"]),
                cumulative_value_at_risk=net_range,
                marginal_next_candidate_cost=None,
                per_position_depth_impact={},
                pool_deficits=dict(pool_deficits or {}),
                caveats=list(caveats or []),
            )
        ],
        unrostered_pool_range={},
        excluded_counts={},
        caveats=[],
    )


def _assert_no_verdict_tokens(obj: object) -> None:
    serialized = str(obj).lower()
    for token in ("buy", "sell", "hold", "accept", "reject", "recommended"):
        assert token not in serialized


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
    assert first_cut["candidate_source"] == "forced_review"


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


def test_rc_v1_scenario_populates_net_recovery_and_adjusted_ranges(monkeypatch):
    """T2: reconciler calls RC v1 with scenarios=None and reads default scenario."""
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)
    calls: list[dict] = []

    def fake_simulate_capacity_scenarios(
        universe_pvo: dict,
        post_trade_snapshot: dict,
        david_roster_id: int,
        *,
        scenarios: list[dict] | None = None,
    ) -> CapacityAuditResult:
        calls.append(
            {
                "scenarios": scenarios,
                "players": list(post_trade_snapshot["rosters"][0]["players"]),
                "taxi": list(post_trade_snapshot["rosters"][0].get("taxi") or []),
                "reserve": list(post_trade_snapshot["rosters"][0].get("reserve") or []),
                "roster_id": david_roster_id,
            }
        )
        return _rc_result(net_range=(4.0, 16.0), cut_set=["P1"])

    monkeypatch.setattr(
        reconciler, "simulate_capacity_scenarios", fake_simulate_capacity_scenarios, raising=False
    )

    result = reconcile_trade_roster(
        [_asset("P0", xvar=25.0)],
        [_asset("PA", xvar=15.0), _asset("PB", xvar=12.0)],
        pvo,
        snapshot,
    )

    assert calls == [
        {
            "scenarios": None,
            "players": [*pids[1:], "PA", "PB"],
            "taxi": [],
            "reserve": [],
            "roster_id": 1,
        }
    ]
    assert result.roster_penalty.forced_cut_penalty_xvar == pytest.approx(20.0)
    assert result.roster_penalty.forced_cut_value_at_risk_range == (4.0, 16.0)
    assert result.roster_penalty.forced_cut_recovery_range == (4.0, 16.0)
    assert result.roster_penalty.pool_deficits == {}
    assert result.roster_penalty.penalty_status == "ok"
    assert result.adjusted_received_value_range == (
        pytest.approx(result.base_evaluation.side_b.side_value - 16.0),
        pytest.approx(result.base_evaluation.side_b.side_value - 4.0),
    )
    assert result.adjusted_fairness_delta_range is not None
    assert result.adjusted_favors_status in {
        "neutral",
        "david",
        "counterparty",
        "uncertain_range_crosses_parity",
    }
    assert _count_ds_true(result.model_dump()) == 0
    _assert_no_verdict_tokens(result.model_dump())


def test_legacy_adjusted_favors_freezes_to_base_direction_on_all_rc_paths(
    monkeypatch,
):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)
    rc_modes: list[str] = []

    def fake_rc(*_args, **_kwargs) -> CapacityAuditResult:
        mode = rc_modes.pop(0)
        if mode == "blocked":
            return CapacityAuditResult(
                status="blocked",
                capacity_health=None,
                candidates=[],
                scenarios=[],
                unrostered_pool_range={},
                excluded_counts={},
                caveats=["capacity_audit_blocked"],
            )
        if mode == "unvalued":
            return _rc_result(net_range=(0.0, 0.0), cut_set=["P1"])
        return _rc_result(net_range=(4.0, 16.0), cut_set=["P1"])

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_rc, raising=False)

    for mode in ("normal", "unvalued", "blocked"):
        rc_modes.append(mode)
        result = reconcile_trade_roster(
            [_asset("P0", xvar=25.0)],
            [_asset("PA", xvar=25.0), _asset("PB", xvar=15.0)],
            pvo,
            snapshot,
        )

        assert result.base_evaluation.favors == "side_b"
        assert result.adjusted_favors == result.base_evaluation.favors
        assert _count_ds_true(result.model_dump()) == 0


def test_capacity_range_changes_status_without_changing_deprecated_favors(
    monkeypatch,
):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)
    net_ranges = [(0.0, 0.0), (0.0, 20.0)]

    def fake_rc(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(net_range=net_ranges.pop(0), cut_set=["P1"])

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_rc, raising=False)

    first = reconcile_trade_roster(
        [_asset("P0", xvar=25.0)],
        [_asset("PA", xvar=25.0), _asset("PB", xvar=15.0)],
        pvo,
        snapshot,
    )
    second = reconcile_trade_roster(
        [_asset("P0", xvar=25.0)],
        [_asset("PA", xvar=25.0), _asset("PB", xvar=15.0)],
        pvo,
        snapshot,
    )

    assert first.base_evaluation.favors == "side_b"
    assert second.base_evaluation.favors == "side_b"
    assert first.adjusted_favors == "side_b"
    assert second.adjusted_favors == "side_b"
    assert first.adjusted_favors_status != second.adjusted_favors_status


def test_parity_straddling_range_keeps_legacy_favors_base_only(monkeypatch):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    def fake_straddling_rc(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(net_range=(0.0, 40.0), cut_set=["P1"])

    monkeypatch.setattr(
        reconciler, "simulate_capacity_scenarios", fake_straddling_rc, raising=False
    )

    result = reconcile_trade_roster(
        [_asset("P0", xvar=100.0)],
        [_asset("PA", xvar=70.0), _asset("PB", xvar=50.0)],
        pvo,
        snapshot,
    )

    assert result.base_evaluation.favors == "side_b"
    assert result.adjusted_received_value_range is not None
    assert (
        result.adjusted_received_value_range[0]
        < result.base_evaluation.side_a.side_value
        < result.adjusted_received_value_range[1]
    )
    assert result.adjusted_favors_status == "uncertain_range_crosses_parity"
    assert result.adjusted_favors == "side_b"


def test_rc_v1_blocked_result_returns_blocked_ranges_without_fabricated_zero(
    monkeypatch,
):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    def fake_blocked(*_args, **_kwargs) -> CapacityAuditResult:
        return CapacityAuditResult(
            status="blocked",
            capacity_health=None,
            candidates=[],
            scenarios=[],
            unrostered_pool_range={},
            excluded_counts={},
            caveats=["capacity_audit_blocked: duplicate sleeper_player_id"],
        )

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_blocked, raising=False)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert result.roster_penalty.penalty_status == "blocked"
    assert result.roster_penalty.forced_cut_value_at_risk_range is None
    assert result.roster_penalty.forced_cut_recovery_range is None
    assert result.adjusted_received_value_range is None
    assert result.adjusted_fairness_delta_range is None
    assert "capacity_audit_blocked" in " ".join(result.caveats)
    assert _count_ds_true(result.model_dump()) == 0
    _assert_no_verdict_tokens(result.model_dump())


def test_unavailable_pre_model_wire_yields_uncertain_range_not_zero(monkeypatch):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [
            _make_pvo_player("PA", xvar=20.0),
            _make_pvo_player("PB", xvar=20.0),
        ]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    def fake_unavailable(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(
            net_range=(0.0, 20.0),
            cut_set=["P1"],
            caveats=[
                "valuation_coverage_below_floor",
                "WR_waiver_range_unavailable_recovery_unverifiable",
                "best_case_recovery",
                "worst_case_recovery",
            ],
        )

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_unavailable, raising=False)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert result.roster_penalty.penalty_status == "uncertain_pool_unavailable"
    assert result.roster_penalty.forced_cut_value_at_risk_range == (0.0, 20.0)
    assert result.roster_penalty.forced_cut_recovery_range == (0.0, 20.0)
    caveats = " ".join(result.roster_penalty.penalty_caveats + result.caveats)
    assert "valuation_coverage_below_floor" in caveats
    assert "best_case_recovery" in caveats
    assert "worst_case_recovery" in caveats
    assert _count_ds_true(result.model_dump()) == 0
    _assert_no_verdict_tokens(result.model_dump())


def test_barren_pool_and_deficit_are_preserved_from_rc_scenario(monkeypatch):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    def fake_deficit(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(
            net_range=(20.0, 20.0),
            cut_set=["P1"],
            pool_deficits={"WR": 1},
            caveats=["wr_unrostered_pool_depleted_all_zero_value"],
        )

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_deficit, raising=False)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert result.roster_penalty.forced_cut_penalty_xvar == pytest.approx(20.0)
    assert result.roster_penalty.forced_cut_value_at_risk_range == (20.0, 20.0)
    assert result.roster_penalty.forced_cut_recovery_range == (0.0, 0.0)
    assert result.roster_penalty.pool_deficits == {"WR": 1}
    assert "depleted_all_zero_value" in " ".join(result.caveats)


def test_unvalued_cut_candidate_marks_net_range_incomplete(monkeypatch):
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [
            _make_pvo_player("P0", xvar=20.0),
            _make_pvo_player("P1", xvar=None, xvar_pct=5.0, engine_path="PRE_MODEL"),
            _make_pvo_player("PA", xvar=20.0),
        ]
    )
    snapshot = _make_snapshot(["P0", "P1"], roster_positions=["QB", "BN"], settings=settings)

    def fake_unvalued_cut(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(net_range=(0.0, 0.0), cut_set=["P1"])

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_unvalued_cut, raising=False)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA")], pvo, snapshot)

    caveats = " ".join(result.roster_penalty.penalty_caveats + result.caveats)
    assert result.roster_penalty.forced_cut_penalty_xvar == 0.0
    assert result.roster_penalty.forced_cut_value_at_risk_range is None
    assert result.roster_penalty.penalty_status == "blocked"
    assert "cut_player_value_unavailable:P1" in caveats


def test_legacy_overflow_and_rc_required_cut_divergence_is_caveated(monkeypatch):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)

    def fake_divergence(*_args, **_kwargs) -> CapacityAuditResult:
        return _rc_result(net_range=(4.0, 16.0), cut_set=["P1"], required_cuts=2)

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_divergence, raising=False)

    result = reconcile_trade_roster([_asset("P0")], [_asset("PA"), _asset("PB")], pvo, snapshot)

    assert result.roster_penalty.post_trade_overflow == 1
    assert "legacy_overflow_rc_required_cuts_divergence" in " ".join(result.caveats)


def test_base_trade_caveats_are_preserved_on_all_rc_paths(monkeypatch):
    pids = [f"P{i}" for i in range(20)]
    settings = dict(_STANDARD_SETTINGS, reserve_slots=0, taxi_slots=0)
    pvo = _make_pvo(
        [_make_pvo_player(pid, xvar=20.0) for pid in pids]
        + [_make_pvo_player("PA", xvar=20.0), _make_pvo_player("PB", xvar=20.0)]
    )
    snapshot = _make_snapshot(pids, roster_positions=_STANDARD_POSITIONS, settings=settings)
    base_caveat = "custom_base_trade_caveat"
    rc_modes: list[str] = []

    def fake_rc(*_args, **_kwargs) -> CapacityAuditResult:
        mode = rc_modes.pop(0)
        if mode == "blocked":
            return CapacityAuditResult(
                status="blocked",
                capacity_health=None,
                candidates=[],
                scenarios=[],
                unrostered_pool_range={},
                excluded_counts={},
                caveats=["capacity_audit_blocked"],
            )
        if mode == "unvalued":
            return _rc_result(net_range=(0.0, 0.0), cut_set=["P1"])
        return _rc_result(net_range=(4.0, 16.0), cut_set=["P1"], caveats=["rc_caveat"])

    monkeypatch.setattr(reconciler, "simulate_capacity_scenarios", fake_rc, raising=False)

    for mode in ("normal", "unvalued", "blocked"):
        rc_modes.append(mode)
        result = reconcile_trade_roster(
            [TradeAsset(player_id="P0", xvar=25.0, position="WR", caveat=base_caveat)],
            [_asset("PA"), _asset("PB")],
            pvo,
            snapshot,
        )

        assert base_caveat in result.base_evaluation.caveats
        assert base_caveat in result.caveats


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
