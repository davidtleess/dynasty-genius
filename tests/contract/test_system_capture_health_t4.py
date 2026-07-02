"""T4 RED: capture-health HTTP route and OpenAPI contract.

End-to-end route tests use temp cadence configs and temp SQLite stores only.
They never read the real ``app/config/capture_cadence.json`` or gitignored
``app/data`` DBs. T4 owns route wiring, sanitized config 503s, response rollup,
clock injection, and OpenAPI exposure.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

BANNED_RESPONSE_RE = re.compile(
    r"\b(gate_4_ready|gate4|trusted|safe|recommended|buy|sell|hold|start|sit)\b",
    re.IGNORECASE,
)


def _route_module():
    from app.api.routes import system_capture_health

    return system_capture_health


def _client_with_temp_config(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config_path: Path,
    repo_root: Path,
    now: datetime | None = None,
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(
        route,
        "_CLOCK",
        lambda: now
        if now is not None
        else datetime(2026, 7, 2, 13, tzinfo=ZoneInfo("America/New_York")),
    )
    from app.main import app

    return TestClient(app)


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _fc_store(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    store = {
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
    if overrides:
        store.update(overrides)
    return store


def _model_store(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    store = {
        "store_id": "model_forward_capture",
        "db_path": "app/data/model_forward_capture.db",
        "table": "model_forward_capture_raw",
        "date_column": "capture_date",
        "source_filter": None,
        "expected_settings_hash": None,
        "capture_start_date": "2026-06-30",
        "expected_cadence": "daily",
        "scheduled_time_local": "09:45",
        "grace_hours": 3,
        "density_floor_pct": 50,
        "density_baseline_window": 14,
        "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
        "window_risk_contiguous_days": 7,
        "companion_tables": [
            {
                "table": "model_forward_prediction_snapshot",
                "date_column": "capture_date",
                "capture_start_date": "2026-06-30",
            }
        ],
    }
    if overrides:
        store.update(overrides)
    return store


def _config_body(stores: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": stores if stores is not None else [_fc_store(), _model_store()],
    }


def _create_fc_db(repo_root: Path) -> Path:
    db_path = repo_root / "app/data/fc_forward_capture.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fc_forward_capture_raw (
                snapshot_date TEXT,
                source TEXT,
                settings_hash TEXT,
                player_key TEXT,
                PRIMARY KEY (snapshot_date, source, settings_hash, player_key)
            )
            """
        )
    return db_path


def _insert_fc_rows(
    db_path: Path,
    *,
    snapshot_date: str,
    settings_hash: str = "canonical_hash",
    count: int = 3,
) -> None:
    with sqlite3.connect(db_path) as conn:
        for idx in range(count):
            conn.execute(
                "INSERT INTO fc_forward_capture_raw VALUES (?, ?, ?, ?)",
                [snapshot_date, "fc_native", settings_hash, f"player:{idx}"],
            )


def _create_model_db(repo_root: Path) -> Path:
    db_path = repo_root / "app/data/model_forward_capture.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE model_forward_capture_raw (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash,
                    provenance_hash, player_key
                )
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE model_forward_prediction_snapshot (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash,
                    provenance_hash, player_key
                )
            )
            """
        )
    return db_path


def _insert_model_rows(db_path: Path, *, capture_date: str, count: int = 3) -> None:
    with sqlite3.connect(db_path) as conn:
        for idx in range(count):
            values = [capture_date, "model_pvo", "semantic", "provenance", f"p:{idx}"]
            conn.execute("INSERT INTO model_forward_capture_raw VALUES (?, ?, ?, ?, ?)", values)
            conn.execute(
                "INSERT INTO model_forward_prediction_snapshot VALUES (?, ?, ?, ?, ?)",
                values,
            )


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


def test_capture_health_route_reports_ok_for_temp_healthy_stores_and_openapi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    fc_db = _create_fc_db(tmp_path)
    model_db = _create_model_db(tmp_path)
    for day in ["2026-06-30", "2026-07-01", "2026-07-02"]:
        _insert_fc_rows(fc_db, snapshot_date=day)
        _insert_model_rows(model_db, capture_date=day)
    client = _client_with_temp_config(monkeypatch, config_path=config_path, repo_root=tmp_path)

    response = client.get("/api/system/capture-health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "ok"
    assert body["config_version"] == 1
    assert body["checked_at"] == "2026-07-02T13:00:00-04:00"
    assert body["decision_supported"] is False
    _assert_decision_supported_false_recursive(body)
    _assert_no_banned_response_language(body)
    stores = {store["store_id"]: store for store in body["stores"]}
    assert set(stores) == {"fc_forward_capture", "model_forward_capture"}
    assert all(store["store_status"] == "ok" for store in stores.values())
    assert all(store["store_presence"] == "present" for store in stores.values())
    assert all(store["timeline"]["present_days"] == 3 for store in stores.values())
    assert all(store["timeline"]["missing_ranges_total"] == 0 for store in stores.values())

    schema = client.get("/openapi.json").json()
    path_spec = schema["paths"]["/api/system/capture-health"]["get"]
    assert path_spec["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("CaptureHealthResponse")
    assert path_spec["responses"]["503"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("CaptureHealthErrorResponse")


def test_capture_health_ci_shape_absent_stores_is_200_degraded_not_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    client = _client_with_temp_config(monkeypatch, config_path=config_path, repo_root=tmp_path)

    response = client.get("/api/system/capture-health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    stores = {store["store_id"]: store for store in body["stores"]}
    assert stores["fc_forward_capture"]["store_status"] == "degraded"
    assert stores["fc_forward_capture"]["store_presence"] == "absent"
    assert stores["fc_forward_capture"]["caveats"] == ["store_absent"]
    assert stores["model_forward_capture"]["store_status"] == "degraded"
    assert stores["model_forward_capture"]["store_presence"] == "absent"
    assert stores["model_forward_capture"]["caveats"] == ["store_absent"]
    _assert_decision_supported_false_recursive(body)


def test_capture_health_rolls_up_degraded_when_one_store_is_degraded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    fc_db = _create_fc_db(tmp_path)
    for day in ["2026-06-30", "2026-07-01", "2026-07-02"]:
        _insert_fc_rows(fc_db, snapshot_date=day)
    client = _client_with_temp_config(monkeypatch, config_path=config_path, repo_root=tmp_path)

    response = client.get("/api/system/capture-health")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    stores = {store["store_id"]: store for store in body["stores"]}
    assert stores["fc_forward_capture"]["store_status"] == "ok"
    assert stores["model_forward_capture"]["store_status"] == "degraded"
    assert stores["model_forward_capture"]["caveats"] == ["store_absent"]


@pytest.mark.parametrize(
    ("writer", "unsafe_substring"),
    [
        (lambda path: None, "capture_cadence.json"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "{not-json"),
        (
            lambda path: path.write_text(
                json.dumps(_config_body([_fc_store({"expected_cadence": "weekly"})])),
                encoding="utf-8",
            ),
            "weekly",
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
                            _fc_store({"store_id": "duplicate"}),
                            _model_store({"store_id": "duplicate"}),
                        ]
                    )
                ),
                encoding="utf-8",
            ),
            "duplicate",
        ),
        (
            lambda path: path.write_text(
                json.dumps(_config_body([_fc_store({"db_path": "/tmp/secret.db"})])),
                encoding="utf-8",
            ),
            "/tmp/secret.db",
        ),
        (
            lambda path: path.write_text(
                json.dumps(
                    _config_body([_fc_store({"table": "raw; DROP TABLE x"})])
                ),
                encoding="utf-8",
            ),
            "DROP TABLE",
        ),
    ],
)
def test_capture_health_config_failures_return_sanitized_fixed_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
    unsafe_substring: str,
) -> None:
    config_path = tmp_path / "capture_cadence.json"
    writer(config_path)
    client = _client_with_temp_config(monkeypatch, config_path=config_path, repo_root=tmp_path)

    response = client.get("/api/system/capture-health")

    assert response.status_code == 503
    body = response.json()
    assert body == {
        "error": "capture_health_unavailable",
        "message": "capture health configuration unavailable",
        "decision_supported": False,
    }
    serialized = json.dumps(body)
    assert unsafe_substring not in serialized
    assert str(tmp_path) not in serialized
    assert "Traceback" not in serialized


def test_capture_health_checked_at_uses_injected_clock_for_deterministic_staleness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    fc_db = _create_fc_db(tmp_path)
    model_db = _create_model_db(tmp_path)
    for day in ["2026-06-30", "2026-07-01"]:
        _insert_fc_rows(fc_db, snapshot_date=day)
        _insert_model_rows(model_db, capture_date=day)
    client = _client_with_temp_config(
        monkeypatch,
        config_path=config_path,
        repo_root=tmp_path,
        now=datetime(2026, 7, 2, 11, 59, 59, tzinfo=ZoneInfo("America/New_York")),
    )

    response = client.get("/api/system/capture-health")

    assert response.status_code == 200
    body = response.json()
    assert body["checked_at"] == "2026-07-02T11:59:59-04:00"
    assert all(store["staleness"]["stale"] is False for store in body["stores"])
