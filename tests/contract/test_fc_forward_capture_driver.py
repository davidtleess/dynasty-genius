"""Dual Daily PIT Capture T2 RED: FantasyCalc capture driver.

T2 is the script/driver layer over the T1 store. Network, sleep, jitter, and time
are injectable so these tests do not touch the real FantasyCalc endpoint.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from src.dynasty_genius.capture.fc_forward_capture_driver import (
    FC_ENDPOINT,
    SETTINGS_HASH,
    capture_fantasycalc_snapshot,
    map_fantasycalc_payload_to_entries,
)
from src.dynasty_genius.capture.fc_forward_capture_store import (
    FCForwardCaptureStore,
)


def _fixed_now() -> datetime:
    return datetime(2026, 6, 24, 13, 15, 0, tzinfo=timezone.utc)


def _payload() -> list[dict]:
    return [
        {
            "player": {
                "id": 1,
                "name": "Bijan Robinson",
                "sleeperId": "9509",
                "position": "RB",
            },
            "value": 10500,
            "overallRank": 1,
            "positionRank": 1,
            "trend30Day": -50,
        },
        {
            "player": {
                "id": 2,
                "name": "No Sleeper ID",
                "sleeperId": None,
                "position": "WR",
            },
            "value": 5000,
            "overallRank": 50,
            "positionRank": 10,
            "trend30Day": 0,
        },
        {
            "player": {
                "id": 3,
                "name": "CeeDee Lamb",
                "sleeperId": "6786",
                "position": "WR",
            },
            "value": 9000,
            "overallRank": 5,
            "positionRank": 1,
            "trend30Day": 100,
        },
    ]


class _Response:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> object:
        return self._body


def test_maps_payload_to_t1_entries_with_stable_keys_and_hashes() -> None:
    entries = map_fantasycalc_payload_to_entries(
        _payload(),
        retrieved_at=_fixed_now(),
    )

    assert len(entries) == 3
    assert entries[0]["player_key"] == "sleeper:9509"
    assert entries[0]["sleeper_id"] == "9509"
    assert entries[0]["snapshot_date"] == "2026-06-24"
    assert entries[0]["retrieved_at"] == "2026-06-24T13:15:00+00:00"
    assert entries[0]["source"] == "fc_native"
    assert entries[0]["settings_hash"] == SETTINGS_HASH
    assert entries[0]["payload_hash"]
    assert entries[1]["player_key"] == "fc:2"
    assert entries[1]["sleeper_id"] is None


def test_successful_capture_appends_to_t1_store_and_writes_aggregate_report(
    tmp_path,
) -> None:
    db_path = tmp_path / "capture.db"
    report_path = tmp_path / "capture_report.json"

    report = capture_fantasycalc_snapshot(
        db_path=db_path,
        report_path=report_path,
        fetch_json=lambda url: _payload(),
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert report["status"] == "ok"
    assert report["snapshot_date"] == "2026-06-24"
    assert report["retrieved_at"] == "2026-06-24T13:15:00+00:00"
    assert report["source"] == "fc_native"
    assert report["settings_hash"] == SETTINGS_HASH
    assert report["endpoint"] == FC_ENDPOINT
    assert report["raw_entries_written"] == 3
    assert report["joinable_rows_written"] == 2
    assert report["missing_sleeper_count"] == 1
    assert report["duplicate_count"] == 0
    assert report["payload_hash"]
    assert report["store_hash"]
    assert report["aborted_reason"] is None
    assert report["decision_supported"] is False

    persisted = json.loads(report_path.read_text())
    assert persisted == report
    assert "Bijan Robinson" not in report_path.read_text()
    assert "CeeDee Lamb" not in report_path.read_text()

    store = FCForwardCaptureStore(db_path)
    assert len(store.get_raw_entries("2026-06-24", "fc_native", SETTINGS_HASH)) == 3
    assert len(store.get_joinable_entries("2026-06-24", "fc_native", SETTINGS_HASH)) == 2


def test_transient_429_retries_then_succeeds_without_partial_write(tmp_path) -> None:
    db_path = tmp_path / "capture.db"
    attempts: list[str] = []
    sleeps: list[float] = []
    responses = iter([
        _Response(429, {"error": "rate limited"}),
        _Response(500, {"error": "server"}),
        _Response(200, {"players": _payload()}),
    ])

    def fetch_json(url: str) -> object:
        attempts.append(url)
        response = next(responses)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                "transient",
                request=httpx.Request("GET", url),
                response=httpx.Response(response.status_code),
            )
        return response.json()

    report = capture_fantasycalc_snapshot(
        db_path=db_path,
        fetch_json=fetch_json,
        now_fn=_fixed_now,
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 0.0,
    )

    assert len(attempts) == 3
    assert sleeps == [1.0, 2.0]
    assert report["status"] == "ok"
    assert report["raw_entries_written"] == 3


def test_retry_exhaustion_writes_aborted_report_and_no_store_rows(tmp_path) -> None:
    db_path = tmp_path / "capture.db"
    report_path = tmp_path / "capture_report.json"
    attempts = 0

    def fetch_json(url: str) -> object:
        nonlocal attempts
        attempts += 1
        raise httpx.TimeoutException("timeout", request=httpx.Request("GET", url))

    report = capture_fantasycalc_snapshot(
        db_path=db_path,
        report_path=report_path,
        fetch_json=fetch_json,
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert attempts == 3
    assert report["status"] == "aborted"
    assert "retry_exhausted" in report["aborted_reason"]
    assert report["raw_entries_written"] == 0
    assert report["joinable_rows_written"] == 0
    assert report["decision_supported"] is False
    assert json.loads(report_path.read_text()) == report

    store = FCForwardCaptureStore(db_path)
    assert store.get_raw_entries("2026-06-24", "fc_native", SETTINGS_HASH) == []


def test_fatal_404_and_malformed_or_empty_payload_abort_without_retry_or_write(
    tmp_path,
) -> None:
    cases = [
        (
            lambda _url: (_ for _ in ()).throw(
                httpx.HTTPStatusError(
                    "not found",
                    request=httpx.Request("GET", FC_ENDPOINT),
                    response=httpx.Response(404),
                )
            ),
            "fatal_http_404",
        ),
        (lambda _url: {"unexpected": []}, "malformed_payload"),
        (lambda _url: {"players": []}, "empty_payload"),
    ]

    for fetch_json, expected_reason in cases:
        db_path = tmp_path / f"{expected_reason}.db"
        report = capture_fantasycalc_snapshot(
            db_path=db_path,
            fetch_json=fetch_json,
            now_fn=_fixed_now,
            sleep_fn=lambda _: None,
            jitter_fn=lambda: 0.0,
        )
        assert report["status"] == "aborted"
        assert expected_reason in report["aborted_reason"]
        assert report["raw_entries_written"] == 0
        assert report["joinable_rows_written"] == 0
        assert FCForwardCaptureStore(db_path).get_raw_entries(
            "2026-06-24",
            "fc_native",
            SETTINGS_HASH,
        ) == []


def test_malformed_player_row_aborts_without_exception_or_write(tmp_path) -> None:
    db_path = tmp_path / "malformed_row.db"
    report_path = tmp_path / "malformed_row_report.json"
    payload = [{"player": {"name": "No Stable Key"}, "value": 1}]

    report = capture_fantasycalc_snapshot(
        db_path=db_path,
        report_path=report_path,
        fetch_json=lambda _url: payload,
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert report["status"] == "aborted"
    assert "malformed_payload" in report["aborted_reason"]
    assert report["raw_entries_written"] == 0
    assert report["joinable_rows_written"] == 0
    assert report["decision_supported"] is False
    assert json.loads(report_path.read_text()) == report
    assert FCForwardCaptureStore(db_path).get_raw_entries(
        "2026-06-24",
        "fc_native",
        SETTINGS_HASH,
    ) == []


def test_store_conflict_surfaces_as_aborted_report_without_overwrite(tmp_path) -> None:
    db_path = tmp_path / "capture.db"
    capture_fantasycalc_snapshot(
        db_path=db_path,
        fetch_json=lambda _url: _payload(),
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )
    changed = _payload()
    changed[0]["value"] = 10600

    report = capture_fantasycalc_snapshot(
        db_path=db_path,
        fetch_json=lambda _url: changed,
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert report["status"] == "aborted"
    assert "immutable snapshot conflict" in report["aborted_reason"]
    assert report["raw_entries_written"] == 0
    assert report["joinable_rows_written"] == 0

    rows = FCForwardCaptureStore(db_path).get_joinable_entries(
        "2026-06-24",
        "fc_native",
        SETTINGS_HASH,
    )
    assert {row["value"] for row in rows} == {10500, 9000}


def test_same_day_identical_capture_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "capture.db"

    first = capture_fantasycalc_snapshot(
        db_path=db_path,
        fetch_json=lambda _url: _payload(),
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )
    second = capture_fantasycalc_snapshot(
        db_path=db_path,
        fetch_json=lambda _url: _payload(),
        now_fn=_fixed_now,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert second["raw_entries_written"] == 3
    assert second["joinable_rows_written"] == 2
