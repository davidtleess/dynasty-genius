"""A scorer must not read the model set while a retrain is replacing it.

Five separate writes (four pickles + the manifest) with no lock, and a scheduled scorer
at 11:30 and 14:00. The failure mode is the day's signature: a mixed model set scored and
published as live serving state with a green receipt, because nothing errored.

The tests that matter most here are the ones that prove it STOPS blocking. A stale lock
that silently stops the daily chain is a worse defect than the race it prevents.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.dynasty_genius.model_publish_lock import (
    SENTINEL_REL_PATH,
    blocking_publish,
    clear_sentinel,
    sentinel_path,
    write_sentinel,
)

NOW = datetime(2026, 8, 31, 20, 45, tzinfo=timezone.utc)


def _write(root: Path, *, started: datetime, pid: int, run_id: str = "R1") -> Path:
    p = root / SENTINEL_REL_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"run_id": run_id, "started_at": started.isoformat(), "pid": pid}))
    return p


def test_a_live_publish_blocks_the_scorer(tmp_path: Path) -> None:
    _write(tmp_path, started=NOW - timedelta(minutes=3), pid=os.getpid())
    blocking = blocking_publish(tmp_path, now=NOW)
    assert blocking is not None
    assert blocking["run_id"] == "R1"


def test_a_dead_writer_does_not_block(tmp_path: Path, monkeypatch) -> None:
    """The fastest honest answer to 'is that run still going?'. A retrain killed
    mid-publish must not wedge the daily chain until a timeout expires."""
    import src.dynasty_genius.model_publish_lock as mod

    _write(tmp_path, started=NOW - timedelta(minutes=3), pid=424242)

    def gone(_pid, _sig):
        raise ProcessLookupError

    monkeypatch.setattr(mod.os, "kill", gone)
    assert blocking_publish(tmp_path, now=NOW) is None


def test_an_old_sentinel_does_not_block_even_with_a_live_pid(tmp_path: Path) -> None:
    """Pids are recycled. A recycled pid must not wedge the chain forever, so age is a
    second independent escape rather than a fallback."""
    _write(tmp_path, started=NOW - timedelta(hours=3), pid=os.getpid())
    assert blocking_publish(tmp_path, now=NOW) is None


def test_no_sentinel_is_the_normal_case_and_blocks_nothing(tmp_path: Path) -> None:
    assert blocking_publish(tmp_path, now=NOW) is None


def test_a_malformed_sentinel_is_stale_not_blocking(tmp_path: Path) -> None:
    """Refusing to score because a bookkeeping file is corrupt would be the cry-wolf
    failure this guard exists to avoid."""
    p = tmp_path / SENTINEL_REL_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not json")
    assert blocking_publish(tmp_path, now=NOW) is None


def test_a_naive_timestamp_blocks_nothing_rather_than_being_guessed_at(
    tmp_path: Path,
) -> None:
    _write(tmp_path, started=datetime(2026, 8, 31, 20, 42), pid=os.getpid())
    assert blocking_publish(tmp_path, now=NOW) is None


def test_write_then_clear_round_trips(tmp_path: Path) -> None:
    path = write_sentinel(tmp_path, run_id="20260831T204458Z", started_at=NOW)
    assert path == sentinel_path(tmp_path)
    payload = json.loads(path.read_text())
    assert payload["run_id"] == "20260831T204458Z"
    assert payload["pid"] == os.getpid()
    assert blocking_publish(tmp_path, now=NOW) is not None

    clear_sentinel(tmp_path)
    assert not path.exists()
    assert blocking_publish(tmp_path, now=NOW) is None


def test_clearing_an_absent_sentinel_never_raises(tmp_path: Path) -> None:
    """clear_sentinel sits on a retrain's failure path. It must not turn a failed
    retrain into a crashed one."""
    clear_sentinel(tmp_path)
