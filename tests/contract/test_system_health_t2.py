"""DEBT-6 Slice 1c T2 RED: pure report freshness evaluator + tier rollup.

Constructed artifact facts only. This file intentionally does not touch disk,
real configs, adapters, FastAPI route wiring, app/main, or OpenAPI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

NY = ZoneInfo("America/New_York")


def _models():
    import app.api.routes.system_health_models as models

    return models


def _artifact(models, overrides: dict[str, Any] | None = None):
    data = {
        "artifact_id": "pvo_refresh",
        "path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "cadence": "daily",
        "scheduled_time_local": "09:30",
        "grace_hours": 3,
        "tier": "core_substrate",
        "min_size_bytes": 128,
        "timestamp_field": None,
        "dormant_ok": False,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    if overrides:
        data.update(overrides)
    return models.ReportArtifactConfig.model_validate(data)


def _config(models, artifacts):
    return models.ReportFreshnessConfig.model_validate(
        {
            "config_version": 1,
            "timezone": "America/New_York",
            "artifacts": artifacts,
        }
    )


def _fact(models, **overrides):
    data = {
        "exists": True,
        "size_bytes": 4096,
        "mtime": datetime(2026, 7, 2, 9, 35, tzinfo=NY),
        "embedded_timestamp_value": None,
    }
    data.update(overrides)
    return models.ReportArtifactFact.model_validate(data)


def _evaluate(models, artifact, fact, now: datetime):
    reports = models.evaluate_report_freshness(
        config=_config(models, [artifact]),
        artifact_facts={artifact.artifact_id: fact},
        now=now,
    )
    assert len(reports) == 1
    report = reports[0]
    assert report.artifact_id == artifact.artifact_id
    assert report.tier == artifact.tier
    assert report.artifact_path == artifact.path
    assert report.producer == artifact.producer
    assert report.decision_supported is False
    return report


def test_embedded_timestamp_wins_over_old_mtime_without_fallback_disclosure() -> None:
    models = _models()
    artifact = _artifact(models, {"timestamp_field": "generated_at"})
    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            mtime=datetime(2026, 6, 30, 9, 30, tzinfo=NY),
            embedded_timestamp_value="2026-07-02T09:35:00-04:00",
        ),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.observed_at == "2026-07-02T09:35:00-04:00"
    assert report.age_seconds == 1500
    assert "embedded_timestamp" in report.basis
    assert "timestamp_source:mtime_fallback" not in report.disclosures


def test_mtime_fallback_is_disclosed_when_no_timestamp_field_is_declared() -> None:
    models = _models()
    artifact = _artifact(models, {"timestamp_field": None})
    report = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 7, 2, 9, 45, tzinfo=NY)),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.observed_at == "2026-07-02T09:45:00-04:00"
    assert "timestamp_source:mtime_fallback" in report.disclosures


def test_past_schedule_inside_grace_reports_overdue_not_fresh_or_degraded() -> None:
    models = _models()
    artifact = _artifact(models)
    report = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 7, 1, 9, 35, tzinfo=NY)),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )
    overall_status, worst_tier = models.rollup_health_status(reports=[report])

    assert report.status == "freshness_overdue"
    assert "within_grace" in report.basis
    assert overall_status == "ok"
    assert worst_tier is None


def test_past_grace_stale_tier_a_report_degrades_core_substrate() -> None:
    models = _models()
    artifact = _artifact(models, {"tier": "core_substrate"})
    report = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 7, 1, 9, 35, tzinfo=NY)),
        now=datetime(2026, 7, 2, 12, 31, tzinfo=NY),
    )
    overall_status, worst_tier = models.rollup_health_status(reports=[report])

    assert report.status == "stale"
    assert "past_grace" in report.basis
    assert overall_status == "degraded"
    assert worst_tier == "core_substrate"


def test_below_min_size_is_corrupt_or_empty_even_when_timestamp_is_fresh() -> None:
    models = _models()
    artifact = _artifact(models, {"tier": "daily_diagnostics", "min_size_bytes": 128})
    report = _evaluate(
        models,
        artifact,
        _fact(models, size_bytes=64, mtime=datetime(2026, 7, 2, 9, 45, tzinfo=NY)),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )
    overall_status, worst_tier = models.rollup_health_status(reports=[report])

    assert report.status == "corrupt_or_empty"
    assert "below_min_size" in report.basis
    assert overall_status == "degraded"
    assert worst_tier == "daily_diagnostics"


def test_malformed_embedded_timestamp_degrades_without_silent_mtime_fallback() -> None:
    models = _models()
    artifact = _artifact(
        models,
        {"tier": "daily_diagnostics", "timestamp_field": "generated_at"},
    )
    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            mtime=datetime(2026, 7, 2, 9, 45, tzinfo=NY),
            embedded_timestamp_value="not-a-timestamp",
        ),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    assert report.status == "corrupt_or_empty"
    assert "malformed_embedded_timestamp" in report.basis
    assert "timestamp_source:mtime_fallback" not in report.disclosures


def test_future_embedded_timestamp_is_corrupt_and_discloses_negative_age() -> None:
    models = _models()
    artifact = _artifact(
        models,
        {"tier": "daily_diagnostics", "timestamp_field": "generated_at"},
    )
    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            mtime=datetime(2026, 7, 2, 9, 45, tzinfo=NY),
            embedded_timestamp_value="2026-07-02T10:05:00-04:00",
        ),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    assert report.status == "corrupt_or_empty"
    assert report.basis == "future_timestamp:embedded_timestamp"
    assert report.observed_at == "2026-07-02T10:05:00-04:00"
    assert report.age_seconds == -300


def test_dormant_ok_offseason_missing_artifact_reports_dormant_not_missing() -> None:
    models = _models()
    artifact = _artifact(
        models,
        {
            "artifact_id": "realized_outcome",
            "cadence": "weekly",
            "tier": "auxiliary",
            "dormant_ok": True,
            "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        },
    )
    report = _evaluate(
        models,
        artifact,
        _fact(models, exists=False, size_bytes=None, mtime=None),
        now=datetime(2026, 7, 7, 10, 0, tzinfo=NY),
    )

    assert report.status == "dormant"
    assert "dormant_ok_offseason" in report.basis
    assert report.observed_at is None
    assert report.age_seconds is None


def test_missing_non_dormant_artifact_degrades_by_tier() -> None:
    models = _models()
    artifact = _artifact(models, {"tier": "daily_diagnostics", "dormant_ok": False})
    report = _evaluate(
        models,
        artifact,
        _fact(models, exists=False, size_bytes=None, mtime=None),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )
    overall_status, worst_tier = models.rollup_health_status(reports=[report])

    assert report.status == "missing"
    assert overall_status == "degraded"
    assert worst_tier == "daily_diagnostics"


def test_auxiliary_stale_report_is_quiet_info_and_does_not_degrade_root() -> None:
    models = _models()
    artifact = _artifact(
        models,
        {
            "artifact_id": "league_opportunity",
            "tier": "auxiliary",
            "scheduled_time_local": "09:30",
        },
    )
    report = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 7, 1, 9, 35, tzinfo=NY)),
        now=datetime(2026, 7, 2, 12, 31, tzinfo=NY),
    )
    overall_status, worst_tier = models.rollup_health_status(reports=[report])

    assert report.status == "stale"
    assert "auxiliary_info_only" in report.disclosures
    assert overall_status == "ok"
    assert worst_tier is None


def test_weekly_cadence_uses_seven_day_window_before_staling() -> None:
    models = _models()
    artifact = _artifact(
        models,
        {
            "artifact_id": "weekly_report",
            "cadence": "weekly",
            "tier": "daily_diagnostics",
            "scheduled_time_local": "10:00",
        },
    )

    recent = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 7, 1, 10, 5, tzinfo=NY)),
        now=datetime(2026, 7, 7, 10, 30, tzinfo=NY),
    )
    stale = _evaluate(
        models,
        artifact,
        _fact(models, mtime=datetime(2026, 6, 29, 10, 5, tzinfo=NY)),
        now=datetime(2026, 7, 7, 13, 1, tzinfo=NY),
    )

    assert recent.status == "fresh"
    assert stale.status == "stale"


def test_evaluator_rejects_naive_now_fail_loud() -> None:
    models = _models()
    artifact = _artifact(models)

    with pytest.raises(ValueError, match="timezone-aware"):
        models.evaluate_report_freshness(
            config=_config(models, [artifact]),
            artifact_facts={artifact.artifact_id: _fact(models)},
            now=datetime(2026, 7, 2, 10, 0),
        )


def test_rollup_chooses_most_severe_affected_tier_across_reports() -> None:
    models = _models()
    core_report = models.ReportHealth.model_validate(
        {
            "artifact_id": "core",
            "status": "stale",
            "tier": "core_substrate",
            "basis": "past_grace",
            "artifact_path": "app/data/core.json",
            "producer": "scripts/core.py",
            "observed_at": "2026-07-01T09:35:00-04:00",
            "age_seconds": 97_000,
            "disclosures": [],
            "decision_supported": False,
        }
    )
    daily_report = core_report.model_copy(
        update={"artifact_id": "daily", "tier": "daily_diagnostics"}
    )
    auxiliary_report = core_report.model_copy(
        update={
            "artifact_id": "aux",
            "tier": "auxiliary",
            "disclosures": ["auxiliary_info_only"],
        }
    )

    overall_status, worst_tier = models.rollup_health_status(
        reports=[auxiliary_report, daily_report, core_report]
    )

    assert overall_status == "degraded"
    assert worst_tier == "core_substrate"
