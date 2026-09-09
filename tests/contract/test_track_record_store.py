"""The immutable store that holds evaluation enrollments AND their later grades.

Why this file exists: a track record is only worth reading if the thing being graded cannot change
after the fact. So the store is content-addressed and append-only, a re-save of identical content
returns the ORIGINAL receipt with its original time, and a record whose bytes no longer match its id
is corruption that raises rather than a value that gets used.

DG-207 writes its grades through this same module, which is why `kind` is a closed set and why a
grade's cross-reference to its enrollment is verified on the way in.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.dynasty_genius.capture.track_record_store import (
    TrackRecordStoreError,
    list_records,
    read_record,
    save_record,
)

RECORDED_AT = datetime(2026, 9, 9, 9, 40, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 10, 9, 40, tzinfo=timezone.utc)


def enrollment(snapshot_id: str = "a" * 64) -> dict:
    return {
        "schema_version": "track_record.enrollment.v1",
        "snapshot_id": snapshot_id,
        "forecast_identity": "forecast-1",
        "enrolled_at": "2026-09-09T09:40:00Z",
    }


def artifacts() -> dict[str, bytes]:
    return {"prior_outcomes.csv": b"player_id,season,points,games,appeared\n1,2025,10.0,17,1\n"}


def test_a_saved_record_carries_its_content_identity(tmp_path):
    saved = save_record(
        tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
        recorded_at=RECORDED_AT,
    )
    assert saved["created"] is True
    record = saved["record"]
    assert set(record) == {"record_id", "kind", "recorded_at", "snapshot_id", "document", "artifact_hashes"}
    assert len(record["record_id"]) == 64 and all(c in "0123456789abcdef" for c in record["record_id"])
    assert record["kind"] == "enrollment"
    assert record["snapshot_id"] == "a" * 64
    assert record["recorded_at"] == "2026-09-09T09:40:00Z"
    assert set(record["artifact_hashes"]) == {"prior_outcomes.csv"}


def test_save_duplicate_keeps_original_time(tmp_path):
    first = save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                        recorded_at=RECORDED_AT)["record"]
    again = save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                        recorded_at=LATER)
    assert again["created"] is False
    assert again["record"]["recorded_at"] == first["recorded_at"]
    assert again["record"]["record_id"] == first["record_id"]


def test_read_record_returns_the_record_without_the_created_flag(tmp_path):
    saved = save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                        recorded_at=RECORDED_AT)["record"]
    read = read_record(tmp_path, saved["record_id"])
    assert read == saved
    assert "created" not in read


def test_corrupt_record_refuses(tmp_path):
    saved = save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                        recorded_at=RECORDED_AT)["record"]
    # tamper with the stored document so it no longer matches the id it is filed under
    path = next(p for p in tmp_path.rglob("document.json"))
    doc = json.loads(path.read_text())
    doc["forecast_identity"] = "someone else's forecast"
    path.write_text(json.dumps(doc))
    with pytest.raises(TrackRecordStoreError, match="content"):
        read_record(tmp_path, saved["record_id"])


def test_a_corrupt_duplicate_refuses_rather_than_returning_the_original(tmp_path):
    save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                recorded_at=RECORDED_AT)
    path = next(p for p in tmp_path.rglob("artifacts") if p.is_dir()) / "prior_outcomes.csv"
    path.write_bytes(b"tampered\n")
    with pytest.raises(TrackRecordStoreError):
        save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                    recorded_at=LATER)


def test_list_records_is_stable_and_filters_by_snapshot(tmp_path):
    one = save_record(tmp_path, kind="enrollment", document=enrollment("a" * 64), artifacts=artifacts(),
                      recorded_at=RECORDED_AT)["record"]
    other = enrollment("b" * 64) | {"forecast_identity": "forecast-2"}
    save_record(tmp_path, kind="enrollment", document=other, artifacts=artifacts(), recorded_at=LATER)
    mine = list_records(tmp_path, snapshot_id="a" * 64)
    assert [r["record_id"] for r in mine] == [one["record_id"]]
    assert list_records(tmp_path, snapshot_id="a" * 64) == mine  # stable across calls


def test_only_enrollment_and_grade_kinds_are_accepted(tmp_path):
    with pytest.raises(TrackRecordStoreError, match="kind"):
        save_record(tmp_path, kind="snapshot", document=enrollment(), artifacts={},
                    recorded_at=RECORDED_AT)


def test_a_grade_takes_its_snapshot_from_its_own_document_and_must_reference_a_real_enrollment(tmp_path):
    enrolled = save_record(tmp_path, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                           recorded_at=RECORDED_AT)["record"]
    grade = {
        "schema_version": "track_record.grade.v1",
        "snapshot_id": "a" * 64,
        "enrollment_id": enrolled["record_id"],
        "claim": "football_production",
        "decision_supported": False,
    }
    saved = save_record(tmp_path, kind="grade", document=grade, artifacts={}, recorded_at=LATER)
    assert saved["record"]["snapshot_id"] == "a" * 64

    dangling = grade | {"enrollment_id": "f" * 64}
    with pytest.raises(TrackRecordStoreError, match="enrollment"):
        save_record(tmp_path, kind="grade", document=dangling, artifacts={}, recorded_at=LATER)


def test_a_count_that_is_a_boolean_or_not_finite_refuses(tmp_path):
    for bad in ({"counts": {"eligible": True}}, {"value": float("nan")}, {"value": float("inf")}):
        with pytest.raises(TrackRecordStoreError):
            save_record(tmp_path, kind="enrollment", document=enrollment() | bad, artifacts={},
                        recorded_at=RECORDED_AT)


def test_an_unknown_schema_version_refuses(tmp_path):
    with pytest.raises(TrackRecordStoreError, match="schema_version"):
        save_record(tmp_path, kind="enrollment",
                    document=enrollment() | {"schema_version": "track_record.enrollment.v2"},
                    artifacts={}, recorded_at=RECORDED_AT)


def test_the_store_root_may_not_be_reached_through_a_symlink(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(TrackRecordStoreError, match="symlink"):
        save_record(link, kind="enrollment", document=enrollment(), artifacts=artifacts(),
                    recorded_at=RECORDED_AT)
