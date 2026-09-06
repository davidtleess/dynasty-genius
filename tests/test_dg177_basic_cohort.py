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


# ── Codex increment: a general historical offensive-role fallback (no hardcoded player) ──

from src.dynasty_genius.eval.basic_cohort import (  # noqa: E402
    OFFENSIVE_POSITIONS,
    ROLE_SOURCES,
    resolve_offensive_role,
)


def _roster(rows):
    return pd.DataFrame(rows, columns=["gsis_id", "season", "week", "position", "depth_chart_position"])


def test_role_sources_are_named_and_offensive_set_is_the_modelled_set():
    assert OFFENSIVE_POSITIONS == frozenset({"QB", "RB", "WR", "TE"})
    assert ROLE_SOURCES == ("statline", "roster_same_season", "conflicting_roster_roles", "no_offensive_role", "no_roster_evidence")


class TestResolveOffensiveRole:
    def test_an_offensive_stat_line_position_is_kept_whatever_the_roster_says(self):
        pos, source, ev = resolve_offensive_role("WR", _roster([("H", 2025, 18, "DB", "CB")]))
        assert (pos, source) == ("WR", "statline") and ev["statline_position"] == "WR"

    def test_a_non_offensive_stat_line_falls_back_to_one_same_season_roster_role(self):
        pos, source, ev = resolve_offensive_role("CB", _roster([("H", 2025, 19, "WR", "WR")]))
        assert (pos, source) == ("WR", "roster_same_season")
        assert ev == {"statline_position": "CB", "roster_positions": ["WR"], "roster_depth_positions": ["WR"],
                      "roster_weeks": [19], "offensive_roles_seen": ["WR"]}

    def test_conflicting_roster_roles_abstain(self):
        pos, source, ev = resolve_offensive_role("CB", _roster([("H", 2025, 1, "WR", "WR"), ("H", 2025, 18, "RB", "RB")]))
        assert pos is None and source == "conflicting_roster_roles" and ev["offensive_roles_seen"] == ["RB", "WR"]

    def test_a_roster_with_no_offensive_role_is_unknown(self):
        pos, source, ev = resolve_offensive_role("CB", _roster([("H", 2025, 18, "DB", "CB")]))
        assert pos is None and source == "no_offensive_role" and ev["offensive_roles_seen"] == []

    def test_no_roster_rows_is_no_evidence(self):
        pos, source, ev = resolve_offensive_role("CB", _roster([]))
        assert pos is None and source == "no_roster_evidence" and ev["roster_weeks"] == []


def _weekly_two_way(points_2024=9.0):
    return _weekly([
        ("H", 2024, 1, "REG", "CB", points_2024), ("H", 2024, 2, "REG", "CB", 12.0),   # receiving points on a CB stat line
        ("H", 2025, 1, "REG", "CB", 8.0), ("H", 2025, 2, "REG", "CB", 10.0),
        ("A", 2025, 1, "REG", "WR", 10.0),
    ])


def test_fallback_uses_only_the_same_seasons_roster_rows_and_records_the_evidence():
    weekly = _weekly_two_way()
    players = _players([("H", "Two Way", "DB", "2003-01-01"), ("A", "A", "WR", "1998-01-01")])
    roster = _roster([("H", 2025, 19, "WR", "WR")])          # evidence for 2025 only
    cohort = build_basic_cohort(weekly, players, seasons=[2024, 2025], roster_roles=roster)
    h = cohort[cohort.player_id == "H"].set_index("feature_season")
    assert h.loc[2025, "position"] == "WR" and h.loc[2025, "position_source"] == "roster_same_season"
    assert h.loc[2025, "statline_position"] == "CB"
    assert '"roster_weeks": [19]' in h.loc[2025, "role_evidence"]
    # 2024 has no roster row of its own: the 2025 evidence must NOT reach back
    assert h.loc[2024, "position"] == "CB" and h.loc[2024, "position_source"] == "no_roster_evidence"
    # the offensive player is untouched
    a = cohort[cohort.player_id == "A"].iloc[0]
    assert a["position"] == "WR" and a["position_source"] == "statline"


def test_todays_listed_position_never_resolves_a_historical_fold():
    weekly = _weekly_two_way()
    players = _players([("H", "Two Way", "WR", "2003-01-01")])   # today's listing says WR
    cohort = build_basic_cohort(weekly, players, seasons=[2024, 2025], roster_roles=_roster([]))
    h = cohort[cohort.player_id == "H"].set_index("feature_season")
    assert h.loc[2024, "position"] == "CB" and h.loc[2025, "position"] == "CB"
    assert set(h["position_source"]) == {"no_roster_evidence"}
    assert h.loc[2025, "listed_position"] == "WR"                 # carried, never used


def test_conflicting_same_season_roles_abstain_in_the_cohort():
    weekly = _weekly_two_way()
    players = _players([("H", "Two Way", "DB", "2003-01-01")])
    roster = _roster([("H", 2025, 1, "WR", "WR"), ("H", 2025, 18, "RB", "RB")])
    cohort = build_basic_cohort(weekly, players, seasons=[2025], roster_roles=roster)
    h = cohort[cohort.player_id == "H"].iloc[0]
    assert h["position"] == "CB" and h["position_source"] == "conflicting_roster_roles"


def test_no_defensive_points_are_added_by_the_fallback():
    weekly = _weekly([("H", 2025, 1, "REG", "CB", 0.0), ("H", 2025, 2, "REG", "CB", 0.0)])   # a pure defender: 0 PPR
    players = _players([("H", "Pure Corner", "DB", "2003-01-01")])
    roster = _roster([("H", 2025, 18, "WR", "WR")])
    cohort = build_basic_cohort(weekly, players, seasons=[2025], roster_roles=roster)
    h = cohort.iloc[0]
    assert h["position"] == "WR" and h["ppg_t"] == 0.0 and h["total_points_t"] == 0.0 and h["games_t"] == 2


def test_without_roster_roles_the_cohort_is_unchanged_and_says_so():
    weekly = _weekly_two_way()
    players = _players([("H", "Two Way", "DB", "2003-01-01")])
    cohort = build_basic_cohort(weekly, players, seasons=[2025])
    h = cohort[cohort.player_id == "H"].iloc[0]
    assert h["position"] == "CB" and h["position_source"] == "no_roster_evidence" and h["statline_position"] == "CB"
    assert cohort.attrs["role_fallback"] == "none supplied"
