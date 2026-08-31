"""Staging scratch from a run that died before its own cleanup must be reclaimed.

``run_backup`` removes its OWN staging directory at the end of a successful run and
nothing ever sweeps the root, so a run killed mid-flight leaks its scratch permanently
and no check notices. Measured 2026-08-31: 4.3GB in two directories, from runs that died
2026-08-01 (1.9G) and 2026-08-12 (2.4G). The 08-01 death is even recorded in this
script's own header comment -- the event was documented, the disk it cost was not.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 31, 14, 15, 3, tzinfo=timezone.utc)


def _mod():
    spec = importlib.util.spec_from_file_location(
        "backup_irreplaceable_data", ROOT / "scripts" / "backup_irreplaceable_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_dir(root: Path, run_id: str, *, size: int = 32) -> Path:
    d = root / run_id
    d.mkdir(parents=True)
    (d / "payload.bin").write_bytes(b"x" * size)
    return d


def test_a_dead_runs_scratch_is_reclaimed_and_reported(tmp_path: Path) -> None:
    root = tmp_path / "backup_staging"
    dead = _run_dir(root, "20260801T141848Z", size=100)

    reclaimed = _mod().sweep_stale_staging(
        root, current_run_id="20260831T141503Z", now=NOW
    )

    assert not dead.exists()
    assert [r["run_id"] for r in reclaimed] == ["20260801T141848Z"]
    assert reclaimed[0]["bytes"] >= 100


def test_the_current_run_is_never_swept(tmp_path: Path) -> None:
    """A sweep that can delete the directory it is about to fill is worse than a leak."""
    root = tmp_path / "backup_staging"
    mine = _run_dir(root, "20260801T141848Z")

    reclaimed = _mod().sweep_stale_staging(
        root, current_run_id="20260801T141848Z", now=NOW
    )

    assert mine.exists()
    assert reclaimed == []


def test_a_recent_directory_is_kept_so_a_concurrent_run_survives(tmp_path: Path) -> None:
    root = tmp_path / "backup_staging"
    recent_id = (NOW - timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
    recent = _run_dir(root, recent_id)

    reclaimed = _mod().sweep_stale_staging(
        root, current_run_id="20260831T141503Z", now=NOW
    )

    assert recent.exists()
    assert reclaimed == []


def test_an_unrecognised_name_is_left_alone(tmp_path: Path) -> None:
    """Never delete what the sweep cannot identify. A directory whose name is not a run
    id was put there by something else, and guessing is how a sweep becomes a defect."""
    root = tmp_path / "backup_staging"
    root.mkdir(parents=True)
    stranger = root / "please-do-not-delete-me"
    stranger.mkdir()
    (stranger / "file").write_text("evidence")

    reclaimed = _mod().sweep_stale_staging(
        root, current_run_id="20260831T141503Z", now=NOW
    )

    assert stranger.exists()
    assert reclaimed == []


def test_an_absent_staging_root_is_not_an_error(tmp_path: Path) -> None:
    reclaimed = _mod().sweep_stale_staging(
        tmp_path / "never_created", current_run_id="20260831T141503Z", now=NOW
    )
    assert reclaimed == []


def test_housekeeping_failure_never_raises(tmp_path: Path, monkeypatch) -> None:
    """This runs at the top of a backup. A bookkeeping failure must never cancel one --
    the same rule the surrounding module already states for its marker write."""
    module = _mod()
    root = tmp_path / "backup_staging"
    _run_dir(root, "20260801T141848Z")

    def boom(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(module.shutil, "rmtree", boom)

    assert module.sweep_stale_staging(
        root, current_run_id="20260831T141503Z", now=NOW
    ) == []
