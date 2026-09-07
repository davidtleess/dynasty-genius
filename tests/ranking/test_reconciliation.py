"""DG-178 round 2, item 4 — the league's scoring and week scope against the candidate's, measured.

The candidate target is nflverse `fantasy_points_ppr` over the NFL regular season (18 calendar
weeks, 17 team games). David's league is a Sleeper PPR league whose fantasy season is weeks
1-17 (14 regular-season weeks, playoffs from week 15). "PPR" in both names does not make them
equal; the differences are listed and typed, never assumed away.
"""
from __future__ import annotations


def _league():
    return {
        "league": {"roster_positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX", "BN"],
                   "scoring_settings": {"pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
                                        "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0, "rec": 1.0, "rec_yd": 0.1,
                                        "rec_td": 6.0, "rec_2pt": 2.0, "fum_lost": -2.0, "fum_rec_td": 6.0,
                                        "st_td": 6.0, "bonus_rec_te": 0.0},
                   "settings": {"playoff_week_start": 15, "playoff_teams": 6}},
        "rosters": [{"roster_id": i} for i in range(12)],
    }


def test_scoring_differences_are_listed_key_by_key_against_the_nflverse_ppr_definition() -> None:
    from src.dynasty_genius.ranking.reconciliation import reconcile_scoring

    r = reconcile_scoring(_league())
    assert r.candidate_definition == "nflverse fantasy_points_ppr"
    same = {d.key for d in r.differences if d.same}
    assert {"pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td", "rec", "rec_yd", "rec_td", "fum_lost"} <= same
    # keys the league scores that nflverse's formula does not, or vice versa, are named, not dropped
    keys = {d.key for d in r.differences}
    assert "st_td" in keys and "bonus_rec_te" in keys
    assert r.all_equal is False or r.unmatched_keys == []


def test_the_week_scope_difference_is_stated_from_the_leagues_playoff_settings() -> None:
    from src.dynasty_genius.ranking.reconciliation import reconcile_scoring

    r = reconcile_scoring(_league())
    # The snapshot states the playoff START only; the final fantasy week is not inferred.
    assert r.league_regular_weeks == (1, 14) and r.playoff_start_week == 15
    assert r.league_final_week is None
    assert r.candidate_weeks == (1, 18)
    assert "not recorded" in r.week_scope_note and "week 18" in r.week_scope_note
    assert r.window_matches_league is False


def test_a_league_with_a_te_premium_is_a_measured_scoring_difference() -> None:
    from src.dynasty_genius.ranking.reconciliation import reconcile_scoring

    lg = _league()
    lg["league"]["scoring_settings"]["bonus_rec_te"] = 0.5
    r = reconcile_scoring(lg)
    d = next(x for x in r.differences if x.key == "bonus_rec_te")
    assert d.same is False and d.league_value == 0.5 and d.candidate_value == 0.0


def test_a_board_refuses_term_sets_with_mixed_replacement_policies_or_snapshots() -> None:
    from datetime import date

    import pytest

    from src.dynasty_genius.ranking.assembler import assemble
    from src.dynasty_genius.ranking.contract import (
        HorizonTerm,
        Posture,
        ProducerRef,
        ReplacementRef,
        TermSet,
        annual_target,
    )

    fd = date(2026, 9, 6)
    spec = annual_target(fd)

    def ts(pid, policy, snap):
        return TermSet(player_id=pid, position="WR", forecast_date=fd,
                       producer=ProducerRef(name="p", version="1", estimate_class="candidate", evidence_verified=True),
                       replacement_ref=ReplacementRef(position="WR", policy=policy, rate_ppg=90.0, snapshot_id=snap,
                                                      horizon_assumption="same_player_from_snapshot_per_season"),
                       terms=[HorizonTerm(h=0, season=2026, ev_above_replacement=1.0, conditioning_event="x", spec=spec)],
                       coverage="full")

    assemble([ts("a", "best_available_expected_points", "s1"), ts("b", "best_available_expected_points", "s1")],
             Posture(label="r", discount=1.0), horizons=0, board=spec)
    with pytest.raises(ValueError, match="replacement"):
        assemble([ts("a", "best_available_expected_points", "s1"), ts("b", "other_policy", "s1")],
                 Posture(label="r", discount=1.0), horizons=0, board=spec)
    with pytest.raises(ValueError, match="snapshot"):
        assemble([ts("a", "best_available_expected_points", "s1"), ts("b", "best_available_expected_points", "s2")],
                 Posture(label="r", discount=1.0), horizons=0, board=spec)
