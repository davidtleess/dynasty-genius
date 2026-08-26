"""DG-049 RED — the gap alert covers the two event-stream stores (SR-10b's scope).

Written test-first 2026-08-26 on David's "keep filling the layers."
``league_transactions`` and ``nflverse_usage`` cannot use cadence-store health
(bursty streams have legitimately quiet days; and the nflverse DB deliberately
keeps an old mtime on unchanged days). What they CAN attest is that the producer
RAN: both write an atomic status marker on every run, no-op days included. This
channel judges the marker — attested today, status ok — never the store bytes.

Alert-once semantics mirror the store channel's known-holes design: a NEW
failure signature alerts exactly once and persists silently; recovery clears it
so the next failure is loud again. Hermetic: scratch configs, scratch markers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "app" / "config" / "capture_cadence.json"
TZ = ZoneInfo("America/New_York")


def _alert():
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


NOW = datetime(2026, 8, 26, 10, 30, 0, tzinfo=TZ)


_MINIMAL_STORE = {
    "store_id": "fc_forward_capture",
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
}


def _write_config(tmp_path: Path, streams: list[dict]) -> Path:
    config = {
        "config_version": 2,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": [_MINIMAL_STORE],
        "event_streams": streams,
    }
    path = tmp_path / "cadence.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _stream(marker_rel: str, hour: int = 6, minute: int = 15) -> dict:
    return {
        "stream_id": "nflverse_usage",
        "marker": marker_rel,
        "hour": hour,
        "minute": minute,
        "grace_hours": 3.0,
    }


def _marker(tmp_path: Path, rel: str, *, finished_at: str, status: str = "ok", **extra):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"status": status, "finished_at": finished_at, **extra}),
        encoding="utf-8",
    )
    return p


class TestEventStreamConfig:
    def test_loader_accepts_event_streams(self, tmp_path):
        from app.api.routes.system_capture_health_models import load_capture_cadence

        path = _write_config(tmp_path, [_stream("m/marker.json")])
        config = load_capture_cadence(config_path=path)
        assert config.event_streams[0].stream_id == "nflverse_usage"
        assert config.event_streams[0].grace_hours == 3.0

    def test_duplicate_stream_ids_are_rejected(self, tmp_path):
        import pytest

        from app.api.routes.system_capture_health_models import (
            CaptureHealthConfigError,
            load_capture_cadence,
        )

        path = _write_config(
            tmp_path, [_stream("m/a.json"), _stream("m/b.json")]
        )
        with pytest.raises(CaptureHealthConfigError, match="duplicate"):
            load_capture_cadence(config_path=path)

    def test_absolute_marker_paths_are_rejected(self, tmp_path):
        import pytest

        from app.api.routes.system_capture_health_models import (
            CaptureHealthConfigError,
            load_capture_cadence,
        )

        path = _write_config(tmp_path, [_stream("/etc/passwd")])
        with pytest.raises(CaptureHealthConfigError, match="marker"):
            load_capture_cadence(config_path=path)

    def test_loader_still_accepts_a_config_without_event_streams(self, tmp_path):
        from app.api.routes.system_capture_health_models import load_capture_cadence

        config = {
            "config_version": 2,
            "timezone": "America/New_York",
            "season_windows": {"in_season_months": [9]},
            "stores": [_MINIMAL_STORE],
        }
        path = tmp_path / "old.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        assert load_capture_cadence(config_path=path).event_streams == []


class TestHealthyAttestation:
    def test_todays_ok_marker_is_silent(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        _marker(tmp_path, "m/marker.json", finished_at="2026-08-26T10:16:54+00:00")
        lines, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        assert lines == []
        assert issues == {}

    def test_before_slot_plus_grace_nothing_is_demanded(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json", hour=9, minute=0)])
        _marker(tmp_path, "m/marker.json", finished_at="2026-08-25T13:00:00+00:00")
        early = datetime(2026, 8, 26, 10, 30, 0, tzinfo=TZ)  # 9:00+3h = 12:00 > now
        lines, _ = alert.event_stream_lines(config, tmp_path, early, {})
        assert lines == []


class TestMissingAndStale:
    def test_absent_marker_is_loud_once_then_suppressed(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        lines, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        assert len(lines) == 1 and "nflverse_usage" in lines[0]
        again, _ = alert.event_stream_lines(config, tmp_path, NOW, issues)
        assert again == []

    def test_stale_marker_after_grace_names_the_last_attestation(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        _marker(tmp_path, "m/marker.json", finished_at="2026-08-25T10:16:54+00:00")
        lines, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        assert len(lines) == 1
        assert "nflverse_usage" in lines[0] and "2026-08-25" in lines[0]
        again, _ = alert.event_stream_lines(config, tmp_path, NOW, issues)
        assert again == []

    def test_unreadable_marker_is_loud(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        p = tmp_path / "m" / "marker.json"
        p.parent.mkdir(parents=True)
        p.write_text("{not json", encoding="utf-8")
        lines, _ = alert.event_stream_lines(config, tmp_path, NOW, {})
        assert len(lines) == 1 and "nflverse_usage" in lines[0]


class TestFailedAttestation:
    def test_failed_status_alerts_once_and_names_the_failure(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        _marker(
            tmp_path,
            "m/marker.json",
            finished_at="2026-08-26T10:16:54+00:00",
            status="failed",
            failed_stream="contracts",
        )
        lines, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        assert len(lines) == 1
        assert "failed" in lines[0] and "contracts" in lines[0]
        again, _ = alert.event_stream_lines(config, tmp_path, NOW, issues)
        assert again == []

    def test_a_new_failure_signature_re_alerts(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        _marker(
            tmp_path,
            "m/marker.json",
            finished_at="2026-08-26T10:16:54+00:00",
            status="failed",
            failed_stream="contracts",
        )
        _, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        _marker(
            tmp_path,
            "m/marker.json",
            finished_at="2026-08-26T10:20:00+00:00",
            status="failed",
            failed_stream="ngs_passing",
        )
        lines, _ = alert.event_stream_lines(config, tmp_path, NOW, issues)
        assert len(lines) == 1 and "ngs_passing" in lines[0]

    def test_recovery_clears_the_issue_so_the_next_failure_is_loud(self, tmp_path):
        alert = _alert()
        config = _write_config(tmp_path, [_stream("m/marker.json")])
        _marker(
            tmp_path,
            "m/marker.json",
            finished_at="2026-08-26T10:16:54+00:00",
            status="failed",
            failed_stream="contracts",
        )
        _, issues = alert.event_stream_lines(config, tmp_path, NOW, {})
        _marker(tmp_path, "m/marker.json", finished_at="2026-08-26T10:30:00+00:00")
        lines, issues2 = alert.event_stream_lines(config, tmp_path, NOW, issues)
        assert lines == [] and issues2 == {}
        _marker(
            tmp_path,
            "m/marker.json",
            finished_at="2026-08-26T10:40:00+00:00",
            status="failed",
            failed_stream="contracts",
        )
        relapse, _ = alert.event_stream_lines(config, tmp_path, NOW, issues2)
        assert len(relapse) == 1


class TestRealConfigContract:
    def test_the_real_config_registers_both_event_streams(self):
        from app.api.routes.system_capture_health_models import load_capture_cadence

        config = load_capture_cadence(config_path=CONFIG_PATH)
        by_id = {s.stream_id: s for s in config.event_streams}
        assert set(by_id) == {"nflverse_usage", "league_transactions"}
        nfl = by_id["nflverse_usage"]
        assert nfl.marker == "app/data/nflverse_usage/nflverse_usage_status_latest.json"
        assert (nfl.hour, nfl.minute) == (6, 15)
        lt = by_id["league_transactions"]
        assert (
            lt.marker
            == "app/data/league_transactions/transaction_capture_status_latest.json"
        )
        assert (lt.hour, lt.minute) == (6, 30)
        # slot + grace must land BEFORE the alert's 10:30 run for same-day detection
        assert nfl.hour + nfl.grace_hours < 10.5
        assert lt.hour + lt.minute / 60 + lt.grace_hours < 10.5
