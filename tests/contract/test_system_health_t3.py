"""DEBT-6 Slice 1c T3 RED: /api/health adapters, artifact reader, and route.

Temp configs, temp report files, injected subsystem adapters, and injected
clocks only. These tests do not read the real ``app/config/report_freshness.json``,
do not depend on real report artifacts, and do not assert T4 OpenAPI/codegen.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

NY = ZoneInfo("America/New_York")

BANNED_RESPONSE_RE = re.compile(
    r"\b(gate_4_ready|gate4|trusted|safe|recommended|buy|sell|hold|start|sit)\b",
    re.IGNORECASE,
)

EXPECTED_DISCLAIMER = (
    "System health reflects pipeline completion, artifact freshness, and model "
    "provenance verification. It does not evaluate model accuracy or guarantee "
    "trade edge."
)


def _models():
    import app.api.routes.system_health_models as models

    return models


def _route_module():
    from app.api.routes import system_health

    return system_health


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _write_text(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _set_mtime(path: Path, when: datetime) -> None:
    ts = when.timestamp()
    path.touch()
    path.chmod(0o644)
    path.stat()
    path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path_stat_time = when.timestamp()
    import os

    os.utime(path, (ts, path_stat_time))


def _artifact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "artifact_id": "pvo_refresh",
        "path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "cadence": "daily",
        "scheduled_time_local": "09:30",
        "grace_hours": 3,
        "tier": "core_substrate",
        "min_size_bytes": 16,
        "timestamp_field": None,
        "dormant_ok": False,
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
    }
    if overrides:
        body.update(overrides)
    return body


def _config_body(artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "artifacts": artifacts if artifacts is not None else [_artifact()],
    }


def _client_with_temp_config(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config_path: Path,
    repo_root: Path,
    now: datetime | None = None,
    model_provenance_status: str | Exception = "ok",
    capture_health_status: str | Exception = "ok",
    tier_readiness_status: str | Exception = "ok",
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(
        route,
        "_CLOCK",
        lambda: now
        if now is not None
        else datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    def _adapter(result: str | Exception):
        def _call() -> str:
            if isinstance(result, Exception):
                raise result
            return result

        return _call

    monkeypatch.setattr(
        route, "_MODEL_PROVENANCE_ADAPTER", _adapter(model_provenance_status)
    )
    monkeypatch.setattr(
        route, "_CAPTURE_HEALTH_ADAPTER", _adapter(capture_health_status)
    )
    monkeypatch.setattr(
        route, "_TIER_READINESS_ADAPTER", _adapter(tier_readiness_status)
    )
    from app.main import app

    return TestClient(app)


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _assert_no_banned_response_language(value: Any) -> None:
    flattened = json.dumps(value, sort_keys=True)
    assert not BANNED_RESPONSE_RE.search(flattened)


def _subsystem_by_id(body: dict[str, Any], subsystem_id: str) -> dict[str, Any]:
    for subsystem in body["subsystems"]:
        if subsystem["subsystem_id"] == subsystem_id:
            return subsystem
    raise AssertionError(f"missing subsystem_id {subsystem_id}")


def _report_by_id(body: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    for report in body["reports"]:
        if report["artifact_id"] == artifact_id:
            return report
    raise AssertionError(f"missing artifact_id {artifact_id}")


def test_health_route_reports_ok_for_green_subsystems_and_fresh_temp_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact()
    report_path = _write_json(
        tmp_path / artifact["path"],
        {"rows": [{"player_key": "p1"}]},
    )
    _set_mtime(report_path, datetime(2026, 7, 2, 9, 45, tzinfo=NY))
    config_path = _write_json(tmp_path / "report_freshness.json", _config_body([artifact]))
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        now=datetime(2026, 7, 2, 10, 0, tzinfo=NY),
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "ok"
    assert body["worst_affected_tier"] is None
    assert body["checked_at"] == "2026-07-02T10:00:00-04:00"
    assert body["config_version"] == 1
    assert body["disclaimer"] == EXPECTED_DISCLAIMER
    assert body["decision_supported"] is False
    _assert_decision_supported_false_recursive(body)
    _assert_no_banned_response_language(body)
    assert {
        subsystem["subsystem_id"]: subsystem["status"]
        for subsystem in body["subsystems"]
    } == {
        "model_provenance": "ok",
        "capture_health": "ok",
        "tier_readiness": "ok",
    }
    report = _report_by_id(body, "pvo_refresh")
    assert report["status"] == "fresh"
    assert report["basis"] == "mtime_fresh"
    assert report["disclosures"] == ["timestamp_source:mtime_fallback"]


def test_health_route_guard_of_guards_adapter_exception_is_200_degraded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact()
    report_path = _write_json(
        tmp_path / artifact["path"], {"ok": True, "padding": "over-floor"}
    )
    _set_mtime(report_path, datetime(2026, 7, 2, 9, 45, tzinfo=NY))
    config_path = _write_json(tmp_path / "report_freshness.json", _config_body([artifact]))
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        model_provenance_status=RuntimeError("boom absolute /tmp/leak"),
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["worst_affected_tier"] == "core_substrate"
    subsystem = _subsystem_by_id(body, "model_provenance")
    assert subsystem["status"] == "unavailable"
    assert subsystem["tier"] == "core_substrate"
    assert subsystem["basis"] == "adapter_status:unavailable"
    assert "boom" not in json.dumps(body)
    assert "/tmp/leak" not in json.dumps(body)


def test_tier_readiness_degradation_maps_to_daily_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact()
    report_path = _write_json(
        tmp_path / artifact["path"], {"ok": True, "padding": "over-floor"}
    )
    _set_mtime(report_path, datetime(2026, 7, 2, 9, 45, tzinfo=NY))
    config_path = _write_json(tmp_path / "report_freshness.json", _config_body([artifact]))
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        tier_readiness_status="degraded",
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["worst_affected_tier"] == "daily_diagnostics"
    subsystem = _subsystem_by_id(body, "tier_readiness")
    assert subsystem["status"] == "degraded"
    assert subsystem["tier"] == "daily_diagnostics"
    assert subsystem["basis"] == "adapter_status:degraded"


def test_report_rollup_and_subsystems_choose_most_severe_tier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_artifact = _artifact({"tier": "core_substrate"})
    report_path = _write_json(
        tmp_path / core_artifact["path"], {"ok": True, "padding": "over-floor"}
    )
    _set_mtime(report_path, datetime(2026, 7, 1, 9, 35, tzinfo=NY))
    config_path = _write_json(
        tmp_path / "report_freshness.json", _config_body([core_artifact])
    )
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        tier_readiness_status="degraded",
        now=datetime(2026, 7, 2, 12, 31, tzinfo=NY),
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["worst_affected_tier"] == "core_substrate"
    assert _report_by_id(body, "pvo_refresh")["status"] == "stale"


def test_auxiliary_report_degradation_is_quiet_info_at_route_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact(
        {
            "artifact_id": "league_opportunity",
            "tier": "auxiliary",
            "path": "app/data/valuation/league_opportunity_latest.json",
            "producer": "scripts/build_league_opportunity_map.py",
        }
    )
    report_path = _write_json(
        tmp_path / artifact["path"], {"ok": True, "padding": "over-floor"}
    )
    _set_mtime(report_path, datetime(2026, 7, 1, 9, 35, tzinfo=NY))
    config_path = _write_json(tmp_path / "report_freshness.json", _config_body([artifact]))
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        now=datetime(2026, 7, 2, 12, 31, tzinfo=NY),
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "ok"
    assert body["worst_affected_tier"] is None
    report = _report_by_id(body, "league_opportunity")
    assert report["status"] == "stale"
    assert "auxiliary_info_only" in report["disclosures"]


def test_health_config_failure_returns_sanitized_fixed_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_config = tmp_path / "does-not-exist.json"
    client = _client_with_temp_config(
        monkeypatch,
        config_path=missing_config,
        repo_root=tmp_path,
    )

    response = client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body == {
        "error": "system_health_unavailable",
        "message": "system health configuration unavailable",
        "decision_supported": False,
    }
    assert str(missing_config) not in json.dumps(body)
    assert "Traceback" not in json.dumps(body)


def test_artifact_reader_extracts_only_declared_embedded_timestamp(
    tmp_path: Path,
) -> None:
    models = _models()
    declared = _artifact(
        {
            "artifact_id": "what_changed",
            "path": "app/data/what_changed/what_changed_latest_report.json",
            "timestamp_field": "generated_at",
            "tier": "daily_diagnostics",
        }
    )
    undeclared = _artifact(
        {
            "artifact_id": "pvo_refresh",
            "path": "app/data/model_capture/pvo_refresh_latest_report.json",
            "timestamp_field": None,
        }
    )
    declared_path = _write_json(
        tmp_path / declared["path"],
        {"generated_at": "2026-07-02T09:45:00-04:00"},
    )
    _set_mtime(declared_path, datetime(2026, 7, 1, 9, 0, tzinfo=NY))
    undeclared_path = _write_text(
        tmp_path / undeclared["path"], "{not-json-but-over-floor"
    )
    _set_mtime(undeclared_path, datetime(2026, 7, 2, 9, 40, tzinfo=NY))
    config = models.ReportFreshnessConfig.model_validate(
        _config_body([declared, undeclared])
    )

    facts = models.read_report_artifact_facts(config=config, repo_root=tmp_path)

    assert facts["what_changed"].exists is True
    assert facts["what_changed"].size_bytes == declared_path.stat().st_size
    assert facts["what_changed"].mtime is not None
    assert facts["what_changed"].embedded_timestamp_value == "2026-07-02T09:45:00-04:00"
    assert facts["pvo_refresh"].exists is True
    assert facts["pvo_refresh"].embedded_timestamp_value is None


def test_unparseable_declared_json_degrades_report_not_the_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact(
        {
            "artifact_id": "what_changed",
            "path": "app/data/what_changed/what_changed_latest_report.json",
            "timestamp_field": "generated_at",
            "tier": "daily_diagnostics",
        }
    )
    report_path = _write_text(
        tmp_path / artifact["path"], "{not-json-but-over-floor"
    )
    _set_mtime(report_path, datetime(2026, 7, 2, 9, 45, tzinfo=NY))
    config_path = _write_json(tmp_path / "report_freshness.json", _config_body([artifact]))
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["worst_affected_tier"] == "daily_diagnostics"
    report = _report_by_id(body, "what_changed")
    assert report["status"] == "corrupt_or_empty"
    assert report["basis"] == "malformed_embedded_timestamp:generated_at"
    assert "timestamp_source:mtime_fallback" not in report["disclosures"]


def test_artifact_reader_refuses_to_resolve_outside_repo_root(tmp_path: Path) -> None:
    models = _models()
    artifact = _artifact({"path": "../outside.json"})
    config = models.ReportFreshnessConfig.model_validate(_config_body([artifact]))

    with pytest.raises(models.HealthConfigError):
        models.read_report_artifact_facts(config=config, repo_root=tmp_path)
