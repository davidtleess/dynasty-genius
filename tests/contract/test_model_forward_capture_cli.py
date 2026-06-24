"""T3 RED: concrete CLI entrypoint for model-output forward capture.

The T2 driver is dependency-injected. T3 adds the executable wrapper that supplies
real filesystem artifact reads, UTC clock, git HEAD provenance, scheduler-friendly
paths, and standalone launchd-safe import behavior.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import timezone
from pathlib import Path


def _load_cli():
    return importlib.import_module("scripts.run_model_forward_capture")


def test_preflight_prints_resolved_config_without_reads_or_writes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()

    def fail_driver(*_args, **_kwargs):
        raise AssertionError("preflight must not call the T2 capture driver")

    monkeypatch.setattr(cli, "capture_model_pvo_snapshot", fail_driver)
    db_path = tmp_path / "model_forward.db"
    report_path = tmp_path / "reports" / "preflight.json"

    result = cli.main(
        [
            "--db-path",
            str(db_path),
            "--report-path",
            str(report_path),
            "--preflight",
        ]
    )

    assert result == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "preflight": True,
        "db_path": str(db_path),
        "pvo_artifact_path": "app/data/valuation/universe_pvo_latest.json",
        "coverage_artifact_path": (
            "app/data/valuation/universe_pvo_coverage_latest.json"
        ),
        "report_path": str(report_path),
        "source": "model_pvo",
    }
    assert not db_path.exists()
    assert not report_path.exists()


def test_success_wires_real_deps_prints_report_and_returns_zero(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = _load_cli()
    pvo_path = tmp_path / "pvo.json"
    coverage_path = tmp_path / "coverage.json"
    pvo_path.write_text('{"players":[]}')
    coverage_path.write_text('{"coverage":true}')
    db_path = tmp_path / "model_forward.db"
    report_path = tmp_path / "nested" / "reports" / "capture.json"
    calls: list[dict] = []

    def fake_capture(**kwargs):
        calls.append(kwargs)
        assert kwargs["read_artifact"](pvo_path) == b'{"players":[]}'
        assert kwargs["read_artifact"](coverage_path) == b'{"coverage":true}'
        now = kwargs["now_fn"]()
        assert now.tzinfo == timezone.utc
        git_sha = kwargs["git_sha_fn"]()
        assert isinstance(git_sha, str)
        assert len(git_sha) >= 7
        report = {
            "status": "ok",
            "capture_date": "2026-06-24",
            "raw_rows": 4,
            "joinable_rows": 2,
            "decision_supported": False,
        }
        kwargs["report_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["report_path"].write_text(json.dumps(report, sort_keys=True))
        return report

    monkeypatch.setattr(cli, "capture_model_pvo_snapshot", fake_capture)
    monkeypatch.setattr(cli, "_git_head_sha", lambda: "abcdef1234567890")

    result = cli.main(
        [
            "--db-path",
            str(db_path),
            "--pvo-artifact-path",
            str(pvo_path),
            "--coverage-artifact-path",
            str(coverage_path),
            "--report-path",
            str(report_path),
        ]
    )

    assert result == 0
    assert len(calls) == 1
    assert calls[0]["db_path"] == db_path
    assert calls[0]["report_path"] == report_path
    assert calls[0]["pvo_artifact_path"] == pvo_path
    assert calls[0]["coverage_artifact_path"] == coverage_path
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert json.loads(report_path.read_text())["decision_supported"] is False


def test_aborted_report_prints_and_returns_nonzero(tmp_path: Path, monkeypatch, capsys) -> None:
    cli = _load_cli()

    def fake_capture(**_kwargs):
        return {
            "status": "aborted",
            "capture_date": "2026-06-24",
            "aborted_reason": "missing_artifact",
            "decision_supported": False,
        }

    monkeypatch.setattr(cli, "capture_model_pvo_snapshot", fake_capture)
    result = cli.main(["--db-path", str(tmp_path / "model_forward.db")])

    assert result == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "aborted"
    assert report["aborted_reason"] == "missing_artifact"
    assert report["decision_supported"] is False


def test_cli_does_not_import_legacy_market_collectors() -> None:
    cli = _load_cli()

    imported_modules = {
        getattr(value, "__name__", "")
        for value in vars(cli).values()
        if getattr(value, "__name__", "")
    }
    assert "scripts.snapshot_fantasycalc" not in imported_modules
    assert "src.dynasty_genius.eval.market_snapshot_store" not in imported_modules


def test_cli_loads_standalone_from_outside_repo(tmp_path: Path) -> None:
    script_path = Path("scripts/run_model_forward_capture.py").resolve()
    probe = "\n".join(
        [
            "import importlib.util",
            "import os",
            "import pathlib",
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"os.chdir({str(tmp_path)!r})",
            "spec = importlib.util.spec_from_file_location(",
            "    'run_model_forward_capture_standalone', script_path",
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
