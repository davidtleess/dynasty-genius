"""Automatic capture-to-enrollment path against private real stores and the real clock."""

import errno
import fcntl
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import run_forward_market_tracker as cli
from src.dynasty_genius.capture.workspace_snapshot_store import save_snapshot
from tests.contract.test_fc_capture_adapter import (
    make_row,
    write_receipt,
    write_source_db,
)
from tests.ranking.test_forward_market_reading import template_bundle


def world(tmp_path):
    bundle = template_bundle(tmp_path)
    saved = save_snapshot(
        tmp_path / "template",
        bundle,
        captured_at=datetime.now(timezone.utc),
        code_sha="unknown",
    )
    now = datetime.now(timezone.utc)
    stamp = (now - timedelta(minutes=5)).isoformat()
    before = (now - timedelta(days=30, minutes=10)).isoformat()

    def rows(at):
        return [
            make_row(
                "sleeper:" + sid,
                "Synthetic " + sid,
                "QB",
                value,
                rank,
                snapshot_date=at[:10],
                retrieved_at=at,
            )
            for sid, value, rank in [("1", 10, 2), ("2", 50, 1), ("4", 0, 3)]
        ]

    current, historical = rows(stamp), rows(before)
    db = write_source_db(tmp_path / "source.db", historical, current)
    latest = write_receipt(tmp_path / "latest.json", current)
    history = write_receipt(tmp_path / "historical.json", historical)
    policy = (
        Path(__file__).resolve().parents[2]
        / "app/config/workspace_market_movement_90d_v1.json"
    )
    config = {
        "schema_version": 1,
        "template_archive_root": str(tmp_path / "template"),
        "template_snapshot_id": saved["snapshot"]["snapshot_id"],
        "archive_root": str(tmp_path / "archive"),
        "evaluation_root": str(tmp_path / "evaluations"),
        "runs_root": str(tmp_path / "runs"),
        "capture_root": str(tmp_path / "captures"),
        "market_plan_path": str(policy),
        "expected_market_plan_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "expected_report_sha256": hashlib.sha256(
            bundle.artifacts["report.json"]
        ).hexdigest(),
        "source_db": str(db),
        "latest_receipt": str(latest),
        "historical_receipts": [str(history)],
    }
    path = tmp_path / "tracker.json"
    path.write_text(json.dumps(config))
    return config, path


def receipts(config):
    return [
        json.loads(p.read_bytes())
        for p in sorted(Path(config["runs_root"]).glob("*/cycle.json"))
    ]


def test_actual_cli_captures_and_enrolls_once_with_frozen_momentum(tmp_path, capsys):
    config, path = world(tmp_path)
    before = Path(config["source_db"]).read_bytes()
    assert cli.main(["--config", str(path)]) == 0, capsys.readouterr().err
    first = receipts(config)[0]
    assert first["enrollment"]["created"] is True
    assert first["capture_inventory"]["imported"] == 2
    assert first["evaluations"][0]["state"] == "awaiting"
    assert cli.main(["--config", str(path)]) == 0, capsys.readouterr().err
    second = receipts(config)[1]
    assert second["enrollment"]["created"] is False
    assert second["enrollment"]["record_id"] == first["enrollment"]["record_id"]
    assert second["capture_inventory"]["imported"] == 0
    assert Path(config["source_db"]).read_bytes() == before
    raw = json.dumps(second)
    assert len(raw) < 16000 and "market_bytes" not in raw


def test_capture_corruption_is_reported_as_error_and_keeps_earlier_record(
    tmp_path, capsys
):
    config, path = world(tmp_path)
    assert cli.main(["--config", str(path)]) == 0, capsys.readouterr().err
    old = receipts(config)[0]["enrollment"]["record_id"]
    with sqlite3.connect(config["source_db"]) as conn:
        conn.execute("UPDATE fc_forward_capture_raw SET value=value+1")
    assert cli.main(["--config", str(path)]) == 1
    latest = receipts(config)[-1]
    assert latest["status"] == "error" and latest["errors"][0]["stage"] == "capture"
    assert (Path(config["evaluation_root"]) / old[:2] / old).is_dir()


def test_lock_contention_has_receipt_but_io_failure_is_error(
    tmp_path, capsys, monkeypatch
):
    config, path = world(tmp_path)
    root = Path(config["runs_root"])
    root.mkdir()
    with (root / ".forward-market-tracker.lock").open("a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert cli.main(["--config", str(path)]) == 0
        assert receipts(config)[-1]["status"] == "already_running"

    def fail(*args):
        raise OSError(errno.EIO, "test I/O fault")

    monkeypatch.setattr(cli.fcntl, "flock", fail)
    assert cli.main(["--config", str(path)]) == 1
    assert receipts(config)[-1]["status"] == "error"
    assert receipts(config)[-1]["errors"][0]["stage"] == "lock"
