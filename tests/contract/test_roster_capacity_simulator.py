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
                "player": {"position": "WR"},
                "league_context": {
                    "rostered": True,
                    "roster_id": 1,
                    "on_ir": pid in set(reserve or []),
                    "on_taxi": pid in set(taxi or []),
                },
            }
            for pid in player_ids
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
