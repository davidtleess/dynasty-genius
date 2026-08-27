"""Derive job schedules from launchd plists — never a hand-kept list.

Hoisted verbatim from scripts/run_capture_gap_alert.py (DG-044) on 2026-08-27
so the catch-up guard consumes the same single source of schedule truth: the
guard's first config hand-duplicated the plists' schedules and immediately
shipped two drift casualties (three Weekday=2 jobs declared daily, one job
missing). The plists are the schedule; everything else derives.
"""

from __future__ import annotations

import plistlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Slot:
    """One StartCalendarInterval entry. ``weekday`` uses launchd's convention
    (0/7 = Sunday, 2 = Tuesday); ``None`` means every day."""

    hour: int
    minute: int
    weekday: int | None = None

    def fires_on(self, day: date) -> bool:
        if self.weekday is None:
            return True
        # launchd: 0 or 7 = Sunday, 1-6 = Mon-Sat; Python: Monday = 0
        return self.weekday % 7 == (day.weekday() + 1) % 7


@dataclass(frozen=True)
class JobSchedule:
    label: str
    slots: list[Slot]
    path: Path


def derive_job_schedules(plist_dir: Path) -> list[JobSchedule]:
    """Derive the sweep's label list from the plist directory itself.

    Never a hand-kept list (spec step 7): a producer added later without anyone
    touching this script must not be invisible to it. Non-recursive on purpose:
    ``ops/launchd/retired/`` must never leak back into the sweep after SR-09.
    """

    schedules: list[JobSchedule] = []
    for path in sorted(plist_dir.glob("*.plist")):
        try:
            data = plistlib.loads(path.read_bytes())
        except Exception:
            # An unparseable plist still names a job we cannot watch; carry it
            # under its filename so the sweep reports it instead of hiding it.
            data = {}
        label = data.get("Label") or path.stem
        calendar = data.get("StartCalendarInterval")
        entries = (
            calendar
            if isinstance(calendar, list)
            else [calendar]
            if isinstance(calendar, dict)
            else []
        )
        slots: list[Slot] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                hour = int(entry.get("Hour", 0))
                minute = int(entry.get("Minute", 0))
                weekday = int(entry["Weekday"]) if "Weekday" in entry else None
            except (TypeError, ValueError):
                continue
            # A typo'd slot (Minute=75) must never crash the whole alert at
            # now.replace() — the job still appears under its label, and the
            # other classes still cover it.
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                continue
            slots.append(Slot(hour=hour, minute=minute, weekday=weekday))
        schedules.append(JobSchedule(label=label, slots=slots, path=path))
    return schedules
