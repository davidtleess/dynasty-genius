"""Sleep catch-up guard for the scheduled launchd jobs.

macOS drops a StartCalendarInterval occurrence the machine sleeps through:
on wake, launchd registers the next occurrence and never runs the missed one
(measured live 2026-08-27 — the 06:15 capture was skipped straight to 08-28).

The guard runs every few minutes while awake. For each job occurrence that
passed within its slot's lookback — yesterday + today for daily slots (sleep
gaps do not respect midnight), the whole 7-day period for weekly slots (no
newer occurrence supersedes a weekly miss) — it reads the
job's receipt artifact — the same status files the freshness system trusts,
embedded timestamps first, mtime only when the artifact declares no timestamp
field or is too mangled to parse — and kicks any occurrence no run attempt has
served, in schedule order, re-reading receipts between kicks so one fresh run
serves every occurrence it covers.

Schedules derive from the launchd plists via launchd_schedules — never a
hand-kept list. A run that happened and failed still counts as attempted
(retries are the health system's territory; re-kicking a deterministic
failure every tick would mask it). A KICK that failed is the opposite case:
surfaced in the report and never recorded as served, so it retries next tick.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from datetime import tzinfo as TzInfo
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

from src.dynasty_genius.launchd_schedules import JobSchedule, Slot

GRACE = timedelta(minutes=10)
# launchd can stamp a run marginally before the calendar tick it served
STARTUP_SLACK = timedelta(seconds=120)
# how far back plan_kicks looks for a daily slot: yesterday + today (a newer
# occurrence supersedes an old miss). A weekly slot has no newer occurrence to
# supersede it for six more days, so its lookback spans its whole period.
DAILY_LOOKBACK_DAYS = 1
WEEKLY_LOOKBACK_DAYS = 6


@dataclass(frozen=True)
class ReceiptSpec:
    receipt_path: str
    timestamp_fields: tuple[str, ...]


@dataclass(frozen=True)
class JobSpec:
    label: str
    slots: tuple[Slot, ...]
    receipt: ReceiptSpec


@dataclass(frozen=True)
class Kick:
    label: str
    occurrence: datetime

    @property
    def key(self) -> str:
        return occurrence_key(self.label, self.occurrence)


def occurrence_key(label: str, occurrence: datetime) -> str:
    return f"{label}|{occurrence.strftime('%Y-%m-%d|%H:%M')}"


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def plan_kicks(
    *,
    now: datetime,
    specs: list[JobSpec],
    receipt_ts: dict[str, datetime | None],
    running: set[str],
    already_kicked: set[str],
    grace: timedelta = GRACE,
) -> list[Kick]:
    """Return the unserved occurrences to kick, in schedule order."""
    kicks: list[Kick] = []
    for spec in specs:
        if spec.label in running:
            continue
        ts = receipt_ts.get(spec.label)
        for slot in spec.slots:
            lookback = (
                WEEKLY_LOOKBACK_DAYS if slot.weekday is not None else DAILY_LOOKBACK_DAYS
            )
            for offset in range(lookback, -1, -1):
                day = now.date() - timedelta(days=offset)
                if not slot.fires_on(day):
                    continue
                occurrence = datetime.combine(
                    day, time(slot.hour, slot.minute), tzinfo=now.tzinfo
                )
                if now < occurrence + grace:
                    continue
                if ts is not None and ts >= occurrence - STARTUP_SLACK:
                    continue
                kick = Kick(spec.label, occurrence)
                if kick.key in already_kicked:
                    continue
                kicks.append(kick)
    return sorted(kicks, key=lambda k: k.occurrence)


def read_receipt_ts(
    path: Path, timestamp_fields: tuple[str, ...], *, tz: TzInfo
) -> datetime | None:
    """Timestamp of the last run attempt a receipt records, or None if absent.

    Embedded timestamps win; mtime is the fallback for artifacts that declare
    no timestamp field, and for a receipt too mangled to parse — a half-written
    or reshaped file is still evidence a producer just ran, and one bad receipt
    must never cost the other jobs their sleep protection.
    """
    if not path.exists():
        return None
    if timestamp_fields:
        try:
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                for field_name in timestamp_fields:
                    raw = payload.get(field_name)
                    if isinstance(raw, str):
                        ts = datetime.fromisoformat(raw)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=tz)
                        return ts
        except Exception:
            pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=tz)
    except OSError:
        return None


@dataclass
class GuardState:
    """One kick per occurrence, remembered across ticks in a small ledger."""

    # occurrence key -> iso timestamp of the kick
    kicked: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "GuardState":
        try:
            payload = json.loads(path.read_text())
            kicked = payload.get("kicked", {})
            if isinstance(kicked, dict):
                return cls(
                    kicked={
                        key: stamp
                        for key, stamp in kicked.items()
                        if isinstance(stamp, str)
                    }
                )
        except (OSError, ValueError):
            pass
        return cls()

    def record(self, key: str, *, at: datetime) -> None:
        self.kicked[key] = at.isoformat()

    def save(self, path: Path, *, now: datetime, keep: timedelta) -> None:
        cutoff = now - keep
        pruned: dict[str, str] = {}
        for key, stamp in self.kicked.items():
            # a bad stamp is dropped, never fatal: a save that raises would
            # stop the ledger from ever persisting, and the re-kicks that
            # follow are exactly the retry loop this module forbids
            try:
                if datetime.fromisoformat(stamp) >= cutoff:
                    pruned[key] = stamp
            except (TypeError, ValueError):
                continue
        atomic_write_json(path, {"kicked": pruned})


def build_specs(
    schedules: list[JobSchedule],
    *,
    receipts: dict[str, ReceiptSpec],
    unguarded: dict[str, str],
) -> tuple[list[JobSpec], list[str]]:
    """Join derived schedules to receipt knowledge.

    Returns the guarded specs plus the labels that are scheduled but neither
    guarded nor explicitly unguarded — surfaced, never silently skipped.
    """
    specs: list[JobSpec] = []
    unconfigured: list[str] = []
    for schedule in schedules:
        if schedule.label in unguarded:
            continue
        receipt = receipts.get(schedule.label)
        # empty slots on a guarded label means an unparseable plist or a slot
        # that failed validation — coverage was lost, which must be loud
        if receipt is None or not schedule.slots:
            unconfigured.append(schedule.label)
            continue
        specs.append(
            JobSpec(
                label=schedule.label,
                slots=tuple(schedule.slots),
                receipt=receipt,
            )
        )
    return specs, unconfigured


def run_once(
    *,
    now_fn: Callable[[], datetime],
    specs: list[JobSpec],
    read_receipts: Callable[[], dict[str, datetime | None]],
    read_running: Callable[[], set[str]],
    state: GuardState,
    kickstart: Callable[[str], bool],
    wait_for_exit: Callable[[str], None],
    persist: Callable[[], None],
    max_kicks: int = 50,
) -> dict:
    """Kick unserved occurrences one at a time, re-planning from fresh
    receipts after each so one run serves every occurrence it covers, and the
    chain keeps its schedule order. Returns a report payload.

    A failed kickstart is reported and NOT recorded as served — it retries on
    the next tick, when the operator may have fixed the unloaded job. Within
    this run it is skipped so the loop cannot spin on it.
    """
    kicked: list[dict] = []
    failures: list[dict] = []
    failed_keys: set[str] = set()
    while len(kicked) < max_kicks:
        kicks = plan_kicks(
            now=now_fn(),
            specs=specs,
            receipt_ts=read_receipts(),
            running=read_running(),
            already_kicked=set(state.kicked) | failed_keys,
        )
        if not kicks:
            break
        kick = kicks[0]
        if not kickstart(kick.label):
            failures.append({"key": kick.key, "label": kick.label})
            failed_keys.add(kick.key)
            continue
        state.record(kick.key, at=now_fn())
        persist()
        kicked.append(
            {
                "key": kick.key,
                "label": kick.label,
                "occurrence": kick.occurrence.isoformat(),
            }
        )
        # wait only when something is actually chained behind this kick: the
        # probe treats the just-kicked job as running, so its own remaining
        # occurrences (which its fresh receipt will serve) don't force a wait
        pending = plan_kicks(
            now=now_fn(),
            specs=specs,
            receipt_ts=read_receipts(),
            running=read_running() | {kick.label},
            already_kicked=set(state.kicked) | failed_keys,
        )
        if not pending:
            break
        wait_for_exit(kick.label)
    return {"checked": len(specs), "kicked": kicked, "kick_failures": failures}


def load_config(path: Path) -> tuple[TzInfo, dict[str, ReceiptSpec], dict[str, str]]:
    payload = json.loads(path.read_text())
    tz = ZoneInfo(payload["timezone"])
    receipts = {
        label: ReceiptSpec(
            receipt_path=entry["receipt_path"],
            timestamp_fields=tuple(entry.get("timestamp_fields", [])),
        )
        for label, entry in payload.get("receipts", {}).items()
    }
    unguarded = dict(payload.get("unguarded", {}))
    return tz, receipts, unguarded
