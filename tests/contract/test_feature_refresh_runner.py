from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = Path("app/data/features_runtime")
CANDIDATE_PATH = RUNTIME_DIR / "engine_b_features_candidate.csv"
RUNTIME_PATH = RUNTIME_DIR / "engine_b_features_runtime.csv"
REPORT_PATH = RUNTIME_DIR / "feature_refresh_latest_report.json"
LOCK_PATH = RUNTIME_DIR / "feature_refresh.lock"


def _now() -> datetime:
    return datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


def _source_frames(*, include_changed_value: bool = False) -> dict[str, pd.DataFrame]:
    current_points = 99.9 if include_changed_value else 10.0
    return {
        "player_stats": pd.DataFrame(
            [
                {
                    "player_id": "p1",
                    "season": 2023,
                    "position": "WR",
                    "team": "MIN",
                    "fantasy_points_ppr": 100.0,
                    "week": 1,
                },
                {
                    "player_id": "p1",
                    "season": 2024,
                    "position": "WR",
                    "team": "MIN",
                    "fantasy_points_ppr": 110.0,
                    "week": 1,
                },
                {
                    "player_id": "p1",
                    "season": 2025,
                    "position": "WR",
                    "team": "MIN",
                    "fantasy_points_ppr": current_points,
                    "week": 1,
                },
            ]
        ),
        "rosters": pd.DataFrame(
            [
                {"gsis_id": "p1", "season": 2023, "birth_date": "2000-01-01"},
                {"gsis_id": "p1", "season": 2024, "birth_date": "2000-01-01"},
                {"gsis_id": "p1", "season": 2025, "birth_date": "2000-01-01"},
            ]
        ),
    }


def test_assemble_engine_b_dataset_uses_shared_inference_rule_not_legacy_drop() -> None:
    engine_b_script = importlib.import_module("scripts.assemble_engine_b_dataset")
    source = Path(engine_b_script.__file__).read_text()

    assert 'df["training_eligible"] = df["feature_season"] < 2024' not in source
    assert "dropna(subset=[OUTCOME_COLUMN])" not in source
    assert "inference_season_rule" in source
    assert "assemble_feature_candidate" in source


def test_inference_season_rule_is_computed_not_hardcoded_2024() -> None:
    assembly = importlib.import_module("src.dynasty_genius.features.feature_assembly")

    assert assembly.inference_season_rule([2021, 2022, 2023]) == 2023
    assert assembly.inference_season_rule([2023, 2024, 2025]) == 2025


def test_source_hash_is_deterministic_and_excludes_wall_clock() -> None:
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    base_inputs = {
        "loader_outputs": _source_frames(),
        "seasons_window": [2023, 2024, 2025],
        "package_version": "nflreadpy-test",
        "builder_config": {"min_games": 4, "generated_at": "2026-06-25T12:00:00Z"},
        "te_rubric_artifacts": {"sha256": "te-rubric"},
        "identity_inputs": {"sha256": "identity"},
    }

    first = runner.compute_source_hash(**base_inputs)
    changed_clock_only = {
        **base_inputs,
        "builder_config": {"min_games": 4, "generated_at": "2030-01-01T00:00:00Z"},
    }
    assert runner.compute_source_hash(**changed_clock_only) == first

    changed_source = {**base_inputs, "loader_outputs": _source_frames(include_changed_value=True)}
    assert runner.compute_source_hash(**changed_source) != first


def test_run_feature_refresh_noops_when_source_hash_matches_report(tmp_path: Path) -> None:
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir()
    (runtime_dir / "feature_refresh_latest_report.json").write_text(
        json.dumps({"source_hash": "same-source"})
    )

    def fail_assembly(**_: object) -> pd.DataFrame:
        raise AssertionError("noop must not assemble or write a candidate")

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=_now,
        read_fns={},
        source_inputs={"source_hash": "same-source"},
        assemble_fn=fail_assembly,
    )

    assert result["status"] == "noop"
    assert result["publish_performed"] is False
    assert result["decision_supported"] is False
    assert not (runtime_dir / "engine_b_features_candidate.csv").exists()


def test_run_feature_refresh_writes_candidate_ready_not_ok_in_t1(tmp_path: Path) -> None:
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    runtime_dir = tmp_path / "features_runtime"

    def assemble(**_: object) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "player_id": "p1",
                    "feature_season": 2025,
                    "position": "WR",
                    "training_eligible": False,
                    "avg_ppg_t1_t2": None,
                }
            ]
        )

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=_now,
        read_fns=_source_frames(),
        source_inputs={"source_hash": "new-source"},
        assemble_fn=assemble,
    )

    assert result["status"] == "candidate_ready"
    assert result["status"] != "ok"
    assert result["publish_performed"] is False
    assert result["decision_supported"] is False
    candidate_path = runtime_dir / "engine_b_features_candidate.csv"
    assert candidate_path.exists()
    assert Path(result["candidate_path"]) == candidate_path
    report = json.loads((runtime_dir / "feature_refresh_latest_report.json").read_text())
    assert report["source_hash"] == "new-source"


def test_cli_preflight_is_readiness_only(tmp_path: Path) -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,training_eligible\n")

    rc = cli.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--seed-path",
            str(seed_path),
            "--preflight",
        ]
    )

    assert rc == 0
    assert not runtime_dir.exists() or not any(runtime_dir.iterdir())


def test_runner_static_and_runtime_audit_blocks_training_and_model_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    runner_source = Path(runner.__file__).read_text()
    cli_source = (ROOT / "scripts" / "run_feature_refresh.py").read_text()
    combined_source = runner_source + "\n" + cli_source
    assert "train_engine_b" not in combined_source
    assert ".fit(" not in combined_source
    assert "app/data/models" not in combined_source

    import sklearn.linear_model

    def fail_fit(*_: object, **__: object) -> None:
        raise AssertionError("feature refresh must not fit a model")

    monkeypatch.setattr(sklearn.linear_model.Ridge, "fit", fail_fit)

    runtime_dir = tmp_path / "features_runtime"
    models_dir = tmp_path / "app" / "data" / "models"
    before_files = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=_now,
        read_fns=_source_frames(),
        source_inputs={"source_hash": "model-write-audit"},
        assemble_fn=lambda **_: pd.DataFrame(
            [{"player_id": "p1", "feature_season": 2025, "training_eligible": False}]
        ),
    )

    assert result["status"] == "candidate_ready"
    assert not models_dir.exists()
    after_files = sorted(
        p.relative_to(tmp_path)
        for p in tmp_path.rglob("*")
        if "features_runtime" not in p.parts
    )
    assert after_files == before_files


def test_cli_loads_standalone_from_outside_repo(tmp_path: Path) -> None:
    script_path = ROOT / "scripts" / "run_feature_refresh.py"
    probe = tmp_path / "load_feature_refresh.py"
    probe.write_text(
        "\n".join(
            [
                "import importlib.util",
                f"script_path = {str(script_path)!r}",
                "spec = importlib.util.spec_from_file_location(",
                "    'run_feature_refresh_standalone', script_path",
                ")",
                "module = importlib.util.module_from_spec(spec)",
                "assert spec.loader is not None",
                "spec.loader.exec_module(module)",
                "assert callable(module.main)",
            ]
        )
    )

    result = subprocess.run(
        [sys.executable, str(probe)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_feature_runtime_paths_are_gitignored() -> None:
    paths = [
        CANDIDATE_PATH,
        RUNTIME_PATH,
        REPORT_PATH,
        LOCK_PATH,
        RUNTIME_DIR / "engine_b_features_runtime.ready.json",
    ]

    result = subprocess.run(
        ["git", "check-ignore", "--", *(str(path) for path in paths)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    ignored = set(result.stdout.splitlines())
    assert {str(path) for path in paths} <= ignored
