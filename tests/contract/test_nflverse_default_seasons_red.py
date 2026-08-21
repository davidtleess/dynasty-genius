"""RED contract: the scheduled capture requests the CURRENT league season.

Measured 2026-08-21: `scripts/run_nflverse_usage_capture.py` declared
`DEFAULT_SEASONS = (2023, 2024, 2025)` and the LaunchAgent passes no `--seasons`. So the job
that runs at 06:15 every morning re-fetched three FINISHED seasons — proven byte-identical
across runs — and requested 2026 from nothing. `load_depth_charts(seasons=[2026])` returns
455,941 rows today, updated daily through training camp, and none of it was being captured.

Hardcoding `2026` fixes this morning and breaks next March. The same edit would be due every
year, and in 2027 it falls inside the season when only Tier 0 lands. So the current league
season is DERIVED from the date.

The NFL league year opens in mid-March; the live 2026 depth chart series begins 2026-03-22.
Treating March as the boundary can flip up to ~two weeks early, and that is deliberately safe:
an early flip asks for a season the source has not published, which
`test_nflverse_season_availability_red` pins as a recorded `not_yet_available` skip rather than
a failure. The two guards compose — the derivation may be approximate precisely because the
refusal path is exact.
"""

from __future__ import annotations

from datetime import date

from src.dynasty_genius.nflverse_usage import (
    ARCHIVE_SEASONS,
    current_league_season,
    default_capture_seasons,
)

# --------------------------------------------------------------------------
# The league-year boundary
# --------------------------------------------------------------------------


def test_august_is_the_season_that_is_about_to_be_played() -> None:
    """2026-08-21: training camp. The 2026 season is the live one."""
    assert current_league_season(date(2026, 8, 21)) == 2026


def test_september_through_december_is_the_current_calendar_year() -> None:
    assert current_league_season(date(2026, 9, 10)) == 2026
    assert current_league_season(date(2026, 12, 28)) == 2026


def test_january_and_february_still_belong_to_the_previous_season() -> None:
    """The playoffs of the 2026 season are played in January 2027."""
    assert current_league_season(date(2027, 1, 15)) == 2026
    assert current_league_season(date(2027, 2, 8)) == 2026


def test_the_league_year_opens_in_march() -> None:
    assert current_league_season(date(2027, 3, 20)) == 2027


def test_the_season_rolls_over_without_a_code_change() -> None:
    """The property that matters: no edit is due in 2027, 2028 or ever."""
    assert current_league_season(date(2030, 8, 1)) == 2030
    assert current_league_season(date(2031, 1, 1)) == 2030


# --------------------------------------------------------------------------
# What the scheduled job actually asks for
# --------------------------------------------------------------------------


def test_the_default_seasons_include_the_current_league_season() -> None:
    assert 2026 in default_capture_seasons(date(2026, 8, 21))


def test_the_default_seasons_still_include_the_declared_archive() -> None:
    """Splitting archival backfill out of the daily path is deferred, not done here."""
    seasons = default_capture_seasons(date(2026, 8, 21))
    assert set(ARCHIVE_SEASONS).issubset(set(seasons))


def test_the_default_seasons_are_sorted_and_carry_no_duplicate() -> None:
    """A season requested twice would fetch, normalize and reconcile the same rows twice."""
    seasons = default_capture_seasons(date(2026, 8, 21))
    assert seasons == tuple(sorted(set(seasons)))


def test_a_current_season_already_in_the_archive_is_not_duplicated() -> None:
    """Once the archive catches up to the live season the two must not collide."""
    seasons = default_capture_seasons(date(2025, 8, 21))
    assert seasons.count(2025) == 1


# --------------------------------------------------------------------------
# The wiring — the LaunchAgent passes no --seasons, so the default IS the schedule
# --------------------------------------------------------------------------


def test_the_scheduled_runner_defaults_to_the_derived_seasons() -> None:
    """`ProgramArguments` is exactly [python, run_nflverse_usage_capture.py] — no flags.

    So whatever this default holds is precisely what the 06:15 job captures every morning.
    """
    from scripts import run_nflverse_usage_capture

    assert tuple(run_nflverse_usage_capture.DEFAULT_SEASONS) == default_capture_seasons()


def test_the_scheduled_runner_asks_for_the_current_season() -> None:
    """The defect this ticket exists to end: 2026 was requested from nothing."""
    from scripts import run_nflverse_usage_capture

    assert current_league_season() in tuple(run_nflverse_usage_capture.DEFAULT_SEASONS)
