"""War Room #2 operational-refresh T1 RED: report CLI + gitignore.

The CLI is a thin scheduler-safe wrapper over the shipped T2 emitter. It must be
read-only over every input and write only the gitignored overwrite-latest report.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_RELATIVE = Path("app/data/what_changed/what_changed_latest_report.json")
INPUT_RELATIVES = {
    "fc_db_path": Path("app/data/fc_forward_capture.db"),
    "model_db_path": Path("app/data/model_forward_capture.db"),
    "sleeper_snapshot_path": Path(
        "app/data/league_snapshots/sleeper_universe_snapshot_latest.json"
    ),
    "team_posture_path": Path("app/data/valuation/team_posture_latest.json"),
    "team_value_matrix_path": Path("app/data/valuation/team_value_matrix_latest.json"),
    "league_opportunity_path": Path("app/data/valuation/league_opportunity_latest.json"),
    "roster_cut_report_path": Path("app/data/valuation/roster_cut_report_latest.json"),
}


def _cli_module():
    return importlib.import_module("scripts.run_what_changed_report")


def _write_input(root: Path, relative: Path, content: bytes = b"input") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _write_inputs(root: Path, keys: set[str] | None = None) -> dict[Path, bytes]:
    keys = keys or set(INPUT_RELATIVES)
    before: dict[Path, bytes] = {}
    for key in keys:
        content = f"{key}:original".encode()
        path = _write_input(root, INPUT_RELATIVES[key], content)
        before[path] = content
    return before


def _patch_root(monkeypatch: pytest.MonkeyPatch, module: Any, root: Path) -> None:
    monkeypatch.setattr(module, "ROOT", root)


def test_what_changed_report_path_is_gitignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", str(REPORT_RELATIVE)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert str(REPORT_RELATIVE) in result.stdout


def test_cli_preflight_is_readiness_only_partial_inputs_are_ok(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    _write_inputs(tmp_path, {"sleeper_snapshot_path"})

    def emitter_must_not_run(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("--preflight must not call the report emitter")

    monkeypatch.setattr(module, "emit_daily_what_changed_report", emitter_must_not_run)

    rc = module.main(["--preflight"])

    assert rc == 0
    assert not (tmp_path / REPORT_RELATIVE).exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["preflight"] is True
    assert payload["ready"] is True
    assert payload["report_path"] == str(tmp_path / REPORT_RELATIVE)
    assert payload["inputs"]["sleeper_snapshot_path"]["exists"] is True
    assert payload["inputs"]["fc_db_path"]["exists"] is False
    assert "no_usable_inputs" not in payload["readiness_failures"]


def test_cli_preflight_fails_only_when_no_inputs_are_usable(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    monkeypatch.setattr(
        module,
        "emit_daily_what_changed_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("--preflight must not call the report emitter")
        ),
    )

    rc = module.main(["--preflight"])

    assert rc == 1
    assert not (tmp_path / REPORT_RELATIVE).exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is False
    assert "no_usable_inputs" in payload["readiness_failures"]


def test_cli_preflight_fails_when_report_parent_is_not_a_directory(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    _write_inputs(tmp_path, {"sleeper_snapshot_path"})
    blocker = tmp_path / REPORT_RELATIVE.parent
    blocker.parent.mkdir(parents=True, exist_ok=True)
    blocker.write_text("not a directory")

    rc = module.main(["--preflight"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is False
    assert "report_parent_unusable" in payload["readiness_failures"]


def test_cli_run_resolves_prod_paths_injects_clock_and_exits_zero_for_degraded_report(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    _write_inputs(tmp_path)
    calls: list[dict[str, Any]] = []

    def fake_emit_daily_what_changed_report(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        report = {
            "schema_version": "war_room_2_what_changed_v1",
            "generated_at": kwargs["now_fn"]().isoformat(),
            "decision_supported": False,
            "overall_status": "degraded",
            "daily_diff": {
                "market": {"status": "ok"},
                "model": {"status": "insufficient_history"},
            },
            "structural_context": {"status": "degraded"},
        }
        Path(kwargs["report_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["report_path"]).write_text(json.dumps(report, sort_keys=True))
        return report

    monkeypatch.setattr(module, "emit_daily_what_changed_report", fake_emit_daily_what_changed_report)

    rc = module.main([])

    assert rc == 0
    assert len(calls) == 1
    kwargs = calls[0]
    for key, relative in INPUT_RELATIVES.items():
        assert kwargs[key] == tmp_path / relative
    assert kwargs["report_path"] == tmp_path / REPORT_RELATIVE
    assert kwargs["top_n"] == 25
    assert kwargs["now_fn"]().tzinfo is not None
    written = json.loads((tmp_path / REPORT_RELATIVE).read_text())
    assert written["overall_status"] == "degraded"
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "overall_status": "degraded",
        "market_status": "ok",
        "model_status": "insufficient_history",
        "structural_status": "degraded",
        "report_path": str(tmp_path / REPORT_RELATIVE),
    }


def test_cli_run_is_read_only_over_inputs_and_writes_only_report(
    tmp_path,
    monkeypatch,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    before = _write_inputs(tmp_path)
    extra_pvo = _write_input(
        tmp_path,
        Path("app/data/valuation/universe_pvo_latest.json"),
        b"pvo-original",
    )
    before[extra_pvo] = b"pvo-original"

    def fake_emit_daily_what_changed_report(**kwargs: Any) -> dict[str, Any]:
        Path(kwargs["report_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["report_path"]).write_text(
            json.dumps({"overall_status": "ok", "decision_supported": False})
        )
        return {"overall_status": "ok", "decision_supported": False}

    monkeypatch.setattr(module, "emit_daily_what_changed_report", fake_emit_daily_what_changed_report)

    assert module.main([]) == 0

    for path, original in before.items():
        assert path.read_bytes() == original
    written_files = {
        p.relative_to(tmp_path)
        for p in tmp_path.rglob("*")
        if p.is_file() and p not in before
    }
    assert written_files == {REPORT_RELATIVE}


def test_cli_run_returns_nonzero_on_real_failure_without_partial_report(
    tmp_path,
    monkeypatch,
) -> None:
    module = _cli_module()
    _patch_root(monkeypatch, module, tmp_path)
    _write_inputs(tmp_path)

    def failing_emit(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("disk full")

    monkeypatch.setattr(module, "emit_daily_what_changed_report", failing_emit)

    assert module.main([]) == 1
    assert not (tmp_path / REPORT_RELATIVE).exists()


def test_cli_loads_standalone_from_outside_repo(tmp_path) -> None:
    # Run from a portable out-of-repo dir (the pytest tmp_path), NOT a hardcoded
    # macOS-only path: the CI Linux runner has no /private/tmp, so a hardcoded path
    # fails the subprocess cwd before the import probe even runs.
    outside = str(tmp_path)
    script_path = REPO_ROOT / "scripts" / "run_what_changed_report.py"
    code = f"""
import importlib.util
import os
from pathlib import Path
os.chdir({outside!r})
spec = importlib.util.spec_from_file_location('run_what_changed_report_standalone', {str(script_path)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.main)
assert Path(module.ROOT) == Path({str(REPO_ROOT)!r})
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=outside,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
