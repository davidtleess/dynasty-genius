"""Model-output forward-capture T1 RED: dedicated PIT store.

T1 is storage/schema only. It deliberately does not read PVO artifacts, resolve
model provenance, compute semantic hashes, refresh PVO, or write capture
reports; those belong to T2+.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureConflictError,
    ModelForwardCaptureStore,
    ModelForwardCaptureValidationError,
    build_model_player_key,
)

CAPTURE_DATE = "2026-06-24"
SOURCE = MODEL_PVO_SOURCE
SEMANTIC_OUTPUT_HASH = "semantic-output-v1"
PROVENANCE_HASH = "provenance-v1"
ARTIFACT_VINTAGE = "2026-06-24T14:00:00+00:00"


def _entry(
    *,
    player_key: str = "sleeper:9509",
    sleeper_id: str | None = "9509",
    dg_player_id: str | None = "dg_bijan",
    player_name: str = "Bijan Robinson",
    position: str = "RB",
    engine_path: str = "ENGINE_B",
    dynasty_value_score: float | None = 98.5,
    dvs_pct: float | None = 99.2,
    xvar: float | None = 21.4,
    model_grade: str | None = "A",
    model_version: str | None = "engine_b_v2",
    row_index: int = 0,
    semantic_row_hash: str = "row-bijan-v1",
    payload_hash: str = "payload-bijan-v1",
    source: str = SOURCE,
    semantic_output_hash: str = SEMANTIC_OUTPUT_HASH,
    provenance_hash: str = PROVENANCE_HASH,
) -> dict:
    return {
        "capture_date": CAPTURE_DATE,
        "source": source,
        "semantic_output_hash": semantic_output_hash,
        "provenance_hash": provenance_hash,
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "dg_player_id": dg_player_id,
        "player_name": player_name,
        "position": position,
        "engine_path": engine_path,
        "dynasty_value_score": dynasty_value_score,
        "dvs_pct": dvs_pct,
        "xvar": xvar,
        "model_grade": model_grade,
        "model_version": model_version,
        "artifact_vintage": ARTIFACT_VINTAGE,
        "row_index": row_index,
        "semantic_row_hash": semantic_row_hash,
        "payload_hash": payload_hash,
    }


def _entries() -> list[dict]:
    return [
        _entry(),
        _entry(
            player_key="sleeper:6786",
            sleeper_id="6786",
            dg_player_id="dg_ceedee",
            player_name="CeeDee Lamb",
            position="WR",
            engine_path="ENGINE_A",
            dynasty_value_score=95.1,
            dvs_pct=97.4,
            xvar=18.2,
            model_grade="A-",
            model_version="engine_a_v2",
            row_index=1,
            semantic_row_hash="row-ceedee-v1",
            payload_hash="payload-ceedee-v1",
        ),
        _entry(
            player_key="dg:dg_pre_model",
            sleeper_id=None,
            dg_player_id="dg_pre_model",
            player_name="Non-model Row",
            position="RB",
            engine_path="PRE_MODEL",
            dynasty_value_score=None,
            dvs_pct=None,
            xvar=None,
            model_grade=None,
            model_version=None,
            row_index=2,
            semantic_row_hash="row-premodel-v1",
            payload_hash="payload-premodel-v1",
        ),
        _entry(
            player_key="unresolved:semantic-output-v1:3:row-unresolved-v1",
            sleeper_id=None,
            dg_player_id=None,
            player_name="Unresolved Identity",
            position=None,
            engine_path="UNRESOLVED_IDENTITY",
            dynasty_value_score=None,
            dvs_pct=None,
            xvar=None,
            model_grade=None,
            model_version=None,
            row_index=3,
            semantic_row_hash="row-unresolved-v1",
            payload_hash="payload-unresolved-v1",
        ),
    ]


def test_player_key_fallback_rejects_pseudo_sleeper_zero_and_uses_stable_semantic_hashes() -> None:
    sleeper_key = build_model_player_key(
        {
            "identity_ids": {"sleeper_id": "9509"},
            "sleeper_player_id": "0",
            "dg_player_id": "dg_bijan",
        },
        semantic_output_hash=SEMANTIC_OUTPUT_HASH,
        row_index=0,
        semantic_row_hash="row-bijan-v1",
    )
    dg_key = build_model_player_key(
        {
            "identity_ids": {"sleeper_id": "0"},
            "sleeper_player_id": "0",
            "dg_player_id": "dg_only",
        },
        semantic_output_hash=SEMANTIC_OUTPUT_HASH,
        row_index=1,
        semantic_row_hash="row-dg-v1",
    )
    unresolved_key = build_model_player_key(
        {
            "identity_ids": {"sleeper_id": "0"},
            "sleeper_player_id": "",
            "dg_player_id": None,
        },
        semantic_output_hash=SEMANTIC_OUTPUT_HASH,
        row_index=2,
        semantic_row_hash="row-unresolved-v1",
    )

    assert sleeper_key == "sleeper:9509"
    assert dg_key == "dg:dg_only"
    assert unresolved_key == (
        "unresolved:semantic-output-v1:2:row-unresolved-v1"
    )
    assert "artifact" not in unresolved_key
    assert sleeper_key != "sleeper:0"


def test_persists_survivorship_complete_raw_and_sleeper_keyed_joinable(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")

    result = store.append_entries(_entries())

    assert result == {"raw_rows_written": 4, "joinable_rows_written": 2}

    raw = store.get_raw_entries(
        capture_date=CAPTURE_DATE,
        source=SOURCE,
        semantic_output_hash=SEMANTIC_OUTPUT_HASH,
        provenance_hash=PROVENANCE_HASH,
    )
    assert len(raw) == 4
    assert {row["player_key"] for row in raw} == {
        "sleeper:9509",
        "sleeper:6786",
        "dg:dg_pre_model",
        "unresolved:semantic-output-v1:3:row-unresolved-v1",
    }
    assert {row["engine_path"] for row in raw} == {
        "ENGINE_A",
        "ENGINE_B",
        "PRE_MODEL",
        "UNRESOLVED_IDENTITY",
    }

    joinable = store.get_joinable_entries(
        capture_date=CAPTURE_DATE,
        source=SOURCE,
        semantic_output_hash=SEMANTIC_OUTPUT_HASH,
        provenance_hash=PROVENANCE_HASH,
    )
    assert len(joinable) == 2
    assert {row["engine_path"] for row in joinable} == {"ENGINE_A", "ENGINE_B"}
    assert {row["sleeper_id"] for row in joinable} == {"9509", "6786"}
    assert all(row["player_key"].startswith("sleeper:") for row in joinable)


def test_schema_uses_parallel_model_namespace_and_composite_key(tmp_path) -> None:
    db_path = tmp_path / "model_forward.db"
    store = ModelForwardCaptureStore(db_path=db_path)
    store.append_entries(_entries())

    with sqlite3.connect(db_path) as conn:
        raw_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(model_forward_capture_raw)")
        }
        joinable_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(model_forward_capture_joinable)"
            )
        }
        legacy_or_fc_tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name IN ("
                "'fc_forward_capture_raw', 'fc_snapshots', 'market_snapshots'"
                ")"
            )
        ]

    expected_key_columns = {
        "capture_date",
        "source",
        "semantic_output_hash",
        "provenance_hash",
        "player_key",
    }
    assert expected_key_columns <= raw_columns
    assert expected_key_columns <= joinable_columns
    assert "artifact_sha256" not in raw_columns
    assert legacy_or_fc_tables == []


def test_identical_reappend_is_idempotent_changed_existing_key_conflicts(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")

    assert store.append_entries(_entries()) == {
        "raw_rows_written": 4,
        "joinable_rows_written": 2,
    }
    assert store.append_entries(_entries()) == {
        "raw_rows_written": 4,
        "joinable_rows_written": 2,
    }

    changed = _entries()
    changed[0] = {
        **changed[0],
        "dynasty_value_score": 99.9,
        "payload_hash": "payload-bijan-v2",
    }
    with pytest.raises(
        ModelForwardCaptureConflictError, match="immutable snapshot conflict"
    ):
        store.append_entries(changed)

    rows = store.get_joinable_entries(
        CAPTURE_DATE, SOURCE, SEMANTIC_OUTPUT_HASH, PROVENANCE_HASH
    )
    assert {row["dynasty_value_score"] for row in rows} == {98.5, 95.1}


def test_same_day_reappend_with_only_new_artifact_vintage_is_idempotent(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")

    assert store.append_entries(_entries()) == {
        "raw_rows_written": 4,
        "joinable_rows_written": 2,
    }

    rerun_same_model_vintage = [
        {
            **entry,
            "artifact_vintage": "2026-06-24T15:30:00+00:00",
        }
        for entry in _entries()
    ]
    assert store.append_entries(rerun_same_model_vintage) == {
        "raw_rows_written": 4,
        "joinable_rows_written": 2,
    }

    raw = store.get_raw_entries(
        CAPTURE_DATE, SOURCE, SEMANTIC_OUTPUT_HASH, PROVENANCE_HASH
    )
    assert len(raw) == 4
    assert {row["artifact_vintage"] for row in raw} == {ARTIFACT_VINTAGE}

    changed_score_same_key = [
        {
            **entry,
            "artifact_vintage": "2026-06-24T16:00:00+00:00",
            "dynasty_value_score": 99.9,
        }
        if entry["player_key"] == "sleeper:9509"
        else entry
        for entry in _entries()
    ]
    with pytest.raises(
        ModelForwardCaptureConflictError, match="immutable snapshot conflict"
    ):
        store.append_entries(changed_score_same_key)


def test_duplicate_player_key_in_batch_conflicts_unless_byte_identical(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")
    duplicate_same = _entries() + [_entries()[0]]

    assert store.append_entries(duplicate_same) == {
        "raw_rows_written": 4,
        "joinable_rows_written": 2,
    }

    duplicate_changed = _entries() + [
        {**_entries()[0], "dynasty_value_score": 99.9}
    ]
    with pytest.raises(ModelForwardCaptureValidationError, match="duplicate player_key"):
        store.append_entries(duplicate_changed)


def test_missing_key_or_mixed_source_fails_closed_before_any_write(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")

    with pytest.raises(ModelForwardCaptureValidationError, match="stable player_key"):
        store.append_entries([{**_entries()[0], "player_key": ""}])
    with pytest.raises(ModelForwardCaptureValidationError, match="single source family"):
        store.append_entries(
            [_entries()[0], {**_entries()[1], "source": "fc_native"}]
        )

    assert store.get_raw_entries(
        CAPTURE_DATE, SOURCE, SEMANTIC_OUTPUT_HASH, PROVENANCE_HASH
    ) == []


@pytest.mark.parametrize(
    ("column", "bad_value"),
    [
        ("capture_date", ""),
        ("semantic_output_hash", None),
        ("provenance_hash", ""),
    ],
)
def test_missing_composite_key_field_fails_closed_before_any_write(
    tmp_path, column: str, bad_value: object
) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")

    with pytest.raises(ModelForwardCaptureValidationError, match="composite key"):
        store.append_entries([{**_entries()[0], column: bad_value}])

    assert store.get_raw_entries(
        CAPTURE_DATE, SOURCE, SEMANTIC_OUTPUT_HASH, PROVENANCE_HASH
    ) == []


def test_single_non_model_pvo_source_family_is_rejected(tmp_path) -> None:
    store = ModelForwardCaptureStore(db_path=tmp_path / "model_forward.db")
    non_model_batch = [{**_entries()[0], "source": "fc_native"}]

    with pytest.raises(ModelForwardCaptureValidationError, match="model_pvo"):
        store.append_entries(non_model_batch)

    store.assert_single_source_family(SOURCE)
    with pytest.raises(ModelForwardCaptureValidationError, match="model_pvo"):
        store.assert_single_source_family("fc_native")
