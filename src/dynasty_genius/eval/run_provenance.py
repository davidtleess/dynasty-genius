"""Launch-time provenance for report-only runs.

A run's manifest must name the code that RAN. HEAD read at finish time names whatever the branch
had moved to meanwhile (run 20260906T195728Z recorded 39545f8e while running older code). So the
runner captures this block as its first action and reuses it; it never asks git again.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()


def launch_provenance(repo_root: Path | None = None, argv: list[str] | None = None) -> dict:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    return {
        "git_head": _git(root, "rev-parse", "HEAD"),
        "git_branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git(root, "status", "--porcelain", "--untracked-files=no")),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "argv": list(sys.argv if argv is None else argv),
        "python": sys.version.split()[0],
    }
