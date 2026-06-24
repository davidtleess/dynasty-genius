"""T5 RED: model-output capture ops files (committable only).

T5 commits the local scheduler plist and gitignore coverage. It must not load
launchd or execute a live refresh/capture; those operational steps remain
separately David-gated.
"""

from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-model-pvo-refresh.plist")
ROOT = Path("/Users/davidleess/dynasty-genius-product")


def test_model_output_launchd_plist_runs_refresh_then_capture_runner() -> None:
    data = plistlib.loads(PLIST.read_bytes())
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-model-pvo-refresh"
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_pvo_refresh.py")
    assert "scripts/refresh_league_intelligence.py" not in args
    assert "scripts/build_universe_pvo_batch.py" not in args
    assert "scripts/run_model_forward_capture.py" not in args

    assert args[2:] == [
        "--pvo-artifact-path",
        str(ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"),
        "--coverage-artifact-path",
        str(
            ROOT
            / "app"
            / "data"
            / "valuation"
            / "universe_pvo_coverage_latest.json"
        ),
        "--capture-db-path",
        str(ROOT / "app" / "data" / "model_forward_capture.db"),
        "--report-path",
        str(ROOT / "app" / "data" / "model_capture" / "pvo_refresh_latest_report.json"),
        "--capture-report-path",
        str(
            ROOT
            / "app"
            / "data"
            / "model_capture"
            / "model_forward_capture_latest_report.json"
        ),
    ]

    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 30}
    assert data["RunAtLoad"] is False
    assert data["StandardOutPath"] == str(
        ROOT / "app" / "data" / "logs" / "pvo_refresh.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app" / "data" / "logs" / "pvo_refresh.err.log"
    )


def test_model_output_launchd_plist_is_valid_plist() -> None:
    result = subprocess.run(
        ["plutil", "-lint", str(PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_model_output_operational_data_is_gitignored() -> None:
    paths = [
        "app/data/model_forward_capture.db",
        "app/data/model_forward_capture.db-journal",
        "app/data/model_capture/model_forward_capture_latest_report.json",
        "app/data/model_capture/pvo_refresh_latest_report.json",
        "app/data/logs/model_forward_capture.out.log",
        "app/data/logs/model_forward_capture.err.log",
        "app/data/logs/pvo_refresh.out.log",
        "app/data/logs/pvo_refresh.err.log",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "-v", *paths],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for path in paths:
        assert path in result.stdout


def test_scheduler_log_directory_placeholder_exists() -> None:
    assert Path("app/data/logs/.gitkeep").is_file()
