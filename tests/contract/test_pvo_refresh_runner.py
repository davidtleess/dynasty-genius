"""T4 RED: PVO refresh runner, Option C local-refresh-with-publication-separate.

T4 is the refresh side of the model-output capture brick. It may refresh the two
tracked PVO artifacts locally and then optionally call the independent T3 capture
path, but it must never run the full league-intelligence chain, mutate training/
model artifacts, or auto-commit repo changes.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.dynasty_genius.features.feature_source import ResolvedFeatureSource

PRODUCER_PATH = Path("scripts/build_universe_pvo_batch.py")
ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")
ENGINE_B_FEATURE_CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")
ENGINE_B_RB_MODEL_PATH = Path("app/data/models/engine_b/runs/test/rb_v2.pkl")


def _load_runner():
    return importlib.import_module("scripts.run_pvo_refresh")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _write_runtime_pair(runtime_dir: Path, *, suffix: str = "old") -> tuple[Path, Path]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    pvo = runtime_dir / "universe_pvo_runtime.json"
    coverage = runtime_dir / "universe_pvo_coverage_runtime.json"
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
    (runtime_dir / "universe_pvo_runtime.ready.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "pvo_sha256": _sha(pvo),
                "coverage_sha256": _sha(coverage),
                "source_as_of": f"2026-06-24T12:00:00+00:00-{suffix}",
                "decision_supported": False,
            },
            sort_keys=True,
        )
    )
    return pvo, coverage


def _write_drift_pvo(path: Path, values: dict[str, float], *, modeled: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine_path = "ENGINE_B" if modeled else "PRE_MODEL"
    path.write_text(
        json.dumps(
            {
                "captured_at": "2026-06-24T12:00:00+00:00",
                "schema_version": "universe_pvo_batch.v1",
                "players": [
                    {
                        "sleeper_player_id": player_id,
                        "valuation": {
                            "engine_path": engine_path,
                            "dynasty_value_score": value,
                            "decision_supported": False,
                        },
                    }
                    for player_id, value in values.items()
                ],
            },
            sort_keys=True,
        )
    )
    return path


def _write_drift_coverage(path: Path, *, engine_b: int, pre_model: int = 0) -> Path:
    return _write_json(
        path,
        {
            "total_players": engine_b + pre_model,
            "counts_by_engine_path": {"ENGINE_B": engine_b, "PRE_MODEL": pre_model},
            "decision_supported_true_count": 0,
        },
    )


def _assert_runtime_marker(runtime_dir: Path, pvo: Path, coverage: Path) -> dict:
    marker = json.loads((runtime_dir / "universe_pvo_runtime.ready.json").read_text())
    assert marker["status"] == "ok"
    assert marker["pvo_sha256"] == _sha(pvo)
    assert marker["coverage_sha256"] == _sha(coverage)
    assert marker["decision_supported"] is False
    assert marker["source_as_of"]
    return marker


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


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
        "seed_pvo_path": "app/data/valuation/universe_pvo_latest.json",
        "seed_coverage_path": "app/data/valuation/universe_pvo_coverage_latest.json",
        "runtime_dir": "app/data/valuation_runtime",
        "report_path": str(report_path),
        "capture_db_path": None,
        "phase": "phase17_2_pvo_rebuild_only",
    }
    assert not report_path.exists()
    assert pvo.read_text()
    assert coverage.read_text()


def test_build_universe_pvo_batch_main_accepts_output_dir_and_run_id(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """The producer must be steerable to a temp/runtime dir, not hardcoded latest paths."""
    producer = importlib.import_module("scripts.build_universe_pvo_batch")
    output_dir = tmp_path / "runtime_candidate"
    tracked_output_dir = tmp_path / "tracked_seed"
    monkeypatch.setattr(producer, "OUTPUT_DIR", tracked_output_dir)
    monkeypatch.setattr(producer, "_load_json", lambda _path: {"players": [], "league_id": "L1"})
    monkeypatch.setattr(producer, "_load_prospect_pvos", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(producer, "_active_pvos_from_engine_b", lambda: [])

    result = producer.main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "runtime-test",
        ]
    )

    assert result is None
    assert (output_dir / "universe_pvo_runtime-test.json").exists()
    assert (output_dir / "universe_pvo_latest.json").exists()
    assert (output_dir / "universe_pvo_coverage_runtime-test.json").exists()
    assert (output_dir / "universe_pvo_coverage_latest.json").exists()
    assert not tracked_output_dir.exists()
    out = capsys.readouterr().out
    assert str(output_dir) in out


def test_refresh_publishes_runtime_pair_atomically_without_touching_seed_paths(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    seed_pvo, seed_coverage = _write_pair(tmp_path, suffix="seed")
    original_seed_pvo = seed_pvo.read_bytes()
    original_seed_coverage = seed_coverage.read_bytes()
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    report_path = tmp_path / "reports" / "refresh.json"
    calls: list[tuple[Path, Path]] = []

    def fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        calls.append((pvo_artifact_path, coverage_artifact_path))
        assert runtime_dir not in pvo_artifact_path.parents
        assert pvo_artifact_path != seed_pvo
        assert coverage_artifact_path != seed_coverage
        pvo_artifact_path.write_text(seed_pvo.read_text().replace("98.5", "99.1"))
        coverage_artifact_path.write_text(json.dumps({"raw_rows": 1, "suffix": "runtime"}))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=seed_pvo,
        coverage_artifact_path=seed_coverage,
        runtime_dir=runtime_dir,
        report_path=report_path,
        refresh_fn=fake_refresh,
        capture_fn=None,
        read_artifact=_fixture_reader(seed_pvo, seed_coverage),
        feature_source=_fixture_feature_source(),
    )

    runtime_pvo = runtime_dir / "universe_pvo_runtime.json"
    runtime_coverage = runtime_dir / "universe_pvo_coverage_runtime.json"
    assert report["status"] == "ok"
    assert len(calls) == 1
    assert seed_pvo.read_bytes() == original_seed_pvo
    assert seed_coverage.read_bytes() == original_seed_coverage
    assert runtime_pvo.exists()
    assert runtime_coverage.exists()
    assert "99.1" in runtime_pvo.read_text()
    assert json.loads(runtime_coverage.read_text())["suffix"] == "runtime"
    marker = _assert_runtime_marker(runtime_dir, runtime_pvo, runtime_coverage)
    assert report["runtime"]["pvo_path"] == str(runtime_pvo)
    assert report["runtime"]["coverage_path"] == str(runtime_coverage)
    assert report["runtime"]["ready_marker_path"] == str(
        runtime_dir / "universe_pvo_runtime.ready.json"
    )
    assert report["runtime"]["pvo_sha256"] == marker["pvo_sha256"]
    assert report["runtime"]["coverage_sha256"] == marker["coverage_sha256"]
    assert report["dirty_paths"] == []
    assert report["commit_required_for_repo_baseline"] is False
    assert json.loads(report_path.read_text()) == report


def test_main_defaults_to_runtime_mode_and_never_mutates_tracked_seed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The scheduler entrypoint (main) must default to seed-split runtime mode: publish into
    the gitignored runtime dir and never write the tracked seed pair."""
    runner = _load_runner()
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    report_path = tmp_path / "reports" / "refresh.json"
    seed_sentinel = tmp_path / "tracked_seed.json"
    seed_sentinel.write_text("SEED-SENTINEL")
    coverage_sentinel = tmp_path / "tracked_coverage.json"
    coverage_sentinel.write_text("COVERAGE-SENTINEL")

    def fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        Path(pvo_artifact_path).write_text(json.dumps({"players": []}))
        Path(coverage_artifact_path).write_text(json.dumps({"raw_rows": 0}))

    monkeypatch.setattr(runner, "_phase17_2_refresh", fake_refresh)

    rc = runner.main(
        [
            "--pvo-artifact-path",
            str(seed_sentinel),
            "--coverage-artifact-path",
            str(coverage_sentinel),
            "--runtime-dir",
            str(runtime_dir),
            "--report-path",
            str(report_path),
        ]
    )

    assert rc == 0
    assert (runtime_dir / "universe_pvo_runtime.json").exists()
    assert (runtime_dir / "universe_pvo_coverage_runtime.json").exists()
    assert (runtime_dir / "universe_pvo_runtime.ready.json").exists()
    report = json.loads(report_path.read_text())
    assert report["status"] == "ok"
    assert report["dirty_paths"] == []
    # The tracked seed paths are NEVER written in runtime mode.
    assert seed_sentinel.read_text() == "SEED-SENTINEL"
    assert coverage_sentinel.read_text() == "COVERAGE-SENTINEL"


def test_runtime_ready_marker_embeds_seed_staleness_from_explicit_seed_baseline(
    tmp_path: Path,
) -> None:
    """T2b: drift is computed once at publish time against explicit read-only seed paths.

    Use absolute movement, not signed mean movement, so offsetting up/down value moves still
    trip the player-count threshold and cannot wash out.
    """
    runner = _load_runner()
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    seed_values = {f"player-{idx}": 100.0 for idx in range(22)}
    runtime_values = {
        player_id: (106.0 if idx % 2 == 0 else 94.0)
        for idx, player_id in enumerate(seed_values)
    }
    seed_pvo = _write_drift_pvo(tmp_path / "seed" / "universe_pvo_latest.json", seed_values)
    seed_coverage = _write_drift_coverage(
        tmp_path / "seed" / "universe_pvo_coverage_latest.json",
        engine_b=22,
        pre_model=0,
    )

    def fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        _write_drift_pvo(pvo_artifact_path, runtime_values)
        _write_drift_coverage(coverage_artifact_path, engine_b=22, pre_model=0)

    report = runner.run_pvo_refresh(
        pvo_artifact_path=tmp_path / "legacy_ignored_pvo.json",
        coverage_artifact_path=tmp_path / "legacy_ignored_coverage.json",
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=runtime_dir,
        report_path=None,
        refresh_fn=fake_refresh,
        capture_fn=None,
        read_artifact=lambda path: Path(path).read_bytes(),
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "ok"
    marker = json.loads((runtime_dir / "universe_pvo_runtime.ready.json").read_text())
    drift = marker["seed_staleness"]
    assert drift["decision_supported"] is False
    assert drift["promote_recommended"] is True
    assert drift["recommendation_reasons"] == [
        "count_model_supported_players_drifted_gt_5pct>20"
    ]
    assert drift["count_players_drifted_gt_5pct"] == 22
    assert drift["count_model_supported_players_drifted_gt_5pct"] == 22
    assert drift["mean_abs_value_delta"] == pytest.approx(6.0)
    assert drift["p95_abs_value_delta"] == pytest.approx(6.0)
    assert drift["coverage_count_deltas"] == {"ENGINE_B": 0, "PRE_MODEL": 0}
    assert drift["seed_as_of"] == "2026-06-24T12:00:00+00:00"
    assert isinstance(drift["seed_age_days"], int | float)
    assert report["runtime"]["seed_staleness"] == drift


def test_runtime_publish_with_missing_seed_baseline_is_graceful_and_not_recommended(
    tmp_path: Path,
) -> None:
    """A missing seed baseline must not crash publish; it should disclose no baseline."""
    runner = _load_runner()
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"

    def fake_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        _write_drift_pvo(pvo_artifact_path, {"player-1": 100.0})
        _write_drift_coverage(coverage_artifact_path, engine_b=1)

    report = runner.run_pvo_refresh(
        pvo_artifact_path=tmp_path / "legacy_ignored_pvo.json",
        coverage_artifact_path=tmp_path / "legacy_ignored_coverage.json",
        seed_pvo_path=tmp_path / "missing_seed_pvo.json",
        seed_coverage_path=tmp_path / "missing_seed_coverage.json",
        runtime_dir=runtime_dir,
        report_path=None,
        refresh_fn=fake_refresh,
        capture_fn=None,
        read_artifact=lambda path: Path(path).read_bytes(),
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "ok"
    marker = json.loads((runtime_dir / "universe_pvo_runtime.ready.json").read_text())
    drift = marker["seed_staleness"]
    assert drift["decision_supported"] is False
    assert drift["promote_recommended"] is False
    assert drift["baseline_status"] == "no_seed_baseline"
    assert drift["recommendation_reasons"] == []


def test_phase17_2_refresh_drives_producer_with_output_dir_to_candidate_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The real refresh_fn must invoke the producer with --output-dir so it writes the
    candidate pair (never the hardcoded tracked OUTPUT_DIR)."""
    runner = _load_runner()
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        out_dir = Path(cmd[cmd.index("--output-dir") + 1])
        run_id = cmd[cmd.index("--run-id") + 1]
        (out_dir / f"universe_pvo_{run_id}.json").write_text("{}")
        (out_dir / f"universe_pvo_coverage_{run_id}.json").write_text("{}")

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    cand_pvo = tmp_path / "universe_pvo_candidate.json"
    cand_coverage = tmp_path / "universe_pvo_coverage_candidate.json"

    runner._phase17_2_refresh(
        pvo_artifact_path=cand_pvo, coverage_artifact_path=cand_coverage
    )

    assert "--output-dir" in captured["cmd"]
    assert str(tmp_path) in captured["cmd"]
    assert "build_universe_pvo_batch.py" in " ".join(captured["cmd"])
    assert cand_pvo.exists()
    assert cand_coverage.exists()


def test_refresh_failure_preserves_prior_runtime_and_seed_paths(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    seed_pvo, seed_coverage = _write_pair(tmp_path, suffix="seed")
    original_seed_pvo = seed_pvo.read_bytes()
    original_seed_coverage = seed_coverage.read_bytes()
    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    prior_runtime_pvo, prior_runtime_coverage = _write_runtime_pair(runtime_dir, suffix="prior")
    prior_runtime_pvo_bytes = prior_runtime_pvo.read_bytes()
    prior_runtime_coverage_bytes = prior_runtime_coverage.read_bytes()
    prior_marker_bytes = (runtime_dir / "universe_pvo_runtime.ready.json").read_bytes()

    def failing_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text("partial candidate pvo")
        coverage_artifact_path.write_text("partial candidate coverage")
        raise RuntimeError("producer_failed")

    report = runner.run_pvo_refresh(
        pvo_artifact_path=seed_pvo,
        coverage_artifact_path=seed_coverage,
        runtime_dir=runtime_dir,
        report_path=None,
        refresh_fn=failing_refresh,
        capture_fn=None,
        read_artifact=_fixture_reader(seed_pvo, seed_coverage),
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "refresh"
    assert report["restored_from_backup"] is False
    assert report["decision_supported"] is False
    assert seed_pvo.read_bytes() == original_seed_pvo
    assert seed_coverage.read_bytes() == original_seed_coverage
    assert prior_runtime_pvo.read_bytes() == prior_runtime_pvo_bytes
    assert prior_runtime_coverage.read_bytes() == prior_runtime_coverage_bytes
    assert (runtime_dir / "universe_pvo_runtime.ready.json").read_bytes() == prior_marker_bytes


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
        feature_source=_fixture_feature_source(),
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


def _fixture_feature_source() -> ResolvedFeatureSource:
    return ResolvedFeatureSource(
        path=ENGINE_B_FEATURE_CSV_PATH,
        source_kind="seed",
        sha256="fixture-feature-sha",
        source_as_of=None,
        ready=True,
        published_seed_sha256="fixture-feature-sha",
    )


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
        feature_source=_fixture_feature_source(),
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
        feature_source=_fixture_feature_source(),
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
        feature_source=_fixture_feature_source(),
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
        feature_source=_fixture_feature_source(),
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
        feature_source=_fixture_feature_source(),
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
