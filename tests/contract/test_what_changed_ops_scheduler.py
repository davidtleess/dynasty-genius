"""War Room #2 operational-refresh T2 RED: launchd plist + active docs."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-what-changed-report.plist")
ARTIFACTS = Path("docs/ARTIFACTS.md")
QUICK_REFERENCE = Path("docs/development/quick-reference.md")

ROOT = Path("/Users/davidleess/dynasty-genius-product")


def test_what_changed_launchd_plist_runs_report_cli_only() -> None:
    data = plistlib.loads(PLIST.read_bytes())
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-what-changed-report"
    assert args == [
        str(ROOT / ".venv" / "bin" / "python3.14"),
        str(ROOT / "scripts" / "run_what_changed_report.py"),
    ]
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 45}
    assert data["RunAtLoad"] is False
    assert data["StandardOutPath"] == str(
        ROOT / "app" / "data" / "logs" / "what_changed_report.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app" / "data" / "logs" / "what_changed_report.err.log"
    )

    forbidden_args = {
        "scripts/run_fc_forward_capture.py",
        "scripts/run_pvo_refresh.py",
        "scripts/run_model_forward_capture.py",
        "scripts/refresh_league_intelligence.py",
    }
    assert not forbidden_args.intersection(args)


def test_what_changed_launchd_plist_is_parseable_without_macos_plutil() -> None:
    data = plistlib.loads(PLIST.read_bytes())

    assert isinstance(data, dict)
    assert "ProgramArguments" in data
    assert "StartCalendarInterval" in data


def test_what_changed_scheduler_log_directory_placeholder_exists() -> None:
    assert Path("app/data/logs/.gitkeep").is_file()


def test_what_changed_active_docs_record_scheduler_and_command() -> None:
    artifacts_text = ARTIFACTS.read_text(encoding="utf-8")
    quick_reference_text = QUICK_REFERENCE.read_text(encoding="utf-8")
    combined = f"{artifacts_text}\n{quick_reference_text}"

    required_fragments = [
        "scripts/run_what_changed_report.py",
        "ops/launchd/com.davidleess.dynasty-what-changed-report.plist",
        "app/data/what_changed/what_changed_latest_report.json",
        "GET /api/league/what-changed",
        "09:45",
        "RunAtLoad=false",
        "decision_supported=false",
    ]
    for fragment in required_fragments:
        assert fragment in combined

    artifacts_section = artifacts_text.split(
        "## War Room #2 Daily What-Changed Operational Refresh", 1
    )[1]
    artifacts_section = artifacts_section.split("\n## ", 1)[0].lower()
    assert "read-only" in artifacts_section
    assert "overwrite-latest" in artifacts_section
    assert "current" in artifacts_section
    assert "launchctl" in artifacts_section and "david" in artifacts_section

    banned_patterns = [
        r"\bbuy\b",
        r"\bsell\b",
        r"\bwin\b",
        r"\bloss\b",
        r"\btiering\b",
        r"tradeable edge",
    ]
    for pattern in banned_patterns:
        assert re.search(pattern, artifacts_section) is None
