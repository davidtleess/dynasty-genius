"""Governed sprint-closeout verifier (spec 2026-06-14). Pre-ship tollgate:
ENFORCE deterministic checks, REPORT human-audit surfaces, REMIND human-judgment
gates. Read-only; never installs/downloads or mutates source/artifacts/git."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

ENFORCE, REPORT, REMIND = "ENFORCE", "REPORT", "REMIND"


@dataclass
class CheckResult:
    name: str
    tier: str
    passed: bool | None  # None for REPORT/REMIND (no verdict)
    detail: str


ARTIFACT_DIRS = ("app/data/",)
FE_DIR = "frontend/"


class _Completed:
    """Uniform result so a missing binary fails loud (rc 127) instead of crashing (F3)."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _subprocess_run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd or str(_REPO_ROOT), capture_output=True, text=True)
    except FileNotFoundError as exc:
        return _Completed(127, "", f"{cmd[0]}: not found ({exc})")


def _lines(out: str) -> list[str]:
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _git(cmd: list[str], run) -> list[str]:
    """Run a git command; FAIL LOUD on nonzero (e.g., a missing --base) rather than
    returning an empty surface that would silently skip checks (F3)."""
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"git failed ({r.returncode}): {' '.join(cmd)} :: {(r.stderr or '').strip()}")
    return _lines(r.stdout)


def changed_paths(base: str = "origin/main", run=_subprocess_run) -> set[str]:
    """Union of committed (base...HEAD), staged, unstaged, and untracked paths. Fail-loud on git error."""
    paths: set[str] = set()
    paths |= set(_git(["git", "diff", "--name-only", f"{base}...HEAD"], run))
    paths |= set(_git(["git", "diff", "--name-only", "--cached"], run))
    paths |= set(_git(["git", "diff", "--name-only"], run))
    paths |= set(_git(["git", "ls-files", "--others", "--exclude-standard"], run))
    return paths


def added_paths(base: str = "origin/main", run=_subprocess_run) -> set[str]:
    """Paths added (A) vs base — committed, STAGED, and untracked (F2). Fail-loud on git error."""
    added = set(_git(["git", "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD"], run))
    added |= set(_git(["git", "diff", "--name-only", "--diff-filter=A", "--cached"], run))
    added |= set(_git(["git", "ls-files", "--others", "--exclude-standard"], run))
    return added


def detect_surfaces(paths: set[str], added: set[str]) -> dict:
    return {
        "frontend": any(p.startswith(FE_DIR) for p in paths),
        "scripts": sorted(p for p in paths if p.startswith("scripts/") and p.endswith(".py")),
        "artifacts": sorted(p for p in paths if p.startswith(ARTIFACT_DIRS)),
        "new_files": sorted(added),
    }
