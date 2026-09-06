#!/usr/bin/env python3.14
"""A rookie's number carries a probability the veteran numbers do not.

The R(h) cells are fitted on QUALIFYING player-seasons. They answer "given he IS
startable at level L and age A, how long does that last?" — and a rookie's dominant
uncertainty is whether he ever becomes startable at all, which the cells condition away
by construction. Plugging a rookie straight in asserts an event that happens 42% of the
time. So one factor goes in front and nothing else changes:

    rookie value = P(ever qualifies) x [the same cells, same bar, same scale]

⭐ P COMES FROM DRAFT CAPITAL ALONE, and that is a finding rather than a shortcut.
Measured leave-one-draft-class-out over 478 prospects with all 85 washouts retained
(DG-165, Bob):

    draft capital alone (pick, round, age)   AUC 0.813
    college production alone                 AUC 0.655
    capital + college                        AUC 0.817
    increment of college over capital        +0.004  CI [-0.007, +0.014]

David asked for college production translated into NFL careers. It already has been
translated — by NFL teams — and the output is where they drafted him.

⚠ THE BOUND ON THAT CLAIM, and it must not drift. The finding is "the college data WE
HOLD adds nothing on top of the pick". It is NOT "college football tells you nothing the
draft does not". Competition adjustment, usage share and per-game splits were
unavailable; what we have is dominator, breakout age and ryptpa at 31-72% coverage, and
`yprr_college` is a contract feature that is 0% populated.

⛔ NO DOUBLE COUNT, measured rather than reasoned. `run_head_a_bakeoff.py` fits only
non-censored rows — 313 of 478, minimum 8 games, zero zeros in the target rate — so
Engine A's score is CONDITIONAL on having played and does not already embed P. The
multiplier counts exactly once. This was the one thing that could have made the whole
structure silently wrong, and it would have been invisible because both factors push the
same way.
"""
from __future__ import annotations

# Share of prospects who EVER post a qualifying season, by draft-capital quintile.
# Calibration, not a fitted curve: these are observed rates on the 478-prospect panel.
QUALIFY_RATE_BY_QUINTILE = (0.86, 0.57, 0.34, 0.22, 0.12)

# A modern draft is 257 picks. Quintile edges are the pick numbers, not a model.
_DRAFT_SIZE = 257


def probability_ever_qualifies(overall_pick: int | None) -> float | None:
    """P(this rookie ever posts a startable season), from where he was drafted.

    Undrafted or unknown returns None rather than the bottom bucket: a player nobody
    drafted is not the same as a player drafted last, and guessing the difference is
    how a blank becomes a confident number.
    """
    if overall_pick is None or overall_pick <= 0:
        return None
    quintile = min(4, int((overall_pick - 1) * 5 / _DRAFT_SIZE))
    return QUALIFY_RATE_BY_QUINTILE[quintile]


def rookie_card_caveat(probability: float) -> str:
    """The sentence that must travel with a rookie's number.

    An 86% first-rounder and a 12% seventh-rounder must not present identically just
    because both now have a number. The veteran numbers carry no such factor.
    """
    return (f"This is what he is worth IF he becomes a starter. "
            f"{probability:.0%} of players drafted where he was ever do.")
