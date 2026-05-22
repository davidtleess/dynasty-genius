from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_refresh_league_intelligence_runs_phase17_scripts_in_order():
    from scripts.refresh_league_intelligence import PHASE_STEPS, run_refresh

    calls: list[list[str]] = []

    def runner(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    result = run_refresh(runner=runner)

    assert result["status"] == "complete"
    assert [step.phase for step in PHASE_STEPS] == ["17.1", "17.2", "17.3", "17.4", "17.5"]
    assert calls == [
        [sys.executable, "scripts/build_sleeper_universe_snapshot.py"],
        [sys.executable, "scripts/build_universe_pvo_batch.py"],
        [sys.executable, "scripts/build_team_value_matrix.py"],
        [sys.executable, "scripts/build_universe_market_divergence.py"],
        [sys.executable, "scripts/build_league_opportunity_map.py"],
    ]
    assert [item["status"] for item in result["steps"]] == ["passed"] * 5
    assert result["decision_supported"] is False
    assert result["market_data_overlay_only"] is True


def test_refresh_league_intelligence_fails_fast_without_running_later_phases():
    from scripts.refresh_league_intelligence import run_refresh

    calls: list[list[str]] = []

    def runner(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess:
        calls.append(command)
        if command[-1] == "scripts/build_universe_pvo_batch.py":
            raise subprocess.CalledProcessError(2, command)
        return subprocess.CompletedProcess(command, 0)

    with pytest.raises(SystemExit) as excinfo:
        run_refresh(runner=runner)

    assert excinfo.value.code == 2
    assert calls == [
        [sys.executable, "scripts/build_sleeper_universe_snapshot.py"],
        [sys.executable, "scripts/build_universe_pvo_batch.py"],
    ]


def test_refresh_league_intelligence_dry_run_reports_commands_without_execution():
    from scripts.refresh_league_intelligence import run_refresh

    def runner(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess:
        raise AssertionError(f"dry run should not execute {command}")

    result = run_refresh(dry_run=True, runner=runner)

    assert result["status"] == "dry_run"
    assert [step["status"] for step in result["steps"]] == ["planned"] * 5
    assert result["steps"][0]["command"] == [sys.executable, "scripts/build_sleeper_universe_snapshot.py"]
