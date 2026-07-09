"""Phase-0b RED: scheduled market-source ownership and provenance.

These tests pin the David-ratified A-prime contract before GREEN:
the scheduled runner reads the owned FC PIT store, rejects source-owned freshness,
keys history by market snapshot date, and carries volatility-fidelity metadata
before any PIT history write.
"""
from __future__ import annotations

import importlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

NOW = datetime(2026, 7, 9, 13, 40, tzinfo=UTC)


@dataclass(frozen=True)
class _ResolvedPvo:
    source_kind: str
    pvo_path: Path
    coverage_path: Path
    source_as_of: str | None = "2026-07-09T13:30:00+00:00"
    ready: bool = True

    def metadata(self) -> dict[str, Any]:
        return {
            "pvo_source_kind": self.source_kind,
            "pvo_path": str(self.pvo_path),
            "coverage_path": str(self.coverage_path),
            "source_as_of": self.source_as_of,
            "ready": self.ready,
            "decision_supported": False,
        }


def _runner():
    return importlib.import_module("scripts.run_market_divergence_refresh")


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_latest_pair(tmp_path: Path) -> tuple[Path, Path]:
    latest = _write_json(
        tmp_path / "app/data/valuation/universe_market_divergence_latest.json",
        {
            "schema_version": "universe_market_divergence.v1",
            "captured_at": "2026-07-08T13:40:00+00:00",
            "players": [],
            "coverage": {"total_players": 0},
        },
    )
    coverage = _write_json(
        tmp_path
        / "app/data/valuation/universe_market_divergence_coverage_latest.json",
        {"total_players": 0},
    )
    return latest, coverage


def _write_pvo_pair(tmp_path: Path) -> tuple[Path, Path]:
    pvo = _write_json(
        tmp_path / "runtime_pvo.json",
        {
            "schema_version": "universe_pvo_batch.v1",
            "captured_at": "2026-07-09T13:30:00+00:00",
            "players": [
                {
                    "sleeper_player_id": "101",
                    "player": {"full_name": "Player One", "position": "WR"},
                    "valuation": {
                        "engine_path": "ENGINE_B",
                        "valuation_status": "MODEL_SUPPORTED",
                        "xvar": 72.0,
                    },
                }
            ],
        },
    )
    coverage = _write_json(tmp_path / "runtime_pvo_coverage.json", {"total_players": 1})
    return pvo, coverage


def _write_market_cache(path: Path, *, fetched_at: str, ttl_hours: int) -> Path:
    return _write_json(
        path,
        {
            "fetched_at": fetched_at,
            "ttl_hours": ttl_hours,
            "data": [
                {
                    "player": {
                        "sleeperId": "101",
                        "name": "Player One",
                        "position": "WR",
                    },
                    "value": 4400,
                    "positionRank": 12,
                    "overallRank": 21,
                    "maybeMovingStandardDeviation": 1.25,
                }
            ],
        },
    )


def _base_kwargs(tmp_path: Path) -> dict[str, Any]:
    latest, coverage = _write_latest_pair(tmp_path)
    pvo, pvo_coverage = _write_pvo_pair(tmp_path)
    cache = _write_market_cache(
        tmp_path / "app/cache/fantasycalc/market_values.json",
        fetched_at="2026-07-09T13:00:00Z",
        ttl_hours=24,
    )
    resolved = _ResolvedPvo("runtime", pvo, pvo_coverage)
    return {
        "latest_path": latest,
        "coverage_latest_path": coverage,
        "history_db_path": tmp_path / "app/data/market_divergence_history.db",
        "marker_path": tmp_path / "app/data/valuation_runtime/status.json",
        "report_path": tmp_path / "reports/refresh.json",
        "market_cache_path": cache,
        "resolve_pvo_source_fn": lambda **_: resolved,
        "now_fn": lambda: NOW,
    }


def _candidate(
    *,
    captured_at: str = "2026-07-09T13:40:00+00:00",
    market_snapshot_date: str = "2026-07-09",
    source_timestamp: str = "2026-07-09T13:00:00Z",
    include_volatility_status: bool = True,
) -> dict[str, Any]:
    overlay: dict[str, Any] = {
        "source": "fantasycalc",
        "market_value": 4400,
        "position_rank": 12,
        "overall_rank": 21,
        "market_volatility": None,
        "source_timestamp": source_timestamp,
        "caveats": ["source_timestamp_is_fetch_time_not_publish_time"],
    }
    if include_volatility_status:
        overlay["market_volatility_status"] = "structurally_unavailable"
    player_payload: dict[str, Any] = {
        "sleeper_player_id": "101",
        "market_overlay": overlay,
        "volatility_schema_effective_date": "2026-07-10",
        "divergence": {
            "signal": "MODEL_HIGH_MARKET_LOW",
            "signal_status": "gates_passed",
            "model_minus_market_delta": 0.25,
            "decision_supported": False,
        },
    }
    payload = {
        "schema_version": "universe_market_divergence.v1",
        "captured_at": captured_at,
        "market_snapshot_date": market_snapshot_date,
        "market_source_timestamp": source_timestamp,
        "volatility_schema_effective_date": "2026-07-10",
        "players": [player_payload],
        "coverage": {"total_players": 1, "decision_supported_true_count": 0},
    }
    if not include_volatility_status:
        payload.pop("volatility_schema_effective_date")
        player_payload.pop("volatility_schema_effective_date")
    return payload


def _init_fc_forward_db(db_path: Path, rows: list[dict[str, Any]]) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cols = (
        "snapshot_date TEXT, source TEXT, settings_hash TEXT, player_key TEXT, "
        "sleeper_id TEXT, player_name TEXT, position TEXT, value INTEGER, "
        "overall_rank INTEGER, position_rank INTEGER, trend_30day INTEGER, "
        "retrieved_at TEXT, payload_hash TEXT, market_volatility REAL, "
        "market_volatility_status TEXT"
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"CREATE TABLE fc_forward_capture_joinable ({cols})")
        for row in rows:
            conn.execute(
                "INSERT INTO fc_forward_capture_joinable VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["snapshot_date"],
                    row["source"],
                    row["settings_hash"],
                    row["player_key"],
                    row["sleeper_id"],
                    row["player_name"],
                    row["position"],
                    row["value"],
                    row["overall_rank"],
                    row["position_rank"],
                    row["trend_30day"],
                    row["retrieved_at"],
                    row["payload_hash"],
                    row["market_volatility"],
                    row["market_volatility_status"],
                ),
            )
    return db_path


def _init_pre_migration_fc_forward_db(
    db_path: Path, rows: list[dict[str, Any]]
) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cols = (
        "snapshot_date TEXT, source TEXT, settings_hash TEXT, player_key TEXT, "
        "sleeper_id TEXT, player_name TEXT, position TEXT, value INTEGER, "
        "overall_rank INTEGER, position_rank INTEGER, trend_30day INTEGER, "
        "retrieved_at TEXT, payload_hash TEXT"
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"CREATE TABLE fc_forward_capture_joinable ({cols})")
        for row in rows:
            conn.execute(
                "INSERT INTO fc_forward_capture_joinable VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["snapshot_date"],
                    row["source"],
                    row["settings_hash"],
                    row["player_key"],
                    row["sleeper_id"],
                    row["player_name"],
                    row["position"],
                    row["value"],
                    row["overall_rank"],
                    row["position_rank"],
                    row["trend_30day"],
                    row["retrieved_at"],
                    row["payload_hash"],
                ),
            )
    return db_path


def _fc_row(
    *,
    settings_hash: str = "settings-a",
    market_volatility: float | None = 1.25,
    market_volatility_status: str | None = "captured",
) -> dict[str, Any]:
    return {
        "snapshot_date": "2026-07-09",
        "source": "fc_native",
        "settings_hash": settings_hash,
        "player_key": "sleeper:101",
        "sleeper_id": "101",
        "player_name": "Player One",
        "position": "WR",
        "value": 4400,
        "overall_rank": 21,
        "position_rank": 12,
        "trend_30day": -15,
        "retrieved_at": "2026-07-09T13:00:00Z",
        "payload_hash": f"hash-{settings_hash}",
        "market_volatility": market_volatility,
        "market_volatility_status": market_volatility_status,
    }


def test_runner_reads_owned_fc_pit_rows_instead_of_orphan_cache(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    kwargs["market_cache_path"].unlink()
    fc_db = _init_fc_forward_db(tmp_path / "app/data/fc_forward_capture.db", [_fc_row()])
    captured: dict[str, Any] = {}

    def build_fn(pvo_batch, fc_response, *, fetch_caveats, captured_at, **meta):
        captured["fc_response"] = fc_response
        captured["fetch_caveats"] = fetch_caveats
        captured["captured_at"] = captured_at
        captured["meta"] = meta
        return _candidate(
            captured_at=captured_at,
            market_snapshot_date=meta["market_snapshot_date"],
            source_timestamp=meta["market_source_timestamp"],
            include_volatility_status=True,
        )

    report = runner.run_market_divergence_refresh(
        **kwargs,
        build_fn=build_fn,
        fc_forward_capture_db_path=fc_db,
        fc_source="fc_native",
        fc_settings_hash="settings-a",
    )

    assert report["status"] == "ok"
    assert report["market_source"]["status"] == "fresh_fc_forward_capture"
    assert report["market_source"]["snapshot_date"] == "2026-07-09"
    assert report["market_source"]["retrieved_at"] == "2026-07-09T13:00:00Z"
    assert captured["fc_response"] == [
        {
            "player": {"sleeperId": "101", "name": "Player One", "position": "WR"},
            "value": 4400,
            "overallRank": 21,
            "positionRank": 12,
            "trend30Day": -15,
            "maybeMovingStandardDeviation": 1.25,
            "marketVolatilityStatus": "captured",
        }
    ]
    assert captured["fetch_caveats"] == ["source_timestamp_is_fetch_time_not_publish_time"]
    assert captured["meta"]["market_snapshot_date"] == "2026-07-09"
    assert captured["meta"]["market_source_timestamp"] == "2026-07-09T13:00:00Z"


def test_payload_supplied_ttl_cannot_self_freshen_prior_date_cache(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    _write_market_cache(
        kwargs["market_cache_path"],
        fetched_at="2026-07-08T02:28:19Z",
        ttl_hours=99999,
    )
    original_latest = kwargs["latest_path"].read_bytes()

    def build_fn(*_args, **_kwargs):
        raise AssertionError("self-freshened market payload must not reach build")

    report = runner.run_market_divergence_refresh(**{**kwargs, "build_fn": build_fn})

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_source_prior_date"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert not kwargs["history_db_path"].exists()


def test_multiple_settings_hash_for_snapshot_aborts_on_ambiguity(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    fc_db = _init_fc_forward_db(
        tmp_path / "app/data/fc_forward_capture.db",
        [_fc_row(settings_hash="settings-a"), _fc_row(settings_hash="settings-b")],
    )
    original_latest = kwargs["latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(
        **kwargs,
        build_fn=lambda *_args, **_kwargs: _candidate(),
        fc_forward_capture_db_path=fc_db,
        fc_source="fc_native",
        fc_settings_hash=None,
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_source_ambiguous_settings_hash"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert not kwargs["history_db_path"].exists()


def test_pre_migration_fc_schema_reads_as_structurally_unavailable(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    kwargs["market_cache_path"].unlink()
    fc_db = _init_pre_migration_fc_forward_db(
        tmp_path / "app/data/fc_forward_capture.db", [_fc_row()]
    )
    captured: dict[str, Any] = {}

    def build_fn(pvo_batch, fc_response, *, fetch_caveats, captured_at, **meta):
        captured["fc_response"] = fc_response
        return _candidate(
            captured_at=captured_at,
            market_snapshot_date=meta["market_snapshot_date"],
            source_timestamp=meta["market_source_timestamp"],
            include_volatility_status=True,
        )

    report = runner.run_market_divergence_refresh(
        **kwargs,
        build_fn=build_fn,
        fc_forward_capture_db_path=fc_db,
        fc_source="fc_native",
        fc_settings_hash="settings-a",
    )

    assert report["status"] == "ok"
    assert {
        row["marketVolatilityStatus"] for row in captured["fc_response"]
    } == {"structurally_unavailable"}
    assert {row["maybeMovingStandardDeviation"] for row in captured["fc_response"]} == {
        None
    }


def test_corrupt_volatility_status_aborts_instead_of_structural_fallback(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    fc_db = _init_fc_forward_db(
        tmp_path / "app/data/fc_forward_capture.db",
        [_fc_row(market_volatility=None, market_volatility_status="silent_null")],
    )
    original_latest = kwargs["latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(
        **kwargs,
        build_fn=lambda *_args, **_kwargs: _candidate(),
        fc_forward_capture_db_path=fc_db,
        fc_source="fc_native",
        fc_settings_hash="settings-a",
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_source_volatility_status_invalid"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert not kwargs["history_db_path"].exists()


def test_incoherent_volatility_status_value_pair_aborts(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    fc_db = _init_fc_forward_db(
        tmp_path / "app/data/fc_forward_capture.db",
        [_fc_row(market_volatility=None, market_volatility_status="captured")],
    )
    original_latest = kwargs["latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(
        **kwargs,
        build_fn=lambda *_args, **_kwargs: _candidate(),
        fc_forward_capture_db_path=fc_db,
        fc_source="fc_native",
        fc_settings_hash="settings-a",
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_source_volatility_status_invalid"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert not kwargs["history_db_path"].exists()


def test_history_capture_date_uses_market_snapshot_date_not_runner_date() -> None:
    runner = _runner()

    capture_date = runner._capture_date(
        {
            "captured_at": "2026-07-09T23:40:00+00:00",
            "market_snapshot_date": "2026-07-08",
        },
        fallback_iso="2026-07-09T23:40:00+00:00",
    )

    assert capture_date == "2026-07-08"


def test_missing_volatility_fidelity_metadata_aborts_before_publish_or_history(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    original_latest = kwargs["latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(
        **{
            **kwargs,
            "build_fn": lambda *_args, **_kwargs: _candidate(
                include_volatility_status=False
            ),
        }
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "validation"
    assert report["aborted_reason"] == "market_volatility_fidelity_missing"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert not kwargs["history_db_path"].exists()


def test_regeneration_history_payload_is_self_describing_and_keyed_by_market_date(
    tmp_path: Path,
) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)

    report = runner.run_market_divergence_refresh(
        **{
            **kwargs,
            "build_fn": lambda *_args, **_kwargs: _candidate(
                captured_at="2026-07-09T13:40:00+00:00",
                market_snapshot_date="2026-07-08",
                source_timestamp="2026-07-08T02:28:19Z",
                include_volatility_status=True,
            ),
        }
    )

    assert report["status"] == "ok"
    with sqlite3.connect(kwargs["history_db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT capture_date, payload_json FROM market_divergence_history"
        ).fetchone()
    payload = json.loads(row["payload_json"])
    assert row["capture_date"] == "2026-07-08"
    assert payload["market_overlay"]["market_volatility_status"] == (
        "structurally_unavailable"
    )
    assert payload["volatility_schema_effective_date"] == "2026-07-10"
