"""Dual Daily PIT Capture T1 RED: dedicated FC forward-capture store.

T1 is storage/schema only. It deliberately does not exercise the FantasyCalc
HTTP client, retry policy, scheduler, or capture report writer; those belong to
T2/T3.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.dynasty_genius.capture.fc_forward_capture_store import (
    FCForwardCaptureConflictError,
    FCForwardCaptureStore,
    FCForwardCaptureValidationError,
)

SETTINGS_HASH = "sf_ppr_12"
SOURCE = "fc_native"
SNAPSHOT_DATE = "2026-06-24"
RETRIEVED_AT = "2026-06-24T13:15:00+00:00"


def _entry(
    *,
    player_key: str = "sleeper:9509",
    sleeper_id: str | None = "9509",
    player_name: str = "Bijan Robinson",
    position: str = "RB",
    value: int = 10500,
    overall_rank: int = 1,
    position_rank: int = 1,
    payload_hash: str = "hash-bijan-v1",
    source: str = SOURCE,
    settings_hash: str = SETTINGS_HASH,
    market_volatility: float | None = 0.0,
    market_volatility_status: str = "captured",
) -> dict:
    return {
        "snapshot_date": SNAPSHOT_DATE,
        "source": source,
        "settings_hash": settings_hash,
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "player_name": player_name,
        "position": position,
        "value": value,
        "overall_rank": overall_rank,
        "position_rank": position_rank,
        "trend_30day": -50,
        "retrieved_at": RETRIEVED_AT,
        "payload_hash": payload_hash,
        "market_volatility": market_volatility,
        "market_volatility_status": market_volatility_status,
    }


def _three_entries() -> list[dict]:
    return [
        _entry(),
        _entry(
            player_key="fc:2",
            sleeper_id=None,
            player_name="No Sleeper ID",
            position="WR",
            value=5000,
            overall_rank=50,
            position_rank=10,
            payload_hash="hash-no-sleeper-v1",
        ),
        _entry(
            player_key="sleeper:6786",
            sleeper_id="6786",
            player_name="CeeDee Lamb",
            position="WR",
            value=9000,
            overall_rank=5,
            position_rank=1,
            payload_hash="hash-ceedee-v1",
        ),
    ]


def test_dedicated_namespace_persists_raw_sidecar_and_joinable_view(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")

    result = store.append_entries(_three_entries())

    assert result == {"raw_entries_written": 3, "joinable_rows_written": 2}

    raw = store.get_raw_entries(
        snapshot_date=SNAPSHOT_DATE,
        source=SOURCE,
        settings_hash=SETTINGS_HASH,
    )
    assert len(raw) == 3
    assert {row["player_key"] for row in raw} == {
        "sleeper:9509",
        "fc:2",
        "sleeper:6786",
    }
    assert [row for row in raw if row["sleeper_id"] is None] == [
        {
            **raw[1],
            "player_key": "fc:2",
            "sleeper_id": None,
            "player_name": "No Sleeper ID",
        }
    ]

    joinable = store.get_joinable_entries(
        snapshot_date=SNAPSHOT_DATE,
        source=SOURCE,
        settings_hash=SETTINGS_HASH,
    )
    assert len(joinable) == 2
    assert {row["sleeper_id"] for row in joinable} == {"9509", "6786"}
    assert all(row["source"] == SOURCE for row in joinable)
    assert all(row["settings_hash"] == SETTINGS_HASH for row in joinable)


def test_schema_is_source_aware_and_does_not_mutate_legacy_fc_snapshots(tmp_path) -> None:
    db_path = tmp_path / "forward.db"
    store = FCForwardCaptureStore(db_path=db_path)
    store.append_entries(_three_entries())

    with sqlite3.connect(db_path) as conn:
        raw_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(fc_forward_capture_raw)")
        }
        joinable_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(fc_forward_capture_joinable)")
        }
        legacy_tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fc_snapshots'"
            )
        ]

    assert {"snapshot_date", "source", "settings_hash", "player_key"} <= raw_columns
    assert {"snapshot_date", "source", "settings_hash", "player_key"} <= joinable_columns
    assert legacy_tables == []


def test_identical_rewrite_is_idempotent_changed_value_conflicts(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")

    assert store.append_entries(_three_entries()) == {
        "raw_entries_written": 3,
        "joinable_rows_written": 2,
    }
    assert store.append_entries(_three_entries()) == {
        "raw_entries_written": 3,
        "joinable_rows_written": 2,
    }

    changed = _three_entries()
    changed[0] = {**changed[0], "value": 10600, "payload_hash": "hash-bijan-v2"}
    with pytest.raises(FCForwardCaptureConflictError, match="immutable snapshot conflict"):
        store.append_entries(changed)

    rows = store.get_joinable_entries(
        snapshot_date=SNAPSHOT_DATE,
        source=SOURCE,
        settings_hash=SETTINGS_HASH,
    )
    assert {row["value"] for row in rows} == {10500, 9000}


def test_duplicate_player_key_in_payload_conflicts_unless_byte_identical(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    duplicate_same = _three_entries() + [_three_entries()[0]]

    assert store.append_entries(duplicate_same) == {
        "raw_entries_written": 3,
        "joinable_rows_written": 2,
    }

    duplicate_changed = _three_entries() + [
        {
            **_three_entries()[0],
            "value": 10600,
            "payload_hash": "hash-bijan-v2",
        }
    ]
    with pytest.raises(FCForwardCaptureValidationError, match="duplicate player_key"):
        store.append_entries(duplicate_changed)


def test_no_sleeper_row_is_stored_and_counted_never_dropped_or_abort(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    no_sleeper_only = [
        _entry(
            player_key="fc:2",
            sleeper_id=None,
            player_name="No Sleeper ID",
            position="WR",
            value=5000,
            payload_hash="hash-no-sleeper-v1",
        )
    ]

    assert store.append_entries(no_sleeper_only) == {
        "raw_entries_written": 1,
        "joinable_rows_written": 0,
    }
    assert len(store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH)) == 1
    assert store.get_joinable_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []


def test_missing_stable_player_key_fails_closed_before_any_write(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    malformed = [{**_three_entries()[0], "player_key": ""}]

    with pytest.raises(FCForwardCaptureValidationError, match="stable player_key"):
        store.append_entries(malformed)

    assert store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []
    assert store.get_joinable_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []


def test_second_source_family_in_fc_namespace_rejected(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    mixed_source = [_three_entries()[0], _entry(source="dp_archive", player_key="dp:1")]

    with pytest.raises(FCForwardCaptureValidationError, match="single source family"):
        store.append_entries(mixed_source)

    assert store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []


def test_single_non_fc_source_family_is_rejected_by_append(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    non_fc_batch = [
        _entry(
            source="dp_archive",
            player_key="dp:1",
            sleeper_id="1",
            payload_hash="hash-dp-v1",
        )
    ]

    with pytest.raises(FCForwardCaptureValidationError, match="fc_native"):
        store.append_entries(non_fc_batch)

    assert store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []


def test_assert_single_source_family_rejects_non_fc_namespace(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")

    store.assert_single_source_family(SOURCE)
    with pytest.raises(FCForwardCaptureValidationError, match="fc_native"):
        store.assert_single_source_family("ktc_community_csv")


def test_changed_immutable_field_conflicts_even_if_payload_hash_matches(
    tmp_path,
) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")
    store.append_entries([_entry(value=10500, payload_hash="same-hash")])

    with pytest.raises(FCForwardCaptureConflictError, match="immutable snapshot conflict"):
        store.append_entries([_entry(value=10600, payload_hash="same-hash")])

    rows = store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH)
    assert len(rows) == 1
    assert rows[0]["value"] == 10500


def test_phase0b_volatility_status_columns_are_persisted_and_typed(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")

    with sqlite3.connect(tmp_path / "forward.db") as conn:
        raw_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(fc_forward_capture_raw)")
        }
        joinable_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(fc_forward_capture_joinable)")
        }

    assert {"market_volatility", "market_volatility_status"} <= raw_columns
    assert {"market_volatility", "market_volatility_status"} <= joinable_columns

    store.append_entries(
        [
            _entry(market_volatility=1.25, market_volatility_status="captured"),
            _entry(
                player_key="sleeper:6786",
                sleeper_id="6786",
                player_name="CeeDee Lamb",
                position="WR",
                value=9000,
                overall_rank=5,
                position_rank=1,
                payload_hash="hash-ceedee-v1",
                market_volatility=None,
                market_volatility_status="source_omitted",
            ),
        ]
    )

    rows = store.get_joinable_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH)
    by_id = {row["sleeper_id"]: row for row in rows}
    assert by_id["9509"]["market_volatility"] == 1.25
    assert by_id["9509"]["market_volatility_status"] == "captured"
    assert by_id["6786"]["market_volatility"] is None
    assert by_id["6786"]["market_volatility_status"] == "source_omitted"


def test_phase0b_volatility_status_enum_fails_closed_before_write(tmp_path) -> None:
    store = FCForwardCaptureStore(db_path=tmp_path / "forward.db")

    with pytest.raises(FCForwardCaptureValidationError, match="market_volatility_status"):
        store.append_entries(
            [_entry(market_volatility=None, market_volatility_status="silent_null")]
        )

    assert store.get_raw_entries(SNAPSHOT_DATE, SOURCE, SETTINGS_HASH) == []
