"""Governed sprint-closeout verifier (spec 2026-06-14). Pre-ship tollgate:
ENFORCE deterministic checks, REPORT human-audit surfaces, REMIND human-judgment
gates. Read-only; never installs/downloads or mutates source/artifacts/git."""
from __future__ import annotations

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
