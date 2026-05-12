"""Engine B Service Tests.

Verifies model loading, prediction logic, and experimental position caveats.
Uses a mocked model bundle to avoid dependency on real artifacts.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.impute import SimpleImputer

from app.services.engine_b_service import EngineBService, predict_player_season
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_EXPERIMENTAL_POSITIONS

@pytest.fixture
def mock_bundle():
    """Create a dummy model bundle for testing."""
    features = ["age", "ppg_t", "weighted_opportunity"]
    model = Ridge()
    # Train on data that ensures ppg_t is the primary driver
    X = np.array([
        [20, 5.0, 0.1],
        [21, 10.0, 0.2],
        [22, 15.0, 0.3],
        [23, 20.0, 0.4],
        [24, 25.0, 0.5]
    ])
    y = np.array([5.0, 10.0, 15.0, 20.0, 25.0])
    model.fit(X, y)
    
    imputer = SimpleImputer(strategy="mean")
    imputer.fit(X)
    
    return {
        "model": model,
        "imputer": imputer,
        "features": features
    }

@patch("app.services.engine_b_service.EngineBService._load_model")
def test_predict_player_season_returns_required_keys(mock_load, mock_bundle):
    mock_load.return_value = mock_bundle
    
    player_features = {
        "player_id": "00-12345",
        "position": "WR",
        "age": 24,
        "ppg_t": 15.5,
        "weighted_opportunity": 0.6,
        "feature_season": 2023
    }
    
    res = predict_player_season(player_features)
    
    assert "predicted_avg_ppg_t1_t2" in res
    assert res["engine"] == "engine_b_v1"
    assert res["feature_season"] == 2023
    assert res["position"] == "WR"
    assert res["decision_supported"] is False
    assert "caveats" in res

@patch("app.services.engine_b_service.EngineBService._load_model")
def test_te_prediction_is_experimental(mock_load, mock_bundle):
    mock_load.return_value = mock_bundle
    
    player_features = {"position": "TE", "age": 25, "ppg_t": 8.0}
    res = predict_player_season(player_features)
    
    assert res["experimental"] is True
    assert "engine_b_does_not_beat_baseline_for_this_position" in res["caveats"]

@patch("app.services.engine_b_service.EngineBService._load_model")
def test_non_te_prediction_is_not_experimental(mock_load, mock_bundle):
    mock_load.return_value = mock_bundle
    
    for pos in ["QB", "RB", "WR"]:
        player_features = {"position": pos, "age": 25, "ppg_t": 15.0}
        res = predict_player_season(player_features)
        assert res["experimental"] is False
        assert "engine_b_does_not_beat_baseline_for_this_position" not in res["caveats"]

@patch("app.services.engine_b_service.EngineBService._load_model")
def test_missing_features_handled_by_imputer(mock_load, mock_bundle):
    mock_load.return_value = mock_bundle
    
    # Missing ppg_t and weighted_opportunity
    player_features = {"position": "WR", "age": 22}
    res = predict_player_season(player_features)
    
    assert res["predicted_avg_ppg_t1_t2"] is not None

@patch("app.services.engine_b_service.EngineBService._load_model")
@patch("app.services.engine_b_service.pd.read_csv")
def test_score_inference_partition_is_sorted(mock_read, mock_load, mock_bundle):
    mock_load.return_value = mock_bundle
    
    # Mock dataset with 3 inference rows
    mock_df = pd.DataFrame([
        {"player_id": "P1", "position": "WR", "age": 22, "ppg_t": 20.0, "training_eligible": False},
        {"player_id": "P2", "position": "WR", "age": 22, "ppg_t": 5.0, "training_eligible": False},
        {"player_id": "P3", "position": "WR", "age": 22, "ppg_t": 12.0, "training_eligible": False},
    ])
    mock_read.return_value = mock_df
    
    service = EngineBService()
    scores = service.score_inference_partition()
    
    assert len(scores) == 3
    # Verify descending sort
    vals = [s["predicted_avg_ppg_t1_t2"] for s in scores]
    assert vals == sorted(vals, reverse=True)
    assert scores[0]["player_id"] == "P1" # Highest ppg_t should have highest pred in this simple model

@patch("app.services.engine_b_service.EngineBService._load_model")
def test_predict_player_season_fails_gracefully_on_missing_model(mock_load):
    mock_load.return_value = {}
    
    res = predict_player_season({"position": "WR"})
    assert res == {"error": "model_not_found"}

def test_engine_b_service_validates_contract_on_load(mock_bundle):
    # Create a bundle with a prohibited feature
    bad_bundle = mock_bundle.copy()
    bad_bundle["features"] = ["age", "ktc_value"] # Prohibited
    
    # We'll mock the inner logic of _load_model by patching the dependencies of the method
    # and using a helper to bypass the read-only Path attributes.
    with patch("app.services.engine_b_service.pickle.load", return_value=bad_bundle):
        with patch("app.services.engine_b_service._MODELS_DIR") as mock_dir:
            # Setup mock directory structure
            mock_run = MagicMock()
            mock_run.is_dir.return_value = True
            mock_run.__truediv__.return_value = MagicMock()
            mock_run.__truediv__.return_value.exists.return_value = True
            
            mock_dir.exists.return_value = True
            mock_dir.iterdir.return_value = [mock_run]
                
            service = EngineBService()
            service._model_bundle = None # Force reload
            bundle = service._load_model()
            
            assert bundle == {} # Should return empty dict on validation failure
