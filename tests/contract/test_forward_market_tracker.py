"""Real archive and capture tests for automatic enrollment and due evaluation."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dynasty_genius.capture.fc_capture_adapter import capture_market_inventory
from src.dynasty_genius.capture.forward_market_tracker import (
    TrackerConfigError,
    run_track_record_cycle,
    validate_config,
)
from src.dynasty_genius.capture.track_record_store import read_record, save_record
from tests.contract.test_fc_capture_adapter import (
    make_row,
    write_receipt,
    write_source_db,
)
from tests.contract.test_forward_market_tracker_cli import world


def inventory(config, now):
    return capture_market_inventory(
        source_db=Path(config["source_db"]),
        latest_receipt=Path(config["latest_receipt"]),
        store_root=Path(config["capture_root"]),
        historical_receipts=[Path(p) for p in config.get("historical_receipts", [])],
        observed_at=now,
    )["captures"]


def seeded(tmp_path):
    config, _ = world(tmp_path)
    now = datetime.now(timezone.utc)
    captures = inventory(config, now)
    first = run_track_record_cycle(config=config, captures=captures, now=now)
    assert first["errors"] == []
    assert first["enrollment"]["created"] is True
    record = read_record(
        Path(config["evaluation_root"]), first["enrollment"]["record_id"]
    )
    return config, now, captures, record


@pytest.mark.parametrize(
    "bad",
    [
        "shared",
        "equal_outputs",
        "relative",
        "wrong_report",
        "missing_report",
        "historical_overlap",
    ],
)
def test_bad_configuration_refuses_before_store_writes(tmp_path, bad):
    config, _ = world(tmp_path)
    if bad == "shared":
        config["runs_root"] = "/Users/davidleess/dynasty-genius-product/app/data/ops"
    elif bad == "equal_outputs":
        config["runs_root"] = config["capture_root"]
    elif bad == "relative":
        config["runs_root"] = "relative"
    elif bad == "wrong_report":
        config["expected_report_sha256"] = "f" * 64
    elif bad == "missing_report":
        config["template_snapshot_id"] = "f" * 64
    elif bad == "historical_overlap":
        config["runs_root"] = config["historical_receipts"][0]
    with pytest.raises(TrackerConfigError):
        validate_config(config)
    assert not Path(config["evaluation_root"]).exists()


def test_future_and_stale_starts_wait_without_enrollment(tmp_path):
    config, _ = world(tmp_path)
    now = datetime.now(timezone.utc)
    captures = inventory(config, now)
    future = copy.deepcopy(captures[-1])
    future["as_of"] = (now + timedelta(days=1)).isoformat()
    waiting = run_track_record_cycle(config=config, captures=[future], now=now)
    assert not waiting["enrollment"]["created"] and not waiting["errors"]
    stale = run_track_record_cycle(
        config=config, captures=captures, now=now + timedelta(days=2)
    )
    assert not stale["enrollment"]["created"] and not stale["errors"]


def test_enrollment_freezes_real_comparator_and_does_not_duplicate(tmp_path):
    config, now, captures, record = seeded(tmp_path)
    market = record["document"]["market"]
    assert (
        market["comparator_capture"] is not None and market["comparator_reason"] == ""
    )
    assert market["state"] == "awaiting_capture"
    second = run_track_record_cycle(
        config=config, captures=captures, now=now + timedelta(hours=1)
    )
    assert not second["enrollment"]["created"]
    assert second["enrollment"]["record_id"] == record["record_id"]
    assert {e["state"] for e in second["evaluations"]} == {"awaiting"}


def test_other_forecast_enrollment_does_not_block_this_forecast(tmp_path):
    config, now, captures, record = seeded(tmp_path)
    config["evaluation_root"] = str(tmp_path / "other-evaluations")
    document = copy.deepcopy(record["document"])
    document["forecast_identity"] = "f" * 64
    oldroot = (
        tmp_path
        / "evaluations"
        / record["record_id"][:2]
        / record["record_id"]
        / "artifacts"
    )
    artifacts = {
        name: (oldroot / name).read_bytes() for name in record["artifact_hashes"]
    }
    save_record(
        Path(config["evaluation_root"]),
        kind="enrollment",
        document=document,
        artifacts=artifacts,
        recorded_at=now,
    )
    result = run_track_record_cycle(
        config=config, captures=captures, now=now + timedelta(seconds=1)
    )
    assert result["enrollment"]["created"] and result["errors"] == []
    actual = read_record(
        Path(config["evaluation_root"]), result["enrollment"]["record_id"]
    )
    assert actual["document"]["market"]["comparator_capture"] is not None


def future_capture(tmp_path, stamp):
    tmp_path.mkdir()
    rows = [
        make_row(
            "sleeper:" + sid,
            "Synthetic " + sid,
            "QB",
            value,
            rank,
            snapshot_date=stamp[:10],
            retrieved_at=stamp,
        )
        for sid, value, rank in [("1", 12, 2), ("2", 45, 1), ("4", 0, 3)]
    ]
    db = write_source_db(tmp_path / "source.db", rows)
    receipt = write_receipt(tmp_path / "receipt.json", rows)
    return capture_market_inventory(
        source_db=db,
        latest_receipt=receipt,
        store_root=tmp_path / "captures",
        observed_at=datetime.fromisoformat(stamp),
    )["captures"][0]


def grader(config, root, now):
    def run(prepared, entry):
        from scripts.grade_workspace_track_record import main

        return main(
            [
                "--evaluation-root",
                config["evaluation_root"],
                "--enrollment-id",
                entry["enrollment_id"],
                "--claim",
                "market",
                "--horizon-days",
                str(entry["horizon_days"]),
                "--outcome-manifest",
                str(prepared["manifest_path"]),
                "--capture-inventory",
                str(prepared["inventory_path"]),
                "--evaluated-at",
                now.isoformat(),
                "--output-root",
                str(root / str(entry["horizon_days"])),
            ]
        )

    return run


def test_due_selection_real_grade_and_idempotent_repeat(tmp_path):
    config, now, captures, record = seeded(tmp_path)
    t0 = datetime.fromisoformat(
        record["document"]["market"]["t0"].replace("Z", "+00:00")
    )
    at = t0 + timedelta(days=30, hours=1)
    endpoint = future_capture(tmp_path / "future", at.isoformat())
    capture_inventory = [*captures, endpoint]
    later = at + timedelta(hours=1)
    first = run_track_record_cycle(
        config=config,
        captures=capture_inventory,
        now=later,
        outcomes_root=tmp_path / "outcomes",
        grade=grader(config, tmp_path / "grades", later),
    )
    assert first["errors"] == []
    assert first["evaluations"][0]["grade_exit"] == 0
    second = run_track_record_cycle(
        config=config,
        captures=capture_inventory,
        now=later + timedelta(minutes=15),
        outcomes_root=tmp_path / "outcomes2",
        grade=grader(config, tmp_path / "grades2", later),
    )
    assert second["errors"] == []
    assert [e["state"] for e in second["evaluations"]] == ["skipped", "awaiting"]
    assert not (tmp_path / "outcomes2").exists()


def test_open_missing_retries_expired_missing_is_graded_once(tmp_path):
    config, now, captures, record = seeded(tmp_path)
    open_at = now + timedelta(days=31)
    waiting = run_track_record_cycle(
        config=config,
        captures=captures,
        now=open_at,
        outcomes_root=tmp_path / "open",
        grade=grader(config, tmp_path / "open-grade", open_at),
    )
    assert waiting["evaluations"][0]["state"] == "missing"
    assert (
        waiting["evaluations"][0]["retryable"] is True
        and not (tmp_path / "open").exists()
    )
    expired = now + timedelta(days=34)
    done = run_track_record_cycle(
        config=config,
        captures=captures,
        now=expired,
        outcomes_root=tmp_path / "expired",
        grade=grader(config, tmp_path / "expired-grade", expired),
    )
    assert done["errors"] == [] and done["evaluations"][0]["grade_exit"] == 0
    again = run_track_record_cycle(
        config=config, captures=captures, now=expired + timedelta(minutes=15)
    )
    assert again["evaluations"][0]["state"] == "skipped"


def test_history_corruption_prevents_new_registration(tmp_path):
    config, _ = world(tmp_path)
    now = datetime.now(timezone.utc)
    captures = inventory(config, now)
    captures[0]["market_bytes"] = b"{}"
    result = run_track_record_cycle(config=config, captures=captures, now=now)
    assert result["errors"][0]["stage"] == "history"
    assert (
        not result["enrollment"]["created"]
        and not Path(config["evaluation_root"]).exists()
    )


def test_start_capture_cannot_predate_its_preservation(tmp_path):
    config, _ = world(tmp_path)
    now = datetime.now(timezone.utc)
    captures = inventory(config, now)
    latest = max(captures, key=lambda c: c["as_of"])
    latest["observed_at"] = (now + timedelta(days=1)).isoformat()
    result = run_track_record_cycle(config=config, captures=[latest], now=now)
    assert result["errors"] == []
    assert not result["enrollment"]["created"]
    assert result["capture"]["state"] == "awaiting_capture"


def test_subsecond_start_waits_for_eligible_t0_instead_of_freezing_unavailable(
    tmp_path,
):
    config, _ = world(tmp_path)
    # The unchanged enrollment policy records T0 at whole-second precision.
    now = datetime.now(timezone.utc).replace(microsecond=700000) + timedelta(seconds=2)
    cap = future_capture(
        tmp_path / "same-second", now.replace(microsecond=500000).isoformat()
    )
    first = run_track_record_cycle(config=config, captures=[cap], now=now)
    assert first["errors"] == [] and not first["enrollment"]["created"]
    assert first["enrollment"]["primary"] is False
    assert not Path(config["evaluation_root"]).exists()
    later = run_track_record_cycle(
        config=config, captures=[cap], now=now + timedelta(seconds=10)
    )
    assert later["errors"] == [] and later["enrollment"]["created"] is True
    assert later["enrollment"]["readiness"]["market"]["state"] == "awaiting_capture"
