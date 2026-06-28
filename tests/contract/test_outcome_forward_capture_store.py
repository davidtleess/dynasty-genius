"""Realized-Outcome Loop T3 RED: outcome ingestion store + week-finalized gate.

The outcome store is an append-only weekly fact store. It ingests only finalized
weeks from an injected schedule/finality payload, never from the presence of stat
rows. Season-to-date and rolling aggregates are computed at read time from the
immutable weekly facts.
"""

from __future__ import annotations

import math

import pytest

from src.dynasty_genius.capture.outcome_forward_capture_store import (
    OutcomeForwardCaptureConflictError,
    OutcomeForwardCaptureStore,
    OutcomeForwardCaptureValidationError,
    week_status,
)


def _schedule(
    *,
    season: int = 2026,
    week: int = 1,
    expected_game_count: int = 1,
    statuses: tuple[str, ...] = ("final",),
) -> dict:
    return {
        "season": season,
        "week": week,
        "expected_game_count": expected_game_count,
        "games": [
            {
                "season": season,
                "week": week,
                "game_id": f"{season}_{week}_{index}",
                "status": status,
            }
            for index, status in enumerate(statuses, start=1)
        ],
    }


def _stat(
    player_id: str,
    *,
    week: int,
    points: float | None,
    season: int = 2026,
    status: str = "active",
    game_played: bool = True,
) -> dict:
    return {
        "player_id": player_id,
        "season": season,
        "week": week,
        "fantasy_points_ppr": points,
        "player_status": status,
        "game_played": game_played,
    }


def _util(
    player_id: str,
    *,
    week: int,
    season: int = 2026,
    snap_share: float | None = None,
    route_participation: float | None = None,
    target_share_nfl: float | None = None,
) -> dict:
    row = {"player_id": player_id, "season": season, "week": week}
    if snap_share is not None:
        row["snap_share_realized"] = snap_share
    if route_participation is not None:
        row["route_participation_realized"] = route_participation
    if target_share_nfl is not None:
        row["target_share_nfl_realized"] = target_share_nfl
    return row


def _get(obj, key: str):
    if isinstance(obj, dict):
        return obj[key]
    return getattr(obj, key)


def _maybe_get(obj, key: str):
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _field(row, name: str) -> dict:
    value = _get(row, name)
    if isinstance(value, dict):
        return value
    return {"value": getattr(value, "value"), "status": getattr(value, "status")}


def test_week_status_uses_injected_schedule_not_stat_rows(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    complete = _schedule(expected_game_count=2, statuses=("final", "final"))
    missing_game = _schedule(expected_game_count=2, statuses=("final",))
    postponed = _schedule(expected_game_count=2, statuses=("final", "postponed"))
    no_games = _schedule(expected_game_count=0, statuses=())

    assert week_status(2026, 1, schedule=complete) == "finalized"
    assert week_status(2026, 1, schedule=missing_game) == "not_finalized"
    assert week_status(2026, 1, schedule=postponed) == "not_finalized"
    assert week_status(2026, 1, schedule=no_games) == "not_finalized"

    # Stat rows are intentionally complete, but the injected schedule is not.
    # The store must not infer finality from player rows or ingest a partial week.
    result = store.ingest_week(
        2026,
        1,
        stat_rows=[_stat("00-A", week=1, points=18.0)],
        util_rows=[_util("00-A", week=1, snap_share=0.7)],
        schedule=postponed,
    )

    assert _get(result, "week_status") == "not_finalized"
    assert _get(result, "rows_written") == 0
    assert _get(result, "noop_reason") == "week_not_finalized"
    assert store.read_outcomes(2026, "00-A") is None


def test_finalized_week_ingests_stats_and_separate_util_statuses(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    result = store.ingest_week(
        2026,
        1,
        stat_rows=[_stat("00-A", week=1, points=21.5)],
        util_rows=[_util("00-A", week=1, snap_share=0.62, target_share_nfl=0.24)],
        schedule=_schedule(),
    )
    outcome = store.read_outcomes(2026, "00-A")

    assert _get(result, "week_status") == "finalized"
    assert _get(result, "rows_written") == 1
    assert _get(outcome, "gsis_id") == "00-A"
    assert _get(outcome, "season") == 2026
    assert _get(outcome, "games_played") == 1
    assert _get(outcome, "ppg_to_date") == pytest.approx(21.5)
    assert _get(outcome, "ppg_rolling_3") == pytest.approx(21.5)
    assert _get(outcome, "ppg_rolling_5") == pytest.approx(21.5)
    assert _get(outcome, "ppg_rolling_8") == pytest.approx(21.5)
    assert _get(outcome, "player_status") == "active"
    assert _field(outcome, "snap_share_realized") == {
        "value": pytest.approx(0.62),
        "status": "ok",
    }
    assert _field(outcome, "route_participation_realized") == {
        "value": None,
        "status": "unavailable",
    }
    assert _field(outcome, "target_share_nfl_realized") == {
        "value": pytest.approx(0.24),
        "status": "ok",
    }


def test_append_only_idempotent_reingest_and_conflict_detection(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    schedule = _schedule()
    stat_rows = [_stat("00-A", week=1, points=10.0)]

    first = store.ingest_week(
        2026, 1, stat_rows=stat_rows, util_rows=[], schedule=schedule
    )
    second = store.ingest_week(
        2026, 1, stat_rows=stat_rows, util_rows=[], schedule=schedule
    )

    assert _get(first, "rows_written") == 1
    assert _get(second, "rows_written") == 0
    assert _get(store.read_outcomes(2026, "00-A"), "games_played") == 1

    with pytest.raises(OutcomeForwardCaptureConflictError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[_stat("00-A", week=1, points=11.0)],
            util_rows=[],
            schedule=schedule,
        )
    assert _get(store.read_outcomes(2026, "00-A"), "ppg_to_date") == pytest.approx(
        10.0
    )


def test_duplicate_same_key_stat_rows_with_different_content_reject_before_write(
    tmp_path,
) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[
                _stat("00-A", week=1, points=18.0),
                _stat("00-A", week=1, points=7.0),
            ],
            util_rows=[],
            schedule=_schedule(),
        )

    assert store.read_outcomes(2026, "00-A") is None


def test_duplicate_same_key_stat_rows_with_identical_content_collapse(
    tmp_path,
) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    row = _stat("00-A", week=1, points=18.0)

    result = store.ingest_week(
        2026,
        1,
        stat_rows=[row, dict(row)],
        util_rows=[],
        schedule=_schedule(),
    )

    assert _get(result, "rows_written") == 1
    assert _get(store.read_outcomes(2026, "00-A"), "ppg_to_date") == pytest.approx(
        18.0
    )


def test_stat_row_season_or_week_misalignment_rejects_before_write(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[_stat("00-A", season=2026, week=2, points=10.0)],
            util_rows=[],
            schedule=_schedule(),
        )
    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[_stat("00-B", season=2025, week=1, points=10.0)],
            util_rows=[],
            schedule=_schedule(),
        )

    assert store.read_outcomes(2026, "00-A") is None
    assert store.read_outcomes(2026, "00-B") is None


def test_duplicate_util_rows_with_different_content_reject_before_write(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[_stat("00-A", week=1, points=10.0)],
            util_rows=[
                _util("00-A", week=1, snap_share=0.1),
                _util("00-A", week=1, snap_share=0.9),
            ],
            schedule=_schedule(),
        )

    assert store.read_outcomes(2026, "00-A") is None


def test_duplicate_util_rows_with_identical_content_collapse(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    util_row = _util("00-A", week=1, snap_share=0.42)

    result = store.ingest_week(
        2026,
        1,
        stat_rows=[_stat("00-A", week=1, points=10.0)],
        util_rows=[util_row, dict(util_row)],
        schedule=_schedule(),
    )
    outcome = store.read_outcomes(2026, "00-A")

    assert _get(result, "rows_written") == 1
    assert _field(outcome, "snap_share_realized") == {
        "value": pytest.approx(0.42),
        "status": "ok",
    }


def test_read_outcomes_computes_ppg_to_date_and_rolling_windows(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    for week in range(1, 9):
        store.ingest_week(
            2026,
            week,
            stat_rows=[_stat("00-A", week=week, points=float(week * 10))],
            util_rows=[],
            schedule=_schedule(week=week),
        )

    outcome = store.read_outcomes(2026, "00-A")

    assert _get(outcome, "games_played") == 8
    assert _get(outcome, "ppg_to_date") == pytest.approx(45.0)
    assert _get(outcome, "ppg_rolling_3") == pytest.approx(70.0)
    assert _get(outcome, "ppg_rolling_5") == pytest.approx(60.0)
    assert _get(outcome, "ppg_rolling_8") == pytest.approx(45.0)


def test_survivorship_complete_retains_zero_game_status_rows(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    store.ingest_week(
        2026,
        1,
        stat_rows=[_stat("00-A", week=1, points=12.0)],
        util_rows=[],
        schedule=_schedule(week=1),
    )
    store.ingest_week(
        2026,
        2,
        stat_rows=[
            _stat(
                "00-A",
                week=2,
                points=None,
                status="injured",
                game_played=False,
            )
        ],
        util_rows=[],
        schedule=_schedule(week=2),
    )

    outcome = store.read_outcomes(2026, "00-A")

    assert _get(outcome, "games_played") == 1
    assert _get(outcome, "ppg_to_date") == pytest.approx(12.0)
    assert _get(outcome, "ppg_rolling_3") == pytest.approx(12.0)
    assert _get(outcome, "player_status") == "injured"


@pytest.mark.parametrize("status", ["bye", "not_yet_played", "departed"])
def test_zero_game_player_is_retained_with_explicit_status(tmp_path, status) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    store.ingest_week(
        2026,
        1,
        stat_rows=[
            _stat(
                "00-Z",
                week=1,
                points=None,
                status=status,
                game_played=False,
            )
        ],
        util_rows=[],
        schedule=_schedule(),
    )
    outcome = store.read_outcomes(2026, "00-Z")

    assert _get(outcome, "gsis_id") == "00-Z"
    assert _get(outcome, "games_played") == 0
    assert _get(outcome, "ppg_to_date") is None
    assert _get(outcome, "ppg_rolling_3") is None
    assert _get(outcome, "player_status") == status


def test_malformed_rows_and_non_finite_points_reject_before_any_write(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    schedule = _schedule()

    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[{"season": 2026, "week": 1, "fantasy_points_ppr": 10.0}],
            util_rows=[],
            schedule=schedule,
        )
    assert store.read_outcomes(2026, "00-BAD") is None

    with pytest.raises(OutcomeForwardCaptureValidationError):
        store.ingest_week(
            2026,
            1,
            stat_rows=[_stat("00-BAD", week=1, points=math.inf)],
            util_rows=[],
            schedule=schedule,
        )
    assert store.read_outcomes(2026, "00-BAD") is None


def test_empty_finalized_week_noops_without_crash(tmp_path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")

    result = store.ingest_week(
        2026,
        1,
        stat_rows=[],
        util_rows=[],
        schedule=_schedule(expected_game_count=1, statuses=("final",)),
    )

    assert _get(result, "week_status") == "finalized"
    assert _get(result, "rows_written") == 0
    assert _maybe_get(result, "noop_reason") in (None, "empty_week")
    assert store.read_outcomes(2026, "00-NOBODY") is None
