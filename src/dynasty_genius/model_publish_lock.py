"""A retrain is publishing model bundles: scorers must not read the set mid-swap.

Publishing a retrain replaces four pickles and a manifest as FIVE separate writes.
``com.davidleess.dynasty-model-pvo-refresh`` fires at 11:30 and 14:00, and
``run_pvo_refresh.py`` contains no lock of any kind -- measured 2026-08-31,
``grep -c "flock\\|lockf\\|LOCK\\|\\.lock"`` returns 0. A scorer starting in that gap reads
a half-replaced set, scores the whole universe from it, and publishes the result as live
serving state **with a green receipt**, because from its point of view nothing failed.

On 2026-08-31 that was avoided only because two lanes compared clocks -- and both were
reading a stale one, so the avoidance was luck as much as discipline.

NOT the manifest window. ``train_engine_b.write_manifest`` became atomic the same day, so
the manifest can no longer be read truncated. What remains is that the manifest and the
bundles it names are not replaced atomically *together*.

The house pattern, followed rather than reinvented: ``backup_irreplaceable_data.py:54`` and
``backup_nflverse_vintages.py:52`` both write an ``app/data/ops/*_active.json`` sentinel,
and ``run_capture_gap_alert.py:1073`` already consumes one. Their payload carries a **pid**
for a stated reason -- so a reader can ask "is that run still going?" instead of guessing
from elapsed time. This copies that, because a dead pid is a faster and more honest answer
than any timeout.

TWO INDEPENDENT WAYS TO STOP BLOCKING, and both are required. A stale lock that silently
stops the daily chain is a WORSE defect than the race it prevents:
  - the writing process is gone  -> stale, ignore
  - the sentinel is older than ``max_age_hours`` -> stale, ignore, even if a pid matches
    (pids are recycled, and a recycled pid must not wedge the chain forever)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

SENTINEL_REL_PATH = "app/data/ops/model_publish_active.json"

# A retrain is minutes. Two hours is generous enough that a slow one is never cut off, and
# short enough that a crashed one blocks at most a single scheduled slot.
DEFAULT_MAX_AGE_HOURS = 2.0


def sentinel_path(repo_root: Path) -> Path:
    return Path(repo_root) / SENTINEL_REL_PATH


def write_sentinel(
    repo_root: Path, *, run_id: str, started_at: datetime, pid: Optional[int] = None
) -> Path:
    """Declare a model publish in flight. Call BEFORE the first bundle write."""
    path = sentinel_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "started_at": started_at.isoformat(),
                "pid": os.getpid() if pid is None else pid,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return path


def clear_sentinel(repo_root: Path) -> None:
    """Call AFTER the last bundle write, and on the failure path too.

    Never raises: a retrain must not fail because its bookkeeping did.
    """
    try:
        sentinel_path(repo_root).unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False
    return True


def blocking_publish(
    repo_root: Path,
    *,
    now: datetime,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
) -> Optional[dict[str, Any]]:
    """The in-flight publish that should stop a scorer, or None.

    Returns None for every stale case, so a crashed retrain cannot wedge the chain.
    Unparseable sentinels are treated as stale rather than blocking: refusing to score
    because a bookkeeping file is malformed would be the cry-wolf failure this is meant
    to avoid.
    """
    path = sentinel_path(repo_root)
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    started_raw = payload.get("started_at")
    try:
        started = datetime.fromisoformat(str(started_raw))
    except (TypeError, ValueError):
        return None
    if started.tzinfo is None or now.tzinfo is None:
        return None
    if now - started > timedelta(hours=max_age_hours):
        return None
    if not _pid_alive(payload.get("pid")):
        return None
    return payload
