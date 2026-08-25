"""CH1 RED — one nflverse loader may never cap the other four."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pandas as pd
import pytest

STREAMS = ("player_stats", "rosters", "snap_counts", "pbp", "participation")


def _frame(*seasons: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": list(seasons),
            "row_id": [f"row-{season}" for season in seasons],
        }
    )


def _provider(
    behaviors: dict[str, Callable[[list[int]], pd.DataFrame]],
) -> SimpleNamespace:
    def loader(name: str):
        def load(*, seasons: list[int]):
            return behaviors[name](list(seasons))

        return load

    return SimpleNamespace(
        # DG-041: the real module exposes get_current_season, and the
        # participation source ceiling in _STREAM_LOADERS derives from it.
        # 2026 keeps this fixture in the same season geometry as the tests.
        get_current_season=lambda roster=False: 2026,
        load_player_stats=loader("player_stats"),
        load_rosters=loader("rosters"),
        load_snap_counts=loader("snap_counts"),
        load_pbp=loader("pbp"),
        load_participation=loader("participation"),
    )


def _run_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    behaviors: dict[str, Callable[[list[int]], pd.DataFrame]],
    *,
    ngs_frames: dict[str, pd.DataFrame] | None = None,
    explicit_season_end: bool = True,
) -> tuple[int, dict]:
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,position,training_eligible\n")
    captured: dict = {"runner_calls": [], "hash_inputs": [], "ngs_windows": []}

    monkeypatch.setitem(sys.modules, "nflreadpy", _provider(behaviors))

    def fake_load_nextgen(seasons: list[int]) -> dict[str, pd.DataFrame]:
        captured["ngs_windows"].append(list(seasons))
        return dict(ngs_frames or {})

    monkeypatch.setattr(cli, "load_nextgen_from_export", fake_load_nextgen)
    monkeypatch.setattr(
        cli,
        "nextgen_export_provenance",
        lambda: {"status": "absent", "reason": "test fixture"},
    )
    monkeypatch.setattr(cli, "_package_version", lambda: "nflreadpy-test")
    monkeypatch.setattr(cli, "_builder_config", lambda: {"min_games": 4})
    monkeypatch.setattr(cli, "_te_artifact_hashes", lambda: {})

    def fake_hash(**kwargs) -> str:
        captured["hash_inputs"].append(kwargs)
        return "source-hash"

    def fake_runner(**kwargs) -> dict:
        captured["runner_calls"].append(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(cli, "compute_source_hash", fake_hash)
    monkeypatch.setattr(cli, "run_feature_refresh", fake_runner)

    argv = [
        "--runtime-dir",
        str(runtime_dir),
        "--seed-path",
        str(seed_path),
        "--season-start",
        "2024",
    ]
    if explicit_season_end:
        argv.extend(["--season-end", "2026"])
    else:
        class FrozenDateTime:
            @staticmethod
            def now(tz=None):
                return datetime(2026, 8, 6, tzinfo=tz)

        monkeypatch.setattr(cli, "datetime", FrozenDateTime)
    rc = cli.main(argv)
    return rc, captured


def _healthy(seasons: list[int]) -> pd.DataFrame:
    return _frame(*seasons)


def _connection_then_previous(seasons: list[int]) -> pd.DataFrame:
    if 2026 in seasons:
        raise ConnectionError("2026 parquet missing")
    return _frame(*seasons)


def _value_then_previous(seasons: list[int]) -> pd.DataFrame:
    if 2026 in seasons:
        raise ValueError("Season must be between 2012 and 2025")
    return _frame(*seasons)


def _always_connection(_seasons: list[int]) -> pd.DataFrame:
    raise ConnectionError("provider unavailable")


def test_ch1_connection_and_value_errors_are_isolated_per_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc, captured = _run_cli(
        tmp_path,
        monkeypatch,
        {
            "player_stats": _connection_then_previous,
            "rosters": _healthy,
            "snap_counts": _value_then_previous,
            "pbp": _healthy,
            "participation": _value_then_previous,
        },
    )

    assert rc == 0
    assert len(captured["runner_calls"]) == 1
    call = captured["runner_calls"][0]
    frames = call["read_fns"]
    assert int(frames["rosters"]["season"].max()) == 2026
    assert int(frames["pbp"]["season"].max()) == 2026
    assert int(frames["player_stats"]["season"].max()) == 2025
    assert int(frames["snap_counts"]["season"].max()) == 2025
    assert int(frames["participation"]["season"].max()) == 2025

    provenance = call["source_inputs"]["stream_provenance"]
    assert provenance["rosters"]["effective_season"] == 2026
    assert provenance["pbp"]["effective_season"] == 2026
    for name, error_type in {
        "player_stats": "ConnectionError",
        "snap_counts": "ValueError",
    }.items():
        assert provenance[name]["effective_season"] == 2025
        assert provenance[name]["fallback_used"] is True
        assert provenance[name]["error_type"] == error_type
    # DISCLOSED TEST CHANGE (DG-041): participation is no longer ASKED for the
    # season its source refuses by construction — the request is capped at the
    # source's own ceiling, so there is no refusal and no fallback to record.
    # Same frame, same effective season; only the provenance stopped claiming
    # an event that never needed to happen.
    assert provenance["participation"]["effective_season"] == 2025
    assert provenance["participation"]["fallback_used"] is False
    assert provenance["participation"]["error_type"] is None


def test_ch1_dynamic_default_path_also_preserves_each_stream_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc, captured = _run_cli(
        tmp_path,
        monkeypatch,
        {
            "player_stats": _connection_then_previous,
            "rosters": _healthy,
            "snap_counts": _value_then_previous,
            "pbp": _healthy,
            "participation": _value_then_previous,
        },
        explicit_season_end=False,
    )

    assert rc == 0
    call = captured["runner_calls"][0]
    assert call["source_inputs"]["seasons_window"][-1] == 2025
    provenance = call["source_inputs"]["stream_provenance"]
    assert provenance["player_stats"]["effective_season"] == 2025
    assert provenance["rosters"]["effective_season"] == 2026
    assert provenance["pbp"]["effective_season"] == 2026


def test_ch1_effective_season_comes_from_returned_rows_not_requested_ceiling() -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    provider = SimpleNamespace(
        load=lambda *, seasons: pd.DataFrame({"season": [2024, 2025]})
    )

    _frame_result, provenance = cli._load_stream_isolated(
        provider, "load", [2024, 2025, 2026]
    )

    assert provenance["status"] == "loaded"
    assert provenance["effective_season"] == 2025


def test_ch1_loaded_empty_has_no_effective_season() -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    provider = SimpleNamespace(
        load=lambda *, seasons: pd.DataFrame(columns=["season"])
    )

    _frame_result, provenance = cli._load_stream_isolated(
        provider, "load", [2024, 2025, 2026]
    )

    assert provenance["status"] == "loaded_empty"
    assert provenance["effective_season"] is None


def test_ch1_fallback_used_requires_an_actual_retry() -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    calls: list[list[int]] = []

    def fail(*, seasons: list[int]) -> pd.DataFrame:
        calls.append(list(seasons))
        raise ConnectionError("missing")

    _frame_result, provenance = cli._load_stream_isolated(
        SimpleNamespace(load=fail), "load", [2026]
    )

    assert calls == [[2026]]
    assert provenance["status"] == "unavailable"
    assert provenance["fallback_used"] is False


def test_ch1_single_fully_unavailable_stream_refuses_cleanly_before_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, captured = _run_cli(
        tmp_path,
        monkeypatch,
        {
            "player_stats": _healthy,
            "rosters": _always_connection,
            "snap_counts": _healthy,
            "pbp": _healthy,
            "participation": lambda _seasons: pd.DataFrame(columns=["season", "row_id"]),
        },
    )

    assert rc == 1
    output = capsys.readouterr().out.lower()
    assert "refusing" in output
    assert "rosters" in output
    assert "unavailable" in output
    assert captured["hash_inputs"] == []
    assert captured["runner_calls"] == []


def test_ch1_all_five_unavailable_fails_loudly_before_hash_or_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, captured = _run_cli(
        tmp_path,
        monkeypatch,
        {name: _always_connection for name in STREAMS},
    )

    assert rc == 1
    output = capsys.readouterr().out.lower()
    assert "refusing" in output
    for name in STREAMS:
        assert name in output
    assert captured["hash_inputs"] == []
    assert captured["runner_calls"] == []


def test_ch1_stream_provenance_participates_in_source_hash() -> None:
    runner = importlib.import_module(
        "src.dynasty_genius.features.feature_refresh_runner"
    )
    common = {
        "loader_outputs": {"participation": pd.DataFrame(columns=["season"])},
        "seasons_window": [2024, 2025, 2026],
        "package_version": "nflreadpy-test",
        "builder_config": {},
        "te_rubric_artifacts": {},
        "identity_inputs": None,
    }
    loaded_empty = {
        "participation": {
            "status": "loaded_empty",
            "effective_season": None,
            "fallback_used": False,
            "error_type": None,
        }
    }
    unavailable = {
        "participation": {
            "status": "unavailable",
            "effective_season": None,
            "fallback_used": True,
            "error_type": "ValueError",
        }
    }

    assert runner.compute_source_hash(
        **common, stream_provenance=loaded_empty
    ) != runner.compute_source_hash(**common, stream_provenance=unavailable)


def test_ch1_stream_provenance_is_persisted_in_latest_report(tmp_path: Path) -> None:
    runner = importlib.import_module(
        "src.dynasty_genius.features.feature_refresh_runner"
    )
    runtime_dir = tmp_path / "runtime"
    stream_provenance = {
        "rosters": {
            "status": "loaded",
            "effective_season": 2026,
            "fallback_used": False,
            "error_type": None,
        },
        "participation": {
            "status": "loaded",
            "effective_season": 2025,
            "fallback_used": True,
            "error_type": "ValueError",
        },
    }

    def publish(_candidate_path: Path, **kwargs) -> dict:
        report_path = Path(kwargs["runtime_dir"]) / "feature_refresh_latest_report.json"
        report_path.write_text(json.dumps({"status": "ok"}))
        return {
            "status": "ok",
            "runtime_path": str(Path(kwargs["runtime_dir"]) / "runtime.csv"),
            "runtime_sha256": "sha",
            "dirty_paths": [],
        }

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=lambda: datetime(2026, 8, 6, tzinfo=timezone.utc),
        read_fns={"rosters": _frame(2026), "participation": _frame(2025)},
        source_inputs={
            "source_hash": "hash",
            "seasons_window": [2025, 2026],
            "stream_provenance": stream_provenance,
        },
        assemble_fn=lambda **_: pd.DataFrame([{"player_id": "p1"}]),
        publish_fn=publish,
    )

    assert result["status"] == "ok"
    report = json.loads(
        (runtime_dir / "feature_refresh_latest_report.json").read_text()
    )
    assert report["stream_provenance"] == stream_provenance


def test_ch1_ngs_last_good_export_path_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ngs = {"ngs_passing": _frame(2024, 2025)}
    rc, captured = _run_cli(
        tmp_path,
        monkeypatch,
        {name: _healthy for name in STREAMS},
        ngs_frames=ngs,
    )

    assert rc == 0
    call = captured["runner_calls"][0]
    assert call["read_fns"]["ngs_passing"].equals(ngs["ngs_passing"])
    assert captured["ngs_windows"] == [[2024, 2025, 2026]]
