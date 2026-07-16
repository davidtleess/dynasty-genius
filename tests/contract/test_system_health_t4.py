"""DEBT-6 Slice 1c T4 RED: real report-freshness config + OpenAPI snapshot.

This is the one health-rollup test that intentionally reads the real checked-in
``app/config/report_freshness.json``. It validates config shape and producer
existence only; it never asserts live freshness, never requires gitignored
report artifacts to exist, and never reads report payloads from ``app/data``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.system_health_models import load_report_freshness

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "app" / "config" / "report_freshness.json"
FRONTEND_OPENAPI_PATH = REPO_ROOT / "frontend" / "openapi.json"


EXPECTED_ARTIFACTS: dict[str, dict[str, Any]] = {
    # league_capture registered 2026-07-15 (F1 spec) — intentional pin amendment
    "league_capture": {
        "path": "app/data/league_runtime/capture_status_latest.json",
        "producer": "scripts/run_league_snapshot_capture.py",
        "cadence": "daily",
        "scheduled_time_local": "09:20",
        "tier": "core_substrate",
        "timestamp_field": "finished_at",
        "dormant_ok": False,
    },
    "pvo_refresh": {
        "path": "app/data/model_capture/pvo_refresh_latest_report.json",
        "producer": "scripts/run_pvo_refresh.py",
        "cadence": "daily",
        "scheduled_time_local": "09:30",
        "tier": "core_substrate",
        "timestamp_field": None,
        "dormant_ok": False,
    },
    "feature_refresh": {
        "path": "app/data/features_runtime/feature_refresh_latest_report.json",
        "producer": "scripts/run_feature_refresh.py",
        "cadence": "weekly",
        "scheduled_time_local": "09:15",
        "tier": "daily_diagnostics",
        "timestamp_field": "generated_at",
        "dormant_ok": True,
    },
    "what_changed": {
        "path": "app/data/what_changed/what_changed_latest_report.json",
        "producer": "scripts/run_what_changed_report.py",
        "cadence": "daily",
        "scheduled_time_local": "09:45",
        "tier": "daily_diagnostics",
        "timestamp_field": "generated_at",
        "dormant_ok": False,
    },
    "roster_capacity": {
        "path": "app/data/roster_capacity/roster_capacity_latest.json",
        "producer": "scripts/run_roster_capacity_audit.py",
        "cadence": "weekly",
        "scheduled_time_local": "10:00",
        "grace_hours": 3,
        "tier": "daily_diagnostics",
        "min_size_bytes": 64,
        "timestamp_field": "created_at",
        "dormant_ok": False,
    },
    "league_opportunity": {
        "path": "app/data/valuation/league_opportunity_latest.json",
        "producer": "scripts/build_league_opportunity_map.py",
        "cadence": "weekly",
        "scheduled_time_local": "09:35",
        "grace_hours": 3,
        "tier": "auxiliary",
        "min_size_bytes": 64,
        "timestamp_field": "captured_at",
        "dormant_ok": False,
    },
    "realized_outcome": {
        # AMENDED (2026-07-11, cockpit-converged shape ii): registration upgraded
        # from the mtime-only scorecard pin (never produced; fresh-mtime failure
        # indistinguishable from success) to the terminal status marker shipped
        # with PR #147. ok AND noop are healthy terminal states; failed carries
        # failure_reason.
        "path": "app/data/valuation_runtime/realized_outcome_scoring_status_latest.json",
        "producer": "scripts/run_realized_outcome_scoring.py",
        "cadence": "weekly",
        "scheduled_time_local": "10:00",
        "tier": "auxiliary",
        "timestamp_field": "finished_at",
        "status_field": "status",
        "success_status": ["ok", "noop"],
        "failure_reason_field": "failure_reason",
        "dormant_ok": True,
    },
    "market_divergence": {
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
    },
}


def test_real_report_freshness_config_loads_and_pins_the_seven_report_artifacts() -> None:
    config = load_report_freshness(config_path=CONFIG_PATH)

    assert config.config_version == 2
    assert config.timezone == "America/New_York"
    artifacts = {artifact.artifact_id: artifact for artifact in config.artifacts}
    assert artifacts.keys() == EXPECTED_ARTIFACTS.keys()

    for artifact_id, expected in EXPECTED_ARTIFACTS.items():
        artifact = artifacts[artifact_id]
        for field, expected_value in expected.items():
            assert getattr(artifact, field) == expected_value, artifact_id
        assert artifact.min_size_bytes > 0
        assert artifact.grace_hours >= 0
        assert artifact.season_windows.in_season_months
        assert (REPO_ROOT / artifact.producer).is_file(), artifact.producer


def test_health_route_openapi_exposes_200_and_503_schema_refs() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/health"]["get"]

    assert operation["tags"] == ["system"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("SystemHealthResponse")
    assert operation["responses"]["503"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("SystemHealthErrorResponse")


def test_committed_frontend_openapi_snapshot_includes_health_route_schema_refs() -> None:
    schema = json.loads(FRONTEND_OPENAPI_PATH.read_text(encoding="utf-8"))
    operation = schema["paths"]["/api/health"]["get"]

    assert operation["tags"] == ["system"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("SystemHealthResponse")
    assert operation["responses"]["503"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("SystemHealthErrorResponse")
