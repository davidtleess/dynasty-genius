"""Manifest prose for the rookie run, derived from the AUTHORITATIVE outcome block.

The logged 2026-09-06 follow-up: the legacy ``definitions`` text said "regular-season" while the
``outcomes`` and ``units`` blocks specified the championship window. Prose is now generated from
the bound outcome block's ``window_rule`` so the two cannot disagree. The legacy wording survives
only when no outcome artifact is bound, because then there is no window to name.
"""
from __future__ import annotations

from collections.abc import Mapping

__all__ = ["manifest_definitions"]


def manifest_definitions(*, outcome_block: Mapping | None, bar: Mapping[str, int], last_completed_season: int) -> dict[str, str]:
    """The five definition strings the manifest carries; the window is read from ``outcome_block``."""
    tail = ("tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance; "
            "cohort players are ranked at their DRAFT role every season, others at their weekly-stats position")
    if outcome_block:
        scope = f"the outcome window ({outcome_block['window_rule']})"
        return {
            "qualifying_season": f"finished at or above the bar rank for the position by points inside {scope}; bar = {dict(bar)}; {tail}",
            "appearance": (f"at least one weekly stat row inside {scope} (not 'dressed', not 'took a snap'); "
                           "a player without a stat row in the window scored zero window points that season"),
            "season_points": f"PPR points (nflverse weekly fantasy_points_ppr) summed inside {scope}, exactly 0 without an appearance",
            "games": f"weeks with a weekly stat row inside {scope}, exactly 0 without an appearance",
            "identity_unresolved": _identity_text(last_completed_season),
        }
    return {
        "qualifying_season": f"finished at or above the bar rank for the position by regular-season PPR total; bar = {dict(bar)}; {tail}",
        "appearance": ("at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); "
                       "a player without a stat row scored zero fantasy points that season"),
        "season_points": "regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance",
        "games": "weeks with a weekly stat row, exactly 0 without an appearance",
        "identity_unresolved": _identity_text(last_completed_season),
    }


def _identity_text(last_completed_season: int) -> str:
    return (f"no gsis_id in nflverse draft picks and no match in the players table or 1999-{last_completed_season} rosters "
            "by draft key or name+year; labels NaN, never zero, except in the named sensitivity arm")
