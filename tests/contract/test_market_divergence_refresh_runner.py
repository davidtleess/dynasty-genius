"""Phase 0 RED: daily market-divergence refresh runner.

The scheduled job must turn the already-captured daily market/PVO state into a fresh
divergence latest pair and a compounding PIT history without live network, stale-as-fresh,
or partial latest writes.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.pvo_source import PvoSourceNotReadyError

NOW = datetime(2026, 7, 8, 13, 40, tzinfo=UTC)


@dataclass(frozen=True)
class _ResolvedPvo:
    source_kind: str
    pvo_path: Path
    coverage_path: Path
    source_as_of: str | None = "2026-07-08T13:30:00+00:00"
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


def _load_runner():
    try:
        return importlib.import_module("scripts.run_market_divergence_refresh")
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "Expected scripts/run_market_divergence_refresh.py for the Phase 0 "
            "daily margin recompute runner."
        ) from exc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _write_latest_pair(tmp_path: Path, *, suffix: str = "old") -> tuple[Path, Path]:
    latest = tmp_path / "app/data/valuation/universe_market_divergence_latest.json"
    coverage = (
        tmp_path
        / "app/data/valuation/universe_market_divergence_coverage_latest.json"
    )
    _write_json(
        latest,
        {
            "schema_version": "universe_market_divergence.v1",
            "captured_at": f"2026-07-07T13:40:00+00:00-{suffix}",
            "players": [],
            "coverage": {"total_players": 0, "decision_supported_true_count": 0},
        },
    )
    _write_json(
        coverage,
        {"total_players": 0, "decision_supported_true_count": 0, "suffix": suffix},
    )
    return latest, coverage


def _write_pvo_pair(tmp_path: Path, *, suffix: str = "runtime") -> tuple[Path, Path]:
    pvo = tmp_path / f"{suffix}_pvo.json"
    coverage = tmp_path / f"{suffix}_pvo_coverage.json"
    _write_json(
        pvo,
        {
            "schema_version": "universe_pvo_batch.v1",
            "captured_at": f"2026-07-08T13:30:00+00:00-{suffix}",
            "players": [
                {
                    "sleeper_player_id": "101",
                    "player": {"full_name": "Player One", "position": "WR"},
                    "valuation": {
                        "engine_path": "ENGINE_B",
                        "valuation_status": "MODEL_SUPPORTED",
                        "xvar": 72.0,
                    },
                },
                {
                    "sleeper_player_id": "202",
                    "player": {"full_name": "Player Two", "position": "RB"},
                    "valuation": {
                        "engine_path": "ENGINE_B",
                        "valuation_status": "MODEL_SUPPORTED",
                        "xvar": 41.0,
                    },
                },
            ],
        },
    )
    _write_json(coverage, {"total_players": 2, "decision_supported_true_count": 0})
    return pvo, coverage


def _write_fresh_market_cache(cache_path: Path) -> Path:
    return _write_json(
        cache_path,
        {
            "fetched_at": "2026-07-08T13:00:00Z",
            "ttl_hours": 24,
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
                },
                {
                    "player": {
                        "sleeperId": "202",
                        "name": "Player Two",
                        "position": "RB",
                    },
                    "value": 3100,
                    "positionRank": 18,
                    "overallRank": 48,
                },
            ],
        },
    )


def _write_stale_market_cache(cache_path: Path) -> Path:
    payload = json.loads(_write_fresh_market_cache(cache_path).read_text())
    payload["fetched_at"] = "2026-07-06T09:00:00Z"
    return _write_json(cache_path, payload)


def _divergence_batch(
    *,
    captured_at: str = "2026-07-08T13:40:00+00:00",
    stale_market: bool = False,
    delta_one: float = 0.25,
) -> dict[str, Any]:
    stale_notes = ["stale_market_data"] if stale_market else []
    rows = [
        {
            "sleeper_player_id": "101",
            "player": {"full_name": "Player One", "position": "WR"},
            "market_overlay": {
                "source": "fantasycalc",
                "source_timestamp": "2026-07-08T13:00:00Z",
                "position_rank": 12,
                "market_volatility": None,
                "market_volatility_status": "source_omitted",
                "caveats": ["source_timestamp_is_fetch_time_not_publish_time"]
                + stale_notes,
            },
            "volatility_schema_effective_date": "2026-07-08",
            "divergence": {
                "signal": (
                    "SUPPRESSED_STALE_MARKET"
                    if stale_market
                    else "MODEL_HIGH_MARKET_LOW"
                ),
                "signal_status": "gates_blocked" if stale_market else "gates_passed",
                "model_percentile": 0.75,
                "market_percentile": 0.50,
                "model_minus_market_delta": delta_one,
                "failed_gates": stale_notes,
                "notes": stale_notes,
                "decision_supported": False,
            },
        },
        {
            "sleeper_player_id": "202",
            "player": {"full_name": "Player Two", "position": "RB"},
            "market_overlay": {
                "source": "fantasycalc",
                "source_timestamp": "2026-07-08T13:00:00Z",
                "position_rank": 18,
                "market_volatility": None,
                "market_volatility_status": "source_omitted",
                "caveats": ["source_timestamp_is_fetch_time_not_publish_time"]
                + stale_notes,
            },
            "volatility_schema_effective_date": "2026-07-08",
            "divergence": {
                "signal": "INSIDE_BAND",
                "signal_status": "inside_band",
                "model_percentile": 0.52,
                "market_percentile": 0.50,
                "model_minus_market_delta": 0.02,
                "failed_gates": stale_notes,
                "notes": stale_notes,
                "decision_supported": False,
            },
        },
    ]
    return {
        "schema_version": "universe_market_divergence.v1",
        "captured_at": captured_at,
        "market_snapshot_date": "2026-07-08",
        "market_source_timestamp": "2026-07-08T13:00:00Z",
        "volatility_schema_effective_date": "2026-07-08",
        "players": rows,
        "coverage": {
            "total_players": len(rows),
            "market_overlay_present_count": len(rows),
            "decision_supported_true_count": 0,
            "banned_language_present": [],
            "signal_status_counts": {"gates_passed": 1, "inside_band": 1},
            "signals_by_type": {"INSIDE_BAND": 1, "MODEL_HIGH_MARKET_LOW": 1},
            "phase17_4_exit_criteria": {
                "decision_supported_false": True,
                "market_data_overlay_only": True,
                "no_imperative_language": True,
            },
        },
    }


def _resolver_for(resolved: _ResolvedPvo):
    def _resolve_pvo_source(*_args, **_kwargs) -> _ResolvedPvo:
        return resolved

    return _resolve_pvo_source


def _base_kwargs(tmp_path: Path) -> dict[str, Any]:
    latest, coverage = _write_latest_pair(tmp_path)
    pvo, pvo_coverage = _write_pvo_pair(tmp_path)
    cache_path = _write_fresh_market_cache(
        tmp_path / "app/cache/fantasycalc/market_values.json"
    )
    return {
        "latest_path": latest,
        "coverage_latest_path": coverage,
        "history_db_path": tmp_path / "app/data/market_divergence_history.db",
        "marker_path": (
            tmp_path
            / "app/data/valuation_runtime/market_divergence_refresh_status_latest.json"
        ),
        "report_path": tmp_path / "reports/market_divergence_refresh.json",
        "market_cache_path": cache_path,
        "pvo_seed_path": tmp_path / "seed/universe_pvo_latest.json",
        "pvo_coverage_seed_path": tmp_path / "seed/universe_pvo_coverage_latest.json",
        "pvo_runtime_dir": tmp_path / "app/data/valuation_runtime",
        "resolve_pvo_source_fn": _resolver_for(_ResolvedPvo("runtime", pvo, pvo_coverage)),
        "build_fn": lambda *_args, **_kwargs: _divergence_batch(),
        "now_fn": lambda: NOW,
    }


def _read_marker(path: Path) -> dict[str, Any]:
    assert path.exists(), f"terminal state did not write marker: {path}"
    return json.loads(path.read_text())


def test_refresh_reads_fresh_cache_only_no_fetch_with_cache_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    import httpx

    from src.dynasty_genius.adapters import fantasycalc_adapter

    bad_calls: list[Any] = []

    def fail_network(*args, **kwargs):
        bad_calls.append((args, kwargs))
        raise AssertionError("scheduled divergence refresh must not live-fetch")

    monkeypatch.setattr(httpx, "get", fail_network)
    monkeypatch.setattr(fantasycalc_adapter, "fetch_with_cache", fail_network)
    if hasattr(runner, "fetch_with_cache"):
        monkeypatch.setattr(runner, "fetch_with_cache", fail_network)
    if hasattr(runner, "httpx"):
        monkeypatch.setattr(runner.httpx, "get", fail_network)
    if hasattr(runner, "subprocess"):
        monkeypatch.setattr(runner.subprocess, "run", fail_network)

    kwargs = _base_kwargs(tmp_path)
    captured: dict[str, Any] = {}

    def build_fn(universe_pvo_batch, fc_response, *, fetch_caveats, captured_at, **_):
        captured["pvo"] = universe_pvo_batch
        captured["fc_response"] = fc_response
        captured["fetch_caveats"] = fetch_caveats
        captured["captured_at"] = captured_at
        return _divergence_batch(captured_at=captured_at)

    kwargs["build_fn"] = build_fn

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["status"] == "ok"
    assert report["decision_supported"] is False
    assert report["pvo_source_kind"] == "runtime"
    assert report["market_source"]["status"] == "fresh_cache"
    assert report["market_source"]["cache_path"] == str(kwargs["market_cache_path"])
    assert report["commit_required_for_repo_baseline"] is True
    assert set(report["dirty_paths"]) == {
        str(kwargs["latest_path"]),
        str(kwargs["coverage_latest_path"]),
    }
    assert report["history_db_path"] == str(kwargs["history_db_path"])
    assert report["forbidden_commands_attempted"] == []
    assert captured["fc_response"][0]["player"]["sleeperId"] == "101"
    assert "stale_market_data" not in captured["fetch_caveats"]
    assert json.loads(kwargs["latest_path"].read_text())["captured_at"] == captured[
        "captured_at"
    ]
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "ok"
    assert marker["decision_supported"] is False
    assert marker["latest_sha256"] == _sha(kwargs["latest_path"])
    assert marker["coverage_sha256"] == _sha(kwargs["coverage_latest_path"])
    assert json.loads(kwargs["report_path"].read_text()) == report
    assert bad_calls == []


def test_runtime_absent_aborts_by_default_but_allow_seed_is_explicit_and_not_fresh(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    seed_pvo, seed_coverage = _write_pvo_pair(tmp_path, suffix="seed")
    kwargs["resolve_pvo_source_fn"] = _resolver_for(
        _ResolvedPvo("seed", seed_pvo, seed_coverage, source_as_of=None)
    )
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == "runtime_pvo_absent_seed_disallowed"
    assert report["decision_supported"] is False
    assert report["pvo_source_kind"] == "seed"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert marker["reason"] == "runtime_pvo_absent_seed_disallowed"

    allow_seed_report = runner.run_market_divergence_refresh(
        **{**kwargs, "allow_seed": True}
    )

    assert allow_seed_report["status"] == "ok"
    assert allow_seed_report["pvo_source_kind"] == "seed"
    assert allow_seed_report["pvo_runtime_verified"] is False
    assert allow_seed_report["freshness_claimed"] is False
    assert "runtime" not in allow_seed_report["freshness_basis"].lower()


def test_unverified_runtime_fails_closed_before_latest_or_history_write(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    def bad_resolver(*_args, **_kwargs):
        raise PvoSourceNotReadyError("runtime marker hash mismatch")

    def build_fn(*_args, **_kwargs):
        raise AssertionError("build must not run when runtime PVO is unverified")

    report = runner.run_market_divergence_refresh(
        **{**kwargs, "resolve_pvo_source_fn": bad_resolver, "build_fn": build_fn}
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "pvo_source"
    assert "pvo_source_not_ready" in report["aborted_reason"]
    assert report["decision_supported"] is False
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    assert not kwargs["history_db_path"].exists()
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert "pvo_source_not_ready" in marker["reason"]


@pytest.mark.parametrize(
    ("cache_setup", "expected_reason"),
    [
        ("stale", "market_source_prior_date"),
        ("missing", "market_cache_missing"),
    ],
)
def test_stale_or_cold_market_cache_aborts_before_build_or_latest_write(
    tmp_path: Path,
    cache_setup: str,
    expected_reason: str,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    if cache_setup == "stale":
        _write_stale_market_cache(kwargs["market_cache_path"])
    else:
        kwargs["market_cache_path"].unlink()
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    def build_fn(*_args, **_kwargs):
        raise AssertionError("build must not run for stale/cold market cache")

    report = runner.run_market_divergence_refresh(
        **{**kwargs, "build_fn": build_fn}
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == expected_reason
    assert report["decision_supported"] is False
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert marker["reason"] == expected_reason


def test_same_date_market_cache_outside_code_owned_bound_is_stale_not_prior_date(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    _write_json(
        kwargs["market_cache_path"],
        {
            "fetched_at": "2026-09-01T00:00:00Z",
            "ttl_hours": 99999,
            "data": [],
        },
    )
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    def build_fn(*_args, **_kwargs):
        raise AssertionError("code-owned stale market source must not reach build")

    report = runner.run_market_divergence_refresh(
        **{
            **kwargs,
            "build_fn": build_fn,
            "now_fn": lambda: datetime(2026, 9, 1, 13, 40, tzinfo=UTC),
        }
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_cache_stale"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    assert not kwargs["history_db_path"].exists()
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert marker["reason"] == "market_cache_stale"


def test_builder_stale_market_caveat_rows_are_rejected_before_publish(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    report = runner.run_market_divergence_refresh(
        **{**kwargs, "build_fn": lambda *_args, **_kwargs: _divergence_batch(stale_market=True)}
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "validation"
    assert report["aborted_reason"] == "stale_market_data_in_candidate"
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    assert not kwargs["history_db_path"].exists()
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert marker["reason"] == "stale_market_data_in_candidate"


def test_partial_publish_failure_restores_latest_pair_byte_identical(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    original_latest = kwargs["latest_path"].read_bytes()
    original_coverage = kwargs["coverage_latest_path"].read_bytes()

    def partial_publish(*, latest_path, coverage_latest_path, latest_text, **_kwargs):
        Path(latest_path).write_text(latest_text)
        assert Path(latest_path).read_bytes() != original_latest
        assert Path(coverage_latest_path).read_bytes() == original_coverage
        raise RuntimeError("coverage_replace_failed")

    report = runner.run_market_divergence_refresh(
        **{**kwargs, "publish_latest_pair_fn": partial_publish}
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "publish"
    assert report["restored_from_backup"] is True
    assert report["decision_supported"] is False
    assert kwargs["latest_path"].read_bytes() == original_latest
    assert kwargs["coverage_latest_path"].read_bytes() == original_coverage
    assert not kwargs["history_db_path"].exists()
    marker = _read_marker(kwargs["marker_path"])
    assert marker["status"] == "degraded"
    assert marker["reason"] == "coverage_replace_failed"


def test_pit_history_upserts_one_row_per_player_and_capture_date(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    kwargs = _base_kwargs(tmp_path)
    batches = [
        _divergence_batch(delta_one=0.25),
        _divergence_batch(delta_one=0.31),
    ]

    def build_fn(*_args, **_kwargs):
        return batches.pop(0)

    first = runner.run_market_divergence_refresh(**{**kwargs, "build_fn": build_fn})
    second = runner.run_market_divergence_refresh(**{**kwargs, "build_fn": build_fn})

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    with sqlite3.connect(kwargs["history_db_path"]) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT player_id, capture_date, decision_supported, payload_json "
            "FROM market_divergence_history ORDER BY player_id"
        ).fetchall()

    assert len(rows) == 2
    assert {row["player_id"] for row in rows} == {"101", "202"}
    assert {row["capture_date"] for row in rows} == {"2026-07-08"}
    assert {row["decision_supported"] for row in rows} == {0}
    payloads = {
        row["player_id"]: json.loads(row["payload_json"])
        for row in rows
    }
    assert payloads["101"]["divergence"]["model_minus_market_delta"] == 0.31
    assert payloads["101"]["divergence"]["decision_supported"] is False
    assert second["history_upserted_rows"] == 2


def test_status_marker_absent_or_too_old_is_degraded(tmp_path: Path) -> None:
    runner = _load_runner()
    marker = (
        tmp_path
        / "app/data/valuation_runtime/market_divergence_refresh_status_latest.json"
    )

    missing = runner.inspect_market_divergence_refresh_status(
        marker_path=marker,
        now_fn=lambda: NOW,
        interval_hours=24,
        grace_hours=3,
    )
    assert missing == {
        "status": "degraded",
        "reason": "marker_absent",
        "decision_supported": False,
    }

    _write_json(
        marker,
        {
            "status": "ok",
            "finished_at": (NOW - timedelta(hours=28)).isoformat(),
            "decision_supported": False,
        },
    )
    stale = runner.inspect_market_divergence_refresh_status(
        marker_path=marker,
        now_fn=lambda: NOW,
        interval_hours=24,
        grace_hours=3,
    )
    assert stale["status"] == "degraded"
    assert stale["reason"] == "marker_stale"
    assert stale["decision_supported"] is False

    _write_json(
        marker,
        {
            "status": "ok",
            "finished_at": (NOW - timedelta(hours=1)).isoformat(),
            "decision_supported": False,
        },
    )
    ok = runner.inspect_market_divergence_refresh_status(
        marker_path=marker,
        now_fn=lambda: NOW,
        interval_hours=24,
        grace_hours=3,
    )
    assert ok["status"] == "ok"
    assert ok["decision_supported"] is False
