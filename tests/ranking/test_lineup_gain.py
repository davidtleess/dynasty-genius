"""DG-178 — marginal lineup gain is a DIFFERENT basis from value above replacement.

A healthy bench quarterback may beat the free-agent quarterback (positive value above the
obtainable replacement) and still add zero points to a lineup whose QB and SUPER_FLEX are
already better than him. The two numbers answer different questions; this module answers
the second one by comparing feasible best lineups with and without the player, and labels
the result so it can never be mistaken for the focal value.
"""
from __future__ import annotations

import pytest

from tests.ranking.test_league_settings import DAVID_SLOTS, _settings


def _p(pid, pos, rate):
    from src.dynasty_genius.ranking.lineup_gain import Starter

    return Starter(player_id=pid, position=pos, rate_ppg=rate)


def _roster():
    return [
        _p("qb1", "QB", 18.0), _p("qb2", "QB", 15.0),
        _p("rb1", "RB", 14.0), _p("rb2", "RB", 11.0), _p("rb3", "RB", 8.0),
        _p("wr1", "WR", 13.0), _p("wr2", "WR", 10.0), _p("wr3", "WR", 9.5),
        _p("te1", "TE", 9.8),
    ]


def test_a_bench_qb_who_beats_the_free_agent_adds_zero_lineup_points() -> None:
    from src.dynasty_genius.ranking.lineup_gain import marginal_lineup_gain

    gain = marginal_lineup_gain(_roster(), _p("qb3", "QB", 12.0), _settings())
    assert gain.gain_ppg == 0.0
    assert gain.basis == "marginal_lineup_gain"
    # ... while he is worth 1.0 ppg above an 11.0 free-agent quarterback on the other basis.
    assert 12.0 - 11.0 > 0.0


def test_the_second_quarterback_fills_the_superflex_over_a_third_back() -> None:
    from src.dynasty_genius.ranking.lineup_gain import best_lineup

    lineup = best_lineup(_roster(), _settings())
    assert lineup.assignment["SUPER_FLEX"] == ["qb2"]
    assert "qb2" not in lineup.assignment["FLEX"]
    # A filler that took the flex pool before the superflex would still seat qb2, but one
    # that filled SUPER_FLEX with the best flex player would seat rb3 there instead.
    assert "rb3" not in lineup.assignment["SUPER_FLEX"]


def test_backs_receivers_and_tight_ends_compete_for_the_same_flex_slots() -> None:
    """The two FLEX slots go to the best remaining of RB/WR/TE regardless of position: the
    tight end slot is already held by te1 (9.8), so a new tight end at 9.0 competes for FLEX
    and displaces rb3 (8.0) there, worth exactly the difference."""
    from src.dynasty_genius.ranking.lineup_gain import best_lineup, marginal_lineup_gain

    base = best_lineup(_roster(), _settings())
    assert set(base.assignment["FLEX"]) == {"wr3", "rb3"}
    gain = marginal_lineup_gain(_roster(), _p("te2", "TE", 9.0), _settings())
    assert gain.gain_ppg == pytest.approx(9.0 - 8.0)


def test_the_gain_names_its_scenario_and_horizon() -> None:
    from src.dynasty_genius.ranking.lineup_gain import marginal_lineup_gain

    gain = marginal_lineup_gain(_roster(), _p("x", "WR", 20.0), _settings())
    assert gain.h == 0
    assert "every listed player available" in gain.scenario


def test_non_nested_eligibility_is_refused_rather_than_solved_wrongly() -> None:
    """Greedy filling is exact only when the starting slots' eligibility sets nest. A league
    with both REC_FLEX and WRRB_FLEX breaks that, and a wrong lineup is worse than none."""
    from src.dynasty_genius.ranking.lineup_gain import best_lineup

    weird = _settings(slots=["QB", "RB", "WR", "TE", "REC_FLEX", "WRRB_FLEX"])
    with pytest.raises(NotImplementedError, match="nest"):
        best_lineup(_roster(), weird)


def test_davids_slots_nest_so_the_filler_is_exact_for_his_league() -> None:
    from src.dynasty_genius.ranking.lineup_gain import eligibility_nests

    assert eligibility_nests(_settings(slots=DAVID_SLOTS)) is True


def test_taxi_and_reserve_players_are_not_in_the_lineup_pool() -> None:
    """Sleeper will not start a taxi or IR player, so the scenario 'every listed player
    available' must list only the active roster. A taxi rookie showing a lineup gain would be
    a gain he cannot legally deliver."""
    from src.dynasty_genius.ranking.lineup_gain import active_lineup_pool

    roster_entry = {"players": ["a", "b", "c", "d", "e"], "taxi": ["d"], "reserve": ["e"]}
    assert active_lineup_pool(roster_entry) == ["a", "b", "c"]


def test_adding_a_player_already_on_the_roster_is_a_remove_one_counterfactual_not_a_duplicate() -> None:
    """Before this fix, adding qb1 again seated him twice (QB and SUPER_FLEX) and 'gained'
    points. A player's identity is unique; his gain is best(with) - best(without him)."""
    from src.dynasty_genius.ranking.lineup_gain import best_lineup, marginal_lineup_gain

    roster = _roster()
    gain = marginal_lineup_gain(roster, _p("qb1", "QB", 18.0), _settings())
    without = best_lineup([s for s in roster if s.player_id != "qb1"], _settings())
    with_ = best_lineup(roster, _settings())
    assert gain.gain_ppg == pytest.approx(with_.total_ppg - without.total_ppg)
    seated = [pid for pids in with_.assignment.values() for pid in pids]
    assert seated.count("qb1") == 1


def test_a_roster_with_a_duplicated_identity_is_refused() -> None:
    from src.dynasty_genius.ranking.lineup_gain import best_lineup

    with pytest.raises(ValueError, match="duplicate"):
        best_lineup(_roster() + [_p("qb1", "QB", 18.0)], _settings())
