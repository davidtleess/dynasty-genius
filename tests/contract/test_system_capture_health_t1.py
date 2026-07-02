"""T1 RED: capture-health cadence config loader and response models.

These tests are fixture-only. They use temp cadence config files and never read
the real app/config cadence file or any gitignored SQLite store. T1 covers only
Pydantic models and the fail-closed cadence loader; analyzer logic, SQLite
reading, route wiring, and OpenAPI generation belong to later tasks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError


def _models():
    import app.api.routes.system_capture_health_models as models

    return models


def _companion(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    companion = {
        "table": "model_forward_prediction_snapshot",
        "date_column": "capture_date",
        "capture_start_date": "2026-06-28",
    }
    if overrides:
        companion.update(overrides)
    return companion


def _store(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    store = {
        "store_id": "model_forward_capture",
        "db_path": "app/data/model_forward_capture.db",
        "table": "model_forward_capture_raw",
        "date_column": "capture_date",
        "source_filter": None,
        "expected_settings_hash": None,
        "capture_start_date": "2026-06-24",
        "expected_cadence": "daily",
        "scheduled_time_local": "09:45",
        "grace_hours": 3,
        "density_floor_pct": 50,
        "density_baseline_window": 14,
        "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
        "window_risk_contiguous_days": 7,
        "companion_tables": [_companion()],
    }
    if overrides:
        store.update(overrides)
    return store


def _fc_store(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    store = _store(
        {
            "store_id": "fc_forward_capture",
            "db_path": "app/data/fc_forward_capture.db",
            "table": "fc_forward_capture_raw",
            "date_column": "snapshot_date",
            "source_filter": "fc_native",
            "expected_settings_hash": "e27351d720e9fcf0",
            "scheduled_time_local": "09:00",
            "companion_tables": [],
        }
    )
    if overrides:
        store.update(overrides)
    return store


def _config_body(stores: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": stores if stores is not None else [_fc_store(), _store()],
    }


def _write_config(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_loader_reads_injected_temp_config_with_companion_tables_and_settings_hash(
    tmp_path: Path,
) -> None:
    models = _models()
    config_path = _write_config(tmp_path / "capture_cadence.json", _config_body())

    config = models.load_capture_cadence(config_path=config_path)

    assert isinstance(config, models.CaptureCadenceConfig)
    assert config.config_version == 1
    assert config.timezone == "America/New_York"
    assert len(config.stores) == 2
    fc_store = config.stores[0]
    assert fc_store.store_id == "fc_forward_capture"
    assert fc_store.source_filter == "fc_native"
    assert fc_store.expected_settings_hash == "e27351d720e9fcf0"
    assert fc_store.companion_tables == []
    model_store = config.stores[1]
    assert model_store.expected_settings_hash is None
    assert model_store.companion_tables[0].table == "model_forward_prediction_snapshot"
    assert model_store.companion_tables[0].capture_start_date == "2026-06-28"


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (
            lambda path: path.write_text(
                json.dumps(_config_body([_store({"expected_cadence": "weekly"})])),
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
                            _store({"store_id": "duplicate"}),
                            _fc_store({"store_id": "duplicate"}),
                        ]
                    )
                ),
                encoding="utf-8",
            ),
            "duplicate",
        ),
    ],
)
def test_loader_raises_typed_error_for_config_family_failures(
    tmp_path: Path,
    writer,
    message_fragment: str,
) -> None:
    models = _models()
    config_path = tmp_path / "capture_cadence.json"
    writer(config_path)

    with pytest.raises(models.CaptureHealthConfigError) as exc_info:
        models.load_capture_cadence(config_path=config_path)

    assert message_fragment in str(exc_info.value).lower()


@pytest.mark.parametrize(
    ("store_overrides", "companion_overrides"),
    [
        ({"db_path": "/tmp/fc_forward_capture.db"}, None),
        ({"db_path": "app/data/../secrets/fc_forward_capture.db"}, None),
        ({"table": "fc_forward_capture_raw; DROP TABLE x"}, None),
        ({"date_column": "snapshot-date"}, None),
        ({}, {"table": "model_forward_prediction_snapshot; DROP TABLE x"}),
        ({}, {"date_column": "capture-date"}),
    ],
)
def test_loader_rejects_unsafe_paths_and_sqlish_identifiers(
    tmp_path: Path,
    store_overrides: dict[str, Any],
    companion_overrides: dict[str, Any] | None,
) -> None:
    models = _models()
    store = _store(store_overrides)
    if companion_overrides is not None:
        store["companion_tables"] = [_companion(companion_overrides)]
    config_path = _write_config(tmp_path / "capture_cadence.json", _config_body([store]))

    with pytest.raises(models.CaptureHealthConfigError) as exc_info:
        models.load_capture_cadence(config_path=config_path)

    assert "config" in str(exc_info.value).lower()


def test_config_models_forbid_extra_fields_and_gate_4_ready_injection() -> None:
    models = _models()
    body = _config_body()

    with pytest.raises(ValidationError):
        models.CaptureCadenceConfig.model_validate(body | {"gate_4_ready": True})
    with pytest.raises(ValidationError):
        models.CadenceStoreConfig.model_validate(_store({"gate_4_ready": True}))
    with pytest.raises(ValidationError):
        models.CompanionTableConfig.model_validate(
            _companion({"gate_4_ready": True})
        )


def test_response_models_lock_enums_recursive_decision_supported_and_extra_forbid() -> None:
    models = _models()

    store_health = {
        "store_id": "fc_forward_capture",
        "store_status": "ok",
        "store_presence": "present",
        "timeline": {
            "capture_start_date": "2026-06-24",
            "first_date": "2026-06-24",
            "last_date": "2026-07-02",
            "expected_days": 9,
            "present_days": 9,
            "missing_dates_count": 0,
            "missing_ranges": [],
            "missing_ranges_total": 0,
            "max_contiguous_gap_days": 0,
            "consecutive_days_current": 9,
        },
        "staleness": {
            "last_capture_date": "2026-07-02",
            "expected_by": "2026-07-02T12:00:00-04:00",
            "stale": False,
            "grace_hours": 3,
        },
        "density": {
            "floor_pct": 50,
            "baseline_median_rows": 462,
            "baseline_window": 14,
            "sub_floor_dates": [],
        },
        "flags": {
            "warn_missing": False,
            "warn_basis": "off_season>=3 consecutive",
            "window_risk": False,
            "window_risk_basis": ">=7 contiguous missing days",
        },
        "caveats": [],
        "decision_supported": False,
    }
    response = models.CaptureHealthResponse.model_validate(
        {
            "overall_status": "ok",
            "config_version": 1,
            "checked_at": "2026-07-02T13:00:00-04:00",
            "stores": [store_health],
            "decision_supported": False,
        }
    )
    error = models.CaptureHealthErrorResponse.model_validate(
        {
            "error": "capture_cadence_unavailable",
            "message": "capture cadence configuration is unavailable",
            "decision_supported": False,
        }
    )

    assert response.stores[0].timeline.missing_ranges_total == 0
    assert response.stores[0].decision_supported is False
    assert error.decision_supported is False

    with pytest.raises(ValidationError):
        models.CaptureHealthResponse.model_validate(
            response.model_dump() | {"overall_status": "blocked"}
        )
    with pytest.raises(ValidationError):
        models.StoreHealth.model_validate(store_health | {"store_presence": "unknown"})
    with pytest.raises(ValidationError):
        models.StoreHealth.model_validate(store_health | {"decision_supported": True})
    with pytest.raises(ValidationError):
        models.CaptureHealthErrorResponse.model_validate(
            error.model_dump() | {"decision_supported": True}
        )
    with pytest.raises(ValidationError):
        models.StoreTimeline.model_validate(
            store_health["timeline"] | {"gate_4_ready": True}
        )
