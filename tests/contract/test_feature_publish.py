from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd

from tests.contract.test_feature_validation import _clean_candidate


def _publish_module():
    return importlib.import_module("src.dynasty_genius.features.feature_publish")


def _write_candidate(path: Path, frame: pd.DataFrame | None = None) -> Path:
    frame = _clean_candidate() if frame is None else frame
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def test_publish_runtime_valid_candidate_writes_runtime_ready_marker_and_report(
    tmp_path: Path,
) -> None:
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"
    candidate_path = _write_candidate(runtime_dir / "engine_b_features_candidate.csv")

    result = publish.publish_runtime(
        candidate_path,
        runtime_dir=runtime_dir,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
    )

    runtime_path = runtime_dir / "engine_b_features_runtime.csv"
    ready_path = runtime_dir / "engine_b_features_runtime.ready.json"
    report_path = runtime_dir / "feature_refresh_latest_report.json"

    assert result["status"] == "ok"
    assert result["publish_performed"] is True
    assert result["decision_supported"] is False
    assert result["runtime_promotable_to_seed"] is True
    assert runtime_path.exists()
    assert ready_path.exists()
    assert report_path.exists()
    ready = json.loads(ready_path.read_text())
    assert ready["status"] == "ok"
    assert ready["validation"]["ok"] is True
    assert ready["runtime_sha256"] == result["runtime_sha256"]
    report = json.loads(report_path.read_text())
    assert report["decision_supported"] is False
    assert report["validation"]["ok"] is True
    assert str(runtime_path) in result["dirty_paths"]


def test_publish_runtime_invalid_candidate_does_not_replace_prior_valid_runtime(
    tmp_path: Path,
) -> None:
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"
    prior_runtime = _write_candidate(runtime_dir / "engine_b_features_runtime.csv")
    prior_ready = runtime_dir / "engine_b_features_runtime.ready.json"
    prior_ready.write_text(json.dumps({"status": "ok", "runtime_sha256": "prior"}))
    prior_runtime_bytes = prior_runtime.read_bytes()
    prior_ready_bytes = prior_ready.read_bytes()

    invalid = _clean_candidate().drop(columns=["snap_share"])
    candidate_path = _write_candidate(runtime_dir / "engine_b_features_candidate.csv", invalid)

    result = publish.publish_runtime(
        candidate_path,
        runtime_dir=runtime_dir,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
    )

    assert result["status"] == "blocked"
    assert result["publish_performed"] is False
    assert result["decision_supported"] is False
    assert any("schema" in failure.lower() for failure in result["validation"]["failures"])
    assert prior_runtime.read_bytes() == prior_runtime_bytes
    assert prior_ready.read_bytes() == prior_ready_bytes
    report = json.loads((runtime_dir / "feature_refresh_latest_report.json").read_text())
    assert report["status"] == "blocked"
    assert report["validation"]["ok"] is False


def test_publish_runtime_invalid_candidate_without_prior_runtime_has_no_ready_marker(
    tmp_path: Path,
) -> None:
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"
    invalid = _clean_candidate().assign(snap_share=1.5)
    candidate_path = _write_candidate(runtime_dir / "engine_b_features_candidate.csv", invalid)

    result = publish.publish_runtime(
        candidate_path,
        runtime_dir=runtime_dir,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
    )

    assert result["status"] == "blocked"
    assert not (runtime_dir / "engine_b_features_runtime.ready.json").exists()
    assert not (runtime_dir / "engine_b_features_runtime.csv").exists()


def test_publish_runtime_restores_prior_runtime_when_write_fails(
    tmp_path: Path,
) -> None:
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"
    prior_runtime = _write_candidate(runtime_dir / "engine_b_features_runtime.csv")
    prior_ready = runtime_dir / "engine_b_features_runtime.ready.json"
    prior_ready.write_text(json.dumps({"status": "ok", "runtime_sha256": "prior"}))
    prior_runtime_bytes = prior_runtime.read_bytes()
    prior_ready_bytes = prior_ready.read_bytes()
    candidate_path = _write_candidate(runtime_dir / "engine_b_features_candidate.csv")

    def fail_replace(*_: object, **__: object) -> None:
        raise OSError("simulated publish write failure")

    result = publish.publish_runtime(
        candidate_path,
        runtime_dir=runtime_dir,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
        replace_fn=fail_replace,
    )

    assert result["status"] == "blocked"
    assert result["restored_from_backup"] is True
    assert "simulated publish write failure" in result["blocked_reason"]
    assert prior_runtime.read_bytes() == prior_runtime_bytes
    assert prior_ready.read_bytes() == prior_ready_bytes


def test_feature_refresh_runner_can_publish_validated_candidate(
    tmp_path: Path,
) -> None:
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=lambda: pd.Timestamp("2026-06-25T12:00:00Z").to_pydatetime(),
        read_fns={},
        source_inputs={"source_hash": "new-source", "seasons_window": [2025]},
        assemble_fn=lambda **_: _clean_candidate(),
        publish_fn=lambda candidate_path, **kwargs: publish.publish_runtime(
            candidate_path,
            inference_season=2025,
            min_total_rows=4,
            min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
            **kwargs,
        ),
    )

    assert result["status"] == "ok"
    assert result["publish_performed"] is True
    assert result["decision_supported"] is False
    assert (runtime_dir / "engine_b_features_runtime.csv").exists()


def test_blocked_publish_does_not_poison_next_run_noop_gate(tmp_path: Path) -> None:
    """A blocked publish may disclose source_hash, but must not make the next run noop.

    If an invalid candidate writes `source_hash` into the latest report and the runner only
    compares that hash, the same upstream source will be skipped forever even though no
    validated runtime exists. T2 must only noop from a successful candidate/publish state.
    """
    runner = importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"

    def publish_with_gates(candidate_path, **kwargs):
        return publish.publish_runtime(
            candidate_path,
            inference_season=2025,
            min_total_rows=4,
            min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
            **kwargs,
        )

    blocked = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=lambda: pd.Timestamp("2026-06-25T12:00:00Z").to_pydatetime(),
        read_fns={},
        source_inputs={"source_hash": "same-source", "seasons_window": [2025]},
        assemble_fn=lambda **_: _clean_candidate().drop(columns=["snap_share"]),
        publish_fn=publish_with_gates,
    )
    assert blocked["status"] == "blocked"
    assert not (runtime_dir / "engine_b_features_runtime.csv").exists()

    attempted = {"called": False}

    def valid_after_block(**_: object) -> pd.DataFrame:
        attempted["called"] = True
        return _clean_candidate()

    second = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        seed_path=tmp_path / "seed.csv",
        now_fn=lambda: pd.Timestamp("2026-06-25T12:05:00Z").to_pydatetime(),
        read_fns={},
        source_inputs={"source_hash": "same-source", "seasons_window": [2025]},
        assemble_fn=valid_after_block,
        publish_fn=publish_with_gates,
    )

    assert attempted["called"] is True
    assert second["status"] == "ok"
    assert (runtime_dir / "engine_b_features_runtime.csv").exists()


def test_publish_report_contains_no_forbidden_terms(tmp_path: Path) -> None:
    publish = _publish_module()
    runtime_dir = tmp_path / "features_runtime"
    candidate_path = _write_candidate(runtime_dir / "engine_b_features_candidate.csv")

    publish.publish_runtime(
        candidate_path,
        runtime_dir=runtime_dir,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
    )

    report_text = (runtime_dir / "feature_refresh_latest_report.json").read_text().lower()
    for forbidden in ("buy", "sell", "win", "loss", "tiering", "tradeable edge"):
        assert forbidden not in report_text
