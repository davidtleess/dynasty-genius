from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pandas as pd
import pytest


def _write_csv(path: Path, player_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "player_id": player_id,
                "feature_season": 2025,
                "training_eligible": False,
                "snap_share": 0.75,
            }
        ]
    ).to_csv(path, index=False)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ready_marker(runtime_path: Path, *, status: str = "ok") -> dict:
    payload = {
        "status": status,
        "runtime_sha256": _sha(runtime_path),
        "source_as_of": "2025",
        "decision_supported": False,
    }
    runtime_path.with_name("engine_b_features_runtime.ready.json").write_text(
        json.dumps(payload, sort_keys=True)
    )
    return payload


def test_resolve_feature_source_prefers_ready_runtime_and_stamps_metadata(
    tmp_path: Path,
) -> None:
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")
    seed = _write_csv(tmp_path / "seed" / "engine_b_features_v2.csv", "seed-player")
    runtime_dir = tmp_path / "features_runtime"
    runtime = _write_csv(runtime_dir / "engine_b_features_runtime.csv", "runtime-player")
    ready = _ready_marker(runtime)

    resolved = feature_source.resolve_feature_source(
        seed_path=seed,
        runtime_dir=runtime_dir,
    )

    assert resolved.path == runtime
    assert resolved.source_kind == "runtime"
    assert resolved.sha256 == _sha(runtime)
    assert resolved.source_as_of == ready["source_as_of"]
    assert resolved.ready is True
    assert resolved.published_seed_sha256 == _sha(seed)
    assert resolved.metadata()["feature_source_kind"] == "runtime"
    assert resolved.metadata()["feature_csv_sha256"] == _sha(runtime)
    assert resolved.metadata()["published_seed_sha256"] == _sha(seed)
    assert resolved.metadata()["decision_supported"] is False


def test_resolve_feature_source_falls_back_to_seed_only_when_runtime_absent(
    tmp_path: Path,
) -> None:
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")
    seed = _write_csv(tmp_path / "seed" / "engine_b_features_v2.csv", "seed-player")

    resolved = feature_source.resolve_feature_source(
        seed_path=seed,
        runtime_dir=tmp_path / "features_runtime",
    )

    assert resolved.path == seed
    assert resolved.source_kind == "seed"
    assert resolved.sha256 == _sha(seed)
    assert resolved.ready is True
    assert resolved.published_seed_sha256 == _sha(seed)


@pytest.mark.parametrize(
    "ready_payload",
    [
        None,
        {"status": "blocked", "runtime_sha256": "wrong", "decision_supported": False},
        {"status": "ok", "runtime_sha256": "not-the-runtime-hash", "decision_supported": False},
    ],
)
def test_resolve_feature_source_fail_closed_when_runtime_present_but_not_ready(
    tmp_path: Path,
    ready_payload,
) -> None:
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")
    seed = _write_csv(tmp_path / "seed" / "engine_b_features_v2.csv", "seed-player")
    runtime_dir = tmp_path / "features_runtime"
    runtime = _write_csv(runtime_dir / "engine_b_features_runtime.csv", "runtime-player")
    if ready_payload is not None:
        runtime.with_name("engine_b_features_runtime.ready.json").write_text(
            json.dumps(ready_payload, sort_keys=True)
        )

    with pytest.raises(feature_source.FeatureSourceNotReadyError):
        feature_source.resolve_feature_source(seed_path=seed, runtime_dir=runtime_dir)


def test_all_engine_b_consumers_route_through_shared_feature_source_helper() -> None:
    """C2 regression: no consumer may read engine_b_features_v2.csv directly anymore."""
    engine_b_service = importlib.import_module("app.services.engine_b_service")
    pvo_batch = importlib.import_module("scripts.build_universe_pvo_batch")
    capture_driver = importlib.import_module(
        "src.dynasty_genius.capture.model_forward_capture_driver"
    )

    service_source = Path(engine_b_service.__file__).read_text()
    pvo_source = Path(pvo_batch.__file__).read_text()
    capture_source = Path(capture_driver.__file__).read_text()

    assert "resolve_feature_source" in service_source
    assert "resolve_feature_source" in pvo_source
    assert "resolve_feature_source" in capture_source

    assert "pd.read_csv(_DATASET_PATH)" not in service_source
    assert "_load_engine_b_feature_rows(feature_source" in pvo_source
    assert "score_inference_partition(feature_source" in pvo_source
    assert "ENGINE_B_FEATURE_CSV_PATH = Path(\"app/data/training/engine_b_features_v2.csv\")" not in capture_source


def test_pvo_batch_uses_single_resolved_feature_source_for_rows_and_predictions() -> None:
    """Direct row-read and score_inference_partition must share the same resolved source."""
    pvo_batch = importlib.import_module("scripts.build_universe_pvo_batch")
    source = Path(pvo_batch.__file__).read_text()

    assert "feature_source = resolve_feature_source" in source
    assert "_load_engine_b_feature_rows(feature_source.path)" in source
    assert "score_inference_partition(feature_source=feature_source)" in source
    assert "feature_source.metadata()" in source


def test_model_forward_capture_provenance_stamps_resolved_feature_source_hash() -> None:
    driver = importlib.import_module("src.dynasty_genius.capture.model_forward_capture_driver")
    source = Path(driver.__file__).read_text()

    assert "resolve_feature_source" in source
    assert "feature_source_kind" in source
    assert "feature_csv_sha256" in source
    assert "published_seed_sha256" in source
    assert "generated_at" not in source[source.find("provenance_hash") : source.find("return _persist(report)")]


def test_capture_provenance_can_pin_feature_source_independent_of_ambient_runtime(
    tmp_path: Path,
) -> None:
    """T3 hermeticity: injected artifact reads must not depend on local gitignored runtime.

    After the first feature-refresh catch-up, app/data/features_runtime may contain a valid
    runtime CSV. Capture/refresh tests that inject read_artifact fixtures must still be able
    to pin the feature source they are hashing instead of silently depending on ambient
    local state.
    """
    driver = importlib.import_module("src.dynasty_genius.capture.model_forward_capture_driver")
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")

    seed = _write_csv(tmp_path / "seed" / "engine_b_features_v2.csv", "seed-player")
    runtime_dir = tmp_path / "features_runtime"
    runtime = _write_csv(runtime_dir / "engine_b_features_runtime.csv", "runtime-player")
    _ready_marker(runtime)

    pinned = feature_source.ResolvedFeatureSource(
        path=seed,
        source_kind="seed",
        sha256=_sha(seed),
        source_as_of=None,
        ready=True,
        published_seed_sha256=_sha(seed),
    )
    pvo = {
        "schema_version": "universe_pvo_batch.v1",
        "source_snapshot_captured_at": "2026-06-23T11:30:00+00:00",
        "players": [{"valuation": {"engine_path": "ENGINE_B"}}],
    }
    model_path = Path("app/data/models/engine_b/runs/test/rb_v2.pkl")
    data = {
        driver.PRODUCER_PATH: b"producer",
        driver.ENGINE_B_MANIFEST_PATH: json.dumps({"RB": str(model_path)}).encode(),
        model_path: b"model",
        seed: seed.read_bytes(),
    }

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized not in data:
            raise FileNotFoundError(str(normalized))
        return data[normalized]

    subset = driver.resolve_provenance_subset(
        pvo,
        read_artifact=read_artifact,
        feature_source=pinned,
    )

    assert subset["engine_b"]["feature_csv_sha256"] == _sha(seed)


def test_pvo_refresh_hashes_can_pin_feature_source_independent_of_ambient_runtime(
    tmp_path: Path,
) -> None:
    """The PVO refresh runner also hashes provenance through injected readers.

    It must expose the same pinned feature-source seam, otherwise the local suite can start
    failing after the first gitignored runtime publish even though the fixture intentionally
    hashes the committed seed bytes.
    """
    runner = importlib.import_module("scripts.run_pvo_refresh")
    driver = importlib.import_module("src.dynasty_genius.capture.model_forward_capture_driver")
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")

    seed = _write_csv(tmp_path / "seed" / "engine_b_features_v2.csv", "seed-player")
    runtime_dir = tmp_path / "features_runtime"
    runtime = _write_csv(runtime_dir / "engine_b_features_runtime.csv", "runtime-player")
    _ready_marker(runtime)

    pinned = feature_source.ResolvedFeatureSource(
        path=seed,
        source_kind="seed",
        sha256=_sha(seed),
        source_as_of=None,
        ready=True,
        published_seed_sha256=_sha(seed),
    )
    model_path = Path("app/data/models/engine_b/runs/test/rb_v2.pkl")
    data = {
        driver.PRODUCER_PATH: b"producer",
        driver.ENGINE_B_MANIFEST_PATH: json.dumps({"RB": str(model_path)}).encode(),
        model_path: b"model",
        seed: seed.read_bytes(),
    }

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized not in data:
            raise FileNotFoundError(str(normalized))
        return data[normalized]

    pvo = {
        "schema_version": "universe_pvo_batch.v1",
        "source_snapshot_captured_at": "2026-06-23T11:30:00+00:00",
        "players": [{"valuation": {"engine_path": "ENGINE_B"}}],
    }
    hashes = runner._artifact_hashes(
        json.dumps(pvo).encode(),
        read_artifact=read_artifact,
        feature_source=pinned,
    )

    assert hashes["provenance_hash"]


def test_what_changed_report_and_api_expose_model_feature_freshness() -> None:
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    models = importlib.import_module("app.api.routes.league_what_changed_models")
    report_source = Path(report.__file__).read_text()

    assert "model_feature_freshness" in report_source
    assert "feature_source_kind" in report_source
    assert "feature_csv_sha256" in report_source
    assert hasattr(models, "WhatChangedModelFeatureFreshness")
    field = models.WhatChangedModelSection.model_fields["feature_freshness"]
    assert field.annotation == models.WhatChangedModelFeatureFreshness | None

    response = models.WhatChangedResponse.model_validate(
        {
            "schema_version": models.SCHEMA_VERSION,
            "generated_at": "2026-06-25T12:00:00+00:00",
            "decision_supported": False,
            "overall_status": "degraded",
            "daily_diff": {
                "decision_supported": False,
                "overall_status": "degraded",
                "market": {
                    "status": "insufficient_history",
                    "decision_supported": False,
                    "market_source": "fc_native",
                },
                "model": {
                    "status": "insufficient_history",
                    "decision_supported": False,
                    "comparison_window": {"status": "insufficient_history"},
                    "feature_freshness": {
                        "decision_supported": False,
                        "feature_source_kind": "runtime",
                        "feature_csv_sha256": "abc123",
                        "source_as_of": "2025",
                        "feature_csv_path": "app/data/features_runtime/engine_b_features_runtime.csv",
                        "published_seed_sha256": "seed123",
                    },
                },
            },
            "structural_context": {
                "status": "ok",
                "decision_supported": False,
                "current_not_delta": True,
                "sections": {
                    name: {
                        "status": "ok",
                        "decision_supported": False,
                        "current_not_delta": True,
                    }
                    for name in (
                        "team_posture",
                        "team_value",
                        "league_opportunity",
                        "drop_pressure",
                        "sleeper_snapshot",
                    )
                },
            },
        }
    )
    assert response.daily_diff.model.feature_freshness is not None
    assert response.daily_diff.model.feature_freshness.decision_supported is False


def test_what_changed_feature_freshness_discloses_not_ready_runtime(monkeypatch) -> None:
    """Freshness labels must not silently disappear when the runtime is not ready.

    The T3 disclosure contract is what keeps the daily login surface honest: a present but
    unverified runtime must be visible as not-ready metadata, not omitted as None.
    """
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    feature_source = importlib.import_module("src.dynasty_genius.features.feature_source")
    models = importlib.import_module("app.api.routes.league_what_changed_models")

    def not_ready(**_kwargs):
        raise feature_source.FeatureSourceNotReadyError("marker status/hash mismatch")

    monkeypatch.setattr(report, "resolve_feature_source", not_ready)

    freshness = report._model_feature_freshness()

    assert freshness == {
        "decision_supported": False,
        "feature_source_status": "not_ready",
        "feature_source_kind": None,
        "aborted_reason": "marker status/hash mismatch",
    }
    model = models.WhatChangedModelSection.model_validate(
        {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "feature_freshness": freshness,
        }
    )
    assert model.feature_freshness is not None
    assert model.feature_freshness.decision_supported is False


def test_what_changed_feature_freshness_rejects_fabricated_statuses() -> None:
    """DTO freshness fields are closed to the honest source/status vocabulary."""
    models = importlib.import_module("app.api.routes.league_what_changed_models")

    with pytest.raises(Exception):
        models.WhatChangedModelFeatureFreshness.model_validate(
            {
                "decision_supported": False,
                "feature_source_kind": "invented",
                "feature_csv_sha256": "abc123",
            }
        )

    with pytest.raises(Exception):
        models.WhatChangedModelFeatureFreshness.model_validate(
            {
                "decision_supported": False,
                "feature_source_status": "maybe_ready",
                "feature_source_kind": None,
                "aborted_reason": "marker mismatch",
            }
        )
