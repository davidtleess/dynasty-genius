"""Tests for the sleep catch-up guard.

The guard's contract: for every scheduled launchd occurrence that passed
within its slot's lookback — yesterday + today for daily slots (sleep gaps do
not respect midnight), the whole 7-day period for weekly slots (no newer
occurrence supersedes a weekly miss) — if the job's receipt
artifact shows no run attempt at or after that occurrence, and the job is not
currently running, and this occurrence has not already been kicked, kick it —
in schedule order, re-reading receipts between kicks so one fresh run serves
every occurrence it covers.

The guard chases missed-due-to-sleep runs only. A run that happened and failed
still counts as attempted: retry-on-failure is the health system's territory,
and re-kicking a deterministic failure every 15 minutes would mask it. A KICK
that failed (launchctl error, unloaded job) is the opposite case: it must be
surfaced, never recorded as served.

Schedule truth derives from the launchd plists themselves (launchd_schedules),
never a hand-kept list — the first config hand-duplicated the plists and
shipped two drift bugs (Weekday lost on three jobs; one job missing).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.dynasty_genius.catchup_guard import (
    GuardState,
    JobSpec,
    ReceiptSpec,
    build_specs,
    load_config,
    occurrence_key,
    plan_kicks,
    read_receipt_ts,
    run_once,
)
from src.dynasty_genius.launchd_schedules import (
    JobSchedule,
    Slot,
    derive_job_schedules,
)

TZ = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).resolve().parents[1]

GUARD_LABEL = "com.davidleess.dynasty-catchup-guard"


def local(hour: int, minute: int = 0, day: int = 27) -> datetime:
    # 2026-08-27 is a Thursday; 2026-08-25 a Tuesday
    return datetime(2026, 8, day, hour, minute, tzinfo=TZ)


NFLVERSE = JobSpec(
    label="com.davidleess.dynasty-nflverse-usage-capture",
    slots=(Slot(6, 15),),
    receipt=ReceiptSpec(
        receipt_path="app/data/nflverse_usage/nflverse_usage_status_latest.json",
        timestamp_fields=("finished_at", "started_at"),
    ),
)
PVO = JobSpec(
    label="com.davidleess.dynasty-model-pvo-refresh",
    slots=(Slot(9, 30), Slot(11, 30), Slot(14, 0)),
    receipt=ReceiptSpec(
        receipt_path="app/data/model_capture/pvo_refresh_latest_report.json",
        timestamp_fields=(),
    ),
)
# launchd Weekday=2 is Tuesday
WEEKLY_TUESDAY = JobSpec(
    label="com.davidleess.dynasty-roster-capacity-audit",
    slots=(Slot(10, 0, weekday=2),),
    receipt=ReceiptSpec(
        receipt_path="app/data/ops/roster_capacity_audit_status_latest.json",
        timestamp_fields=("finished_at", "started_at"),
    ),
)


def plan(now, specs, receipt_ts, running=frozenset(), already_kicked=frozenset()):
    return plan_kicks(
        now=now,
        specs=specs,
        receipt_ts=receipt_ts,
        running=set(running),
        already_kicked=set(already_kicked),
    )


class TestPlanKicks:
    def test_kicks_job_whose_receipt_predates_todays_occurrence(self):
        kicks = plan(local(6, 44), [NFLVERSE], {NFLVERSE.label: local(6, 16, day=26)})
        assert [(k.label, k.occurrence) for k in kicks] == [(NFLVERSE.label, local(6, 15))]

    def test_no_kick_when_receipt_is_at_or_after_occurrence(self):
        kicks = plan(local(6, 44), [NFLVERSE], {NFLVERSE.label: local(6, 16)})
        assert kicks == []

    def test_receipt_within_startup_slack_before_occurrence_counts(self):
        # launchd can stamp a run a second or two shy of the calendar tick
        ts = local(6, 15) - timedelta(seconds=90)
        assert plan(local(6, 44), [NFLVERSE], {NFLVERSE.label: ts}) == []

    def test_no_kick_inside_grace_window(self):
        # at 06:20 launchd may still be about to fire today's slot itself
        # post-wake; yesterday's unserved slot is fair game immediately
        kicks = plan(local(6, 20), [NFLVERSE], {NFLVERSE.label: None})
        assert [k.occurrence for k in kicks] == [local(6, 15, day=26)]

    def test_missing_receipt_means_never_ran(self):
        # no receipt at all: both window days' occurrences need chasing
        kicks = plan(local(6, 44), [NFLVERSE], {NFLVERSE.label: None})
        assert [k.occurrence for k in kicks] == [local(6, 15, day=26), local(6, 15)]

    def test_no_kick_while_job_is_running(self):
        kicks = plan(
            local(6, 44), [NFLVERSE], {NFLVERSE.label: None}, running={NFLVERSE.label}
        )
        assert kicks == []

    def test_each_occurrence_kicked_at_most_once(self):
        key = occurrence_key(NFLVERSE.label, local(6, 15))
        kicks = plan(
            local(6, 44), [NFLVERSE], {NFLVERSE.label: None}, already_kicked={key}
        )
        # yesterday's 06:15 is also in the window; only today's was ledgered
        assert [k.occurrence for k in kicks] == [local(6, 15, day=26)]

    def test_a_served_weekly_job_is_never_rekicked_off_its_day(self):
        # regression pin for the shipped bug: Weekday=2 jobs declared daily
        # would have been force-run 7x/week. Tuesday's run satisfies the whole
        # week — no Thursday occurrence exists to fabricate.
        kicks = plan(
            local(11, 0),  # Thursday 2026-08-27
            [WEEKLY_TUESDAY],
            {WEEKLY_TUESDAY.label: local(10, 1, day=25)},  # this week's run
        )
        assert kicks == []

    def test_weekly_tuesday_job_is_kicked_on_a_tuesday(self):
        kicks = plan(
            local(11, 0, day=25),  # Tuesday 2026-08-25
            [WEEKLY_TUESDAY],
            {WEEKLY_TUESDAY.label: None},
        )
        assert [k.occurrence for k in kicks] == [local(10, 0, day=25)]

    def test_weekly_slot_slept_past_survives_a_multi_day_gap(self):
        # lid closes Mon 20:00, opens Thu 09:00 (travel weekend shape): the
        # Tuesday 10:00 slot has no newer occurrence to supersede it — a
        # 2-day window would silently cost the job its whole week
        kicks = plan(
            local(9, 0),  # Thursday 2026-08-27
            [WEEKLY_TUESDAY],
            {WEEKLY_TUESDAY.label: local(10, 1, day=18)},  # last week's run
        )
        assert [k.occurrence for k in kicks] == [local(10, 0, day=25)]

    def test_daily_slots_still_use_the_short_window(self):
        # a daily job's newer occurrences supersede old misses; do not chase
        # a week of stale dailies
        kicks = plan(local(6, 44), [NFLVERSE], {NFLVERSE.label: local(6, 16, day=24)})
        assert [k.occurrence for k in kicks] == [local(6, 15, day=26), local(6, 15)]

    def test_sleep_across_midnight_still_chases_yesterday(self):
        # lid closes Wed 13:00, opens Thu 00:30: Wednesday's 14:00 slot was
        # dropped by launchd and must still be chased
        kicks = plan(
            local(0, 30),
            [PVO],
            {PVO.label: local(9, 31, day=26)},
        )
        assert [k.occurrence for k in kicks] == [
            local(11, 30, day=26),
            local(14, 0, day=26),
        ]

    def test_kicks_come_back_in_schedule_order_across_days(self):
        kicks = plan(
            local(12, 0),
            [PVO, NFLVERSE],
            {PVO.label: local(14, 1, day=26), NFLVERSE.label: local(6, 16, day=26)},
        )
        assert [k.occurrence for k in kicks] == [local(6, 15), local(9, 30), local(11, 30)]


class TestReadReceiptTs:
    def test_prefers_embedded_timestamp_over_mtime(self, tmp_path: Path):
        p = tmp_path / "status.json"
        p.write_text(json.dumps({"finished_at": "2026-08-26T10:16:54+00:00"}))
        ts = read_receipt_ts(p, ("finished_at", "started_at"), tz=TZ)
        assert ts == datetime(2026, 8, 26, 10, 16, 54, tzinfo=timezone.utc)

    def test_falls_through_timestamp_fields_in_order(self, tmp_path: Path):
        # a run captured mid-flight has started_at but no finished_at yet
        p = tmp_path / "status.json"
        p.write_text(json.dumps({"started_at": "2026-08-27T10:46:33+00:00"}))
        ts = read_receipt_ts(p, ("finished_at", "started_at"), tz=TZ)
        assert ts == datetime(2026, 8, 27, 10, 46, 33, tzinfo=timezone.utc)

    def test_uses_mtime_when_no_fields_declared(self, tmp_path: Path):
        p = tmp_path / "report.json"
        p.write_text(json.dumps({"status": "ok"}))
        ts = read_receipt_ts(p, (), tz=TZ)
        assert ts is not None
        assert abs((ts - datetime.now(tz=TZ)).total_seconds()) < 60

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert read_receipt_ts(tmp_path / "absent.json", ("finished_at",), tz=TZ) is None

    def test_unparseable_json_falls_back_to_mtime(self, tmp_path: Path):
        # a half-written receipt must not crash the guard or hide the file
        p = tmp_path / "status.json"
        p.write_text("{truncated")
        assert read_receipt_ts(p, ("finished_at",), tz=TZ) is not None

    def test_non_string_timestamp_falls_back_to_mtime(self, tmp_path: Path):
        # one producer switching to epoch numbers must not sink all 13 jobs
        p = tmp_path / "status.json"
        p.write_text(json.dumps({"finished_at": 1756288614}))
        assert read_receipt_ts(p, ("finished_at",), tz=TZ) is not None

    def test_non_dict_payload_falls_back_to_mtime(self, tmp_path: Path):
        p = tmp_path / "status.json"
        p.write_text(json.dumps(["not", "a", "dict"]))
        assert read_receipt_ts(p, ("finished_at",), tz=TZ) is not None


class TestGuardState:
    def test_round_trip_and_prune(self, tmp_path: Path):
        p = tmp_path / "state.json"
        state = GuardState.load(p)
        old_key = "some.job|2026-08-20|09:15"
        fresh_key = "some.job|2026-08-27|06:15"
        state.record(old_key, at=local(9, 16, day=20))
        state.record(fresh_key, at=local(6, 45))
        state.save(p, now=local(7, 0), keep=timedelta(days=3))
        reloaded = GuardState.load(p)
        assert fresh_key in reloaded.kicked
        assert old_key not in reloaded.kicked

    def test_load_missing_or_corrupt_starts_empty(self, tmp_path: Path):
        assert GuardState.load(tmp_path / "absent.json").kicked == {}
        bad = tmp_path / "bad.json"
        bad.write_text("{nope")
        assert GuardState.load(bad).kicked == {}

    def test_bad_ledger_stamps_are_dropped_not_fatal(self, tmp_path: Path):
        # one hand-edited or half-written stamp must not stop the ledger from
        # ever persisting again (that would re-kick every tick forever)
        p = tmp_path / "state.json"
        p.write_text(
            json.dumps(
                {
                    "kicked": {
                        "a|2026-08-27|06:15": 12345,
                        "b|2026-08-27|06:30": "not-a-date",
                        "c|2026-08-27|09:00": local(9, 1).isoformat(),
                    }
                }
            )
        )
        state = GuardState.load(p)
        state.save(p, now=local(10, 0), keep=timedelta(days=3))
        assert set(GuardState.load(p).kicked) == {"c|2026-08-27|09:00"}


class TestRunOnce:
    @staticmethod
    def _receipts_static(mapping):
        return lambda: dict(mapping)

    def test_kicks_in_order_and_records_and_persists_each(self):
        events: list[str] = []
        state = GuardState()
        report = run_once(
            now_fn=lambda: local(8, 0),
            specs=[NFLVERSE],
            read_receipts=self._receipts_static({NFLVERSE.label: local(6, 16, day=26)}),
            read_running=lambda: set(),
            state=state,
            kickstart=lambda label: (events.append(f"kick:{label}"), True)[1],
            wait_for_exit=lambda label: events.append(f"wait:{label}"),
            persist=lambda: events.append("persist"),
        )
        # no trailing wait: nothing else is chained behind the last kick
        assert events == [f"kick:{NFLVERSE.label}", "persist"]
        assert [k["key"] for k in report["kicked"]] == [
            occurrence_key(NFLVERSE.label, local(6, 15))
        ]
        assert report["kick_failures"] == []
        assert occurrence_key(NFLVERSE.label, local(6, 15)) in state.kicked

    def test_waits_between_kicks_to_preserve_chain_order(self):
        # A (06:15) must finish before B (06:30) starts, but the last kick in
        # a chain blocks nobody and is not waited on
        transaction = JobSpec(
            label="com.davidleess.dynasty-league-transaction-capture",
            slots=(Slot(6, 30),),
            receipt=ReceiptSpec(
                receipt_path="app/data/league_transactions/transaction_capture_status_latest.json",
                timestamp_fields=("finished_at", "started_at"),
            ),
        )
        events: list[str] = []
        report = run_once(
            now_fn=lambda: local(8, 0),
            specs=[NFLVERSE, transaction],
            read_receipts=self._receipts_static(
                {
                    NFLVERSE.label: local(6, 16, day=26),
                    transaction.label: local(6, 31, day=26),
                }
            ),
            read_running=lambda: set(),
            state=GuardState(),
            kickstart=lambda label: (events.append(f"kick:{label}"), True)[1],
            wait_for_exit=lambda label: events.append(f"wait:{label}"),
            persist=lambda: None,
        )
        assert events == [
            f"kick:{NFLVERSE.label}",
            f"wait:{NFLVERSE.label}",
            f"kick:{transaction.label}",
        ]
        assert len(report["kicked"]) == 2

    def test_fresh_receipt_after_first_kick_serves_later_occurrences(self):
        # wake at noon with pvo (09:30, 11:30) stale: ONE fresh run covers both
        kicked: list[str] = []
        receipts = {PVO.label: local(14, 1, day=26)}

        def kickstart(label: str) -> bool:
            kicked.append(label)
            receipts[label] = local(12, 1)  # the kicked run wrote its receipt
            return True

        report = run_once(
            now_fn=lambda: local(12, 0),
            specs=[PVO],
            read_receipts=lambda: dict(receipts),
            read_running=lambda: set(),
            state=GuardState(),
            kickstart=kickstart,
            wait_for_exit=lambda label: None,
            persist=lambda: None,
        )
        assert kicked == [PVO.label]
        assert len(report["kicked"]) == 1

    def test_failed_kick_is_surfaced_never_recorded_as_served(self):
        state = GuardState()
        waited: list[str] = []
        report = run_once(
            now_fn=lambda: local(8, 0),
            specs=[NFLVERSE],
            read_receipts=self._receipts_static({NFLVERSE.label: None}),
            read_running=lambda: set(),
            state=state,
            kickstart=lambda label: False,  # unloaded plist / typo'd label
            wait_for_exit=waited.append,
            persist=lambda: None,
        )
        assert report["kicked"] == []
        assert [f["label"] for f in report["kick_failures"]] == [
            NFLVERSE.label,
            NFLVERSE.label,  # yesterday's and today's occurrences both failed
        ]
        assert state.kicked == {}  # next tick retries; nothing marked served
        assert waited == []  # nothing started, nothing to wait for

    def test_nothing_to_do_reports_clean(self):
        report = run_once(
            now_fn=lambda: local(6, 44),
            specs=[NFLVERSE],
            read_receipts=self._receipts_static({NFLVERSE.label: local(6, 16)}),
            read_running=lambda: set(),
            state=GuardState(),
            kickstart=lambda label: (_ for _ in ()).throw(AssertionError("no kick")),
            wait_for_exit=lambda label: None,
            persist=lambda: None,
        )
        assert report["kicked"] == []
        assert report["kick_failures"] == []
        assert report["checked"] == 1


class TestBuildSpecs:
    def test_joins_schedules_to_receipts_and_surfaces_gaps(self, tmp_path: Path):
        schedules = derive_job_schedules(REPO_ROOT / "ops/launchd")
        receipts = {
            "com.davidleess.dynasty-nflverse-usage-capture": NFLVERSE.receipt,
        }
        unguarded = {GUARD_LABEL: "the guard itself"}
        specs, unconfigured = build_specs(
            schedules, receipts=receipts, unguarded=unguarded
        )
        assert [s.label for s in specs] == [
            "com.davidleess.dynasty-nflverse-usage-capture"
        ]
        assert specs[0].slots == (Slot(6, 15),)
        # everything else scheduled in ops/launchd must be surfaced, not hidden
        assert "com.davidleess.dynasty-daily-chain" in unconfigured
        assert GUARD_LABEL not in unconfigured

    def test_a_schedule_that_lost_its_slots_is_surfaced_not_dropped(self):
        # an unparseable plist or a typo'd slot (Minute=75) yields empty slots;
        # losing guard coverage must never be silent, even with a receipt entry
        broken = JobSchedule(
            label="com.davidleess.dynasty-nflverse-usage-capture",
            slots=[],
            path=Path("ops/launchd/broken.plist"),
        )
        specs, unconfigured = build_specs(
            [broken], receipts={broken.label: NFLVERSE.receipt}, unguarded={}
        )
        assert specs == []
        assert unconfigured == [broken.label]


class TestConfigCoversTheRealPlists:
    """The drift contract: every scheduled job in ops/launchd is either
    guarded (has a receipt entry) or explicitly unguarded with a written
    reason. A new or retimed plist fails here instead of silently escaping
    sleep protection."""

    def test_every_scheduled_label_is_guarded_or_explained(self):
        tz, receipts, unguarded = load_config(REPO_ROOT / "app/config/catchup_guard.json")
        # ALL labels, slotless included: a plist that loses its slots must
        # still be accounted for, not silently exit the contract
        schedules = derive_job_schedules(REPO_ROOT / "ops/launchd")
        scheduled = {s.label for s in schedules}
        covered = set(receipts) | set(unguarded)
        assert scheduled <= covered, f"unexplained jobs: {sorted(scheduled - covered)}"
        # and no dead entries pointing at labels that no longer exist
        assert set(receipts) <= scheduled, f"stale entries: {sorted(set(receipts) - scheduled)}"

    def test_unguarded_entries_carry_a_reason(self):
        _, _, unguarded = load_config(REPO_ROOT / "app/config/catchup_guard.json")
        assert all(isinstance(reason, str) and reason for reason in unguarded.values())


class TestLoadConfig:
    def test_loads_receipts_unguarded_and_timezone(self, tmp_path: Path):
        cfg = tmp_path / "catchup_guard.json"
        cfg.write_text(
            json.dumps(
                {
                    "config_version": 2,
                    "timezone": "America/New_York",
                    "receipts": {
                        NFLVERSE.label: {
                            "receipt_path": NFLVERSE.receipt.receipt_path,
                            "timestamp_fields": ["finished_at", "started_at"],
                        }
                    },
                    "unguarded": {GUARD_LABEL: "the guard itself"},
                }
            )
        )
        tz, receipts, unguarded = load_config(cfg)
        assert tz == TZ
        assert receipts == {NFLVERSE.label: NFLVERSE.receipt}
        assert unguarded == {GUARD_LABEL: "the guard itself"}
