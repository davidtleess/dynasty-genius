"""RED contract: a season the source does not publish YET is not a failure.

Measured live 2026-08-21 against `nflreadpy`:

    load_depth_charts(seasons=[2026])    -> 455,941 rows          (published)
    load_injuries(seasons=[2026])        -> ValueError: Season must be between 2009 and 2025
    load_snap_counts(seasons=[2026])     -> ValueError: Season must be between 2012 and 2025
    load_nextgen_stats(seasons=[2026])   -> ValueError: Season must be between 2016 and 2025

The streams that have no 2026 data do not return empty — they RAISE. So adding 2026 to the
season list (SR-06) would kill the run on `ngs_passing`, the FIRST stream in `build_streams()`,
before ever reaching the depth charts that are genuinely available. The ticket written to
protect goal 1 would have broken capture entirely.

The fix is not a hardcoded upper bound per stream. A hardcoded bound is a code edit in-season,
after the 2026-09-04 freeze, when only Tier 0 lands. Instead the source's OWN declared bound is
read off the refusal and the season is recorded as `not_yet_available` — so when nflverse
publishes 2026 snap counts after week 1, the data starts flowing with NO code change.

The narrowness is the point. Only a refusal that names a bound the requested season is ABOVE is
skipped. Anything else still fails the run, because a capture that swallows errors it does not
understand is how a season goes missing quietly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.nflverse_usage import (
    NGS_PASSING,
    NGS_RECEIVING,
    NGS_RUSHING,
    SNAP_COUNTS,
    IdentityIndex,
    StreamSpec,
    UsageStore,
    run_usage_capture,
    status_marker_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json"

SPECS = (NGS_PASSING, NGS_RUSHING, NGS_RECEIVING, SNAP_COUNTS)

#: The verbatim refusal `nflreadpy` 0.1.5 raises for a season it has not published.
UNPUBLISHED = "Season must be between 2016 and 2025"


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity() -> IdentityIndex:
    return IdentityIndex.from_governed_crosswalk()


@pytest.fixture()
def harness(fixture_payload):
    def fetch(spec: StreamSpec, season: int):
        return fixture_payload[spec.name]

    return fetch


def _run(tmp_path: Path, harness, identity, **overrides) -> dict[str, Any]:
    kwargs = {
        "seasons": [2025],
        "specs": SPECS,
        "identity": identity,
        "db_path": tmp_path / "usage.db",
        "raw_root": tmp_path / "runtime",
        "fetch": harness,
        **overrides,
    }
    return run_usage_capture(**kwargs)


def _unpublished_above(bound_message: str, unavailable_season: int):
    """A fetch that refuses exactly one season the way the live source refuses it."""

    def fetch(spec: StreamSpec, season: int, _inner=None):
        if season == unavailable_season:
            raise ValueError(bound_message)
        return _inner(spec, season)

    return fetch


# --------------------------------------------------------------------------
# Move 1 — an unpublished season is recorded, and the run still succeeds
# --------------------------------------------------------------------------


def test_a_season_the_source_has_not_published_yet_does_not_fail_the_run(
    tmp_path, harness, identity
) -> None:
    """2026 is above nflverse's published bound today. That is news, not an error."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise ValueError(UNPUBLISHED)
        return harness(spec, season)

    status = _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)

    assert status["status"] == "ok", (
        "a season the source has not published yet must not fail the capture — "
        "otherwise adding 2026 before week 1 kills every stream"
    )


def test_the_unpublished_season_is_recorded_by_name_not_silently_dropped(
    tmp_path, harness, identity
) -> None:
    """A reader must be able to tell 'not published yet' from 'we forgot to fetch it'."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise ValueError(UNPUBLISHED)
        return harness(spec, season)

    status = _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)

    skipped = [r for r in status["results"] if r.get("skipped") == "not_yet_available"]
    assert {r["stream"] for r in skipped} == {s.name for s in SPECS}
    assert {r["season"] for r in skipped} == {2026}
    assert all(r["source_bound"] == 2025 for r in skipped), (
        "the bound must be read off the source's own refusal, not hardcoded"
    )


def test_the_published_season_still_captures_alongside_the_unpublished_one(
    tmp_path, harness, identity
) -> None:
    """2025 must land normally. A skip must not poison the seasons that do exist."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise ValueError(UNPUBLISHED)
        return harness(spec, season)

    _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)

    captures = {c["stream"]: c for c in UsageStore(tmp_path / "usage.db", SPECS).captures()}
    assert captures["ngs_passing"]["status"] == "ok"
    assert captures["snap_counts"]["status"] == "ok"


def test_the_run_marker_records_the_run_as_ok_with_the_skip(
    tmp_path, harness, identity
) -> None:
    """Operational truth: the marker is what the morning report reads."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise ValueError(UNPUBLISHED)
        return harness(spec, season)

    _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)

    marker = json.loads(status_marker_path(tmp_path / "runtime").read_text())
    assert marker["status"] == "ok"


# --------------------------------------------------------------------------
# The narrowness — everything else still fails loudly
# --------------------------------------------------------------------------


def test_a_value_error_that_names_no_bound_still_fails_the_run(
    tmp_path, harness, identity
) -> None:
    """A capture that swallows errors it does not understand loses seasons quietly."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise ValueError("connection reset by peer")
        return harness(spec, season)

    with pytest.raises(Exception, match="connection reset by peer"):
        _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)


def test_a_season_BELOW_the_sources_bound_still_fails_the_run(
    tmp_path, harness, identity
) -> None:
    """Below the bound is a misconfiguration (min_season exists for that), not 'not yet'."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2011:
            raise ValueError(UNPUBLISHED)
        return harness(spec, season)

    with pytest.raises(Exception, match="Season must be between"):
        _run(tmp_path, harness, identity, seasons=[2011, 2025], fetch=fetch)


def test_a_non_value_error_from_the_source_still_fails_the_run(
    tmp_path, harness, identity
) -> None:
    """Only ValueError carries nflreadpy's bound refusal. A 503 is still fatal."""

    def fetch(spec: StreamSpec, season: int):
        if season == 2026:
            raise RuntimeError(UNPUBLISHED)
        return harness(spec, season)

    with pytest.raises(Exception):
        _run(tmp_path, harness, identity, seasons=[2025, 2026], fetch=fetch)
