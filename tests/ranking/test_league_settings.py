"""DG-178 — league settings are READ from the snapshot, never assumed.

Every structural number here derives from `league.roster_positions` and the roster count,
so a league with different slots gives different answers and nothing carries a 72 or a 24
written down once (DG-170's trap).
"""
from __future__ import annotations

import pytest

DAVID_SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX"] + ["BN"] * 11


def _settings(slots=None, teams: int = 12, scoring=None):
    from src.dynasty_genius.ranking.league_settings import LeagueSettings

    return LeagueSettings.from_snapshot({
        "league": {
            "name": "fixture",
            "season": "2026",
            "roster_positions": list(slots if slots is not None else DAVID_SLOTS),
            "scoring_settings": scoring if scoring is not None else {"rec": 1.0, "pass_td": 4.0},
            "settings": {"taxi_slots": 2, "reserve_slots": 4},
        },
        "rosters": [{"roster_id": i + 1} for i in range(teams)],
    })


def test_slot_counts_come_from_roster_positions() -> None:
    s = _settings()
    assert s.teams == 12
    assert s.slots == {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 2, "SUPER_FLEX": 1, "BN": 11}


def test_a_quarterback_is_eligible_for_the_superflex_slot_and_nothing_else_shared() -> None:
    s = _settings()
    assert s.eligible_slots("QB") == {"QB", "SUPER_FLEX"}


def test_tight_ends_enter_the_flex_pool_because_the_slot_is_named_flex() -> None:
    """Sleeper's FLEX is RB/WR/TE by definition; REC_FLEX or WRRB_FLEX would say otherwise.
    Read from the slot name in his settings, not assumed (DG-170)."""
    s = _settings()
    assert s.eligible_slots("TE") == {"TE", "FLEX", "SUPER_FLEX"}
    narrow = _settings(slots=["QB", "RB", "RB", "WR", "WR", "TE", "WRRB_FLEX", "SUPER_FLEX"])
    assert "WRRB_FLEX" not in narrow.eligible_slots("TE")
    assert "WRRB_FLEX" in narrow.eligible_slots("RB")


def test_quarterback_start_capacity_doubles_with_a_superflex_slot() -> None:
    """The most quarterbacks that could start league-wide: 12 x (1 QB + 1 SF) = 24 in his
    league, 12 without the superflex. An upper bound by eligibility, not a replacement rule."""
    assert _settings().start_capacity("QB") == 24
    no_sf = _settings(slots=["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX"])
    assert no_sf.start_capacity("QB") == 12


def test_flex_capacity_is_pooled_across_backs_receivers_and_tight_ends() -> None:
    """Backs, receivers and tight ends compete for the same shared slots, so the pooled
    capacity counts each shared slot ONCE (DG-170). Dedicated 2+2+1 plus FLEX 2 plus SF 1,
    times 12 teams."""
    s = _settings()
    assert s.pooled_start_capacity(["RB", "WR", "TE"]) == 12 * (2 + 2 + 1 + 2 + 1)
    # Summing per-position capacities would count every shared slot three times.
    assert sum(s.start_capacity(p) for p in ("RB", "WR", "TE")) > s.pooled_start_capacity(["RB", "WR", "TE"])


def test_nothing_is_hardcoded_to_twelve_teams() -> None:
    ten = _settings(teams=10)
    assert ten.start_capacity("QB") == 20
    assert ten.pooled_start_capacity(["RB", "WR"]) == 10 * (2 + 2 + 2 + 1)


def test_scoring_flags_are_read_not_assumed() -> None:
    s = _settings(scoring={"rec": 1.0, "pass_td": 4.0})
    assert s.full_ppr is True
    assert s.te_premium == 0.0
    half = _settings(scoring={"rec": 0.5, "bonus_rec_te": 0.5})
    assert half.full_ppr is False
    assert half.te_premium == 0.5


def test_an_unknown_slot_name_is_refused_rather_than_guessed() -> None:
    from src.dynasty_genius.ranking.league_settings import LeagueSettings

    with pytest.raises(ValueError, match="slot"):
        LeagueSettings.from_snapshot({
            "league": {"roster_positions": ["QB", "MYSTERY"], "scoring_settings": {}},
            "rosters": [{"roster_id": 1}],
        })


def test_settings_carry_their_snapshot_identity() -> None:
    from src.dynasty_genius.ranking.league_settings import LeagueSettings

    s = LeagueSettings.from_snapshot({
        "league": {"name": "L", "season": "2026", "roster_positions": DAVID_SLOTS,
                   "scoring_settings": {"rec": 1.0}},
        "rosters": [{"roster_id": i} for i in range(12)],
        "captured_at": "2026-09-06T13:00:52+00:00",
    }, snapshot_id="league-20260906T130052Z")
    assert s.snapshot_id == "league-20260906T130052Z"
    assert s.captured_at == "2026-09-06T13:00:52+00:00"
