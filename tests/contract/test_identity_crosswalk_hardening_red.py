"""RED contract for TW28 identity Units A, B, and D.

This file deliberately excludes Unit C (David-facing degradation copy). David
ordered the threads split, and they must not share an implementation commit.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

FROZEN_CROSSWALK_PATH = Path(
    "app/data/identity/_runs/ff_playerids_20260516.json"
)
FROZEN_CROSSWALK_SHA256 = (
    "8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593"
)


def _producer():
    return importlib.import_module("scripts.build_universe_pvo_batch")


def _runner():
    return importlib.import_module("scripts.run_pvo_refresh")


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _configure_producer(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entries: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    feature_rows: dict[str, dict[str, Any]] | None = None,
) -> tuple[Any, Path]:
    producer = _producer()
    snapshot_path = _write_json(
        tmp_path / "resources" / "snapshot.json",
        {
            "league_id": "test-league",
            "captured_at": "2026-07-28T12:00:00+00:00",
            "players": [],
        },
    )
    crosswalk_path = _write_json(
        tmp_path / FROZEN_CROSSWALK_PATH,
        {"entries": entries},
    )
    feature_path = tmp_path / "app" / "data" / "training" / "features.csv"
    _write_json(feature_path, {})

    source = SimpleNamespace(
        path=feature_path,
        metadata=lambda: {
            "feature_csv_path": str(feature_path),
            "feature_source_kind": "test",
            "feature_csv_sha256": "test-feature-sha",
        },
    )

    original_load_ff_playerids = producer._load_ff_playerids
    monkeypatch.setattr(producer, "ROOT", tmp_path)
    monkeypatch.setattr(producer, "SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(producer, "FF_PLAYERIDS_PATH", crosswalk_path)
    # The production function's default Path was bound at import time. Route the
    # zero-argument production call to this test's explicit fixture without asking
    # GREEN to change its public signature merely for test injection.
    monkeypatch.setattr(
        producer,
        "_load_ff_playerids",
        lambda path=crosswalk_path: original_load_ff_playerids(path),
    )
    monkeypatch.setattr(producer, "ENGINE_B_FEATURES_PATH", feature_path)
    monkeypatch.setattr(
        producer,
        "FEATURES_RUNTIME_DIR",
        tmp_path / "app" / "data" / "features_runtime",
    )
    monkeypatch.setattr(producer, "_load_prospect_pvos", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(producer, "resolve_feature_source", lambda **_kwargs: source)
    monkeypatch.setattr(
        producer,
        "_load_engine_b_feature_rows",
        lambda _path: feature_rows or {},
    )
    monkeypatch.setattr(
        producer,
        "score_inference_partition",
        lambda **_kwargs: predictions,
    )
    monkeypatch.setattr(
        producer,
        "PlayerIdentity",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    def fake_assemble(identity, **_kwargs):
        payload = {
            "sleeper_id": identity.sleeper_id,
            "player_id": identity.dg_id,
            "gsis_id": identity.dg_id,
            "full_name": identity.full_name,
            "position": identity.position,
            "model_grade": "ACTIVE_B",
            "dvs_engine": "B",
            "dynasty_value_score": 50.0,
            "xvar": 0.0,
        }
        # DG-086: the assembly output is no longer only dumped — the whole population
        # runs through compute_dvs_pct_batch first, which reads position / model_grade /
        # dynasty_value_score and writes dvs_pct / dvs_pct_as_of. The fake must carry
        # that PVO-shaped surface (production's assemble_pvo always did).
        return SimpleNamespace(
            position=identity.position,
            model_grade="ACTIVE_B",
            dynasty_value_score=50.0,
            dvs_pct=None,
            dvs_pct_as_of=None,
            model_dump=lambda: payload,
        )

    monkeypatch.setattr(producer, "assemble_pvo", fake_assemble)
    return producer, crosswalk_path


def _run_producer(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entries: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    feature_rows: dict[str, dict[str, Any]] | None = None,
    run_id: str = "identity-red",
) -> dict[str, Any]:
    producer, _ = _configure_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=entries,
        predictions=predictions,
        feature_rows=feature_rows,
    )
    output_dir = tmp_path / "candidate"
    producer.main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            run_id,
        ]
    )
    return json.loads(
        (output_dir / f"universe_pvo_coverage_{run_id}.json").read_text()
    )


def test_missing_crosswalk_aborts_scheduled_refresh_and_preserves_prior_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    producer, crosswalk_path = _configure_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[],
        predictions=[{"player_id": "00-0001", "position": "RB"}],
    )
    crosswalk_path.unlink()
    runner = _runner()

    runtime_dir = tmp_path / "app" / "data" / "valuation_runtime"
    runtime_dir.mkdir(parents=True)
    prior_paths = {
        runtime_dir / "universe_pvo_runtime.json": b"prior-pvo",
        runtime_dir / "universe_pvo_coverage_runtime.json": b"prior-coverage",
        runtime_dir / "universe_pvo_runtime.ready.json": b"prior-marker",
    }
    for path, payload in prior_paths.items():
        path.write_bytes(payload)
    report_path = (
        tmp_path / "app" / "data" / "model_capture" / "pvo_refresh_latest_report.json"
    )

    def refresh_with_real_producer(
        *,
        pvo_artifact_path: Path,
        coverage_artifact_path: Path,
    ) -> None:
        output_dir = tmp_path / "candidate"
        producer.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "missing-crosswalk",
            ]
        )
        # Mirror the real runner adapter: after a successful producer return, move
        # the named run pair into the candidate paths supplied by run_pvo_refresh.
        pvo_artifact_path.write_bytes(
            (output_dir / "universe_pvo_missing-crosswalk.json").read_bytes()
        )
        coverage_artifact_path.write_bytes(
            (
                output_dir
                / "universe_pvo_coverage_missing-crosswalk.json"
            ).read_bytes()
        )

    report = runner.run_pvo_refresh(
        pvo_artifact_path=tmp_path / "unused-seed-pvo.json",
        coverage_artifact_path=tmp_path / "unused-seed-coverage.json",
        runtime_dir=runtime_dir,
        report_path=report_path,
        refresh_fn=refresh_with_real_producer,
        capture_fn=None,
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "refresh"
    assert report["aborted_reason"] == "ff_playerids_crosswalk_missing"
    assert report["decision_supported"] is False
    assert json.loads(report_path.read_text()) == report
    for path, payload in prior_paths.items():
        assert path.read_bytes() == payload


@pytest.mark.parametrize(
    ("raw_payload", "expected_reason"),
    [
        ("not-json", "ff_playerids_crosswalk_invalid_json"),
        ([], "ff_playerids_payload_not_object"),
        ({}, "ff_playerids_entries_not_list"),
        ({"entries": {}}, "ff_playerids_entries_not_list"),
        ({"entries": [1]}, "ff_playerids_entry_not_object"),
        (
            {"entries": [{"gsis_id": 123, "sleeper_id": "456"}]},
            "ff_playerids_identifier_wrong_type",
        ),
        (
            {"entries": [{"gsis_id": "00-1", "sleeper_id": False}]},
            "ff_playerids_identifier_wrong_type",
        ),
    ],
)
def test_crosswalk_shape_corruption_fails_closed_with_named_reason(
    tmp_path: Path,
    raw_payload: Any,
    expected_reason: str,
) -> None:
    producer = _producer()
    path = tmp_path / "ff_playerids.json"
    if isinstance(raw_payload, str):
        path.write_text(raw_payload)
    else:
        _write_json(path, raw_payload)

    with pytest.raises(ValueError, match=expected_reason):
        producer._load_ff_playerids(path)


def test_duplicate_json_key_fails_closed_before_last_write_wins(
    tmp_path: Path,
) -> None:
    producer = _producer()
    path = tmp_path / "ff_playerids.json"
    path.write_text(
        '{"entries":[{"gsis_id":"00-good","gsis_id":"00-wrong",'
        '"sleeper_id":"101"}]}'
    )

    with pytest.raises(ValueError, match="ff_playerids_duplicate_json_key"):
        producer._load_ff_playerids(path)


def test_non_utf8_crosswalk_uses_named_invalid_json_reason(
    tmp_path: Path,
) -> None:
    producer = _producer()
    path = tmp_path / "ff_playerids.json"
    path.write_bytes(b'{"entries":[{"gsis_id":"\xff","sleeper_id":"101"}]}')

    with pytest.raises(ValueError, match="ff_playerids_crosswalk_invalid_json"):
        producer._load_ff_playerids(path)


@pytest.mark.parametrize(
    ("entries", "expected_reason"),
    [
        (
            [
                {"gsis_id": "00-1", "sleeper_id": "101"},
                {"gsis_id": "00-1", "sleeper_id": "202"},
            ],
            "ff_playerids_conflicting_gsis_mapping",
        ),
        (
            [
                {"gsis_id": "00-1", "sleeper_id": "101"},
                {"gsis_id": "00-2", "sleeper_id": "101"},
            ],
            "ff_playerids_conflicting_sleeper_mapping",
        ),
    ],
)
def test_conflicting_crosswalk_mappings_fail_closed_instead_of_last_write_wins(
    tmp_path: Path,
    entries: list[dict[str, Any]],
    expected_reason: str,
) -> None:
    producer = _producer()
    path = _write_json(tmp_path / "ff_playerids.json", {"entries": entries})

    with pytest.raises(ValueError, match=expected_reason):
        producer._load_ff_playerids(path)


def test_null_crosswalk_identifiers_are_absent_not_stringified(
    tmp_path: Path,
) -> None:
    producer = _producer()
    path = _write_json(
        tmp_path / "ff_playerids.json",
        {"entries": [{"gsis_id": None, "sleeper_id": None, "name": "No IDs"}]},
    )

    by_gsis, by_sleeper = producer._load_ff_playerids(path)

    assert by_gsis == {}
    assert by_sleeper == {}
    assert "None" not in by_gsis
    assert "None" not in by_sleeper


def test_partial_join_reports_every_orphan_in_deterministic_gsis_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage = _run_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[
            {
                "gsis_id": "00-0003",
                "sleeper_id": "303",
                "name": "Joined Player",
                "position": "RB",
            },
            {
                "gsis_id": "00-0002",
                "name": "No Sleeper Player",
                "position": "WR",
            },
        ],
        predictions=[
            {"player_id": "00-0003", "position": "RB"},
            {"player_id": "00-0002", "position": "WR"},
            {"player_id": "00-0001", "position": "TE"},
        ],
        feature_rows={
            "00-0001": {"full_name": None, "position": "TE"},
            "00-0002": {"full_name": "Feature Name", "position": "WR"},
            "00-0003": {"full_name": "Joined Player", "position": "RB"},
        },
    )

    join = coverage["engine_b_identity_join"]
    assert join["prediction_count"] == 3
    assert join["join_success_count"] == 1
    assert join["orphan_count"] == len(join["orphan_records"]) == 2
    assert join["orphan_records"] == [
        {
            "gsis_id": "00-0001",
            "name": None,
            "position": "TE",
            "reason": "crosswalk_entry_missing",
        },
        {
            "gsis_id": "00-0002",
            "name": "No Sleeper Player",
            "position": "WR",
            "reason": "sleeper_id_missing",
        },
    ]


def test_zero_orphans_emits_present_empty_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage = _run_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[
            {
                "gsis_id": "00-0001",
                "sleeper_id": "101",
                "name": "Joined Player",
                "position": "QB",
            }
        ],
        predictions=[{"player_id": "00-0001", "position": "QB"}],
    )

    join = coverage["engine_b_identity_join"]
    assert join["join_success_count"] == 1
    assert join["orphan_count"] == 0
    assert join["orphan_records"] == []


def test_empty_prediction_collection_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    producer, _ = _configure_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[
            {
                "gsis_id": "00-0001",
                "sleeper_id": "101",
                "name": "Available Mapping",
                "position": "QB",
            }
        ],
        predictions=[],
    )

    with pytest.raises(ValueError, match="engine_b_predictions_empty"):
        producer.main(
            [
                "--output-dir",
                str(tmp_path / "candidate"),
                "--run-id",
                "empty-predictions",
            ]
        )


def test_zero_successful_joins_fails_closed_without_selecting_partial_coverage_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    producer, _ = _configure_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[{"gsis_id": "00-0001", "name": "Orphan", "position": "WR"}],
        predictions=[{"player_id": "00-0001", "position": "WR"}],
    )

    with pytest.raises(ValueError, match="engine_b_identity_join_zero_success"):
        producer.main(
            [
                "--output-dir",
                str(tmp_path / "candidate"),
                "--run-id",
                "zero-success",
            ]
        )


def test_parsed_object_identical_crosswalk_duplicates_are_counted_and_tolerated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = {
        "gsis_id": "00-0001",
        "sleeper_id": "101",
        "name": "Same Player",
        "position": "RB",
    }
    coverage = _run_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[entry, dict(entry)],
        predictions=[{"player_id": "00-0001", "position": "RB"}],
    )

    join = coverage["engine_b_identity_join"]
    assert join["crosswalk_duplicate_count"] == 1
    assert join["join_success_count"] == 1
    assert join["orphan_count"] == 0


def test_identical_prediction_duplicates_are_counted_not_silently_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prediction = {"player_id": "00-0001", "position": "TE", "score": 1.25}
    coverage = _run_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[
            {
                "gsis_id": "00-0001",
                "sleeper_id": "101",
                "name": "Same Prediction",
                "position": "TE",
            }
        ],
        predictions=[prediction, dict(prediction)],
    )

    join = coverage["engine_b_identity_join"]
    assert join["prediction_duplicate_count"] == 1
    assert join["prediction_count"] == 2
    assert join["join_success_count"] == 1
    assert join["orphan_count"] == 0


def test_conflicting_prediction_duplicates_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    producer, _ = _configure_producer(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        entries=[
            {
                "gsis_id": "00-0001",
                "sleeper_id": "101",
                "name": "Conflicting Prediction",
                "position": "QB",
            }
        ],
        predictions=[
            {"player_id": "00-0001", "position": "QB", "score": 1.0},
            {"player_id": "00-0001", "position": "QB", "score": 2.0},
        ],
    )

    with pytest.raises(ValueError, match="engine_b_prediction_conflict"):
        producer.main(
            [
                "--output-dir",
                str(tmp_path / "candidate"),
                "--run-id",
                "prediction-conflict",
            ]
        )


def test_production_loader_resolves_tracked_frozen_crosswalk_and_keeps_siblings_ignored() -> None:
    producer = _producer()
    resolved = producer.FF_PLAYERIDS_PATH.resolve()
    expected = (Path.cwd() / FROZEN_CROSSWALK_PATH).resolve()

    assert resolved == expected
    assert resolved.is_file()
    assert hashlib.sha256(resolved.read_bytes()).hexdigest() == FROZEN_CROSSWALK_SHA256

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(FROZEN_CROSSWALK_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr

    ignored_sibling = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            "app/data/identity/_runs/not_the_frozen_crosswalk.json",
        ],
        check=False,
    )
    assert ignored_sibling.returncode == 0
