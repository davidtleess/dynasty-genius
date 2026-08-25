"""DG-042 — David's "all games" PPG ruling, enforced instead of assumed.

David ruled 2026-08-19 (DG-024, verbatim *"all games"*) that Engine B's points-per-game
counts every game a player played, postseason included. `fetch_and_agg_stats` has no
`season_type` filter and that is **correct by decision, not a defect** — nobody should
"fix" it.

What was missing is the other half: nothing noticed if the world moved. Preseason stays
out of `load_player_stats` because nflverse does not publish it there, not because this
repo enforces anything. Measured 2026-08-25: the `season_type` column exists and is
populated (`REG` weeks 1–18, `POST` weeks 19–22 for 2025), so the day nflverse adds `PRE`,
PPG absorbs it silently and every valuation shifts.

These tests pin both halves: the ruling still holds (postseason IS counted), and an
unruled season type raises loudly and names itself rather than being averaged in.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.assemble_engine_b_dataset import fetch_and_agg_stats
from src.dynasty_genius.models.engine_b_contract import (
    PPG_MAX_GAMES_T,
    PPG_RULED_SEASON_TYPES,
    validate_ppg_season_types,
)

_STAT_COLUMNS = {
    "fantasy_points_ppr": 10.0,
    "targets": 5,
    "receptions": 3,
    "receiving_yards": 40,
    "rushing_yards": 0,
    "rushing_tds": 0,
    "receiving_air_yards": 50,
}


def _row(week: int, season_type: str = "REG", points: float = 10.0, **over):
    row = {
        "player_id": "00-0000001",
        "season": 2025,
        "position": "WR",
        "team": "SF",
        "week": week,
        "season_type": season_type,
        **_STAT_COLUMNS,
    }
    row["fantasy_points_ppr"] = points
    row.update(over)
    return row


def _frame(rows: list[dict], *, drop_season_type: bool = False) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if drop_season_type:
        df = df.drop(columns=["season_type"])
    return df


# ── the ruled set itself ──────────────────────────────────────────────────────


def test_the_ruled_set_is_exactly_davids_2026_08_19_ruling():
    """`{REG, POST}` — all games, postseason included. Not regular season only."""
    assert PPG_RULED_SEASON_TYPES == frozenset({"REG", "POST"})


def test_the_validator_accepts_the_ruled_types():
    validate_ppg_season_types(["REG", "POST", "REG"])


def test_a_preseason_value_raises_and_names_it():
    with pytest.raises(ValueError) as excinfo:
        validate_ppg_season_types(["REG", "PRE", "POST"])
    assert "PRE" in str(excinfo.value)


def test_the_validator_names_every_offender_not_just_the_first():
    with pytest.raises(ValueError) as excinfo:
        validate_ppg_season_types(["REG", "PRE", "PRO_BOWL"])
    message = str(excinfo.value)
    assert "PRE" in message
    assert "PRO_BOWL" in message


def test_an_absent_season_type_column_fails_rather_than_assuming_clean():
    """Absent is not the same as clean — we cannot verify the ruling, so we do not claim to."""
    with pytest.raises(ValueError) as excinfo:
        validate_ppg_season_types(None)
    assert "season_type" in str(excinfo.value)


# ── the ruling, protected from the other direction ────────────────────────────


def test_postseason_games_are_still_counted_in_ppg():
    """DG-024: all games. A POST week must raise games_t and enter the PPG mean."""
    frame = _frame(
        [_row(17, "REG", points=10.0), _row(19, "POST", points=30.0)]
    )
    out = fetch_and_agg_stats([2025], weekly=frame)
    assert len(out) == 1
    assert out.iloc[0]["games_t"] == 2
    assert out.iloc[0]["ppg_t"] == pytest.approx(20.0)


def test_a_regular_season_only_frame_still_assembles():
    frame = _frame([_row(1), _row(2), _row(3)])
    out = fetch_and_agg_stats([2025], weekly=frame)
    assert out.iloc[0]["games_t"] == 3


# ── the guard on the assembly path ────────────────────────────────────────────


def test_assembly_raises_on_a_preseason_row_and_names_pre():
    frame = _frame([_row(1, "REG"), _row(2, "PRE", points=2.0)])
    with pytest.raises(ValueError) as excinfo:
        fetch_and_agg_stats([2025], weekly=frame)
    assert "PRE" in str(excinfo.value)


def test_assembly_raises_when_the_frame_carries_no_season_type_column():
    frame = _frame([_row(1), _row(2)], drop_season_type=True)
    with pytest.raises(ValueError) as excinfo:
        fetch_and_agg_stats([2025], weekly=frame)
    assert "season_type" in str(excinfo.value)


def test_a_preseason_row_for_a_non_skill_position_does_not_false_alarm():
    """The guard grades the rows that actually feed PPG — a K never reaches the mean."""
    frame = _frame([_row(1, "REG"), _row(2, "PRE", position="K")])
    out = fetch_and_agg_stats([2025], weekly=frame)
    assert out.iloc[0]["games_t"] == 1


# ── the secondary tripwire ────────────────────────────────────────────────────


def test_the_games_ceiling_is_seventeen_regular_plus_four_postseason():
    assert PPG_MAX_GAMES_T == 21


def test_more_games_than_a_season_can_hold_raises_and_names_the_player():
    """Catches the same drift from the other direction — when it extends the week range."""
    frame = _frame([_row(week, "REG") for week in range(1, 19)]
                   + [_row(week, "POST") for week in range(19, 23)])
    with pytest.raises(ValueError) as excinfo:
        fetch_and_agg_stats([2025], weekly=frame)
    assert "00-0000001" in str(excinfo.value)


def test_a_full_legal_season_of_twenty_one_games_is_accepted():
    frame = _frame([_row(week, "REG") for week in range(1, 18)]
                   + [_row(week, "POST") for week in range(19, 23)])
    out = fetch_and_agg_stats([2025], weekly=frame)
    assert out.iloc[0]["games_t"] == PPG_MAX_GAMES_T


def test_an_empty_frame_is_not_graded():
    """Nothing feeds PPG, so the ruling has no opinion — the guard must not invent a failure."""
    empty = pd.DataFrame(
        columns=["player_id", "season", "position", "team", "week", *_STAT_COLUMNS]
    )
    out = fetch_and_agg_stats([2025], weekly=empty)
    assert out.empty
