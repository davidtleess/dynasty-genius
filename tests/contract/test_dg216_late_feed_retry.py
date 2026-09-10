"""Contract: the guard retries a delayed feed without becoming a retry loop (DG-216).

David, 2026-09-10: late snap counts must not fail the pipeline — check what is
available, ingest what is missing, and continue. The guard already owns "an
occurrence nobody served"; this adds "a partition upstream has not published
yet", which is a different fact and must not be confused with it.

The whole risk here is that a retry path turns a real failure into a green
wait. So the capture owner (DG-215) decides what is retryable and the guard
never infers it: a deterministic failure — bad schema, auth, malformed
receipt — is surfaced, never re-invoked. The guard's own brakes are a per
(partition, attempt) ledger and an hourly floor, and neither is bypassable by
a receipt that simply asserts it is due.

Existing missed-launch behaviour is unchanged: a run that failed still counts
as attempted, and a failed KICK still retries next tick.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dynasty_genius.catchup_guard import (
    RETRY_SCHEMA,
    RetryJob,
    RetryLedger,
    acquire_retry_lock,
    invoke_retry,
    plan_retries,
    read_retry_block,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
LABEL = "com.davidleess.dynasty-nflverse-usage-capture"

# a real second process that takes the advisory lock and holds it until killed
HOLD_LOCK = (
    "import fcntl,sys,time\n"
    "h=open(sys.argv[1],'a+')\n"
    "fcntl.flock(h.fileno(), fcntl.LOCK_EX)\n"
    "print('held', flush=True)\n"
    "time.sleep(120)\n"
)


def _receipt(tmp_path: Path, retry: object, *, name: str = "usage.json") -> Path:
    path = tmp_path / name
    payload = {"finished_at": "2026-09-10T10:15:00+00:00"}
    if retry is not ...:
        payload["retry"] = retry
    path.write_text(json.dumps(payload))
    return path


def _due(**over: object) -> dict:
    base = {
        "partition": "snap_counts:2026",
        "reason": "upstream_release_absent",
        "retryable": True,
        "attempt": 3,
        "attempt_id": "a3",
        "last_attempt_at": "2026-09-10T14:00:00+00:00",
    }
    base.update(over)
    return base


def _block(**over: object) -> dict:
    base = {
        "schema_version": RETRY_SCHEMA,
        "next_retry_at": "2026-09-10T15:00:00+00:00",
        "in_flight": None,
        "due": [_due()],
    }
    base.update(over)
    return base


def _job(tmp_path: Path, receipt: Path) -> RetryJob:
    return RetryJob(
        label=LABEL,
        receipt_path=str(receipt),
        command=("/bin/true", "--retry-only"),
        min_interval=timedelta(hours=1),
        lock_path=str(tmp_path / "retry.lock"),
    )


# --------------------------------------------------------------- reading state
def test_a_receipt_with_no_retry_block_is_nothing_due_not_an_error(tmp_path: Path) -> None:
    """Every receipt in production today has no retry key. That must stay silent."""
    state = read_retry_block(_receipt(tmp_path, ...), now=NOW)
    assert state.due == []
    assert state.refusal is None


def test_a_missing_receipt_is_nothing_due(tmp_path: Path) -> None:
    state = read_retry_block(tmp_path / "absent.json", now=NOW)
    assert state.due == []
    assert state.refusal is None


def test_a_malformed_receipt_is_a_refusal_not_a_quiet_wait(tmp_path: Path) -> None:
    """The failure path must not return the success signal.

    A half-written or reshaped receipt is exactly when a retry loop would do
    the most damage, so it is surfaced and nothing is invoked.
    """
    path = tmp_path / "usage.json"
    path.write_text("{not json")
    state = read_retry_block(path, now=NOW)
    assert state.due == []
    assert state.refusal is not None
    assert "malformed" in state.refusal


def test_an_unknown_retry_schema_is_refused_never_guessed(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block(schema_version="capture.retry.v99"))
    state = read_retry_block(receipt, now=NOW)
    assert state.due == []
    assert state.refusal is not None
    assert "schema" in state.refusal


def test_a_naive_timestamp_is_refused_rather_than_assumed_utc(tmp_path: Path) -> None:
    """Two machines must not read one field differently (the DG-207 lesson)."""
    receipt = _receipt(tmp_path, _block(next_retry_at="2026-09-10T15:00:00"))
    state = read_retry_block(receipt, now=NOW)
    assert state.due == []
    assert state.refusal is not None
    assert "timezone" in state.refusal


# --------------------------------------------------------- what is retryable
def test_only_the_capture_owner_declares_retryable(tmp_path: Path) -> None:
    """A deterministic failure must never be re-invoked by the guard."""
    receipt = _receipt(
        tmp_path,
        _block(due=[_due(retryable=False, reason="schema_changed", partition="snap_counts:2026")]),
    )
    state = read_retry_block(receipt, now=NOW)
    assert state.due == []
    assert state.not_retryable == ["snap_counts:2026"]


def test_a_missing_retryable_flag_is_not_retryable(tmp_path: Path) -> None:
    """Absence must not read as permission. Only an explicit True qualifies."""
    entry = _due()
    del entry["retryable"]
    state = read_retry_block(_receipt(tmp_path, _block(due=[entry])), now=NOW)
    assert state.due == []


# -------------------------------------------------------------- due / not due
def test_a_due_partition_past_its_next_retry_is_planned(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block())
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert [p.partition for p in plan.due] == ["snap_counts:2026"]


def test_a_partition_before_its_next_retry_is_waiting_not_due(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block(next_retry_at="2026-09-10T16:00:00+00:00"))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert plan.waiting_until is not None


def test_in_flight_is_diagnostic_and_never_a_gate(tmp_path: Path) -> None:
    """Reviewer 54331 and root, jointly: a SIGKILL leaves in_flight written with
    nothing to clear it, so gating on it vetoes every later retry forever. It
    records who and when; liveness is decided by whether a lock can be taken."""
    receipt = _receipt(
        tmp_path,
        _block(in_flight={"attempt_id": "a3", "started_at": "2026-09-10T14:59:00+00:00"}),
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert [p.partition for p in plan.due] == ["snap_counts:2026"]
    assert plan.in_flight == {"attempt_id": "a3", "started_at": "2026-09-10T14:59:00+00:00"}
    assert plan.skipped_reason is None


def test_an_orphaned_in_flight_marker_does_not_veto_forever(tmp_path: Path) -> None:
    """A SIGKILL leaves in_flight written and nothing clears it. Honouring it
    forever would block every later retry — the wedge this feature exists to
    prevent. Past the grace the capture's own lock arbitrates (exit 3)."""
    receipt = _receipt(
        tmp_path,
        _block(in_flight={"attempt_id": "a3", "started_at": "2026-09-09T00:00:00+00:00"}),
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert [p.partition for p in plan.due] == ["snap_counts:2026"]


def test_an_in_flight_marker_with_no_usable_start_does_not_veto(tmp_path: Path) -> None:
    """A marker that cannot say when it started proves no liveness."""
    receipt = _receipt(tmp_path, _block(in_flight={"attempt_id": "a3"}))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert [p.partition for p in plan.due] == ["snap_counts:2026"]


# ------------------------------------------------------------- the two brakes
def test_one_invocation_per_attempt_identity(tmp_path: Path) -> None:
    """If the CLI ran and capture did not advance the attempt, do not run again.

    Re-invoking the same attempt forever is the retry loop this module exists
    to forbid; capture advancing attempt_id is what earns another invocation.
    """
    receipt = _receipt(tmp_path, _block())
    job = _job(tmp_path, receipt)
    ledger = RetryLedger()
    ledger.record(LABEL, "snap_counts:2026", "a3", at=NOW - timedelta(hours=6))
    assert plan_retries(now=NOW, job=job, ledger=ledger).due == []


def test_a_new_attempt_identity_earns_another_invocation(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block(due=[_due(attempt_id="a4", attempt=4)]))
    ledger = RetryLedger()
    ledger.record(LABEL, "snap_counts:2026", "a3", at=NOW - timedelta(hours=6))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=ledger)
    assert [p.attempt_id for p in plan.due] == ["a4"]


def test_the_hourly_floor_holds_even_for_a_new_attempt(tmp_path: Path) -> None:
    """A receipt cannot buy extra invocations by minting attempt ids."""
    receipt = _receipt(tmp_path, _block(due=[_due(attempt_id="a4")]))
    ledger = RetryLedger()
    ledger.record(LABEL, "snap_counts:2026", "a3", at=NOW - timedelta(minutes=20))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=ledger)
    assert plan.due == []
    assert plan.skipped_reason == "rate_limited"


# ------------------------------------------------------------------- overlap
def test_the_lock_prevents_two_ticks_overlapping(tmp_path: Path) -> None:
    path = tmp_path / "retry.lock"
    with acquire_retry_lock(path, now=NOW) as first:
        assert first is not None
        with acquire_retry_lock(path, now=NOW) as second:
            assert second is None, "a held lock must not be acquired twice"
    with acquire_retry_lock(path, now=NOW) as third:
        assert third is not None, "the lock must be released on exit"


def test_a_lock_held_by_a_live_process_is_respected(tmp_path: Path) -> None:
    """Real holder, not pre-written bytes: another process flocks the file."""
    path = tmp_path / "retry.lock"
    path.write_text("")
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_LOCK, str(path)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        with acquire_retry_lock(path, now=NOW) as blocked:
            assert blocked is None, "a live holder's lock must not be acquired"
    finally:
        holder.kill()
        holder.wait(timeout=10)


def test_the_lock_recovers_when_the_holder_is_killed(tmp_path: Path) -> None:
    """The wedge root and the reviewer both flagged: a SIGKILL must not leave
    the retry path locked forever. flock is released by the kernel on death,
    so recovery needs no timeout, no stale heuristic and no unlink."""
    path = tmp_path / "retry.lock"
    path.write_text("")
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_LOCK, str(path)], stdout=subprocess.PIPE, text=True
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "held"
    holder.kill()
    holder.wait(timeout=10)
    with acquire_retry_lock(path, now=NOW) as recovered:
        assert recovered is not None, "the lock must recover from holder death"


def test_the_lock_inode_is_stable_so_no_tick_can_replace_anothers_claim(
    tmp_path: Path,
) -> None:
    """Unlinking is what let one tick delete another tick's live claim.

    Existence alone is too weak a check — unlink-then-recreate satisfies it and
    still breaks mutual exclusion, because flock lives on the inode. Assert the
    inode is unchanged across an acquire/release cycle.
    """
    path = tmp_path / "retry.lock"
    path.write_text("")
    before = path.stat().st_ino
    with acquire_retry_lock(path, now=NOW) as held:
        assert held is not None
        assert path.stat().st_ino == before, "the lock inode changed while held"
    assert path.exists(), "the lock file persists; ownership is the flock, not the file"
    assert path.stat().st_ino == before, "the lock inode changed across the cycle"


# ------------------------------------------------------- late arrival, restart
def test_a_late_arrival_clears_the_due_list(tmp_path: Path) -> None:
    """When capture finally gets the data it stops declaring the partition due."""
    receipt = _receipt(tmp_path, _block(due=[]))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert plan.skipped_reason is None


def test_the_ledger_survives_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "retry_ledger.json"
    ledger = RetryLedger()
    ledger.record(LABEL, "snap_counts:2026", "a3", at=NOW)
    ledger.save(path, now=NOW, keep=timedelta(days=3))
    assert RetryLedger.load(path).invoked_at(LABEL, "snap_counts:2026", "a3") is not None


def test_a_future_receipt_does_not_grant_an_immediate_retry(tmp_path: Path) -> None:
    """A clock-skewed or hand-edited receipt claiming the future stays waiting."""
    receipt = _receipt(tmp_path, _block(next_retry_at="2027-01-01T00:00:00+00:00"))
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []


def test_a_refusal_is_reported_and_nothing_is_planned(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    path.write_text("{not json")
    job = RetryJob(
        label=LABEL,
        receipt_path=str(path),
        command=("/bin/true",),
        min_interval=timedelta(hours=1),
        lock_path=str(tmp_path / "retry.lock"),
    )
    plan = plan_retries(now=NOW, job=job, ledger=RetryLedger())
    assert plan.due == []
    assert plan.refusal is not None


@pytest.mark.parametrize("bad", ["", [], 3, "not-a-dict"])
def test_a_reshaped_retry_block_is_refused(tmp_path: Path, bad: object) -> None:
    state = read_retry_block(_receipt(tmp_path, bad), now=NOW)
    assert state.due == []
    assert state.refusal is not None


# ------------------------------------------------- invocation and exit codes
# DG-215's contract (agreed 2026-09-10):
#   0 = ran, including "checked and still waiting"
#   1 = real failure, visible; never auto-retried
#   3 = capture's own lock held, nothing done; benign, try next tick
def _plan_one(tmp_path: Path):
    receipt = _receipt(tmp_path, _block())
    job = _job(tmp_path, receipt)
    return job, plan_retries(now=NOW, job=job, ledger=RetryLedger())


def test_exit_zero_records_the_attempt_as_invoked(tmp_path: Path) -> None:
    job, plan = _plan_one(tmp_path)
    ledger = RetryLedger()
    out = invoke_retry(job=job, plan=plan, run=lambda cmd: 0, now=NOW, ledger=ledger)
    assert out.state == "ran"
    assert ledger.invoked_at(LABEL, "snap_counts:2026", "a3") is not None


def test_a_real_failure_is_surfaced_and_not_auto_retried(tmp_path: Path) -> None:
    """Exit 1 is a real failure. It must not become a green wait, and the same
    attempt must not be invoked again on the next tick."""
    job, plan = _plan_one(tmp_path)
    ledger = RetryLedger()
    out = invoke_retry(job=job, plan=plan, run=lambda cmd: 1, now=NOW, ledger=ledger)
    assert out.state == "failed"
    assert out.exit_code == 1
    assert ledger.invoked_at(LABEL, "snap_counts:2026", "a3") is not None, (
        "a failed attempt is still an attempt; re-invoking it every tick is the loop"
    )


def test_lock_held_is_benign_and_retries_next_tick(tmp_path: Path) -> None:
    job, plan = _plan_one(tmp_path)
    ledger = RetryLedger()
    out = invoke_retry(job=job, plan=plan, run=lambda cmd: 3, now=NOW, ledger=ledger)
    assert out.state == "lock_held"
    assert ledger.invoked_at(LABEL, "snap_counts:2026", "a3") is None, (
        "nothing ran, so nothing was attempted — next tick must try again"
    )


def test_a_wedged_capture_lock_stops_looking_like_waiting(tmp_path: Path) -> None:
    """DG-215's known hazard: their lock is O_EXCL removed in a finally, so a
    SIGKILL or reboot leaves it behind and every later capture refuses forever.
    Under 15-minute ticks that is a silent wedge with no data moving, so an
    hour of continuous exit 3 must read as degraded, not as patience."""
    receipt = _receipt(tmp_path, _block(
        next_retry_at="2026-09-10T09:00:00+00:00",
        due=[_due(last_attempt_at="2026-09-10T08:00:00+00:00")],
    ))
    job = _job(tmp_path, receipt)
    ledger = RetryLedger()
    earlier = NOW - timedelta(hours=2)
    first = invoke_retry(job=job, plan=plan_retries(now=earlier, job=job, ledger=ledger),
                         run=lambda cmd: 3, now=earlier, ledger=ledger)
    assert first.state == "lock_held", first
    second = invoke_retry(job=job, plan=plan_retries(now=NOW, job=job, ledger=ledger),
                          run=lambda cmd: 3, now=NOW, ledger=ledger)
    assert second.state == "lock_held", second
    assert ledger.lock_held_since(LABEL) == earlier
    assert ledger.lock_wedged(LABEL, now=NOW, threshold=timedelta(hours=1)) is True


def test_a_successful_run_clears_the_wedge_signal(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block(
        next_retry_at="2026-09-10T09:00:00+00:00",
        due=[_due(last_attempt_at="2026-09-10T08:00:00+00:00")],
    ))
    job = _job(tmp_path, receipt)
    ledger = RetryLedger()
    earlier = NOW - timedelta(hours=2)
    invoke_retry(job=job, plan=plan_retries(now=earlier, job=job, ledger=ledger),
                 run=lambda cmd: 3, now=earlier, ledger=ledger)
    invoke_retry(job=job, plan=plan_retries(now=NOW, job=job, ledger=ledger),
                 run=lambda cmd: 0, now=NOW, ledger=ledger)
    assert ledger.lock_held_since(LABEL) is None
    assert ledger.lock_wedged(LABEL, now=NOW, threshold=timedelta(hours=1)) is False


def test_an_unexpected_exit_code_is_a_failure_not_a_wait(tmp_path: Path) -> None:
    job, plan = _plan_one(tmp_path)
    out = invoke_retry(job=job, plan=plan, run=lambda cmd: 42, now=NOW, ledger=RetryLedger())
    assert out.state == "failed"


def test_dry_run_invokes_nothing_and_records_nothing(tmp_path: Path) -> None:
    """Dry-run must be truly read-only: no subprocess, no ledger, no lock."""
    job, plan = _plan_one(tmp_path)
    ledger = RetryLedger()
    calls: list[tuple[str, ...]] = []

    def run(cmd: tuple[str, ...]) -> int:
        calls.append(cmd)
        return 0

    out = invoke_retry(job=job, plan=plan, run=run, now=NOW, ledger=ledger, dry_run=True)
    assert calls == []
    assert out.state == "would_run"
    assert ledger.invoked_at(LABEL, "snap_counts:2026", "a3") is None
    assert not (tmp_path / "retry.lock").exists()


def test_the_command_is_the_configured_argv(tmp_path: Path) -> None:
    job, plan = _plan_one(tmp_path)
    seen: list[tuple[str, ...]] = []
    invoke_retry(job=job, plan=plan, run=lambda cmd: seen.append(cmd) or 0, now=NOW,
                 ledger=RetryLedger())
    assert seen == [("/bin/true", "--retry-only", "--partition", "snap_counts:2026")], (
        "the guard's per-partition selection must reach the CLI, or rate-limiting "
        "one partition while allowing another retries both"
    )


def test_nothing_due_invokes_nothing(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, _block(due=[]))
    job = _job(tmp_path, receipt)
    plan = plan_retries(now=NOW, job=job, ledger=RetryLedger())
    calls: list[object] = []
    out = invoke_retry(job=job, plan=plan, run=lambda cmd: calls.append(cmd) or 0, now=NOW,
                       ledger=RetryLedger())
    assert calls == []
    assert out.state == "skipped"


def test_a_pending_partition_missing_from_due_is_surfaced_not_treated_as_done(
    tmp_path: Path,
) -> None:
    """Reviewer 54331's amendment: a dropped partition and a finished one look
    identical unless the guard says so. Absence from `due` while the capture
    still calls it pending is a bug, and must not read as completion."""
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "finished_at": "2026-09-10T10:15:00+00:00",
                "partitions": [
                    {"partition": "snap_counts:2026", "state": "waiting"},
                    {"partition": "pbp:2026", "state": "ok"},
                ],
                "retry": _block(due=[]),
            }
        )
    )
    state = read_retry_block(path, now=NOW)
    assert state.due == []
    assert state.dropped == ["snap_counts:2026"]

    plan = plan_retries(
        now=NOW,
        job=RetryJob(
            label=LABEL,
            receipt_path=str(path),
            command=("/bin/true",),
            min_interval=timedelta(hours=1),
            lock_path=str(tmp_path / "retry.lock"),
        ),
        ledger=RetryLedger(),
    )
    assert plan.dropped == ["snap_counts:2026"]


def test_a_pending_partition_that_is_due_is_not_reported_as_dropped(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "partitions": [{"partition": "snap_counts:2026", "state": "waiting"}],
                "retry": _block(),
            }
        )
    )
    assert read_retry_block(path, now=NOW).dropped == []


# ----------------------------------------- per-partition refusal (reviewer 54331)
def test_a_future_last_attempt_refuses_only_that_partition(tmp_path: Path) -> None:
    """Reviewer's evidence: last_attempt_at 17:00Z planned at 15:00 with no
    refusal. A future stamp must never buy an immediate retry, must not vanish
    silently, and must not take the other partitions down with it."""
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(partition="snap_counts:2026", last_attempt_at="2026-09-10T17:00:00+00:00"),
                _due(partition="ngs_passing:2026", attempt_id="b1",
                     last_attempt_at="2026-09-10T08:00:00+00:00"),
            ]
        ),
    )
    state = read_retry_block(receipt, now=NOW)
    assert [p.partition for p in state.due] == ["ngs_passing:2026"]
    assert [u["partition"] for u in state.unusable] == ["snap_counts:2026"]
    assert "future" in state.unusable[0]["reason"]
    assert "rewrites it" in state.unusable[0]["reason"], "say that it clears itself"


def test_a_malformed_last_attempt_refuses_only_that_partition(tmp_path: Path) -> None:
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(partition="snap_counts:2026", last_attempt_at="not-a-time"),
                _due(partition="ngs_passing:2026", attempt_id="b1",
                     last_attempt_at="2026-09-10T08:00:00+00:00"),
            ]
        ),
    )
    state = read_retry_block(receipt, now=NOW)
    assert [p.partition for p in state.due] == ["ngs_passing:2026"]
    assert [u["partition"] for u in state.unusable] == ["snap_counts:2026"]


def test_a_recent_capture_attempt_blocks_a_retry_even_with_an_empty_ledger(
    tmp_path: Path,
) -> None:
    """Reviewer's evidence: 14:55Z planned at 15:00 because the decision came
    from an empty guard ledger instead of the canonical field. The floor must
    survive the ledger being lost."""
    receipt = _receipt(
        tmp_path, _block(due=[_due(last_attempt_at="2026-09-10T14:55:00+00:00")])
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert plan.skipped_reason == "rate_limited"


def test_the_selection_narrows_and_only_allowed_partitions_reach_the_cli(
    tmp_path: Path,
) -> None:
    """Reviewer's mixed-due evidence: snaps rate-limited, NGS allowed, and a
    bare --retry-only let the capture retry both. The guard's narrowing must
    reach the argv."""
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(partition="snap_counts:2026", last_attempt_at="2026-09-10T14:55:00+00:00"),
                _due(partition="ngs_passing:2026", attempt_id="b1",
                     last_attempt_at="2026-09-10T08:00:00+00:00"),
            ]
        ),
    )
    job = _job(tmp_path, receipt)
    plan = plan_retries(now=NOW, job=job, ledger=RetryLedger())
    assert [p.partition for p in plan.due] == ["ngs_passing:2026"]
    seen: list[tuple[str, ...]] = []
    invoke_retry(job=job, plan=plan, run=lambda cmd: seen.append(cmd) or 0, now=NOW,
                 ledger=RetryLedger())
    assert seen == [("/bin/true", "--retry-only", "--partition", "ngs_passing:2026")]
    assert "snap_counts:2026" not in " ".join(seen[0])


def test_the_decision_is_remade_inside_the_lock(tmp_path: Path) -> None:
    """Reviewer's two-tick evidence: invocations 2, ledger_entries 1 — the lock
    serialised the invocations but both ticks had decided before either
    acquired. The second must re-derive under the lock and find nothing."""
    receipt = _receipt(tmp_path, _block())
    job = _job(tmp_path, receipt)
    shared = RetryLedger()
    stale_plan_a = plan_retries(now=NOW, job=job, ledger=shared)
    stale_plan_b = plan_retries(now=NOW, job=job, ledger=shared)
    assert stale_plan_a.due and stale_plan_b.due, "both ticks decided before the lock"

    calls: list[tuple[str, ...]] = []

    def run(cmd: tuple[str, ...]) -> int:
        calls.append(cmd)
        return 0

    first = invoke_retry(job=job, plan=stale_plan_a, run=run, now=NOW, ledger=shared)
    second = invoke_retry(job=job, plan=stale_plan_b, run=run, now=NOW, ledger=shared)
    assert first.state == "ran"
    assert second.state == "skipped", "a stale plan must not invoke a served attempt"
    assert len(calls) == 1, f"the same attempt was invoked {len(calls)} times"


# ------------------------------------- canonical stamp required (root's review)
def test_a_due_entry_with_no_last_attempt_at_is_unusable(tmp_path: Path) -> None:
    """An absent stamp is as unusable as a malformed one.

    Accepting it leaves the hourly floor nothing canonical to measure from, so
    the partition becomes instantly eligible — which is precisely the hole the
    canonical field exists to close.
    """
    entry = _due()
    del entry["last_attempt_at"]
    state = read_retry_block(_receipt(tmp_path, _block(due=[entry])), now=NOW)
    assert state.due == []
    assert [u["partition"] for u in state.unusable] == ["snap_counts:2026"]
    assert "no last_attempt_at" in state.unusable[0]["reason"]


def test_a_null_last_attempt_at_is_unusable(tmp_path: Path) -> None:
    state = read_retry_block(
        _receipt(tmp_path, _block(due=[_due(last_attempt_at=None)])), now=NOW
    )
    assert state.due == []
    assert [u["partition"] for u in state.unusable] == ["snap_counts:2026"]


def test_an_all_unusable_batch_still_reports_its_diagnostics(tmp_path: Path) -> None:
    """If every entry has a bad stamp there is nothing due and nothing that
    looks wrong. The diagnostics are the only thing between that and a quiet,
    healthy-looking report."""
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(partition="snap_counts:2026", last_attempt_at="not-a-time"),
                _due(partition="ngs_passing:2026", attempt_id="b1",
                     last_attempt_at="2026-09-10T17:00:00+00:00"),
            ]
        ),
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert [u["partition"] for u in plan.unusable] == ["ngs_passing:2026", "snap_counts:2026"]


def test_a_block_refusal_still_carries_the_diagnostics_it_had(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    path.write_text("{not json")
    plan = plan_retries(
        now=NOW,
        job=RetryJob(
            label=LABEL,
            receipt_path=str(path),
            command=("/bin/true",),
            min_interval=timedelta(hours=1),
            lock_path=str(tmp_path / "retry.lock"),
        ),
        ledger=RetryLedger(),
    )
    assert plan.refusal is not None
    assert plan.due == []


# ------------------------------- current-season revision checks (root, 2026-09-10)
# The first scoping covered "the file is not published yet". The recurrence
# David actually hits is narrower and nastier: snap_counts_2026.parquet EXISTS
# and holds week 1, week 2 is late, so the capture calls it ready and unchanged
# and clears the retry — and nothing looks back. A successful current-season
# partition must therefore be able to carry a bounded re-check, and the guard
# must obey it without inferring anything about readiness from membership.
def test_a_successful_partition_can_still_be_due_for_a_revision_check(
    tmp_path: Path,
) -> None:
    """`due` membership is the capture's statement, not evidence of absence.

    The guard must not treat a partition that is data-available with observed
    coverage as pending, and must not refuse to re-check it either.
    """
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "finished_at": "2026-09-10T10:15:00+00:00",
                "partitions": [
                    {"partition": "snap_counts:2026", "state": "ok", "rows": 4812},
                ],
                "retry": _block(
                    due=[_due(reason="current_season_revision_check",
                              last_attempt_at="2026-09-10T08:00:00+00:00")]
                ),
            }
        )
    )
    state = read_retry_block(path, now=NOW)
    assert [p.partition for p in state.due] == ["snap_counts:2026"]
    assert state.due[0].reason == "current_season_revision_check"
    assert state.dropped == [], "a ready partition that IS due is not a dropped one"

    job = _job(tmp_path, path)
    seen: list[tuple[str, ...]] = []
    plan = plan_retries(now=NOW, job=job, ledger=RetryLedger())
    invoke_retry(job=job, plan=plan, run=lambda cmd: seen.append(cmd) or 0, now=NOW,
                 ledger=RetryLedger())
    assert seen == [("/bin/true", "--retry-only", "--partition", "snap_counts:2026")]


@pytest.mark.parametrize(
    "reason",
    ["current_season_revision_check", "upstream_release_absent", "not_yet_available",
     "upstream_empty_current_season", "a_reason_this_guard_has_never_seen"],
)
def test_the_guard_holds_no_reason_whitelist(tmp_path: Path, reason: str) -> None:
    """The reason vocabulary is the capture's and it is closed on that side.

    If the guard also enforced a list, adding a reason would need a synchronised
    change in two lanes and a partition would silently stop being retried in the
    window between them. The guard reports the reason and obeys `due`.
    """
    receipt = _receipt(
        tmp_path, _block(due=[_due(reason=reason, last_attempt_at="2026-09-10T08:00:00+00:00")])
    )
    state = read_retry_block(receipt, now=NOW)
    assert [p.reason for p in state.due] == [reason]


def test_a_ready_partition_absent_from_due_is_not_reported_as_dropped(
    tmp_path: Path,
) -> None:
    """Only a partition the capture still calls pending can be dropped. A ready
    one that is simply not due is finished, and must not be alarmed about."""
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "partitions": [
                    {"partition": "snap_counts:2026", "state": "ok"},
                    {"partition": "pbp:2025", "state": "ok"},
                ],
                "retry": _block(due=[]),
            }
        )
    )
    assert read_retry_block(path, now=NOW).dropped == []


def test_the_hourly_floor_applies_to_revision_checks_too(tmp_path: Path) -> None:
    """A bounded re-check is bounded. An hourly policy on a ready partition must
    not become an hourly rewrite of unchanged content."""
    receipt = _receipt(
        tmp_path,
        _block(due=[_due(reason="current_season_revision_check",
                         last_attempt_at="2026-09-10T14:40:00+00:00")]),
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert plan.skipped_reason == "rate_limited"


# ------------------------- interrupted capture (reviewer 54331's cross-lane hole)
def test_a_running_receipt_with_no_retry_block_is_surfaced_not_read_as_healthy(
    tmp_path: Path,
) -> None:
    """Absence carries two facts under one shape.

    "Nothing is pending" and "we were killed before writing what was" look
    identical, because DG-215's running marker carries no retry block. The
    nothing-due rule is unchanged — but the ambiguity is reported rather than
    read as health, so an interrupted capture is visible before the next daily
    full run instead of after it.
    """
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"status": "running", "started_at": "2026-09-10T14:00:00+00:00"}))
    state = read_retry_block(path, now=NOW)
    assert state.due == []
    assert state.refusal is None, "still not an error — the rule did not change"
    assert state.interrupted is not None
    assert "pending queue cannot be read" in state.interrupted

    plan = plan_retries(now=NOW, job=_job(tmp_path, path), ledger=RetryLedger())
    assert plan.interrupted is not None, "the diagnostic must survive to the report"


def test_a_finished_receipt_with_no_retry_block_stays_silent(tmp_path: Path) -> None:
    """Every healthy receipt in production today looks like this. It must not
    start alarming."""
    state = read_retry_block(_receipt(tmp_path, ...), now=NOW)
    assert state.due == []
    assert state.interrupted is None
    assert state.refusal is None


def test_the_lock_takes_no_ttl_argument(tmp_path: Path) -> None:
    """A live TTL beside a lock whose correctness argument is that it has none
    is an invitation to wire it back up. There is nothing to wire."""
    import inspect

    from src.dynasty_genius import catchup_guard as guard

    assert "ttl" not in inspect.signature(acquire_retry_lock).parameters
    assert not hasattr(guard, "RETRY_LOCK_TTL")


# ---------------- attempt_interrupted, DG-215's fourth reason (flagged 2026-09-10)
# Their running marker now carries the merged retry block, checkpointed after
# every partition, so the crashed-with-no-retry-key case is unreachable rather
# than merely visible. A start-of-attempt record that survives a kill is neither
# pending nor error — the fetch never reported anything — so it arrives as
# reason "attempt_interrupted" with data_available false, and it is retryable
# because an interruption is not evidence of a failure.
def test_an_interrupted_attempt_flows_through_like_any_other_reason(
    tmp_path: Path,
) -> None:
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(
                    reason="attempt_interrupted",
                    data_available=False,
                    last_attempt_at="2026-09-10T08:00:00+00:00",
                )
            ]
        ),
    )
    state = read_retry_block(receipt, now=NOW)
    assert [p.reason for p in state.due] == ["attempt_interrupted"]

    job = _job(tmp_path, receipt)
    seen: list[tuple[str, ...]] = []
    invoke_retry(
        job=job,
        plan=plan_retries(now=NOW, job=job, ledger=RetryLedger()),
        run=lambda cmd: seen.append(cmd) or 0,
        now=NOW,
        ledger=RetryLedger(),
    )
    assert seen == [("/bin/true", "--retry-only", "--partition", "snap_counts:2026")]


def test_unknown_entry_fields_are_ignored_not_fatal(tmp_path: Path) -> None:
    """The capture may add fields the guard does not read. Additive changes on
    their side must never need a synchronised change on mine."""
    receipt = _receipt(
        tmp_path,
        _block(
            due=[
                _due(
                    data_available=False,
                    state="interrupted",
                    some_future_field={"nested": [1, 2, 3]},
                    last_attempt_at="2026-09-10T08:00:00+00:00",
                )
            ]
        ),
    )
    assert [p.partition for p in read_retry_block(receipt, now=NOW).due] == ["snap_counts:2026"]


def test_an_interrupted_attempt_still_serves_its_hourly_floor(tmp_path: Path) -> None:
    """Their stamp is now written BEFORE the fetch, so a partition killed
    mid-fetch is not instantly due even with my ledger lost — which is the half
    a surviving queue alone does not give."""
    receipt = _receipt(
        tmp_path,
        _block(
            due=[_due(reason="attempt_interrupted",
                      last_attempt_at="2026-09-10T14:40:00+00:00")]
        ),
    )
    plan = plan_retries(now=NOW, job=_job(tmp_path, receipt), ledger=RetryLedger())
    assert plan.due == []
    assert plan.skipped_reason == "rate_limited"


def test_a_running_receipt_that_carries_its_queue_is_not_flagged_interrupted(
    tmp_path: Path,
) -> None:
    """DG-215's fix makes the ambiguous case unreachable. My rev-3 diagnostic
    must go quiet for it rather than firing on every in-progress capture."""
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "status": "running",
                "partitions": [{"partition": "snap_counts:2026", "state": "interrupted"}],
                "retry": _block(
                    in_flight={"attempt_id": "a3", "started_at": "2026-09-10T14:59:00+00:00"},
                    due=[_due(reason="attempt_interrupted",
                              last_attempt_at="2026-09-10T08:00:00+00:00")],
                ),
            }
        )
    )
    state = read_retry_block(path, now=NOW)
    assert state.interrupted is None, "a running marker that carries its queue is not ambiguous"
    assert [p.reason for p in state.due] == ["attempt_interrupted"]
    assert state.dropped == [], "the partition is in due, so it is not dropped"


def test_an_interrupted_partition_missing_from_due_is_reported_as_dropped(
    tmp_path: Path,
) -> None:
    """An attempt that died mid-fetch is unfinished by definition. If it never
    reaches the queue it looks exactly like a completed partition, which is the
    same bug as a dropped pending one — found by writing the test above."""
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "status": "ok",
                "partitions": [
                    {"partition": "snap_counts:2026", "state": "interrupted"},
                    {"partition": "pbp:2025", "state": "ok"},
                ],
                "retry": _block(due=[]),
            }
        )
    )
    assert read_retry_block(path, now=NOW).dropped == ["snap_counts:2026"]
