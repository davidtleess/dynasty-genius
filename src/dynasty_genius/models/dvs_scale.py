"""DG-159 — the three derivations that turn a ceiling into every other scale constant.

The displayed 0-100 score is a player's points per game divided by a ceiling. Everything else
on that scale is derived from the SAME ceiling and then frozen as a hand-written literal in
three different modules:

    multiplier   lambda[pos]         = ceiling[pos] / ceiling[anchor]
    replacement  replacement_dvs[pos] = replacement_ppg[pos] / ceiling[pos] * 100
    band         sigma[pos]           = model_rmse[pos]      / ceiling[pos] * 100

Because they are literals, moving a ceiling does not move them — it silently invalidates
them. That is not hypothetical: the tight-end ceiling has been stale against its own training
table since a June de-duplication, and the band sigmas are stored in score units and would
have shipped describing a scale that no longer existed.

This module is the single place those three live. It is pure arithmetic with no state and no
constants of its own: give it a denominator and it returns what every other scale constant
must be for that denominator to hold.

**No denominator is named here, deliberately, and a test enforces that.** David ruled both the
criteria — "the absolute best player in the league, or something mathematically achievable
because we believe it is a Hall of Fame level Dynasty asset", and "not unreachable or extremely
reachable" — and, on 2026-09-04, the value: 20.1 points a game. It lives as
``DVS_SCALE_ANCHOR_PPG`` in ``engine_b_contract.py``, with the docstring explaining the choice.
A second copy here would be somewhere for the two to drift apart in silence, which is the exact
failure this module exists to end.
"""
from __future__ import annotations

# Rounding matches what the shipped constants carry, so a derivation can be compared to a
# literal without a tolerance argument every time: multipliers to 3 decimals, the two
# 100-point quantities to 1. These are the precisions the existing tables were written at.
_LAMBDA_DECIMALS = 3
_SCORE_DECIMALS = 1


def derive_lambda(ceiling: float, anchor_ceiling: float) -> float:
    """The cross-positional multiplier: this position's ceiling over the anchor's.

    It exists so the position ceiling CANCELS out of the uncapped cross-positional value,
    leaving points above replacement in one common unit. That cancellation is why editing a
    multiplier on its own creates a distortion rather than removing one — the retracted
    "TE lambda should be 0.703" edit is on record as exactly that mistake.

    Under a single shared ceiling this returns 1.000 at every position, which is the identity
    doing its job rather than being switched off: with one denominator there is no
    position-specific scale left to cancel.
    """
    if anchor_ceiling <= 0:
        raise ValueError("anchor ceiling must be positive")
    return round(ceiling / anchor_ceiling, _LAMBDA_DECIMALS)


def derive_replacement_dvs(replacement_ppg: float, ceiling: float) -> float:
    """Where replacement level sits on the 0-100 scale.

    The points-per-game figure is a property of the league's lineup structure — how many of
    this position start — and does NOT move when the ceiling moves. Its position on the scale
    does. Both engines already carry the same points-per-game values, which is why one shared
    ceiling collapses their two replacement tables into one.
    """
    if ceiling <= 0:
        raise ValueError("ceiling must be positive")
    return round(replacement_ppg / ceiling * 100.0, _SCORE_DECIMALS)


def derive_sigma(model_rmse: float, ceiling: float) -> float:
    """The band half-width on the 0-100 scale, from the served model's own error.

    The error is a fact about the model measured in points per game; sigma is that error
    expressed on whatever scale the score currently uses. It is stored in score units, so it
    is the member of this family most easily forgotten: leave it alone while the ceiling moves
    and the band silently describes a scale that no longer exists, growing or shrinking
    relative to the range it is meant to qualify.
    """
    if ceiling <= 0:
        raise ValueError("ceiling must be positive")
    return round(model_rmse / ceiling * 100.0, _SCORE_DECIMALS)
