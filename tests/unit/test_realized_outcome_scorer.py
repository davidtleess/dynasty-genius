"""Realized-Outcome Loop T4 RED: pure realized-outcome scorer.

The scorer is pure: predictions, point-in-time identity resolution, outcome rows,
and weekly realized-util facts are all injected. For Model Input Fidelity, these
tests encode source option B: ``score`` receives weekly realized-util facts inside
the ``outcomes`` input and computes the 4-week rolling realized utilization itself.
T3 remains an immutable weekly fact store; no scorer I/O is allowed.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from src.dynasty_genius.outcome_loop.realized_outcome_scorer import (
    RealizedOutcomeScoringValidationError,
    compute_model_precision_at_k,
    score,
)


class FakeBridge:
    def __init__(self, mapping: dict[str, dict[str, Any]]) -> None:
        self.mapping = mapping

    def resolve(self, sleeper_id: str | None, capture_date: str) -> dict[str, Any]:
        return self.mapping.get(
            str(sleeper_id),
            {
                "gsis_id": None,
                "dg_player_id": None,
                "pfr_id": None,
                "resolution_status": "unresolved",
            },
        )


def _prediction(
    index: int,
    *,
    position: str = "WR",
    projection: float | None = None,
    util_value: float = 0.50,
) -> dict[str, Any]:
    return {
        "capture_date": "2026-06-01",
        "sleeper_id": f"sid-{index}",
        "player_key": f"player-{index}",
        "position": position,
        "projection_2y": float(index if projection is None else projection),
        "utilization": {
            "snap_share": {"value": util_value, "role": "model_input"},
            "route_participation": {"value": 0.70, "role": "model_input"},
            "target_share_nfl": {"value": 0.25, "role": "diagnostic_only"},
        },
    }


def _bridge(count: int) -> FakeBridge:
    return FakeBridge(
        {
            f"sid-{index}": {
                "gsis_id": f"00-{index:04d}",
                "dg_player_id": f"dg-{index}",
                "pfr_id": f"Pfr{index:04d}",
                "resolution_status": "resolved",
            }
            for index in range(1, count + 1)
        }
    )


def _outcome(
    index: int,
    *,
    points: float | None = None,
    games_played: int = 8,
    player_status: str = "active",
    weekly_snap_values: list[float] | None = None,
    survivorship_floor_ppg: float | None = None,
) -> dict[str, Any]:
    if weekly_snap_values is None:
        weekly_snap_values = [0.40, 0.50, 0.60, 0.70]
    row: dict[str, Any] = {
        "outcome": {
            "gsis_id": f"00-{index:04d}",
            "season": 2026,
            "games_played": games_played,
            "ppg_to_date": points,
            "ppg_rolling_3": points,
            "ppg_rolling_5": points,
            "ppg_rolling_8": points,
            "player_status": player_status,
        },
        "weekly_util": [
            {
                "season": 2026,
                "week": week,
                "snap_share_realized": {"value": value, "status": "ok"},
                "route_participation_realized": {
                    "value": 0.70 + (week * 0.01),
                    "status": "ok",
                },
                "target_share_nfl_realized": {"value": 0.20, "status": "ok"},
            }
            for week, value in enumerate(weekly_snap_values, start=1)
        ],
    }
    if survivorship_floor_ppg is not None:
        row["survivorship_floor_ppg"] = survivorship_floor_ppg
    return row


def _outcomes(count: int, *, games_played: int = 8) -> dict[str, Any]:
    return {
        "players": {
            f"00-{index:04d}": _outcome(
                index,
                points=float(index),
                games_played=games_played,
            )
            for index in range(1, count + 1)
        }
    }


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {key: _dump(val) for key, val in vars(value).items()}
    if isinstance(value, dict):
        return {key: _dump(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_dump(item) for item in value]
    return value


def _assert_no_true_decision_supported(value: Any) -> None:
    dumped = _dump(value)
    if isinstance(dumped, dict):
        if "decision_supported" in dumped:
            assert dumped["decision_supported"] is False
        for child in dumped.values():
            _assert_no_true_decision_supported(child)
    elif isinstance(dumped, list):
        for child in dumped:
            _assert_no_true_decision_supported(child)


def test_metric_surface_is_metric_specific_and_excludes_market_outputs() -> None:
    predictions = [_prediction(index, projection=float(11 - index)) for index in range(1, 11)]
    outcomes = _outcomes(10)

    scorecard = score(predictions, outcomes, _bridge(10), as_of_week=8)
    body = _dump(scorecard)
    cohort = body["cohort_metrics"]["WR"]

    assert body["decision_supported"] is False
    assert cohort["status"] == "ok"
    assert cohort["eligible_count"] == 10
    assert cohort["spearman"]["bca_ci"] is not None
    assert cohort["kendall"]["bca_ci"] is not None
    assert "bca_ci" not in cohort["ndcg"]
    assert cohort["ndcg"]["value"] is not None
    assert cohort["precision_at_k"]["truth_def"] == "realized_top_k_within_position"
    assert "diff_wilson_ci95" not in cohort["precision_at_k"]
    assert "market_hit_rate" not in cohort["precision_at_k"]
    assert "ndcg_diff" not in str(body).lower()
    assert "market" not in str(cohort).lower()
    _assert_no_true_decision_supported(body)


def test_power_floor_blocks_small_or_immature_cohort_without_metric_values() -> None:
    predictions = [_prediction(index) for index in range(1, 10)]
    outcomes = _outcomes(9, games_played=3)

    body = _dump(score(predictions, outcomes, _bridge(9), as_of_week=3))
    cohort = body["cohort_metrics"]["WR"]

    assert cohort["status"] == "power_floor_not_met"
    assert cohort["eligible_count"] == 9
    assert cohort["spearman"]["value"] is None
    assert cohort["spearman"]["bca_ci"] is None
    assert cohort["kendall"]["value"] is None
    assert cohort["kendall"]["bca_ci"] is None
    assert cohort["ndcg"]["value"] is None
    assert "maturity_weight" not in str(body).lower()


def test_power_floor_blocks_mature_count_but_immature_games_cohort() -> None:
    predictions = [_prediction(index) for index in range(1, 11)]
    outcomes = _outcomes(10, games_played=3)

    body = _dump(score(predictions, outcomes, _bridge(10), as_of_week=3))
    cohort = body["cohort_metrics"]["WR"]

    assert cohort["status"] == "power_floor_not_met"
    assert cohort["eligible_count"] == 10
    assert cohort["spearman"]["value"] is None
    assert cohort["kendall"]["value"] is None
    assert cohort["ndcg"]["value"] is None
    assert cohort["precision_at_k"]["value"] is None


def test_partial_tracking_and_mif_partial_window_before_four_games() -> None:
    predictions = [_prediction(1, util_value=0.50)]
    outcomes = {
        "players": {
            "00-0001": _outcome(
                1,
                points=12.0,
                games_played=3,
                weekly_snap_values=[0.60, 0.70, 0.80],
            )
        }
    }

    body = _dump(score(predictions, outcomes, _bridge(1), as_of_week=3))
    row = body["tracking_rows"][0]

    assert row["decision_supported"] is False
    assert row["settlement_status"] == "partial"
    assert 0 < row["maturity_pct"] < 100
    assert row["realized_ppg_to_date"] == pytest.approx(12.0)
    assert row["realized_vs_expected_delta"] == pytest.approx(11.0)
    assert row["model_input_fidelity"]["snap_share"]["status"] == "partial_window"
    assert row["model_input_fidelity"]["snap_share"].get("delta") is None


def test_mif_uses_four_week_rolling_realized_util_for_model_input_fields_only() -> None:
    predictions = [_prediction(1, util_value=0.50)]
    outcomes = {
        "players": {
            "00-0001": _outcome(
                1,
                points=12.0,
                games_played=4,
                weekly_snap_values=[0.60, 0.70, 0.80, 0.90],
            )
        }
    }

    body = _dump(score(predictions, outcomes, _bridge(1), as_of_week=4))
    mif = body["tracking_rows"][0]["model_input_fidelity"]

    assert mif["snap_share"]["status"] == "ok"
    assert mif["snap_share"]["delta"] == pytest.approx(0.25)
    assert mif["route_participation"]["status"] == "ok"
    assert mif["target_share_nfl"]["status"] == "diagnostic_only"
    assert mif["target_share_nfl"].get("delta") is None


def test_unresolved_identity_is_excluded_with_count_and_missing_outcome_is_partial() -> None:
    bridge = FakeBridge(
        {
            "sid-1": {
                "gsis_id": None,
                "dg_player_id": None,
                "pfr_id": None,
                "resolution_status": "unresolved",
            },
            "sid-2": {
                "gsis_id": "00-0002",
                "dg_player_id": "dg-2",
                "pfr_id": "Pfr0002",
                "resolution_status": "resolved",
            },
        }
    )

    body = _dump(score([_prediction(1), _prediction(2)], {"players": {}}, bridge, as_of_week=2))

    assert body["excluded_counts"]["identity_unresolved"] == 1
    assert body["excluded_counts"]["missing_outcome"] == 1
    assert body["tracking_rows"][0]["gsis_id"] == "00-0002"
    assert body["tracking_rows"][0]["settlement_status"] == "partial"
    assert body["tracking_rows"][0]["realized_ppg_to_date"] is None
    assert body["cohort_metrics"]["WR"]["status"] == "power_floor_not_met"


def test_settled_zero_game_player_gets_survivorship_floor_and_stays_in_cohort() -> None:
    predictions = [_prediction(index, projection=float(index)) for index in range(1, 11)]
    outcomes = _outcomes(9, games_played=8)
    outcomes["players"]["00-0010"] = _outcome(
        10,
        points=None,
        games_played=0,
        player_status="departed",
        weekly_snap_values=[],
    )

    body = _dump(score(predictions, outcomes, _bridge(10), as_of_week=40))
    row = next(item for item in body["tracking_rows"] if item["gsis_id"] == "00-0010")
    cohort = body["cohort_metrics"]["WR"]

    assert row["settlement_status"] == "settled"
    assert row["realized_ppg_to_date"] == pytest.approx(1.4)
    assert row["realized_outcome_status"] == "survivorship_floor_applied"
    assert cohort["eligible_count"] == 10


def test_non_finite_prediction_or_outcome_rejects() -> None:
    with pytest.raises(RealizedOutcomeScoringValidationError):
        score([_prediction(1, projection=math.inf)], _outcomes(1), _bridge(1), as_of_week=8)

    bad_outcomes = {
        "players": {
            "00-0001": _outcome(1, points=math.nan, games_played=8),
        }
    }
    with pytest.raises(RealizedOutcomeScoringValidationError):
        score([_prediction(1)], bad_outcomes, _bridge(1), as_of_week=8)


def test_empty_cohort_no_crash_and_model_only_precision_shape() -> None:
    body = _dump(score([], {"players": {}}, FakeBridge({}), as_of_week=1))

    assert body["decision_supported"] is False
    assert body["tracking_rows"] == []
    assert body["cohort_metrics"] == {}
    assert body["excluded_counts"] == {}

    precision = compute_model_precision_at_k(
        {"a", "b"},
        {"b", "c"},
        k=2,
    )
    precision_body = _dump(precision)
    assert precision_body == {"model_hit_rate": 0.5, "hits": 1, "k": 2}
    assert "diff_wilson_ci95" not in precision_body
