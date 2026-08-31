"""Week finality DERIVED from the schedule, per David's ruling of 2026-08-31.

Verbatim: "a week ends after Monday Night Football every single week of the regular
season... look at the schedule for Week 1 and see when the last game in Week 1 is. When
that game is over, the week is final, and the stats are in."

The point of the design, and why it is better than the options it replaced: it swaps an
ASSERTION for a DERIVATION. "The feed says final" is a source's claim about itself. "The
last game of week 1 has ended" is a fact the schedule already contains and that nobody
has to be trusted to declare.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.dynasty_genius.eval.week_finality import derive_week_finality

ET = ZoneInfo("America/New_York")


def _week(*, mnf_score=(24, 27)) -> list[dict]:
    """A normal week 1: Thursday opener, a Sunday slate, and a Monday night closer."""
    return [
        {"game_id": "TNF", "gameday": "2025-09-04", "gametime": "20:20",
         "home_score": 21, "away_score": 20},
        {"game_id": "SUN", "gameday": "2025-09-07", "gametime": "13:00",
         "home_score": 27, "away_score": 13},
        {"game_id": "SNF", "gameday": "2025-09-07", "gametime": "20:20",
         "home_score": 41, "away_score": 40},
        {"game_id": "MNF", "gameday": "2025-09-08", "gametime": "20:15",
         "home_score": mnf_score[0], "away_score": mnf_score[1]},
    ]


def _at(dt: str) -> datetime:
    return datetime.fromisoformat(dt).replace(tzinfo=ET)


def test_the_week_is_final_once_the_last_game_has_ended() -> None:
    """David's Tuesday 3-4am: a 20:15 Monday kickoff is comfortably done by then."""
    out = derive_week_finality(_week(), season=2025, week=1, now=_at("2025-09-09T04:00"))
    assert {g["status"] for g in out["games"]} == {"final"}
    assert out["expected_game_count"] == 4


def test_the_week_is_not_final_while_monday_night_is_still_being_played() -> None:
    """The Sunday games are long over and their scores are in. The WEEK is not."""
    out = derive_week_finality(_week(), season=2025, week=1, now=_at("2025-09-08T22:00"))
    assert "final" not in {g["status"] for g in out["games"]}


def test_a_sunday_afternoon_mid_slate_is_not_final() -> None:
    out = derive_week_finality(_week(), season=2025, week=1, now=_at("2025-09-07T16:00"))
    statuses = {g["game_id"]: g["status"] for g in out["games"]}
    assert statuses["TNF"] == "result_observed_unverified"
    assert statuses["MNF"] == "scheduled"


def test_a_postponed_game_keeps_the_week_open() -> None:
    """A game with no score after the week's clock has run is exactly the case David's
    'at the very least for the regular season' caveat points at. Staying non-final is the
    conservative answer and it is the right one: grading a week that has not finished
    playing is worse than grading it late."""
    games = _week()
    games[-1]["home_score"] = None
    games[-1]["away_score"] = None
    out = derive_week_finality(games, season=2025, week=1, now=_at("2025-09-09T04:00"))
    statuses = {g["game_id"]: g["status"] for g in out["games"]}
    assert statuses["MNF"] == "scheduled"
    assert statuses["TNF"] == "final"


def test_the_buffer_is_what_delays_finality_not_the_kickoff() -> None:
    """Finality is not 'the last game kicked off'. A game takes hours and the stats settle
    after it. Immediately after kickoff the week must still be open."""
    out = derive_week_finality(
        _week(), season=2025, week=1, now=_at("2025-09-08T20:16")
    )
    assert "final" not in {g["status"] for g in out["games"]}


def test_no_games_is_never_final(  ) -> None:
    out = derive_week_finality([], season=2025, week=99, now=_at("2026-01-01T12:00"))
    assert out["expected_game_count"] == 0
    assert out["games"] == []


def test_a_game_with_no_kickoff_time_does_not_silently_shorten_the_week() -> None:
    """An unparseable gametime must not drop out of the max() and let the week close
    early. Unknown is treated as still-to-come, which is the safe direction."""
    games = _week()
    games.append({"game_id": "TBD", "gameday": "2025-09-08", "gametime": None,
                  "home_score": None, "away_score": None})
    out = derive_week_finality(games, season=2025, week=1, now=_at("2025-09-09T04:00"))
    assert "final" not in {g["status"] for g in out["games"]}


def test_output_shape_matches_what_week_status_consumes() -> None:
    out = derive_week_finality(_week(), season=2025, week=1, now=_at("2025-09-09T04:00"))
    assert set(out) == {"season", "week", "expected_game_count", "games"}
    for game in out["games"]:
        assert set(game) >= {"season", "week", "game_id", "status", "gameday"}
