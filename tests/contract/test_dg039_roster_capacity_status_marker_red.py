"""DG-039 RED — a refused roster-capacity audit becomes visible without
destroying the last good artifact.

The audit deliberately writes its artifact ONLY on ok (preserve-last-good, the
DG-036 instinct) — but that left a blocked run structurally invisible: nothing
anywhere recorded that today's run refused, and last week's audit stood as
current. The DG-036 shape fits exactly: a small separate status marker the
producer ALWAYS writes (both blocked branches and ok), atomically, plus its own
report-freshness registration — whose ``status_field`` declaration is honest
ONLY because the marker is written on every exit path (the DG-033 rule).

Hermetic: injected loaders, tmp paths. David's go 2026-08-26 ("do DG-039").
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRESHNESS_PATH = REPO_ROOT / "app" / "config" / "report_freshness.json"


def _audit():
    name = "run_roster_capacity_audit"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_roster_capacity_audit.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def _now():
    return "2026-08-26T15:45:00+00:00"


def _run(tmp_path, *, pvo_loader, snapshot_loader):
    audit = _audit()
    return audit.run_audit(
        report_path=tmp_path / "roster_capacity_latest.json",
        status_marker_path=tmp_path / "status_latest.json",
        universe_pvo_loader=pvo_loader,
        sleeper_snapshot_loader=snapshot_loader,
        now_fn=_now,
    )


def _marker(tmp_path):
    return json.loads((tmp_path / "status_latest.json").read_text(encoding="utf-8"))


class TestBlockedRunsAreLegible:
    def test_input_failure_writes_a_blocked_marker_and_no_artifact(self, tmp_path):
        def broken_loader():
            raise OSError("input missing")

        report = _run(tmp_path, pvo_loader=broken_loader, snapshot_loader=broken_loader)
        assert report["producer_status"] == "blocked"
        marker = _marker(tmp_path)
        assert marker["producer_status"] == "blocked"
        assert marker["finished_at"] == _now()
        assert marker["artifact_written"] is False
        assert not (tmp_path / "roster_capacity_latest.json").exists()

    def test_blocked_run_leaves_the_prior_artifact_byte_identical(self, tmp_path):
        prior = tmp_path / "roster_capacity_latest.json"
        prior_bytes = b'{"created_at": "2026-08-19T10:00:00+00:00", "status": "ok"}\n'
        prior.write_bytes(prior_bytes)

        def broken_loader():
            raise OSError("input missing")

        _run(tmp_path, pvo_loader=broken_loader, snapshot_loader=broken_loader)
        assert prior.read_bytes() == prior_bytes
        assert _marker(tmp_path)["producer_status"] == "blocked"

    def test_no_tmp_residue_after_a_marker_write(self, tmp_path):
        def broken_loader():
            raise OSError("input missing")

        _run(tmp_path, pvo_loader=broken_loader, snapshot_loader=broken_loader)
        assert not list(tmp_path.glob("*.tmp"))


class TestOkRunsAttestToo:
    def test_ok_run_writes_marker_and_artifact(self, tmp_path, monkeypatch):
        audit = _audit()

        from src.dynasty_genius.roster_capacity.models import CapacityAuditResult

        result = CapacityAuditResult.model_construct(status="ok")
        monkeypatch.setattr(
            audit, "simulate_capacity_scenarios", lambda *a, **k: result
        )
        report = _run(
            tmp_path,
            pvo_loader=lambda: {"players": []},
            snapshot_loader=lambda: {"captured_at": "2026-08-26T09:20:00+00:00"},
        )
        assert report["producer_status"] == "ok"
        marker = _marker(tmp_path)
        assert marker["producer_status"] == "ok"
        assert marker["artifact_written"] is True
        assert (tmp_path / "roster_capacity_latest.json").is_file()

    def test_content_blocked_run_carries_scorecard_and_blocked_marker(
        self, tmp_path, monkeypatch
    ):
        audit = _audit()

        from src.dynasty_genius.roster_capacity.models import CapacityAuditResult

        result = CapacityAuditResult.model_construct(status="insufficient_data")
        monkeypatch.setattr(
            audit, "simulate_capacity_scenarios", lambda *a, **k: result
        )
        report = _run(
            tmp_path,
            pvo_loader=lambda: {"players": []},
            snapshot_loader=lambda: {"captured_at": "2026-08-26T09:20:00+00:00"},
        )
        assert report["producer_status"] == "blocked"
        assert _marker(tmp_path)["producer_status"] == "blocked"
        assert not (tmp_path / "roster_capacity_latest.json").exists()


class TestFreshnessRegistration:
    def test_the_marker_is_registered_with_an_honest_status_field(self):
        config = json.loads(FRESHNESS_PATH.read_text(encoding="utf-8"))
        by_id = {a["artifact_id"]: a for a in config["artifacts"]}
        entry = by_id["roster_capacity_status"]
        assert entry["path"] == "app/data/ops/roster_capacity_audit_status_latest.json"
        assert entry["status_field"] == "producer_status"
        assert entry["timestamp_field"] == "finished_at"
        assert entry["cadence"] == "weekly"
        # The artifact itself keeps NO status_field: its failures are
        # structurally invisible there (the DG-033/DG-039 rule) — only the
        # always-written marker may declare one.
        assert "status_field" not in by_id["roster_capacity"]
