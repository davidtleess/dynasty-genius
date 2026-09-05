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

def test_counter_argument_present_for_a_top_asset_rookie():
    """A rookie in the top fifth of his position's scale gets the mandatory
    counter-argument (Constitution Rule 4).

    DG-159 changed WHO that is, and the change is real rather than cosmetic. The
    threshold used to be a flat 80 on a scale where every position's ceiling was 100,
    including the rookie engine's own four ceilings — so a rookie was ranked against
    other rookies and a veteran against other veterans, and the same number meant
    different football. It is now 80% of the position's real ceiling on the shared
    scale, and both engines are measured against it.

    Measured across the served artifact, the population carrying this argument goes
    57 -> 52. The five it loses are receivers scored by the rookie engine, whose own
    ceiling (12.7 points a game) sits below the receiver position's (14.5) — they were
    never in the top fifth of what a receiver can be, only of what the rookie model
    predicts. A top-four rookie receiver is one of them, which is why this test no
    longer uses one.
    """
    payload = {"name": "Ashton Jeanty", "position": "RB", "pick": 4, "round": 1, "age": 21.8}
    response = client.post("/api/rookies/score", json=payload)
    data = response.json()

    assert data["dynasty_value_score"] is not None
    assert data["counter_argument"] is not None
    assert len(data["counter_argument"]) > 0
