"""Harness Trust Completion W2a.3 RED: local scheduler + Gate-4 clock docs."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-fc-snapshot.plist")
ARTIFACTS = Path("docs/ARTIFACTS.md")


ROOT = Path("/Users/davidleess/dynasty-genius-product")


def test_scheduler_plist_is_valid_and_runs_the_forward_capture_entrypoint() -> None:
    data = plistlib.loads(PLIST.read_bytes())
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-fc-snapshot"
    assert args[0].endswith("python3.14")
    assert args[1] == str(ROOT / "scripts" / "run_fc_forward_capture.py")
    assert "scripts/snapshot_fantasycalc.py" not in args

    assert args[2:] == [
        "--db-path",
        str(ROOT / "app" / "data" / "fc_forward_capture.db"),
        "--report-path",
        str(
            ROOT
            / "app"
            / "data"
            / "capture"
            / "fc_forward_capture_latest_report.json"
        ),
    ]

    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 0}
    assert data["RunAtLoad"] is False
    assert data["StandardOutPath"].endswith(
        "app/data/logs/fc_forward_capture.out.log"
    )
    assert data["StandardErrorPath"].endswith(
        "app/data/logs/fc_forward_capture.err.log"
    )


def test_scheduler_log_directory_exists() -> None:
    # Codex W2a.3 finding: launchd does not mkdir StandardOut/ErrorPath dirs, so the
    # plist's app/data/logs/ must exist (committed placeholder) or logging fails.
    assert Path("app/data/logs").is_dir()


def test_artifacts_doc_records_cadence_and_gate4_readiness() -> None:
    text = ARTIFACTS.read_text(encoding="utf-8")
    section = text.split("## Harness Trust Completion — Gate-4 forward-collection clock (W2a)", 1)[1]
    section = section.split("\n## ", 1)[0].lower()

    assert "scripts/run_fc_forward_capture.py" in section
    assert "app/data/fc_forward_capture.db" in section
    assert "survivorship-complete" in section
    assert "append-only" in section
    assert "descriptive benchmark" in section
    assert "fc_native" in section
    assert "daily" in section
    assert "gate-4" in section or "gate 4" in section
    assert "readiness" in section
    assert "6-month" in section or "6 month" in section or "six month" in section
    assert "divergence is unvalidated" in section
    assert "overlay" in section
    assert "decision_supported=false" in section

    assert "scripts/snapshot_fantasycalc.py" in section
    assert "app/data/fc_snapshots.db" in section
    assert "frozen" in section
    assert "read-only" in section
    assert "not active" in section or "not the active" in section
    assert "migration" in section and "out of scope" in section

    banned_patterns = [
        r"\bbuy\b",
        r"\bsell\b",
        r"\bwin\b",
        r"\bloss\b",
        r"\btiering\b",
        r"tradeable edge",
    ]
    for pattern in banned_patterns:
        assert re.search(pattern, section) is None
