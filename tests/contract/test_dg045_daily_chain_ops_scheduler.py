"""Contract: the 09:00 daily-chain launchd job (DG-045 / SR-09 step 6).

ONE plist replaces six wall-clock slots. It is committable configuration only —
installing it (symlink + ``launchctl bootstrap``) and retiring the six old
agents happen together in one David-gated launchctl session, because a repo-side
retirement landed before that session leaves dangling symlinks that a reboot
would turn into silently-missing producers.

Two lines here are load-bearing:
- ``--dry-run=false``: the runner is safe-by-default (bare invocation prints the
  plan and touches nothing). A plist without this flag captures NOTHING.
- absolute venv python: launchd's bare PATH resolves python3 to Apple's 3.9.
"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/Users/davidleess/dynasty-genius-product")
PLIST = Path("ops/launchd/com.davidleess.dynasty-daily-chain.plist")


def _plist() -> dict:
    return plistlib.loads(PLIST.read_bytes())


def test_daily_chain_plist_runs_the_chain_executing_at_0900() -> None:
    data = _plist()
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-daily-chain"
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 0}
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_daily_chain.py")
    assert "--dry-run=false" in args, "without this the chain prints a plan and captures NOTHING"
    assert data["StandardOutPath"] == str(ROOT / "app/data/logs/daily_chain.out.log")
    assert data["StandardErrorPath"] == str(ROOT / "app/data/logs/daily_chain.err.log")


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_daily_chain_plist_is_valid_plist() -> None:
    proc = subprocess.run(
        ["plutil", "-lint", str(PLIST)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
