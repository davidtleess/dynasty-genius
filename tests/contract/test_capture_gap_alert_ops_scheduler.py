"""Contract: the 10:30 capture-gap-alert launchd job (DG-044 / SR-11).

The alert runs at 10:30, after the 10:15 backup, so one run covers 06:15,
06:30, the 09:00 chain and the backup (spec step 4). The plist is committable
configuration only — installing it (symlink into ~/Library/LaunchAgents +
``launchctl bootstrap``) is a separate David-gated machine change, and a
committed plist is not an installed plist.

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
PLIST = Path("ops/launchd/com.davidleess.dynasty-capture-gap-alert.plist")


def _plist() -> dict:
    return plistlib.loads(PLIST.read_bytes())


def test_gap_alert_plist_runs_the_alert_script_at_1030() -> None:
    data = _plist()
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-capture-gap-alert"
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 10, "Minute": 30}
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_capture_gap_alert.py")
    assert data["StandardOutPath"] == str(
        ROOT / "app/data/logs/capture_gap_alert.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app/data/logs/capture_gap_alert.err.log"
    )


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_gap_alert_plist_is_valid_plist() -> None:
    result = subprocess.run(
        ["plutil", "-lint", str(PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
