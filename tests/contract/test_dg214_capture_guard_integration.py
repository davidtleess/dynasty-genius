"""DG214: actual guard -> CLI -> store/export, with a synthetic provider and clock.

No network or shared writes. This exercises the process/argument boundary that
separate capture and scheduler tests cannot prove.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dynasty_genius import nflverse_usage as capture
from src.dynasty_genius.catchup_guard import (
    RetryJob,
    RetryLedger,
    invoke_retry,
    plan_retries,
)

ROOT = Path(__file__).resolve().parents[2]

CHILD = '''
import json, os, runpy, sys
from datetime import datetime
from unittest.mock import patch
import nflreadpy as nfl
import polars as pl
from src.dynasty_genius import nflverse_usage as capture
payload = json.loads(open(os.environ["DG_CAPTURE_FIXTURE"]).read())
clock = datetime.fromisoformat(os.environ["DG_CAPTURE_CLOCK"])
mode = os.environ["DG_CAPTURE_MODE"]
original_retry = capture.run_usage_retry
calls = []
def retry(**kwargs):
    return original_retry(now_fn=lambda: clock, **kwargs)
def snaps(*args, **kwargs):
    calls.append("snap_counts")
    return pl.DataFrame(payload["snaps_added" if mode == "added" else "snaps"])
def ngs(*args, **kwargs):
    assert kwargs.get("stat_type") == "passing", kwargs
    calls.append("ngs_passing")
    return pl.DataFrame(payload["passing"])
def no_network(*args, **kwargs):
    raise AssertionError("Unexpected network request in isolated integration test")
script = sys.argv[1]
sys.argv = sys.argv[1:]
with patch.object(capture, "run_usage_retry", retry), \\
     patch.object(nfl, "load_snap_counts", snaps), \\
     patch.object(nfl, "load_nextgen_stats", ngs), \\
     patch("requests.sessions.Session.request", no_network):
    try:
        runpy.run_path(script, run_name="__main__")
    finally:
        with open(os.environ["DG_CAPTURE_CALLS"], "x") as handle:
            json.dump(calls, handle)
'''


@pytest.mark.parametrize("guard_delays_passing", [False, True])
def test_guard_cli_discovers_late_game_in_existing_feed_without_rewriting_unchanged_facts(
    tmp_path, guard_delays_passing,
):
    # Deliberately synthetic: public fixture values are relabelled to exercise
    # current-season scheduling, never represented as actual game observations.
    now = datetime.now(timezone.utc)
    season = capture.current_league_season(now.date())
    source = json.loads((ROOT / "tests/fixtures/nflverse_usage_2025_slice.json").read_text())
    snap = {**source["snap_counts"][0], "season": season, "week": 1,
            "game_id": f"{season}_01_SYN_TEST", "pfr_game_id": "synthetic-week1"}
    later = {**snap, "week": 2, "game_id": f"{season}_02_SYN_TEST",
             "pfr_game_id": "synthetic-week2", "offense_snaps": 12}
    passing = {**source["ngs_passing"][0], "season": season}
    payload = {"snaps": [snap], "snaps_added": [snap, later], "passing": [passing]}
    fixture = tmp_path / "synthetic-provider.json"
    fixture.write_text(json.dumps(payload))
    child = tmp_path / "invoke_actual_cli.py"
    child.write_text(CHILD)
    db_path, raw_root, export_root = tmp_path / "usage.db", tmp_path / "raw", tmp_path / "export"
    identity = capture.IdentityIndex.from_governed_crosswalk()
    first = capture.run_usage_capture(
        seasons=[season], specs=(capture.SNAP_COUNTS, capture.NGS_PASSING),
        identity=identity, db_path=db_path, raw_root=raw_root, export_root=export_root,
        fetch=lambda spec, year: payload["snaps" if spec.name == "snap_counts" else "passing"],
        now_fn=lambda: now,
    )
    assert {item["reason"] for item in first["retry"]["due"]} == {"current_season_revision_check"}
    original_export = capture.read_last_good_export(export_root)
    passing_sha = original_export["files"]["ngs_passing"]["sha256"]
    initial_raw = {str(path.relative_to(raw_root)) for path in raw_root.rglob("*.json")
                   if "checks" not in path.parts and path.name != capture.status_marker_path(raw_root).name}
    job = RetryJob(
        label="isolated-usage", receipt_path=str(capture.status_marker_path(raw_root)),
        command=(sys.executable, str(ROOT / "scripts/run_nflverse_usage_capture.py"),
                 "--retry-only", "--db-path", str(db_path), "--raw-root", str(raw_root),
                 "--export-root", str(export_root)),
        lock_path=str(tmp_path / "guard.lock"),
    )
    ledger = RetryLedger()
    if guard_delays_passing:
        # The guard can legitimately have a later attempt than the source receipt.
        # Its narrower selection must survive the real process/CLI boundary.
        ledger.record(job.label, f"ngs_passing:{season}", "earlier-other-attempt",
                      at=now + timedelta(minutes=30))
    invocations = []

    def tick(at, mode, label):
        plan = plan_retries(now=at, job=job, ledger=ledger)
        calls_path = tmp_path / f"{label}-calls.json"
        def execute(argv):
            invocations.append(argv)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONPATH": str(ROOT), "NFLREADPY_CACHE": "off",
                   "NFLREADPY_CACHE_DIR": str(tmp_path / "sdk-cache"),
                   "DG_CAPTURE_FIXTURE": str(fixture), "DG_CAPTURE_CLOCK": at.isoformat(),
                   "DG_CAPTURE_MODE": mode, "DG_CAPTURE_CALLS": str(calls_path)}
            done = subprocess.run([argv[0], str(child), *argv[1:]], cwd=ROOT, env=env,
                                  capture_output=True, text=True, timeout=45)
            (tmp_path / f"{label}-stdout.txt").write_text(done.stdout)
            (tmp_path / f"{label}-stderr.txt").write_text(done.stderr)
            assert done.returncode == 0, done.stderr + done.stdout[-1500:]
            return done.returncode
        return invoke_retry(job=job, plan=plan, run=execute, now=at, ledger=ledger)

    tick(now + timedelta(hours=1, seconds=1), "same", "unchanged")
    assert len(invocations) == 1
    expected_calls = {"snap_counts"} if guard_delays_passing else {"snap_counts", "ngs_passing"}
    assert set(json.loads((tmp_path / "unchanged-calls.json").read_text())) == expected_calls
    checked = json.loads(capture.status_marker_path(raw_root).read_text())
    checked_parts = {part["stream"]: part for part in checked["partitions"]}
    assert checked_parts["snap_counts"]["state"] == "unchanged"
    assert checked_parts["ngs_passing"]["state"] == ("updated" if guard_delays_passing else "unchanged")
    after_raw = {str(path.relative_to(raw_root)) for path in raw_root.rglob("*.json")
                 if "checks" not in path.parts and path.name != capture.status_marker_path(raw_root).name}
    assert after_raw == initial_raw, "Unchanged provider content created another raw revision"
    tick(now + timedelta(hours=1, minutes=2), "added", "too-early")
    assert len(invocations) == 1, "Not-due guard invoked actual CLI"
    tick(now + timedelta(hours=2, seconds=2), "added", "late-game")
    assert len(invocations) == 2
    with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute(f"SELECT COUNT(*) FROM {capture.SNAP_COUNTS.table}").fetchone()[0] == 2
        assert db.execute(f"SELECT COUNT(*) FROM {capture.NGS_PASSING.table}").fetchone()[0] == 1
    final = capture.read_last_good_export(export_root)
    assert final["files"]["ngs_passing"]["sha256"] == passing_sha
    parts = {item["partition"]: item for item in final["partition_readiness"]}
    assert parts[f"snap_counts:{season}"]["fresh_this_run"] is True
    assert parts[f"ngs_passing:{season}"]["fresh_this_run"] is False
    assert parts[f"ngs_passing:{season}"]["data_observed_at"] == now.isoformat()


CLI_BOUNDARY_CHILD = '''
import json, os, runpy, sys
from datetime import datetime
from unittest.mock import patch
import nflreadpy as nfl
import polars as pl
from src.dynasty_genius import nflverse_usage as capture
payload = json.loads(open(os.environ["DG_CAPTURE_FIXTURE"]).read())
clock = datetime.fromisoformat(os.environ["DG_CAPTURE_CLOCK"])
season = capture.current_league_season(clock.date())
calls = []
original_capture = capture.run_usage_capture
original_build = capture.build_streams
def timed_capture(**kwargs):
    kwargs["now_fn"] = lambda: clock
    return original_capture(**kwargs)
def declared_streams():
    return tuple(spec for spec in original_build() if spec.name in {"snap_counts", "ngs_passing"})
def snaps(*args, **kwargs):
    calls.append("snap_counts")
    raise ConnectionError(f"Failed to download https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.parquet: 404 Client Error: Not Found")
def ngs(*args, **kwargs):
    calls.append("ngs_passing")
    return pl.DataFrame(payload["passing"])
class InventoryResponse:
    def raise_for_status(self):
        pass
    def json(self):
        return {"assets": [{"name": f"snap_counts_{season-1}.parquet"}]}
def inventory(url, **kwargs):
    assert url == "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/snap_counts"
    calls.append("release_inventory")
    return InventoryResponse()
def no_network(*args, **kwargs):
    raise AssertionError("Unexpected network request in isolated integration test")
script = sys.argv[1]
sys.argv = sys.argv[1:]
with patch.object(capture, "run_usage_capture", timed_capture), \\
     patch.object(capture, "build_streams", declared_streams), \\
     patch.object(nfl, "load_snap_counts", snaps), \\
     patch.object(nfl, "load_nextgen_stats", ngs), \\
     patch("requests.get", inventory), \\
     patch("requests.sessions.Session.request", no_network):
    try:
        runpy.run_path(script, run_name="__main__")
    finally:
        with open(os.environ["DG_CAPTURE_CALLS"], "x") as handle:
            json.dump(calls, handle)
'''


def test_actual_cli_observes_source_absence_on_both_full_and_retry_paths(tmp_path):
    now = datetime.now(timezone.utc)
    season = capture.current_league_season(now.date())
    source = json.loads((ROOT / "tests/fixtures/nflverse_usage_2025_slice.json").read_text())
    fixture = tmp_path / "synthetic-provider.json"
    fixture.write_text(json.dumps({"passing": [{**source["ngs_passing"][0], "season": season}]}))
    child = tmp_path / "invoke_actual_cli.py"
    child.write_text(CLI_BOUNDARY_CHILD)
    raw = tmp_path / "raw"
    common = [sys.executable, str(child), str(ROOT / "scripts/run_nflverse_usage_capture.py"),
              "--db-path", str(tmp_path / "usage.db"), "--raw-root", str(raw),
              "--export-root", str(tmp_path / "export")]

    for label, at, flags in (
        ("full", now, ["--seasons", str(season)]),
        ("retry", now + timedelta(hours=1, seconds=1), ["--retry-only"]),
    ):
        calls_file = tmp_path / f"{label}-calls.json"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT),
               "NFLREADPY_CACHE": "off", "NFLREADPY_CACHE_DIR": str(tmp_path / "cache"),
               "DG_CAPTURE_FIXTURE": str(fixture), "DG_CAPTURE_CLOCK": at.isoformat(),
               "DG_CAPTURE_CALLS": str(calls_file)}
        done = subprocess.run([*common, *flags], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=45)
        assert done.returncode == 0, done.stderr + done.stdout[-2500:]
        assert set(json.loads(calls_file.read_text())) == {"snap_counts", "ngs_passing", "release_inventory"}
        status = json.loads(capture.status_marker_path(raw).read_text())
        parts = {part["stream"]: part for part in status["partitions"]}
        assert parts["snap_counts"]["state"] == "pending"
        assert parts["ngs_passing"]["state"] == ("updated" if label == "full" else "unchanged")
        assert {part["stream"] for part in status["retry"]["due"]} == {"snap_counts", "ngs_passing"}
