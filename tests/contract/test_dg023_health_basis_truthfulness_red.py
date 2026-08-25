"""DG-023 — the health gate describes its inputs falsely, in two separate words.

RED rows for the READER half of DG-023. The producer half landed in ``f2e09ab``
(`status` follows the row count) and, measured on 2026-08-25, **changes nothing an
operator sees**: run ``summarize_input_provenance`` over the live block before and
after that fix and the string is byte-identical. The whole user-visible defect
lives here, in ``summarize_input_provenance``.

Two independent false statements, both measured 2026-08-25 against the shipped
artifact ``app/data/features_runtime/feature_refresh_latest_report.json``:

1. **"EMPTY: participation".** ``system_health_models.py`` buckets a stream as empty
   on ``status != "loaded" OR effective_season is None``. ``load_participation``
   returns **45,184 rows for 2025 across 26 columns, none of them ``season``** — so
   the second clause fires on good data no matter what the producer says. Verified::

       >>> f = nflreadpy.load_participation(seasons=[2025]).to_pandas()
       >>> len(f), "season" in f.columns
       (45184, False)

   Those rows reach the build: ``route_participation`` / ``tprr`` / ``yprr`` are each
   populated 498/505 in the inference season. Degrading on a missing COLUMN is
   grading file shape — the exact defect this ticket was opened to remove.

2. **"pbp on 2025 cache".** ``fallback_used`` is ``attempts_made > 1``: the requested
   season was REFUSED and an earlier window was served. It carries no information
   about cache at all. And it cannot: ``nflreadpy``'s ``cache_mode`` is ``MEMORY``,
   which is per-process, so a scheduled run starts with an empty cache and every
   load is a live fetch. Verified::

       >>> get_config().cache_mode
       <CacheMode.MEMORY: 'memory'>
       >>> nflreadpy.load_participation(seasons=[2026])
       ValueError: Season must be between 2016 and 2025

   So the word is false in both directions: what happened was a season step-back,
   and whether anything came from cache is unknowable from this block.

David's rulings, 2026-08-25: fix the words only (the permanently-red gate is filed
separately), and a stream that loaded real rows but reports no season is **healthy
and disclosed**, not degraded.

The gate itself is preserved: an empty stream, an unavailable stream and a
season step-back all still degrade. Only the words change.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.api.routes.system_health_models import (
    ReportArtifactFact,
    ReportFreshnessConfig,
    evaluate_report_freshness,
    summarize_input_provenance,
)

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


def _stream(status="loaded", season=2026, fallback=False, error=None, rows=1000):
    """A provenance entry in the shape the producer writes it after ``f2e09ab``."""
    entry = {
        "status": status,
        "effective_season": season,
        "fallback_used": fallback,
        "error_type": error,
    }
    if rows is not _OMIT:
        entry["row_count"] = rows
    return entry


class _Omit:
    """Sentinel: an artifact written BEFORE the producer fix carries no row count."""


_OMIT = _Omit()


def _participation():
    """The real shape, 2026-08-25: rows loaded, no season column, season refused."""
    return _stream(status="loaded", season=None, fallback=True,
                   error="ValueError", rows=45184)


# ---------------------------------------------------------------------------
# Falsehood 1 — "EMPTY: participation" over 45,184 good rows
# ---------------------------------------------------------------------------

def test_rows_loaded_without_a_season_column_are_not_labelled_empty() -> None:
    """The headline defect. 45,184 rows are not an empty stream."""
    _, basis = summarize_input_provenance({"participation": _participation()})

    assert "EMPTY" not in basis, (
        "a stream carrying 45,184 rows must never be reported EMPTY merely because "
        f"its frame has no `season` column — got: {basis!r}"
    )


def test_rows_loaded_without_a_season_column_do_not_degrade_on_that_fact_alone() -> None:
    """David's ruling 2026-08-25: healthy, but disclosed.

    The ONLY unusual fact here is an unobservable season. No fallback, no error.
    A missing column is frame shape, not data quality.
    """
    degraded, basis = summarize_input_provenance(
        {
            "participation": _stream(status="loaded", season=None, rows=45184),
            "rosters": _stream(),
        }
    )

    assert degraded is False, (
        f"an unobservable season is not a data failure — got degraded, basis: {basis!r}"
    )


def test_the_basis_discloses_a_season_the_source_did_not_report() -> None:
    """Healthy must not mean silent. A reader has to know the season was unverified."""
    _, basis = summarize_input_provenance(
        {"participation": _stream(status="loaded", season=None, rows=45184)}
    )

    assert "participation" in basis
    assert "season not reported" in basis, (
        f"grading it healthy without saying why hides the fact — got: {basis!r}"
    )
    assert "None" not in basis, (
        f"a missing season must be described, never rendered as None — got: {basis!r}"
    )


def test_the_row_count_is_disclosed_when_the_producer_reports_one() -> None:
    """The count is the evidence that 'healthy' is the right call. Show it."""
    _, basis = summarize_input_provenance(
        {"participation": _stream(status="loaded", season=None, rows=45184)}
    )

    assert "45,184" in basis, f"expected the row count in the basis — got: {basis!r}"


# ---------------------------------------------------------------------------
# Falsehood 2 — "on 2025 cache" for a live fetch at an earlier season
# ---------------------------------------------------------------------------

def test_a_season_step_back_is_never_described_as_a_cache() -> None:
    """`fallback_used` means a retry happened. It says nothing about cache.

    With `cache_mode=MEMORY` a scheduled run cannot serve anything from cache at all.
    """
    _, basis = summarize_input_provenance(
        {"pbp": _stream(season=2025, fallback=True, error="ValueError")}
    )

    assert "cache" not in basis.lower(), (
        f"nothing in this block records a cache read — got: {basis!r}"
    )


def test_a_season_step_back_names_the_season_it_served_and_why() -> None:
    """Replace the false word with the true fact, not with vagueness."""
    _, basis = summarize_input_provenance(
        {"pbp": _stream(season=2025, fallback=True, error="ValueError")}
    )

    assert "pbp" in basis
    assert "2025" in basis, "the season actually served must survive the rewording"
    assert "ValueError" in basis, "the reason the requested season was refused"


def test_a_step_back_with_no_observable_season_still_reads_truthfully() -> None:
    """Participation is BOTH cases at once: it steps back AND reports no season."""
    _, basis = summarize_input_provenance({"participation": _participation()})

    assert "None" not in basis, f"got: {basis!r}"
    assert "cache" not in basis.lower(), f"got: {basis!r}"
    assert "ValueError" in basis


# ---------------------------------------------------------------------------
# The gate is preserved — "fix the words, keep the gate"
# ---------------------------------------------------------------------------

def test_a_season_step_back_still_degrades() -> None:
    """Rewording must not disarm the signal."""
    degraded, _ = summarize_input_provenance(
        {"pbp": _stream(season=2025, fallback=True, error="ValueError")}
    )

    assert degraded is True


def test_a_genuinely_empty_stream_is_still_reported_empty() -> None:
    """The negative control. Zero rows is a real failure and keeps its real name."""
    degraded, basis = summarize_input_provenance(
        {"pbp": _stream(status="loaded_empty", season=None, rows=0)}
    )

    assert degraded is True
    assert "EMPTY" in basis


def test_an_unavailable_stream_still_degrades() -> None:
    """A stream that never loaded is not made healthy by having no season."""
    degraded, basis = summarize_input_provenance(
        {"pbp": _stream(status="unavailable", season=None, error="ConnectionError",
                        rows=None)}
    )

    assert degraded is True
    assert "pbp" in basis and "ConnectionError" in basis


def test_all_live_inputs_still_grade_healthy() -> None:
    """The anti-amber contract: a light that never says fresh is not a light."""
    degraded, basis = summarize_input_provenance(
        {name: _stream() for name in ("pbp", "rosters", "snap_counts")}
    )

    assert degraded is False
    assert "2026" in basis


@pytest.mark.parametrize("block", [None, {}, "not-an-object", [], 0])
def test_the_summarizer_still_fails_closed_on_an_unreadable_block(block) -> None:
    """Declared-but-missing stays a degradation, unchanged by this ticket."""
    assert summarize_input_provenance(block)[0] is True


# ---------------------------------------------------------------------------
# Backward compatibility — artifacts written before the producer fix
# ---------------------------------------------------------------------------

def test_a_block_written_before_the_producer_fix_still_summarises() -> None:
    """`row_count` is new. Yesterday's artifact has none and must not crash or lie."""
    degraded, basis = summarize_input_provenance(
        {
            "participation": _stream(status="loaded", season=None, fallback=True,
                                     error="ValueError", rows=_OMIT),
            "rosters": _stream(rows=_OMIT),
        }
    )

    assert degraded is True
    assert "None" not in basis, f"got: {basis!r}"
    assert "rows" not in basis, (
        f"an unknown row count must be omitted, never invented — got: {basis!r}"
    )


# ---------------------------------------------------------------------------
# End to end, on the exact block the product wrote
# ---------------------------------------------------------------------------

def _fact(provenance):
    return ReportArtifactFact(
        exists=True,
        size_bytes=4096,
        mtime=_NOW,
        embedded_timestamp_value=_NOW.isoformat(),
        input_provenance=provenance,
    )


def _config():
    return ReportFreshnessConfig.model_validate(
        {
            "config_version": 2,
            "timezone": "America/New_York",
            "artifacts": [
                {
                    "artifact_id": "feature_refresh",
                    "path": "app/data/features_runtime/feature_refresh_latest_report.json",
                    "producer": "scripts/run_feature_refresh.py",
                    "cadence": "daily",
                    "scheduled_time_local": "09:15",
                    "grace_hours": 3,
                    "tier": "daily_diagnostics",
                    "min_size_bytes": 64,
                    "timestamp_field": "generated_at",
                    "input_provenance_field": "stream_provenance",
                    "dormant_ok": True,
                    "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
                }
            ],
        }
    )


def test_the_live_2026_08_24_block_reads_without_a_falsehood() -> None:
    """The shipped block, with the producer fix applied as it will be in production."""
    report = evaluate_report_freshness(
        config=_config(),
        artifact_facts={
            "feature_refresh": _fact(
                {
                    "participation": _participation(),
                    "pbp": _stream(season=2025, fallback=True, error="ValueError"),
                    "player_stats": _stream(season=2025, fallback=True,
                                            error="ConnectionError"),
                    "snap_counts": _stream(season=2025, fallback=True,
                                           error="ValueError"),
                    "rosters": _stream(season=2026),
                }
            )
        },
        now=_NOW,
    )[0]

    assert report.status == "inputs_degraded", "four streams stepped back — keep the gate"
    assert "EMPTY" not in report.basis, f"got: {report.basis!r}"
    assert "cache" not in report.basis.lower(), f"got: {report.basis!r}"
    assert "rosters" in report.basis, "the healthy stream is still named"
