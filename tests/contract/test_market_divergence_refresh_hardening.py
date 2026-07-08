"""Phase 0 GREEN hardening — silence-is-not-success on the unguarded paths.

Codex's Phase-0 RED pinned the happy path + the named abort reasons, but flagged (in
the v3.1 GREEN re-review) that malformed cache JSON, an unparseable timestamp, a
builder failure, or an unexpected resolver error would crash the scheduled job WITHOUT
writing a degraded marker — a silent death, the exact failure mode the design exists to
prevent. These tests pin that EVERY terminal state writes a marker and leaves the
tracked pair byte-identical with no PIT history side effect.
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

NOW = datetime(2026, 7, 8, 13, 40, tzinfo=UTC)


@dataclass(frozen=True)
class _ResolvedPvo:
    source_kind: str
    pvo_path: Path
    coverage_path: Path
    source_as_of: str | None = "2026-07-08T13:30:00+00:00"
    ready: bool = True


def _runner():
    return importlib.import_module("scripts.run_market_divergence_refresh")


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _base_kwargs(tmp_path: Path) -> dict[str, Any]:
    latest = _write_json(
        tmp_path / "app/data/valuation/universe_market_divergence_latest.json",
        {"schema_version": "universe_market_divergence.v1", "captured_at": "old", "players": []},
    )
    coverage = _write_json(
        tmp_path / "app/data/valuation/universe_market_divergence_coverage_latest.json",
        {"total_players": 0},
    )
    pvo = _write_json(
        tmp_path / "pvo.json",
        {"schema_version": "universe_pvo_batch.v1", "players": []},
    )
    pvo_cov = _write_json(tmp_path / "pvo_coverage.json", {"total_players": 0})
    cache = _write_json(
        tmp_path / "app/cache/fantasycalc/market_values.json",
        {"fetched_at": "2026-07-08T13:00:00Z", "ttl_hours": 24, "data": []},
    )
    return {
        "latest_path": latest,
        "coverage_latest_path": coverage,
        "history_db_path": tmp_path / "app/data/market_divergence_history.db",
        "marker_path": tmp_path / "app/data/valuation_runtime/status.json",
        "report_path": tmp_path / "reports/refresh.json",
        "market_cache_path": cache,
        "resolve_pvo_source_fn": lambda **_: _ResolvedPvo("runtime", pvo, pvo_cov),
        "build_fn": lambda *_a, **_k: {
            "schema_version": "universe_market_divergence.v1",
            "captured_at": "2026-07-08T13:40:00+00:00",
            "players": [],
            "coverage": {"total_players": 0},
        },
        "now_fn": lambda: NOW,
    }


def _assert_silent_death_avoided(report: dict[str, Any], kwargs: dict[str, Any], *, before) -> None:
    assert report["status"] == "aborted"
    assert report["decision_supported"] is False
    # silence-is-not-success: a marker MUST exist for the terminal state.
    marker_path = Path(kwargs["marker_path"])
    assert marker_path.exists(), "terminal state wrote no status marker (silent death)"
    marker = json.loads(marker_path.read_text())
    assert marker["status"] == "degraded"
    assert marker["reason"] == report["aborted_reason"]
    # the tracked pair is untouched and no PIT history was created.
    assert Path(kwargs["latest_path"]).read_bytes() == before[0]
    assert Path(kwargs["coverage_latest_path"]).read_bytes() == before[1]
    assert not Path(kwargs["history_db_path"]).exists()


def test_malformed_market_cache_json_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    Path(kwargs["market_cache_path"]).write_text("{ this is not json ")
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_cache_unreadable"
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_unparseable_fetched_at_timestamp_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    _write_json(
        Path(kwargs["market_cache_path"]),
        {"fetched_at": "not-a-timestamp", "ttl_hours": 24, "data": []},
    )
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_cache_unreadable"
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_builder_exception_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("model join blew up")

    kwargs["build_fn"] = boom
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "build"
    assert report["aborted_reason"].startswith("build_failed:")
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_unexpected_resolver_error_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)

    def boom(**_k):
        raise OSError("runtime dir vanished")

    kwargs["resolve_pvo_source_fn"] = boom
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "pvo_source"
    assert report["aborted_reason"].startswith("pvo_source_error:")
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_non_numeric_ttl_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    _write_json(
        Path(kwargs["market_cache_path"]),
        {"fetched_at": "2026-07-08T13:00:00Z", "ttl_hours": "bad", "data": []},
    )
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_cache_unreadable"
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_list_shaped_cache_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    # valid JSON, wrong shape: a bare list has no .get()
    Path(kwargs["market_cache_path"]).write_text(json.dumps([{"nope": True}]))
    before = (
        Path(kwargs["latest_path"]).read_bytes(),
        Path(kwargs["coverage_latest_path"]).read_bytes(),
    )

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["aborted_stage"] == "market_source"
    assert report["aborted_reason"] == "market_cache_unreadable"
    _assert_silent_death_avoided(report, kwargs, before=before)


def test_unreadable_tracked_pair_is_degraded_not_silent(tmp_path: Path) -> None:
    runner = _runner()
    kwargs = _base_kwargs(tmp_path)
    # the tracked latest is gone at publish-prep → cannot safely publish
    Path(kwargs["latest_path"]).unlink()

    report = runner.run_market_divergence_refresh(**kwargs)

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "publish"
    assert report["aborted_reason"].startswith("tracked_pair_unreadable:")
    marker_path = Path(kwargs["marker_path"])
    assert marker_path.exists(), "terminal state wrote no status marker (silent death)"
    assert json.loads(marker_path.read_text())["status"] == "degraded"
    assert not Path(kwargs["history_db_path"]).exists()
