"""T4 RED: PVO refresh runner, Option C local-refresh-with-publication-separate.

T4 is the refresh side of the model-output capture brick. It may refresh the two
tracked PVO artifacts locally and then optionally call the independent T3 capture
path, but it must never run the full league-intelligence chain, mutate training/
model artifacts, or auto-commit repo changes.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCER_PATH = Path("scripts/build_universe_pvo_batch.py")
ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")
ENGINE_B_FEATURE_CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")
ENGINE_B_RB_MODEL_PATH = Path("app/data/models/engine_b/runs/test/rb_v2.pkl")


def _load_runner():
    return importlib.import_module("scripts.run_pvo_refresh")


def _write_pair(tmp_path: Path, *, suffix: str = "old") -> tuple[Path, Path]:
    pvo = tmp_path / "app" / "data" / "valuation" / "universe_pvo_latest.json"
    coverage = (
        tmp_path
        / "app"
        / "data"
        / "valuation"
        / "universe_pvo_coverage_latest.json"
    )
    pvo.parent.mkdir(parents=True)
    pvo.write_text(
        json.dumps(
            {
                "captured_at": f"2026-06-24T12:00:00+00:00-{suffix}",
                "schema_version": "universe_pvo_batch.v1",
                "source_snapshot_captured_at": "2026-06-23T11:30:00+00:00",
                "players": [
                    {
                        "captured_at": f"volatile-{suffix}",
                        "pipeline_run_id": f"run-{suffix}",
                        "identity_ids": {"sleeper_id": "9509"},
                        "lineage": {
                            "governance_version": "1.0.0",
                            "sleeper_snapshot_hash": "sleeper-snapshot-v1",
                        },
                        "valuation": {
                            "engine_path": "ENGINE_B",
                            "dynasty_value_score": 98.5,
                        },
                    }
                ],
            },
            sort_keys=True,
        )
    )
    coverage.write_text(json.dumps({"raw_rows": 1, "suffix": suffix}, sort_keys=True))
    return pvo, coverage


def test_preflight_prints_config_without_refresh_capture_or_writes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    report_path = tmp_path / "reports" / "refresh.json"

    def fail_refresh(*_args, **_kwargs):
        raise AssertionError("preflight must not refresh PVO")

    def fail_capture(*_args, **_kwargs):
        raise AssertionError("preflight must not call capture")

    monkeypatch.setattr(runner, "_phase17_2_refresh", fail_refresh)
    monkeypatch.setattr(runner, "capture_model_pvo_snapshot", fail_capture)

    result = runner.main(
        [
            "--pvo-artifact-path",
            str(pvo),
            "--coverage-artifact-path",
            str(coverage),
            "--report-path",
            str(report_path),
            "--preflight",
        ]
    )

    assert result == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "preflight": True,
        "pvo_artifact_path": str(pvo),
        "coverage_artifact_path": str(coverage),
        "report_path": str(report_path),
        "capture_db_path": None,
        "phase": "phase17_2_pvo_rebuild_only",
    }
    assert not report_path.exists()
    assert pvo.read_text()
    assert coverage.read_text()


def test_success_refreshes_only_two_artifacts_reports_hashes_and_never_commits(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    report_path = tmp_path / "reports" / "refresh.json"
    bad_calls: list[list[str]] = []
    refresh_calls: list[tuple[Path, Path]] = []

    def fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        refresh_calls.append((pvo_artifact_path, coverage_artifact_path))
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))

    def fake_run(cmd, *_args, **_kwargs):
        bad_calls.append(list(cmd))
        raise AssertionError(f"runner must not execute git or banned producers: {cmd}")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=report_path,
        refresh_fn=fake_refresh,
        capture_fn=None,
        read_artifact=_fixture_reader(pvo, coverage),
    )

    assert result["status"] == "ok"
    assert refresh_calls == [(pvo, coverage)]
    assert result["decision_supported"] is False
    assert result["commit_required_for_repo_baseline"] is True
    assert result["pre"]["artifact_sha256"] != result["post"]["artifact_sha256"]
    assert result["pre"]["semantic_output_hash"] != result["post"]["semantic_output_hash"]
    assert "provenance_hash" in result["pre"]
    assert "provenance_hash" in result["post"]
    assert result["semantic_changed"] is True
    assert isinstance(result["provenance_changed"], bool)
    assert set(result["dirty_paths"]) == {str(pvo), str(coverage)}
    assert result["forbidden_commands_attempted"] == []
    assert bad_calls == []
    assert json.loads(report_path.read_text()) == result

    # main() should print the same report shape and return zero on status=ok.
    monkeypatch.setattr(runner, "run_pvo_refresh", lambda **_kwargs: result)
    assert runner.main(
        [
            "--pvo-artifact-path",
            str(pvo),
            "--coverage-artifact-path",
            str(coverage),
            "--report-path",
            str(report_path),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def _lineage_bytes(*, model_bytes: bytes = b"rb model v1") -> dict[Path, bytes]:
    return {
        PRODUCER_PATH: b"phase17.2 producer v1",
        ENGINE_B_MANIFEST_PATH: json.dumps(
            {"RB": str(ENGINE_B_RB_MODEL_PATH)}, sort_keys=True
        ).encode(),
        ENGINE_B_RB_MODEL_PATH: model_bytes,
        ENGINE_B_FEATURE_CSV_PATH: (
            b"season,training_eligible\n"
            b"2022,true\n"
            b"2023,true\n"
            b"2024,false\n"
        ),
    }


def _fixture_reader(pvo: Path, coverage: Path, *, model_bytes: bytes = b"rb model v1"):
    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized == pvo:
            return pvo.read_bytes()
        if normalized == coverage:
            return coverage.read_bytes()
        lineage = _lineage_bytes(model_bytes=model_bytes)
        if normalized in lineage:
            return lineage[normalized]
        raise FileNotFoundError(str(normalized))

    return read_artifact


def test_provenance_changed_tracks_lineage_artifact_change_with_same_semantic_output(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    reads_after_refresh = False

    def refresh_same_semantic_output(
        *, pvo_artifact_path: Path, coverage_artifact_path: Path
    ) -> None:
        nonlocal reads_after_refresh
        # Only volatile bytes change; semantic_output_hash should stay stable.
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text()
            .replace("volatile-old", "volatile-new")
            .replace("run-old", "run-new")
        )
        coverage_artifact_path.write_text(coverage_artifact_path.read_text())
        reads_after_refresh = True

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized == pvo:
            return pvo.read_bytes()
        if normalized == coverage:
            return coverage.read_bytes()
        lineage = _lineage_bytes(
            model_bytes=b"rb model v2" if reads_after_refresh else b"rb model v1"
        )
        if normalized in lineage:
            return lineage[normalized]
        raise FileNotFoundError(str(normalized))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_same_semantic_output,
        capture_fn=None,
        read_artifact=read_artifact,
    )

    assert report["status"] == "ok"
    assert report["pre"]["artifact_sha256"] != report["post"]["artifact_sha256"]
    assert report["pre"]["semantic_output_hash"] == report["post"]["semantic_output_hash"]
    assert report["pre"]["provenance_hash"] != report["post"]["provenance_hash"]
    assert report["semantic_changed"] is False
    assert report["provenance_changed"] is True


def test_unresolvable_refresh_provenance_aborts_and_restores_artifacts(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    original_pvo = pvo.read_bytes()
    original_coverage = coverage.read_bytes()

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized == pvo:
            return pvo.read_bytes()
        if normalized == coverage:
            return coverage.read_bytes()
        lineage = _lineage_bytes()
        if normalized == ENGINE_B_MANIFEST_PATH:
            raise FileNotFoundError(str(normalized))
        if normalized in lineage:
            return lineage[normalized]
        raise FileNotFoundError(str(normalized))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_fn,
        capture_fn=None,
        read_artifact=read_artifact,
    )

    assert report["status"] == "aborted"
    assert "required_provenance_missing" in report["aborted_reason"]
    assert report["restored_from_backup"] is True
    assert report["decision_supported"] is False
    assert pvo.read_bytes() == original_pvo
    assert coverage.read_bytes() == original_coverage


def test_refresh_failure_restores_both_artifacts_byte_identical_and_skips_capture(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    original_pvo = pvo.read_bytes()
    original_coverage = coverage.read_bytes()
    report_path = tmp_path / "reports" / "refresh.json"
    capture_calls: list[dict] = []

    def failing_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text("partial pvo mutation")
        coverage_artifact_path.write_text("partial coverage mutation")
        raise RuntimeError("phase17_2_failed")

    def fake_capture(**kwargs) -> dict:
        capture_calls.append(kwargs)
        return {"status": "ok"}

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=report_path,
        refresh_fn=failing_refresh,
        capture_fn=fake_capture,
        capture_db_path=tmp_path / "model_forward.db",
        read_artifact=_fixture_reader(pvo, coverage),
    )

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == "phase17_2_failed"
    assert report["restored_from_backup"] is True
    assert report["decision_supported"] is False
    assert pvo.read_bytes() == original_pvo
    assert coverage.read_bytes() == original_coverage
    assert capture_calls == []
    assert json.loads(report_path.read_text()) == report


def test_orchestrated_success_calls_capture_after_refresh_but_capture_cli_remains_independent(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    capture_calls: list[dict] = []

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))

    def capture_fn(**kwargs) -> dict:
        capture_calls.append(kwargs)
        return {"status": "ok", "decision_supported": False}

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_fn,
        capture_fn=capture_fn,
        capture_db_path=tmp_path / "model_forward.db",
        capture_report_path=tmp_path / "model_capture" / "latest.json",
        read_artifact=_fixture_reader(pvo, coverage),
    )

    assert report["status"] == "ok"
    assert report["capture_report"]["status"] == "ok"
    assert len(capture_calls) == 1
    assert capture_calls[0]["pvo_artifact_path"] == pvo
    assert capture_calls[0]["coverage_artifact_path"] == coverage
    assert capture_calls[0]["db_path"] == tmp_path / "model_forward.db"

    model_cli = importlib.import_module("scripts.run_model_forward_capture")
    assert callable(model_cli.main)


def test_capture_stage_exception_writes_abort_report_without_restoring_successful_refresh(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = _load_runner()
    pvo, coverage = _write_pair(tmp_path)
    original_pvo = pvo.read_bytes()
    original_coverage = coverage.read_bytes()
    report_path = tmp_path / "reports" / "refresh.json"
    bad_calls: list[list[str]] = []

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "new"}))

    def capture_fn(**_kwargs) -> dict:
        raise RuntimeError("capture_conflict")

    def fake_run(cmd, *_args, **_kwargs):
        bad_calls.append(list(cmd))
        raise AssertionError(f"runner must not auto-commit or run subprocesses: {cmd}")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=report_path,
        refresh_fn=refresh_fn,
        capture_fn=capture_fn,
        capture_db_path=tmp_path / "model_forward.db",
        capture_report_path=tmp_path / "model_capture" / "latest.json",
        read_artifact=_fixture_reader(pvo, coverage),
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "capture"
    assert report["aborted_reason"] == "capture_conflict"
    assert report["decision_supported"] is False
    assert report["commit_required_for_repo_baseline"] is True
    assert report["restored_from_backup"] is False
    assert report["pre"]["artifact_sha256"] != report["post"]["artifact_sha256"]
    assert report["semantic_changed"] is True
    assert isinstance(report["provenance_changed"], bool)
    assert set(report["dirty_paths"]) == {str(pvo), str(coverage)}
    assert report["capture_report"] is None
    assert report["forbidden_commands_attempted"] == []
    assert pvo.read_bytes() != original_pvo
    assert coverage.read_bytes() != original_coverage
    assert json.loads(report_path.read_text()) == report
    assert bad_calls == []


def test_runner_rejects_banned_refresh_commands_without_executing(tmp_path: Path) -> None:
    runner = _load_runner()

    for cmd in [
        ["scripts/refresh_league_intelligence.py"],
        ["scripts/assemble_engine_b_dataset.py"],
        ["scripts/train_engine_b.py"],
        ["git", "commit", "-m", "nope"],
        ["git", "add", "app/data/valuation/universe_pvo_latest.json"],
    ]:
        with pytest.raises(ValueError, match="forbidden"):
            runner.assert_allowed_refresh_command(cmd)

    runner.assert_allowed_refresh_command(["scripts/build_universe_pvo_batch.py"])


def test_refresh_runner_loads_standalone_from_outside_repo(tmp_path: Path) -> None:
    script_path = Path("scripts/run_pvo_refresh.py").resolve()
    probe = "\n".join(
        [
            "import importlib.util",
            "import os",
            "import pathlib",
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"os.chdir({str(tmp_path)!r})",
            "spec = importlib.util.spec_from_file_location(",
            "    'run_pvo_refresh_standalone', script_path",
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
