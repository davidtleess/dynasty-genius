"""BUILD-3 increment 1 RED: the 26-hour backup law surfaces on capture-health.

Governance 02 §Standing Infrastructure ruling 3 ("Silence is not success")
binds NOW: backup-marker absence, or a marker older than 26 hours (one daily
interval plus a sleep/timezone grace), is a degraded state, and the automation
surfacing it was a named follow-up. This RED makes ``GET
/api/system/capture-health`` carry that law as a descriptive ``backup`` block:

- marker absent            -> 200 degraded, ``backup_marker_absent``
- marker unparseable       -> 200 degraded, ``backup_marker_unparseable`` (fail closed)
- ``finished_at`` naive/missing -> 200 degraded, ``backup_marker_unparseable``
- age(now, finished_at) > 26h  -> 200 degraded, ``backup_stale`` (strict >)
- ``status`` != completed  -> 200 degraded, ``backup_run_failed``
- ``sha256_verified`` != True -> 200 degraded, ``backup_unverified``
- fresh + completed + verified -> ok; ``failures`` list still echoed verbatim

Descriptive only: ``decision_supported=False`` recursively, no verdict
language, and the marker echo never includes the bucket path (``run_prefix``).
Tests monkeypatch the marker path via the route's ``_REPO_ROOT`` — they never
read the real gitignored ``app/data/ops`` marker (League Opportunity lesson).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

BANNED_RESPONSE_RE = re.compile(
    r"\b(gate_4_ready|gate4|trusted|safe|recommended|buy|sell|hold|start|sit)\b",
    re.IGNORECASE,
)

_NOW = datetime(2026, 7, 2, 13, 0, tzinfo=ZoneInfo("America/New_York"))
_MARKER_RELPATH = Path("app/data/ops/backup_status_latest.json")


def _route_module():
    from app.api.routes import system_capture_health

    return system_capture_health


def _client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config_path: Path,
    repo_root: Path,
    now: datetime = _NOW,
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(route, "_CLOCK", lambda: now)
    from app.main import app

    return TestClient(app)


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _config_body() -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": [
            {
                "store_id": "fc_forward_capture",
                "db_path": "app/data/fc_forward_capture.db",
                "table": "fc_forward_capture_raw",
                "date_column": "snapshot_date",
                "source_filter": "fc_native",
                "expected_settings_hash": "canonical_hash",
                "capture_start_date": "2026-06-30",
                "expected_cadence": "daily",
                "scheduled_time_local": "09:00",
                "grace_hours": 3,
                "density_floor_pct": 50,
                "density_baseline_window": 14,
                "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
                "window_risk_contiguous_days": 7,
                "companion_tables": [],
            }
        ],
    }


def _marker_body(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    finished = _NOW - timedelta(hours=1)
    body: dict[str, Any] = {
        "schema_version": "backup_status.v1",
        "run_id": "20260702T141500Z",
        "run_prefix": "gs://example-bucket/dynasty-genius/runs/20260702T141500Z",
        "status": "completed",
        "sha256_verified": True,
        "files": 559,
        "bytes": 2520054611,
        "failures": ["missing_optional:app/data/example.db"],
        "started_at": (finished - timedelta(minutes=39)).isoformat(),
        "finished_at": finished.isoformat(),
    }
    if overrides:
        body.update(overrides)
    return body


def _setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    marker: dict[str, Any] | None,
    marker_raw: str | None = None,
    now: datetime = _NOW,
) -> TestClient:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    marker_path = tmp_path / _MARKER_RELPATH
    if marker_raw is not None:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(marker_raw, encoding="utf-8")
    elif marker is not None:
        _write_json(marker_path, marker)
    return _client(monkeypatch, config_path=config_path, repo_root=tmp_path, now=now)


def _backup(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/system/capture-health")
    assert response.status_code == 200
    body = response.json()
    assert "backup" in body, "capture-health response must carry a backup block"
    return body["backup"]


# --- absence / unparseable (fail closed, never 503) ---------------------------


def test_absent_marker_is_first_class_degraded(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=None)
    backup = _backup(client)
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_marker_absent"]
    assert backup["marker_present"] is False
    assert backup["marker"] is None


def test_unparseable_marker_fails_closed_degraded(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=None, marker_raw="{not json")
    backup = _backup(client)
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_marker_unparseable"]
    assert backup["marker_present"] is True
    assert backup["marker"] is None


def test_non_object_marker_fails_closed_degraded(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=None, marker_raw='["not", "a", "dict"]')
    backup = _backup(client)
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_marker_unparseable"]
    assert backup["marker"] is None


def test_missing_finished_at_is_unparseable(tmp_path, monkeypatch):
    marker = _marker_body()
    del marker["finished_at"]
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert "backup_marker_unparseable" in backup["reasons"]


def test_naive_finished_at_is_unparseable(tmp_path, monkeypatch):
    marker = _marker_body({"finished_at": "2026-07-02T11:00:00"})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert "backup_marker_unparseable" in backup["reasons"]


# --- the 26-hour law ----------------------------------------------------------


def test_fresh_verified_marker_is_ok(tmp_path, monkeypatch):
    backup = _backup(_setup(tmp_path, monkeypatch, marker=_marker_body()))
    assert backup["status"] == "ok"
    assert backup["reasons"] == []
    assert backup["marker_present"] is True
    assert backup["threshold_hours"] == 26
    marker = backup["marker"]
    assert marker["run_id"] == "20260702T141500Z"
    assert marker["status"] == "completed"
    assert marker["sha256_verified"] is True
    assert marker["files"] == 559
    assert marker["failures"] == ["missing_optional:app/data/example.db"]
    assert "run_prefix" not in marker, "bucket paths are never echoed"


def test_marker_older_than_26h_is_stale(tmp_path, monkeypatch):
    finished = _NOW - timedelta(hours=26, minutes=1)
    marker = _marker_body({"finished_at": finished.isoformat()})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_stale"]


def test_marker_at_exactly_26h_is_not_stale(tmp_path, monkeypatch):
    finished = _NOW - timedelta(hours=26)
    marker = _marker_body({"finished_at": finished.isoformat()})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "ok"
    assert backup["reasons"] == []


# --- terminal-state honesty ---------------------------------------------------


def test_failed_run_status_degrades(tmp_path, monkeypatch):
    marker = _marker_body({"status": "failed"})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_run_failed"]


def test_unverified_completed_run_degrades(tmp_path, monkeypatch):
    marker = _marker_body({"sha256_verified": False})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert backup["reasons"] == ["backup_unverified"]


def test_stale_and_failed_reasons_stack(tmp_path, monkeypatch):
    finished = _NOW - timedelta(hours=30)
    marker = _marker_body({"finished_at": finished.isoformat(), "status": "failed"})
    backup = _backup(_setup(tmp_path, monkeypatch, marker=marker))
    assert backup["status"] == "degraded"
    assert set(backup["reasons"]) == {"backup_stale", "backup_run_failed"}


# --- rollup + honesty discipline ---------------------------------------------


def test_degraded_backup_folds_into_overall_status(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=None)
    body = client.get("/api/system/capture-health").json()
    assert body["backup"]["status"] == "degraded"
    assert body["overall_status"] == "degraded"


def test_ok_backup_leaves_overall_to_stores(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=_marker_body())
    body = client.get("/api/system/capture-health").json()
    assert body["backup"]["status"] == "ok"
    # the single configured store is absent in the temp root -> store-degraded;
    # overall reflects the stores, proving backup-ok never masks store state.
    assert body["overall_status"] == "degraded"


def test_backup_block_is_descriptive_only(tmp_path, monkeypatch):
    for marker in (None, _marker_body(), _marker_body({"status": "failed"})):
        client = _setup(tmp_path, monkeypatch, marker=marker)
        body = client.get("/api/system/capture-health").json()
        assert "backup" in body

        def _recurse(value: Any) -> None:
            if isinstance(value, dict):
                if "decision_supported" in value:
                    assert value["decision_supported"] is False
                for nested in value.values():
                    _recurse(nested)
            elif isinstance(value, list):
                for nested in value:
                    _recurse(nested)

        _recurse(body)
        assert not BANNED_RESPONSE_RE.search(json.dumps(body, sort_keys=True))


def test_openapi_exposes_backup_health_schema(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, marker=_marker_body())
    schema = client.get("/openapi.json").json()
    assert "BackupHealth" in schema["components"]["schemas"]
