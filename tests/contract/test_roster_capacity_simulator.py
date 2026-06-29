from __future__ import annotations

import math
from typing import Any

import pytest

from src.dynasty_genius.roster_capacity.scenario_simulator import (
    simulate_capacity_scenarios,
)


def _snapshot(
    player_ids: list[str],
    *,
    snapshot_player_ids: list[str] | None = None,
    positions: dict[str, str] | None = None,
    active_slots: int = 2,
    reserve_slots: int = 0,
    taxi_slots: int = 0,
    reserve: list[str] | None = None,
    taxi: list[str] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_settings = {
        "reserve_slots": reserve_slots,
        "taxi_slots": taxi_slots,
        "taxi_years": 2,
        "taxi_allow_vets": 0,
        **(settings or {}),
    }
    return {
        "league": {
            "roster_positions": ["QB"] * active_slots,
            "settings": merged_settings,
        },
        "rosters": [
            {
                "roster_id": 1,
                "owner_id": "david",
                "players": player_ids,
                "starters": player_ids[:active_slots],
                "reserve": reserve or [],
                "taxi": taxi or [],
            }
        ],
        "players": [
            {
                "sleeper_player_id": pid,
                "player": {"position": (positions or {}).get(pid, "WR")},
                "league_context": {
                    "rostered": True,
                    "roster_id": 1,
                    "on_ir": pid in set(reserve or []),
                    "on_taxi": pid in set(taxi or []),
                },
            }
            for pid in (snapshot_player_ids if snapshot_player_ids is not None else player_ids)
        ],
    }


def _pvo_player(
    pid: str,
    *,
    position: str = "WR",
    xvar: float | None = 10.0,
    dvs: float | None = 60.0,
    xvar_pct: float | None = 50.0,
    projection_2y: float | None = 11.5,
    engine_path: str = "ENGINE_B",
    sleeper_status: str = "active",
) -> dict[str, Any]:
    return {
        "sleeper_player_id": pid,
        "player": {
            "full_name": f"Player {pid}",
            "position": position,
            "age": 24.0,
            "years_exp": 2,
            "sleeper_status": sleeper_status,
        },
        "valuation": {
            "engine_path": engine_path,
            "xvar": xvar,
            "dynasty_value_score": dvs,
            "xvar_percentile_overall": xvar_pct,
        },
        "projection_2y": projection_2y,
        "decision_supported": False,
    }


def _pvo(players: list[dict[str, Any]]) -> dict[str, Any]:
    return {"players": players, "decision_supported": False}


def _candidate(result: Any, sleeper_id: str) -> Any:
    return next(c for c in result.candidates if c.sleeper_player_id == sleeper_id)


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def _pool(result: Any, position: str) -> Any:
    return result.unrostered_pool_range[position]


def _scenario(result: Any, index: int = 0) -> Any:
    return result.scenarios[index]


def _strings(value: object) -> list[str]:
    if hasattr(value, "model_dump"):
        return _strings(value.model_dump())
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            if isinstance(key, str):
                out.append(key)
            out.extend(_strings(item))
        return out
    if isinstance(value, list | tuple):
        out: list[str] = []
        for item in value:
            out.extend(_strings(item))
        return out
    return [value] if isinstance(value, str) else []


def test_capacity_health_reports_total_capacity_and_active_slot_pressure() -> None:
    snapshot = _snapshot(
        ["p1", "p2", "p3", "p4", "p5"],
        active_slots=2,
        reserve_slots=1,
        taxi_slots=1,
    )
    pvo = _pvo([
        _pvo_player("p1", xvar_pct=90.0),
        _pvo_player("p2", xvar_pct=80.0),
        _pvo_player("p3", xvar_pct=30.0),
        _pvo_player("p4", xvar_pct=70.0),
        _pvo_player("p5", xvar_pct=60.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)

    assert result.status == "ok"
    assert result.capacity_health.total_players == 5
    assert result.capacity_health.total_capacity == 4
    assert result.capacity_health.total_capacity_cuts_required == 1
    assert result.capacity_health.active_slot_overflow == 3
    assert [c.sleeper_player_id for c in result.candidates] == [
        "p3",
        "p5",
        "p4",
        "p2",
        "p1",
    ]


def test_active_slot_overflow_is_distinct_from_total_capacity_cuts_required() -> None:
    snapshot = _snapshot(
        ["p1", "p2", "p3", "p4"],
        active_slots=2,
        reserve_slots=2,
        taxi_slots=0,
    )
    pvo = _pvo([_pvo_player(pid, xvar_pct=50.0 + i) for i, pid in enumerate(["p1", "p2", "p3", "p4"])])

    result = simulate_capacity_scenarios(pvo, snapshot)

    assert result.status == "ok"
    assert result.capacity_health.total_capacity_cuts_required == 0
    assert result.capacity_health.active_slot_overflow == 2


def test_candidates_join_raw_value_fields_from_pvo_not_cut_engine() -> None:
    snapshot = _snapshot(["p1", "p2", "p3"], active_slots=1)
    pvo = _pvo([
        _pvo_player("p1", xvar=21.25, dvs=81.0, xvar_pct=99.0, projection_2y=17.75),
        _pvo_player("p2", xvar=3.5, dvs=45.0, xvar_pct=10.0, projection_2y=8.25),
        _pvo_player("p3", xvar=15.0, dvs=65.0, xvar_pct=80.0, projection_2y=13.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    candidate = _candidate(result, "p2")

    assert candidate.xvar_pct == 10.0
    assert candidate.dvs == 45.0
    assert candidate.raw_xvar == 3.5
    assert candidate.median_projection_2y == 8.25
    assert candidate.value_field_status == {
        "xvar": "ok",
        "dvs": "ok",
        "projection_2y": "ok",
        "position": "ok",
        "model": "ok",
    }


def test_missing_pvo_join_marks_per_field_unavailable_and_counts_exclusion() -> None:
    snapshot = _snapshot(["p1", "missing"], active_slots=1)
    pvo = _pvo([_pvo_player("p1", xvar_pct=90.0)])

    result = simulate_capacity_scenarios(pvo, snapshot)
    candidate = _candidate(result, "missing")

    assert result.status == "ok"
    assert candidate.raw_xvar is None
    assert candidate.dvs is None
    assert candidate.xvar_pct is None
    assert candidate.median_projection_2y is None
    assert candidate.value_field_status == {
        "xvar": "unavailable",
        "dvs": "unavailable",
        "projection_2y": "unavailable",
        "position": "unknown_position",
        "model": "pre_model",
    }
    assert result.excluded_counts["missing_pvo_join"] == 1


def test_duplicate_pvo_sleeper_id_blocks_instead_of_last_win_join() -> None:
    snapshot = _snapshot(["dup", "other"], active_slots=1)
    pvo = _pvo([
        _pvo_player("dup", xvar=1.0, xvar_pct=90.0, projection_2y=2.0),
        _pvo_player("dup", xvar=99.0, xvar_pct=1.0, projection_2y=99.0),
        _pvo_player("other", xvar=5.0, xvar_pct=50.0, projection_2y=6.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)

    assert result.status == "blocked"
    assert result.capacity_health is None
    assert result.candidates == []
    assert result.excluded_counts == {}
    assert any("duplicate" in caveat and "dup" in caveat for caveat in result.caveats)
    assert _decision_supported_true_count(result) == 0


def test_candidate_source_distinguishes_forced_review_from_capacity_ordered() -> None:
    snapshot = _snapshot(
        ["active1", "active2", "bad_ir"],
        active_slots=1,
        reserve_slots=1,
        reserve=["bad_ir"],
        settings={"reserve_allow_out": 1},
    )
    pvo = _pvo([
        _pvo_player("active1", xvar_pct=60.0),
        _pvo_player("active2", xvar_pct=20.0),
        _pvo_player("bad_ir", xvar_pct=10.0, sleeper_status="active"),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)

    forced = _candidate(result, "bad_ir")
    normal = _candidate(result, "active2")
    assert forced.cut_priority == 0
    assert forced.candidate_source == "forced_review"
    assert normal.cut_priority > 0
    assert normal.candidate_source == "capacity_ordered"


def test_malformed_data_returns_blocked_result_not_exception() -> None:
    result = simulate_capacity_scenarios({"not_players": []}, _snapshot(["p1"]))

    assert result.status == "blocked"
    assert result.capacity_health is None
    assert result.candidates == []
    assert result.caveats
    assert _decision_supported_true_count(result) == 0


def test_malformed_pvo_row_returns_blocked_result_not_exception() -> None:
    result = simulate_capacity_scenarios({"players": [123]}, _snapshot(["p1"]))

    assert result.status == "blocked"
    assert result.capacity_health is None
    assert result.candidates == []
    assert result.caveats
    assert _decision_supported_true_count(result) == 0


def test_malformed_snapshot_value_error_returns_blocked_result_not_exception() -> None:
    snapshot = _snapshot(["p1"])
    snapshot["league"]["roster_positions"] = ["QB", "IR"]
    result = simulate_capacity_scenarios(_pvo([_pvo_player("p1")]), snapshot)

    assert result.status == "blocked"
    assert result.capacity_health is None
    assert result.candidates == []
    assert result.caveats
    assert _decision_supported_true_count(result) == 0


def test_wrong_type_arguments_raise_for_api_misuse() -> None:
    with pytest.raises((TypeError, ValueError)):
        simulate_capacity_scenarios([], _snapshot(["p1"]))  # type: ignore[arg-type]

    with pytest.raises((TypeError, ValueError)):
        simulate_capacity_scenarios(_pvo([]), [])  # type: ignore[arg-type]


def test_non_finite_value_fields_are_unavailable_per_field() -> None:
    snapshot = _snapshot(["bad", "ok"], active_slots=1)
    pvo = _pvo([
        _pvo_player(
            "bad",
            xvar=math.inf,
            dvs=math.nan,
            xvar_pct=1.0,
            projection_2y=-math.inf,
        ),
        _pvo_player("ok", xvar=10.0, dvs=50.0, xvar_pct=90.0, projection_2y=11.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    candidate = _candidate(result, "bad")

    assert candidate.raw_xvar is None
    assert candidate.dvs is None
    assert candidate.median_projection_2y is None
    assert candidate.value_field_status["xvar"] == "unavailable"
    assert candidate.value_field_status["dvs"] == "unavailable"
    assert candidate.value_field_status["projection_2y"] == "unavailable"
    assert result.excluded_counts["non_finite_value_field"] == 3


def test_decision_supported_false_recursively() -> None:
    snapshot = _snapshot(["p1", "p2"], active_slots=1)
    pvo = _pvo([_pvo_player("p1", xvar_pct=20.0), _pvo_player("p2", xvar_pct=80.0)])

    result = simulate_capacity_scenarios(pvo, snapshot)

    assert result.decision_supported is False
    assert _decision_supported_true_count(result) == 0


def test_unrostered_pool_range_uses_wide_top_k_raw_xvar_ordered_descending() -> None:
    rostered = ["rostered1", "rostered2"]
    waiver_ids = [f"wr{i}" for i in range(1, 13)]
    snapshot = _snapshot(
        rostered,
        active_slots=1,
        snapshot_player_ids=rostered + waiver_ids,
    )
    pvo = _pvo(
        [_pvo_player(pid, xvar=50.0, xvar_pct=80.0) for pid in rostered]
        + [
            _pvo_player("wr1", xvar=12.0),
            _pvo_player("wr2", xvar=1.0),
            _pvo_player("wr3", xvar=7.5),
            _pvo_player("wr4", xvar=3.0),
            _pvo_player("wr5", xvar=9.0),
            _pvo_player("wr6", xvar=6.0),
            _pvo_player("wr7", xvar=4.5),
            _pvo_player("wr8", xvar=2.0),
            _pvo_player("wr9", xvar=11.0),
            _pvo_player("wr10", xvar=8.0),
            _pvo_player("wr11", xvar=5.5),
            _pvo_player("wr12", xvar=10.0),
        ]
    )

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "ok"
    assert wr_pool.top_k_values == [12.0, 11.0, 10.0, 9.0, 8.0, 7.5, 6.0, 5.5]
    assert wr_pool.low == 5.5
    assert wr_pool.high == 12.0
    assert wr_pool.pool_size == 12
    assert "median" not in wr_pool.model_dump()
    assert "std" not in wr_pool.model_dump()


def test_unrostered_pool_excludes_players_rostered_only_via_starters_taxi_or_reserve() -> None:
    snapshot = _snapshot(
        ["active"],
        active_slots=1,
        reserve=["reserve_only"],
        taxi=["taxi_only"],
        snapshot_player_ids=[
            "active",
            "starter_only",
            "reserve_only",
            "taxi_only",
            "free1",
            "free2",
            "free3",
            "free4",
            "free5",
            "free6",
            "free7",
            "free8",
        ],
    )
    snapshot["rosters"][0]["starters"] = ["starter_only"]
    pvo = _pvo([
        _pvo_player("active", xvar=1.0),
        _pvo_player("starter_only", xvar=99.0),
        _pvo_player("reserve_only", xvar=98.0),
        _pvo_player("taxi_only", xvar=97.0),
        *[_pvo_player(f"free{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "ok"
    assert wr_pool.top_k_values == [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    assert 99.0 not in wr_pool.top_k_values
    assert 98.0 not in wr_pool.top_k_values
    assert 97.0 not in wr_pool.top_k_values


def test_unrostered_pool_retains_enough_values_for_largest_requested_scenario() -> None:
    waiver_ids = [f"wr{i}" for i in range(1, 13)]
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *waiver_ids],
    )
    pvo = _pvo([
        _pvo_player("rostered", xvar=30.0, xvar_pct=50.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 13)],
    ])

    result = simulate_capacity_scenarios(
        pvo,
        snapshot,
        scenarios=[{"clear_n": 10}],
    )
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "ok"
    assert wr_pool.top_k_values == [12.0, 11.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
    assert wr_pool.low == 5.0
    assert wr_pool.high == 12.0


def test_unrostered_pool_snapshot_staleness_fails_closed() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *[f"wr{i}" for i in range(1, 9)]],
    )
    snapshot["captured_at"] = "2020-01-01T00:00:00+00:00"
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert wr_pool.caveats


@pytest.mark.parametrize("bad_captured_at", ["not-a-date", 12345])
def test_unrostered_pool_present_malformed_captured_at_fails_closed(
    bad_captured_at: object,
) -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *[f"wr{i}" for i in range(1, 9)]],
    )
    snapshot["captured_at"] = bad_captured_at
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert result.status == "ok"
    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert any("snapshot_freshness_unverifiable" in caveat for caveat in wr_pool.caveats)


def test_unrostered_pool_incomplete_roster_coverage_fails_closed() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *[f"wr{i}" for i in range(1, 9)]],
    )
    snapshot["coverage"] = {"rostered_players_missing_from_snapshot": ["missing_rostered"]}
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert any("coverage" in caveat for caveat in wr_pool.caveats)


def test_unrostered_pool_thin_position_pool_fails_closed() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", "wr1", "wr2", "wr3"],
    )
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        _pvo_player("wr1", xvar=1.0),
        _pvo_player("wr2", xvar=2.0),
        _pvo_player("wr3", xvar=3.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert wr_pool.pool_size == 3


def test_unrostered_pool_valuation_coverage_floor_fails_closed() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *[f"wr{i}" for i in range(1, 11)]],
    )
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        _pvo_player("wr1", xvar=10.0),
        _pvo_player("wr2", xvar=9.0),
        *[
            _pvo_player(f"wr{i}", xvar=None, engine_path="PRE_MODEL")
            for i in range(3, 11)
        ],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert any("valuation_coverage" in caveat for caveat in wr_pool.caveats)
    assert result.excluded_counts["unrostered_pool_value_unavailable"] == 8


def test_unrostered_pool_barren_zero_value_pool_is_ok_with_caveat() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        *[_pvo_player(f"wr{i}", xvar=0.0) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "ok"
    assert wr_pool.top_k_values == [0.0] * 8
    assert wr_pool.low == 0.0
    assert wr_pool.high == 0.0
    assert any("depleted" in caveat or "barren" in caveat for caveat in wr_pool.caveats)


def test_unrostered_pool_non_finite_and_missing_values_are_counted_and_excluded() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=[
            "rostered",
            "bad_inf",
            "bad_missing",
            *[f"wr{i}" for i in range(1, 9)],
        ],
    )
    pvo = _pvo([
        _pvo_player("rostered", xvar=20.0),
        _pvo_player("bad_inf", xvar=math.inf),
        _pvo_player("bad_missing", xvar=None),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "ok"
    assert wr_pool.top_k_values == [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    assert result.excluded_counts["unrostered_pool_value_unavailable"] == 2


def test_unrostered_pool_empty_position_pool_unavailable_without_crash() -> None:
    snapshot = _snapshot(
        ["rostered"],
        active_slots=1,
        snapshot_player_ids=["rostered"],
    )
    pvo = _pvo([_pvo_player("rostered", xvar=20.0)])

    result = simulate_capacity_scenarios(pvo, snapshot)
    wr_pool = _pool(result, "WR")

    assert wr_pool.status == "waiver_range_unavailable"
    assert wr_pool.low is None
    assert wr_pool.high is None
    assert wr_pool.pool_size == 0


def test_default_clear_n_scenario_uses_single_player_value_at_risk_orientation() -> None:
    snapshot = _snapshot(
        ["cut1", "next1"],
        active_slots=1,
        snapshot_player_ids=["cut1", "next1", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("cut1", xvar=5.0, xvar_pct=1.0),
        _pvo_player("next1", xvar=8.0, xvar_pct=2.0),
        _pvo_player("wr1", xvar=6.0),
        _pvo_player("wr2", xvar=4.0),
        _pvo_player("wr3", xvar=2.0),
        _pvo_player("wr4", xvar=0.0),
        *[_pvo_player(f"wr{i}", xvar=0.0) for i in range(5, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot)
    scenario = _scenario(result)

    assert scenario.cut_set == ["cut1"]
    assert scenario.cumulative_value_at_risk == (-1.0, 5.0)
    assert scenario.marginal_next_candidate_cost == (2.0, 8.0)
    assert "marginal_next_candidate_id" not in scenario.model_dump()
    assert "marginal_next_candidate_name" not in scenario.model_dump()


def test_depletion_aware_cumulative_value_at_risk_uses_exact_n_deep_formula() -> None:
    snapshot = _snapshot(
        ["cut1", "cut2", "next1"],
        active_slots=1,
        snapshot_player_ids=["cut1", "cut2", "next1", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("cut1", xvar=10.0, xvar_pct=1.0),
        _pvo_player("cut2", xvar=9.0, xvar_pct=2.0),
        _pvo_player("next1", xvar=30.0, xvar_pct=99.0),
        _pvo_player("wr1", xvar=8.0),
        _pvo_player("wr2", xvar=7.0),
        _pvo_player("wr3", xvar=6.0),
        _pvo_player("wr4", xvar=5.0),
        _pvo_player("wr5", xvar=4.0),
        _pvo_player("wr6", xvar=3.0),
        _pvo_player("wr7", xvar=2.0),
        _pvo_player("wr8", xvar=1.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 2}])
    scenario = _scenario(result)

    assert scenario.cut_set == ["cut1", "cut2"]
    assert scenario.cumulative_value_at_risk == (4.0, 16.0)
    assert scenario.cumulative_value_at_risk != (2 * (10.0 - 8.0), 2 * (10.0 - 1.0))
    assert scenario.cumulative_value_at_risk[0] <= scenario.cumulative_value_at_risk[1]


@pytest.mark.parametrize("captured_at", ["2020-01-01T00:00:00+00:00", "not-a-date"])
def test_unavailable_pool_widens_scenario_uncertainty_instead_of_zero_recovery(
    captured_at: str,
) -> None:
    snapshot = _snapshot(
        ["cut1", "cut2"],
        active_slots=1,
        snapshot_player_ids=["cut1", "cut2", *[f"wr{i}" for i in range(1, 9)]],
    )
    snapshot["captured_at"] = captured_at
    pvo = _pvo([
        _pvo_player("cut1", xvar=10.0, xvar_pct=1.0),
        _pvo_player("cut2", xvar=9.0, xvar_pct=2.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 2}])
    scenario = _scenario(result)

    assert result.status == "ok"
    assert _pool(result, "WR").status == "waiver_range_unavailable"
    assert scenario.cumulative_value_at_risk == (0.0, 19.0)
    assert scenario.cumulative_value_at_risk != (19.0, 19.0)
    assert scenario.pool_deficits == {}
    assert any(
        "WR_waiver_range_unavailable_recovery_unverifiable" in caveat
        for caveat in scenario.caveats
    )


def test_pool_deficit_is_structured_when_cuts_exceed_valid_pool_size() -> None:
    cut_ids = [f"cut{i}" for i in range(1, 7)]
    snapshot = _snapshot(
        cut_ids,
        active_slots=1,
        snapshot_player_ids=[*cut_ids, "wr1", "wr2", "wr3", "wr4"],
    )
    pvo = _pvo([
        *[_pvo_player(pid, xvar=10.0, xvar_pct=float(i)) for i, pid in enumerate(cut_ids, 1)],
        _pvo_player("wr1", xvar=8.0),
        _pvo_player("wr2", xvar=7.0),
        _pvo_player("wr3", xvar=6.0),
        _pvo_player("wr4", xvar=5.0),
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 6}])
    scenario = _scenario(result)

    assert _pool(result, "WR").status == "ok"
    assert scenario.pool_deficits == {"WR": 2}
    assert any("pool" in caveat and "deficit" in caveat for caveat in scenario.caveats)
    assert not any("do not cut" in caveat.lower() for caveat in scenario.caveats)


def test_depletion_uses_real_n_deep_pool_when_scenario_n_exceeds_display_k() -> None:
    cut_ids = [f"cut{i}" for i in range(1, 11)]
    waiver_ids = [f"wr{i}" for i in range(1, 13)]
    snapshot = _snapshot(
        cut_ids,
        active_slots=1,
        snapshot_player_ids=[*cut_ids, *waiver_ids],
    )
    pvo = _pvo([
        *[_pvo_player(pid, xvar=20.0, xvar_pct=float(i)) for i, pid in enumerate(cut_ids, 1)],
        *[_pvo_player(f"wr{i}", xvar=float(21 - i)) for i in range(1, 13)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 10}])
    scenario = _scenario(result)

    assert _pool(result, "WR").top_k_values == [20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0]
    assert scenario.pool_deficits == {}
    assert scenario.cumulative_value_at_risk == (45.0, 45.0)


def test_proposed_cuts_are_honored_with_exempt_and_off_roster_caveats() -> None:
    snapshot = _snapshot(
        ["valid", "taxi_player", "other"],
        active_slots=1,
        taxi=["taxi_player"],
        taxi_slots=1,
        snapshot_player_ids=["valid", "taxi_player", "other", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("valid", xvar=5.0, xvar_pct=1.0),
        _pvo_player("taxi_player", xvar=2.0, xvar_pct=2.0),
        _pvo_player("other", xvar=9.0, xvar_pct=3.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(
        pvo,
        snapshot,
        scenarios=[{"proposed_cuts": ["valid", "taxi_player", "ghost"]}],
    )
    scenario = _scenario(result)

    assert scenario.cut_set == ["valid"]
    assert any("taxi_player" in caveat for caveat in scenario.caveats)
    assert any("ghost" in caveat for caveat in scenario.caveats)


def test_clear_n_larger_than_available_candidates_caveats_without_crashing() -> None:
    snapshot = _snapshot(
        ["cut1", "cut2"],
        active_slots=1,
        snapshot_player_ids=["cut1", "cut2", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("cut1", xvar=5.0, xvar_pct=1.0),
        _pvo_player("cut2", xvar=6.0, xvar_pct=2.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 5}])
    scenario = _scenario(result)

    assert scenario.cut_set == ["cut1", "cut2"]
    assert any("clear_n" in caveat or "available" in caveat for caveat in scenario.caveats)


def test_mixed_position_zero_crossing_cumulative_range_is_unclamped() -> None:
    positions = {
        "wr_cut": "WR",
        "rb_cut": "RB",
        **{f"wr{i}": "WR" for i in range(1, 5)},
        **{f"rb{i}": "RB" for i in range(1, 5)},
    }
    snapshot = _snapshot(
        ["wr_cut", "rb_cut"],
        active_slots=1,
        snapshot_player_ids=["wr_cut", "rb_cut", *[f"wr{i}" for i in range(1, 5)], *[f"rb{i}" for i in range(1, 5)]],
        positions=positions,
    )
    pvo = _pvo([
        _pvo_player("wr_cut", position="WR", xvar=5.0, xvar_pct=1.0),
        _pvo_player("rb_cut", position="RB", xvar=4.0, xvar_pct=2.0),
        _pvo_player("wr1", position="WR", xvar=8.0),
        _pvo_player("wr2", position="WR", xvar=6.0),
        _pvo_player("wr3", position="WR", xvar=4.0),
        _pvo_player("wr4", position="WR", xvar=3.0),
        _pvo_player("rb1", position="RB", xvar=6.0),
        _pvo_player("rb2", position="RB", xvar=3.0),
        _pvo_player("rb3", position="RB", xvar=2.0),
        _pvo_player("rb4", position="RB", xvar=1.0),
    ])

    result = simulate_capacity_scenarios(
        pvo,
        snapshot,
        scenarios=[{"proposed_cuts": ["wr_cut", "rb_cut"]}],
    )
    scenario = _scenario(result)

    assert scenario.cumulative_value_at_risk == (-5.0, 5.0)
    assert scenario.cumulative_value_at_risk[0] < 0 < scenario.cumulative_value_at_risk[1]


def test_scenario_results_are_decision_supported_false_and_verdict_free() -> None:
    snapshot = _snapshot(
        ["cut1", "cut2"],
        active_slots=1,
        snapshot_player_ids=["cut1", "cut2", *[f"wr{i}" for i in range(1, 9)]],
    )
    pvo = _pvo([
        _pvo_player("cut1", xvar=5.0, xvar_pct=1.0),
        _pvo_player("cut2", xvar=6.0, xvar_pct=2.0),
        *[_pvo_player(f"wr{i}", xvar=float(i)) for i in range(1, 9)],
    ])

    result = simulate_capacity_scenarios(pvo, snapshot, scenarios=[{"clear_n": 1}])

    assert _decision_supported_true_count(result) == 0
    dumped = result.model_dump()
    assert "optimizer" not in dumped
    forbidden_phrases = ("safe to cut", "must keep", "do not cut", "drop him", "sell now")
    lowered_strings = [item.lower() for item in _strings(dumped)]
    for phrase in forbidden_phrases:
        assert all(phrase not in item for item in lowered_strings)
