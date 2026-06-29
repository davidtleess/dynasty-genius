"""T4 RED: read-only roster capacity audit producer.

The producer is a scheduler-safe wrapper over the pure T1-T3 simulator. It
reads injected PVO/snapshot artifacts, writes only the gitignored latest
scorecard artifact on success, never invokes git, and keeps producer metadata
out of the deterministic core model.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_cli():
    return importlib.import_module("scripts.run_roster_capacity_audit")


def _snapshot(
    player_ids: list[str],
    *,
    snapshot_player_ids: list[str] | None = None,
    active_slots: int = 1,
    captured_at: str = "2026-06-28T12:00:00+00:00",
) -> dict[str, Any]:
    return {
        "captured_at": captured_at,
        "league": {
            "roster_positions": ["QB"] * active_slots,
            "settings": {
                "reserve_slots": 0,
                "taxi_slots": 0,
                "taxi_years": 2,
                "taxi_allow_vets": 0,
            },
        },
        "rosters": [
            {
                "roster_id": 1,
                "owner_id": "david",
                "players": player_ids,
                "starters": player_ids[:active_slots],
                "reserve": [],
                "taxi": [],
            }
        ],
        "players": [
            {
                "sleeper_player_id": pid,
                "player": {"position": "WR"},
                "league_context": {
                    "rostered": pid in set(player_ids),
                    "roster_id": 1 if pid in set(player_ids) else None,
                    "on_ir": False,
                    "on_taxi": False,
                },
            }
            for pid in (
                snapshot_player_ids if snapshot_player_ids is not None else player_ids
            )
        ],
    }


def _pvo_player(
    pid: str,
    *,
    xvar: float = 10.0,
    xvar_pct: float = 50.0,
) -> dict[str, Any]:
    return {
        "sleeper_player_id": pid,
        "player": {
            "full_name": f"Player {pid}",
            "position": "WR",
            "age": 24.0,
            "years_exp": 2,
            "sleeper_status": "active",
        },
        "valuation": {
            "engine_path": "ENGINE_B",
            "xvar": xvar,
            "dynasty_value_score": 60.0,
            "xvar_percentile_overall": xvar_pct,
        },
        "projection_2y": 11.5,
        "decision_supported": False,
    }


def _pvo(players: list[dict[str, Any]]) -> dict[str, Any]:
    return {"players": players, "decision_supported": False}


def _ok_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    rostered = ["cut1", "cut2"]
    waiver = [f"wr{i}" for i in range(1, 9)]
    pvo = _pvo(
        [
            _pvo_player("cut1", xvar=10.0, xvar_pct=1.0),
            _pvo_player("cut2", xvar=9.0, xvar_pct=2.0),
            *[_pvo_player(pid, xvar=float(i), xvar_pct=50.0) for i, pid in enumerate(waiver, 1)],
        ]
    )
    snapshot = _snapshot(
        rostered,
        snapshot_player_ids=[*rostered, *waiver],
        captured_at="2026-06-28T12:00:00+00:00",
    )
    return pvo, snapshot


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            if isinstance(key, str):
                out.append(key)
            out.extend(_strings(item))
        return out
    if isinstance(value, list | tuple):
        out: list[str] = []
        for item in value:
            out.extend(_strings(item))
        return out
    return [value] if isinstance(value, str) else []


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def test_producer_report_model_separates_preflight_from_core_status() -> None:
    from src.dynasty_genius.roster_capacity.models import ProducerReport

    report = ProducerReport(producer_status="preflight_ready", scorecard=None)

    assert report.producer_status == "preflight_ready"
    assert report.scorecard is None
    assert report.decision_supported is False
    assert report.model_dump() == {
        "producer_status": "preflight_ready",
        "scorecard": None,
        "decision_supported": False,
    }


def test_preflight_prints_ready_report_without_loading_scoring_or_writing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()
    report_path = tmp_path / "app" / "data" / "roster_capacity" / "roster_capacity_latest.json"

    def fail_loader(*_args, **_kwargs):
        raise AssertionError("preflight must not load, score, or write")

    monkeypatch.setattr(cli, "_load_universe_pvo", fail_loader)
    monkeypatch.setattr(cli, "_load_sleeper_snapshot", fail_loader)

    result = cli.main(["--report-path", str(report_path), "--preflight"])

    assert result == 0
    body = json.loads(capsys.readouterr().out)
    assert body == {
        "producer_status": "preflight_ready",
        "scorecard": None,
        "decision_supported": False,
    }
    assert not report_path.exists()


def test_ok_run_writes_only_gitignored_artifact_with_producer_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cli = _load_cli()
    pvo, snapshot = _ok_inputs()
    report_path = tmp_path / "app" / "data" / "roster_capacity" / "roster_capacity_latest.json"

    def forbid_git(*_args, **_kwargs):
        raise AssertionError("roster capacity producer must never invoke git")

    monkeypatch.setattr(cli.subprocess, "run", forbid_git)

    report = cli.run_audit(
        report_path=report_path,
        universe_pvo_loader=lambda: pvo,
        sleeper_snapshot_loader=lambda: snapshot,
        now_fn=lambda: "2026-06-28T16:00:00+00:00",
    )

    assert report["producer_status"] == "ok"
    assert report["decision_supported"] is False
    assert report["scorecard"]["status"] == "ok"
    assert report_path.exists()
    assert sorted(
        p.relative_to(tmp_path).as_posix()
        for p in tmp_path.rglob("*")
        if p.is_file()
    ) == ["app/data/roster_capacity/roster_capacity_latest.json"]

    artifact = json.loads(report_path.read_text())
    assert artifact["status"] == "ok"
    assert artifact["decision_supported"] is False
    assert artifact["created_at"] == "2026-06-28T16:00:00+00:00"
    assert artifact["sleeper_snapshot_captured_at"] == "2026-06-28T12:00:00+00:00"
    assert "producer_status" not in artifact
    assert "scorecard" not in artifact
    assert _decision_supported_true_count(artifact) == 0


def test_blocked_run_prints_nonzero_and_does_not_overwrite_prior_latest(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()
    _pvo_ok, snapshot = _ok_inputs()
    report_path = tmp_path / "app" / "data" / "roster_capacity" / "roster_capacity_latest.json"
    report_path.parent.mkdir(parents=True)
    prior = {"status": "prior_good", "decision_supported": False}
    report_path.write_text(json.dumps(prior, sort_keys=True))

    monkeypatch.setattr(cli, "_load_universe_pvo", lambda: {"not_players": []})
    monkeypatch.setattr(cli, "_load_sleeper_snapshot", lambda: snapshot)
    monkeypatch.setattr(cli, "_now", lambda: "2026-06-28T16:00:00+00:00")

    result = cli.main(["--report-path", str(report_path)])

    assert result == 1
    body = json.loads(capsys.readouterr().out)
    assert body["producer_status"] == "blocked"
    assert body["scorecard"]["status"] == "blocked"
    assert body["decision_supported"] is False
    assert json.loads(report_path.read_text()) == prior


def test_main_prints_descriptive_stdout_and_exit_codes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()
    pvo, snapshot = _ok_inputs()
    report_path = tmp_path / "roster_capacity_latest.json"

    monkeypatch.setattr(cli, "_load_universe_pvo", lambda: pvo)
    monkeypatch.setattr(cli, "_load_sleeper_snapshot", lambda: snapshot)
    monkeypatch.setattr(cli, "_now", lambda: "2026-06-28T16:00:00+00:00")

    result = cli.main(["--report-path", str(report_path)])

    assert result == 0
    body = json.loads(capsys.readouterr().out)
    assert body["producer_status"] == "ok"
    assert body["scorecard"]["capacity_health"]["total_capacity_cuts_required"] == 1
    assert body["scorecard"]["capacity_health"]["active_slot_overflow"] == 1

    banned_phrases = [
        "must cut",
        "do not cut",
        "safe cut",
        "recommended",
        "recommendation",
        "verdict",
        "buy",
        "sell",
        "hold",
    ]
    stdout_values = " ".join(_strings(body)).lower()
    artifact_values = " ".join(_strings(json.loads(report_path.read_text()))).lower()
    for phrase in banned_phrases:
        assert phrase not in stdout_values
        assert phrase not in artifact_values


def test_missing_snapshot_blocks_without_partial_artifact(tmp_path: Path) -> None:
    cli = _load_cli()
    pvo, _snapshot_ok = _ok_inputs()
    report_path = tmp_path / "roster_capacity_latest.json"

    report = cli.run_audit(
        report_path=report_path,
        universe_pvo_loader=lambda: pvo,
        sleeper_snapshot_loader=lambda: {"not_rosters": []},
        now_fn=lambda: "2026-06-28T16:00:00+00:00",
    )

    assert report["producer_status"] == "blocked"
    assert report["scorecard"]["status"] == "blocked"
    assert report["decision_supported"] is False
    assert not report_path.exists()


def test_standalone_execution_imports_without_module_not_found(tmp_path: Path) -> None:
    script_path = Path("scripts/run_roster_capacity_audit.py").resolve()
    probe = "\n".join(
        [
            "import importlib.util",
            "import os",
            "import pathlib",
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"os.chdir({str(tmp_path)!r})",
            "spec = importlib.util.spec_from_file_location(",
            "    'run_roster_capacity_audit_standalone', script_path",
            ")",
            "module = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(module)",
            "assert callable(module.main)",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_roster_capacity_artifact_path_is_gitignored() -> None:
    gitignore = Path(".gitignore").read_text()

    assert "app/data/roster_capacity/" in gitignore
