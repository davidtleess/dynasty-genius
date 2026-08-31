"""Derive week finality from the schedule itself, rather than believing a feed.

David's ruling, 2026-08-31, verbatim:

    "a week ends after Monday Night Football every single week of the regular season.
    So, at the very least for the regular season, the week is over typically by Tuesday
    at 3 or 4 a.m. Otherwise, the NFL schedule is broken out by week. You could use that
    as well; for example, look at the schedule for Week 1 and see when the last game in
    Week 1 is. When that game is over, the week is final, and the stats are in."

WHY THIS IS THE RIGHT SHAPE, and not merely a smaller option than the alternatives: it
replaces an ASSERTION with a DERIVATION. "The feed says final" is a source's claim about
itself. "The last game of week 1 has ended" is a fact the schedule already contains and
that nobody has to be trusted to declare. Every defect found on 2026-08-31 was the first
kind wearing the second's clothes -- ``noop`` counted as success, ``tier: auxiliary``
unable to dim the root, a constant rendered as a measurement, ``launchctl`` reporting
exit 0 for a job that never ran. A self-report standing in for an observable.

``run_realized_outcome_scoring._default_schedule_loader`` states the rule this module is
built to satisfy: a populated score proves play was OBSERVED, never that play ENDED, so
the score-derived loader may never certify finality. That door was closed deliberately
(commit ``17cfc1e9``) and the thing meant to reopen it -- a governed finality provider --
was never built. **This is that provider.** The score-derived default is left exactly as
it is; this is a second, explicit door beside it.

Three refusals, each one a way a week could be closed too early:

  - A game whose kickoff has not passed is ``scheduled`` **whatever its score column
    says**. A score on an unplayed game is bad data, not evidence.
  - A game with no score after the week's clock has run keeps the week open. That is the
    postponement case, and it is precisely what David's "at the very least for the
    regular season" caveat points at. Grading a week that has not finished playing is
    worse than grading it late.
  - A game with an unreadable kickoff time closes nothing. Unknown is treated as
    still-to-come, because the alternative is dropping it out of the ``max()`` and
    silently shortening the week.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

# The NFL schedule publishes kickoff in US Eastern.
DEFAULT_TZ = "America/New_York"

# Not game length -- "when the stats are settled". A 20:15 Monday kickoff plus this lands
# at 03:15 Tuesday Eastern, which is what David described as "typically by Tuesday at 3 or
# 4 a.m.". Erring late costs a few hours of delay; erring early grades a week that is
# still being played, so the asymmetry is deliberate.
DEFAULT_SETTLE_HOURS = 7.0

FINAL = "final"
OBSERVED = "result_observed_unverified"
SCHEDULED = "scheduled"


def _kickoff(game: dict[str, Any], tz: ZoneInfo) -> Optional[datetime]:
    """Kickoff as an aware datetime, or None when it cannot be read."""
    gameday = game.get("gameday")
    gametime = game.get("gametime")
    if not isinstance(gameday, str) or not gameday.strip():
        return None
    if not isinstance(gametime, str) or not gametime.strip():
        return None
    try:
        return datetime.fromisoformat(f"{gameday.strip()}T{gametime.strip()}").replace(
            tzinfo=tz
        )
    except ValueError:
        return None


def _has_score(game: dict[str, Any]) -> bool:
    for field in ("home_score", "away_score"):
        value = game.get(field)
        if value is None:
            return False
        if isinstance(value, str) and value.strip().lower() in {"", "none", "nan"}:
            return False
        if isinstance(value, float) and value != value:  # NaN
            return False
    return True


def derive_week_finality(
    games: Iterable[dict[str, Any]],
    *,
    season: int,
    week: int,
    now: datetime,
    settle_hours: float = DEFAULT_SETTLE_HOURS,
    tz: str = DEFAULT_TZ,
) -> dict[str, Any]:
    """Build the schedule dict ``week_status`` consumes, certifying finality when earned.

    Returns the same shape as ``_default_schedule_loader`` so it is a drop-in authority:
    ``{season, week, expected_game_count, games:[{season, week, game_id, status,
    gameday}]}``.
    """
    zone = ZoneInfo(tz)
    rows = list(games)

    kickoffs = [_kickoff(game, zone) for game in rows]
    # An unreadable kickoff must not drop out of the max() and shorten the week.
    week_clock_run = bool(rows) and all(k is not None for k in kickoffs)
    if week_clock_run:
        week_ends = max(kickoffs) + timedelta(hours=settle_hours)  # type: ignore[type-var]
        week_clock_run = now >= week_ends

    game_rows: list[dict[str, Any]] = []
    for game, kickoff in zip(rows, kickoffs):
        if kickoff is None or now < kickoff:
            status = SCHEDULED
        elif not _has_score(game):
            status = SCHEDULED
        elif week_clock_run:
            status = FINAL
        else:
            status = OBSERVED
        game_rows.append(
            {
                "season": season,
                "week": week,
                "game_id": game.get("game_id"),
                "status": status,
                "gameday": game.get("gameday"),
            }
        )

    return {
        "season": season,
        "week": week,
        "expected_game_count": len(rows),
        "games": game_rows,
    }
