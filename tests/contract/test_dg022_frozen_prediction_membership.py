"""DG-022 contracts for historical frozen-prediction membership."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.dynasty_genius.outcome_loop.frozen_prediction_membership import (
    resolve_frozen_prediction_membership,
)

CAPTURE_DATE = "2026-08-05"
SOURCE = "model_pvo"
KEY_COLUMNS = (
    "capture_date",
    "source",
    "semantic_output_hash",
    "provenance_hash",
    "player_key",
)


def _declaration(path: Path, payload: dict | None = None) -> Path:
    data = payload or {
        "seasons": {
            "2026": {
                "frozen_capture_date": CAPTURE_DATE,
                "source": SOURCE,
                "declared_by": "David",
                "declared_at": "2026-08-13T23:59:00-04:00",
            }
        }
    }
    path.write_text(json.dumps(data))
    return path


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE model_forward_capture_raw (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                sleeper_id TEXT,
                engine_path TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash,
                    provenance_hash, player_key
                )
            );
            CREATE TABLE model_forward_capture_joinable (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                sleeper_id TEXT,
                engine_path TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash,
                    provenance_hash, player_key
                )
            );
            CREATE TABLE model_forward_prediction_snapshot (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                projection_2y,
                prediction_ppg_status TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash,
                    provenance_hash, player_key
                )
            );
            """
        )
    return path


def _insert(
    db_path: Path,
    *,
    sleeper_id: str,
    engine_path: str,
    suffix: str = "a",
    joinable: bool = False,
    prediction_status: str | None = None,
    projection_2y: object = None,
) -> None:
    key = (
        CAPTURE_DATE,
        SOURCE,
        f"semantic-{suffix}",
        f"provenance-{suffix}",
        f"sleeper:{sleeper_id}",
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO model_forward_capture_raw VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*key, sleeper_id, engine_path),
        )
        if joinable:
            conn.execute(
                "INSERT INTO model_forward_capture_joinable VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*key, sleeper_id, engine_path),
            )
        if prediction_status is not None:
            conn.execute(
                "INSERT INTO model_forward_prediction_snapshot VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*key, projection_2y, prediction_status),
            )


def _resolve(tmp_path: Path, sleeper_id: str, rostered: tuple[str, ...] = ()) -> dict:
    return resolve_frozen_prediction_membership(
        sleeper_id,
        season=2026,
        declaration_path=_declaration(tmp_path / "declaration.json"),
        db_path=tmp_path / "capture.db",
        current_rostered_skill_sleeper_ids=rostered,
    )


def test_captured_joinable_prediction_is_included(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="modeled",
        engine_path="ENGINE_B",
        joinable=True,
        prediction_status="captured",
        projection_2y=14.5,
    )

    result = _resolve(tmp_path, "modeled", ("modeled",))

    assert result["status"] == "included"
    assert result["basis"] == "model_supported_prediction_captured"
    assert result["frozen_capture_date"] == CAPTURE_DATE
    assert result["coverage"] == {
        "current_rostered_skill_player_count": 1,
        "current_rostered_skill_in_frozen_prediction_cohort_count": 1,
        "current_rostered_skill_not_in_frozen_prediction_cohort_count": 0,
    }


def test_pre_model_with_sleeper_and_null_dg_is_proven_excluded_not_identity_pending(
    tmp_path: Path,
) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="9502",
        engine_path="PRE_MODEL",
        prediction_status="capture_incomplete",
        projection_2y=None,
    )

    result = _resolve(tmp_path, "9502", ("9502",))

    assert result["status"] == "not_in_frozen_prediction_cohort"
    assert result["basis"] == "non_model_route_at_freeze"
    assert result["message"] == (
        "No model prediction was frozen for 2026 outcome evaluation."
    )
    assert "identity" not in result["message"].lower()


def test_current_roster_player_absent_from_frozen_universe_is_excluded(tmp_path: Path) -> None:
    _database(tmp_path / "capture.db")

    result = _resolve(tmp_path, "late-addition", ("late-addition",))

    assert result["status"] == "not_in_frozen_prediction_cohort"
    assert result["basis"] == "not_present_in_frozen_universe"


def test_model_supported_raw_without_joinable_row_fails_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(db_path, sleeper_id="broken", engine_path="ENGINE_B")

    result = _resolve(tmp_path, "broken")

    assert result["status"] == "unavailable"
    assert result["basis"] == "store_unavailable_or_ambiguous"


def test_unknown_frozen_engine_route_fails_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(db_path, sleeper_id="unknown-route", engine_path="SURPRISE_ROUTE")

    result = _resolve(tmp_path, "unknown-route")

    assert result["status"] == "unavailable"


def test_nonmodel_row_with_captured_finite_companion_fails_closed(
    tmp_path: Path,
) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="contradictory",
        engine_path="PRE_MODEL",
        prediction_status="captured",
        projection_2y=12.0,
    )

    result = _resolve(tmp_path, "contradictory")

    assert result["status"] == "unavailable"


def test_joinable_row_without_captured_prediction_is_incomplete(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="incomplete",
        engine_path="ENGINE_A",
        joinable=True,
        prediction_status="capture_incomplete",
        projection_2y=None,
    )

    result = _resolve(tmp_path, "incomplete")

    assert result["status"] == "prediction_capture_incomplete"
    assert result["basis"] == "prediction_capture_incomplete"


def test_incomplete_status_with_finite_projection_fails_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="contradictory-incomplete",
        engine_path="ENGINE_B",
        joinable=True,
        prediction_status="capture_incomplete",
        projection_2y=12.0,
    )

    result = _resolve(tmp_path, "contradictory-incomplete")

    assert result["status"] == "unavailable"
    assert result["basis"] == "store_unavailable_or_ambiguous"


def test_captured_prediction_with_wrong_type_fails_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="wrong-type",
        engine_path="ENGINE_B",
        joinable=True,
        prediction_status="captured",
        projection_2y="not-a-number",
    )

    result = _resolve(tmp_path, "wrong-type")

    assert result["status"] == "unavailable"


def test_captured_prediction_with_nonfinite_value_fails_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="nonfinite",
        engine_path="ENGINE_B",
        joinable=True,
        prediction_status="captured",
        projection_2y=float("inf"),
    )

    result = _resolve(tmp_path, "nonfinite")

    assert result["status"] == "unavailable"


def test_conflicting_same_day_vintages_fail_closed(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(db_path, sleeper_id="conflict", engine_path="PRE_MODEL", suffix="a")
    _insert(
        db_path,
        sleeper_id="conflict",
        engine_path="ENGINE_B",
        suffix="b",
        joinable=True,
        prediction_status="captured",
        projection_2y=11.0,
    )

    result = _resolve(tmp_path, "conflict")

    assert result["status"] == "unavailable"
    assert result["basis"] == "store_unavailable_or_ambiguous"


def test_consistent_same_day_vintages_are_deterministic(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(db_path, sleeper_id="stable", engine_path="PRE_MODEL", suffix="a")
    _insert(db_path, sleeper_id="stable", engine_path="PRE_MODEL", suffix="b")

    result = _resolve(tmp_path, "stable")

    assert result["status"] == "not_in_frozen_prediction_cohort"
    assert result["basis"] == "non_model_route_at_freeze"


def test_malformed_declaration_degrades_only_membership_lane(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    declaration_path = _declaration(
        tmp_path / "declaration.json", {"seasons": {"2026": {"source": SOURCE}}}
    )

    result = resolve_frozen_prediction_membership(
        "9502",
        season=2026,
        declaration_path=declaration_path,
        db_path=db_path,
        current_rostered_skill_sleeper_ids=("9502",),
    )

    assert result["status"] == "unavailable"
    assert result["frozen_capture_date"] is None
    assert result["coverage"] is None
    assert result["decision_supported"] is False


def test_timezone_naive_declaration_degrades_membership_lane(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    declaration_path = _declaration(
        tmp_path / "declaration.json",
        {
            "seasons": {
                "2026": {
                    "frozen_capture_date": CAPTURE_DATE,
                    "source": SOURCE,
                    "declared_by": "David",
                    "declared_at": "2026-08-13T23:59:00",
                }
            }
        },
    )

    result = resolve_frozen_prediction_membership(
        "9502", season=2026, declaration_path=declaration_path, db_path=db_path
    )

    assert result["status"] == "unavailable"


def test_duplicate_declaration_key_degrades_membership_lane(tmp_path: Path) -> None:
    db_path = _database(tmp_path / "capture.db")
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_text(
        '{"seasons":{"2026":{"frozen_capture_date":"2026-08-05",'
        '"frozen_capture_date":"2026-08-06","source":"model_pvo",'
        '"declared_by":"David","declared_at":"2026-08-13T23:59:00-04:00"}}}'
    )

    result = resolve_frozen_prediction_membership(
        "9502", season=2026, declaration_path=declaration_path, db_path=db_path
    )

    assert result["status"] == "unavailable"


def test_roster_coverage_uses_frozen_inclusion_not_current_model_route(
    tmp_path: Path,
) -> None:
    db_path = _database(tmp_path / "capture.db")
    _insert(
        db_path,
        sleeper_id="included-now-pre-model",
        engine_path="ENGINE_B",
        joinable=True,
        prediction_status="captured",
        projection_2y=9.0,
    )
    _insert(db_path, sleeper_id="excluded-now-modeled", engine_path="PRE_MODEL")

    result = _resolve(
        tmp_path,
        "included-now-pre-model",
        ("included-now-pre-model", "excluded-now-modeled", "late-addition"),
    )

    assert result["coverage"] == {
        "current_rostered_skill_player_count": 3,
        "current_rostered_skill_in_frozen_prediction_cohort_count": 1,
        "current_rostered_skill_not_in_frozen_prediction_cohort_count": 2,
    }
