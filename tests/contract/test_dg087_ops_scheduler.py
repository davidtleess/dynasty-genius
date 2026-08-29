"""Contract: the API launchd service + the weekly replay-verify job (DG-087).

SR-12: the product must be openable without a terminal. The API becomes a
launchd KeepAlive SERVICE (``com.davidleess.dynasty-api``) — RunAtLoad +
KeepAlive, never a calendar slot — serving uvicorn on 127.0.0.1:8000.
Two constraints are load-bearing and pinned here:

- **No ``--reload``**: reload watches the working tree, and app/data holds
  ~15 GB — a watcher over it thrashes the machine (spec SR-12, verbatim).
- **WorkingDirectory = the trunk repo root**: app/main.py mounts
  ``app/data/assets/headshots`` and ``frontend/dist`` via CWD-relative
  ``Path(...)`` (main.py:63, :76) — the wrong WD serves the API but 404s
  on ``/``. The trunk, never a worktree.

Rides-along (DG-050 scheduling addendum, David's panel 2026-08-29): the
replay-reproducibility harness joins launchd WEEKLY as
``com.davidleess.dynasty-replay-verify`` — Monday 12:00, clear of the
06:15-10:30 capture cluster and 15+ min past the 11:30 retry slot. The
harness is read-only over the stores and writes its own receipts to
``app/data/ops/`` (its defaults — no override here).

Guard registration is part of the contract, because the guard enforces it
(TestConfigCoversTheRealPlists fails on any unexplained plist):

- replay-verify is GUARDED: a Monday-noon slot slept through must be
  re-kicked, and the weekly lookback covers its whole 7-day period. Its
  receipt is the harness's own ``replay_reproducibility_latest.json``
  (embedded ``generated_at`` UTC timestamp).
- dynasty-api is UNGUARDED with a written reason: it is a KeepAlive
  service with no slots to miss — launchd itself is its supervisor. It
  must NOT get a receipts entry: build_specs surfaces any receipt-bearing
  label with empty slots as unconfigured, which would flip the guard's
  status to degraded forever.

Both plists COMMIT UNLOADED — bootstrap is David's own gesture at the
machine, exactly like every sibling plist in ops/launchd/.
"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

from src.dynasty_genius.catchup_guard import build_specs, load_config
from src.dynasty_genius.launchd_schedules import derive_job_schedules

ROOT = Path("/Users/davidleess/dynasty-genius-product")
REPO_ROOT = Path(__file__).resolve().parents[2]

API_PLIST = Path("ops/launchd/com.davidleess.dynasty-api.plist")
REPLAY_PLIST = Path("ops/launchd/com.davidleess.dynasty-replay-verify.plist")

API_LABEL = "com.davidleess.dynasty-api"
REPLAY_LABEL = "com.davidleess.dynasty-replay-verify"

GUARD_CONFIG = Path("app/config/catchup_guard.json")


def _plist(path: Path) -> dict:
    return plistlib.loads(path.read_bytes())


# --- the API service ------------------------------------------------------------


def test_api_plist_is_a_keepalive_uvicorn_service() -> None:
    data = _plist(API_PLIST)
    assert data["Label"] == API_LABEL
    assert data["ProgramArguments"] == [
        str(ROOT / ".venv" / "bin" / "python3.14"),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is True
    assert data["StandardOutPath"] == str(ROOT / "app/data/logs/dynasty_api.out.log")
    assert data["StandardErrorPath"] == str(ROOT / "app/data/logs/dynasty_api.err.log")


def test_api_plist_never_passes_reload() -> None:
    # --reload watches the working tree; app/data is ~15 GB (spec SR-12)
    args = _plist(API_PLIST)["ProgramArguments"]
    assert "--reload" not in args


def test_api_working_directory_is_the_trunk_never_a_worktree() -> None:
    # app/main.py:63 and :76 mount headshots + frontend/dist CWD-relative:
    # the wrong WD serves the API but 404s on / — and a worktree WD would
    # serve a stale or absent frontend build against live data
    assert _plist(API_PLIST)["WorkingDirectory"] == str(ROOT)


def test_api_is_a_service_not_a_scheduled_job() -> None:
    data = _plist(API_PLIST)
    assert "StartCalendarInterval" not in data
    assert "StartInterval" not in data


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_api_plist_is_valid_plist() -> None:
    proc = subprocess.run(
        ["plutil", "-lint", str(API_PLIST)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# --- the weekly replay-verify job -----------------------------------------------


def test_replay_verify_plist_runs_the_harness_weekly_monday_noon() -> None:
    data = _plist(REPLAY_PLIST)
    assert data["Label"] == REPLAY_LABEL
    assert data["ProgramArguments"] == [
        str(ROOT / ".venv" / "bin" / "python3.14"),
        str(ROOT / "scripts" / "run_replay_reproducibility.py"),
        "--repo-root",
        str(ROOT),
    ]
    # launchd Weekday=1 is Monday; 12:00 is clear of the capture cluster
    # (06:15-10:30) and 15+ min past the 11:30 retry slot (DG-050 addendum)
    assert data["StartCalendarInterval"] == {"Weekday": 1, "Hour": 12, "Minute": 0}
    assert data["RunAtLoad"] is False
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StandardOutPath"] == str(ROOT / "app/data/logs/replay_verify.out.log")
    assert data["StandardErrorPath"] == str(ROOT / "app/data/logs/replay_verify.err.log")


def test_replay_verify_receipts_go_where_the_harness_writes_by_default() -> None:
    # No --ops-root override: the receipt location is the harness's own
    # default (app/data/ops/ under --repo-root), so the guard's receipt_path
    # below and the harness agree by construction.
    args = _plist(REPLAY_PLIST)["ProgramArguments"]
    assert "--ops-root" not in args


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS-only")
def test_replay_verify_plist_is_valid_plist() -> None:
    proc = subprocess.run(
        ["plutil", "-lint", str(REPLAY_PLIST)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# --- guard registration ----------------------------------------------------------


def test_replay_verify_is_guarded_by_its_own_receipt() -> None:
    # A slept-through Monday noon must be re-kicked: the weekly lookback
    # covers the whole 7-day period, but only for a GUARDED label.
    _, receipts, _ = load_config(GUARD_CONFIG)
    spec = receipts.get(REPLAY_LABEL)
    assert spec is not None, "replay-verify missing from catchup_guard.json receipts"
    assert spec.receipt_path == "app/data/ops/replay_reproducibility_latest.json"
    assert spec.timestamp_fields == ("generated_at",)


def test_replay_verify_slot_derives_as_weekly_monday() -> None:
    # derive_job_schedules is the guard's schedule truth: the slot must
    # survive derivation as weekday=1 (Monday), or the 7-day lookback never
    # applies and the guard treats a missed Monday as unprotected.
    schedules = {s.label: s for s in derive_job_schedules(REPO_ROOT / "ops/launchd")}
    slots = schedules[REPLAY_LABEL].slots
    assert len(slots) == 1
    assert (slots[0].weekday, slots[0].hour, slots[0].minute) == (1, 12, 0)


def test_api_is_explicitly_unguarded_with_a_reason_and_never_a_receipt() -> None:
    _, receipts, unguarded = load_config(GUARD_CONFIG)
    assert API_LABEL in unguarded, (
        "dynasty-api must be explicitly unguarded: it is a KeepAlive service "
        "with no calendar slots — otherwise the guard reports it unconfigured "
        "and degrades every tick"
    )
    assert isinstance(unguarded[API_LABEL], str) and unguarded[API_LABEL]
    # a receipts entry for a slotless label is surfaced as unconfigured by
    # build_specs — registration there would degrade the guard, not help it
    assert API_LABEL not in receipts


def test_real_config_over_real_plists_leaves_nothing_unconfigured() -> None:
    # The end-to-end drift check the guard itself runs every tick: joined
    # against the REAL plist directory and the REAL config, no label may
    # land in unconfigured — that is the guard's degraded state.
    tz, receipts, unguarded = load_config(GUARD_CONFIG)
    schedules = derive_job_schedules(REPO_ROOT / "ops/launchd")
    specs, unconfigured = build_specs(schedules, receipts=receipts, unguarded=unguarded)
    assert unconfigured == [], f"guard would degrade on: {unconfigured}"
    assert REPLAY_LABEL in {s.label for s in specs}
    assert API_LABEL not in {s.label for s in specs}
