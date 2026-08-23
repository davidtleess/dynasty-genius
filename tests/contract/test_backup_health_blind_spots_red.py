"""DG-034 RED: the two states the 26-hour backup law cannot currently see.

BUILD-3 wired the backup status marker onto capture-health so that silence
stops reading as success. Two blind spots survived that wiring, and either one
alone lets a failed backup report ``ok``:

1. **A future-dated marker is never stale.** Staleness is
   ``now - finished_at > threshold``. A ``finished_at`` in the future yields a
   NEGATIVE delta, which is never greater than the threshold, so the 26-hour
   law can never fire again for as long as that timestamp stands. A marker
   dated 2036 reads fresh in 2026.
2. **``failures`` is echoed but never judged.** The list is read off the marker
   and passed into the descriptive echo, and never appended to ``reasons`` —
   while the returned status is literally ``"degraded" if reasons else "ok"``.

The second one carries a trap, and these tests encode which side of it we land
on. The producer (``scripts/backup_irreplaceable_data.py``) appends to the
run-level ``failures`` list from exactly one site that does not also set
``status = "failed"``: ``missing_optional:<path>`` at :229, which ``continue``s
past a declared-optional file that is absent. Every other append sits inside an
``except`` clause, so ``status`` stays ``failed``. The manifest says the same
thing in words at :253 — *"``required: false`` still means tolerated"*.

So a blanket "any failures degrades" rule would degrade the HEALTHY steady
state: this repo's manifest declares 4 optional entries, one of which
(``app/data/footballguys/observations.db``) does not exist, so today's live
marker carries exactly one ``missing_optional:`` token beside
``status=completed`` and ``sha256_verified=true``. Blanket-degrading would pin
the backup block to ``degraded`` every day forever — the DG-023 pathology,
where a signal that cries wolf on good data is worse than no signal because a
real failure becomes indistinguishable from the standing noise.

These tests therefore assert a **fail-closed allowlist**: ``missing_optional:``
is tolerated and every other token — including one this repo has never emitted
— degrades. Unknown tokens degrade, so a new producer failure mode added later
is loud by default rather than silently benign.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

_NOW = datetime(2026, 7, 2, 13, 0, tzinfo=ZoneInfo("America/New_York"))
_MARKER_RELPATH = Path("app/data/ops/backup_status_latest.json")


def _route_module():
    from app.api.routes import system_capture_health

    return system_capture_health


def _client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config_path: Path,
    repo_root: Path,
    now: datetime = _NOW,
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(route, "_CLOCK", lambda: now)
    from app.main import app

    return TestClient(app)


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _config_body() -> dict[str, Any]:
    return {
        "config_version": 1,
        "timezone": "America/New_York",
        "season_windows": {"in_season_months": [9, 10, 11, 12, 1]},
        "stores": [
            {
                "store_id": "fc_forward_capture",
                "db_path": "app/data/fc_forward_capture.db",
                "table": "fc_forward_capture_raw",
                "date_column": "snapshot_date",
                "source_filter": "fc_native",
                "expected_settings_hash": "canonical_hash",
                "capture_start_date": "2026-06-30",
                "expected_cadence": "daily",
                "scheduled_time_local": "09:00",
                "grace_hours": 3,
                "density_floor_pct": 50,
                "density_baseline_window": 14,
                "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
                "window_risk_contiguous_days": 7,
                "companion_tables": [],
            }
        ],
    }


def _marker_body(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """A marker that is healthy in every respect, with NO failures."""
    finished = _NOW - timedelta(hours=1)
    body: dict[str, Any] = {
        "schema_version": "backup_status.v1",
        "run_id": "20260702T141500Z",
        "run_prefix": "gs://example-bucket/dynasty-genius/runs/20260702T141500Z",
        "status": "completed",
        "sha256_verified": True,
        "files": 559,
        "bytes": 2520054611,
        "failures": [],
        "started_at": (finished - timedelta(minutes=39)).isoformat(),
        "finished_at": finished.isoformat(),
    }
    if overrides:
        body.update(overrides)
    return body


def _backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    marker: dict[str, Any],
    *,
    now: datetime = _NOW,
) -> dict[str, Any]:
    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    _write_json(tmp_path / _MARKER_RELPATH, marker)
    client = _client(monkeypatch, config_path=config_path, repo_root=tmp_path, now=now)
    response = client.get("/api/system/capture-health")
    assert response.status_code == 200
    return response.json()["backup"]


# --- blind spot 1: the future-dated marker ------------------------------------


def test_future_dated_marker_is_degraded(tmp_path, monkeypatch):
    """A finished_at ahead of now is an anomaly, not a free pass on staleness."""
    marker = _marker_body({"finished_at": (_NOW + timedelta(hours=3)).isoformat()})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_marker_future_dated" in backup["reasons"]


def test_far_future_marker_cannot_launder_staleness(tmp_path, monkeypatch):
    """The whole point: a 2036 timestamp must not buy permanent freshness."""
    marker = _marker_body({"finished_at": (_NOW + timedelta(days=3650)).isoformat()})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_marker_future_dated" in backup["reasons"]


def test_small_clock_skew_is_tolerated(tmp_path, monkeypatch):
    """Marker and reader share a clock; sub-minute skew must not flap the gate."""
    marker = _marker_body({"finished_at": (_NOW + timedelta(seconds=30)).isoformat()})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "ok"
    assert backup["reasons"] == []


# --- blind spot 2: failures that are never judged -----------------------------


def test_missing_optional_failure_stays_ok(tmp_path, monkeypatch):
    """The healthy steady state. This repo's live marker looks exactly like this.

    `required: false` means tolerated (backup_irreplaceable_data.py:253). If this
    degrades, the backup block reads degraded every day forever and the signal
    is worth nothing.
    """
    marker = _marker_body(
        {"failures": ["missing_optional:app/data/footballguys/observations.db"]}
    )
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "ok"
    assert backup["reasons"] == []
    assert backup["marker"]["failures"] == [
        "missing_optional:app/data/footballguys/observations.db"
    ]


def test_several_missing_optionals_still_ok(tmp_path, monkeypatch):
    marker = _marker_body(
        {
            "failures": [
                "missing_optional:app/data/footballguys/observations.db",
                "missing_optional:app/data/features_runtime/engine_b_features_runtime.csv",
            ]
        }
    )
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "ok"
    assert backup["reasons"] == []


def test_unrecognised_failure_token_degrades(tmp_path, monkeypatch):
    """Fail closed: a token this producer has never emitted must still be loud."""
    marker = _marker_body({"failures": ["upload_failed:app/data/fc_forward_capture.db"]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_unexpected_exception_token_degrades(tmp_path, monkeypatch):
    """`unexpected:<Type>` is the producer's own catch-all (backup script :376)."""
    marker = _marker_body({"failures": ["unexpected:ConnectionError"]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_one_bad_token_among_benign_ones_degrades(tmp_path, monkeypatch):
    """A real failure must not hide behind tolerated ones."""
    marker = _marker_body(
        {
            "failures": [
                "missing_optional:app/data/footballguys/observations.db",
                "unexpected:ConnectionError",
            ]
        }
    )
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_missing_optional_prefix_is_matched_not_substringed(tmp_path, monkeypatch):
    """A token that merely CONTAINS the benign prefix is not benign."""
    marker = _marker_body({"failures": ["upload_failed:missing_optional:decoy"]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_near_miss_prefix_degrades(tmp_path, monkeypatch):
    """`missing_optional_partial:` is a different token and must not be tolerated."""
    marker = _marker_body({"failures": ["missing_optional_partial:app/data/x.db"]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_bare_prefix_with_no_path_degrades(tmp_path, monkeypatch):
    """The grammar is prefix + a non-empty path. A bare prefix names nothing."""
    marker = _marker_body({"failures": ["missing_optional:"]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_malformed_failures_field_degrades(tmp_path, monkeypatch):
    """A `failures` that is not a list is a malformed marker, not a clean one."""
    marker = _marker_body({"failures": "missing_optional:app/data/x.db"})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


def test_non_string_failure_entry_degrades(tmp_path, monkeypatch):
    """Junk in the list is not evidence of health; the echo drops non-strings."""
    marker = _marker_body({"failures": [{"path": "something"}, 42]})
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert "backup_failures_present" in backup["reasons"]


# --- the two blind spots together ---------------------------------------------


def test_future_dated_and_failing_marker_degrades_on_both(tmp_path, monkeypatch):
    """The ticket's worst case, verbatim: completed + verified + future + failures."""
    marker = _marker_body(
        {
            "finished_at": (_NOW + timedelta(days=365)).isoformat(),
            "failures": ["upload_failed:everything"],
        }
    )
    backup = _backup(tmp_path, monkeypatch, marker)
    assert backup["status"] == "degraded"
    assert set(backup["reasons"]) == {
        "backup_marker_future_dated",
        "backup_failures_present",
    }
