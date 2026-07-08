"""Phase 0 RED: daily market-divergence refresh ops artifacts.

The plist is committable configuration only. Installing/reloading it with launchctl is a
separate David-gated machine change.
"""

from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/Users/davidleess/dynasty-genius-product")
PLIST = Path("ops/launchd/com.davidleess.dynasty-market-divergence-refresh.plist")
HISTORY_DB = "app/data/market_divergence_history.db"
STATUS_MARKER = (
    "app/data/valuation_runtime/market_divergence_refresh_status_latest.json"
)
REPORT = "app/data/valuation_runtime/market_divergence_refresh_latest_report.json"


def test_market_divergence_launchd_plist_runs_refresh_wrapper_only() -> None:
    data = plistlib.loads(PLIST.read_bytes())
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-market-divergence-refresh"
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 40}
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_market_divergence_refresh.py")
    assert "scripts/build_universe_market_divergence.py" not in args
    assert "scripts/run_league_intelligence_refresh.py" not in args
    assert "launchctl" not in args
    assert "--latest-path" in args
    assert args[args.index("--latest-path") + 1] == str(
        ROOT / "app/data/valuation/universe_market_divergence_latest.json"
    )
    assert "--coverage-latest-path" in args
    assert args[args.index("--coverage-latest-path") + 1] == str(
        ROOT / "app/data/valuation/universe_market_divergence_coverage_latest.json"
    )
    assert "--history-db-path" in args
    assert args[args.index("--history-db-path") + 1] == str(ROOT / HISTORY_DB)
    assert "--marker-path" in args
    assert args[args.index("--marker-path") + 1] == str(ROOT / STATUS_MARKER)
    assert "--report-path" in args
    assert args[args.index("--report-path") + 1] == str(ROOT / REPORT)
    assert "--allow-seed" not in args
    assert data["StandardOutPath"] == str(
        ROOT / "app/data/logs/market_divergence_refresh.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app/data/logs/market_divergence_refresh.err.log"
    )


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_market_divergence_launchd_plist_is_valid_plist() -> None:
    result = subprocess.run(
        ["plutil", "-lint", str(PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_market_divergence_operational_outputs_are_gitignored() -> None:
    paths = [
        HISTORY_DB,
        f"{HISTORY_DB}-journal",
        STATUS_MARKER,
        REPORT,
        "app/data/logs/market_divergence_refresh.out.log",
        "app/data/logs/market_divergence_refresh.err.log",
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


def test_market_divergence_history_db_is_in_backup_manifest() -> None:
    payload = json.loads(Path("app/config/backup_manifest.json").read_text())
    entries = payload.get("required", []) + payload.get("optional", [])
    matches = [entry for entry in entries if entry.get("path") == HISTORY_DB]

    assert matches == [
        {
            "path": HISTORY_DB,
            "required": True,
            "kind": "sqlite",
        }
    ]
