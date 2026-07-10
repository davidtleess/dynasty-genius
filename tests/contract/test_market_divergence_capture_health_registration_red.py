"""Phase-0b RED: market-divergence status marker joins report freshness.

The marker path is gitignored, so these tests use constructed facts and temp
files only. They never assert the live ``/api/health`` route state.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

NY = ZoneInfo("America/New_York")


def _models():
    import app.api.routes.system_health_models as models

    return models


def _marker_artifact_body(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "artifact_id": "market_divergence",
        "path": "app/data/valuation_runtime/market_divergence_refresh_status_latest.json",
        "producer": "scripts/run_market_divergence_refresh.py",
        "cadence": "daily",
        "scheduled_time_local": "09:40",
        "grace_hours": 3,
        "tier": "core_substrate",
        "min_size_bytes": 64,
        "timestamp_field": "finished_at",
        "status_field": "status",
        "success_status": "ok",
        "failure_reason_field": "reason",
        "dormant_ok": False,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    if overrides:
        body.update(overrides)
    return body


def _legacy_artifact_body(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "artifact_id": "pvo_refresh",
        "path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "cadence": "daily",
        "scheduled_time_local": "09:30",
        "grace_hours": 3,
        "tier": "core_substrate",
        "min_size_bytes": 64,
        "timestamp_field": None,
        "dormant_ok": False,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    if overrides:
        body.update(overrides)
    return body


def _artifact(models, body: dict[str, Any] | None = None):
    return models.ReportArtifactConfig.model_validate(body or _marker_artifact_body())


def _config(models, artifacts, *, config_version: int = 2):
    return models.ReportFreshnessConfig.model_validate(
        {
            "config_version": config_version,
            "timezone": "America/New_York",
            "artifacts": artifacts,
        }
    )


def _fact(models, **overrides):
    body = {
        "exists": True,
        "size_bytes": 256,
        "mtime": datetime(2026, 7, 9, 9, 45, tzinfo=NY),
        "embedded_timestamp_value": "2026-07-09T09:45:00-04:00",
        "status_value": "ok",
        "failure_reason": None,
    }
    body.update(overrides)
    return models.ReportArtifactFact.model_validate(body)


def _evaluate(models, artifact, fact, now: datetime):
    reports = models.evaluate_report_freshness(
        config=_config(models, [artifact]),
        artifact_facts={artifact.artifact_id: fact},
        now=now,
    )
    assert len(reports) == 1
    return reports[0]


def test_status_gate_precedes_freshness_for_failed_market_divergence_marker() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="degraded",
            failure_reason="market_source_prior_date",
            embedded_timestamp_value="2026-07-09T09:45:00-04:00",
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:market_source_prior_date"
    assert "timestamp_source:mtime_fallback" not in report.disclosures


def test_successful_market_divergence_marker_uses_finished_at_liveness_clock() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, embedded_timestamp_value="2026-07-09T09:45:00-04:00"),
        now=datetime(2026, 7, 9, 22, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.basis == "embedded_timestamp_fresh"
    assert report.observed_at == "2026-07-09T09:45:00-04:00"


def test_successful_market_divergence_marker_past_grace_goes_stale() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, embedded_timestamp_value="2026-07-08T09:45:00-04:00"),
        now=datetime(2026, 7, 9, 13, 0, tzinfo=NY),
    )

    assert report.status == "stale"
    assert report.basis == "past_grace"


def test_missing_market_divergence_marker_degrades_as_missing() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, exists=False, size_bytes=None, mtime=None),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "missing"
    assert report.basis == "artifact_absent"


def test_status_marker_missing_status_fails_closed_before_clock_gate() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value=None,
            embedded_timestamp_value="2026-07-09T09:45:00-04:00",
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "corrupt_or_empty"
    assert report.basis == "malformed_status:status"


def test_status_marker_failure_outweighs_future_finished_at_corruption() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="degraded",
            failure_reason="market_source_prior_date",
            embedded_timestamp_value="2026-07-10T09:45:00-04:00",
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:market_source_prior_date"


def test_reader_opens_marker_json_for_status_field_and_rejects_non_string_status(
    tmp_path: Path,
) -> None:
    models = _models()
    artifact = _artifact(models)
    marker_path = tmp_path / artifact.path
    marker_path.parent.mkdir(parents=True)
    marker_path.write_text(
        json.dumps(
            {
                "status": 123,
                "finished_at": "2026-07-09T09:45:00-04:00",
                "reason": "market_source_prior_date",
            }
        ),
        encoding="utf-8",
    )
    config = _config(models, [artifact])

    facts = models.read_report_artifact_facts(config=config, repo_root=tmp_path)
    fact = facts["market_divergence"]
    report = _evaluate(
        models,
        artifact,
        fact,
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert fact.status_value is None
    assert report.status == "corrupt_or_empty"
    assert report.basis == "malformed_status:status"


def test_reader_opens_json_when_only_status_field_is_configured(tmp_path: Path) -> None:
    models = _models()
    artifact = _artifact(
        models,
        _marker_artifact_body({"timestamp_field": None, "min_size_bytes": 16}),
    )
    marker_path = tmp_path / artifact.path
    marker_path.parent.mkdir(parents=True)
    marker_path.write_text(
        json.dumps({"status": "degraded", "reason": "market_source_prior_date"}),
        encoding="utf-8",
    )
    config = _config(models, [artifact])

    facts = models.read_report_artifact_facts(config=config, repo_root=tmp_path)

    assert facts["market_divergence"].status_value == "degraded"
    assert facts["market_divergence"].failure_reason == "market_source_prior_date"


def test_status_config_rejects_success_status_without_status_field(
    tmp_path: Path,
) -> None:
    models = _models()
    body = _marker_artifact_body()
    body.pop("status_field")
    config_path = tmp_path / "report_freshness.json"
    config_path.write_text(
        json.dumps(
            {
                "config_version": 2,
                "timezone": "America/New_York",
                "artifacts": [body],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(models.HealthConfigError, match="status_field"):
        models.load_report_freshness(config_path=config_path)


@pytest.mark.parametrize("blank", ["", "   "])
@pytest.mark.parametrize(
    "field_name", ["status_field", "success_status", "failure_reason_field"]
)
def test_status_config_rejects_blank_value_bounds(
    tmp_path: Path, field_name: str, blank: str
) -> None:
    """Blank opt-in status fields must fail closed at load (Codex NOT-CLEAR).

    A blank ``success_status`` is the dangerous one: no producer ever writes the
    empty string, so every healthy run would report ``producer_failed`` forever.
    Lexical confinement alone does not catch it — empty identifiers pass.
    """
    models = _models()
    body = _marker_artifact_body({field_name: blank})
    config_path = tmp_path / "report_freshness.json"
    config_path.write_text(
        json.dumps(
            {
                "config_version": 2,
                "timezone": "America/New_York",
                "artifacts": [body],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(models.HealthConfigError, match=f"empty {field_name}"):
        models.load_report_freshness(config_path=config_path)


def test_optional_status_config_fields_default_none_for_legacy_artifacts() -> None:
    models = _models()

    artifact = _artifact(models, _legacy_artifact_body())

    assert artifact.status_field is None
    assert artifact.success_status is None
    assert artifact.failure_reason_field is None


def test_legacy_artifact_health_output_remains_byte_for_byte_equivalent() -> None:
    models = _models()
    artifact = _artifact(models, _legacy_artifact_body())
    report = _evaluate(
        models,
        artifact,
        models.ReportArtifactFact.model_validate(
            {
                "exists": True,
                "size_bytes": 256,
                "mtime": datetime(2026, 7, 9, 9, 45, tzinfo=NY),
                "embedded_timestamp_value": None,
            }
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.model_dump() == {
        "artifact_id": "pvo_refresh",
        "status": "fresh",
        "tier": "core_substrate",
        "basis": "mtime_fresh",
        "artifact_path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "observed_at": "2026-07-09T09:45:00-04:00",
        "age_seconds": 900,
        "disclosures": ["timestamp_source:mtime_fallback"],
        "decision_supported": False,
    }


def _report_health(models, *, status: str, tier: str):
    return models.ReportHealth.model_validate(
        {
            "artifact_id": f"{tier}_{status}",
            "status": status,
            "tier": tier,
            "basis": "producer_failure:market_source_prior_date",
            "artifact_path": "app/data/valuation_runtime/marker.json",
            "producer": "scripts/run_market_divergence_refresh.py",
            "observed_at": "2026-07-09T09:45:00-04:00",
            "age_seconds": 900,
            "disclosures": [],
            "decision_supported": False,
        }
    )


def test_producer_failed_core_substrate_degrades_rollup() -> None:
    models = _models()
    report = _report_health(models, status="producer_failed", tier="core_substrate")

    assert models.rollup_health_status(reports=[report]) == (
        "degraded",
        "core_substrate",
    )


def test_producer_failed_auxiliary_remains_info_only_at_root() -> None:
    models = _models()
    report = _report_health(models, status="producer_failed", tier="auxiliary")

    assert models.rollup_health_status(reports=[report]) == ("ok", None)
