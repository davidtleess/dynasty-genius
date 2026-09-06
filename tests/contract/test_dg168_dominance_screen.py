"""DG-168 — the dominance screen, and the four ways it could lie.

The screen says: the market prices these two the same, and one of them produces more
AND has more startable career left. That sentence can be false in four ways, and each
has a test here because the mechanics were exercised by hand for a full day before
anything checked them.

⚠ Every pair this screen produces is a HYPOTHESIS. Nothing has been graded against a
realised outcome. It finds the market contradicting itself on facts we measured; who is
right is a season away.
"""
from __future__ import annotations

import pytest

from scripts.dg168.dominance_screen import (
    LEAGUE_TRANSLATION,
    MIN_CAREER_EDGE,
    MIN_PRODUCTION_EDGE,
    SAME_PRICE_BAND,
    UnknownMarketBaseline,
    find_contradictions,
    translation_for,
)


def _p(name, pos, market, production, career):
    return {"name": name, "pos": pos, "market": market,
            "production": production, "career": career}


# ── 1. it finds a real contradiction ────────────────────────────────────────
def test_a_clear_contradiction_is_found():
    """Same price, comfortably ahead on both axes. If this does not fire the screen
    is not doing its job at all."""
    a = _p("Ahead", "RB", 1000.0, 6.0, 3.0)
    b = _p("Behind", "RB", 1000.0, 2.0, 1.5)
    found = find_contradictions([a, b])
    assert len(found) == 1
    assert found[0]["better"]["name"] == "Ahead"


# ── 2. it does not fire on noise ────────────────────────────────────────────
def test_a_hair_of_difference_is_not_a_finding():
    """The failure that would flood him with claims: two players a rounding error
    apart. The margins are 15% on each axis precisely so numerical noise cannot
    manufacture a sentence about a trade."""
    a = _p("Barely", "RB", 1000.0, 6.00, 3.00)
    b = _p("Almost", "RB", 1000.0, 5.99, 2.99)
    assert find_contradictions([a, b]) == []


def test_ahead_on_only_one_axis_is_not_dominance():
    """Produces more but will not last as long is a TRADE-OFF, not a contradiction.
    Reporting it as one would be the screen inventing an edge out of a preference."""
    a = _p("Better now", "RB", 1000.0, 6.0, 1.0)
    b = _p("Lasts longer", "RB", 1000.0, 2.0, 4.0)
    assert find_contradictions([a, b]) == []


# ── 3. it does not fire when the market prices them differently ─────────────
def test_players_the_market_prices_differently_are_not_a_finding():
    """'The market prices these two the same' is a claim ABOUT THE MARKET. If the
    market charges twice as much for one of them, there is nothing to contradict."""
    a = _p("Cheap", "RB", 1000.0, 6.0, 3.0)
    b = _p("Dear", "RB", 3000.0, 2.0, 1.5)
    assert find_contradictions([a, b]) == []


# ── 4. the format explains it, so it is not a market error ──────────────────
def test_a_gap_the_format_already_explains_is_discarded():
    """The dominant player's position carries the larger format correction, so the
    market pricing them alike already underprices him for HIS league — the finding is
    partly the format rather than a market error.

    Quarterback carries 1.95 against running back's 0.98, so a quarterback beating a
    back at the same price is half explained before we start.
    """
    qb = _p("Quarterback", "QB", 1000.0, 6.0, 3.0)
    rb = _p("Back", "RB", 1000.0, 2.0, 1.5)
    assert find_contradictions([qb, rb]) == []


def test_a_gap_the_format_makes_WORSE_is_kept():
    """The mirror, and the one an over-eager refuter would wrongly discard. A running
    back beating a tight end at the same price is a LARGER contradiction in his league,
    not a smaller one — tight end carries 1.96 against running back's 0.98, so the
    market restated for his format says the tight end should cost twice as much."""
    rb = _p("Back", "RB", 1000.0, 6.0, 3.0)
    te = _p("Tight end", "TE", 1000.0, 2.0, 1.5)
    assert len(find_contradictions([rb, te])) == 1


# ── 5. an unmeasured market source fails closed ─────────────────────────────
def test_an_unmeasured_source_refuses_rather_than_assuming_no_correction():
    """Defaulting to 1.0 asserts that a source publishes for his league. That is false
    of every source measured — the smallest correction in the table is 1.45."""
    assert translation_for("fantasycalc")["TE"] == pytest.approx(1.96)
    with pytest.raises(UnknownMarketBaseline):
        translation_for("ktc")
    with pytest.raises(UnknownMarketBaseline):
        translation_for(None)


# ── 6. the thresholds are stated, not buried ────────────────────────────────
def test_the_thresholds_are_practical_margins_rather_than_epsilons():
    """A screen whose margins are tiny is a screen that reports noise. These are the
    numbers a reader should be able to argue with, so they are named."""
    assert SAME_PRICE_BAND == 0.10
    assert MIN_PRODUCTION_EDGE == 0.15
    assert MIN_CAREER_EDGE == 0.15
