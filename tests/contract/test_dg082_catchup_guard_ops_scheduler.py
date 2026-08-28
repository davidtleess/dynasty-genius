"""Contract: the catch-up guard's launchd schedule (DG-082).

A bare ``StartInterval`` is not enough: launchd defers interval spawns while
the machine idles (``pended nondemand spawn = interval``) — measured twice on
2026-08-27/28, including a 15-hour overnight freeze at ``runs = 21`` — which
silences the guard during exactly the long-idle stretches it exists to
protect. ``StartCalendarInterval`` fires through the same idle (the 06:15 /
06:30 / 06:45 captures on the idle morning of 08-28 all fired on the dot).

The schedule is therefore a HYBRID:
- a 15-minute calendar lattice (:02/:17/:32/:47, every hour) — the idle rescue;
- ``StartInterval 900`` kept — fires overdue on wake-from-sleep, which a
  calendar slot slept through never does (measured 2026-08-27);
- ``RunAtLoad`` kept — login catch-up recovered the whole 08-27 morning.

Hours are EXPLICIT in every lattice entry: ``derive_job_schedules`` reads a
missing ``Hour`` as 0, not launchd's "every hour", so a Minute-only form would
derive as phantom midnight slots. The minutes are offset from :00/:15/:30/:45
so a guard tick never lands on a capture slot itself.
"""

from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/Users/davidleess/dynasty-genius-product")
PLIST = Path("ops/launchd/com.davidleess.dynasty-catchup-guard.plist")

LATTICE = [
    {"Hour": hour, "Minute": minute} for hour in range(24) for minute in (2, 17, 32, 47)
]


def _plist() -> dict:
    return plistlib.loads(PLIST.read_bytes())


def test_guard_schedule_is_the_hybrid_lattice_plus_interval() -> None:
    data = _plist()
    assert data["StartCalendarInterval"] == LATTICE
    assert data["StartInterval"] == 900, "wake-from-sleep overdue fire — keep it"
    assert data["RunAtLoad"] is True, "login catch-up recovered the 08-27 morning"


def test_every_lattice_entry_names_an_explicit_hour() -> None:
    # derive_job_schedules defaults a missing Hour to 0 — a Minute-only entry
    # would derive as a phantom midnight slot, not "every hour"
    for entry in _plist()["StartCalendarInterval"]:
        assert "Hour" in entry, f"Minute-only entry {entry} derives as Hour=0"


def test_guard_plist_runs_the_guard_script() -> None:
    data = _plist()
    args = data["ProgramArguments"]
    assert data["Label"] == "com.davidleess.dynasty-catchup-guard"
    assert data["WorkingDirectory"] == str(ROOT)
    assert args[0] == str(ROOT / ".venv" / "bin" / "python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_catchup_guard.py")
    assert data["StandardOutPath"] == str(ROOT / "app/data/logs/catchup_guard.out.log")
    assert data["StandardErrorPath"] == str(ROOT / "app/data/logs/catchup_guard.err.log")


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_guard_plist_is_valid_plist() -> None:
    proc = subprocess.run(
        ["plutil", "-lint", str(PLIST)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_guard_unguarded_reason_matches_the_calendar_world() -> None:
    # the guard stays unguarded (self-guarding is circular) but the reason must
    # not claim "no calendar slot to miss" once the plist carries 96 of them
    cfg = json.loads(Path("app/config/catchup_guard.json").read_text())
    reason = cfg["unguarded"]["com.davidleess.dynasty-catchup-guard"]
    assert "no calendar slot" not in reason
    assert reason
