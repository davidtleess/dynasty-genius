"""The age-cliff rule, in one place.

Two surfaces state an age verdict about the same player: the roster audit, which
recomputes it from the live Sleeper row on every request, and the universe
artifact, whose ``top_drivers``/``risk_flags`` are computed once at model time
from the FEATURE-season age and then copied onto the row (``pvo_assembler`` ->
``universe_pvo_batch``). DG-139 made the artifact serve Sleeper's current age;
this module lets the batch re-derive the verdict from that same age, so the
number and the sentence beside it come from one number (DG-140).

It deliberately imports nothing from ``app`` or from ``universe_pvo_batch``:
``roster_auditor`` already imports ``served_age`` from ``universe_pvo_batch``,
so a rule owned by either of them could not be shared with the other.
"""
from __future__ import annotations

from typing import Any, Optional

#: Age at which each position's decline is conventionally marked. The roster
#: audit has used these since v2; they are a display and evidence convention, never
#: a model feature.
CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}

SKILL_POSITIONS = set(CLIFF_AGES.keys())

#: cliff band -> the evidence token that states it.
SIGNAL_DRIVERS = {
    "past_cliff": "age_past_position_cliff",
    "at_cliff": "age_at_position_cliff",
    "approaching_cliff": "age_within_two_years_of_position_cliff",
    "no_age_signal": "age_not_near_position_cliff",
}

#: Every token this rule can produce. A row carries at most one of them; the
#: batch swaps whichever is present rather than appending a second verdict.
AGE_DRIVER_TOKENS = frozenset(SIGNAL_DRIVERS.values())

#: The one age token that is also a risk flag (``pvo_assembler`` mirrors it into
#: ``risk_flags``); it must be added and removed with the driver.
PAST_CLIFF_TOKEN = SIGNAL_DRIVERS["past_cliff"]


def cliff_band(position: str, age: Optional[float]) -> Optional[str]:
    """The cliff band for a player, or None when the rule does not apply.

    Returns None for a non-skill position or a missing age — the same two
    conditions under which ``audit_player`` declines to produce a verdict.
    ``int(age)`` truncates exactly as the roster audit has always done, so a
    fractional prospect age lands in the same band on both surfaces.
    """
    if position not in CLIFF_AGES or age is None:
        return None
    # The age arriving here is Sleeper's raw value (sleeper_universe.py:245 copies it
    # with no coercion) and this runs inside the single artifact-build loop, so an
    # unparseable age must degrade THIS row, never abort the 12,227-row build and
    # leave the morning with no artifact at all.
    try:
        years_to_cliff = CLIFF_AGES[position] - int(float(age))
    except (TypeError, ValueError):
        return None
    if years_to_cliff < 0:
        return "past_cliff"
    if years_to_cliff == 0:
        return "at_cliff"
    if years_to_cliff <= 2:
        return "approaching_cliff"
    return "no_age_signal"


def cliff_driver(position: str, age: Optional[float]) -> Optional[str]:
    """The evidence token stating this player's age verdict, or None."""
    band = cliff_band(position, age)
    return SIGNAL_DRIVERS[band] if band else None


def restate_age_verdict(
    drivers: Optional[list[Any]],
    risk_flags: Optional[list[Any]],
    position: str,
    served_age: Optional[float],
) -> tuple[Optional[list[Any]], Optional[list[Any]]]:
    """Restate a row's age verdict in terms of the age actually being served.

    The artifact's age tokens were computed at the feature-season age, which is a
    year stale once the season turns; the age printed beside them is Sleeper's
    (DG-139). This replaces the stale token in place — preserving position, so a
    reader cannot tell the difference except that the sentence is now true — and
    keeps ``age_past_position_cliff`` in ``risk_flags`` in step with it.

    A row carrying no age token is left alone: a verdict is never INVENTED for a
    player the model did not give one to. Both lists are returned unchanged (and
    ``None`` stays ``None``) when there is nothing to restate.
    """
    if not drivers:
        return drivers, risk_flags

    drivers = list(drivers)
    stale = [d for d in drivers if d in AGE_DRIVER_TOKENS]
    if not stale:
        return drivers, risk_flags

    fresh = cliff_driver(position, served_age)
    if fresh is None:
        # No verdict is derivable at the served age (no age, or a position the
        # rule does not cover — e.g. a row whose served position has drifted).
        # Drop the stale claim rather than keep asserting it.
        out_drivers = [d for d in drivers if d not in AGE_DRIVER_TOKENS]
    else:
        seen = False
        out_drivers = []
        for d in drivers:
            if d in AGE_DRIVER_TOKENS:
                if not seen:
                    out_drivers.append(fresh)
                    seen = True
                continue
            out_drivers.append(d)

    out_flags = risk_flags
    has_past = fresh == PAST_CLIFF_TOKEN
    current = list(risk_flags or [])
    if has_past and PAST_CLIFF_TOKEN not in current:
        # A past-cliff verdict always carries its flag, even onto a row that had
        # none — the flag is what makes the counter-argument mandatory downstream.
        out_flags = [*current, PAST_CLIFF_TOKEN]
    elif not has_past and PAST_CLIFF_TOKEN in current:
        out_flags = [f for f in current if f != PAST_CLIFF_TOKEN]

    return out_drivers, out_flags
