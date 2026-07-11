"""Realized-Outcome Loop T5 RED: scorecard CLI producer + weekly LaunchAgent.

The CLI is a thin scheduler-safe wrapper over Tasks 1-4. It is read-only over source
stores/snapshots, writes only the gitignored realized-outcome scorecard artifact, never
invokes git, and treats off-season/not-finalized weeks as healthy no-ops.
"""

from __future__ import annotations

import importlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path


def _load_cli():
    return importlib.import_module("scripts.run_realized_outcome_scoring")


def _final_schedule() -> dict:
    return {
        "season": 2026,
        "week": 1,
        "expected_game_count": 1,
        "games": [{"season": 2026, "week": 1, "game_id": "g1", "status": "final"}],
    }


def _not_final_schedule() -> dict:
    return {
        "season": 2026,
        "week": 1,
        "expected_game_count": 1,
        "games": [
            {"season": 2026, "week": 1, "game_id": "g1", "status": "postponed"}
        ],
    }


def _prediction_rows() -> list[dict]:
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


def _identity_snapshots() -> list[dict]:
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


def _stat_rows() -> list[dict]:
    return [
        {
            "player_id": "00-0001",
            "season": 2026,
            "week": 1,
            "fantasy_points_ppr": 11.0,
            "player_status": "active",
            "game_played": True,
        }
    ]


def _util_rows() -> list[dict]:
    return [
        {
            "player_id": "00-0001",
            "season": 2026,
            "week": 1,
            "snap_share_realized": 0.55,
        }
    ]


def test_preflight_reports_readiness_without_scoring_or_writing(tmp_path, monkeypatch, capsys):
    cli = _load_cli()
    report_path = tmp_path / "realized_outcome" / "scorecard.json"

    def fail_run_scoring(**_kwargs):
        raise AssertionError("preflight must not score or write")

    monkeypatch.setattr(cli, "run_scoring", fail_run_scoring)

    result = cli.main(["--report-path", str(report_path), "--preflight"])

    assert result == 0
    body = json.loads(capsys.readouterr().out)
    assert body["preflight"] is True
    assert body["status"] == "ready"
    assert body["decision_supported"] is False
    assert body["report_path"] == str(report_path)
    assert not report_path.exists()


def test_offseason_no_finalized_week_noops_without_artifact_mutation(tmp_path):
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    report_path.write_text(json.dumps({"status": "prior", "decision_supported": False}))
    before = report_path.read_text()

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        schedule_loader=lambda *_args, **_kwargs: {
            "season": 2026,
            "week": 1,
            "expected_game_count": 0,
            "games": [],
        },
        stat_loader=lambda *_args, **_kwargs: _stat_rows(),
        util_loader=lambda *_args, **_kwargs: _util_rows(),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=lambda *_args, **_kwargs: _identity_snapshots(),
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "week_not_finalized"
    assert result["week_status"] == "not_finalized"
    assert result["decision_supported"] is False
    assert report_path.read_text() == before


def test_week_not_finalized_noops_before_loading_or_writing(tmp_path):
    # AMENDED (spec 2026-07-11, F5/Codex R4): the predictions gate now runs FIRST by
    # design, so the prediction loader is legitimately called before the finality no-op;
    # stat/util/identity loaders must still stay dark on a not-finalized week.
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"

    def fail_loader(*_args, **_kwargs):
        raise AssertionError("not-finalized week must not load/score source rows")

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        schedule_loader=lambda *_args, **_kwargs: _not_final_schedule(),
        stat_loader=fail_loader,
        util_loader=fail_loader,
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=fail_loader,
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "week_not_finalized"
    assert result["decision_supported"] is False
    assert not report_path.exists()


def test_full_score_path_uses_injected_seams_writes_only_gitignored_artifact(
    tmp_path,
    monkeypatch,
):
    cli = _load_cli()
    report_path = tmp_path / "app" / "data" / "realized_outcome" / "scorecard.json"

    def forbid_git(*_args, **_kwargs):
        raise AssertionError("realized-outcome scoring CLI must never invoke git")

    monkeypatch.setattr(cli.subprocess, "run", forbid_git)

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=report_path,
        schedule_loader=lambda *_args, **_kwargs: _final_schedule(),
        stat_loader=lambda *_args, **_kwargs: _stat_rows(),
        util_loader=lambda *_args, **_kwargs: _util_rows(),
        prediction_loader=lambda *_args, **_kwargs: _prediction_rows(),
        identity_snapshot_loader=lambda *_args, **_kwargs: _identity_snapshots(),
    )

    assert result["status"] == "ok"
    assert result["decision_supported"] is False
    assert result["git_commit_performed"] is False
    assert result["scorecard_path"] == str(report_path)
    assert report_path.exists()
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()) == [
        "app/data/realized_outcome/scorecard.json"
    ]

    scorecard = json.loads(report_path.read_text())
    assert scorecard["decision_supported"] is False
    assert scorecard["status"] == "ok"
    assert scorecard["tracking_rows"]
    assert "cohort_metrics" in scorecard
    assert "buy" not in report_path.read_text().lower()
    assert "sell" not in report_path.read_text().lower()
    assert "tier" not in report_path.read_text().lower()
    assert "verdict" not in report_path.read_text().lower()


def test_main_exit_codes_follow_ok_noop_vs_blocked_convention(tmp_path, monkeypatch):
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"

    monkeypatch.setattr(
        cli,
        "run_scoring",
        lambda **_kwargs: {"status": "ok", "decision_supported": False},
    )
    assert cli.main(["--report-path", str(report_path)]) == 0

    monkeypatch.setattr(
        cli,
        "run_scoring",
        lambda **_kwargs: {"status": "noop", "decision_supported": False},
    )
    assert cli.main(["--report-path", str(report_path)]) == 0

    monkeypatch.setattr(
        cli,
        "run_scoring",
        lambda **_kwargs: {"status": "blocked", "decision_supported": False},
    )
    assert cli.main(["--report-path", str(report_path)]) == 1


def test_main_without_season_week_resolves_concrete_values_before_run_scoring(
    tmp_path,
    monkeypatch,
):
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    seen: list[dict] = []

    monkeypatch.setattr(cli, "_resolve_season_week", lambda: (2026, 5))

    def fake_run_scoring(**kwargs):
        seen.append(kwargs)
        return {"status": "noop", "decision_supported": False}

    monkeypatch.setattr(cli, "run_scoring", fake_run_scoring)

    result = cli.main(["--report-path", str(report_path)])

    assert result == 0
    assert seen
    assert seen[0]["season"] == 2026
    assert seen[0]["week"] == 5
    assert seen[0]["season"] is not None
    assert seen[0]["week"] is not None


def test_main_default_offseason_path_noops_without_artifact_mutation(
    tmp_path,
    monkeypatch,
):
    cli = _load_cli()
    report_path = tmp_path / "scorecard.json"
    report_path.write_text(json.dumps({"status": "prior", "decision_supported": False}))
    before = report_path.read_text()

    monkeypatch.setattr(cli, "_resolve_season_week", lambda: (2026, 5))
    monkeypatch.setattr(
        cli,
        "_default_schedule_loader",
        lambda *_args, **_kwargs: {
            "season": 2026,
            "week": 5,
            "expected_game_count": 0,
            "games": [],
        },
    )

    def fail_loader(*_args, **_kwargs):
        raise AssertionError("off-season default no-op must not load source rows")

    # AMENDED (spec 2026-07-11): the prediction loader now legitimately runs first —
    # off-season it returns [] (unwired/no snapshots), which IS the honest no-op trigger.
    # A hermetic --marker-path keeps the new terminal marker off the live default path.
    monkeypatch.setattr(cli, "_default_stat_loader", fail_loader)
    monkeypatch.setattr(cli, "_default_util_loader", fail_loader)
    monkeypatch.setattr(cli, "_default_prediction_loader", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "_default_identity_snapshot_loader", fail_loader)

    result = cli.main(
        [
            "--report-path",
            str(report_path),
            "--marker-path",
            str(tmp_path / "status.json"),
        ]
    )

    assert result == 0
    assert report_path.read_text() == before


def test_cli_loads_standalone_from_outside_repo_without_module_error(tmp_path):
    script_path = Path("scripts/run_realized_outcome_scoring.py").resolve()
    probe = "\n".join(
        [
            "import importlib.util",
            "import os",
            "import pathlib",
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"os.chdir({str(tmp_path)!r})",
            "spec = importlib.util.spec_from_file_location(",
            "    'run_realized_outcome_scoring_standalone', script_path",
            ")",
            "module = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(module)",
            "assert callable(module.main)",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_realized_outcome_runtime_dir_is_gitignored() -> None:
    gitignore = Path(".gitignore").read_text()

    assert "app/data/realized_outcome/" in gitignore


def test_weekly_launchagent_is_committed_but_not_run_at_load() -> None:
    plist_path = Path("ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist")
    plist = plistlib.loads(plist_path.read_bytes())

    assert plist["Label"] == "com.davidleess.dynasty-realized-outcome-scoring"
    args = plist["ProgramArguments"]
    assert any(arg.endswith(".venv/bin/python3.14") for arg in args)
    assert any(arg.endswith("scripts/run_realized_outcome_scoring.py") for arg in args)
    assert plist["RunAtLoad"] is False
    interval = plist["StartCalendarInterval"]
    assert set(interval) >= {"Weekday", "Hour", "Minute"}
    assert "app/data/realized_outcome" in " ".join(args)
