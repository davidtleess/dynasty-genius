"""DG-053 RED — capture the ff_playerids crosswalk on cadence, content-addressed.

Written test-first 2026-08-26 (David: "2. pre freeze"). The product's canonical
identity today keys off ONE frozen crosswalk snapshot from 2026-05-16; in-season
the crosswalk changes weekly (rookies signed, ids minted, teams corrected) and
every unsnapshotted week is identity truth the 2027 rebuild's as-of joins can
never recover. This job captures the crosswalk daily: content-addressed,
idempotent on unchanged content, and it NEVER touches the frozen snapshot
production consumers read — capture only, zero consumer change.

Hermetic: fetch is injected, all paths are tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _cap():
    name = "run_ff_playerids_snapshot_capture"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_ff_playerids_snapshot_capture.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


ROWS_V1 = [
    {"gsis_id": "00-001", "sleeper_id": "111", "name": "Alpha", "mfl_id": None},
    {"gsis_id": "00-002", "sleeper_id": "222", "name": "Beta", "mfl_id": "9"},
]
ROWS_V2 = [
    {"gsis_id": "00-001", "sleeper_id": "111", "name": "Alpha", "mfl_id": None},
    {"gsis_id": "00-002", "sleeper_id": "222", "name": "Beta", "mfl_id": "9"},
    {"gsis_id": "00-003", "sleeper_id": "333", "name": "Gamma", "mfl_id": None},
]


def _run(tmp_path, rows, day="2026-08-26"):
    cap = _cap()
    return cap.run_capture(
        snapshots_dir=tmp_path / "snaps",
        marker_path=tmp_path / "marker.json",
        today=day,
        fetch_fn=lambda: [dict(r) for r in rows],
    )


def _marker(tmp_path):
    return json.loads((tmp_path / "marker.json").read_text(encoding="utf-8"))


def _latest(tmp_path):
    return json.loads((tmp_path / "snaps" / "latest.json").read_text(encoding="utf-8"))


class TestFirstCapture:
    def test_writes_content_addressed_snapshot_latest_and_marker(self, tmp_path):
        assert _run(tmp_path, ROWS_V1) == 0
        latest = _latest(tmp_path)
        snap = tmp_path / "snaps" / latest["snapshot_file"]
        assert snap.is_file()
        assert latest["content_sha256"] in latest["snapshot_file"][:60] or len(latest["content_sha256"]) == 64
        assert latest["rows"] == 2
        marker = _marker(tmp_path)
        assert marker["status"] == "ok"
        assert marker["changed"] is True
        assert marker["content_sha256"] == latest["content_sha256"]

    def test_snapshot_content_round_trips(self, tmp_path):
        _run(tmp_path, ROWS_V1)
        latest = _latest(tmp_path)
        rows = json.loads(
            (tmp_path / "snaps" / latest["snapshot_file"]).read_text(encoding="utf-8")
        )["rows"]
        assert {r["gsis_id"] for r in rows} == {"00-001", "00-002"}


class TestIdempotency:
    def test_unchanged_content_writes_no_new_snapshot(self, tmp_path):
        _run(tmp_path, ROWS_V1, day="2026-08-26")
        first = _latest(tmp_path)["snapshot_file"]
        assert _run(tmp_path, ROWS_V1, day="2026-08-27") == 0
        assert _latest(tmp_path)["snapshot_file"] == first
        snaps = [p.name for p in (tmp_path / "snaps").glob("ff_playerids_*.json")]
        assert len(snaps) == 1
        marker = _marker(tmp_path)
        assert marker["status"] == "ok" and marker["changed"] is False

    def test_row_order_does_not_change_the_hash(self, tmp_path):
        _run(tmp_path, ROWS_V1)
        sha1 = _latest(tmp_path)["content_sha256"]
        _run(tmp_path, list(reversed(ROWS_V1)), day="2026-08-27")
        assert _latest(tmp_path)["content_sha256"] == sha1


class TestChangeCapture:
    def test_changed_content_writes_a_second_snapshot_and_repoints_latest(self, tmp_path):
        _run(tmp_path, ROWS_V1, day="2026-08-26")
        first = _latest(tmp_path)["snapshot_file"]
        assert _run(tmp_path, ROWS_V2, day="2026-08-27") == 0
        latest = _latest(tmp_path)
        assert latest["snapshot_file"] != first
        assert latest["rows"] == 3
        assert (tmp_path / "snaps" / first).is_file()  # history is append-only
        assert _marker(tmp_path)["changed"] is True


class TestFailure:
    def test_fetch_failure_is_a_loud_marker_and_exit_1(self, tmp_path):
        cap = _cap()

        def boom():
            raise RuntimeError("upstream 404")

        rc = cap.run_capture(
            snapshots_dir=tmp_path / "snaps",
            marker_path=tmp_path / "marker.json",
            today="2026-08-26",
            fetch_fn=boom,
        )
        assert rc == 1
        marker = _marker(tmp_path)
        assert marker["status"] == "failed"
        assert "upstream 404" in marker["failure_reason"]
        assert not list((tmp_path / "snaps").glob("ff_playerids_*.json"))

    def test_failure_after_a_good_snapshot_leaves_latest_standing(self, tmp_path):
        cap = _cap()
        _run(tmp_path, ROWS_V1)
        good = _latest(tmp_path)

        def boom():
            raise RuntimeError("timeout")

        rc = cap.run_capture(
            snapshots_dir=tmp_path / "snaps",
            marker_path=tmp_path / "marker.json",
            today="2026-08-27",
            fetch_fn=boom,
        )
        assert rc == 1
        assert _latest(tmp_path) == good
        assert _marker(tmp_path)["status"] == "failed"
