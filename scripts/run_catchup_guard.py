"""Kick scheduled launchd jobs the machine slept through.

macOS drops a StartCalendarInterval occurrence it sleeps across (measured
2026-08-27: the 06:15 capture was skipped straight to the next day). This
guard runs every few minutes while awake, derives the schedule from the
launchd plists themselves (never a hand-kept list), reads each job's receipt
artifact — the embedded-timestamp status files the freshness system trusts —
and kickstarts any unserved occurrence within each slot's lookback (daily
slots: yesterday + today; weekly slots: their whole 7-day period, since no
newer occurrence supersedes the miss), in schedule order, re-reading receipts between kicks so one
fresh run serves every occurrence it covers. One kick per occurrence; a run
that failed still counts as attempted (retries are the health system's
territory), but a KICK that failed is surfaced and retried next tick.

    .venv/bin/python3.14 scripts/run_catchup_guard.py
    .venv/bin/python3.14 scripts/run_catchup_guard.py --dry-run   # plan only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.catchup_guard import (  # noqa: E402
    GuardState,
    atomic_write_json,
    build_specs,
    load_config,
    read_receipt_ts,
    run_once,
)
from src.dynasty_genius.launchd_schedules import derive_job_schedules  # noqa: E402

PLIST_DIR = REPO_ROOT / "ops/launchd"
CONFIG_PATH = REPO_ROOT / "app/config/catchup_guard.json"
STATE_PATH = REPO_ROOT / "app/data/ops/catchup_guard_state.json"
STATUS_PATH = REPO_ROOT / "app/data/ops/catchup_guard_status_latest.json"
# must exceed the widest plan_kicks lookback (weekly = 7 days), or a pruned
# ledger entry lets an already-kicked occurrence re-kick
STATE_KEEP = timedelta(days=8)
WAIT_POLL_MAX_SECONDS = 10
WAIT_CAP_SECONDS = 1800
SPAWN_WAIT_SECONDS = 10

GUI_DOMAIN = f"gui/{os.getuid()}"


def _job_pid(label: str) -> int | None:
    proc = subprocess.run(["launchctl", "list", label], capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if '"PID"' in line:
            _, _, value = line.partition("=")
            digits = value.strip().rstrip(";")
            return int(digits) if digits.isdigit() else None
    return None


def _kickstart(label: str) -> bool:
    proc = subprocess.run(
        ["launchctl", "kickstart", f"{GUI_DOMAIN}/{label}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(
            f"kickstart failed for {label}: rc={proc.returncode} "
            f"{proc.stderr.strip()}",
            file=sys.stderr,
        )
    return proc.returncode == 0


def _wait_for_exit(label: str) -> None:
    # "PID never appeared" and "PID appeared then vanished" are different
    # facts: under post-wake load launchd can take seconds to spawn, and
    # concluding "exited" from an early empty poll would overlap the chain.
    # Poll up to SPAWN_WAIT_SECONDS for the PID to appear; once seen (or the
    # spawn window closes), an empty poll means the job is done. Short first
    # sleeps keep a 10-second job from paying a 10-second floor.
    start = time.monotonic()
    deadline = start + WAIT_CAP_SECONDS
    spawn_deadline = start + SPAWN_WAIT_SECONDS
    seen = False
    delay = 1.0
    while time.monotonic() < deadline:
        if _job_pid(label) is not None:
            seen = True
        elif seen or time.monotonic() >= spawn_deadline:
            return
        time.sleep(delay)
        delay = min(delay * 2, WAIT_POLL_MAX_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would be kicked, kick nothing"
    )
    args = parser.parse_args()

    tz, receipts, unguarded = load_config(CONFIG_PATH)
    schedules = derive_job_schedules(PLIST_DIR)
    specs, unconfigured = build_specs(
        schedules, receipts=receipts, unguarded=unguarded
    )

    def read_receipts() -> dict:
        return {
            spec.label: read_receipt_ts(
                REPO_ROOT / spec.receipt.receipt_path,
                spec.receipt.timestamp_fields,
                tz=tz,
            )
            for spec in specs
        }

    def read_running() -> set[str]:
        return {spec.label for spec in specs if _job_pid(spec.label) is not None}

    state = GuardState.load(STATE_PATH)
    now = datetime.now(tz=tz)

    if args.dry_run:
        # same code path and report schema as the real run; the "kicks" land
        # only in a throwaway copy of the ledger and nothing is persisted
        report = run_once(
            now_fn=lambda: datetime.now(tz=tz),
            specs=specs,
            read_receipts=read_receipts,
            read_running=read_running,
            state=GuardState(kicked=dict(state.kicked)),
            kickstart=lambda label: True,
            wait_for_exit=lambda label: None,
            persist=lambda: None,
        )
    else:
        report = run_once(
            now_fn=lambda: datetime.now(tz=tz),
            specs=specs,
            read_receipts=read_receipts,
            read_running=read_running,
            state=state,
            kickstart=_kickstart,
            wait_for_exit=_wait_for_exit,
            persist=lambda: state.save(
                STATE_PATH, now=datetime.now(tz=tz), keep=STATE_KEEP
            ),
        )

    degraded = bool(report["kick_failures"]) or bool(unconfigured)
    status = {
        "generated_at": now.isoformat(),
        "dry_run": args.dry_run,
        "status": "degraded" if degraded else "ok",
        "jobs_checked": report["checked"],
        "jobs_unconfigured": sorted(unconfigured),
        "unguarded": unguarded,
        "kicked": report["kicked"],
        "kick_failures": report["kick_failures"],
    }
    if not args.dry_run:
        atomic_write_json(STATUS_PATH, status)
    if report["kicked"] or report["kick_failures"] or unconfigured or args.dry_run:
        print(json.dumps(status, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
