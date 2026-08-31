"""Engine B Service Tests — Phase 6 (v2 position routing + v1 fallback).

Tests cover:
  - v2 per-position routing (QB/RB/WR use v2 artifacts)
  - v1 fallback for non-promoted positions (TE)
  - experimental caveat propagation
  - market-overlay isolation
  - graceful failure on missing model
"""
from __future__ import annotations

import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge

from app.services.engine_b_service import EngineBService, predict_player_season

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_bundle(features: list[str], version: str = "engine_b_v1") -> dict:
    model = Ridge()
    X = np.array([[20, 5.0, 0.1], [21, 10.0, 0.2], [22, 15.0, 0.3],
                  [23, 20.0, 0.4], [24, 25.0, 0.5]])
    y = np.array([5.0, 10.0, 15.0, 20.0, 25.0])
    padded_X = np.zeros((len(X), len(features)))
    for i, _ in enumerate(features):
        if i < X.shape[1]:
            padded_X[:, i] = X[:, i]
    model.fit(padded_X, y)
    imputer = SimpleImputer(strategy="mean")
    imputer.fit(padded_X)
    return {"model": model, "imputer": imputer, "features": features, "version": version}


@pytest.fixture
def mock_bundle():
    return _make_bundle(["age", "ppg_t", "weighted_opportunity"], version="engine_b_v1")


@pytest.fixture
def mock_v2_wr_bundle():
    return _make_bundle(
        ["age", "ppg_t", "weighted_opportunity", "aging_curve_value"],
        version="engine_b_v2_wr",
    )


def _patch_service(v2_bundles: dict, v1_bundle: dict):
    """Context manager that injects bundles into a fresh service instance."""
    svc = EngineBService.__new__(EngineBService)
    svc._loaded = True
    svc._v2_bundles = v2_bundles
    svc._v1_bundle = v1_bundle
    return patch("app.services.engine_b_service.service", svc)


# ── Basic prediction contract ─────────────────────────────────────────────────

def test_predict_player_season_returns_required_keys(mock_bundle):
    with _patch_service(v2_bundles={"WR": mock_bundle}, v1_bundle={}):
        res = predict_player_season({
            "player_id": "00-12345",
            "position": "WR",
            "age": 24,
            "ppg_t": 15.5,
            "weighted_opportunity": 0.6,
            "feature_season": 2023,
        })
    assert "predicted_avg_ppg_t1_t2" in res
    assert res["position"] == "WR"
    assert res["feature_season"] == 2023
    assert res["decision_supported"] is False
    assert "caveats" in res


def test_predict_returns_v2_engine_name_for_promoted_position(mock_v2_wr_bundle):
    with _patch_service(v2_bundles={"WR": mock_v2_wr_bundle}, v1_bundle={}):
        res = predict_player_season({"position": "WR", "age": 25, "ppg_t": 15.0})
    assert res["engine"] == "engine_b_v2_wr"


def test_predict_falls_back_to_v1_for_unpromoted_position(mock_bundle):
    v1 = _make_bundle(["age", "ppg_t"], version="engine_b_v1")
    with _patch_service(v2_bundles={}, v1_bundle=v1):
        res = predict_player_season({"position": "TE", "age": 27, "ppg_t": 9.0})
    assert res["engine"] == "engine_b_v1"


# ── TE experimental caveat ────────────────────────────────────────────────────

def test_te_prediction_is_experimental(mock_bundle):
    v1 = _make_bundle(["age", "ppg_t", "weighted_opportunity"], version="engine_b_v1")
    with _patch_service(v2_bundles={}, v1_bundle=v1):
        res = predict_player_season({"position": "TE", "age": 25, "ppg_t": 8.0})
    assert res["experimental"] is True
    assert "engine_b_does_not_beat_baseline_for_this_position" in res["caveats"]


def test_non_te_prediction_not_experimental(mock_bundle):
    v2 = {pos: _make_bundle(["age", "ppg_t"], version=f"engine_b_v2_{pos.lower()}")
          for pos in ("QB", "RB", "WR")}
    with _patch_service(v2_bundles=v2, v1_bundle={}):
        for pos in ("QB", "RB", "WR"):
            res = predict_player_season({"position": pos, "age": 25, "ppg_t": 15.0})
            assert res["experimental"] is False
            assert "engine_b_does_not_beat_baseline_for_this_position" not in res["caveats"]


# ── v2 position routing ───────────────────────────────────────────────────────

def test_v2_qb_bundle_used_for_qb_position():
    qb_bundle = _make_bundle(
        ["age", "ppg_t", "epa_per_dropback"], version="engine_b_v2_qb"
    )
    with _patch_service(v2_bundles={"QB": qb_bundle}, v1_bundle={}):
        res = predict_player_season({"position": "QB", "age": 28, "ppg_t": 20.0})
    assert res["engine"] == "engine_b_v2_qb"
    assert res["position"] == "QB"


def test_v2_routing_uses_correct_bundle_per_position():
    bundles = {
        pos: _make_bundle(["age", "ppg_t"], version=f"engine_b_v2_{pos.lower()}")
        for pos in ("QB", "RB", "WR")
    }
    v1 = _make_bundle(["age", "ppg_t"], version="engine_b_v1")
    with _patch_service(v2_bundles=bundles, v1_bundle=v1):
        for pos in ("QB", "RB", "WR"):
            res = predict_player_season({"position": pos, "age": 25, "ppg_t": 15.0})
            assert res["engine"] == f"engine_b_v2_{pos.lower()}", f"Wrong engine for {pos}"
        te_res = predict_player_season({"position": "TE", "age": 25, "ppg_t": 9.0})
        assert te_res["engine"] == "engine_b_v1"


# ── Resilience ────────────────────────────────────────────────────────────────

def test_predict_fails_gracefully_on_missing_model():
    with _patch_service(v2_bundles={}, v1_bundle={}):
        res = predict_player_season({"position": "WR"})
    assert res == {"error": "model_not_found"}


def test_missing_features_handled_by_imputer(mock_bundle):
    with _patch_service(v2_bundles={"WR": mock_bundle}, v1_bundle={}):
        res = predict_player_season({"position": "WR", "age": 22})
    assert "predicted_avg_ppg_t1_t2" in res


# ── Inference partition sorting ───────────────────────────────────────────────

@patch("app.services.engine_b_service.pd.read_csv")
def test_score_inference_partition_is_sorted(mock_read, mock_bundle):
    mock_read.return_value = pd.DataFrame([
        {"player_id": "P1", "position": "WR", "age": 22, "ppg_t": 20.0,
         "weighted_opportunity": 0.8, "training_eligible": False},
        {"player_id": "P2", "position": "WR", "age": 22, "ppg_t": 5.0,
         "weighted_opportunity": 0.2, "training_eligible": False},
        {"player_id": "P3", "position": "WR", "age": 22, "ppg_t": 12.0,
         "weighted_opportunity": 0.5, "training_eligible": False},
    ])
    svc = EngineBService.__new__(EngineBService)
    svc._loaded = True
    svc._v2_bundles = {"WR": mock_bundle}
    svc._v1_bundle = {}
    with patch("app.services.engine_b_service.service", svc):
        scores = svc.score_inference_partition()
    assert len(scores) == 3
    vals = [s["predicted_avg_ppg_t1_t2"] for s in scores]
    assert vals == sorted(vals, reverse=True)


# ── Contract validation on load ───────────────────────────────────────────────

def test_service_rejects_bundle_with_prohibited_feature(tmp_path, monkeypatch):
    """_load_v2_bundles must reject any artifact whose features violate the contract.

    This test previously asserted its own title and then did not test it: it built four
    mocks, never called _load_v2_bundles, and asserted validate_no_prohibited_features
    directly -- which would pass whatever the service did. Rewritten 2026-08-31 to
    exercise the real load path, which is possible now that a validation failure raises
    rather than being logged and skipped.
    """
    import pickle as _pickle

    import app.services.engine_b_service as mod

    run_dir = tmp_path / "app/data/models/engine_b/runs/fake"
    run_dir.mkdir(parents=True)
    artifact = run_dir / "wr_v2.pkl"
    artifact.write_bytes(
        _pickle.dumps(
            {
                "model": Ridge(),
                "imputer": SimpleImputer(),
                "features": ["age", "ktc_value"],
                "version": "engine_b_v2_wr",
            }
        )
    )
    manifest = tmp_path / "v2_manifest.json"
    manifest.write_text(
        json.dumps({"WR": "app/data/models/engine_b/runs/fake/wr_v2.pkl"})
    )
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", manifest)
    monkeypatch.setattr(mod, "_ROOT", tmp_path)

    svc = EngineBService.__new__(EngineBService)
    with pytest.raises(mod.EngineBManifestUnavailableError):
        svc._load_v2_bundles()


# ── The manifest refusal (David's ruling, 2026-08-31) ─────────────────────────────
# "if the model can't read the file, then it needs to be a hard error."
#
# This class of failure previously resolved to {} and fell through
# `self._v2_bundles.get(position) or self._v1_bundle` to the SUPERSEDED v1 model for
# every position, silently. That is how the land gate spent weeks validating against a
# build the repo documents as not beating a naive baseline.

def _fresh_service():
    from app.services.engine_b_service import EngineBService as _S
    return _S.__new__(_S)


def test_absent_manifest_refuses_instead_of_serving_v1(tmp_path, monkeypatch):
    import app.services.engine_b_service as mod
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", tmp_path / "not_here.json")
    with pytest.raises(mod.EngineBManifestUnavailableError, match="not found"):
        _fresh_service()._load_v2_bundles()


def test_unreadable_manifest_refuses_instead_of_serving_v1(tmp_path, monkeypatch):
    import app.services.engine_b_service as mod
    bad = tmp_path / "v2_manifest.json"
    bad.write_text("{ this is not json")
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", bad)
    with pytest.raises(mod.EngineBManifestUnavailableError, match="could not be read"):
        _fresh_service()._load_v2_bundles()


def test_a_manifest_naming_a_missing_model_is_a_broken_deployment(tmp_path, monkeypatch):
    """A manifest that promotes a position to a pickle which is not on disk is lying.
    Serving v1 in that case is the silent-downgrade defect wearing a different hat."""
    import app.services.engine_b_service as mod
    manifest = tmp_path / "v2_manifest.json"
    manifest.write_text(json.dumps({"WR": "app/data/models/engine_b/runs/gone/wr_v2.pkl"}))
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", manifest)
    monkeypatch.setattr(mod, "_ROOT", tmp_path)
    with pytest.raises(mod.EngineBManifestUnavailableError, match="does not exist"):
        _fresh_service()._load_v2_bundles()


def test_a_position_the_manifest_does_not_promote_still_falls_back_to_v1(
    tmp_path, monkeypatch
):
    """The ONE fallback that survives, and it must. train_engine_b writes entries only
    for promoted positions, so a null is a deliberate statement that v1 is right for it
    -- not a failure to read anything."""
    import app.services.engine_b_service as mod
    manifest = tmp_path / "v2_manifest.json"
    manifest.write_text(json.dumps({"TE": None}))
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", manifest)
    monkeypatch.setattr(mod, "_ROOT", tmp_path)

    assert _fresh_service()._load_v2_bundles() == {}


def test_a_failed_load_does_not_strand_the_service_answering_from_an_empty_map(
    tmp_path, monkeypatch
):
    """_load() used to set _loaded=True BEFORE loading. A raise then left a singleton
    that answered every later call from an empty v2 map -- silently reinstating the very
    v1 fallback this refusal exists to prevent."""
    import app.services.engine_b_service as mod
    monkeypatch.setattr(mod, "_V2_MANIFEST_PATH", tmp_path / "not_here.json")
    svc = _fresh_service()
    svc._loaded = False
    svc._v2_bundles = {}
    svc._v1_bundle = {}

    with pytest.raises(mod.EngineBManifestUnavailableError):
        svc._load()
    assert svc._loaded is False, "a failed load must not mark the service loaded"
