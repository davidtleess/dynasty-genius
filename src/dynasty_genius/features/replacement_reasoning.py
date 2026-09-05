"""DG-160 — replacement level, explained from the live lineup so a wrong derivation shows.

David's 2026-08-31 ranking ruling 5, in his own words:

    "REPLACEMENT LEVEL — let the derived number stand and show the reasoning. Compute it as an
     order statistic from the real lineup structure. 'Replacement TE = the 12th-best TE,
     because your league starts 12.'"

The order-statistic half shipped as ``ENGINE_B_VAR_THRESHOLDS``. This is the other half.

**It is a detector, not a caption, and the difference is the whole design.** A line reading
"replacement = 8.79 points a game" tells him nothing he can check: a wrong rank is invisible in
it. So this prints the slot arithmetic — how many of this position his league starts every
week, and how many more the rank assumes are started in a shared place.

**The detector itself is a budget, and it needs no assumption at all.** A first attempt asked
whether each position's rank was individually defensible, and it was too permissive to catch
anything: allowing every shared place to go to one position makes almost any rank arguable. The
question that bites is whether the four ranks can be true AT THE SAME TIME. Each rank implies a
demand on the shared places — rank minus dedicated starters minus one — and those demands
compete for one pool. On David's league the four shipped ranks demand 48 shared places from a
league that has 36. No split of the flex makes all four true; it is arithmetic, not taste, and
receiver alone accounts for 28 of the 36.

That is not a hypothetical safeguard. ``ENGINE_B_VAR_THRESHOLDS['WR'] = 53`` carries a comment
deriving it from "12 x 3 = 36 + ~7 flex + buffer" — a third receiver slot his league does not
have. His league starts two. Had this been on his roster in August he would have said "I start
two" in a sentence, and a wrong constant would not have survived to six days before kickoff.
**Nothing here is told that receiver is the broken one**; it compares every position the same
way and receiver is the one that fails.

**What it deliberately does not do:** it changes no constant and no number David already sees.
It cannot, by construction — it computes an explanation and a verdict, and never returns a
replacement value of its own. Correcting the thresholds is separate work and waits on him.

**Honesty about what is not derivable.** The dedicated slots are unambiguous: multiply each
position's starting slots by the number of teams. The flex and superflex places are shared, and
how they split between positions is behavioural rather than structural. It cannot be measured
honestly today either — the 52 daily snapshots on disk are the same lineups re-observed, with
two edits between them, so they are one observation of 21 filled flex slots rather than 1,091,
and pooling them would be pseudo-replication dressed as evidence. So this refuses to invent a
split. It reports how many shared places each rank assumes and says, on screen, that the split
is a judgement rather than a fact.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

# The league runs the daily chain captures. Read from here rather than from Sleeper: no
# network in a request path, and it is the same governed snapshot every other derivation uses.
LEAGUE_RUNTIME_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "data" / "league_runtime" / "runs"
)

# Slot tokens that are not a starting place at all.
NON_STARTING_SLOTS = frozenset({"BN", "IR", "TAXI"})

# Which slot tokens a position can be started in beyond its own dedicated slot. Read from the
# league's roster_positions rather than assumed: a superflex takes a quarterback, a flex does
# not, and that difference is what makes the quarterback rank derivable without any assumption.
FLEX_SLOT = "FLEX"
SUPERFLEX_SLOT = "SUPER_FLEX"
FLEX_ELIGIBLE = frozenset({"RB", "WR", "TE"})
SUPERFLEX_ELIGIBLE = frozenset({"QB", "RB", "WR", "TE"})

_POSITION_WORDS = {
    "QB": ("quarterback", "quarterbacks"),
    "RB": ("running back", "running backs"),
    "WR": ("receiver", "receivers"),
    "TE": ("tight end", "tight ends"),
}


class DerivationStatus(Enum):
    """Whether the shipped ranks can all be true at once in this league."""

    AGREES = "agrees"
    DISAGREES = "disagrees"


@dataclass(frozen=True)
class StartingSlots:
    """What the league actually starts, counted across every team."""

    dedicated: dict[str, int]
    flex_pool: int
    superflex_pool: int

    @property
    def shared_pool(self) -> int:
        """Places not tied to one position: the flex and superflex slots together."""
        return self.flex_pool + self.superflex_pool


def starting_slots(roster_positions: Iterable[str], *, teams: int) -> StartingSlots:
    """Count starting places from the league's own roster structure.

    Deliberately reads the slot list rather than any comment or constant: the comment above the
    receiver threshold is precisely the thing that was wrong, and a derivation that trusted it
    would reproduce the bug it exists to catch.
    """
    dedicated: dict[str, int] = {}
    flex = superflex = 0
    for slot in roster_positions:
        token = str(slot).upper()
        if token in NON_STARTING_SLOTS:
            continue
        if token == FLEX_SLOT:
            flex += teams
        elif token == SUPERFLEX_SLOT:
            superflex += teams
        else:
            dedicated[token] = dedicated.get(token, 0) + teams
    return StartingSlots(dedicated=dedicated, flex_pool=flex, superflex_pool=superflex)


def _words(position: str) -> tuple[str, str]:
    return _POSITION_WORDS.get(position.upper(), (position, position))


def shared_places_demanded(rank: int, dedicated: int) -> int:
    """How many shared places a rank implies, beyond the players who start every week.

    A replacement level at rank N means N-1 players start somewhere. Of those, `dedicated`
    have a slot of their own; the rest must be taking flex or superflex places.
    """
    return max(0, rank - dedicated - 1)


def audit_shared_slot_budget(
    *, thresholds: dict[str, int], roster_positions: Sequence[str], teams: int
) -> dict[str, Any]:
    """Can all four replacement ranks be true at the same time in this league?

    This is the detector, and its whole value is that it assumes NOTHING about behaviour. It
    never asks how the flex splits between positions — an unanswerable question here, since
    every lineup on record is the same one re-observed. It asks only whether the ranks jointly
    demand more shared places than the league has. That is arithmetic, and it is decisive.

    On David's league today the four shipped ranks demand 48 shared places from a league that
    has 36, over-subscribed by 12, with receiver alone demanding 28 of the 36. That is not a
    matter of taste about flex usage: no split exists that makes all four true.
    """
    slots = starting_slots(roster_positions, teams=teams)
    demands = {
        position: shared_places_demanded(rank, slots.dedicated.get(position, 0))
        for position, rank in thresholds.items()
    }
    demanded = sum(demands.values())
    available = slots.shared_pool
    over = demanded - available
    worst = max(demands, key=lambda p: demands[p]) if demands else None
    return {
        "demands": demands,
        "demanded": demanded,
        "available": available,
        "over_subscribed_by": max(0, over),
        "status": DerivationStatus.DISAGREES if over > 0 else DerivationStatus.AGREES,
        "largest_demand": worst,
        "explanation": (
            f"Your replacement levels assume {demanded} players start in a flex or superflex "
            f"place, but your league only has {available} of them"
            + (
                f" — {demands[worst]} of that demand is at {_words(worst)[0]} alone."
                if worst and over > 0
                else "."
            )
        ),
        "decision_supported": False,
    }


def explain_replacement(
    *,
    position: str,
    shipped_rank: int,
    roster_positions: Sequence[str],
    teams: int,
    replacement_ppg: float,
    thresholds: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Explain one position's replacement level in the terms David asked for.

    Returns the rank, the points per game it resolves to, the reason in plain language built
    from his real slots, how many shared places the rank implies, and — when the other
    positions' ranks are supplied — whether they can all be true at once. It never returns a
    replacement value of its own and never changes one.
    """
    position = position.upper()
    slots = starting_slots(roster_positions, teams=teams)
    dedicated = slots.dedicated.get(position, 0)
    demanded = shared_places_demanded(shipped_rank, dedicated)

    eligible_for_shared = (position in FLEX_ELIGIBLE and slots.flex_pool > 0) or (
        position in SUPERFLEX_ELIGIBLE and slots.superflex_pool > 0
    )

    singular, plural = _words(position)
    reason = (
        f"the {_ordinal(shipped_rank)}-best {singular}, because your league starts "
        f"{dedicated} {plural} every week"
    )
    if demanded:
        reason += (
            f" and this assumes {demanded} more are started in your "
            f"{slots.shared_pool} flex and superflex places"
        )

    budget = (
        audit_shared_slot_budget(
            thresholds=thresholds, roster_positions=roster_positions, teams=teams
        )
        if thresholds
        else None
    )

    return {
        "position": position,
        "rank": shipped_rank,
        "points_per_game": replacement_ppg,
        "reason": reason,
        "dedicated": dedicated,
        "shared_places_demanded": demanded,
        "shared_places_available": slots.shared_pool,
        "status": budget["status"] if budget else None,
        "budget": budget,
        "flex_is_assumed": bool(demanded) and eligible_for_shared,
        "assumption": (
            "How many of the shared flex places go to this position is a judgement, not a fact "
            "about your league. Nobody has measured how your managers actually fill them: "
            "every lineup on record is the same one re-observed, so there is one observation "
            "to go on, not fifty-two."
            if demanded
            else ""
        ),
        "decision_supported": False,
    }


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def load_league_structure(
    runtime_root: Path | str | None = None,
) -> Optional[dict[str, Any]]:
    """The lineup the explanation is derived from: slot list and team count.

    Returns None when no snapshot is readable, and the caller then shows NO reasoning at all.
    That is deliberate: a derivation stated without the league's own slots would be a confident
    sentence resting on a structure nobody checked, which is the failure this module exists to
    catch. Silence is the honest degradation; a guess is not.
    """
    root = Path(runtime_root) if runtime_root is not None else LEAGUE_RUNTIME_ROOT
    try:
        snapshots = sorted(root.glob("league-*/snapshot.json"))
    except OSError:
        return None
    for path in reversed(snapshots):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        league = payload.get("league") or {}
        roster_positions = league.get("roster_positions")
        rosters = payload.get("rosters")
        if not roster_positions or not rosters:
            continue
        return {
            "roster_positions": list(roster_positions),
            "teams": len(rosters),
            "captured_at": payload.get("captured_at"),
        }
    return None
