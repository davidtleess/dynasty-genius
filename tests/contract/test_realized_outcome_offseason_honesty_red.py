"""RED: realized-outcome scorer off-season honesty + fd lifecycle.

Spec: docs/superpowers/specs/2026-07-11-realized-outcome-offseason-honesty-design.md

These tests pin the Thread-B fix before implementation. They use temp scorecard/marker
paths only and must not depend on live realized-outcome artifacts.
"""

from __future__ import annotations

import gc
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from src.dynasty_genius.capture.outcome_forward_capture_store import (
    OutcomeForwardCaptureStore,
)


def _load_cli():
    return importlib.import_module("scripts.run_realized_outcome_scoring")


def _fd_count() -> int:
    return len(list(Path("/dev/fd").iterdir()))


def _final_schedule(
    *,
    season: int = 2026,
    week: int = 1,
    gameday: str = "2026-09-15",
) -> dict[str, Any]:
    return {
        "season": season,
        "week": week,
        "expected_game_count": 1,
        "games": [
            {
                "season": season,
                "week": week,
                "game_id": f"{season}_{week}",
                "status": "final",
                "gameday": gameday,
            }
        ],
    }


def _not_final_schedule() -> dict[str, Any]:
    return {
        "season": 2026,
        "week": 2,
        "expected_game_count": 2,
        "games": [
            {
                "season": 2026,
                "week": 2,
                "game_id": "g1",
                "status": "final",
                "gameday": "2026-09-22",
            }
        ],
    }


def _prediction_rows() -> list[dict[str, Any]]:
    return [
        {
            "capture_date": "2026-06-01",
            "sleeper_id": "sid-1",
            "player_key": "player-1",
            "position": "WR",
            "projection_2y": 10.0,
            "utilization": {
                "snap_share": {"value": 0.5, "role": "model_input"},
                "target_share_nfl": {"value": 0.2, "role": "diagnostic_only"},
            },
        }
    ]


def _identity_snapshots() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": "2026-06-01T00:00:00Z",
            "mappings": {
                "dg-1": {
                    "sleeper_id": "sid-1",
                    "gsis_id": "00-0001",
                    "pfr_id": "Pfr0001",
                }
            },
        }
    ]


def _stat_rows(season: int = 2026, week: int = 1) -> list[dict[str, Any]]:
    return [
        {
            "player_id": "00-0001",
            "season": season,
            "week": week,
            "fantasy_points_ppr": 11.0,
            "player_status": "active",
            "game_played": True,
        }
    ]


def _util_rows(season: int = 2026, week: int = 1) -> list[dict[str, Any]]:
    return [
        {
            "player_id": "00-0001",
            "season": season,
            "week": week,
            "snap_share_realized": 0.55,
        }
    ]


def _fail_loader(name: str) -> Callable[..., Any]:
    def _loader(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{name} must stay dark")

    return _loader


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_main(cli: Any, argv: list[str], *, now: datetime | None = None) -> int:
    return cli.main(
        argv,
        now_fn=(lambda: now or datetime(2026, 9, 20, tzinfo=timezone.utc)),
    )


def test_f1_read_outcomes_repeated_calls_do_not_leak_fds(tmp_path: Path) -> None:
    store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
    store.ingest_week(
        2026,
        1,
        stat_rows=_stat_rows(),
        util_rows=_util_rows(),
        schedule=_final_schedule(),
    )

    before = _fd_count()
    try:
        for _ in range(100):
            assert store.read_outcomes(2026, "00-0001") is not None
        after = _fd_count()
    finally:
        gc.collect()

    assert after - before == 0


def test_f2_ingest_week_repeated_calls_do_not_leak_fds(tmp_path: Path) -> None:
    before = _fd_count()
    try:
        store = OutcomeForwardCaptureStore(tmp_path / "outcomes.sqlite")
        for _ in range(100):
            store.ingest_week(
                2026,
                1,
                stat_rows=_stat_rows(),
                util_rows=_util_rows(),
                schedule=_final_schedule(),
            )
        after = _fd_count()
    finally:
        gc.collect()

    assert after - before == 0


def test_f3_empty_predictions_noop_before_schedule_or_network_loaders(
    tmp_path: Path,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        schedule_loader=_fail_loader("schedule_loader"),
        stat_loader=_fail_loader("stat_loader"),
        util_loader=_fail_loader("util_loader"),
        prediction_loader=lambda *_args, **_kwargs: [],
        identity_snapshot_loader=_fail_loader("identity_snapshot_loader"),
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "no_predictions_for_target"
    assert result["decision_supported"] is False
    assert not report_path.exists()


def test_f4_empty_predictions_write_noop_marker_not_scorecard(tmp_path: Path) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=_fail_loader("schedule_loader"),
        stat_loader=_fail_loader("stat_loader"),
        util_loader=_fail_loader("util_loader"),
        prediction_loader=lambda *_args, **_kwargs: [],
        identity_snapshot_loader=_fail_loader("identity_snapshot_loader"),
    )

    assert result["status"] == "noop"
    assert not report_path.exists()
    marker = _read_json(marker_path)
    assert marker["status"] == "noop"
    assert marker["noop_reason"] == "no_predictions_for_target"
    assert marker["season"] == 2026
    assert marker["week"] == 1
    assert marker["decision_supported"] is False


def test_f5_not_finalized_week_allows_prediction_and_schedule_only(
    tmp_path: Path,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"
    calls: list[str] = []

    def prediction_loader(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls.append("prediction")
        return _prediction_rows()

    def schedule_loader(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("schedule")
        return _not_final_schedule()

    result = cli.run_scoring(
        season=2026,
        week=2,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=schedule_loader,
        stat_loader=_fail_loader("stat_loader"),
        util_loader=_fail_loader("util_loader"),
        prediction_loader=prediction_loader,
        identity_snapshot_loader=_fail_loader("identity_snapshot_loader"),
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "week_not_finalized"
    assert calls == ["prediction", "schedule"]
    assert not report_path.exists()
    assert _read_json(marker_path)["status"] == "noop"


def test_f6_outcome_build_failure_writes_failed_marker_without_scorecard_mutation(
    tmp_path: Path,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"
    report_path.write_text(
        json.dumps({"status": "prior", "decision_supported": False}),
        encoding="utf-8",
    )
    before = report_path.read_text(encoding="utf-8")

    def stat_loader(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("boom")

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=lambda *_args, **_kwargs: _final_schedule(),
        stat_loader=stat_loader,
        util_loader=lambda *_args, **_kwargs: _util_rows(),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=lambda *_args, **_kwargs: _identity_snapshots(),
    )

    assert result["status"] == "failed"
    assert report_path.read_text(encoding="utf-8") == before
    marker = _read_json(marker_path)
    assert marker["status"] == "failed"
    assert marker["failure_reason"] == "outcome_build_failed:RuntimeError"
    assert marker["decision_supported"] is False


def test_f7_happy_path_writes_scorecard_and_ok_marker(tmp_path: Path) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=lambda *_args, **_kwargs: _final_schedule(),
        stat_loader=lambda *_args, **_kwargs: _stat_rows(),
        util_loader=lambda *_args, **_kwargs: _util_rows(),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=lambda *_args, **_kwargs: _identity_snapshots(),
        now_fn=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    assert result["status"] == "ok"
    assert _read_json(report_path)["status"] == "ok"
    marker = _read_json(marker_path)
    assert marker["status"] == "ok"
    assert marker["season"] == 2026
    assert marker["week"] == 1
    assert marker["decision_supported"] is False


def test_f8_ok_marker_for_same_target_noops_before_rescoring(tmp_path: Path) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"
    marker_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "season": 2026,
                "week": 1,
                "finished_at": "2026-09-20T00:00:00+00:00",
                "decision_supported": False,
            }
        ),
        encoding="utf-8",
    )

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=_fail_loader("schedule_loader"),
        stat_loader=_fail_loader("stat_loader"),
        util_loader=_fail_loader("util_loader"),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=_fail_loader("identity_snapshot_loader"),
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "already_scored"
    assert not report_path.exists()


def test_f9_stale_completed_season_without_predictions_noops_hermetically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    monkeypatch.setattr(cli, "_resolve_season_week", lambda **_kwargs: (2025, 22))
    monkeypatch.setattr(cli, "_default_prediction_loader", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "_default_schedule_loader", _fail_loader("schedule_loader"))
    monkeypatch.setattr(cli, "_default_stat_loader", _fail_loader("stat_loader"))
    monkeypatch.setattr(cli, "_default_util_loader", _fail_loader("util_loader"))
    monkeypatch.setattr(
        cli,
        "_default_identity_snapshot_loader",
        _fail_loader("identity_snapshot_loader"),
    )

    result = _run_main(
        cli,
        ["--report-path", str(report_path), "--marker-path", str(marker_path)],
        now=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )

    assert result == 0
    assert not report_path.exists()
    marker = _read_json(marker_path)
    assert marker["status"] == "noop"
    assert marker["noop_reason"] == "no_predictions_for_target"
    assert marker["season"] == 2025
    assert marker["week"] == 22


def test_f10_unwritable_marker_path_fails_loud_without_scorecard_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path
    monkeypatch.setattr(cli, "_default_prediction_loader", lambda *_args, **_kwargs: [])

    result = _run_main(
        cli,
        [
            "--report-path",
            str(report_path),
            "--marker-path",
            str(marker_path),
            "--season",
            "2026",
            "--week",
            "1",
        ],
    )

    captured = capsys.readouterr()
    assert result != 0
    assert "marker" in captured.err.lower()
    assert not report_path.exists()


def test_f11_marker_and_noop_output_are_execution_state_only(tmp_path: Path) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=_fail_loader("schedule_loader"),
        stat_loader=_fail_loader("stat_loader"),
        util_loader=_fail_loader("util_loader"),
        prediction_loader=lambda *_args, **_kwargs: [],
        identity_snapshot_loader=_fail_loader("identity_snapshot_loader"),
    )

    text = json.dumps({"result": result, "marker": _read_json(marker_path)}).lower()
    assert '"decision_supported": false' in text
    for forbidden in [
        "buy",
        "sell",
        "start",
        "sit",
        "verdict",
        "accuracy",
        "improved",
        "performance",
    ]:
        assert forbidden not in text


def test_f12_no_git_invocation_on_scheduler_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    def forbid_git(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("realized-outcome scoring must never invoke subprocess/git")

    monkeypatch.setattr(cli.subprocess, "run", forbid_git)
    monkeypatch.setattr(cli, "_default_prediction_loader", lambda *_args, **_kwargs: [])

    result = _run_main(
        cli,
        ["--report-path", str(report_path), "--marker-path", str(marker_path)],
    )

    assert result == 0
    assert _read_json(marker_path)["status"] == "noop"


def test_f13_scheduled_stale_target_with_predictions_noops_without_scoring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    monkeypatch.setattr(cli, "_resolve_season_week", lambda **_kwargs: (2025, 22))
    monkeypatch.setattr(
        cli,
        "_default_schedule_loader",
        lambda *_args, **_kwargs: _final_schedule(
            season=2025, week=22, gameday="2026-02-08"
        ),
    )
    monkeypatch.setattr(
        cli,
        "_default_prediction_loader",
        lambda *_args, **_kwargs: _prediction_rows(),
    )
    monkeypatch.setattr(cli, "_default_stat_loader", _fail_loader("stat_loader"))
    monkeypatch.setattr(cli, "_default_util_loader", _fail_loader("util_loader"))
    monkeypatch.setattr(
        cli,
        "_default_identity_snapshot_loader",
        _fail_loader("identity_snapshot_loader"),
    )

    result = _run_main(
        cli,
        ["--report-path", str(report_path), "--marker-path", str(marker_path)],
        now=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )

    assert result == 0
    assert not report_path.exists()
    marker = _read_json(marker_path)
    assert marker["status"] == "noop"
    assert marker["noop_reason"] == "stale_target"
    assert marker["season"] == 2025
    assert marker["week"] == 22


def test_f14_explicit_stale_target_bypasses_guard_for_intentional_backfill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    monkeypatch.setattr(
        cli,
        "_default_schedule_loader",
        lambda *_args, **_kwargs: _final_schedule(
            season=2025, week=22, gameday="2026-02-08"
        ),
    )
    monkeypatch.setattr(
        cli,
        "_default_prediction_loader",
        lambda *_args, **_kwargs: _prediction_rows(),
    )
    monkeypatch.setattr(
        cli,
        "_default_stat_loader",
        lambda *_args, **_kwargs: _stat_rows(season=2025, week=22),
    )
    monkeypatch.setattr(
        cli,
        "_default_util_loader",
        lambda *_args, **_kwargs: _util_rows(season=2025, week=22),
    )
    monkeypatch.setattr(
        cli,
        "_default_identity_snapshot_loader",
        lambda *_args, **_kwargs: _identity_snapshots(),
    )

    result = _run_main(
        cli,
        [
            "--report-path",
            str(report_path),
            "--marker-path",
            str(marker_path),
            "--season",
            "2025",
            "--week",
            "22",
        ],
        now=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )

    assert result == 0
    assert _read_json(report_path)["status"] == "ok"
    assert _read_json(marker_path)["status"] == "ok"


def test_f15_preflight_writes_neither_scorecard_nor_job_marker(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    marker_path = tmp_path / "status.json"

    result = _run_main(
        cli,
        [
            "--report-path",
            str(report_path),
            "--marker-path",
            str(marker_path),
            "--preflight",
        ],
    )

    assert result == 0
    body = json.loads(capsys.readouterr().out)
    assert body["preflight"] is True
    assert body["status"] == "ready"
    assert not report_path.exists()
    assert not marker_path.exists()


@pytest.mark.parametrize("preexisting_report", [False, True])
def test_f16_unwritable_marker_on_full_scoring_path_preserves_scorecard_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    preexisting_report: bool,
) -> None:
    cli = _load_cli()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "scorecard.json"
    if preexisting_report:
        report_path.write_text(
            json.dumps({"status": "prior", "decision_supported": False}),
            encoding="utf-8",
        )
        before = report_path.read_text(encoding="utf-8")
    else:
        before = None
    marker_path = tmp_path / "marker-as-directory"
    marker_path.mkdir()

    monkeypatch.setattr(
        cli,
        "_default_schedule_loader",
        lambda *_args, **_kwargs: _final_schedule(),
    )
    monkeypatch.setattr(cli, "_default_stat_loader", lambda *_args, **_kwargs: _stat_rows())
    monkeypatch.setattr(cli, "_default_util_loader", lambda *_args, **_kwargs: _util_rows())
    monkeypatch.setattr(
        cli,
        "_default_prediction_loader",
        lambda *_args, **_kwargs: _prediction_rows(),
    )
    monkeypatch.setattr(
        cli,
        "_default_identity_snapshot_loader",
        lambda *_args, **_kwargs: _identity_snapshots(),
    )

    result = _run_main(
        cli,
        [
            "--report-path",
            str(report_path),
            "--marker-path",
            str(marker_path),
            "--season",
            "2026",
            "--week",
            "1",
        ],
    )

    captured = capsys.readouterr()
    assert result != 0
    assert "marker" in captured.err.lower()
    if preexisting_report:
        assert report_path.read_text(encoding="utf-8") == before
        expected_files = ["scorecard.json"]
    else:
        assert not report_path.exists()
        expected_files = []
    assert sorted(path.name for path in report_dir.iterdir()) == expected_files


def test_f17_scorecard_publish_failure_rewrites_failed_marker_and_preserves_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _load_cli()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "scorecard.json"
    report_path.write_text(
        json.dumps({"status": "prior", "decision_supported": False}),
        encoding="utf-8",
    )
    before = report_path.read_text(encoding="utf-8")
    marker_path = tmp_path / "status.json"

    def fail_replace(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("publish boom")

    monkeypatch.setattr(os, "replace", fail_replace)

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        marker_path=marker_path,
        schedule_loader=lambda *_args, **_kwargs: _final_schedule(),
        stat_loader=lambda *_args, **_kwargs: _stat_rows(),
        util_loader=lambda *_args, **_kwargs: _util_rows(),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=lambda *_args, **_kwargs: _identity_snapshots(),
        now_fn=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    assert result["status"] == "failed"
    assert result["failure_reason"].startswith("scorecard_publish_failed")
    assert report_path.read_text(encoding="utf-8") == before
    marker = _read_json(marker_path)
    assert marker["status"] == "failed"
    assert marker["failure_reason"].startswith("scorecard_publish_failed")
    assert marker["decision_supported"] is False
    assert sorted(path.name for path in report_dir.iterdir()) == ["scorecard.json"]
