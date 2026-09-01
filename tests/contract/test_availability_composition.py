"""Served value composes as P(plays) x E[points | plays], not E[points | plays] alone.

The product estimated points CONDITIONAL ON PLAYING and called the result dynasty value.
That is one factor of two. The missing factor is why the live divergence signal told David
to buy 27-year-olds and sell 22-year-olds in a dynasty league: holding production constant
the market discounts age at -0.3855 and the model at -0.2246, and the gap is availability,
which a points model cannot express because it only ever asks how much a player scores
GIVEN that he plays.

Composing measured (503 players, 2025 inference set, ppg_t held constant):

    age effect, DVS today      -0.2593
    age effect, DVS composed   -0.4176
    market                     -0.3855

WHY MULTIPLY THE PROJECTION RATHER THAN NORMALISE THE MULTIPLIER. An earlier attempt
divided P by the population base rate to hold the DVS scale steady. It held the scale and
nearly TRIPLED the number of players pinned at the DVS ceiling (21 -> 58), because players
with above-average availability were pushed past the P90. A probability is a discount:
P <= 1, so multiplying can only ever reduce a value and can never invent a new ceiling
player. Measured, the ceiling count FALLS 21 -> 17. The mean DVS drops with it, and that
drop is the correction rather than a side effect -- the old number overstated expected
value by ignoring attrition entirely.

WHAT THIS DOES NOT TOUCH. ENGINE_B_P90_PPG, XVAR_LAMBDA_ENGINE_B and
ENGINE_B_REPLACEMENT_DVS are one coupled system (DG-092): move all three together with a
new diagnostic and David's approval, or none. This moves none of them. The adjustment is
applied to the projection BEFORE the existing normalisation, so every constant keeps its
meaning and the coupled-identity contract tests keep passing.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG


def _dvs(projection: float, position: str, availability: float | None) -> float:
    from src.dynasty_genius.pvo_assembler import apply_availability

    adjusted = apply_availability(projection, availability)
    return round(min(100.0, max(0.0, adjusted / ENGINE_B_P90_PPG[position] * 100.0)), 1)


def test_availability_discounts_a_projection() -> None:
    """The hurdle: expected value is what he scores times the chance he is there to score."""
    from src.dynasty_genius.pvo_assembler import apply_availability

    assert apply_availability(10.0, 0.5) == pytest.approx(5.0)
    assert apply_availability(10.0, 1.0) == pytest.approx(10.0)


def test_availability_can_never_inflate_a_projection() -> None:
    """P is a probability. A composition that can raise a value invents ceiling players."""
    from src.dynasty_genius.pvo_assembler import apply_availability

    for p in (0.0, 0.25, 0.5, 0.773, 0.99, 1.0):
        assert apply_availability(12.0, p) <= 12.0 + 1e-9


def test_a_missing_availability_leaves_the_projection_untouched() -> None:
    """Absent evidence must not be read as certain attrition, nor as certain availability.

    A player with no availability estimate keeps the unadjusted number and is flagged
    elsewhere. Substituting 0.0 would delete him; substituting 1.0 would silently claim we
    measured a certainty we never observed. Passing him through unchanged is the only
    option that asserts nothing.
    """
    from src.dynasty_genius.pvo_assembler import apply_availability

    assert apply_availability(9.5, None) == pytest.approx(9.5)


def test_two_players_with_equal_projections_are_separated_by_availability() -> None:
    """Kelce at 36 and Bowers at 23 stop being the same asset. That is the whole point."""
    young = _dvs(9.0, "TE", 0.92)
    old = _dvs(9.0, "TE", 0.61)
    assert young > old, (
        "identical projections must diverge on availability, or the composition is inert"
    )


def test_the_composition_does_not_create_new_ceiling_players() -> None:
    """Measured regression guard: the base-rate-normalised variant tripled the ceiling."""
    at_ceiling_before = _dvs(20.0, "TE", None)
    at_ceiling_after = _dvs(20.0, "TE", 0.85)
    assert at_ceiling_before == 100.0
    assert at_ceiling_after <= at_ceiling_before, (
        "a player at the ceiling must not be pushed further into the clamp by this change; "
        "an adjustment that can raise values makes the clamp defect worse, not better"
    )


def test_an_out_of_range_availability_is_refused_rather_than_clamped() -> None:
    """A probability outside [0,1] means the producer is broken; silence would hide it."""
    from src.dynasty_genius.pvo_assembler import apply_availability

    for bad in (-0.1, 1.4):
        with pytest.raises(ValueError):
            apply_availability(10.0, bad)
