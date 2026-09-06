"""Run-scoped output directories that refuse to overwrite.

AGENT-HOOK §5: new artifacts go to ``runs/<UTC timestamp>/``, never in place. A 23-round
run record was overwritten with no backup on 2026-08-17; that is why ``FileExistsError``
here is not caught anywhere.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

__all__ = ["create_run_dir", "utc_run_id"]


def utc_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ")


def create_run_dir(root: Path | str, *, run_id: str | None = None, name: str | None = None) -> Path:
    path = Path(root) / (run_id or utc_run_id())
    if name:
        path = path / name
    if path.exists():
        raise FileExistsError(f"run directory already exists, refusing to overwrite: {path}")
    path.mkdir(parents=True, exist_ok=False)
    return path
