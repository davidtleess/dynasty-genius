from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_score_prospect_returns_pvo_shape():
    """POST /api/rookies/score returns a PVO-shaped response."""
    payload = {
        "name": "Caleb Williams",
        "position": "QB",
        "pick": 1,
        "round": 1,
        "age": 22.1
    }
    response = client.post("/api/rookies/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Required PVO fields
    assert "player_id" in data
    assert data["full_name"] == "Caleb Williams"
    assert data["position"] == "QB"
    assert data["engine_used"].startswith("engine_a")
    assert "model_grade" in data
    assert "signal_completeness" in data
    assert "top_drivers" in data
    assert "caveats" in data
    assert "risk_flags" in data
    assert "counter_argument" in data
    assert data["is_prospect"] is True
    assert data["nfl_draft_pick"] == 1
    assert data["nfl_draft_round"] == 1

def test_score_prospect_retired_fields_absent():
    """The response must NOT contain retired fields."""
    payload = {
        "name": "Caleb Williams",
        "position": "QB",
        "pick": 1,
        "round": 1,
        "age": 22.1
    }
    response = client.post("/api/rookies/score", json=payload)
    data = response.json()
    
    assert "valuation" not in data
    assert "projected_outcome_band" not in data
    assert "confidence" not in data
    assert "dynasty_tier" not in data
    assert "predicted_y24_ppg" not in data

def test_score_class_sorting_and_shape():
    """POST /api/rookies/score-class returns a list sorted by dynasty_value_score desc."""
    payload = [
        {"name": "Player A", "position": "WR", "pick": 10, "round": 1, "age": 21.0},
        {"name": "Player B", "position": "WR", "pick": 1, "round": 1, "age": 21.0},
        {"name": "Player C", "position": "WR", "pick": 50, "round": 2, "age": 22.0}
    ]
    response = client.post("/api/rookies/score-class", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) == 3
    
    scores = [item["dynasty_value_score"] for item in data if item["dynasty_value_score"] is not None]
    assert scores == sorted(scores, reverse=True)
    
    # Check shape of first item
    assert "player_id" in data[0]
    assert "dynasty_value_score" in data[0]

def test_pvo_governance_flags():
    """market_overlay is None and decision_supported is False."""
    payload = {
        "name": "Marvin Harrison Jr.",
        "position": "WR",
        "pick": 4,
        "round": 1,
        "age": 21.8
    }
    response = client.post("/api/rookies/score", json=payload)
    data = response.json()
    
    assert data["market_overlay"] is None
    assert data["decision_supported"] is False

def test_counter_argument_present_when_scored():
    """counter_argument is present when dynasty_value_score is non-null."""
    payload = {
        "name": "Marvin Harrison Jr.",
        "position": "WR",
        "pick": 4,
        "round": 1,
        "age": 21.8
    }
    response = client.post("/api/rookies/score", json=payload)
    data = response.json()
    
    if data["dynasty_value_score"] is not None:
        assert data["counter_argument"] is not None
        assert len(data["counter_argument"]) > 0
