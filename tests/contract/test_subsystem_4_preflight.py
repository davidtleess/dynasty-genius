"""Subsystem 4 Backtest-A input-readiness preflight contract tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import get_args, get_origin

import pytest
from pydantic import BaseModel

from src.dynasty_genius.eval import backtest_mock_draft as bmd

UUID_A = "cpr_13000000-0000-4000-8000-000000000001"
UUID_B = "cpr_13000000-0000-4000-8000-000000000002"
UUID_C = "cpr_13000000-0000-4000-8000-000000000003"
UUID_D = "cpr_13000000-0000-4000-8000-000000000004"


def _registry_entry(
    *,
    uuid: str,
    name: str,
    position: str = "WR",
    draft_class: int = 2025,
    verification_status: str = "confirmed",
) -> dict:
    return {
        "raw_name": name,
        "normalized_name": name.lower(),
        "full_name": name,
        "position": position,
        "position_group": position,
        "draft_class": draft_class,
        "current_school": "Test U",
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "test_fixture",
        "source_record_id": uuid,
        "source_snapshot_id": "preflight_registry",
        "id_provenance": {},
        "notes": None,
        "prospect_uuid": uuid,
        "verification_status": verification_status,
        "match_key": f"preflight|{uuid}",
        "status_history": [
            {
                "event_id": f"confirm-{uuid[-1]}",
                "decision": "confirm",
                "after_status": verification_status,
                "decided_at": "2026-01-01T00:00:00Z",
                "reviewer_id": "codex",
            }
        ],
        "merged_into_prospect_uuid": None,
        "reviewer_id": "codex",
        "reviewer_metadata": {},
    }


def _bridge_entry(
    uuid: str,
    *,
    draft_year: int = 2025,
    gsis_id: str | None = None,
    pick_no: int = 40,
) -> dict:
    return {
        "prospect_uuid": uuid,
        "gsis_id": gsis_id or f"00-{uuid[-4:]}",
        "pfr_id": None,
        "draft_year": draft_year,
        "draft_pick_no": pick_no,
        "draft_round": 1 if pick_no <= 32 else 2,
        "nfl_team": "TEN",
        "udfa": False,
        "nflreadr_source": "test",
        "nflreadr_season": draft_year,
        "draft_truth_content_hash": f"hash-{uuid[-4:]}",
        "nflreadr_fetched_at": "2026-01-01T00:00:00Z",
        "evidence_snapshot": {
            "full_name": f"Prospect {uuid[-4:]}",
            "position": "WR",
            "college": "Test U",
        },
        "event_id": f"event-{uuid[-4:]}",
        "decided_at": "2026-01-01T00:00:00Z",
        "reviewer_id": "codex",
        "decision": "confirm",
        "note": None,
    }


def _snapshot_payload(
    *,
    draft_year: int | None = 2025,
    parse_status: str = "complete",
) -> dict:
    metadata = {
        "source_url": "https://example.test/preflight",
        "source_label": "preflight_source",
        "analyst": "Preflight Analyst",
        "mock_version": "v1",
        "published_date": "2025-04-01",
        "fetched_at": "2025-04-20T00:00:00Z",
        "content_hash": "preflight-content",
        "parser_version": "preflight_parser",
        "parse_status": parse_status,
    }
    if draft_year is not None:
        metadata["draft_year"] = draft_year
    return {
        "metadata": metadata,
        "picks": [
            {"pick_no": 1, "prospect_uuid": UUID_A},
            {"pick_no": 48, "prospect_uuid": UUID_B},
        ],
    }


def _write_snapshot(
    snapshots_dir: Path,
    payload: dict,
    *,
    name: str = "snapshot.json",
) -> Path:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = snapshots_dir / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_registry(identity_dir: Path, *entries: dict) -> Path:
    identity_dir.mkdir(parents=True, exist_ok=True)
    path = identity_dir / "college_prospect_registry.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {"schema_version": "preflight_registry"},
                "entries": list(entries),
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_bridge(
    identity_dir: Path,
    *entries: dict,
    draft_year: int = 2025,
) -> Path:
    identity_dir.mkdir(parents=True, exist_ok=True)
    path = identity_dir / "prospect_nfl_bridge.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "draft_year": draft_year,
                    "schema_version": "prospect_nfl_bridge_v1.0.0",
                },
                "entries": list(entries),
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_ready_inputs(tmp_path: Path) -> tuple[Path, Path]:
    snapshots_dir = tmp_path / "snapshots"
    identity_dir = tmp_path / "identity"
    _write_snapshot(snapshots_dir, _snapshot_payload())
    _write_registry(
        identity_dir,
        _registry_entry(uuid=UUID_A, name="Preflight Quarterback", position="QB"),
        _registry_entry(uuid=UUID_B, name="Preflight Receiver", position="WR"),
    )
    _write_bridge(
        identity_dir,
        _bridge_entry(UUID_A, gsis_id="00-preflight-a", pick_no=1),
        _bridge_entry(UUID_B, gsis_id="00-preflight-b", pick_no=40),
    )
    return snapshots_dir, identity_dir


def _check(report, name: str):
    matches = [check for check in report.checks if check.name == name]
    assert len(matches) == 1
    return matches[0]


def _snapshot_tree(root: Path) -> set[tuple[str, str]]:
    if not root.exists():
        return set()
    return {
        (str(path.relative_to(root)), path.read_text(encoding="utf-8"))
        for path in root.rglob("*")
        if path.is_file()
    }


def _preflight_cli_module():
    path = Path("scripts/preflight_backtest_a.py")
    spec = importlib.util.spec_from_file_location("preflight_backtest_a_cli", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_report_model_contract():
    report_cls = bmd.BacktestAPreflightReport
    check_cls = bmd.BacktestAPreflightCheck

    assert issubclass(check_cls, BaseModel)
    assert check_cls.model_config.get("extra") == "forbid"
    assert check_cls.model_fields["name"].annotation is str
    assert get_origin(check_cls.model_fields["status"].annotation).__name__ == "Literal"
    assert set(get_args(check_cls.model_fields["status"].annotation)) == {
        "ok",
        "blocked",
        "not_checked",
    }
    assert check_cls.model_fields["detail"].annotation is str

    assert issubclass(report_cls, BaseModel)
    assert report_cls.model_config.get("extra") == "forbid"
    assert set(report_cls.model_fields) == {
        "ready",
        "checks",
        "blocking_reasons",
        "confirmed_class_unbridged_count",
        "confirmed_class_unbridged_uuids",
        "orphan_bridges_detected",
        "ingest_summary",
    }
    assert "decision_supported" not in report_cls.model_fields
    assert "verdict" not in report_cls.model_fields
    assert "pass" not in report_cls.model_fields
    assert report_cls.model_fields["ready"].annotation is bool
    assert get_origin(report_cls.model_fields["checks"].annotation) is list
    assert get_args(report_cls.model_fields["checks"].annotation) == (check_cls,)
    assert report_cls.model_fields["blocking_reasons"].annotation == list[str]
    assert report_cls.model_fields["confirmed_class_unbridged_count"].annotation is int
    assert report_cls.model_fields["confirmed_class_unbridged_uuids"].annotation == (
        list[str]
    )
    assert get_origin(report_cls.model_fields["orphan_bridges_detected"].annotation) is list
    assert report_cls.model_fields["ingest_summary"].annotation is dict


def test_preflight_ready_inputs_report_static_readiness_and_not_checked_limits(
    tmp_path: Path,
):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is True
    assert report.blocking_reasons == []
    assert _check(report, "presence").status == "ok"
    assert _check(report, "ingest").status == "ok"
    assert _check(report, "alignment").status == "ok"
    assert _check(report, "static_coverage").status == "ok"
    assert _check(report, "output_collision").status == "not_checked"
    assert _check(report, "live_truth_source").status == "not_checked"
    assert report.ingest_summary == {
        "snapshot_files": 1,
        "schema_invalid": 0,
        "normalized_picks": 2,
        "draft_date_resolved": True,
    }
    assert report.confirmed_class_unbridged_count == 0
    assert report.confirmed_class_unbridged_uuids == []
    assert report.orphan_bridges_detected == []
    assert all(check.status != "blocked" for check in report.checks)


@pytest.mark.parametrize(
    "missing_target",
    ["snapshots_dir", "bridge", "registry"],
)
def test_preflight_blocks_missing_required_inputs(
    tmp_path: Path,
    missing_target: str,
):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    if missing_target == "snapshots_dir":
        snapshots_dir = tmp_path / "missing_snapshots"
    elif missing_target == "bridge":
        (identity_dir / "prospect_nfl_bridge.json").unlink()
    else:
        (identity_dir / "college_prospect_registry.json").unlink()

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "presence").status == "blocked"
    assert any(missing_target in reason for reason in report.blocking_reasons)


@pytest.mark.parametrize(
    ("zero_byte_target", "relative_path"),
    [
        ("bridge", "prospect_nfl_bridge.json"),
        ("registry", "college_prospect_registry.json"),
    ],
)
def test_preflight_blocks_zero_byte_identity_inputs(
    tmp_path: Path,
    zero_byte_target: str,
    relative_path: str,
):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    (identity_dir / relative_path).write_text("", encoding="utf-8")

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "presence").status == "blocked"
    assert any(zero_byte_target in reason for reason in report.blocking_reasons)


def test_preflight_blocks_when_snapshots_are_schema_invalid(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_snapshot(snapshots_dir, {"not": "a snapshot"})

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "ingest").status == "blocked"
    assert report.ingest_summary["snapshot_files"] == 1
    assert report.ingest_summary["schema_invalid"] == 1
    assert report.ingest_summary["normalized_picks"] == 0
    assert any("zero_usable_picks" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_no_draft_date_sentinel_without_override(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_snapshot(snapshots_dir, _snapshot_payload(draft_year=None))

    report = bmd.preflight_backtest_a_inputs(snapshots_dir, identity_dir, 2025)

    assert report.ready is False
    assert _check(report, "ingest").status == "blocked"
    assert report.ingest_summary["draft_date_resolved"] is False
    assert any("draft_date_unresolved" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_bridge_year_mismatch(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_bridge(
        identity_dir,
        _bridge_entry(UUID_A, draft_year=2024),
        _bridge_entry(UUID_B, draft_year=2024),
        draft_year=2024,
    )

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "alignment").status == "blocked"
    assert any("bridge_draft_year_mismatch" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_when_registry_has_no_confirmed_entries_for_draft_year(
    tmp_path: Path,
):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_registry(
        identity_dir,
        _registry_entry(
            uuid=UUID_A,
            name="Unconfirmed Prospect",
            verification_status="provisional",
        ),
    )

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "alignment").status == "blocked"
    assert any("no_confirmed_registry_entries" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_confirmed_class_unbridged_uuid(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_registry(
        identity_dir,
        _registry_entry(uuid=UUID_A, name="Preflight Quarterback", position="QB"),
        _registry_entry(uuid=UUID_B, name="Preflight Receiver", position="WR"),
        _registry_entry(uuid=UUID_C, name="Unbridged Confirmed", position="RB"),
    )

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "static_coverage").status == "blocked"
    assert report.confirmed_class_unbridged_count == 1
    assert report.confirmed_class_unbridged_uuids == [UUID_C]
    assert any("confirmed_class_unbridged" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_orphan_bridge_reason(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    _write_bridge(
        identity_dir,
        _bridge_entry(UUID_A, gsis_id="00-preflight-a", pick_no=1),
        _bridge_entry(UUID_B, gsis_id="00-preflight-b", pick_no=40),
        _bridge_entry(UUID_D),
    )

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
    )

    assert report.ready is False
    assert _check(report, "static_coverage").status == "blocked"
    assert {"prospect_uuid": UUID_D, "reason": "not_in_registry"} in (
        report.orphan_bridges_detected
    )
    assert any("orphan_bridges_detected" in reason for reason in report.blocking_reasons)


def test_preflight_blocks_output_collision_when_run_target_exists(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    output_root = tmp_path / "runs"
    artifact_path = output_root / "existing_run" / "backtest_a_result.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{}", encoding="utf-8")

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
        run_id="existing_run",
        output_root=output_root,
    )

    assert report.ready is False
    assert _check(report, "output_collision").status == "blocked"
    assert any("output_collision" in reason for reason in report.blocking_reasons)


def test_preflight_is_read_only(tmp_path: Path):
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    output_root = tmp_path / "runs"
    before = {
        "snapshots": _snapshot_tree(snapshots_dir),
        "identity": _snapshot_tree(identity_dir),
        "output": _snapshot_tree(output_root),
    }

    report = bmd.preflight_backtest_a_inputs(
        snapshots_dir,
        identity_dir,
        2025,
        override_draft_date="2025-04-24",
        run_id="read_only",
        output_root=output_root,
    )

    after = {
        "snapshots": _snapshot_tree(snapshots_dir),
        "identity": _snapshot_tree(identity_dir),
        "output": _snapshot_tree(output_root),
    }
    assert before == after
    assert report.ready is True


def test_preflight_cli_prints_descriptive_report_and_exits_zero_when_ready(
    tmp_path: Path,
    capsys,
):
    cli = _preflight_cli_module()
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)

    exit_code = cli.main([
        "--snapshots-dir",
        str(snapshots_dir),
        "--identity-dir",
        str(identity_dir),
        "--draft-year",
        "2025",
        "--override-draft-date",
        "2025-04-24",
    ])

    stdout = capsys.readouterr().out
    assert exit_code == 0
    assert "DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim." in stdout
    assert (
        "Preflight checks INPUT READINESS only (file presence, schema validation, "
        "and selection-bias gate prerequisites). It does NOT validate model "
        "predictions, market divergence, or represent decision-grade clearance."
    ) in stdout
    assert "checks" in stdout
    assert "presence" in stdout
    assert "ok" in stdout
    assert "blocking_reasons" in stdout
    assert "confirmed_class_unbridged_count" in stdout
    assert "confirmed_class_unbridged_uuids" in stdout
    assert "orphan_bridges_detected" in stdout
    assert "ingest_summary" in stdout
    assert "normalized_picks" in stdout
    assert "live_truth_source" in stdout
    assert "not_checked" in stdout


def test_preflight_cli_exits_nonzero_and_prints_blocked_report(
    tmp_path: Path,
    capsys,
):
    cli = _preflight_cli_module()
    snapshots_dir, identity_dir = _write_ready_inputs(tmp_path)
    missing_snapshots = snapshots_dir.parent / "missing_snapshots"

    exit_code = cli.main([
        "--snapshots-dir",
        str(missing_snapshots),
        "--identity-dir",
        str(identity_dir),
        "--draft-year",
        "2025",
        "--override-draft-date",
        "2025-04-24",
    ])

    stdout = capsys.readouterr().out
    assert exit_code != 0
    assert "DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim." in stdout
    assert "blocked" in stdout
    assert "blocking_reasons" in stdout
    assert "snapshots_dir_missing_or_empty" in stdout


def test_preflight_cli_passes_include_untrusted_flag(monkeypatch, tmp_path: Path):
    cli = _preflight_cli_module()
    captured = {}

    def fake_preflight(
        snapshots_dir,
        identity_dir,
        draft_year,
        *,
        override_draft_date=None,
        include_untrusted=False,
        run_id=None,
        output_root=None,
    ):
        captured.update(
            {
                "snapshots_dir": Path(snapshots_dir),
                "identity_dir": Path(identity_dir),
                "draft_year": draft_year,
                "override_draft_date": override_draft_date,
                "include_untrusted": include_untrusted,
                "run_id": run_id,
                "output_root": Path(output_root),
            }
        )
        return bmd.BacktestAPreflightReport(
            ready=True,
            checks=[
                bmd.BacktestAPreflightCheck(
                    name="presence",
                    status="ok",
                    detail="captured",
                )
            ],
            blocking_reasons=[],
            confirmed_class_unbridged_count=0,
            confirmed_class_unbridged_uuids=[],
            orphan_bridges_detected=[],
            ingest_summary={
                "snapshot_files": 1,
                "schema_invalid": 0,
                "normalized_picks": 1,
                "draft_date_resolved": True,
            },
        )

    monkeypatch.setattr(cli, "preflight_backtest_a_inputs", fake_preflight)
    snapshots_dir = tmp_path / "snapshots"
    identity_dir = tmp_path / "identity"
    output_root = tmp_path / "runs"

    assert cli.main([
        "--snapshots-dir",
        str(snapshots_dir),
        "--identity-dir",
        str(identity_dir),
        "--draft-year",
        "2025",
        "--override-draft-date",
        "2025-04-24",
        "--include-untrusted",
        "--run-id",
        "preflight_cli",
        "--output-root",
        str(output_root),
    ]) == 0

    assert captured == {
        "snapshots_dir": snapshots_dir,
        "identity_dir": identity_dir,
        "draft_year": 2025,
        "override_draft_date": "2025-04-24",
        "include_untrusted": True,
        "run_id": "preflight_cli",
        "output_root": output_root,
    }
