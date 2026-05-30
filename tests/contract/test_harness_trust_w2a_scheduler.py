"""Harness Trust Completion W2a.3 RED: local scheduler + Gate-4 clock docs."""

from __future__ import annotations

import plistlib
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-fc-snapshot.plist")
ARTIFACTS = Path("docs/ARTIFACTS.md")


def test_scheduler_plist_is_valid_and_runs_the_snapshot_script() -> None:
    data = plistlib.loads(PLIST.read_bytes())

    assert data["Label"] == "com.davidleess.dynasty-fc-snapshot"
    assert data["ProgramArguments"][0].endswith("python3.14")
    assert any(
        str(arg).endswith("scripts/snapshot_fantasycalc.py")
        for arg in data["ProgramArguments"]
    )
    assert "StartCalendarInterval" in data


def test_scheduler_log_directory_exists() -> None:
    # Codex W2a.3 finding: launchd does not mkdir StandardOut/ErrorPath dirs, so the
    # plist's app/data/logs/ must exist (committed placeholder) or logging fails.
    assert Path("app/data/logs").is_dir()


def test_artifacts_doc_records_cadence_and_gate4_readiness() -> None:
    text = ARTIFACTS.read_text(encoding="utf-8").lower()

    assert "fc_native" in text or "fantasycalc snapshot" in text
    assert "cadence" in text or "daily" in text
    assert "gate-4" in text or "gate 4" in text
    assert "readiness" in text
    assert "6-month" in text or "6 month" in text or "six month" in text
