"""The freshness layer must grade an artifact's INPUTS, not just its shape.

`feature_refresh` graded `fresh` on `embedded_timestamp_fresh` all summer while its
own `stream_provenance` recorded participation as `loaded_empty` and three other
streams silently serving the season BEFORE the one requested. The producer wrote that
block every run; nothing outside the producer read it.

(DG-023, 2026-08-25 corrected two words in that sentence, and this file inherited both.
Participation was never empty — it loads 45,184 rows and its frame carries no `season`
column, which the reader was treating as emptiness. And a step-back is not a "cache"
read: `fallback_used` means the requested season was REFUSED and an earlier window was
served live. The three step-backs are real; only the labels were wrong.) Harmless in August because 2026 had
not happened — but from Week 1 it is the failure that makes numbers wrong and
fine-looking at the same time, and anything grading predictions built on those
features inherits it.

The second contract here is the one that is easy to forget: a signal that always says
"degraded" carries exactly as little information as one that always says "fresh".
Healthy inputs must still grade fresh, and a partial failure must name which streams
failed and which are fine.
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


def _stream(status="loaded", season=2026, fallback=False, error=None):
    return {
        "status": status,
        "effective_season": season,
        "fallback_used": fallback,
        "error_type": error,
    }


def _config(**overrides):
    artifact = {
        "artifact_id": "feature_refresh",
        "path": "app/data/features_runtime/feature_refresh_latest_report.json",
        "producer": "scripts/run_feature_refresh.py",
        "cadence": "weekly",
        "scheduled_time_local": "09:15",
        "grace_hours": 3,
        "tier": "daily_diagnostics",
        "min_size_bytes": 64,
        "timestamp_field": "generated_at",
        "input_provenance_field": "stream_provenance",
        "dormant_ok": True,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    artifact.update(overrides)
    return ReportFreshnessConfig.model_validate(
        {"config_version": 2, "timezone": "America/New_York", "artifacts": [artifact]}
    )


def _fact(provenance):
    """A file that is present, on time, big enough, and freshly stamped — i.e. one
    that every SHAPE check passes. Only the inputs are in question."""
    return ReportArtifactFact(
        exists=True,
        size_bytes=4096,
        mtime=_NOW,
        embedded_timestamp_value=_NOW.isoformat(),
        input_provenance=provenance,
    )


def _evaluate(provenance, config=None):
    config = config or _config()
    return evaluate_report_freshness(
        config=config,
        artifact_facts={"feature_refresh": _fact(provenance)},
        now=_NOW,
    )[0]


def test_an_otherwise_fresh_artifact_with_an_empty_stream_is_not_fresh():
    """The core defect: a punctual, successful run built on an empty input."""
    report = _evaluate(
        {
            "participation": _stream(status="loaded_empty", season=None, fallback=True,
                                     error="ValueError"),
            "rosters": _stream(),
        }
    )

    assert report.status == "inputs_degraded", (
        "an artifact whose input loaded empty must not grade fresh"
    )
    assert "participation" in report.basis


def test_a_stream_that_stepped_back_a_season_is_not_fresh():
    """`fallback_used` is the quiet one — the stream loaded, just not from the season
    it was asked for. Named for what it is: a season step-back, never a cache read."""
    report = _evaluate(
        {
            "pbp": _stream(season=2025, fallback=True, error="ConnectionError"),
            "rosters": _stream(),
        }
    )

    assert report.status == "inputs_degraded"
    assert "pbp" in report.basis and "2025" in report.basis


def test_healthy_inputs_still_grade_fresh():
    """The anti-amber contract. A light that never says fresh is not a light."""
    report = _evaluate({name: _stream() for name in ("pbp", "rosters", "participation")})

    assert report.status == "fresh", (
        "genuinely live inputs must still grade fresh — always-degraded is the same "
        "defect as always-green wearing the other colour"
    )


def test_the_basis_names_what_failed_and_what_is_fine():
    """`adapter_status:degraded` is not a reason. Name the streams, the cause, and
    the ones that are healthy."""
    report = _evaluate(
        {
            "participation": _stream(status="loaded_empty", season=None,
                                     error="ValueError"),
            "player_stats": _stream(season=2025, fallback=True, error="ConnectionError"),
            "rosters": _stream(),
        }
    )

    assert "participation" in report.basis
    assert "ValueError" in report.basis
    assert "player_stats" in report.basis
    assert "ConnectionError" in report.basis
    # the healthy stream is reported too, so a partial failure reads as partial
    assert "rosters" in report.basis


@pytest.mark.parametrize("block", [None, {}, "not-an-object", [], 0])
def test_the_summarizer_fails_closed_on_any_unreadable_block(block):
    """Config says the block exists. If it does not — absent, empty, or the wrong
    type — the check has lost the thing it was watching. That is a degradation,
    never a silent pass."""
    assert summarize_input_provenance(block)[0] is True


@pytest.mark.parametrize("block", [None, {}])
def test_a_declared_but_unreadable_provenance_block_degrades_the_artifact(block):
    """End to end. Only `None` and `{}` are reachable here by construction: the
    reader coerces any non-object it finds to `{}` before the fact is built, so a
    wrong-typed block arrives as empty rather than propagating its type."""
    assert _evaluate(block).status == "inputs_degraded"


def test_an_artifact_without_the_opt_in_is_unaffected():
    """The gate is opt-in per artifact: undeclared artifacts keep grading on shape."""
    config = _config(input_provenance_field=None)
    report = _evaluate(None, config=config)

    assert report.status == "fresh"
