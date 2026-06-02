"""Cockpit hygiene tripwire contracts."""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
from subprocess import CompletedProcess


def _hygiene_module():
    path = Path("scripts/cockpit_hygiene_check.py")
    spec = importlib.util.spec_from_file_location("cockpit_hygiene_check", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_partition_status_lines_keeps_status_codes_for_anomalous_untracked_file():
    module = _hygiene_module()
    status_lines = [
        " M AGENT_SYNC.md",
        "?? docs/agent-ledger/2026-06-02.md",
        "?? docs/strategies/2025 college prospect data sources.md",
        "?? scripts/run_2025_curation.py",
    ]

    result = module.partition_status_lines(
        status_lines,
        allow_patterns=[
            "AGENT_SYNC.md",
            "docs/agent-ledger/2026-06-02.md",
            "docs/strategies/*.md",
        ],
    )

    assert [(item.status, item.path) for item in result.accounted] == [
        ("M", "AGENT_SYNC.md"),
        ("??", "docs/agent-ledger/2026-06-02.md"),
        ("??", "docs/strategies/2025 college prospect data sources.md"),
    ]
    assert [(item.status, item.path) for item in result.anomalous] == [
        ("??", "scripts/run_2025_curation.py")
    ]


def test_default_allow_patterns_cover_known_session_mutable_paths():
    module = _hygiene_module()

    patterns = module.default_allow_patterns(today=date(2026, 6, 2))

    result = module.partition_status_lines(
        [
            " M AGENT_SYNC.md",
            "?? docs/agent-ledger/2026-06-02.md",
            "?? docs/strategies/deep-research-report-Dynasty data backfill.md",
            "?? app/data/backtest/subpopulation/subpopulation_landscape_latest.json",
            "?? scripts/run_2025_curation.py",
        ],
        allow_patterns=patterns,
    )

    assert [(item.status, item.path) for item in result.anomalous] == [
        ("??", "scripts/run_2025_curation.py")
    ]


def test_format_anomalies_prints_status_and_path():
    module = _hygiene_module()
    result = module.partition_status_lines(
        ["?? scripts/run_2025_curation.py"],
        allow_patterns=[],
    )

    message = module.format_anomalies(result.anomalous)

    assert "?? scripts/run_2025_curation.py" in message


def test_cli_main_exits_nonzero_and_prints_anomalies_for_unexpected_paths(
    capsys,
):
    module = _hygiene_module()

    exit_code = module.main(
        [],
        status_lines_provider=lambda: [
            " M AGENT_SYNC.md",
            "?? scripts/run_2025_curation.py",
        ],
        today=date(2026, 6, 2),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "?? scripts/run_2025_curation.py" in captured.err


def test_cli_main_allows_extra_glob_for_known_in_flight_batch(capsys):
    module = _hygiene_module()

    exit_code = module.main(
        ["--allow", "scripts/run_2025_curation.py"],
        status_lines_provider=lambda: ["?? scripts/run_2025_curation.py"],
        today=date(2026, 6, 2),
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_git_status_porcelain_provider_uses_z_output_and_dequotes_space_paths(
    monkeypatch,
):
    module = _hygiene_module()
    calls: list[list[str]] = []

    def fake_run(command, *, capture_output, text, check):
        calls.append(command)
        assert capture_output is True
        assert text is False
        assert check is True
        return CompletedProcess(
            command,
            0,
            stdout=(
                b"?? docs/strategies/2025 college prospect data sources.md\x00"
                b" M AGENT_SYNC.md\x00"
            ),
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    lines = module._git_status_porcelain()

    assert calls == [["git", "status", "--porcelain", "-z"]]
    assert lines == [
        "?? docs/strategies/2025 college prospect data sources.md",
        " M AGENT_SYNC.md",
    ]
    result = module.partition_status_lines(
        lines,
        allow_patterns=["docs/strategies/*.md", "AGENT_SYNC.md"],
    )
    assert result.anomalous == []


def test_git_status_porcelain_provider_handles_rename_records_from_z_output(
    monkeypatch,
):
    module = _hygiene_module()

    def fake_run(command, *, capture_output, text, check):
        return CompletedProcess(
            command,
            0,
            stdout=(
                b"R  docs/strategies/new report.md\x00"
                b"docs/strategies/old report.md\x00"
            ),
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    lines = module._git_status_porcelain()

    assert lines == ["R  docs/strategies/new report.md"]
