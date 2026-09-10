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

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
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


# --------------------------------------------------------------- feed retries
# DG-216. A delayed upstream feed is a different fact from a missed launchd
# occurrence: nobody failed to run. It has two shapes, and the second is the
# one that actually recurs:
#   1. the seasonal file is not published yet at all;
#   2. the file IS published and readable, holds week 1, and week 2 is late.
# Shape 2 looks entirely healthy — the capture reads it, finds it unchanged,
# calls the partition ready and clears the retry — so without a bounded
# re-check nothing ever looks again and the same morning repeats.
#
# The capture owner (DG-215) decides what is retryable and publishes it in the
# receipt; the guard only obeys, and only for an explicitly configured job.
# Membership in `due` is the capture's statement about what to re-check. The
# guard infers NOTHING about readiness from it: a partition can be data
# available with observed coverage and still be due for a revision check, and
# the guard must neither call that pending nor refuse to re-check it.
#
# What this is not: a game-aware readiness framework. Nothing here knows which
# games have been played. A ready partition means season-level source coverage
# was observed, never proof that every completed game is already in it.
#
# Contract agreed with DG-215 on 2026-09-10. Exit codes from the retry CLI:
#   0  ran, including "checked and still waiting"
#   1  real failure — surfaced, never auto-retried
#   3  capture's own lock held, nothing done — benign, try the next tick
RETRY_SCHEMA = "capture.retry.v1"
RETRY_MIN_INTERVAL = timedelta(hours=1)
# DG-215's capture lock is O_CREAT|O_EXCL removed in a finally, so a SIGKILL or
# reboot leaves it behind and every later capture refuses by name until a human
# deletes it. Under 15-minute ticks that is a silent wedge with no data moving,
# so a continuous hour of exit 3 stops reading as patience and starts reading
# as degraded. The guard never deletes that file: a capture that clears its own
# guard rail is worse than one that stops.
LOCK_WEDGE_THRESHOLD = timedelta(hours=1)
EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_LOCK_HELD = 3
# States the capture reports for a partition that is NOT finished. Any of these
# appearing outside `due` is a dropped partition, which otherwise looks exactly
# like a completed one. "interrupted" belongs here: DG-215 writes it for an
# attempt that died mid-fetch, so it is unfinished by definition and its absence
# from the queue is the same bug as a dropped pending one.
PENDING_STATES = ("waiting", "pending", "due", "interrupted")


@dataclass(frozen=True)
class DuePartition:
    partition: str
    reason: str
    attempt_id: str
    attempt: int | None = None
    stream: str | None = None
    season: int | None = None
    # the capture's own record of when it last tried this partition. Canonical:
    # it outlives the guard's ledger, so losing the ledger cannot buy a retry.
    last_attempt_at: datetime | None = None


@dataclass(frozen=True)
class RetryState:
    due: list[DuePartition] = field(default_factory=list)
    next_retry_at: datetime | None = None
    in_flight: dict | None = None
    not_retryable: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    unusable: list[dict] = field(default_factory=list)
    interrupted: str | None = None
    refusal: str | None = None


@dataclass(frozen=True)
class RetryJob:
    label: str
    receipt_path: str
    command: tuple[str, ...]
    min_interval: timedelta = RETRY_MIN_INTERVAL
    lock_path: str = "app/data/ops/catchup_guard_retry.lock"


@dataclass(frozen=True)
class RetryPlan:
    label: str
    due: list[DuePartition] = field(default_factory=list)
    waiting_until: datetime | None = None
    skipped_reason: str | None = None
    refusal: str | None = None
    not_retryable: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    unusable: list[dict] = field(default_factory=list)
    interrupted: str | None = None
    in_flight: dict | None = None


@dataclass(frozen=True)
class RetryOutcome:
    label: str
    state: str
    exit_code: int | None = None
    partitions: list[str] = field(default_factory=list)
    note: str = ""


def _aware(raw: Any, what: str) -> tuple[datetime | None, str | None]:
    """An instant with an offset, or a refusal. Never a local-time guess.

    `.timestamp()` on a naive datetime silently reads the machine's local zone,
    so identical bytes would be judged differently on two machines.
    """
    if raw is None:
        return None, None
    if not isinstance(raw, str):
        return None, f"{what} is not a string"
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None, f"{what} is not a valid instant"
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return None, f"{what} carries no timezone offset"
    return moment, None


def read_retry_block(path: Path, *, now: datetime) -> RetryState:
    """Parse the capture receipt's additive retry block.

    Absence is silence: no file, or no ``retry`` key, means nothing is due and
    nothing is wrong — every receipt in production today looks like that. A
    receipt that is present but malformed is the opposite: it is refused and
    surfaced, because a half-written state file is exactly when an automatic
    retry would do the most damage.
    """
    path = Path(path)
    if not path.exists():
        return RetryState()
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return RetryState(refusal="capture receipt is malformed and was not trusted")
    if not isinstance(payload, dict):
        return RetryState(refusal="capture receipt is malformed and was not trusted")
    if "retry" not in payload:
        # Absence normally means nothing is pending, and that stays the rule —
        # every healthy receipt today has no retry key. But reviewer 54331
        # found that absence currently carries TWO facts under one shape:
        # "nothing is pending" and "we were killed before writing what was".
        # DG-215's running marker carries no retry block, so a SIGKILL
        # mid-capture leaves status=running with the queue gone, and the guard
        # cannot tell the cases apart. The rule does not change — but the
        # ambiguity is surfaced instead of read as health, so an interrupted
        # capture is visible before the next daily full run rather than after.
        if str(payload.get("status") or "").lower() == "running":
            return RetryState(
                interrupted=(
                    "the capture receipt says status=running but carries no retry block; "
                    "either it is running now and has not written one yet, or it was "
                    "killed before it could — the pending queue cannot be read either way"
                )
            )
        return RetryState()

    block = payload.get("retry")
    if not isinstance(block, dict):
        return RetryState(refusal="retry block is malformed and was not trusted")
    if block.get("schema_version") != RETRY_SCHEMA:
        return RetryState(
            refusal=f"unknown retry schema {block.get('schema_version')!r}; expected {RETRY_SCHEMA}"
        )

    next_retry_at, problem = _aware(block.get("next_retry_at"), "next_retry_at")
    if problem:
        return RetryState(refusal=problem)

    entries = block.get("due")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        return RetryState(refusal="retry.due is malformed and was not trusted")

    due: list[DuePartition] = []
    not_retryable: list[str] = []
    unusable: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return RetryState(refusal="a retry.due entry is malformed and was not trusted")
        partition = entry.get("partition")
        attempt_id = entry.get("attempt_id")
        if not isinstance(partition, str) or not isinstance(attempt_id, str):
            return RetryState(refusal="a retry.due entry names no partition and attempt")
        # DG-215 guarantees `due` holds only retryable partitions; this second
        # check is deliberate belt and braces, because absence must never read
        # as permission and the cost of being wrong here is a retry loop
        if entry.get("retryable") is not True:
            not_retryable.append(partition)
            continue
        # A bad stamp refuses THIS partition with a stated reason and leaves the
        # others alone. Refusing the whole block would let one malformed entry
        # stop every delayed feed; silently dropping it would make a partition
        # vanish. Neither is a wedge: the capture owns the field and its next
        # ordinary write corrects it.
        # An ABSENT stamp is as unusable as a malformed one. Accepting it would
        # leave the floor with nothing to measure from and make the partition
        # instantly eligible — the canonical field is exactly what stops a lost
        # guard ledger buying a retry, so it cannot be optional.
        if entry.get("last_attempt_at") is None:
            unusable.append({
                "partition": partition,
                "reason": (
                    "no last_attempt_at, so the hourly floor has nothing canonical "
                    "to measure from; refused until the capture writes one"
                ),
            })
            continue
        stamp, problem = _aware(entry.get("last_attempt_at"), "last_attempt_at")
        if problem:
            unusable.append({
                "partition": partition,
                "reason": f"{problem}; refused until the capture rewrites it",
            })
            continue
        if stamp is not None and stamp > now:
            unusable.append({
                "partition": partition,
                "reason": (
                    "last_attempt_at is in the future; refused until the capture "
                    "rewrites it, and never treated as an immediate retry"
                ),
            })
            continue
        season = entry.get("season")
        due.append(
            DuePartition(
                partition=partition,
                reason=str(entry.get("reason") or "unstated"),
                attempt_id=attempt_id,
                attempt=entry.get("attempt") if isinstance(entry.get("attempt"), int) else None,
                stream=entry.get("stream") if isinstance(entry.get("stream"), str) else None,
                season=season if isinstance(season, int) else None,
                last_attempt_at=stamp,
            )
        )

    # A partition the capture still calls pending, that never reaches `due`, is
    # a dropped partition — it looks identical to a finished one otherwise.
    named = (
        {item.partition for item in due}
        | set(not_retryable)
        | {item["partition"] for item in unusable}
    )
    dropped: list[str] = []
    partitions = payload.get("partitions")
    if isinstance(partitions, list):
        for item in partitions:
            if not isinstance(item, dict):
                continue
            name = item.get("partition") or item.get("name")
            if not isinstance(name, str):
                continue
            if str(item.get("state") or "").lower() in PENDING_STATES and name not in named:
                dropped.append(name)

    in_flight = block.get("in_flight")
    return RetryState(
        due=due,
        next_retry_at=next_retry_at,
        in_flight=in_flight if isinstance(in_flight, dict) else None,
        not_retryable=sorted(not_retryable),
        dropped=sorted(dropped),
        unusable=sorted(unusable, key=lambda item: item["partition"]),
    )


@dataclass
class RetryLedger:
    """The guard's own brakes, remembered across ticks.

    Two of them, deliberately independent: one invocation per (partition,
    attempt) so a receipt that never advances cannot be re-run forever, and an
    hourly floor per partition so minting new attempt ids cannot buy extra
    invocations either.
    """

    invoked: dict[str, str] = field(default_factory=dict)
    last_seen: dict[str, str] = field(default_factory=dict)
    lock_since: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _attempt_key(label: str, partition: str, attempt_id: str) -> str:
        return f"{label}|{partition}|{attempt_id}"

    @staticmethod
    def _partition_key(label: str, partition: str) -> str:
        return f"{label}|{partition}"

    def record(self, label: str, partition: str, attempt_id: str, *, at: datetime) -> None:
        stamp = at.isoformat()
        self.invoked[self._attempt_key(label, partition, attempt_id)] = stamp
        self.last_seen[self._partition_key(label, partition)] = stamp

    @staticmethod
    def _parse(raw: str | None) -> datetime | None:
        if not isinstance(raw, str):
            return None
        try:
            moment = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return moment if moment.tzinfo is not None else None

    def invoked_at(self, label: str, partition: str, attempt_id: str) -> datetime | None:
        return self._parse(self.invoked.get(self._attempt_key(label, partition, attempt_id)))

    def last_invocation(self, label: str, partition: str) -> datetime | None:
        return self._parse(self.last_seen.get(self._partition_key(label, partition)))

    def mark_lock_held(self, label: str, *, at: datetime) -> None:
        # first sighting wins: the wedge is measured from when it started
        self.lock_since.setdefault(label, at.isoformat())

    def clear_lock_held(self, label: str) -> None:
        self.lock_since.pop(label, None)

    def lock_held_since(self, label: str) -> datetime | None:
        return self._parse(self.lock_since.get(label))

    def lock_wedged(
        self, label: str, *, now: datetime, threshold: timedelta = LOCK_WEDGE_THRESHOLD
    ) -> bool:
        since = self.lock_held_since(label)
        return since is not None and now - since >= threshold

    @classmethod
    def load(cls, path: Path) -> "RetryLedger":
        try:
            payload = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            return cls()
        if not isinstance(payload, dict):
            return cls()

        def _strings(key: str) -> dict[str, str]:
            value = payload.get(key, {})
            if not isinstance(value, dict):
                return {}
            return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)}

        return cls(
            invoked=_strings("invoked"),
            last_seen=_strings("last_seen"),
            lock_since=_strings("lock_since"),
        )

    def save(self, path: Path, *, now: datetime, keep: timedelta) -> None:
        cutoff = now - keep

        def _prune(entries: dict[str, str]) -> dict[str, str]:
            kept: dict[str, str] = {}
            for key, stamp in entries.items():
                moment = self._parse(stamp)
                # a bad stamp is dropped, never fatal — a save that raised would
                # stop the ledger persisting, and the re-invocations that follow
                # are exactly the loop these brakes exist to prevent
                if moment is not None and moment >= cutoff:
                    kept[key] = stamp
            return kept

        atomic_write_json(
            Path(path),
            {
                "invoked": _prune(self.invoked),
                "last_seen": _prune(self.last_seen),
                # never pruned by age: a wedge older than the window is the most
                # important one to still be reporting
                "lock_since": dict(self.lock_since),
            },
        )


@contextmanager
def acquire_retry_lock(path: Path, *, now: datetime):
    """Hold the guard's retry lock, or yield None if another tick holds it.

    Advisory ``flock`` on a persistent, resolved inode, opened O_CREAT and
    never O_EXCL, and NEVER unlinked anywhere including the finally. The kernel
    releases the lock when the holder dies, SIGKILL included, and that is the
    entire recovery property: no TTL, no content staleness, no deletion.

    The O_CREAT|O_EXCL sentinel written first was wrong, and worse than it
    looked. Between creating the file and writing the pid into it there is a
    window where a second tick reads it blank, judges it stale, unlinks it and
    proceeds — and then the first holder's cleanup unlinks the *second*
    holder's file, letting a third in. That is a split inode and two live
    holders. flock has no such window, because the lock is on the open file
    description rather than on the bytes, and unlinking under waiters is
    exactly what splits it.

    The path is resolved first so two aliases of one store — a symlink and the
    real path — collide instead of taking two different locks.

    There is deliberately no "stale lock" policy here, and no TTL parameter or
    constant either — reviewer 54331's point, and a good one: a live constant
    named TTL sitting beside a lock whose entire correctness argument is that
    it has none is an invitation to wire it back up later. An earlier version
    of this docstring argued the capture lock should NOT self-heal and that a
    stale one should stop the world until a human looked; that rationale is
    retired on both sides. With advisory locks there is no stale lock to have a
    policy about.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # resolve AFTER the parent exists so aliases converge on one inode
    path = path.resolve()
    handle = open(path, "a+", encoding="utf-8")  # noqa: SIM115 — closed in finally
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield None
            return
        try:
            # diagnostic only; ownership is the flock, never these bytes
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({"pid": os.getpid(), "at": now.isoformat()}))
            handle.flush()
        except OSError:
            pass
        try:
            yield path
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _floor_cleared(
    *, now: datetime, job: RetryJob, item: DuePartition, ledger: RetryLedger
) -> bool:
    """Has the hourly floor elapsed since the LAST attempt by anyone?

    Two sources, and the later one wins. The guard's ledger is local and can be
    lost or start empty; the capture's ``last_attempt_at`` is canonical and
    survives that, so a fresh ledger cannot buy an immediate retry of something
    tried five minutes ago.

    A stamp in the future is clamped to now rather than believed, so a skewed
    or hand-edited receipt earns the full interval from now instead of an
    instant retry.
    """
    candidates = [ledger.last_invocation(job.label, item.partition), item.last_attempt_at]
    stamps = [min(stamp, now) for stamp in candidates if stamp is not None]
    if not stamps:
        return True
    return now - max(stamps) >= job.min_interval


def plan_retries(*, now: datetime, job: RetryJob, ledger: RetryLedger) -> RetryPlan:
    """What, if anything, this tick should ask the capture CLI to re-check."""
    state = read_retry_block(Path(job.receipt_path), now=now)
    if state.refusal:
        return RetryPlan(
            label=job.label,
            refusal=state.refusal,
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
        )
    if not state.due:
        # carries `unusable`: if EVERY entry had a bad stamp there is nothing
        # due and nothing wrong-looking, and the diagnostics are the only thing
        # standing between that and a quiet, healthy-looking report
        return RetryPlan(
            label=job.label,
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
            in_flight=state.in_flight,
        )
    # in_flight is DIAGNOSTIC ONLY — who and when, for the receipt and for a
    # human. It is never a gate. A SIGKILL leaves it written with nothing to
    # clear it, so gating on it would veto every later retry forever and cancel
    # out the advisory-lock recovery on both sides. Liveness is decided by
    # whether a lock can be taken: the guard's own lock here, and the capture's
    # lock when it answers exit 3.
    if state.next_retry_at is None:
        return RetryPlan(
            label=job.label,
            refusal="partitions are due but the receipt names no next_retry_at",
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
            in_flight=state.in_flight,
        )
    if now < state.next_retry_at:
        return RetryPlan(
            label=job.label,
            waiting_until=state.next_retry_at,
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
        )

    fresh = [
        item
        for item in state.due
        if ledger.invoked_at(job.label, item.partition, item.attempt_id) is None
    ]
    if not fresh:
        return RetryPlan(
            label=job.label,
            skipped_reason="already_attempted",
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
        )
    allowed = [
        item for item in fresh if _floor_cleared(now=now, job=job, item=item, ledger=ledger)
    ]
    if not allowed:
        return RetryPlan(
            label=job.label,
            skipped_reason="rate_limited",
            not_retryable=state.not_retryable,
            dropped=state.dropped,
            unusable=state.unusable,
            interrupted=state.interrupted,
        )
    return RetryPlan(
        label=job.label,
        due=allowed,
        not_retryable=state.not_retryable,
        dropped=state.dropped,
        unusable=state.unusable,
        interrupted=state.interrupted,
        in_flight=state.in_flight,
    )


def invoke_retry(
    *,
    job: RetryJob,
    plan: RetryPlan,
    run: Callable[[tuple[str, ...]], int],
    now: datetime,
    ledger: RetryLedger,
    dry_run: bool = False,
    reload: Callable[[], RetryLedger] | None = None,
    persist: Callable[[RetryLedger], None] | None = None,
) -> RetryOutcome:
    """Run the capture's retry-only CLI once, and record what that means.

    The decision is re-derived INSIDE the lock, not reused from the plan that
    was made outside it. Two ticks can both plan the same attempt while neither
    holds the lock; if the winner recorded only after releasing, the loser
    would take the lock and invoke the very same attempt again. So inside the
    lock we reload the ledger, re-plan against the receipt as it is now, and
    persist the decision before releasing. The plan passed in is a proposal;
    what runs is what still holds under the lock.

    Dry-run spawns nothing, takes no lock and writes no ledger — the moment a
    dry run can start a capture it has stopped being read-only.
    """
    if not plan.due:
        return RetryOutcome(
            label=job.label,
            state="skipped",
            note=plan.refusal or plan.skipped_reason or "nothing due",
        )
    if dry_run:
        return RetryOutcome(
            label=job.label,
            state="would_run",
            partitions=[item.partition for item in plan.due],
            note="dry run: nothing was invoked",
        )

    with acquire_retry_lock(Path(job.lock_path), now=now) as held:
        if held is None:
            return RetryOutcome(
                label=job.label,
                state="skipped",
                partitions=[item.partition for item in plan.due],
                note="another guard tick holds the retry lock",
            )
        live_ledger = reload() if reload is not None else ledger
        confirmed = plan_retries(now=now, job=job, ledger=live_ledger)
        if not confirmed.due:
            return RetryOutcome(
                label=job.label,
                state="skipped",
                note=(
                    confirmed.refusal
                    or confirmed.skipped_reason
                    or "another tick served this attempt first"
                ),
            )
        partitions = [item.partition for item in confirmed.due]
        code = run(_retry_command(job, confirmed.due))

        if code == EXIT_LOCK_HELD:
            # nothing ran, so nothing was attempted: the next tick must try
            # again. Recording it here would consume the attempt and hide a
            # wedged capture lock behind what looks like patience.
            live_ledger.mark_lock_held(job.label, at=now)
            if persist is not None:
                persist(live_ledger)
            if live_ledger is not ledger:
                ledger.mark_lock_held(job.label, at=now)
            return RetryOutcome(
                label=job.label,
                state="lock_held",
                exit_code=code,
                partitions=partitions,
                note="capture lock held; nothing was done",
            )

        for target in (live_ledger, ledger):
            target.clear_lock_held(job.label)
            for item in confirmed.due:
                target.record(job.label, item.partition, item.attempt_id, at=now)
            if target is ledger:
                break
        # persisted INSIDE the lock, so a concurrent tick cannot read a ledger
        # that has not yet learned about this attempt
        if persist is not None:
            persist(live_ledger)

    if code == EXIT_OK:
        return RetryOutcome(
            label=job.label, state="ran", exit_code=code, partitions=partitions
        )
    return RetryOutcome(
        label=job.label,
        state="failed",
        exit_code=code,
        partitions=partitions,
        note="retry CLI reported a real failure; not retried automatically",
    )


def _retry_command(job: RetryJob, due: list[DuePartition]) -> tuple[str, ...]:
    """The configured argv plus the partitions this tick actually allows.

    The guard's per-partition rate limit is meaningless if the CLI is free to
    retry everything it considers due: rate-limiting snap counts while allowing
    NGS, then invoking a bare --retry-only, retries both. Naming the selection
    makes the guard's decision the one that takes effect.
    """
    selected: tuple[str, ...] = ()
    for item in due:
        selected += ("--partition", item.partition)
    return tuple(job.command) + selected


def load_retry_jobs(path: Path, receipts: dict[str, ReceiptSpec]) -> list[RetryJob]:
    """Feed-retry jobs, for the explicitly configured labels only.

    Additive to ``load_config`` rather than folded into it: existing callers
    keep their three-tuple, and a config with no ``feed_retry`` key behaves
    exactly as it does today.
    """
    payload = json.loads(Path(path).read_text())
    jobs: list[RetryJob] = []
    for label, entry in (payload.get("feed_retry") or {}).items():
        receipt = receipts.get(label)
        if receipt is None:
            # a retry job with no receipt has nothing to read; skipping it
            # quietly would be a retry path nobody can see
            raise ValueError(f"feed_retry names {label}, which has no receipts entry")
        command = tuple(entry["command"])
        if not command:
            raise ValueError(f"feed_retry {label} names no command")
        jobs.append(
            RetryJob(
                label=label,
                receipt_path=receipt.receipt_path,
                command=command,
                min_interval=timedelta(minutes=int(entry.get("min_interval_minutes", 60))),
                lock_path=entry.get("lock_path", "app/data/ops/catchup_guard_retry.lock"),
            )
        )
    return jobs
