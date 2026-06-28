"""Realized-Outcome Loop T1 RED: companion prediction-snapshot store.

These tests define the companion table contract only. Production implementation belongs
to the GREEN step.
"""

from __future__ import annotations

import importlib
import math
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.capture import model_forward_capture_store as core_store_module
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
)

PK_COLUMNS = (
    "capture_date",
    "source",
    "semantic_output_hash",
    "provenance_hash",
    "player_key",
)
CANONICAL_UTIL_FIELDS = (
    "snap_share",
    "route_participation",
    "target_share_nfl",
    "air_yards_share",
    "weighted_opportunity",
    "yprr",
    "tprr",
)


def _prediction_module():
    return importlib.import_module(
        "src.dynasty_genius.capture.prediction_snapshot_store"
    )


def _as_mapping(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return record
    if hasattr(record, "model_dump"):
        return record.model_dump()
    if hasattr(record, "__dict__"):
        return dict(record.__dict__)
    raise TypeError(f"unsupported record shape: {type(record)!r}")


def _pk(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row[column] for column in PK_COLUMNS}


def _core_entry(
    *,
    capture_date: str = "2026-06-24",
    player_key: str = "sleeper:9509",
) -> dict[str, Any]:
    return {
        "capture_date": capture_date,
        "source": MODEL_PVO_SOURCE,
        "semantic_output_hash": "semantic-v1",
        "provenance_hash": "provenance-v1",
        "player_key": player_key,
        "sleeper_id": "9509",
        "dg_player_id": "dg_bijan",
        "player_name": "Bijan Robinson",
        "position": "RB",
        "engine_path": "ENGINE_B",
        "dynasty_value_score": 98.5,
        "dvs_pct": 97.0,
        "xvar": 18.5,
        "model_grade": "MODEL",
        "model_version": "engine_b_v2",
        "artifact_vintage": "2026-06-23T12:00:00+00:00",
        "row_index": 0,
        "semantic_row_hash": "row-hash-v1",
        "payload_hash": "row-hash-v1",
    }


def _prediction_row(**overrides: Any) -> dict[str, Any]:
    row = {
        **_pk(_core_entry()),
        "projection_2y": 17.25,
        "utilization": {
            "snap_share": {"value": 0.71, "role": "model_input"},
            "route_participation": {"value": 0.64, "role": "model_input"},
            "target_share_nfl": {"value": 0.18, "role": "diagnostic_only"},
            "air_yards_share": {"value": 0.08, "role": "diagnostic_only"},
            "weighted_opportunity": {"value": 0.79, "role": "model_input"},
            "yprr": {"value": 2.19, "role": "model_input"},
            "tprr": {"value": 0.22, "role": "model_input"},
        },
        "prediction_ppg_status": "captured",
        "util_snapshot_status": "complete",
        "schema_version": 1,
        "source_hash": "source-hash-v1",
    }
    row.update(overrides)
    return row


def _core_row_bytes(db_path: Path, entry: dict[str, Any]) -> tuple[Any, ...]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM model_forward_capture_raw WHERE "
            + " AND ".join(f"{column}=?" for column in PK_COLUMNS),
            [entry[column] for column in PK_COLUMNS],
        ).fetchone()


def test_append_snapshot_round_trips_projection_and_role_tagged_utilization(
    tmp_path,
) -> None:
    module = _prediction_module()
    store = module.PredictionSnapshotStore(tmp_path / "model_forward.db")
    row = _prediction_row()

    store.append_snapshot(row)
    stored = _as_mapping(store.read_snapshot(_pk(row)))

    assert stored["projection_2y"] == pytest.approx(17.25)
    assert stored["prediction_ppg_status"] == "captured"
    assert stored["util_snapshot_status"] == "complete"
    assert set(stored["utilization"]) == set(CANONICAL_UTIL_FIELDS)
    assert stored["utilization"]["snap_share"] == {
        "value": pytest.approx(0.71),
        "role": "model_input",
    }
    assert stored["utilization"]["target_share_nfl"] == {
        "value": pytest.approx(0.18),
        "role": "diagnostic_only",
    }


def test_companion_store_does_not_mutate_core_schema_or_core_row_bytes(
    tmp_path,
) -> None:
    module = _prediction_module()
    db_path = tmp_path / "model_forward.db"
    core = ModelForwardCaptureStore(db_path)
    entry = _core_entry()
    core.append_entries([entry])
    data_columns_before = core_store_module._DATA_COLUMNS
    content_columns_before = core_store_module._CONTENT_COLUMNS
    core_row_before = _core_row_bytes(db_path, entry)

    companion = module.PredictionSnapshotStore(db_path)
    companion.append_snapshot(_prediction_row())

    assert core_store_module._DATA_COLUMNS == data_columns_before
    assert core_store_module._CONTENT_COLUMNS == content_columns_before
    assert _core_row_bytes(db_path, entry) == core_row_before


def test_absent_companion_row_uses_store_rollout_marker_to_classify_legacy_vs_failed_write(
    tmp_path,
) -> None:
    module = _prediction_module()
    db_path = tmp_path / "model_forward.db"
    companion = module.PredictionSnapshotStore(db_path)
    core = ModelForwardCaptureStore(db_path)
    before_rollout = _core_entry(
        capture_date="1900-01-01",
        player_key="sleeper:legacy",
    )
    after_rollout = _core_entry(
        capture_date="2999-01-01",
        player_key="sleeper:failed-write",
    )
    core.append_entries([before_rollout, after_rollout])

    legacy = _as_mapping(companion.read_snapshot(_pk(before_rollout)))
    failed_write = _as_mapping(companion.read_snapshot(_pk(after_rollout)))

    assert legacy["projection_2y"] is None
    assert legacy["prediction_ppg_status"] == "missing_legacy_capture"
    assert failed_write["projection_2y"] is None
    assert failed_write["prediction_ppg_status"] == "capture_incomplete"


def test_missing_projection_is_preserved_as_null_with_incomplete_status(
    tmp_path,
) -> None:
    module = _prediction_module()
    store = module.PredictionSnapshotStore(tmp_path / "model_forward.db")
    row = _prediction_row(
        projection_2y=None,
        prediction_ppg_status="capture_incomplete",
    )

    store.append_snapshot(row)

    stored = _as_mapping(store.read_snapshot(_pk(row)))
    assert stored["projection_2y"] is None
    assert stored["prediction_ppg_status"] == "capture_incomplete"


def test_absent_util_column_is_preserved_as_null_with_partial_status(tmp_path) -> None:
    module = _prediction_module()
    store = module.PredictionSnapshotStore(tmp_path / "model_forward.db")
    util = dict(_prediction_row()["utilization"])
    util.pop("route_participation")
    row = _prediction_row(utilization=util, util_snapshot_status="partial")

    store.append_snapshot(row)

    stored = _as_mapping(store.read_snapshot(_pk(row)))
    assert stored["utilization"]["route_participation"] == {
        "value": None,
        "role": "diagnostic_only",
    }
    assert stored["util_snapshot_status"] == "partial"


def test_wrong_type_util_value_fails_loud(tmp_path) -> None:
    module = _prediction_module()
    store = module.PredictionSnapshotStore(tmp_path / "model_forward.db")
    util = dict(_prediction_row()["utilization"])
    util["snap_share"] = {"value": "not-a-number", "role": "model_input"}

    with pytest.raises((TypeError, ValueError)):
        store.append_snapshot(_prediction_row(utilization=util))


@pytest.mark.parametrize("bad_projection", [math.nan, math.inf, -math.inf])
def test_non_finite_projection_is_rejected(tmp_path, bad_projection: float) -> None:
    module = _prediction_module()
    store = module.PredictionSnapshotStore(tmp_path / "model_forward.db")

    with pytest.raises((TypeError, ValueError)):
        store.append_snapshot(_prediction_row(projection_2y=bad_projection))


def test_duplicate_pk_is_idempotent_no_dup_and_not_upsert(tmp_path) -> None:
    module = _prediction_module()
    db_path = tmp_path / "model_forward.db"
    store = module.PredictionSnapshotStore(db_path)
    row = _prediction_row()

    store.append_snapshot(row)
    store.append_snapshot(dict(row))

    with sqlite3.connect(db_path) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM model_forward_prediction_snapshot"
        ).fetchone()[0]
    assert row_count == 1
    assert _as_mapping(store.read_snapshot(_pk(row)))["projection_2y"] == pytest.approx(
        17.25
    )

    with pytest.raises(ValueError):
        store.append_snapshot(_prediction_row(projection_2y=22.0))
    assert _as_mapping(store.read_snapshot(_pk(row)))["projection_2y"] == pytest.approx(
        17.25
    )
