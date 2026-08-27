"""DG-044 / SR-11 RED — the daily capture gap alert, and SR-10a's registration.

Written test-first 2026-08-26 (D4), before ``scripts/run_capture_gap_alert.py``
existed and before ``app/config/capture_cadence.json`` registered
``market_divergence_history``. Spec: docs/strategies/2026-08-20-dg-SEASON-BUILD-SPEC.md
SR-11 (:595-749, MIG-1) and SR-10a step 1 (:955-1020). Ticket:
~/dg-build/tickets/DG-044-sr11-daily-capture-gap-alert.md.

Everything here is hermetic: scratch configs, scratch SQLite stores, scratch
markers, canned ``launchctl print`` output. The ONLY reads of real repo state
are the checked-in cadence config and the checked-in pin file — both tracked
files, never gitignored runtime data.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "app" / "config" / "capture_cadence.json"
TZ = ZoneInfo("America/New_York")


def _alert():
    """Load scripts/run_capture_gap_alert.py as a module (scripts/ is no package).

    The module must sit in ``sys.modules`` before exec: dataclass annotation
    resolution on 3.14 looks the defining module up by name.
    """
    import sys

    name = "run_capture_gap_alert"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_capture_gap_alert.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def _write_plist(path: Path, label: str, calendar: object) -> None:
    import plistlib

    payload: dict = {
        "Label": label,
        "RunAtLoad": False,
        "ProgramArguments": ["/usr/bin/true"],
    }
    if calendar is not None:
        payload["StartCalendarInterval"] = calendar
    path.write_bytes(plistlib.dumps(payload))


# Verbatim shapes from `launchctl print gui/501/...` on this machine, 2026-08-26.
# The dg-cockpit-backup output carries NESTED `state = active` lines from
# dispatch-source sub-blocks AFTER the top-level `state =` — first match wins.
LAUNCHCTL_HEALTHY_NEVER_RAN = """\
	active count = 0
	path = /Users/davidleess/x/ops/launchd/com.example.job.plist
	state = not running
	program = /Users/davidleess/x/.venv/bin/python3.14
	runs = 0
	last exit code = (never exited)
	properties = inferred program | needs LWCR update | managed LWCR
"""

LAUNCHCTL_RAN_AND_FAILED = """\
	state = not running
	runs = 1
	last exit code = 127
		state = active
		state = active
"""

LAUNCHCTL_RAN_OK = """\
	state = not running
	runs = 3
	last exit code = 0
"""

# The 2026-08-22 incident shape: spawn-failed jobs left in launchd's in-memory
# penalty box (recorded in machine notes; kickstart does NOT clear this state).
LAUNCHCTL_PENALTY_BOX = """\
	state = spawn scheduled
	properties = penalty box | inferred program
	runs = 0
	last exit code = (never exited)
"""


# --- Cycle A: the launchd channel (MIG-1 steps 7-9 scaffolding) ----------------


class TestDeriveJobSchedules:
    """Spec step 7: derive the label list from the plist directory, never a
    hand-kept list — and non-recursively, so ops/launchd/retired/ never leaks
    back into the sweep after SR-09."""

    def test_labels_come_from_plists_non_recursively(self, tmp_path: Path) -> None:
        _write_plist(tmp_path / "com.a.daily.plist", "com.a.daily", {"Hour": 6, "Minute": 15})
        _write_plist(
            tmp_path / "com.b.tuesday.plist",
            "com.b.tuesday",
            {"Hour": 9, "Minute": 35, "Weekday": 2},
        )
        (tmp_path / "retired").mkdir()
        _write_plist(tmp_path / "retired" / "com.c.old.plist", "com.c.old", {"Hour": 9, "Minute": 0})
        (tmp_path / "README.md").write_text("not a plist", encoding="utf-8")

        schedules = _alert().derive_job_schedules(tmp_path)

        assert [s.label for s in schedules] == ["com.a.daily", "com.b.tuesday"]

    def test_calendar_interval_array_form_yields_multiple_slots(self, tmp_path: Path) -> None:
        _write_plist(
            tmp_path / "com.d.retry.plist",
            "com.d.retry",
            [{"Hour": 11, "Minute": 30}, {"Hour": 14, "Minute": 0}],
        )

        (schedule,) = _alert().derive_job_schedules(tmp_path)

        assert [(s.hour, s.minute) for s in schedule.slots] == [(11, 30), (14, 0)]

    def test_a_plist_with_no_calendar_interval_still_appears_with_no_slots(
        self, tmp_path: Path
    ) -> None:
        _write_plist(tmp_path / "com.e.interval.plist", "com.e.interval", None)

        (schedule,) = _alert().derive_job_schedules(tmp_path)

        assert schedule.label == "com.e.interval"
        assert schedule.slots == []


class TestParseLaunchctlPrint:
    def test_never_ran_job_parses_runs_zero_and_never_exited(self) -> None:
        state = _alert().parse_launchctl_print(LAUNCHCTL_HEALTHY_NEVER_RAN)

        assert state.runs == 0
        assert state.last_exit_code is None
        assert state.never_exited is True
        assert state.penalty_box is False

    def test_failed_job_parses_numeric_exit_and_ignores_nested_state_lines(self) -> None:
        state = _alert().parse_launchctl_print(LAUNCHCTL_RAN_AND_FAILED)

        assert state.runs == 1
        assert state.last_exit_code == 127
        assert state.never_exited is False
        assert state.penalty_box is False

    def test_penalty_box_is_detected(self) -> None:
        state = _alert().parse_launchctl_print(LAUNCHCTL_PENALTY_BOX)

        assert state.penalty_box is True
        assert state.runs == 0

    def test_not_loaded_returns_none(self) -> None:
        assert _alert().parse_launchctl_print(None) is None


class TestSlotsPassedToday:
    def _slot(self, hour: int, minute: int, weekday: int | None = None):
        return _alert().Slot(hour=hour, minute=minute, weekday=weekday)

    def test_morning_slot_has_passed_by_1030(self) -> None:
        now = datetime(2026, 8, 26, 10, 30, tzinfo=TZ)  # a Wednesday
        passed = _alert().slots_passed_today([self._slot(6, 15)], now)
        assert len(passed) == 1

    def test_a_slot_inside_the_grace_window_has_not_passed(self) -> None:
        # The alert's own 10:30 slot must not read as "passed" while the alert
        # itself is the thing running at 10:30:xx.
        now = datetime(2026, 8, 26, 10, 31, tzinfo=TZ)
        assert _alert().slots_passed_today([self._slot(10, 30)], now) == []

    def test_weekday_slot_only_counts_on_its_weekday(self) -> None:
        wednesday = datetime(2026, 8, 26, 12, 0, tzinfo=TZ)
        tuesday = datetime(2026, 8, 25, 12, 0, tzinfo=TZ)
        tuesday_slot = [self._slot(9, 35, weekday=2)]  # launchd: Tuesday == 2

        assert _alert().slots_passed_today(tuesday_slot, wednesday) == []
        assert len(_alert().slots_passed_today(tuesday_slot, tuesday)) == 1


class TestNeverAttempted:
    """Class (f): runs = 0 on a job whose slot has already passed today.
    Nothing else in this ticket can see it — a job that never spawned writes
    no store, no marker, no log, no exit code."""

    def test_runs_zero_with_a_passed_slot_is_named(self) -> None:
        m = _alert()
        now = datetime(2026, 8, 26, 10, 30, tzinfo=TZ)
        state = m.parse_launchctl_print(LAUNCHCTL_HEALTHY_NEVER_RAN)
        passed = m.slots_passed_today([m.Slot(hour=6, minute=15, weekday=None)], now)

        line = m.never_attempted_line("com.a.daily", state, passed)

        assert line is not None
        assert "com.a.daily" in line
        assert "never attempted" in line
        assert "06:15" in line

    def test_runs_zero_with_no_passed_slot_is_silent(self) -> None:
        m = _alert()
        state = m.parse_launchctl_print(LAUNCHCTL_HEALTHY_NEVER_RAN)

        assert m.never_attempted_line("com.a.daily", state, []) is None

    def test_a_job_that_ran_is_silent(self) -> None:
        m = _alert()
        now = datetime(2026, 8, 26, 10, 30, tzinfo=TZ)
        state = m.parse_launchctl_print(LAUNCHCTL_RAN_OK)
        passed = m.slots_passed_today([m.Slot(hour=6, minute=15, weekday=None)], now)

        assert m.never_attempted_line("com.a.daily", state, passed) is None


class TestPenaltyBox:
    """Class (g): in-memory only, destroyed by reboot, and kickstart does NOT
    clear it — the line must hand the operator bootout + bootstrap."""

    def test_penalty_boxed_job_is_named_with_the_right_remedy(self) -> None:
        m = _alert()
        state = m.parse_launchctl_print(LAUNCHCTL_PENALTY_BOX)

        line = m.penalty_box_line("com.b.job", state)

        assert line is not None
        assert "com.b.job" in line
        assert "bootout" in line
        assert "bootstrap" in line
        assert "kickstart" not in line

    def test_a_healthy_job_is_silent(self) -> None:
        m = _alert()
        state = m.parse_launchctl_print(LAUNCHCTL_RAN_OK)

        assert m.penalty_box_line("com.b.job", state) is None


class TestBootToLoginGap:
    """Class (h): launchd does not replay a StartCalendarInterval slot that
    elapsed while nobody was logged in. The 08-22 counter-example: boot
    09:04:39, login 10:48:52, thirteen slots swallowed silently."""

    def test_slots_inside_the_gap_are_named_and_declared_unreplayable(self) -> None:
        m = _alert()
        boot = datetime(2026, 8, 22, 9, 4, 39, tzinfo=TZ)
        login = datetime(2026, 8, 22, 10, 48, 52, tzinfo=TZ)
        schedules = [
            m.JobSchedule(
                label="com.x.what-changed",
                slots=[m.Slot(hour=9, minute=45, weekday=None)],
                path=Path("x.plist"),
            ),
            m.JobSchedule(
                label="com.x.backup",
                slots=[m.Slot(hour=10, minute=15, weekday=None)],
                path=Path("y.plist"),
            ),
            m.JobSchedule(
                label="com.x.afternoon",
                slots=[m.Slot(hour=11, minute=30, weekday=None)],
                path=Path("z.plist"),
            ),
        ]

        lines = m.boot_to_login_lines(schedules, boot_time=boot, login_time=login)

        assert len(lines) == 2
        assert any("com.x.what-changed" in line for line in lines)
        assert any("com.x.backup" in line for line in lines)
        assert all("will not replay" in line for line in lines)
        assert not any("com.x.afternoon" in line for line in lines)

    def test_no_gap_no_lines(self) -> None:
        m = _alert()
        boot = datetime(2026, 8, 26, 5, 0, tzinfo=TZ)
        login = datetime(2026, 8, 26, 5, 1, tzinfo=TZ)
        schedules = [
            m.JobSchedule(
                label="com.x.job",
                slots=[m.Slot(hour=6, minute=15, weekday=None)],
                path=Path("x.plist"),
            )
        ]

        assert m.boot_to_login_lines(schedules, boot_time=boot, login_time=login) == []


def _scratch_store_config(tmp_path: Path, *, store_id: str = "scratch_store") -> Path:
    """A one-store cadence config pointing at a scratch SQLite db."""
    body = {
        "config_version": 2,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": [
            {
                "store_id": store_id,
                "db_path": "scratch.db",
                "table": "capture_raw",
                "date_column": "capture_date",
                "source_filter": None,
                "expected_settings_hash": None,
                "capture_start_date": "2026-08-20",
                "expected_cadence": "daily",
                "scheduled_time_local": "09:40",
                "grace_hours": 3,
                "density_floor_pct": 50,
                "density_baseline_window": 14,
                "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
                "window_risk_contiguous_days": 7,
                "companion_tables": [],
            }
        ],
    }
    config_path = tmp_path / "cadence.json"
    config_path.write_text(json.dumps(body), encoding="utf-8")
    return config_path


def _scratch_db(tmp_path: Path, dates: list[str]) -> None:
    import sqlite3

    connection = sqlite3.connect(tmp_path / "scratch.db")
    connection.execute("CREATE TABLE capture_raw (capture_date TEXT, payload TEXT)")
    connection.executemany(
        "INSERT INTO capture_raw VALUES (?, 'x')", [(d,) for d in dates for _ in range(5)]
    )
    connection.commit()
    connection.close()


# 10:30 on Wed 2026-08-26: the store's 09:40+3h grace deadline has not passed,
# so the analyzer's end date is yesterday — exactly the alert's morning view.
NOW = datetime(2026, 8, 26, 10, 30, tzinfo=TZ)


class TestStoreLines:
    """Classes (a) and the SR-10a dry-run target: missing dates, reported once.

    The spec demands both that the build-day dry run NAMES the historical
    2026-08-12 hole and that a clean morning is silent — irreconcilable
    without memory, since the market store's four holes are permanent
    (forward capture cannot backfill). Resolution: a known-holes state. A
    hole alerts when first seen (so a fresh state names everything, which is
    what the dry run exercises) and never again while it persists; class (a)
    still catches every new hole the morning it is born.
    """

    def test_first_sight_of_a_hole_is_named(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        _scratch_db(tmp_path, ["2026-08-20", "2026-08-21", "2026-08-23", "2026-08-24", "2026-08-25"])

        lines, holes = m.store_lines(
            config_path=config_path, repo_root=tmp_path, now=NOW, known_holes={}
        )

        assert any("scratch_store" in line and "2026-08-22" in line for line in lines)
        assert holes["scratch_store"] == ["2026-08-22"]

    def test_a_known_hole_is_silent(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        _scratch_db(tmp_path, ["2026-08-20", "2026-08-21", "2026-08-23", "2026-08-24", "2026-08-25"])

        lines, holes = m.store_lines(
            config_path=config_path,
            repo_root=tmp_path,
            now=NOW,
            known_holes={"scratch_store": ["2026-08-22"]},
        )

        assert lines == []
        assert holes["scratch_store"] == ["2026-08-22"]

    def test_a_new_hole_beside_a_known_one_is_named(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        # yesterday (08-25) missing: the class-(a) case, born this morning
        _scratch_db(tmp_path, ["2026-08-20", "2026-08-21", "2026-08-23", "2026-08-24"])

        lines, holes = m.store_lines(
            config_path=config_path,
            repo_root=tmp_path,
            now=NOW,
            known_holes={"scratch_store": ["2026-08-22"]},
        )

        assert any("2026-08-25" in line for line in lines)
        assert not any("2026-08-22" in line for line in lines)
        assert holes["scratch_store"] == ["2026-08-22", "2026-08-25"]

    def test_a_recovered_hole_leaves_the_state(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        _scratch_db(
            tmp_path,
            ["2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23", "2026-08-24", "2026-08-25"],
        )

        lines, holes = m.store_lines(
            config_path=config_path,
            repo_root=tmp_path,
            now=NOW,
            known_holes={"scratch_store": ["2026-08-22"]},
        )

        assert lines == []
        assert holes["scratch_store"] == []

    def test_an_absent_store_is_named_not_skipped(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        # no scratch.db written at all

        lines, _ = m.store_lines(
            config_path=config_path, repo_root=tmp_path, now=NOW, known_holes={}
        )

        assert any("scratch_store" in line and "store_absent" in line for line in lines)

    def test_a_new_hole_is_named_even_past_the_display_cap(self, tmp_path: Path) -> None:
        """Review IMPORTANT: the API's 20-range display cap must not blind the
        alert — a brand-new 'missing yesterday' in a store already holding 21+
        ranges is chronologically the LAST range and would be truncated out."""
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["stores"][0]["capture_start_date"] = "2026-06-01"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        # every other day present through 08-24 => far more than 20 single-day
        # ranges; 08-25 (yesterday) newly missing is the range past the cap
        from datetime import date as _date

        present = [
            (_date(2026, 6, 1) + timedelta(days=offset)).isoformat()
            for offset in range(0, 85, 2)
        ]
        present = [d for d in present if d <= "2026-08-24"]
        _scratch_db(tmp_path, present)
        known = sorted(
            {
                (_date(2026, 6, 1) + timedelta(days=offset)).isoformat()
                for offset in range(0, 85)
            }
            - set(present)
        )
        known = [d for d in known if d <= "2026-08-24"]

        lines, holes = m.store_lines(
            config_path=config_path,
            repo_root=tmp_path,
            now=NOW,
            known_holes={"scratch_store": known},
        )

        assert any("2026-08-25" in line for line in lines)
        assert "2026-08-25" in holes["scratch_store"]

    def test_a_clean_store_is_silent(self, tmp_path: Path) -> None:
        m = _alert()
        config_path = _scratch_store_config(tmp_path)
        _scratch_db(
            tmp_path,
            ["2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23", "2026-08-24", "2026-08-25"],
        )

        lines, holes = m.store_lines(
            config_path=config_path, repo_root=tmp_path, now=NOW, known_holes={}
        )

        assert lines == []
        assert holes == {"scratch_store": []}


class TestBackupLines:
    """Class (d), through the landed inspect_backup_marker — the 26-hour law,
    verification, and the DG-036 sentinel, not just ``status != completed``."""

    def _marker(self, tmp_path: Path, body: dict) -> Path:
        path = tmp_path / "backup_status_latest.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_a_fresh_verified_completed_backup_is_silent(self, tmp_path: Path) -> None:
        marker = self._marker(
            tmp_path,
            {
                "run_id": "20260826T141500Z",
                "status": "completed",
                "finished_at": "2026-08-26T10:20:00-04:00",
                "sha256_verified": True,
                "files": 666,
                "bytes": 1,
                "failures": [],
            },
        )

        lines = _alert().backup_lines(
            marker_path=marker, sentinel_path=tmp_path / "absent.json", now=NOW
        )

        assert lines == []

    def test_a_failed_backup_is_named(self, tmp_path: Path) -> None:
        marker = self._marker(
            tmp_path,
            {
                "run_id": "20260826T141500Z",
                "status": "failed",
                "finished_at": "2026-08-26T10:20:00-04:00",
                "sha256_verified": False,
                "failures": ["auth_unavailable"],
            },
        )

        lines = _alert().backup_lines(
            marker_path=marker, sentinel_path=tmp_path / "absent.json", now=NOW
        )

        assert len(lines) >= 1
        assert any("backup" in line and "backup_run_failed" in line for line in lines)

    def test_an_absent_marker_is_named(self, tmp_path: Path) -> None:
        lines = _alert().backup_lines(
            marker_path=tmp_path / "nope.json",
            sentinel_path=tmp_path / "absent.json",
            now=NOW,
        )

        assert any("backup_marker_absent" in line for line in lines)


class TestPmsetWake:
    """Class (e): some macOS updates clear ``pmset repeat`` and nothing today
    would notice. ``pmset -g sched`` is the ONLY reliable check (08-22 lesson:
    the AutoWake file paths do not exist on macOS 26 even when the schedule
    is live)."""

    def test_the_live_schedule_shape_is_silent(self) -> None:
        output = "Repeating power events:\n  wakepoweron at 6:00AM every day\n"
        assert _alert().pmset_wake_line(output) is None

    def test_the_moved_613_wake_is_also_silent(self) -> None:
        # 2026-08-27: the 6:00 wake measurably fails its purpose — the Mac
        # idles back to sleep before the 06:15 capture — so David moves it to
        # 6:13. Any wake in the 6:00-6:14 window serves the captures.
        output = "Repeating power events:\n  wakepoweron at 6:13AM every day\n"
        assert _alert().pmset_wake_line(output) is None

    def test_a_wake_after_the_capture_window_is_named(self) -> None:
        output = "Repeating power events:\n  wakepoweron at 6:15AM every day\n"
        assert _alert().pmset_wake_line(output) is not None

    def test_a_cleared_schedule_is_named(self) -> None:
        assert _alert().pmset_wake_line("No scheduled events.\n") is not None
        assert "daily wake" in _alert().pmset_wake_line("")


class TestChainReportLines:
    """Class (c): the SR-09 chain report. It does not exist until D6 — absence
    before then is expected and silent; a fail-soft chain that carried on past
    a failure must still say a failure happened."""

    def test_an_absent_report_is_silent(self, tmp_path: Path) -> None:
        assert _alert().chain_report_lines(tmp_path / "none.json") == []

    def test_failed_and_skipped_steps_are_each_named(self, tmp_path: Path) -> None:
        report = tmp_path / "daily_chain_latest_report.json"
        report.write_text(
            json.dumps(
                {
                    "steps": [
                        {"name": "market_divergence_refresh", "exit_code": 1},
                        {"name": "model_pvo_refresh", "status": "skipped_upstream_failed"},
                        {"name": "feature_refresh", "exit_code": 0, "status": "ok"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        lines = _alert().chain_report_lines(report)

        assert len(lines) == 2
        assert any("market_divergence_refresh" in line for line in lines)
        assert any("model_pvo_refresh" in line for line in lines)

    def test_an_unreadable_report_is_named_not_ignored(self, tmp_path: Path) -> None:
        report = tmp_path / "daily_chain_latest_report.json"
        report.write_text("{not json", encoding="utf-8")

        lines = _alert().chain_report_lines(report)

        assert len(lines) == 1
        assert "unreadable" in lines[0]


class TestPins:
    """Step 9: class (b) is DISARMED until the pin file exists, pins match on
    failed_stream (never exit code alone), and every pin carries a review date
    — an expired pin demands review rather than silently suppressing forever.
    This is the SR-20 cry-wolf regression test, both directions."""

    def _states(self, m, exit_code: int) -> dict:
        return {
            "com.davidleess.dynasty-nflverse-usage-capture": m.LaunchdJobState(
                runs=1, last_exit_code=exit_code, never_exited=False, penalty_box=False
            )
        }

    def _pin_file(self, tmp_path: Path, pins: list[dict]) -> Path:
        path = tmp_path / "capture_gap_accepted_exits.json"
        path.write_text(json.dumps({"pins": pins}), encoding="utf-8")
        return path

    def _nflverse_marker(self, tmp_path: Path, failed_stream: str | None) -> None:
        marker_dir = tmp_path / "app" / "data" / "nflverse_usage"
        marker_dir.mkdir(parents=True)
        (marker_dir / "nflverse_usage_status_latest.json").write_text(
            json.dumps(
                {
                    "status": "failed" if failed_stream else "ok",
                    "failed_stream": failed_stream,
                    # fresh: a pin honors only a marker from this morning's run
                    "finished_at": (NOW - timedelta(hours=4)).isoformat(),
                }
            ),
            encoding="utf-8",
        )

    def _contracts_pin(self) -> dict:
        return {
            "producer_label": "com.davidleess.dynasty-nflverse-usage-capture",
            "marker_path": "app/data/nflverse_usage/nflverse_usage_status_latest.json",
            "accepted_failed_stream": "contracts",
            "review_date": "2026-09-30",
        }

    def test_no_pin_file_means_class_b_is_disarmed(self, tmp_path: Path) -> None:
        m = _alert()
        lines, _ = m.exit_code_lines(
            self._states(m, 1), pin_path=tmp_path / "absent.json", repo_root=tmp_path, now=NOW
        )
        assert lines == []

    def test_an_empty_pin_file_arms_class_b(self, tmp_path: Path) -> None:
        m = _alert()
        pin_path = self._pin_file(tmp_path, [])

        lines, _ = m.exit_code_lines(
            self._states(m, 127), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )

        assert len(lines) == 1
        assert "nflverse" in lines[0]
        assert "127" in lines[0]

    def test_a_pinned_failure_is_silent(self, tmp_path: Path) -> None:
        m = _alert()
        pin_path = self._pin_file(tmp_path, [self._contracts_pin()])
        self._nflverse_marker(tmp_path, failed_stream="contracts")

        lines, _ = m.exit_code_lines(
            self._states(m, 1), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )

        assert lines == []

    def test_a_different_stream_failing_is_not_hidden_by_the_pin(self, tmp_path: Path) -> None:
        m = _alert()
        pin_path = self._pin_file(tmp_path, [self._contracts_pin()])
        self._nflverse_marker(tmp_path, failed_stream="depth_charts")

        lines, _ = m.exit_code_lines(
            self._states(m, 1), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )

        assert len(lines) == 1
        assert "depth_charts" in lines[0]

    def test_an_expired_pin_demands_review(self, tmp_path: Path) -> None:
        m = _alert()
        pin = self._contracts_pin() | {"review_date": "2026-08-01"}
        pin_path = self._pin_file(tmp_path, [pin])
        self._nflverse_marker(tmp_path, failed_stream="contracts")

        lines, _ = m.exit_code_lines(
            self._states(m, 1), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )

        assert len(lines) == 1
        assert "review" in lines[0].lower()

    def test_a_zero_exit_is_always_silent(self, tmp_path: Path) -> None:
        m = _alert()
        pin_path = self._pin_file(tmp_path, [])

        lines, _ = m.exit_code_lines(
            self._states(m, 0), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )
        assert lines == []


# Drifted launchctl output: fields renamed by a hypothetical macOS update.
LAUNCHCTL_DRIFTED = """\
	state = not running
	run count: 0
	exit status: (never exited)
"""


class TestCrashResilience:
    """Review CRITICAL 2026-08-26: an uncaught exception must never kill the
    detection channel silently. The crash itself becomes the alert."""

    def test_an_unreadable_config_degrades_to_a_loud_line_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        import pytest

        from app.api.routes.system_capture_health_models import (
            CaptureHealthConfigError,
            load_capture_cadence,
        )

        with pytest.raises(CaptureHealthConfigError):
            load_capture_cadence(config_path=tmp_path)  # a directory: OSError inside

        lines, _ = _alert().store_lines(
            config_path=tmp_path, repo_root=tmp_path, now=NOW, known_holes={}
        )
        assert any("config unusable" in line for line in lines)

    def test_an_out_of_range_plist_slot_is_dropped_not_fatal(self, tmp_path: Path) -> None:
        _write_plist(tmp_path / "com.typo.plist", "com.typo", {"Hour": 10, "Minute": 75})

        (schedule,) = _alert().derive_job_schedules(tmp_path)

        assert schedule.label == "com.typo"
        assert schedule.slots == []

    def test_a_crash_mid_run_still_delivers_a_crash_alert(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, notifications = TestRunAlert()._scaffold(
            m, tmp_path, store_dates=TestRunAlert.ALL_DATES
        )

        def _boom(label: str) -> str:
            raise RuntimeError("launchctl exploded")

        kwargs["launchctl_print"] = _boom

        code = m.run_and_deliver(m.Runtime(**kwargs))

        assert code == 1
        content = (tmp_path / "alerts.txt").read_text(encoding="utf-8")
        assert "crashed" in content
        assert "UNVERIFIED" in content
        assert len(notifications) == 1 and "crashed" in notifications[0]

    def test_a_crash_in_dry_run_returns_1_and_writes_nothing(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, notifications = TestRunAlert()._scaffold(
            m, tmp_path, store_dates=TestRunAlert.ALL_DATES
        )

        def _boom(label: str) -> str:
            raise RuntimeError("boom")

        kwargs["launchctl_print"] = _boom
        kwargs["dry_run"] = True

        code = m.run_and_deliver(m.Runtime(**kwargs))

        assert code == 1
        assert notifications == []
        assert not (tmp_path / "alerts.txt").exists()


class TestRebootSemantics:
    """Review IMPORTANT: launchd's runs counter is per-bootstrap. A slot that
    predates today's boot/login cannot be judged by runs=0 — a mid-morning
    reboot after a healthy 06:15 capture must not flood the channel with
    false 'never attempted' lines. Unverifiable is one consolidated line,
    naming the jobs (so a genuinely un-run job never passes unnamed) without
    asserting they never ran."""

    def test_a_reboot_after_a_healthy_run_does_not_cry_never_attempted(
        self, tmp_path: Path
    ) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.ALL_DATES)
        kwargs["launchctl_print"] = lambda label: LAUNCHCTL_HEALTHY_NEVER_RAN
        kwargs["boot_time"] = datetime(2026, 8, 26, 9, 50, tzinfo=TZ)
        kwargs["login_time"] = datetime(2026, 8, 26, 9, 52, tzinfo=TZ)

        lines = m.run_alert(m.Runtime(**kwargs))

        assert not any("never attempted" in line for line in lines)
        consolidated = [line for line in lines if "cannot verify" in line]
        assert len(consolidated) == 1
        assert "com.x.capture" in consolidated[0]

    def test_a_slot_swallowed_by_the_gap_is_not_double_reported(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.ALL_DATES)
        kwargs["launchctl_print"] = lambda label: LAUNCHCTL_HEALTHY_NEVER_RAN
        kwargs["boot_time"] = datetime(2026, 8, 26, 5, 50, tzinfo=TZ)
        kwargs["login_time"] = datetime(2026, 8, 26, 10, 28, tzinfo=TZ)

        lines = m.run_alert(m.Runtime(**kwargs))

        gap_lines = [line for line in lines if "com.x.capture" in line]
        assert any("will not replay" in line for line in gap_lines)
        assert not any("cannot verify" in line for line in gap_lines)
        assert not any("never attempted" in line for line in gap_lines)


class TestDayTwoGapEnumeration:
    """Review IMPORTANT: on the true 08-22 shape (login after 10:30) the
    alert's own slot fell in the gap, so the enumeration must be delivered by
    the FIRST run after the gap — a heartbeat older than the login proves
    this run is that first run."""

    def test_the_first_run_after_the_gap_still_enumerates_it(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.ALL_DATES)
        # the gap happened YESTERDAY; login after 10:30 meant no run that day
        kwargs["boot_time"] = datetime(2026, 8, 25, 9, 4, tzinfo=TZ)
        kwargs["login_time"] = datetime(2026, 8, 25, 10, 48, tzinfo=TZ)
        _write_plist(
            tmp_path / "launchd" / "com.x.morning.plist", "com.x.morning", {"Hour": 9, "Minute": 45}
        )
        m.append_heartbeat(tmp_path / "alerts.txt", now=datetime(2026, 8, 24, 10, 30, tzinfo=TZ))

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any(
            "com.x.morning" in line and "will not replay" in line for line in lines
        )


class TestLaunchctlDrift:
    """Review IMPORTANT: launchctl print is not a stable interface. A loaded
    job whose output no longer parses must be a loud line, never a silently
    blind channel — data we hold and cannot interpret is not health."""

    def test_unparseable_output_for_a_loaded_job_is_named(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.ALL_DATES)
        kwargs["launchctl_print"] = lambda label: (
            LAUNCHCTL_DRIFTED if label == "com.x.capture" else LAUNCHCTL_RAN_OK
        )

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any(
            "com.x.capture" in line and "unparseable" in line for line in lines
        )


class TestExitDedup:
    """Review: launchd's last exit code persists per-bootstrap, so one stale
    failure must not re-alert every morning until the job's next run. The
    state file remembers the (runs, exit) evidence already reported."""

    def _states(self, m, runs: int, exit_code: int) -> dict:
        return {
            "com.x.job": m.LaunchdJobState(
                runs=runs, last_exit_code=exit_code, never_exited=False, penalty_box=False
            )
        }

    def test_the_same_stale_failure_is_reported_once(self, tmp_path: Path) -> None:
        m = _alert()
        pin_path = tmp_path / "pins.json"
        pin_path.write_text(json.dumps({"pins": []}), encoding="utf-8")

        first, reported = m.exit_code_lines(
            self._states(m, 1, 127), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )
        second, _ = m.exit_code_lines(
            self._states(m, 1, 127),
            pin_path=pin_path,
            repo_root=tmp_path,
            now=NOW,
            reported_exits=reported,
        )
        third, _ = m.exit_code_lines(
            self._states(m, 2, 127),
            pin_path=pin_path,
            repo_root=tmp_path,
            now=NOW,
            reported_exits=reported,
        )

        assert len(first) == 1
        assert second == []
        assert len(third) == 1  # a NEW run failed — new news


class TestPinFreshness:
    """Review: a pin must never honor a STALE marker — a producer that
    crashed before writing today's marker would otherwise hide behind
    yesterday's accepted failure."""

    def test_a_stale_accepted_marker_does_not_suppress(self, tmp_path: Path) -> None:
        m = _alert()
        pins = TestPins()
        pin_path = pins._pin_file(tmp_path, [pins._contracts_pin()])
        marker_dir = tmp_path / "app" / "data" / "nflverse_usage"
        marker_dir.mkdir(parents=True)
        (marker_dir / "nflverse_usage_status_latest.json").write_text(
            json.dumps(
                {
                    "status": "failed",
                    "failed_stream": "contracts",
                    "finished_at": "2026-08-23T10:16:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        lines, _ = m.exit_code_lines(
            pins._states(m, 1), pin_path=pin_path, repo_root=tmp_path, now=NOW
        )

        assert len(lines) == 1
        assert "stale" in lines[0]


class TestChainUnknownShape:
    """Review: a chain step carrying neither exit_code nor status must degrade
    loudly — renamed keys must not parse as all-healthy."""

    def test_a_step_with_unrecognized_keys_is_named(self, tmp_path: Path) -> None:
        report = tmp_path / "daily_chain_latest_report.json"
        report.write_text(
            json.dumps({"steps": [{"name": "x", "exit": 1}]}), encoding="utf-8"
        )

        lines = _alert().chain_report_lines(report)

        assert len(lines) == 1
        assert "unreadable" in lines[0]


class TestNotifyDeliveryFailure:
    """Review: osascript failing must leave a trace in the one channel that
    cannot be permission-suppressed — the alert file."""

    def test_a_failed_notification_is_recorded_in_the_file(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.HOLE_DATES)
        kwargs["notify"] = lambda message: False

        m.run_alert(m.Runtime(**kwargs))

        content = (tmp_path / "alerts.txt").read_text(encoding="utf-8")
        assert "delivery failed" in content


class TestDryRunNamesNeverAttempted:
    """DG-035 option (b)'s close condition, self-evidencing in the suite:
    a dry run must name a runs = 0 job."""

    def test_dry_run_names_a_never_attempted_job(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = TestRunAlert()._scaffold(m, tmp_path, store_dates=TestRunAlert.ALL_DATES)
        kwargs["dry_run"] = True
        kwargs["launchctl_print"] = lambda label: (
            LAUNCHCTL_HEALTHY_NEVER_RAN if label == "com.x.capture" else LAUNCHCTL_RAN_OK
        )

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any(
            "com.x.capture" in line and "never attempted" in line for line in lines
        )


class TestCheckedInPinFile:
    """Step 9's pin file must EXIST (class (b) stays disarmed without it) and
    every pin it ever carries must name its producer, its marker, its accepted
    failed_stream, and a review date — a pin with no expiry is how an accepted
    defect becomes a permanent one.

    Content note, measured 2026-08-26 06:22 ET: the nflverse/contracts pin the
    spec drafted is NOT warranted anymore — DG-040 fixed the schema drift and
    the live marker reads status=ok / failed_stream=None (second consecutive
    scheduled success). The file therefore ships with zero pins, armed."""

    PIN_PATH = REPO_ROOT / "app" / "config" / "capture_gap_accepted_exits.json"

    def test_the_pin_file_exists_and_is_loadable(self) -> None:
        raw = json.loads(self.PIN_PATH.read_text(encoding="utf-8"))

        assert isinstance(raw["pins"], list)
        assert raw.get("measured"), (
            "the pin file must cite the measurement its content is based on"
        )

    def test_every_pin_carries_the_four_required_fields(self) -> None:
        raw = json.loads(self.PIN_PATH.read_text(encoding="utf-8"))

        for pin in raw["pins"]:
            assert pin.get("producer_label")
            assert pin.get("marker_path")
            assert pin.get("accepted_failed_stream")
            assert _alert()._parse_iso_date(pin.get("review_date")) is not None, (
                f"pin for {pin.get('producer_label')} needs an ISO review_date"
            )


class TestHeartbeat:
    """Step 8: the alert must survive the conditions it reports on. A
    heartbeat line every run; a heartbeat aged past one day plus grace means
    the alert itself missed a run, reported retroactively."""

    def test_heartbeat_appends_a_timestamp_line(self, tmp_path: Path) -> None:
        m = _alert()
        alert_file = tmp_path / "alerts.txt"

        m.append_heartbeat(alert_file, now=NOW)
        m.append_heartbeat(alert_file, now=NOW + timedelta(days=1))

        content = alert_file.read_text(encoding="utf-8")
        assert content.count("HEARTBEAT") == 2
        assert m.read_last_heartbeat(alert_file) == NOW + timedelta(days=1)

    def test_no_file_means_first_run_and_no_line(self, tmp_path: Path) -> None:
        m = _alert()
        assert m.read_last_heartbeat(tmp_path / "absent.txt") is None
        assert m.missed_self_line(None, now=NOW) is None

    def test_a_fresh_heartbeat_is_silent(self) -> None:
        m = _alert()
        assert m.missed_self_line(NOW - timedelta(hours=24), now=NOW) is None

    def test_a_sleep_delayed_late_run_is_not_a_missed_run(self) -> None:
        # launchd DOES replay a slot missed while asleep; a 13:05 wake-and-run
        # with yesterday's 10:30 heartbeat is the day's (late) run, not a miss.
        m = _alert()
        late_now = NOW.replace(hour=13, minute=5)

        assert m.missed_self_line(NOW - timedelta(days=1), now=late_now) is None

    def test_an_aged_heartbeat_reports_the_missed_self_run(self) -> None:
        m = _alert()
        line = m.missed_self_line(NOW - timedelta(days=2), now=NOW)

        assert line is not None
        assert "alert" in line.lower()
        assert "2026-08-24" in line


class TestRunAlert:
    """The assembly. Silence must mean healthy: a clean morning returns no
    lines, notifies nothing, and leaves only a heartbeat. Dry-run evaluates
    everything and touches nothing. The state file is what keeps permanent
    holes from nagging daily while letting a fresh dry run name them all."""

    def _scaffold(self, m, tmp_path: Path, *, store_dates: list[str]) -> dict:
        _scratch_store_config(tmp_path)
        _scratch_db(tmp_path, store_dates)
        plist_dir = tmp_path / "launchd"
        plist_dir.mkdir()
        _write_plist(plist_dir / "com.x.capture.plist", "com.x.capture", {"Hour": 6, "Minute": 15})
        _write_plist(
            plist_dir / "own.plist", m.OWN_LABEL, {"Hour": 10, "Minute": 30}
        )
        (tmp_path / "backup.json").write_text(
            json.dumps(
                {
                    "run_id": "20260826T141500Z",
                    "status": "completed",
                    "finished_at": "2026-08-26T10:20:00-04:00",
                    "sha256_verified": True,
                    "failures": [],
                }
            ),
            encoding="utf-8",
        )
        notifications: list[str] = []
        return dict(
            repo_root=tmp_path,
            config_path=tmp_path / "cadence.json",
            plist_dir=plist_dir,
            alert_file=tmp_path / "alerts.txt",
            state_path=tmp_path / "state.json",
            pin_path=tmp_path / "pins-absent.json",
            chain_report_path=tmp_path / "chain-absent.json",
            backup_marker_path=tmp_path / "backup.json",
            backup_sentinel_path=tmp_path / "sentinel-absent.json",
            now=NOW,
            launchctl_print=lambda label: LAUNCHCTL_RAN_OK,
            pmset_sched="Repeating power events:\n  wakepoweron at 6:00AM every day\n",
            boot_time=datetime(2026, 8, 26, 5, 0, tzinfo=TZ),
            login_time=datetime(2026, 8, 26, 5, 1, tzinfo=TZ),
            notify=notifications.append,
            dry_run=False,
        ), notifications

    ALL_DATES = ["2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23", "2026-08-24", "2026-08-25"]
    HOLE_DATES = ["2026-08-20", "2026-08-21", "2026-08-23", "2026-08-24", "2026-08-25"]

    def test_a_clean_morning_is_silent_but_leaves_a_heartbeat(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, notifications = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)

        lines = m.run_alert(m.Runtime(**kwargs))

        assert lines == []
        assert notifications == []
        content = (tmp_path / "alerts.txt").read_text(encoding="utf-8")
        assert content.count("HEARTBEAT") == 1
        assert "GAP" not in content
        state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
        assert state["holes_by_store"] == {"scratch_store": []}

    def test_a_new_hole_alerts_once_then_goes_quiet(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, notifications = self._scaffold(m, tmp_path, store_dates=self.HOLE_DATES)

        first = m.run_alert(m.Runtime(**kwargs))
        second = m.run_alert(m.Runtime(**kwargs))

        assert any("2026-08-22" in line for line in first)
        assert len(notifications) == 1
        assert second == []
        assert len(notifications) == 1
        content = (tmp_path / "alerts.txt").read_text(encoding="utf-8")
        assert "2026-08-22" in content
        assert content.count("HEARTBEAT") == 2

    def test_dry_run_evaluates_everything_and_touches_nothing(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, notifications = self._scaffold(m, tmp_path, store_dates=self.HOLE_DATES)
        kwargs["dry_run"] = True

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any("2026-08-22" in line for line in lines)
        assert notifications == []
        assert not (tmp_path / "alerts.txt").exists()
        assert not (tmp_path / "state.json").exists()

    def test_a_never_attempted_job_is_named_through_the_assembly(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)
        kwargs["launchctl_print"] = lambda label: (
            LAUNCHCTL_HEALTHY_NEVER_RAN if label == "com.x.capture" else LAUNCHCTL_RAN_OK
        )

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any("com.x.capture" in line and "never attempted" in line for line in lines)

    def test_an_unloaded_job_is_named_but_the_alerts_own_label_is_exempt(
        self, tmp_path: Path
    ) -> None:
        m = _alert()
        kwargs, _ = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)
        kwargs["launchctl_print"] = lambda label: (
            None if label in ("com.x.capture", m.OWN_LABEL) else LAUNCHCTL_RAN_OK
        )

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any("com.x.capture" in line and "not loaded" in line for line in lines)
        assert not any(m.OWN_LABEL in line for line in lines)

    def test_a_boot_to_login_gap_this_morning_is_named(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)
        kwargs["boot_time"] = datetime(2026, 8, 26, 5, 50, tzinfo=TZ)
        kwargs["login_time"] = datetime(2026, 8, 26, 10, 48, tzinfo=TZ)

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any(
            "com.x.capture" in line and "will not replay" in line for line in lines
        )

    def test_an_old_boot_login_pair_is_not_replayed_daily(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)
        kwargs["boot_time"] = datetime(2026, 8, 22, 9, 4, tzinfo=TZ)
        kwargs["login_time"] = datetime(2026, 8, 22, 10, 48, tzinfo=TZ)

        lines = m.run_alert(m.Runtime(**kwargs))

        assert not any("will not replay" in line for line in lines)

    def test_an_aged_heartbeat_is_reported_retroactively(self, tmp_path: Path) -> None:
        m = _alert()
        kwargs, _ = self._scaffold(m, tmp_path, store_dates=self.ALL_DATES)
        m.append_heartbeat(tmp_path / "alerts.txt", now=NOW - timedelta(days=2))

        lines = m.run_alert(m.Runtime(**kwargs))

        assert any("missed at least one run" in line for line in lines)


class TestNotLoaded:
    """A committed plist is not an installed plist (the 08-23 backup incident):
    a label in ops/launchd/ that launchd does not hold is drift worth a line —
    except the alert's own label, whose liveness is the heartbeat's job and
    which is legitimately unloaded between commit and David's bootstrap."""

    def test_unloaded_job_is_named(self) -> None:
        line = _alert().not_loaded_line(
            "com.x.job", own_label="com.davidleess.dynasty-capture-gap-alert"
        )

        assert line is not None
        assert "com.x.job" in line
        assert "not loaded" in line

    def test_the_alerts_own_label_is_exempt(self) -> None:
        own = "com.davidleess.dynasty-capture-gap-alert"

        assert _alert().not_loaded_line(own, own_label=own) is None


def _real_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


# --- SR-10a step 1: the store with four measured holes must be alertable -------


class TestMarketDivergenceRegistration:
    """SR-10a: "an unregistered store is an unalertable store" (spec:35-38)."""

    def test_market_divergence_history_is_registered(self) -> None:
        stores = {s["store_id"]: s for s in _real_config()["stores"]}

        assert "market_divergence_history" in stores, (
            "the one store with four measured holes (2026-07-10, 07-12, 07-17, "
            "08-12) is not in the cadence config — nothing watches it"
        )
        store = stores["market_divergence_history"]
        assert store["db_path"] == "app/data/market_divergence_history.db"
        assert store["table"] == "market_divergence_history"
        assert store["date_column"] == "capture_date"
        # The store's own first date, measured — never the plist's install date.
        assert store["capture_start_date"] == "2026-07-09"
        # The plist's original slot. Deliberately NOT moved to 09:00 when SR-09
        # rewires the chain — hiding the drift would defeat the point (spec).
        assert store["scheduled_time_local"] == "09:40"

    def test_config_version_is_bumped(self) -> None:
        assert _real_config()["config_version"] >= 2

    def test_fail_closed_loader_accepts_the_real_config(self) -> None:
        from app.api.routes.system_capture_health_models import load_capture_cadence

        config = load_capture_cadence(config_path=CONFIG_PATH)

        assert {
            "fc_forward_capture",
            "model_forward_capture",
            "market_divergence_history",
        } <= {s.store_id for s in config.stores}

    def test_season_window_discrepancy_is_stated_not_silent(self) -> None:
        """SR-10a step 2: two silent in-season definitions are forbidden.

        The cadence config says in-season = months [9,10,11,12,1]; both market
        producers say Aug 16 - Jan 15. The narrower cadence window must be
        explained IN the config file, and the strict loader must accept the
        annotated shape (``_Strict`` forbids unknown fields, so this requires a
        deliberate optional field, not a smuggled key).
        """
        from app.api.routes.system_capture_health_models import load_capture_cadence

        raw = _real_config()
        comment = raw["season_windows"].get("comment")

        assert comment and "Aug" in comment, (
            "the cadence in-season window is narrower than the market "
            "producers' Aug 16 - Jan 15 definition; the config must say why"
        )
        load_capture_cadence(config_path=CONFIG_PATH)
