"""DEBT-6 Slice 1c T1 RED: health config loader and response models.

These tests use temp report-freshness configs only. T1 covers strict Pydantic
models and the fail-closed config loader; freshness evaluation, artifact
reading, adapters, route wiring, real config, and OpenAPI belong to later tasks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

DISCLAIMER = (
    "System health reflects pipeline completion, artifact freshness, and model "
    "provenance verification. It does not evaluate model accuracy or guarantee "
    "trade edge."
)
BANNED_NAME_TOKENS = (
    "certified",
    "validated",
    "trusted",
    "approved",
    "safe",
    "recommended",
    "buy",
    "sell",
    "hold",
    "start",
    "sit",
)


def _models():
    import app.api.routes.system_health_models as models

    return models


def _artifact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = {
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
        artifact.update(overrides)
    return artifact


def _weekly_artifact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = _artifact(
        {
            "artifact_id": "realized_outcome",
            "path": "app/data/realized_outcome/realized_outcome_scorecard_latest.json",
            "producer": "scripts/run_realized_outcome_scoring.py",
            "cadence": "weekly",
            "scheduled_time_local": "10:00",
            "tier": "auxiliary",
            "timestamp_field": None,
            "dormant_ok": True,
        }
    )
    if overrides:
        artifact.update(overrides)
    return artifact


def _config_body(artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "artifacts": artifacts if artifacts is not None else [_artifact()],
    }


def _write_config(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_loader_reads_injected_temp_report_freshness_config(tmp_path: Path) -> None:
    models = _models()
    config_path = _write_config(
        tmp_path / "report_freshness.json",
        _config_body([_artifact(), _weekly_artifact()]),
    )
    config = models.load_report_freshness(config_path=config_path)

    assert isinstance(config, models.ReportFreshnessConfig)
    assert config.config_version == 1
    assert config.timezone == "America/New_York"
    assert len(config.artifacts) == 2
    first = config.artifacts[0]
    assert first.artifact_id == "pvo_refresh"
    assert first.cadence == "daily"
    assert first.scheduled_time_local == "09:30"
    assert first.grace_hours == 3
    assert first.tier == "core_substrate"
    assert first.min_size_bytes == 128
    assert first.timestamp_field is None
    assert first.dormant_ok is False
    assert first.season_windows.in_season_months == [9, 10, 11, 12, 1]
    second = config.artifacts[1]
    assert second.cadence == "weekly"
    assert second.dormant_ok is True


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (
            lambda path: path.write_text(
                json.dumps(_config_body([_artifact({"cadence": "manual"})])),
                encoding="utf-8",
            ),
            "schema",
        ),
        (
            lambda path: path.write_text(json.dumps(_config_body([])), encoding="utf-8"),
            "empty",
        ),
        (
            lambda path: path.write_text(
                json.dumps(
                    _config_body(
                        [
                            _artifact({"artifact_id": "duplicate"}),
                            _weekly_artifact({"artifact_id": "duplicate"}),
                        ]
                    )
                ),
                encoding="utf-8",
            ),
            "duplicate",
        ),
        (
            lambda path: path.write_text(
                json.dumps(_config_body([_artifact({"tier": "critical"})])),
                encoding="utf-8",
            ),
            "schema",
        ),
    ],
)
def test_loader_raises_typed_error_for_config_family_failures(
    tmp_path: Path,
    writer,
    message_fragment: str,
) -> None:
    models = _models()
    config_path = tmp_path / "report_freshness.json"
    writer(config_path)

    with pytest.raises(models.HealthConfigError) as exc_info:
        models.load_report_freshness(config_path=config_path)

    assert message_fragment in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "artifact_overrides",
    [
        {"path": "/tmp/report.json"},
        {"path": "app/data/../secret/report.json"},
        {"path": r"app\data\model_capture\report.json"},
        {"producer": "/tmp/run_report.py"},
        {"producer": "../scripts/run_report.py"},
        {"producer": r"scripts\run_report.py"},
    ],
)
def test_loader_rejects_paths_that_escape_or_use_backslashes(
    tmp_path: Path,
    artifact_overrides: dict[str, Any],
) -> None:
    models = _models()
    config_path = _write_config(
        tmp_path / "report_freshness.json",
        _config_body([_artifact(artifact_overrides)]),
    )

    with pytest.raises(models.HealthConfigError) as exc_info:
        models.load_report_freshness(config_path=config_path)

    assert "path" in str(exc_info.value).lower() or "producer" in str(
        exc_info.value
    ).lower()


def test_config_models_forbid_extra_fields_and_strict_type_coercion() -> None:
    models = _models()
    body = _config_body()

    with pytest.raises(ValidationError):
        models.ReportFreshnessConfig.model_validate(body | {"gate_4_ready": True})
    with pytest.raises(ValidationError):
        models.ReportArtifactConfig.model_validate(
            _artifact({"gate_4_ready": True})
        )
    with pytest.raises(ValidationError):
        models.ReportArtifactConfig.model_validate(_artifact({"grace_hours": "3"}))
    with pytest.raises(ValidationError):
        models.ReportArtifactConfig.model_validate(_artifact({"dormant_ok": "false"}))
    with pytest.raises(ValidationError):
        models.ReportArtifactConfig.model_validate(
            _artifact({"season_windows": {"in_season_months": ["9"]}})
        )


def test_response_models_lock_disclaimer_enums_recursive_false_and_extra_forbid() -> None:
    models = _models()
    report = {
        "artifact_id": "pvo_refresh",
        "status": "fresh",
        "tier": "core_substrate",
        "basis": "embedded_timestamp_fresh",
        "artifact_path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "observed_at": "2026-07-02T09:31:00-04:00",
        "age_seconds": 120,
        "disclosures": ["timestamp_source:mtime_fallback"],
        "decision_supported": False,
    }
    subsystem = {
        "subsystem_id": "model_provenance",
        "status": "ok",
        "basis": "overall_status:ok",
        "tier": "core_substrate",
        "decision_supported": False,
    }
    response = models.SystemHealthResponse.model_validate(
        {
            "overall_status": "ok",
            "worst_affected_tier": None,
            "checked_at": "2026-07-02T13:00:00-04:00",
            "config_version": 1,
            "subsystems": [subsystem],
            "reports": [report],
            "disclaimer": DISCLAIMER,
            "decision_supported": False,
        }
    )
    error = models.SystemHealthErrorResponse.model_validate(
        {
            "error": "health_config_unavailable",
            "message": "health configuration unavailable",
            "decision_supported": False,
        }
    )

    assert response.disclaimer == DISCLAIMER
    assert response.reports[0].decision_supported is False
    assert error.decision_supported is False
    _assert_decision_supported_false_recursive(response.model_dump())

    with pytest.raises(ValidationError):
        models.SystemHealthResponse.model_validate(
            response.model_dump() | {"decision_supported": True}
        )
    with pytest.raises(ValidationError):
        models.SystemHealthResponse.model_validate(
            response.model_dump() | {"recommendation": "trust this"}
        )
    with pytest.raises(ValidationError):
        models.ReportHealth.model_validate(report | {"status": "blocked"})


def test_disclaimer_exact_copy_is_required() -> None:
    models = _models()

    with pytest.raises(ValidationError):
        models.SystemHealthResponse.model_validate(
            {
                "overall_status": "ok",
                "worst_affected_tier": None,
                "checked_at": "2026-07-02T13:00:00-04:00",
                "config_version": 1,
                "subsystems": [],
                "reports": [],
                "disclaimer": "System health is safe.",
                "decision_supported": False,
            }
        )


def test_model_field_and_enum_names_do_not_use_banned_vocabulary() -> None:
    models = _models()
    names: set[str] = set()
    model_types = [
        models.SeasonWindows,
        models.ReportArtifactConfig,
        models.ReportFreshnessConfig,
        models.SubsystemHealth,
        models.ReportHealth,
        models.SystemHealthResponse,
        models.SystemHealthErrorResponse,
    ]
    for model_type in model_types:
        names.update(model_type.model_fields)
    for literal_type in (
        models.HealthOverallStatus,
        models.HealthTier,
        models.ReportCadence,
        models.ReportFreshnessStatus,
        models.SubsystemStatus,
    ):
        names.update(str(value) for value in get_args(literal_type))

    lowered = {name.lower() for name in names}
    for banned in BANNED_NAME_TOKENS:
        assert all(banned not in name for name in lowered), banned


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)
