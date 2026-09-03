"""DG-136 — a capture-stage refusal must exit red, not green.

Every refusal inside ``capture_model_pvo_snapshot`` is RETURNED as a report dict
(``{"status": "aborted", "aborted_reason": ...}``), never raised. The runner only
rewrote its outer ``status`` on a *raised* exception, so a returned refusal was
stored under ``capture_report`` and the run still exited 0. The standalone launchd
label did exactly that twice on 2026-08-31 (``pvo_refresh.out.log``, the 11:30 and
14:00 runs; ``model_forward_capture_raw`` has no 08-31 rows), and the 09:00 chain
would have marked the same refusal ``ok`` — it reads nothing but the exit code.

The contract these tests pin:

* a returned refusal is a capture-stage abort: outer ``status`` is ``aborted``,
  ``aborted_stage`` is ``capture``, ``aborted_reason`` is the driver's own reason;
* the runtime pair on disk is the NEW bytes — the refresh did its job and the
  serving state stays published (``restored_from_backup`` is False);
* ``main()`` exits 1 on that path, so the chain step and the standalone launchd
  label both go red;
* the receipt is still written, so the catch-up guard (which keys on the
  receipt, not the exit code) counts the run as attempted and does not re-kick it;
* the chain does not amplify: no step declares ``run_pvo_refresh`` a hard
  upstream, so market-divergence and what-changed still run over the pair.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.dynasty_genius.catchup_guard import (
    JobSpec,
    ReceiptSpec,
    plan_kicks,
    read_receipt_ts,
)
from src.dynasty_genius.launchd_schedules import Slot
from tests.contract.test_pvo_refresh_runner import (
    _fixture_feature_source,
    _fixture_reader,
    _write_pair,
)

_REFUSAL_REASON = "required_provenance_missing:te_v3_metadata.json"


def _load_runner():
    return importlib.import_module("scripts.run_pvo_refresh")


def _fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
    Path(pvo_artifact_path).write_text(
        json.dumps({"players": [{"valuation": {"dynasty_value_score": 99.1}}]})
    )
    Path(coverage_artifact_path).write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))


def _refusing_capture(**_kwargs) -> dict:
    """The driver's ``abort()`` shape, verbatim — returned, never raised."""
    return {
        "status": "aborted",
        "capture_date": "2026-08-31",
        "aborted_reason": _REFUSAL_REASON,
        "decision_supported": False,
    }


def _ok_capture(**_kwargs) -> dict:
    return {"status": "ok", "capture_date": "2026-09-02", "raw_rows": 1, "aborted_reason": None}


def _publish(runner, tmp_path: Path, *, capture_fn) -> tuple[dict, Path, Path]:
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    report_path = tmp_path / "reports" / "refresh.json"
    report = runner.run_pvo_refresh(
        pvo_artifact_path=tmp_path / "unused_candidate.json",
        coverage_artifact_path=tmp_path / "unused_candidate_coverage.json",
        runtime_dir=runtime_dir,
        report_path=report_path,
        refresh_fn=_fake_refresh,
        capture_fn=capture_fn,
        capture_db_path=tmp_path / "model_forward.db",
        capture_report_path=tmp_path / "model_capture" / "latest.json",
    )
    return report, runtime_dir, report_path


def test_returned_capture_refusal_is_a_capture_stage_abort_that_keeps_the_new_pair(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    report, runtime_dir, report_path = _publish(
        runner, tmp_path, capture_fn=_refusing_capture
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "capture"
    assert report["aborted_reason"] == _REFUSAL_REASON
    assert report["restored_from_backup"] is False
    assert report["decision_supported"] is False
    # The driver's own report survives untouched for the readers that want the detail.
    assert report["capture_report"]["status"] == "aborted"
    assert report["capture_report"]["aborted_reason"] == _REFUSAL_REASON
    # The refresh succeeded: the runtime block is still reported and the pair on disk
    # is this run's bytes, marker included — a capture refusal never rolls back serving.
    runtime_pvo = runtime_dir / "universe_pvo_runtime.json"
    assert report["runtime"]["pvo_path"] == str(runtime_pvo)
    assert "99.1" in runtime_pvo.read_text()
    assert json.loads((runtime_dir / "universe_pvo_coverage_runtime.json").read_text()) == {
        "raw_rows": 1,
        "suffix": "new",
    }
    marker = json.loads((runtime_dir / "universe_pvo_runtime.ready.json").read_text())
    assert marker["status"] == "ok"
    assert marker["pvo_sha256"] == report["runtime"]["pvo_sha256"]
    # The receipt on disk is the abort report, byte-for-byte what was returned.
    assert json.loads(report_path.read_text()) == report


def test_ok_capture_path_is_unchanged(tmp_path: Path) -> None:
    runner = _load_runner()
    report, _runtime_dir, report_path = _publish(runner, tmp_path, capture_fn=_ok_capture)

    assert report["status"] == "ok"
    assert "aborted_stage" not in report
    assert report["capture_report"]["status"] == "ok"
    assert json.loads(report_path.read_text()) == report


def test_a_capture_report_without_an_ok_status_is_never_read_as_ok(tmp_path: Path) -> None:
    """Fail closed, like the health card on the same field: the driver always writes
    ``status``, so a report that lacks it -- or is not a report at all -- is a broken
    contract, not a success. Only a literal ``"ok"`` clears the stage."""
    runner = _load_runner()

    report, _runtime_dir, _report_path = _publish(
        runner, tmp_path, capture_fn=lambda **_k: {"raw_rows": 3}
    )
    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "capture"
    assert report["aborted_reason"] == "capture_report_missing_status"

    report, _runtime_dir, _report_path = _publish(runner, tmp_path, capture_fn=lambda **_k: None)
    assert report["status"] == "aborted"
    assert report["aborted_reason"] == "capture_report_malformed:NoneType"


def test_main_exits_1_when_the_capture_refuses(tmp_path: Path, monkeypatch) -> None:
    """The exit code is what the chain and the launchd label read. It must go red."""
    runner = _load_runner()
    runtime_dir = tmp_path / "rt"
    report_path = tmp_path / "reports" / "refresh.json"
    monkeypatch.setattr(runner, "ROOT", tmp_path)  # no publish-in-flight lock here
    monkeypatch.setattr(runner, "_phase17_2_refresh", _fake_refresh)
    monkeypatch.setattr(runner, "capture_model_pvo_snapshot", _refusing_capture)

    rc = runner.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--report-path",
            str(report_path),
            "--capture-db-path",
            str(tmp_path / "model_forward.db"),
            "--capture-report-path",
            str(tmp_path / "model_capture" / "latest.json"),
        ]
    )

    assert rc == 1
    report = json.loads(report_path.read_text())
    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "capture"
    # Red exit, published pair: the serving state is this run's, not a rollback.
    assert "99.1" in (runtime_dir / "universe_pvo_runtime.json").read_text()


def test_legacy_in_place_path_flips_the_same_way(tmp_path: Path) -> None:
    """The back-compat in-place refresh has the same returned-refusal hole; it gets the
    same contract, with its own report shape (refresh metadata preserved)."""
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    report_path = tmp_path / "reports" / "refresh.json"

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text(pvo_artifact_path.read_text().replace("98.5", "99.1"))
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=report_path,
        refresh_fn=refresh_fn,
        capture_fn=_refusing_capture,
        capture_db_path=tmp_path / "model_forward.db",
        capture_report_path=tmp_path / "model_capture" / "latest.json",
        read_artifact=_fixture_reader(pvo, coverage),
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "capture"
    assert report["aborted_reason"] == _REFUSAL_REASON
    assert report["restored_from_backup"] is False
    assert report["capture_report"]["status"] == "aborted"
    assert report["semantic_changed"] is True
    assert set(report["dirty_paths"]) == {str(pvo), str(coverage)}
    assert "99.1" in pvo.read_text()  # not restored
    assert json.loads(report_path.read_text()) == report


def test_the_catchup_guard_counts_a_red_refresh_as_attempted(tmp_path: Path) -> None:
    """The guard keys on the receipt, never the exit code: a refusal that wrote its
    receipt is a run that happened, so the guard must not re-kick it every tick.
    pvo_refresh declares no timestamp field (``catchup_guard.json``), so the receipt's
    mtime is the clock -- pin the mtime to just after the 14:00 slot and ask the
    guard's own planner what it would do at 14:15: nothing."""
    runner = _load_runner()
    _report, _runtime_dir, report_path = _publish(
        runner, tmp_path, capture_fn=_refusing_capture
    )
    tz = ZoneInfo("America/New_York")
    fired_at = datetime(2026, 9, 3, 14, 0, 5, tzinfo=tz)
    os.utime(report_path, (fired_at.timestamp(), fired_at.timestamp()))
    label = "com.davidleess.dynasty-model-pvo-refresh"
    spec = JobSpec(
        label=label,
        slots=(Slot(11, 30), Slot(14, 0)),  # the live plist's StartCalendarInterval
        receipt=ReceiptSpec(receipt_path=str(report_path), timestamp_fields=()),
    )

    receipt_ts = read_receipt_ts(report_path, spec.receipt.timestamp_fields, tz=tz)
    assert receipt_ts is not None
    kicks = plan_kicks(
        now=fired_at + timedelta(minutes=15),
        specs=[spec],
        receipt_ts={label: receipt_ts},
        running=set(),
        already_kicked=set(),
    )
    assert kicks == []
    # The same planner DOES kick when the receipt is missing -- the red receipt is what
    # stands between a refusal and a re-kick loop, so the assertion above is load-bearing.
    without_receipt = plan_kicks(
        now=fired_at + timedelta(minutes=15),
        specs=[spec],
        receipt_ts={label: None},
        running=set(),
        already_kicked=set(),
    )
    assert datetime(2026, 9, 3, 14, 0, tzinfo=tz) in [k.occurrence for k in without_receipt]


def test_a_red_refresh_marks_its_step_and_does_not_skip_the_pair_consumers() -> None:
    """Mark red, never amplify: the pair is still published, so the steps that read
    it (market-divergence, what-changed) must not declare pvo_refresh a hard upstream."""
    chain = importlib.import_module("scripts.run_daily_chain")
    steps = chain.build_steps(Path("/repo"))
    names = [s.name for s in steps]
    assert "run_pvo_refresh" in names
    dependants = [s.name for s in steps if "run_pvo_refresh" in s.hard_upstreams]
    assert dependants == []
