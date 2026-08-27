"""The daily capture gap alert — the only detection channel that will exist.

DG-044 / season sprint SR-11 (docs/strategies/2026-08-20-dg-SEASON-BUILD-SPEC.md
:595-749, AMENDED 2026-08-23 MIG-1). Runs at 10:30 via
``ops/launchd/com.davidleess.dynasty-capture-gap-alert.plist`` — after the
10:15 backup, so one run covers 06:15, 06:30, the 09:00 chain and the backup.

Two channels, because the 2026-08-22 morning proved one is not enough:

* **Stores and markers** ("did the data arrive?") — the cadence-config stores,
  the backup marker under the 26-hour law, the SR-09 chain report (from D6),
  the 6:00 AM wake schedule.
* **launchd itself** ("did the job even try?") — for every label under
  ``ops/launchd/*.plist``, ``launchctl print gui/501/<label>`` parsed for
  ``runs`` and ``last exit code``. A job that never spawned writes no store,
  no marker, no log and no exit code; only this channel can see it.

Silence means healthy: a clean morning prints nothing, notifies nothing and
exits 0. One line per problem otherwise, delivered as a macOS notification
plus a plain-text file David reads without opening anything.

Dumb and dependency-free by design (spec step 6): stdlib plus this repo's own
capture-health inspectors. An alerting system that can itself fail silently is
worse than none — hence the heartbeat (step 8) and the alert's own label in
its own sweep.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OWN_LABEL = "com.davidleess.dynasty-capture-gap-alert"

# A slot counts as "passed" only this many minutes after it fires, so the
# alert's own 10:30 slot never reads as missed while the alert itself is the
# process running at 10:30:xx, and a job mid-spawn is not named prematurely.
SLOT_GRACE_MINUTES = 15


# --- the launchd channel (spec steps 7-9) --------------------------------------


# Slot / JobSchedule / derive_job_schedules moved to
# src.dynasty_genius.launchd_schedules (2026-08-27) so the catch-up guard
# derives from the same source of schedule truth; re-imported here unchanged.
from src.dynasty_genius.launchd_schedules import (  # noqa: E402
    JobSchedule,
    Slot,
    derive_job_schedules,
)


@dataclass(frozen=True)
class LaunchdJobState:
    runs: int | None
    last_exit_code: int | None
    never_exited: bool
    penalty_box: bool


_RUNS_RE = re.compile(r"^\s*runs = (\d+)\s*$", re.MULTILINE)
_LAST_EXIT_RE = re.compile(r"^\s*last exit code = (.+?)\s*$", re.MULTILINE)


def parse_launchctl_print(text: str | None) -> LaunchdJobState | None:
    """Parse ``launchctl print gui/501/<label>`` output, defensively.

    First match wins for every field: the real output nests dispatch-source
    sub-blocks carrying their own ``state = active`` lines below the top-level
    fields (measured on this machine, 2026-08-26). ``launchctl print`` is not a
    documented stable interface, so this keys on field names, never positions,
    and treats the non-numeric ``(never exited)`` as a first-class value.
    ``None`` in means not loaded; ``None`` out says so.
    """

    if text is None:
        return None

    runs_match = _RUNS_RE.search(text)
    runs = int(runs_match.group(1)) if runs_match else None

    last_exit: int | None = None
    never_exited = False
    exit_match = _LAST_EXIT_RE.search(text)
    if exit_match:
        value = exit_match.group(1)
        if "never exited" in value:
            never_exited = True
        else:
            try:
                last_exit = int(value)
            except ValueError:
                last_exit = None

    lowered = text.lower()
    penalty_box = "penalty box" in lowered or "throttled" in lowered

    return LaunchdJobState(
        runs=runs,
        last_exit_code=last_exit,
        never_exited=never_exited,
        penalty_box=penalty_box,
    )


def slots_passed_today(
    slots: list[Slot],
    now: datetime,
    grace_minutes: int = SLOT_GRACE_MINUTES,
) -> list[datetime]:
    """Today's scheduled firings that are more than ``grace_minutes`` old."""

    passed: list[datetime] = []
    for slot in slots:
        if not slot.fires_on(now.date()):
            continue
        slot_time = now.replace(
            hour=slot.hour, minute=slot.minute, second=0, microsecond=0
        )
        if now >= slot_time + timedelta(minutes=grace_minutes):
            passed.append(slot_time)
    return passed


def never_attempted_line(
    label: str, state: LaunchdJobState | None, passed_slots: list[datetime]
) -> str | None:
    """Class (f): ``runs = 0`` on a job whose slot has already passed today.

    The 08-22 class. ``runs`` is per-bootstrap, so 0 means "not since login",
    which is exactly the question: a slot passed since login with zero runs is
    a job launchd never even tried.
    """

    if state is None or state.runs != 0 or not passed_slots:
        return None
    times = ", ".join(slot.strftime("%H:%M") for slot in sorted(passed_slots))
    return (
        f"GAP {label}: never attempted today — its {times} slot passed and "
        f"launchd records runs = 0"
    )


def penalty_box_line(label: str, state: LaunchdJobState | None) -> str | None:
    """Class (g): held in launchd's penalty box.

    That state lives only in launchd's memory and a reboot destroys the
    evidence, so a 10:30 read that misses it loses it permanently. The remedy
    is exact — nothing short of bootout + bootstrap clears it.
    """

    if state is None or not state.penalty_box:
        return None
    return (
        f"GAP {label}: held in launchd's penalty box (in-memory — a reboot "
        f"destroys the evidence). Clear it with `launchctl bootout gui/501/"
        f"{label}` then `launchctl bootstrap gui/501 <plist>`; nothing else "
        f"clears this state"
    )


def boot_to_login_lines(
    schedules: list[JobSchedule], *, boot_time: datetime, login_time: datetime
) -> list[str]:
    """Class (h): slots that elapsed between boot and console login.

    LaunchAgents exist only inside a logged-in GUI session, and launchd does
    not replay a StartCalendarInterval slot that elapsed while nobody was
    logged in (measured 2026-08-22: boot 09:04:39, login 10:48:52, thirteen
    slots swallowed silently). Missed-while-asleep is different and handled.
    """

    return [
        _gap_hit_line(label, slot_time, boot_time, login_time)
        for label, slot_time in _boot_to_login_hits(
            schedules, boot_time=boot_time, login_time=login_time
        )
    ]


def _boot_to_login_hits(
    schedules: list[JobSchedule], *, boot_time: datetime, login_time: datetime
) -> list[tuple[str, datetime]]:
    hits: list[tuple[str, datetime]] = []
    for schedule in schedules:
        for slot in schedule.slots:
            if not slot.fires_on(login_time.date()):
                continue
            slot_time = login_time.replace(
                hour=slot.hour, minute=slot.minute, second=0, microsecond=0
            )
            if boot_time < slot_time < login_time:
                hits.append((schedule.label, slot_time))
    return hits


def not_loaded_line(label: str, *, own_label: str = OWN_LABEL) -> str | None:
    """A label in ops/launchd/ that launchd does not hold is drift.

    A committed plist is not an installed plist (the 08-23 backup incident ran
    broken for weeks on exactly this). The alert's own label is exempt: it is
    legitimately unloaded between commit and David's bootstrap, and its
    liveness is the heartbeat's job, not the sweep's.
    """

    if label == own_label:
        return None
    return (
        f"GAP {label}: present in ops/launchd but not loaded in launchd — a "
        f"committed plist is not an installed plist (needs bootstrap)"
    )


# --- the store/marker channel (spec steps 1-5) ---------------------------------

# Healthy-but-immature caveats (Class A in the analyzer): never worth a line.
_BENIGN_CAVEATS = frozenset(("density_baseline_insufficient", "pre_capture_window"))


def store_lines(
    *,
    config_path: Path,
    repo_root: Path,
    now: datetime,
    known_holes: dict[str, list[str]],
) -> tuple[list[str], dict[str, list[str]]]:
    """Classes (a)+: missing capture dates and unreadable stores, via the
    landed inspectors — never the API server (spec step 1).

    ``known_holes`` is the memory that reconciles the spec's two demands: the
    dry run must NAME every hole it can see (a fresh state names all of them,
    including market_divergence_history's four permanent, unbackfillable
    ones), while a clean morning must be SILENT (a persisting known hole never
    prints again). Every NEW hole — which is what "a store missing
    yesterday's date" produces the morning it is born — alerts exactly once.
    A recovered hole (a retry overtaking bad news) simply leaves the state.
    """

    from app.api.routes.system_capture_health_models import (
        CaptureHealthConfigError,
        inspect_capture_store,
        load_capture_cadence,
    )

    lines: list[str] = []
    holes_by_store: dict[str, list[str]] = {}
    try:
        config = load_capture_cadence(config_path=config_path)
    except CaptureHealthConfigError as exc:
        # A broken config means the store channel is blind — that is itself
        # the loudest possible gap, never a silent skip.
        return [f"GAP capture_cadence config unusable: {exc}"], dict(known_holes)

    for store in config.stores:
        health = inspect_capture_store(
            store_config=store,
            repo_root=repo_root,
            now=now,
            timezone=config.timezone,
            season_windows=config.season_windows,
            # The API's 20-range display cap must not blind the alert: a new
            # "missing yesterday" in a store already past the cap is the LAST
            # range chronologically and would be truncated out of both the
            # lines and the known-holes state (review finding, 2026-08-26).
            missing_ranges_cap=100_000,
        )

        current: list[str] = []
        for missing_range in health.timeline.missing_ranges:
            day = date.fromisoformat(missing_range.from_date)
            end = date.fromisoformat(missing_range.to_date)
            while day <= end:
                current.append(day.isoformat())
                day += timedelta(days=1)
        holes_by_store[store.store_id] = current

        known = set(known_holes.get(store.store_id, []))
        new_holes = [day for day in current if day not in known]
        if new_holes:
            lines.append(
                f"GAP {store.store_id}: missing capture date"
                f"{'s' if len(new_holes) > 1 else ''} {', '.join(new_holes)}"
            )

        for caveat in health.caveats:
            if caveat in _BENIGN_CAVEATS:
                continue
            # An unreadable or absent store is an ONGOING emergency and repeats
            # daily on purpose — unlike an immutable historical hole.
            lines.append(f"GAP {store.store_id}: {caveat}")

    return lines, holes_by_store


def backup_lines(
    *, marker_path: Path, sentinel_path: Path | None, now: datetime
) -> list[str]:
    """Class (d) through the landed 26-hour-law inspector — marker absence,
    staleness, failed status, unearned verification, and the DG-036 sentinel,
    not just ``status != "completed"``."""

    from app.api.routes.system_capture_health_models import inspect_backup_marker

    health = inspect_backup_marker(
        marker_path=marker_path, now=now, sentinel_path=sentinel_path
    )
    if health.status == "ok":
        return []
    return [f"GAP backup: {reason}" for reason in health.reasons]


# Any wake from 6:00 through 6:14 serves the 06:15 capture. David set 6:00 on
# 08-20; 2026-08-27 measured the Mac idling back to sleep before 06:15, so the
# wake moves to 6:13 — both shapes are healthy while the change rolls out.
_WAKE_RE = re.compile(r"wakepoweron at 0?6:(0\d|1[0-4])AM", re.IGNORECASE)


def pmset_wake_line(pmset_output: str) -> str | None:
    """Class (e): the pre-06:15 daily wake. Some macOS updates clear
    ``pmset repeat`` and nothing today would notice; ``pmset -g sched``
    is the only reliable check on macOS 26."""

    if _WAKE_RE.search(pmset_output):
        return None
    return (
        "GAP pmset: the early-morning daily wake (6:00-6:14) is no longer "
        "scheduled — `pmset -g sched` shows no matching `wakepoweron`; the "
        "06:15/06:30 captures depend on it when the lid is closed"
    )


_CHAIN_FAILED_STATUSES = frozenset(("failed", "skipped_upstream_failed"))


def chain_report_lines(report_path: Path) -> list[str]:
    """Class (c): the SR-09 chain report. It does not exist until SR-09 lands
    (D6) — absence is expected and silent. Present but unreadable degrades
    loudly: data we hold and cannot interpret is never evidence of health."""

    if not report_path.is_file():
        return []
    try:
        raw = json.loads(report_path.read_text(encoding="utf-8"))
        steps = raw["steps"]
        assert isinstance(steps, list)
    except Exception:
        return [f"GAP chain report: {report_path.name} is unreadable"]

    lines: list[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            lines.append(f"GAP chain step #{index}: unreadable entry in chain report")
            continue
        name = step.get("name", f"step #{index}")
        exit_code = step.get("exit_code")
        status = step.get("status")
        if isinstance(exit_code, int) and exit_code != 0:
            lines.append(f"GAP chain step {name}: recorded exit_code {exit_code}")
        elif status in _CHAIN_FAILED_STATUSES:
            lines.append(f"GAP chain step {name}: recorded status {status}")
        elif exit_code is None and status is None:
            # Renamed keys must not parse as all-healthy: a step carrying
            # neither signal is uninterpretable, and uninterpretable is loud.
            lines.append(f"GAP chain step {name}: unreadable entry in chain report")
    return lines


# --- step 9: the pin file, and class (b) armed only behind it ------------------


# A pin honors only a marker written recently enough to describe the failing
# run — the same one-interval-plus-grace bound the backup law uses. A stale
# accepted-failure marker must never hide a NEW failure of a pinned producer.
_PIN_MARKER_FRESH_HOURS = 26


def exit_code_lines(
    states: dict[str, LaunchdJobState | None],
    *,
    pin_path: Path,
    repo_root: Path,
    now: datetime,
    reported_exits: dict[str, list[int]] | None = None,
) -> tuple[list[str], dict[str, list[int]]]:
    """Class (b): a producer that exited non-zero — DISARMED until the pin
    file exists (spec step 9: one producer can exit non-zero on a perfectly
    healthy morning by design, and unpinned this class cries wolf from day
    one — the SR-20 failure reproduced inside the ticket meant to cure it).

    A pin suppresses a failure only when the producer's own marker names
    exactly the accepted ``failed_stream`` AND that marker is fresh — a
    producer that crashed before writing today's marker must not hide behind
    yesterday's accepted failure. An expired review date turns the pin into a
    demand for review instead of a silent forever-acceptance.

    launchd's ``last exit code`` persists per-bootstrap, so one stale failure
    would otherwise re-alert every morning until the job's next run:
    ``reported_exits`` remembers the (runs, exit) evidence already delivered,
    and a line fires only on new evidence. Returns ``(lines, evidence)`` for
    the caller's state file.
    """

    current_evidence: dict[str, list[int]] = {}
    if not pin_path.is_file():
        return [], current_evidence
    try:
        pins_raw = json.loads(pin_path.read_text(encoding="utf-8"))
        pins = pins_raw["pins"]
        assert isinstance(pins, list)
    except Exception:
        return (
            [f"GAP pin file: {pin_path.name} is unreadable — class (b) blind"],
            current_evidence,
        )

    already = reported_exits or {}
    lines: list[str] = []
    for label in sorted(states):
        state = states[label]
        if state is None or state.last_exit_code in (None, 0):
            continue
        evidence = [state.runs if state.runs is not None else -1, state.last_exit_code]
        current_evidence[label] = evidence

        failed_stream: str | None = None
        marker_stale = False
        pin = next(
            (p for p in pins if isinstance(p, dict) and p.get("producer_label") == label),
            None,
        )
        if pin is not None:
            marker_path = repo_root / str(pin.get("marker_path", ""))
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                failed_stream = marker.get("failed_stream")
                finished = datetime.fromisoformat(str(marker.get("finished_at")))
                if finished.tzinfo is None or now - finished > timedelta(
                    hours=_PIN_MARKER_FRESH_HOURS
                ):
                    marker_stale = True
            except Exception:
                failed_stream = None
                marker_stale = True
            if (
                not marker_stale
                and failed_stream is not None
                and failed_stream == pin.get("accepted_failed_stream")
            ):
                review_raw = pin.get("review_date")
                review = _parse_iso_date(review_raw)
                if review is None or review < now.date():
                    lines.append(
                        f"PIN REVIEW OVERDUE {label}: accepted failure "
                        f"'{failed_stream}' passed its review date "
                        f"({review_raw!r}) — re-decide the pin"
                    )
                continue

        if already.get(label) == evidence:
            continue
        suffix = ""
        if failed_stream and marker_stale:
            suffix = f" (marker stale: names '{failed_stream}' — pin not applied)"
        elif failed_stream:
            suffix = f" (failed_stream: {failed_stream})"
        elif pin is not None and marker_stale:
            suffix = " (pin marker stale or unreadable — pin not applied)"
        lines.append(
            f"GAP {label}: exited {state.last_exit_code} on its last run{suffix}"
        )
    return lines, current_evidence


def _parse_iso_date(value: object) -> date | None:
    try:
        return date.fromisoformat(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# --- step 8: the heartbeat -----------------------------------------------------

_HEARTBEAT_PREFIX = "HEARTBEAT "

# Calendar days, not wall-clock hours: launchd DOES replay a slot missed
# while asleep, so a lid-closed morning yields a LATE same-day run — a
# heartbeat dated yesterday is that late run's normal predecessor, never a
# miss. A genuinely missed day always leaves the previous heartbeat two or
# more calendar days old by the time the next run fires.
_HEARTBEAT_STALE_DAYS = 2


def append_heartbeat(alert_file: Path, *, now: datetime) -> None:
    alert_file.parent.mkdir(parents=True, exist_ok=True)
    with alert_file.open("a", encoding="utf-8") as handle:
        handle.write(f"{_HEARTBEAT_PREFIX}{now.isoformat()}\n")


def read_last_heartbeat(alert_file: Path) -> datetime | None:
    if not alert_file.is_file():
        return None
    last: datetime | None = None
    try:
        for line in alert_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(_HEARTBEAT_PREFIX):
                try:
                    parsed = datetime.fromisoformat(line[len(_HEARTBEAT_PREFIX) :].strip())
                except ValueError:
                    continue
                if parsed.tzinfo is not None:
                    last = parsed
    except OSError:
        return None
    return last


def missed_self_line(last_heartbeat: datetime | None, *, now: datetime) -> str | None:
    """The alert must notice its own absence (spec step 8): on the boot-to-
    login morning the alert certainly did not fire either. First run ever has
    no heartbeat and is not a miss."""

    if last_heartbeat is None:
        return None
    if (now.date() - last_heartbeat.date()).days < _HEARTBEAT_STALE_DAYS:
        return None
    return (
        f"GAP {OWN_LABEL}: the alert itself missed at least one run — last "
        f"heartbeat {last_heartbeat.date().isoformat()} "
        f"({last_heartbeat.isoformat()}); the silent mornings since then are "
        f"unverified, not clean"
    )


# --- assembly ------------------------------------------------------------------


@dataclass
class Runtime:
    """Everything the alert touches, injectable so tests never touch the
    machine and the machine run never needs a test double."""

    repo_root: Path
    config_path: Path
    plist_dir: Path
    alert_file: Path
    state_path: Path
    pin_path: Path
    chain_report_path: Path
    backup_marker_path: Path
    backup_sentinel_path: Path
    now: datetime
    launchctl_print: Callable[[str], str | None]
    pmset_sched: str
    boot_time: datetime | None
    login_time: datetime | None
    notify: Callable[[str], None]
    dry_run: bool = False


def event_stream_lines(
    config_path: Path,
    repo_root: Path,
    now: datetime,
    known_issues: dict[str, str],
) -> tuple[list[str], dict[str, str]]:
    """DG-049 / SR-10b: the two event-stream stores, judged by ATTESTATION.

    Bursty streams have legitimately quiet days and (nflverse) deliberately
    unchanged store bytes, so cadence semantics do not fit — but both producers
    write an atomic status marker on EVERY run, no-op days included. After the
    slot plus grace, the marker must attest TODAY with status ok. Alert-once
    semantics mirror the store channel's known-holes design: a NEW failure
    signature alerts exactly once and persists silently; recovery clears it so
    the next failure is loud again.
    """

    from app.api.routes.system_capture_health_models import (
        CaptureHealthConfigError,
        load_capture_cadence,
    )

    try:
        config = load_capture_cadence(config_path=config_path)
    except CaptureHealthConfigError:
        # store_lines already screams about an unusable config; a second
        # identical scream here would be noise, not signal.
        return [], dict(known_issues)

    tz = ZoneInfo(config.timezone)
    today = now.astimezone(tz).date()
    lines: list[str] = []
    issues: dict[str, str] = {}

    for stream in config.event_streams:
        due_at = now.astimezone(tz).replace(
            hour=stream.hour, minute=stream.minute, second=0, microsecond=0
        ) + timedelta(hours=stream.grace_hours)
        if now.astimezone(tz) < due_at:
            # Slot not yet due: nothing is demanded, nothing is verified —
            # carry any existing issue forward unchanged.
            if stream.stream_id in known_issues:
                issues[stream.stream_id] = known_issues[stream.stream_id]
            continue

        marker_path = repo_root / stream.marker
        signature: str | None = None
        line: str | None = None
        if not marker_path.is_file():
            signature = "absent"
            line = (
                f"GAP event stream {stream.stream_id}: no attestation marker at "
                f"{stream.marker}"
            )
        else:
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                status = str(marker["status"])
                finished_local = datetime.fromisoformat(
                    marker["finished_at"]
                ).astimezone(tz)
            except Exception:
                signature = "unreadable"
                line = (
                    f"GAP event stream {stream.stream_id}: attestation marker is "
                    "unreadable"
                )
            else:
                finished_date = finished_local.date()
                if finished_date > today:
                    signature = f"future:{finished_date.isoformat()}"
                    line = (
                        f"GAP event stream {stream.stream_id}: attestation marker is "
                        f"future-dated ({finished_date.isoformat()}) — unreadable as "
                        "evidence"
                    )
                elif finished_date < today:
                    signature = f"stale:{finished_date.isoformat()}"
                    line = (
                        f"GAP event stream {stream.stream_id}: no attestation today — "
                        f"last attested {finished_date.isoformat()} (status {status})"
                    )
                elif status != "ok":
                    detail = str(marker.get("failed_stream") or "")
                    signature = f"status:{status}:{detail}"
                    line = f"GAP event stream {stream.stream_id}: attested status {status}"
                    if detail:
                        line += f" — failed_stream {detail}"

        if signature is None:
            # Attested today, status ok: healthy. The issue (if any) clears so a
            # future failure is loud again.
            continue
        issues[stream.stream_id] = signature
        if known_issues.get(stream.stream_id) != signature:
            lines.append(line)

    return lines, issues


def _load_state(
    state_path: Path,
) -> tuple[dict[str, list[str]], dict[str, list[int]], dict[str, str]]:
    """(known holes, reported exit evidence). Unreadable state means
    over-reporting once, never under-reporting."""
    if not state_path.is_file():
        return {}, {}, {}
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        holes = raw.get("holes_by_store", {})
        exits = raw.get("reported_exits", {})
        stream_issues = raw.get("event_stream_issues", {})
        assert isinstance(holes, dict) and isinstance(exits, dict)
        assert isinstance(stream_issues, dict)
        return (
            {str(k): [str(d) for d in v] for k, v in holes.items()},
            {str(k): [int(x) for x in v] for k, v in exits.items()},
            {str(k): str(v) for k, v in stream_issues.items()},
        )
    except Exception:
        return {}, {}, {}


def _save_state(
    state_path: Path,
    holes_by_store: dict[str, list[str]],
    reported_exits: dict[str, list[int]],
    now: datetime,
    event_stream_issues: dict[str, str] | None = None,
) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema": 2,
                "updated_at": now.isoformat(),
                "holes_by_store": holes_by_store,
                "reported_exits": reported_exits,
                "event_stream_issues": event_stream_issues or {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def notification_message(lines: list[str]) -> str:
    head = lines[0]
    more = f" (+{len(lines) - 1} more)" if len(lines) > 1 else ""
    return f"{head}{more}"


def run_alert(rt: Runtime) -> list[str]:
    """Evaluate both channels; deliver only in a live run.

    Returns every problem line. A dry run evaluates everything against a
    fresh view but writes nothing, notifies nothing, and never updates the
    known-holes state — so the build-day dry run names every hole it can see.
    """

    lines: list[str] = []

    # Step 8 first: read the heartbeat BEFORE this run writes its own.
    last_heartbeat = read_last_heartbeat(rt.alert_file)
    lines.extend(filter(None, [missed_self_line(last_heartbeat, now=rt.now)]))

    known_holes, reported_exits, known_stream_issues = _load_state(rt.state_path)
    store_ls, holes_by_store = store_lines(
        config_path=rt.config_path,
        repo_root=rt.repo_root,
        now=rt.now,
        known_holes=known_holes,
    )
    lines.extend(store_ls)
    stream_ls, event_stream_issues = event_stream_lines(
        rt.config_path, rt.repo_root, rt.now, known_stream_issues
    )
    lines.extend(stream_ls)

    lines.extend(
        backup_lines(
            marker_path=rt.backup_marker_path,
            sentinel_path=rt.backup_sentinel_path,
            now=rt.now,
        )
    )
    lines.extend(chain_report_lines(rt.chain_report_path))
    lines.extend(filter(None, [pmset_wake_line(rt.pmset_sched)]))

    # Class (h) fires on THIS morning's gap, or on the FIRST run after a gap
    # that swallowed the alert's own slot (login after 10:30 — the true 08-22
    # shape): a heartbeat older than the login proves this run is that first
    # run. Replaying an old boot/login pair on ordinary mornings is noise.
    gap_hits: list[tuple[str, datetime]] = []
    schedules = derive_job_schedules(rt.plist_dir)
    if (
        rt.boot_time is not None
        and rt.login_time is not None
        and (
            rt.login_time.date() == rt.now.date()
            or (last_heartbeat is not None and last_heartbeat < rt.login_time)
        )
    ):
        gap_hits = _boot_to_login_hits(
            schedules, boot_time=rt.boot_time, login_time=rt.login_time
        )
        lines.extend(
            _gap_hit_line(label, slot_time, rt.boot_time, rt.login_time)
            for label, slot_time in gap_hits
        )
    gap_slot_keys = {(label, slot.strftime("%H:%M")) for label, slot in gap_hits}

    # launchd's counters are per-bootstrap: a slot that predates today's
    # boot/login cannot be judged by runs = 0 (a mid-morning reboot after a
    # healthy 06:15 capture must not cry "never attempted"). Unverifiable
    # slots are collected into ONE consolidated line naming the jobs — so a
    # genuinely un-run job never passes unnamed — without asserting a miss.
    counter_cutoff: datetime | None = None
    if (
        rt.boot_time is not None
        and rt.login_time is not None
        and rt.login_time.date() == rt.now.date()
    ):
        counter_cutoff = max(rt.boot_time, rt.login_time)

    states: dict[str, LaunchdJobState | None] = {}
    unverifiable: list[tuple[str, datetime]] = []
    for schedule in schedules:
        state = parse_launchctl_print(rt.launchctl_print(schedule.label))
        states[schedule.label] = state
        if state is None:
            lines.extend(filter(None, [not_loaded_line(schedule.label)]))
            continue
        if state.runs is None:
            # launchctl print is not a stable interface; a loaded job whose
            # output no longer parses is a BLIND channel, and blind is loud.
            lines.append(
                f"GAP {schedule.label}: loaded but `launchctl print` output is "
                f"unparseable (no runs field) — the launchd channel cannot "
                f"verify this job"
            )
            continue
        passed = slots_passed_today(schedule.slots, rt.now)
        if counter_cutoff is not None and state.runs == 0:
            hard = [t for t in passed if t > counter_cutoff]
            for slot_time in passed:
                if slot_time <= counter_cutoff and (
                    (schedule.label, slot_time.strftime("%H:%M")) not in gap_slot_keys
                ):
                    unverifiable.append((schedule.label, slot_time))
            passed = hard
        lines.extend(filter(None, [never_attempted_line(schedule.label, state, passed)]))
        lines.extend(filter(None, [penalty_box_line(schedule.label, state)]))

    if unverifiable:
        named = ", ".join(
            f"{label} ({slot.strftime('%H:%M')})" for label, slot in unverifiable
        )
        lines.append(
            f"GAP launchd: run counters were reset by today's "
            f"{counter_cutoff.strftime('%H:%M')} boot/login after these slots — "
            f"cannot verify they ran: {named}; the store channel is "
            f"authoritative this morning"
        )

    exit_ls, exit_evidence = exit_code_lines(
        states,
        pin_path=rt.pin_path,
        repo_root=rt.repo_root,
        now=rt.now,
        reported_exits=reported_exits,
    )
    lines.extend(exit_ls)

    if not rt.dry_run:
        if lines:
            rt.alert_file.parent.mkdir(parents=True, exist_ok=True)
            with rt.alert_file.open("a", encoding="utf-8") as handle:
                for line in lines:
                    handle.write(f"{rt.now.isoformat()} {line}\n")
        append_heartbeat(rt.alert_file, now=rt.now)
        # Merge, don't replace: exit evidence for a label with no new failure
        # this run must survive (the stale code persists in launchd).
        merged_exits = {**reported_exits, **exit_evidence}
        _save_state(
            rt.state_path, holes_by_store, merged_exits, rt.now, event_stream_issues
        )
        if lines:
            delivered = rt.notify(notification_message(lines))
            if delivered is False:
                # The one channel permissions cannot suppress is this file.
                with rt.alert_file.open("a", encoding="utf-8") as handle:
                    handle.write(
                        f"{rt.now.isoformat()} GAP notification: delivery "
                        f"failed (osascript) — this file is the record\n"
                    )

    return lines


def _gap_hit_line(
    label: str, slot_time: datetime, boot_time: datetime, login_time: datetime
) -> str:
    return (
        f"GAP {label}: its {slot_time.strftime('%H:%M')} slot fell between boot "
        f"({boot_time.strftime('%H:%M:%S')}) and console login "
        f"({login_time.strftime('%H:%M:%S')}) — launchd did not run it and "
        f"will not replay it"
    )


def run_and_deliver(rt: Runtime) -> int:
    """The crash guard: an uncaught exception must never kill the detection
    channel silently (review CRITICAL, 2026-08-26). The crash itself becomes
    the alert — best-effort file line, best-effort notification, exit 1 —
    because a persistent crash otherwise means permanent false silence: every
    self-detection path needs a LATER successful run to fire."""

    try:
        for line in run_alert(rt):
            print(line)
        return 0
    except Exception as exc:  # noqa: BLE001 — the whole point is catching everything
        message = (
            f"GAP {OWN_LABEL}: the alert itself crashed: {exc!r} — this "
            f"morning is UNVERIFIED, not clean"
        )
        if not rt.dry_run:
            try:
                rt.alert_file.parent.mkdir(parents=True, exist_ok=True)
                with rt.alert_file.open("a", encoding="utf-8") as handle:
                    handle.write(f"{rt.now.isoformat()} {message}\n")
            except Exception:
                pass
            try:
                rt.notify(message)
            except Exception:
                pass
        try:
            print(message, file=sys.stderr)
        except Exception:
            pass
        return 1


# --- the real machine ----------------------------------------------------------


def _live_launchctl_print(label: str) -> str | None:
    import os
    import subprocess

    result = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or "Could not find service" in result.stderr:
        return None
    return result.stdout


def _live_pmset_sched() -> str:
    import subprocess

    result = subprocess.run(
        ["pmset", "-g", "sched"], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else ""


def _live_boot_time(tz) -> datetime | None:
    import subprocess

    result = subprocess.run(
        ["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, check=False
    )
    match = re.search(r"sec = (\d+)", result.stdout)
    if result.returncode != 0 or not match:
        return None
    return datetime.fromtimestamp(int(match.group(1)), tz=tz)


def _live_login_time(tz, now: datetime) -> datetime | None:
    """Console login from ``who`` (no year in its output; assume this year —
    class (h) only consults a login dated today anyway)."""
    import subprocess

    result = subprocess.run(["who"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == "console":
            try:
                parsed = datetime.strptime(
                    f"{now.year} {parts[2]} {parts[3]} {parts[4]}", "%Y %b %d %H:%M"
                )
                return parsed.replace(tzinfo=tz)
            except ValueError:
                return None
    return None


def _live_notify(message: str) -> bool:
    """True only when osascript itself succeeded — exit 0 still cannot prove
    the banner RENDERED (Focus, permissions), which is why delivery failure
    lands in the alert file and the first live run gets human eyes."""
    import subprocess

    body = message.replace('"', "'")
    result = subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{body}" with title "Dynasty Genius capture alert"',
        ],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="evaluate and print, but write nothing, notify nothing, keep no state",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repo to inspect (default: this script's repo)",
    )
    args = parser.parse_args(argv)

    root = args.repo_root.resolve()
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)

    runtime = Runtime(
        repo_root=root,
        config_path=root / "app" / "config" / "capture_cadence.json",
        plist_dir=root / "ops" / "launchd",
        # Outside the repo (a branch switch must never move it) and outside
        # TCC-protected folders (Desktop/Documents can silently deny a
        # launchd-spawned writer — a silent alert file would be the exact
        # failure this script exists to end).
        alert_file=Path.home() / "DG-CAPTURE-ALERTS.txt",
        state_path=root / "app" / "data" / "ops" / "capture_gap_alert_state.json",
        pin_path=root / "app" / "config" / "capture_gap_accepted_exits.json",
        chain_report_path=root / "app" / "data" / "ops" / "daily_chain_latest_report.json",
        backup_marker_path=root / "app" / "data" / "ops" / "backup_status_latest.json",
        backup_sentinel_path=root / "app" / "data" / "ops" / "backup_run_active.json",
        now=now,
        launchctl_print=_live_launchctl_print,
        pmset_sched=_live_pmset_sched(),
        boot_time=_live_boot_time(tz),
        login_time=_live_login_time(tz, now),
        notify=_live_notify,
        dry_run=args.dry_run,
    )

    # Exit 0 whether or not gaps were found: the alert JOB succeeded at
    # alerting, and a non-zero exit here would trip class (b) on the alert
    # itself every problem morning. Non-zero means the alert crashed — and
    # run_and_deliver makes even that crash loud.
    return run_and_deliver(runtime)


if __name__ == "__main__":
    sys.exit(main())
