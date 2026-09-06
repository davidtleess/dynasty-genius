"""Round 2, item 5 — a longer BASIC historical cohort from first-party football statistics.

Feature rows are built from nflverse weekly stats (all games, the DG-024 definition for
the production features) and the players table (birth date, position). A player has a
row for season t if he appeared in t or in t-1, so a whole missed season is a row with
zero games and NaN production (Tank Dell 2025), never a fabricated stat line; after two
straight absent seasons he leaves the cohort. Labels come from the same source through
annual_targets on the agreed REG event.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.annual_outcomes import SCORING_COLUMN
from src.dynasty_genius.eval.basic_cohort import (
    BASIC_FEATURES,
    COHORT_RULE,
    build_basic_cohort,
    validate_players_table,
)

WEEKLY_COLUMNS = ["player_id", "season", "week", "season_type", "position", SCORING_COLUMN]


def _weekly(rows):
    return pd.DataFrame(rows, columns=WEEKLY_COLUMNS)


def _players(rows):
    return pd.DataFrame(rows, columns=["gsis_id", "display_name", "position", "birth_date"])


def test_basic_features_are_first_party_and_named():
    assert BASIC_FEATURES == [
        "ppg_t", "games_t", "age", "ppg_t_minus_1", "games_t_minus_1", "ppg_t_minus_1_available",
        "ppg_last_observed", "seasons_since_last_observed", "seasons_played",
    ]
    assert "appeared in season t or t-1" in COHORT_RULE


def test_rows_carry_all_games_production_age_and_lags():
    weekly = _weekly([
        ("A", 2022, 1, "REG", "WR", 10.0), ("A", 2022, 2, "REG", "WR", 20.0), ("A", 2022, 19, "POST", "WR", 30.0),
        ("A", 2023, 1, "REG", "WR", 12.0),
    ])
    players = _players([("A", "A Player", "WR", "1998-06-01")])
    cohort = build_basic_cohort(weekly, players, seasons=[2022, 2023])
    a22 = cohort.set_index(["player_id", "feature_season"]).loc[("A", 2022)]
    assert a22["games_t"] == 3 and a22["ppg_t"] == pytest.approx(60.0 / 3)      # all games, DG-024
    assert a22["age"] == pytest.approx(2022 - 1998)
    assert a22["ppg_t_minus_1_available"] == 0 and np.isnan(a22["ppg_t_minus_1"])
    assert a22["seasons_played"] == 1 and a22["seasons_since_last_observed"] == 0
    a23 = cohort.set_index(["player_id", "feature_season"]).loc[("A", 2023)]
    assert a23["ppg_t_minus_1"] == pytest.approx(20.0) and a23["games_t_minus_1"] == 3
    assert a23["ppg_t_minus_1_available"] == 1 and a23["seasons_played"] == 2
    assert a23["position"] == "WR" and a23["identity_status"] == "resolved"


def test_a_whole_missed_season_after_an_active_one_is_a_zero_row_not_a_fabricated_line():
    weekly = _weekly([("D", 2024, 1, "REG", "WR", 15.0), ("D", 2024, 2, "REG", "WR", 5.0)])
    players = _players([("D", "Tank Dell", "WR", "1999-10-29")])
    cohort = build_basic_cohort(weekly, players, seasons=[2024, 2025])
    d25 = cohort.set_index(["player_id", "feature_season"]).loc[("D", 2025)]
    assert d25["games_t"] == 0 and np.isnan(d25["ppg_t"])
    assert d25["ppg_last_observed"] == pytest.approx(10.0) and d25["seasons_since_last_observed"] == 1
    assert d25["ppg_t_minus_1"] == pytest.approx(10.0) and d25["games_t_minus_1"] == 2
    assert d25["age"] == pytest.approx(2025 - 1999)


def test_two_straight_absent_seasons_leave_the_cohort():
    weekly = _weekly([("R", 2020, 1, "REG", "RB", 15.0)])
    players = _players([("R", "Retired Back", "RB", "1990-01-01")])
    cohort = build_basic_cohort(weekly, players, seasons=[2020, 2021, 2022, 2023])
    seasons = sorted(cohort.loc[cohort.player_id == "R", "feature_season"])
    assert seasons == [2020, 2021]           # 2021 is the zero row; 2022+ are gone, not zero


def test_position_is_the_seasons_modal_stat_line_position_not_the_current_listing():
    weekly = _weekly([("H", 2024, 1, "REG", "WR", 9.0), ("H", 2024, 2, "REG", "WR", 9.0), ("H", 2024, 3, "REG", "DB", 0.0)])
    players = _players([("H", "Two Way", "DB", "2003-01-01")])
    cohort = build_basic_cohort(weekly, players, seasons=[2024])
    assert cohort.iloc[0]["position"] == "WR"
    assert cohort.iloc[0]["listed_position"] == "DB"


def test_missing_birth_date_is_unresolved_age_not_a_guess():
    weekly = _weekly([("N", 2024, 1, "REG", "TE", 4.0)])
    players = _players([("N", "No Birthday", "TE", None)])
    cohort = build_basic_cohort(weekly, players, seasons=[2024])
    assert np.isnan(cohort.iloc[0]["age"]) and cohort.iloc[0]["identity_status"] == "resolved_no_birth_date"


def test_players_table_validation_refuses_duplicates_and_missing_ids():
    good = _players([("A", "A", "WR", "1998-06-01"), ("B", "B", "RB", "1999-01-01")])
    facts = validate_players_table(good)
    assert facts["rows"] == 2 and facts["duplicate_gsis"] == 0
    with pytest.raises(ValueError, match="duplicate"):
        validate_players_table(pd.concat([good, good.iloc[[0]]]))
    with pytest.raises(ValueError, match="gsis"):
        validate_players_table(_players([(None, "X", "WR", "1998-06-01")]))
