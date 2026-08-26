"""Contract: the 06:45 ff_playerids crosswalk snapshot launchd job (DG-053).

06:45 joins the early-capture family (06:15 nflverse, 06:30 transactions) —
after the 06:00 scheduled wake, clear of the 09:00 chain. The plist is
committable configuration only — installing it (symlink into
~/Library/LaunchAgents + ``launchctl bootstrap``) is a separate David-gated
machine change, batched with the SR-09 D5/D6 launchctl session.

Under launchd PATH is ``/usr/bin:/bin:/usr/sbin:/sbin``: a bare ``python3``
resolves to Apple's 3.9, so ProgramArguments must carry the absolute venv
interpreter, exactly like every other capture plist.
"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/Users/davidleess/dynasty-genius-product")
PLIST = Path("ops/launchd/com.davidleess.dynasty-ff-playerids-snapshot.plist")


def _plist() -> dict:
    return plistlib.loads(PLIST.read_bytes())


def test_ff_playerids_plist_runs_the_snapshot_at_0645() -> None:
    data = _plist()
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-ff-playerids-snapshot"
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 6, "Minute": 45}
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_ff_playerids_snapshot_capture.py")
    assert data["StandardOutPath"] == str(
        ROOT / "app/data/logs/ff_playerids_snapshot.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app/data/logs/ff_playerids_snapshot.err.log"
    )


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_ff_playerids_plist_is_valid_plist() -> None:
    proc = subprocess.run(
        ["plutil", "-lint", str(PLIST)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
