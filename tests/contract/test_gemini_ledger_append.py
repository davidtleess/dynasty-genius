"""Gemini ledger append control contracts."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

FIXED_NOW = datetime(2026, 6, 2, 12, 7, tzinfo=ZoneInfo("America/New_York"))


def _ledger_module():
    path = Path("scripts/gemini_ledger_append.py")
    spec = importlib.util.spec_from_file_location("gemini_ledger_append", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry_body(task: str = "Bootstrap review") -> str:
    return "\n".join(
        [
            f"- Task: {task}",
            "- Governance read: Required governance set.",
            "- Active phase / surface: Gemini controls P1.",
            "- Intended or completed write scope: Ledger append only.",
            "- Files changed: docs/agent-ledger/2026-06-02.md.",
            "- Tests / checks: N/A.",
            "- Product alignment: PM read-only source verification.",
            "- Drift risks: None.",
            "- Handoff / next step: Return to cockpit.",
        ]
    )


def test_append_gemini_entry_creates_today_ledger_with_hardcoded_attribution(
    tmp_path: Path,
):
    module = _ledger_module()

    written_path = module.append_gemini_ledger_entry(
        body=_entry_body(),
        ledger_dir=tmp_path / "docs" / "agent-ledger",
        now=FIXED_NOW,
    )

    assert written_path == tmp_path / "docs" / "agent-ledger" / "2026-06-02.md"
    text = written_path.read_text(encoding="utf-8")
    assert text.startswith("## 12:07 ET - Gemini (Product Manager)\n\n")
    assert "- Task: Bootstrap review" in text
    assert "Claude" not in text
    assert "Codex" not in text


def test_append_gemini_entry_is_append_only_and_never_truncates(tmp_path: Path):
    module = _ledger_module()
    ledger_dir = tmp_path / "docs" / "agent-ledger"
    ledger_dir.mkdir(parents=True)
    ledger_path = ledger_dir / "2026-06-02.md"
    original = "## 08:00 ET - Codex (Implementation / CI / Automation)\n\n- Task: Existing.\n"
    ledger_path.write_text(original, encoding="utf-8")

    module.append_gemini_ledger_entry(
        body=_entry_body("First Gemini append"),
        ledger_dir=ledger_dir,
        now=FIXED_NOW,
    )
    module.append_gemini_ledger_entry(
        body=_entry_body("Second Gemini append"),
        ledger_dir=ledger_dir,
        now=FIXED_NOW,
    )

    text = ledger_path.read_text(encoding="utf-8")
    assert text.startswith(original)
    assert text.count("## 12:07 ET - Gemini (Product Manager)") == 2
    assert "- Task: First Gemini append" in text
    assert "- Task: Second Gemini append" in text


def test_append_gemini_entry_fails_closed_when_ledger_file_symlink_escapes(
    tmp_path: Path,
):
    module = _ledger_module()
    ledger_dir = tmp_path / "docs" / "agent-ledger"
    ledger_dir.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("outside-before\n", encoding="utf-8")
    (ledger_dir / "2026-06-02.md").symlink_to(outside)

    with pytest.raises(ValueError, match="escapes docs/agent-ledger"):
        module.append_gemini_ledger_entry(
            body=_entry_body("Escaping symlink"),
            ledger_dir=ledger_dir,
            now=FIXED_NOW,
        )

    assert outside.read_text(encoding="utf-8") == "outside-before\n"


def test_append_gemini_entry_fails_closed_when_ledger_directory_symlink_escapes(
    tmp_path: Path,
):
    module = _ledger_module()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    outside_dir = tmp_path / "outside-ledger"
    outside_dir.mkdir()
    ledger_dir = docs_dir / "agent-ledger"
    ledger_dir.symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes docs/agent-ledger"):
        module.append_gemini_ledger_entry(
            body=_entry_body("Escaping directory symlink"),
            ledger_dir=ledger_dir,
            now=FIXED_NOW,
        )

    assert not (outside_dir / "2026-06-02.md").exists()


def test_append_gemini_entry_fails_closed_when_symlink_target_has_ledger_tail(
    tmp_path: Path,
):
    module = _ledger_module()
    repo_docs_dir = tmp_path / "repo" / "docs"
    repo_docs_dir.mkdir(parents=True)
    outside_ledger_dir = tmp_path / "outside" / "docs" / "agent-ledger"
    outside_ledger_dir.mkdir(parents=True)
    ledger_dir = repo_docs_dir / "agent-ledger"
    ledger_dir.symlink_to(outside_ledger_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes docs/agent-ledger"):
        module.append_gemini_ledger_entry(
            body=_entry_body("Escaping same-tail directory symlink"),
            ledger_dir=ledger_dir,
            now=FIXED_NOW,
        )

    assert not (outside_ledger_dir / "2026-06-02.md").exists()


def test_append_gemini_entry_fails_closed_when_parent_directory_symlink_escapes(
    tmp_path: Path,
):
    module = _ledger_module()
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    outside_docs_dir = tmp_path / "outside" / "docs"
    outside_ledger_dir = outside_docs_dir / "agent-ledger"
    outside_ledger_dir.mkdir(parents=True)
    (repo_dir / "docs").symlink_to(outside_docs_dir, target_is_directory=True)
    ledger_dir = repo_dir / "docs" / "agent-ledger"

    with pytest.raises(ValueError, match="escapes docs/agent-ledger"):
        module.append_gemini_ledger_entry(
            body=_entry_body("Escaping parent directory symlink"),
            ledger_dir=ledger_dir,
            now=FIXED_NOW,
        )

    assert not (outside_ledger_dir / "2026-06-02.md").exists()
