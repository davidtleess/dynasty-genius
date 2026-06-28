"""Model-output forward-capture T2 RED: artifact-read capture driver.

T2 reads published PVO artifacts through injected byte readers, resolves the
read-only provenance block, maps rows into the T1 store, and emits the §5 report.
It deliberately does not refresh PVO, touch the real filesystem, use wall-clock
time, or perform scheduler work; those belong to T3+.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.capture.model_forward_capture_driver import (
    capture_model_pvo_snapshot,
)
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
)
from src.dynasty_genius.features.feature_source import ResolvedFeatureSource

PVO_PATH = Path("app/data/valuation/universe_pvo_latest.json")
COVERAGE_PATH = Path("app/data/valuation/universe_pvo_coverage_latest.json")
PRODUCER_PATH = Path("scripts/build_universe_pvo_batch.py")
ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")
ENGINE_B_FEATURE_CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")
ENGINE_A_LATEST_PATH = Path("app/data/models/latest.json")
HEAD_A_V3_MANIFEST_PATH = Path("app/data/models/head_a/v3_manifest.json")
TE_V3_METADATA_PATH = Path(
    "app/data/models/head_a/runs/20260524T140748Z/te_v3_metadata.json"
)


def _json_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _model_row(
    *,
    sleeper_id: str | None,
    name: str,
    position: str | None,
    engine_path: str,
    score: float | None,
    dg_player_id: str | None = "00-TEST-RB",
    row_captured_at: str = "2026-06-23T12:00:00+00:00",
    pipeline_run_id: str | None = "phase17-2-volatile-a",
    market_overlay: dict | None = None,
    divergence: dict | None = None,
    projection_2y: float | None = 17.25,
) -> dict[str, Any]:
    return {
        "captured_at": row_captured_at,
        "dg_player_id": dg_player_id,
        "sleeper_player_id": sleeper_id,
        "identity_ids": {"sleeper_id": sleeper_id},
        "player": {"full_name": name, "position": position},
        "valuation": {
            "decision_supported": False,
            "dynasty_value_score": score,
            "engine_path": engine_path,
            "model_grade": "MODEL" if score is not None else None,
            "model_version": "engine_b_v2" if engine_path == "ENGINE_B" else "engine_a_v2",
        },
        "dvs_pct": 97.0 if score is not None else None,
        "xvar": 18.5 if score is not None else None,
        "lineage": {
            "governance_version": "1.0.0",
            "sleeper_snapshot_hash": "sleeper-snapshot-v1",
        },
        "pipeline_run_id": pipeline_run_id,
        "market_overlay": market_overlay,
        "divergence": divergence,
        "projection_2y": projection_2y,
    }


def _pvo_artifact(
    *,
    captured_at: str = "2026-06-23T12:00:00+00:00",
    volatile_suffix: str = "a",
) -> dict[str, Any]:
    return {
        "captured_at": captured_at,
        "schema_version": "universe_pvo_batch.v1",
        "source_snapshot_captured_at": "2026-06-23T11:30:00+00:00",
        "coverage": {
            "counts_by_engine_path": {
                "ENGINE_A": 1,
                "ENGINE_B": 1,
                "PRE_MODEL": 1,
                "UNRESOLVED_IDENTITY": 1,
            }
        },
        "players": [
            _model_row(
                sleeper_id="9509",
                dg_player_id="00-TEST-RB",
                name="Bijan Robinson",
                position="RB",
                engine_path="ENGINE_B",
                score=98.5,
                row_captured_at=captured_at,
                pipeline_run_id=f"phase17-2-volatile-{volatile_suffix}",
                market_overlay={"fc_value": 9999},
                divergence={"model_market_gap": 7.5},
            ),
            _model_row(
                sleeper_id="6786",
                dg_player_id="dg_ceedee",
                name="CeeDee Lamb",
                position="WR",
                engine_path="ENGINE_A",
                score=95.1,
                row_captured_at=captured_at,
                pipeline_run_id=f"phase17-2-volatile-{volatile_suffix}",
            ),
            _model_row(
                sleeper_id=None,
                dg_player_id="dg_pre_model",
                name="Non-model Row",
                position="RB",
                engine_path="PRE_MODEL",
                score=None,
                row_captured_at=captured_at,
                pipeline_run_id=f"phase17-2-volatile-{volatile_suffix}",
            ),
            _model_row(
                sleeper_id="0",
                dg_player_id=None,
                name="Unresolved Identity",
                position=None,
                engine_path="UNRESOLVED_IDENTITY",
                score=None,
                row_captured_at=captured_at,
                pipeline_run_id=f"phase17-2-volatile-{volatile_suffix}",
            ),
        ],
    }


def _artifact_bytes(overrides: dict[Path, bytes] | None = None) -> dict[Path, bytes]:
    engine_b_manifest = {
        "QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
        "RB": "app/data/models/engine_b/runs/20260513T012309Z/rb_v2.pkl",
        "WR": "app/data/models/engine_b/runs/20260513T012309Z/wr_v2.pkl",
        "TE": "app/data/models/engine_b/runs/20260516T164503Z/te_v3.pkl",
    }
    data = {
        PVO_PATH: _json_bytes(_pvo_artifact()),
        COVERAGE_PATH: _json_bytes({"schema_version": "coverage.v1", "raw_rows": 4}),
        PRODUCER_PATH: b"# fake pvo producer\nPHASE_17_2_ONLY = True\n",
        ENGINE_B_MANIFEST_PATH: _json_bytes(engine_b_manifest),
        ENGINE_B_FEATURE_CSV_PATH: (
            b"player_id,season,feature_season,position,training_eligible,snap_share,"
            b"route_participation,target_share_nfl,air_yards_share,"
            b"weighted_opportunity,yprr,tprr\n"
            b"00-OLD,2023,2023,QB,true,0.10,0.20,0.30,0.40,0.50,0.60,0.70\n"
            b"00-TEST-RB,2025,2025,RB,false,0.71,0.64,0.18,0.08,0.79,2.19,0.22\n"
        ),
        ENGINE_A_LATEST_PATH: _json_bytes(
            {
                "model_version": "20260502T153931Z",
                "run_dir": "app/data/models/runs/20260502T153931Z",
            }
        ),
        HEAD_A_V3_MANIFEST_PATH: _json_bytes(
            {"TE": "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl"}
        ),
        TE_V3_METADATA_PATH: _json_bytes(
            {"model_version": "head_a_te_v3", "training_cutoff": "unknown"}
        ),
    }
    for path_text in engine_b_manifest.values():
        data[Path(path_text)] = f"fake model bytes for {path_text}\n".encode()
    if overrides:
        data.update(overrides)
    return data


def _reader(data: dict[Path, bytes]):
    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized not in data:
            raise FileNotFoundError(str(normalized))
        return data[normalized]

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


def _now(day: int = 24):
    return lambda: datetime(2026, 6, day, 15, 0, tzinfo=timezone.utc)


def test_capture_reads_artifacts_appends_store_and_emits_section5_report(tmp_path) -> None:
    artifacts = _artifact_bytes()
    report_path = tmp_path / "model_capture" / "latest_report.json"

    report = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=report_path,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "docs-only-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "ok"
    assert report["capture_date"] == "2026-06-24"
    assert report["artifact_vintage"] == "2026-06-23T12:00:00+00:00"
    assert report["artifact_age_days"] == 1
    assert report["raw_rows"] == 4
    assert report["joinable_rows"] == 2
    assert report["counts_by_engine_path"] == {
        "ENGINE_A": 1,
        "ENGINE_B": 1,
        "PRE_MODEL": 1,
        "UNRESOLVED_IDENTITY": 1,
    }
    assert report["missing_sleeper_count"] == 2
    assert report["unresolved_count"] == 1
    assert report["duplicate_count"] == 0
    assert report["market_fields_excluded_count"] == 1
    assert report["artifact_sha256"] == _sha(artifacts[PVO_PATH])
    assert report["coverage_sha256"] == _sha(artifacts[COVERAGE_PATH])
    assert report["semantic_output_hash"]
    assert report["provenance_hash"]
    assert report["store_hash"]
    assert report["vintage_changed"] is True
    assert report["decision_supported"] is False
    assert report["aborted_reason"] is None
    assert report["provenance"]["git_sha"] == "docs-only-sha"
    assert report["provenance"]["row_lineage"] == [
        {
            "player_key": "sleeper:9509",
            "lineage": {
                "governance_version": "1.0.0",
                "sleeper_snapshot_hash": "sleeper-snapshot-v1",
            },
            "pipeline_run_id": "phase17-2-volatile-a",
        },
        {
            "player_key": "sleeper:6786",
            "lineage": {
                "governance_version": "1.0.0",
                "sleeper_snapshot_hash": "sleeper-snapshot-v1",
            },
            "pipeline_run_id": "phase17-2-volatile-a",
        },
    ]
    assert report["provenance"]["engine_b_derived_training_cutoff"] == {
        "value": 2023,
        "status": "derived",
    }
    assert report["provenance"]["engine_a_v2_pointer"]["path"] == str(
        ENGINE_A_LATEST_PATH
    )
    assert report["provenance"]["head_a_v3_manifest"]["path"] == str(
        HEAD_A_V3_MANIFEST_PATH
    )
    assert report["provenance"]["te_v3_metadata"]["path"] == str(TE_V3_METADATA_PATH)
    assert report_path.exists()
    assert json.loads(report_path.read_text()) == report

    store = ModelForwardCaptureStore(tmp_path / "model_forward.db")
    raw = store.get_raw_entries(
        "2026-06-24",
        MODEL_PVO_SOURCE,
        report["semantic_output_hash"],
        report["provenance_hash"],
    )
    joinable = store.get_joinable_entries(
        "2026-06-24",
        MODEL_PVO_SOURCE,
        report["semantic_output_hash"],
        report["provenance_hash"],
    )
    assert len(raw) == 4
    assert len(joinable) == 2
    assert {row["player_key"] for row in joinable} == {
        "sleeper:9509",
        "sleeper:6786",
    }
    assert any(
        row["player_key"].startswith(
            f"unresolved:{report['semantic_output_hash']}:3:"
        )
        for row in raw
    )
    assert all("market_overlay" not in row and "divergence" not in row for row in raw)


def test_capture_writes_prediction_snapshot_companion_row_from_same_pvo_row(
    tmp_path,
) -> None:
    from src.dynasty_genius.capture.prediction_snapshot_store import (
        PredictionSnapshotStore,
    )

    artifacts = _artifact_bytes()
    db_path = tmp_path / "model_forward.db"

    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "ok"
    snapshot = PredictionSnapshotStore(db_path).read_snapshot(
        {
            "capture_date": "2026-06-24",
            "source": MODEL_PVO_SOURCE,
            "semantic_output_hash": report["semantic_output_hash"],
            "provenance_hash": report["provenance_hash"],
            "player_key": "sleeper:9509",
        }
    )
    assert snapshot is not None
    if hasattr(snapshot, "model_dump"):
        snapshot = snapshot.model_dump()
    elif not isinstance(snapshot, dict):
        snapshot = dict(snapshot.__dict__)
    assert snapshot["projection_2y"] == pytest.approx(17.25)
    assert set(snapshot["utilization"]) == {
        "snap_share",
        "route_participation",
        "target_share_nfl",
        "air_yards_share",
        "weighted_opportunity",
        "yprr",
        "tprr",
    }
    assert snapshot["utilization"]["snap_share"] == {
        "value": pytest.approx(0.71),
        "role": "model_input",
    }
    assert snapshot["utilization"]["route_participation"] == {
        "value": pytest.approx(0.64),
        "role": "diagnostic_only",
    }
    assert snapshot["utilization"]["weighted_opportunity"] == {
        "value": pytest.approx(0.79),
        "role": "diagnostic_only",
    }
    assert snapshot["utilization"]["yprr"] == {
        "value": pytest.approx(2.19),
        "role": "diagnostic_only",
    }
    assert snapshot["utilization"]["tprr"] == {
        "value": pytest.approx(0.22),
        "role": "diagnostic_only",
    }
    assert snapshot["utilization"]["target_share_nfl"] == {
        "value": pytest.approx(0.18),
        "role": "diagnostic_only",
    }
    assert snapshot["source_hash"] == report["provenance"]["feature_csv"]["sha256"]
    assert snapshot["source_hash"] == _sha(artifacts[ENGINE_B_FEATURE_CSV_PATH])


def test_prediction_snapshot_roles_are_position_aware_for_receiver_model_inputs(
    tmp_path,
) -> None:
    from src.dynasty_genius.capture.prediction_snapshot_store import (
        PredictionSnapshotStore,
    )

    wr_row = _model_row(
        sleeper_id="1111",
        dg_player_id="00-TEST-WR",
        name="Wide Receiver",
        position="WR",
        engine_path="ENGINE_B",
        score=77.7,
        projection_2y=12.5,
    )
    pvo = _pvo_artifact()
    pvo["players"] = [wr_row]
    feature_csv = (
        b"player_id,season,feature_season,position,training_eligible,snap_share,"
        b"route_participation,target_share_nfl,air_yards_share,"
        b"weighted_opportunity,yprr,tprr\n"
        b"00-TEST-WR,2025,2025,WR,false,0.82,0.91,0.27,0.44,0.713,2.61,0.29\n"
    )
    artifacts = _artifact_bytes(
        {
            PVO_PATH: _json_bytes(pvo),
            ENGINE_B_FEATURE_CSV_PATH: feature_csv,
        }
    )
    db_path = tmp_path / "model_forward.db"

    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    snapshot = PredictionSnapshotStore(db_path).read_snapshot(
        {
            "capture_date": "2026-06-24",
            "source": MODEL_PVO_SOURCE,
            "semantic_output_hash": report["semantic_output_hash"],
            "provenance_hash": report["provenance_hash"],
            "player_key": "sleeper:1111",
        }
    )
    assert snapshot is not None
    assert snapshot["utilization"]["weighted_opportunity"] == {
        "value": pytest.approx(0.713),
        "role": "model_input",
    }
    assert snapshot["utilization"]["yprr"]["role"] == "model_input"
    assert snapshot["utilization"]["tprr"]["role"] == "model_input"
    assert snapshot["utilization"]["route_participation"] == {
        "value": pytest.approx(0.91),
        "role": "diagnostic_only",
    }


def test_production_cli_path_threads_resolved_feature_source_hash_to_companion(
    tmp_path, monkeypatch
) -> None:
    import src.dynasty_genius.capture.model_forward_capture_driver as driver
    from src.dynasty_genius.capture.prediction_snapshot_store import (
        PredictionSnapshotStore,
    )

    resolved = _fixture_feature_source()
    monkeypatch.setattr(driver, "resolve_feature_source", lambda **_: resolved)
    artifacts = _artifact_bytes()
    db_path = tmp_path / "model_forward.db"

    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=None,
    )

    snapshot = PredictionSnapshotStore(db_path).read_snapshot(
        {
            "capture_date": "2026-06-24",
            "source": MODEL_PVO_SOURCE,
            "semantic_output_hash": report["semantic_output_hash"],
            "provenance_hash": report["provenance_hash"],
            "player_key": "sleeper:9509",
        }
    )
    assert snapshot is not None
    assert snapshot["source_hash"] == report["provenance"]["feature_csv"]["sha256"]
    assert snapshot["source_hash"] is not None


def test_unmatched_feature_source_key_records_null_util_with_explicit_status(
    tmp_path,
) -> None:
    from src.dynasty_genius.capture.prediction_snapshot_store import (
        PredictionSnapshotStore,
    )

    pvo = _pvo_artifact()
    pvo["players"][0]["dg_player_id"] = "dg-not-gsis-shaped"
    artifacts = _artifact_bytes({PVO_PATH: _json_bytes(pvo)})
    db_path = tmp_path / "model_forward.db"

    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    snapshot = PredictionSnapshotStore(db_path).read_snapshot(
        {
            "capture_date": "2026-06-24",
            "source": MODEL_PVO_SOURCE,
            "semantic_output_hash": report["semantic_output_hash"],
            "provenance_hash": report["provenance_hash"],
            "player_key": "sleeper:9509",
        }
    )
    assert snapshot is not None
    assert snapshot["util_snapshot_status"] == "missing_feature_row"
    assert all(
        field_snapshot["value"] is None
        for field_snapshot in snapshot["utilization"].values()
    )


def test_absent_feature_source_column_records_null_util_with_explicit_status(
    tmp_path,
) -> None:
    from src.dynasty_genius.capture.prediction_snapshot_store import (
        PredictionSnapshotStore,
    )

    feature_csv = (
        b"player_id,season,feature_season,position,training_eligible,snap_share,"
        b"target_share_nfl,air_yards_share,weighted_opportunity,yprr,tprr\n"
        b"00-TEST-RB,2025,2025,RB,false,0.71,0.18,0.08,0.79,2.19,0.22\n"
    )
    artifacts = _artifact_bytes({ENGINE_B_FEATURE_CSV_PATH: feature_csv})
    db_path = tmp_path / "model_forward.db"

    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    snapshot = PredictionSnapshotStore(db_path).read_snapshot(
        {
            "capture_date": "2026-06-24",
            "source": MODEL_PVO_SOURCE,
            "semantic_output_hash": report["semantic_output_hash"],
            "provenance_hash": report["provenance_hash"],
            "player_key": "sleeper:9509",
        }
    )
    assert snapshot is not None
    assert snapshot["util_snapshot_status"] == "partial_missing_util_columns"
    assert snapshot["utilization"]["snap_share"]["value"] == pytest.approx(0.71)
    assert snapshot["utilization"]["route_participation"] == {
        "value": None,
        "role": "diagnostic_only",
    }


def test_companion_write_failure_rolls_back_core_capture_row(
    tmp_path, monkeypatch
) -> None:
    import src.dynasty_genius.capture.model_forward_capture_driver as driver

    class FailingPredictionSnapshotStore:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def append_snapshot(self, row: dict[str, Any], *, conn=None) -> None:
            assert conn is not None
            raise RuntimeError("forced companion failure")

    monkeypatch.setattr(
        driver,
        "PredictionSnapshotStore",
        FailingPredictionSnapshotStore,
        raising=False,
    )
    db_path = tmp_path / "model_forward.db"

    try:
        report = capture_model_pvo_snapshot(
            db_path=db_path,
            report_path=None,
            pvo_artifact_path=PVO_PATH,
            coverage_artifact_path=COVERAGE_PATH,
            read_artifact=_reader(_artifact_bytes()),
            now_fn=_now(),
            git_sha_fn=lambda: "git-sha",
            feature_source=_fixture_feature_source(),
        )
        assert report["status"] == "aborted"
        assert "companion" in report["aborted_reason"]
    except RuntimeError as exc:
        assert "forced companion failure" in str(exc)

    store = ModelForwardCaptureStore(db_path)
    assert store.get_raw_entries(
        "2026-06-24",
        MODEL_PVO_SOURCE,
        "semantic-output-does-not-matter",
        "provenance-does-not-matter",
    ) == []
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM model_forward_capture_raw"
        ).fetchone()[0] == 0


def test_semantic_and_provenance_hashes_ignore_volatile_timestamps_and_git_sha(
    tmp_path,
) -> None:
    base = _artifact_bytes()
    changed_pvo = _json_bytes(
        _pvo_artifact(
            captured_at="2026-06-24T12:00:00+00:00",
            volatile_suffix="b",
        )
    )

    report1 = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(base),
        now_fn=_now(24),
        git_sha_fn=lambda: "git-sha-a",
        feature_source=_fixture_feature_source(),
    )
    report2 = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader({**base, PVO_PATH: changed_pvo}),
        now_fn=_now(25),
        git_sha_fn=lambda: "git-sha-b",
        feature_source=_fixture_feature_source(),
    )

    assert report1["status"] == "ok"
    assert report2["status"] == "ok"
    assert report1["artifact_sha256"] != report2["artifact_sha256"]
    assert report1["semantic_output_hash"] == report2["semantic_output_hash"]
    assert report1["provenance_hash"] == report2["provenance_hash"]
    assert report2["vintage_changed"] is False
    assert report2["provenance"]["git_sha"] == "git-sha-b"


@pytest.mark.parametrize(
    ("pvo_bytes", "reason"),
    [
        (b"{not-json", "malformed_artifact"),
        (_json_bytes({"captured_at": "2026-06-23T12:00:00+00:00", "players": []}), "empty_artifact"),
    ],
)
def test_missing_malformed_or_empty_artifact_aborts_without_store_write(
    tmp_path, pvo_bytes: bytes, reason: str
) -> None:
    artifacts = _artifact_bytes({PVO_PATH: pvo_bytes})

    report = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == reason
    assert report["decision_supported"] is False
    store = ModelForwardCaptureStore(tmp_path / "model_forward.db")
    assert store.get_raw_entries(
        "2026-06-24", MODEL_PVO_SOURCE, "anything", "anything"
    ) == []


def test_required_model_provenance_missing_aborts_before_write(tmp_path) -> None:
    artifacts = _artifact_bytes()
    del artifacts[ENGINE_B_MANIFEST_PATH]

    report = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert "required_provenance" in report["aborted_reason"]
    store = ModelForwardCaptureStore(tmp_path / "model_forward.db")
    assert store.get_raw_entries(
        "2026-06-24", MODEL_PVO_SOURCE, "anything", "anything"
    ) == []


@pytest.mark.parametrize(
    ("missing_key", "reason_fragment"),
    [
        (
            "sleeper_snapshot_hash",
            "row_lineage_sleeper_snapshot_hash",
        ),
        ("governance_version", "row_lineage_governance_version"),
    ],
)
def test_missing_model_supported_row_lineage_aborts_before_write(
    tmp_path, missing_key: str, reason_fragment: str
) -> None:
    pvo = _pvo_artifact()
    del pvo["players"][0]["lineage"][missing_key]
    artifacts = _artifact_bytes({PVO_PATH: _json_bytes(pvo)})

    report = capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert "required_provenance" in report["aborted_reason"]
    assert reason_fragment in report["aborted_reason"]
    store = ModelForwardCaptureStore(tmp_path / "model_forward.db")
    assert store.get_raw_entries(
        "2026-06-24", MODEL_PVO_SOURCE, "anything", "anything"
    ) == []
