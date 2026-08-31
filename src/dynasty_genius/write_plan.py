"""Preflight write plans: what a runner WILL write, and whether any of it is live.

Every publish-defaulting runner already had a ``--preflight`` that printed a flat
settings dict. That is not the same thing, and the difference is what let a careful
operator clobber production on 2026-08-31.

The settings dump prints ``"runtime_dir": "app/data/valuation_runtime"`` among a dozen
sibling keys. A reader scanning it sees a *setting*. Nothing on the line says "this is
the live serving directory and this run will overwrite it", and nothing distinguishes
the two paths that get written from the nine that get read. So the operator redirected
every flag whose name contained "path", missed the one whose name did not, read the
settings dump, and saw nothing wrong -- because there was nothing in it to see.

A preflight should answer one question: **what will this write, and is any of it live?**

``target`` is deliberately coarse. Anything landing inside the repo's ``app/`` tree is
LIVE, including a scratch subdirectory someone created there -- writing into the serving
tree is the risk, and a rule an operator can restate from memory is worth more than a
precise one they cannot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

LIVE = "LIVE"
SANDBOX = "SANDBOX"


def _resolved(path: Path | str, repo_root: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = repo_root / p
    # resolve() so a symlink pointing into the serving tree is classified by where it
    # actually lands, not by how it is spelled. The 2026-08-31 head_a incident was a
    # write that reached the trunk THROUGH a symlink.
    return p.resolve()


def classify(path: Path | str, *, repo_root: Optional[Path] = None) -> str:
    """LIVE if the write lands inside the repo's ``app/`` tree, else SANDBOX."""
    root = (repo_root or _REPO_ROOT).resolve()
    resolved = _resolved(path, root)
    app = root / "app"
    return LIVE if (resolved == app or app in resolved.parents) else SANDBOX


def write_plan(
    *,
    writes: Mapping[str, object],
    reads: Optional[Mapping[str, object]] = None,
    repo_root: Optional[Path] = None,
) -> dict:
    """Build the preflight payload. ``None`` values are dropped as not-in-play.

    Returns ``writes`` sorted by role, each carrying its resolved path and LIVE/SANDBOX,
    a ``live_writes`` count, and a ``verdict`` written for a human in a hurry.
    """
    root = (repo_root or _REPO_ROOT).resolve()

    write_rows = [
        {
            "role": role,
            "path": str(_resolved(value, root)),
            "target": classify(value, repo_root=root),
        }
        for role, value in sorted(writes.items())
        if value is not None
    ]
    read_rows = [
        {"role": role, "path": str(_resolved(value, root))}
        for role, value in sorted((reads or {}).items())
        if value is not None
    ]

    live = [r for r in write_rows if r["target"] == LIVE]
    if live:
        noun = "artifact" if len(live) == 1 else "artifacts"
        verdict = (
            f"WILL OVERWRITE {len(live)} LIVE SERVING {noun.upper()}. "
            "This is NOT a sandboxed run."
        )
    elif write_rows:
        verdict = "No live writes — every write target is outside the serving tree."
    else:
        verdict = "No writes declared."

    return {
        "preflight": True,
        "writes": write_rows,
        "reads": read_rows,
        "live_writes": len(live),
        "verdict": verdict,
    }
