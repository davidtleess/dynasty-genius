"""T3 RED: read-only SQLite capture-store reader and assembly glue.

These tests use temp SQLite databases that mirror the real capture schemas
needed by the reader:

- ``fc_forward_capture_raw`` with ``snapshot_date``, ``source``,
  ``settings_hash``, and ``player_key``.
- ``model_forward_capture_raw`` plus the
  ``model_forward_prediction_snapshot`` companion table keyed by
  ``capture_date``.

No route, app/main wiring, OpenAPI, real app/config, or real app/data files.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


def _models():
    import app.api.routes.system_capture_health_models as models

    return models


def _season_windows():
    return _models().SeasonWindows.model_validate({"in_season_months": [9, 10, 11, 12, 1]})


def _now() -> datetime:
    return datetime(2026, 7, 2, 13, 0, tzinfo=ZoneInfo("America/New_York"))


def _fc_store(**overrides):
    models = _models()
    body = {
        "store_id": "fc_forward_capture",
        "db_path": "app/data/fc_forward_capture.db",
        "table": "fc_forward_capture_raw",
        "date_column": "snapshot_date",
        "source_filter": "fc_native",
        "expected_settings_hash": "canonical_hash",
        "capture_start_date": "2026-06-24",
        "expected_cadence": "daily",
        "scheduled_time_local": "09:00",
        "grace_hours": 3,
        "density_floor_pct": 50,
        "density_baseline_window": 14,
        "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
        "window_risk_contiguous_days": 7,
        "companion_tables": [],
    }
    body.update(overrides)
    return models.CadenceStoreConfig.model_validate(body)


def _model_store(**overrides):
    models = _models()
    body = {
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
        "companion_tables": [
            {
                "table": "model_forward_prediction_snapshot",
                "date_column": "capture_date",
                "capture_start_date": "2026-06-28",
            }
        ],
    }
    body.update(overrides)
    return models.CadenceStoreConfig.model_validate(body)


def _inspect(store_config, repo_root: Path):
    return _models().inspect_capture_store(
        store_config=store_config,
        repo_root=repo_root,
        now=_now(),
        timezone="America/New_York",
        season_windows=_season_windows(),
    )


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
                sleeper_id TEXT,
                player_name TEXT,
                position TEXT,
                value REAL,
                overall_rank INTEGER,
                position_rank INTEGER,
                trend_30day REAL,
                retrieved_at TEXT,
                payload_hash TEXT,
                PRIMARY KEY (snapshot_date, source, settings_hash, player_key)
            )
            """
        )
    return db_path


def _insert_fc_rows(
    db_path: Path,
    *,
    snapshot_date: str,
    source: str = "fc_native",
    settings_hash: str = "canonical_hash",
    count: int = 3,
    key_prefix: str = "player",
) -> None:
    with sqlite3.connect(db_path) as conn:
        for idx in range(count):
            conn.execute(
                """
                INSERT INTO fc_forward_capture_raw (
                    snapshot_date, source, settings_hash, player_key,
                    sleeper_id, player_name, position, value, overall_rank,
                    position_rank, trend_30day, retrieved_at, payload_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    snapshot_date,
                    source,
                    settings_hash,
                    f"{key_prefix}:{idx}",
                    str(idx),
                    f"Player {idx}",
                    "WR",
                    1.0,
                    idx + 1,
                    idx + 1,
                    0.0,
                    "2026-07-02T09:00:00-04:00",
                    f"hash-{idx}",
                ],
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
                sleeper_id TEXT,
                dg_player_id TEXT,
                player_name TEXT,
                position TEXT,
                engine_path TEXT,
                dynasty_value_score REAL,
                dvs_pct REAL,
                xvar REAL,
                model_grade TEXT,
                model_version TEXT,
                artifact_vintage TEXT,
                row_index INTEGER,
                semantic_row_hash TEXT,
                payload_hash TEXT,
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
                projection_2y REAL,
                utilization TEXT,
                prediction_ppg_status TEXT,
                util_snapshot_status TEXT,
                schema_version INTEGER,
                source_hash TEXT,
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
            key = f"sleeper:{idx}"
            values = [
                capture_date,
                "model_pvo",
                "semantic",
                "provenance",
                key,
                str(idx),
                f"dg-{idx}",
                f"Player {idx}",
                "WR",
                "ENGINE_B",
                10.0,
                0.5,
                1.0,
                "B",
                "v1",
                "vintage",
                idx,
                f"row-{idx}",
                f"payload-{idx}",
            ]
            conn.execute(
                """
                INSERT INTO model_forward_capture_raw (
                    capture_date, source, semantic_output_hash, provenance_hash,
                    player_key, sleeper_id, dg_player_id, player_name, position,
                    engine_path, dynasty_value_score, dvs_pct, xvar,
                    model_grade, model_version, artifact_vintage, row_index,
                    semantic_row_hash, payload_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            conn.execute(
                """
                INSERT INTO model_forward_prediction_snapshot (
                    capture_date, source, semantic_output_hash, provenance_hash,
                    player_key, projection_2y, utilization, prediction_ppg_status,
                    util_snapshot_status, schema_version, source_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    capture_date,
                    "model_pvo",
                    "semantic",
                    "provenance",
                    key,
                    11.0,
                    "{}",
                    "ok",
                    "ok",
                    1,
                    "source",
                ],
            )


def test_absent_store_returns_degraded_absent_without_creating_file(tmp_path: Path) -> None:
    store = _fc_store()
    db_path = tmp_path / store.db_path
    assert not db_path.exists()

    result = _inspect(store, tmp_path)

    assert result.store_status == "degraded"
    assert result.store_presence == "absent"
    assert result.caveats == ["store_absent"]
    assert result.decision_supported is False
    assert not db_path.exists()


def test_healthy_store_is_read_only_and_bytes_do_not_change(tmp_path: Path) -> None:
    store = _fc_store(capture_start_date="2026-06-30")
    db_path = _create_fc_db(tmp_path)
    for day in ["2026-06-30", "2026-07-01", "2026-07-02"]:
        _insert_fc_rows(db_path, snapshot_date=day, count=3)
    before = db_path.read_bytes()

    result = _inspect(store, tmp_path)

    assert result.store_status == "ok"
    assert result.store_presence == "present"
    assert result.timeline.present_days == 3
    assert result.timeline.missing_dates_count == 0
    assert db_path.read_bytes() == before


@pytest.mark.parametrize(
    "db_builder",
    [
        lambda path: path.write_bytes(b""),
        lambda path: sqlite3.connect(path).close(),
        lambda path: sqlite3.connect(path).execute(
            "CREATE TABLE fc_forward_capture_raw (source TEXT, settings_hash TEXT)"
        ).connection.close(),
    ],
)
def test_unreadable_or_malformed_store_returns_degraded_without_raw_sqlite_exception(
    tmp_path: Path,
    db_builder,
) -> None:
    store = _fc_store()
    db_path = tmp_path / store.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_builder(db_path)

    result = _inspect(store, tmp_path)

    assert result.store_status == "degraded"
    assert result.store_presence == "present"
    assert "store_unreadable" in result.caveats
    assert result.decision_supported is False


def test_source_filter_and_expected_settings_hash_grouping_feed_analyzer_metadata(
    tmp_path: Path,
) -> None:
    store = _fc_store(capture_start_date="2026-06-30")
    db_path = _create_fc_db(tmp_path)
    _insert_fc_rows(db_path, snapshot_date="2026-06-30", settings_hash="canonical_hash")
    _insert_fc_rows(db_path, snapshot_date="2026-07-01", settings_hash="other_hash")
    _insert_fc_rows(db_path, snapshot_date="2026-07-02", source="other_source")

    result = _inspect(store, tmp_path)

    assert result.store_status == "degraded"
    assert result.timeline.present_days == 1
    assert result.timeline.missing_dates_count == 2
    assert "unexpected_settings_hash_detected" in result.caveats


def test_distinct_date_counts_sum_rows_and_do_not_count_duplicate_dates_twice(
    tmp_path: Path,
) -> None:
    store = _fc_store(capture_start_date="2026-07-02")
    db_path = _create_fc_db(tmp_path)
    _insert_fc_rows(db_path, snapshot_date="2026-07-02", count=5)

    result = _inspect(store, tmp_path)

    assert result.store_status == "ok"
    assert result.timeline.expected_days == 1
    assert result.timeline.present_days == 1
    assert result.timeline.consecutive_days_current == 1
    assert result.density.sub_floor_dates == []


def test_companion_table_distinct_dates_feed_companion_coverage(tmp_path: Path) -> None:
    store = _model_store(capture_start_date="2026-06-24")
    db_path = _create_model_db(tmp_path)
    for day in [
        "2026-06-24",
        "2026-06-25",
        "2026-06-26",
        "2026-06-27",
        "2026-06-28",
        "2026-06-29",
        "2026-06-30",
        "2026-07-01",
        "2026-07-02",
    ]:
        _insert_model_rows(db_path, capture_date=day)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM model_forward_prediction_snapshot WHERE capture_date < ?", ["2026-06-28"])

    real_shape = _inspect(store, tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "DELETE FROM model_forward_prediction_snapshot WHERE capture_date = ?",
            ["2026-06-30"],
        )
    missing_post_start = _inspect(store, tmp_path)

    assert real_shape.store_status == "ok"
    assert "companion_rows_missing" not in real_shape.caveats
    assert missing_post_start.store_status == "degraded"
    assert "companion_rows_missing" in missing_post_start.caveats
