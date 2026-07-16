"""RED: realized-outcome status marker joins report freshness.

The realized-outcome marker is gitignored, so these tests use constructed facts
and temp files. Only the config pin reads the checked-in report-freshness config;
no test depends on live ``app/data`` artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

NY = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "app" / "config" / "report_freshness.json"


def _models():
    import app.api.routes.system_health_models as models

    return models


def _marker_artifact_body(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "artifact_id": "realized_outcome",
        "path": "app/data/valuation_runtime/realized_outcome_scoring_status_latest.json",
        "producer": "scripts/run_realized_outcome_scoring.py",
        "cadence": "weekly",
        "scheduled_time_local": "10:00",
        "grace_hours": 3,
        "tier": "auxiliary",
        "min_size_bytes": 64,
        "timestamp_field": "finished_at",
        "status_field": "status",
        "success_status": ["ok", "noop"],
        "failure_reason_field": "failure_reason",
        "dormant_ok": True,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    if overrides:
        body.update(overrides)
    return body


def _write_config(
    tmp_path: Path, artifact_body: dict[str, Any], *, config_version: int = 2
) -> Path:
    config_path = tmp_path / "report_freshness.json"
    config_path.write_text(
        json.dumps(
            {
                "config_version": config_version,
                "timezone": "America/New_York",
                "artifacts": [artifact_body],
            }
        ),
        encoding="utf-8",
    )
    return config_path


def _artifact(models, overrides: dict[str, Any] | None = None):
    return models.ReportArtifactConfig.model_validate(_marker_artifact_body(overrides))


def _config(models, artifacts):
    return models.ReportFreshnessConfig.model_validate(
        {
            "config_version": 2,
            "timezone": "America/New_York",
            "artifacts": artifacts,
        }
    )


def _fact(models, **overrides):
    body = {
        "exists": True,
        "size_bytes": 256,
        "mtime": datetime(2026, 9, 15, 10, 5, tzinfo=NY),
        "embedded_timestamp_value": "2026-09-15T10:05:00-04:00",
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


def test_real_config_pins_realized_outcome_to_status_marker_with_two_successes() -> None:
    models = _models()

    config = models.load_report_freshness(config_path=CONFIG_PATH)
    artifacts = {artifact.artifact_id: artifact for artifact in config.artifacts}
    realized = artifacts["realized_outcome"]

    assert config.config_version == 2
    assert len(config.artifacts) == 8  # league_capture registered 2026-07-15 (F1 spec) — intentional pin amendment
    assert realized.path == (
        "app/data/valuation_runtime/realized_outcome_scoring_status_latest.json"
    )
    assert realized.producer == "scripts/run_realized_outcome_scoring.py"
    assert realized.cadence == "weekly"
    assert realized.scheduled_time_local == "10:00"
    assert realized.timestamp_field == "finished_at"
    assert realized.status_field == "status"
    assert realized.success_status == ["ok", "noop"]
    assert realized.failure_reason_field == "failure_reason"
    assert realized.dormant_ok is True


def test_status_config_accepts_string_or_list_success_status(tmp_path: Path) -> None:
    models = _models()

    list_config = models.load_report_freshness(
        config_path=_write_config(tmp_path, _marker_artifact_body())
    )
    scalar_config = models.load_report_freshness(
        config_path=_write_config(
            tmp_path,
            _marker_artifact_body(
                {
                    "artifact_id": "market_divergence",
                    "success_status": "ok",
                    "dormant_ok": False,
                }
            ),
            config_version=3,
        )
    )

    assert list_config.artifacts[0].success_status == ["ok", "noop"]
    assert scalar_config.artifacts[0].success_status == "ok"


@pytest.mark.parametrize(
    ("success_status", "message"),
    [
        ([], "success_status.*non-empty"),
        (["ok", ""], "empty success_status"),
        (["ok", "   "], "empty success_status"),
        (["ok", "noop", "ok"], "duplicate success_status"),
        (["ok", 123], "success_status.*string"),
    ],
)
def test_status_config_rejects_bad_success_status_lists(
    tmp_path: Path, success_status: Any, message: str
) -> None:
    models = _models()
    config_path = _write_config(
        tmp_path, _marker_artifact_body({"success_status": success_status})
    )

    with pytest.raises(models.HealthConfigError, match=message):
        models.load_report_freshness(config_path=config_path)


def test_fresh_ok_marker_is_fresh() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, status_value="ok"),
        now=datetime(2026, 9, 15, 12, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.basis == "embedded_timestamp_fresh"
    assert report.observed_at == "2026-09-15T10:05:00-04:00"


def test_fresh_noop_marker_is_fresh_not_producer_failed() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, status_value="noop"),
        now=datetime(2026, 9, 15, 12, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.basis == "embedded_timestamp_fresh"


def test_failed_marker_uses_failure_reason_field() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="failed",
            failure_reason="outcome_build_failed:OperationalError",
        ),
        now=datetime(2026, 9, 15, 12, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:outcome_build_failed:OperationalError"


def test_missing_offseason_marker_remains_dormant() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            exists=False,
            size_bytes=None,
            mtime=None,
            embedded_timestamp_value=None,
            status_value=None,
        ),
        now=datetime(2026, 7, 14, 10, 30, tzinfo=NY),
    )

    assert report.status == "dormant"
    assert report.basis == "dormant_ok_offseason"


def test_existing_offseason_noop_marker_beats_dormant_short_circuit() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="noop",
            embedded_timestamp_value="2026-07-14T10:05:00-04:00",
        ),
        now=datetime(2026, 7, 14, 10, 30, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert report.basis == "embedded_timestamp_fresh"
    assert report.observed_at == "2026-07-14T10:05:00-04:00"


def test_existing_offseason_failed_marker_beats_dormant_short_circuit() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="failed",
            failure_reason="predictions_load_failed:RuntimeError",
            embedded_timestamp_value="2026-07-14T10:05:00-04:00",
        ),
        now=datetime(2026, 7, 14, 10, 30, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:predictions_load_failed:RuntimeError"


def test_existing_offseason_stale_marker_beats_dormant_short_circuit() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="noop",
            embedded_timestamp_value="2026-07-14T10:05:00-04:00",
        ),
        now=datetime(2026, 7, 22, 13, 1, tzinfo=NY),
    )

    assert report.status == "stale"
    assert report.basis == "past_grace"
    assert report.observed_at == "2026-07-14T10:05:00-04:00"
    assert report.age_seconds is not None


def test_stale_weekly_marker_uses_weekly_window() -> None:
    models = _models()
    artifact = _artifact(models)

    report = _evaluate(
        models,
        artifact,
        _fact(models, embedded_timestamp_value="2026-09-15T10:05:00-04:00"),
        now=datetime(2026, 9, 22, 13, 1, tzinfo=NY),
    )

    assert report.status == "stale"
    assert report.basis == "past_grace"


def test_reader_extracts_realized_outcome_failure_reason(tmp_path: Path) -> None:
    models = _models()
    artifact = _artifact(models)
    marker_path = tmp_path / artifact.path
    marker_path.parent.mkdir(parents=True)
    marker_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "finished_at": "2026-09-15T10:05:00-04:00",
                "failure_reason": "scorecard_publish_failed:OSError",
            }
        ),
        encoding="utf-8",
    )
    config = _config(models, [artifact])

    facts = models.read_report_artifact_facts(config=config, repo_root=tmp_path)
    fact = facts["realized_outcome"]
    report = _evaluate(
        models,
        artifact,
        fact,
        now=datetime(2026, 9, 15, 12, 0, tzinfo=NY),
    )

    assert fact.status_value == "failed"
    assert fact.failure_reason == "scorecard_publish_failed:OSError"
    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:scorecard_publish_failed:OSError"


def test_system_health_openapi_report_status_enum_does_not_gain_noop_status() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    status_enum = schema["components"]["schemas"]["ReportHealth"]["properties"][
        "status"
    ]["enum"]

    assert "noop" not in status_enum
    assert "producer_failed" in status_enum
