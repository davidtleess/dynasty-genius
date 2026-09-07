"""Marginal lineup gain — a different basis from value above replacement (DG-178).

Value above the obtainable replacement says what a player is worth against the best man
nobody owns. Marginal lineup gain says what he adds to THIS roster's best feasible lineup.
A healthy bench quarterback can be positive on the first and zero on the second. Both are
true; neither is the other; the result carries its basis so nobody reads one as the other.

The lineup filler is greedy and EXACT only when the starting slots' eligibility sets nest
(QB c SUPER_FLEX; RB, WR, TE c FLEX c SUPER_FLEX — David's league). Fill the most restrictive
slots first with the best eligible remaining player and no exchange can improve the total.
A league whose slots do not nest (REC_FLEX beside WRRB_FLEX) is refused rather than solved
wrongly.

Scenario: one week at the h=0 rate with every listed player available at that rate. It is a
lineup comparison, not a forecast of the season.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.dynasty_genius.ranking.contract import BASIS_MARGINAL_LINEUP_GAIN
from src.dynasty_genius.ranking.league_settings import (
    SLEEPER_SLOT_ELIGIBILITY,
    LeagueSettings,
)

SCENARIO = ("one week at the h=0 rate, every listed player available at his rate, "
            "best feasible lineup with and without him")


class Starter(BaseModel):
    model_config = ConfigDict(frozen=True)

    player_id: str
    position: str
    rate_ppg: float


class Lineup(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_ppg: float
    assignment: dict[str, list[str]]


class LineupGain(BaseModel):
    model_config = ConfigDict(frozen=True)

    player_id: str
    gain_ppg: float
    with_total_ppg: float
    without_total_ppg: float
    basis: str = Field(default=BASIS_MARGINAL_LINEUP_GAIN)
    h: int = 0
    scenario: str = SCENARIO


def eligibility_nests(settings: LeagueSettings) -> bool:
    sets = [SLEEPER_SLOT_ELIGIBILITY[s] for s in settings.starting_slots]
    for a in sets:
        for b in sets:
            if not (a <= b or b <= a or a.isdisjoint(b)):
                return False
    return True


def best_lineup(roster: list[Starter], settings: LeagueSettings) -> Lineup:
    if not eligibility_nests(settings):
        raise NotImplementedError(
            "the starting slots' eligibility sets do not nest; greedy filling is not exact "
            "here and a wrong lineup is worse than none"
        )
    ids = [s.player_id for s in roster]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"duplicate player identity in the roster: {dupes}")
    remaining = sorted(roster, key=lambda s: s.rate_ppg, reverse=True)
    assignment: dict[str, list[str]] = {}
    total = 0.0
    order = sorted(settings.starting_slots.items(), key=lambda kv: (len(SLEEPER_SLOT_ELIGIBILITY[kv[0]]), kv[0]))
    for slot, count in order:
        eligible = SLEEPER_SLOT_ELIGIBILITY[slot]
        assignment[slot] = []
        for _ in range(count):
            pick = next((s for s in remaining if s.position.upper() in eligible), None)
            if pick is None:
                break
            remaining.remove(pick)
            assignment[slot].append(pick.player_id)
            total += pick.rate_ppg
    return Lineup(total_ppg=total, assignment=assignment)


def marginal_lineup_gain(roster: list[Starter], candidate: Starter, settings: LeagueSettings) -> LineupGain:
    """best(with him) - best(without him). A player already on the roster is not added twice:
    his gain is the remove-one counterfactual, so identity is enforced in both directions."""
    others = [s for s in roster if s.player_id != candidate.player_id]
    without = best_lineup(others, settings)
    with_ = best_lineup([*others, candidate], settings)
    return LineupGain(player_id=candidate.player_id,
                      gain_ppg=max(0.0, with_.total_ppg - without.total_ppg),
                      with_total_ppg=with_.total_ppg, without_total_ppg=without.total_ppg)


def active_lineup_pool(roster_entry: dict) -> list[str]:
    """The sleeper ids a Sleeper roster may actually start this week: everyone on the roster
    minus the taxi squad and the injured reserve. A taxi rookie's lineup gain is a gain he
    cannot legally deliver, so he is not in the pool."""
    excluded = {str(x) for x in (roster_entry.get("taxi") or [])} | {str(x) for x in (roster_entry.get("reserve") or [])}
    return [str(pid) for pid in (roster_entry.get("players") or []) if str(pid) not in excluded]
