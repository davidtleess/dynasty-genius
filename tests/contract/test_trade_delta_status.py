from app.services.trade_analyzer import analyze_trade_pvo


def test_analyze_trade_pvo_shape():
    """Prove analyze_trade_pvo() returns the correct experimental envelope."""
    my_assets = [{"type": "player", "name": "CeeDee Lamb", "position": "WR", "age": 25}]
    their_assets = [{"type": "player", "name": "Breece Hall", "position": "RB", "age": 23}]
    
    response = analyze_trade_pvo(my_assets, their_assets)
    
    assert response["status"] == "experimental"
    assert response["engine"] == "trade_analyzer_pvo_v1"
    assert response["decision_supported"] is False
    assert "delta_status" in response
    assert response["delta_status"] in ["Within_Model_Error", "Likely_Favors_You", "Likely_Favors_Opponent"]
    assert "uncertainty_note" in response
    assert "my_assets" in response
    assert "their_assets" in response
    
    # Banned fields
    for banned in ["verdict", "my_total", "their_total", "difference", "my_assets_scored", "their_assets_scored", "experimental_totals"]:
        assert banned not in response
        
    # Check string banned fields
    banned_strings = ["Strong win", "Win", "Fair", "Loss", "Strong loss"]
    response_str = str(response)
    for s in banned_strings:
        assert s not in response_str

def test_delta_status_within_model_error_picks():
    """Prove Within_Model_Error for picks (insufficient data)."""
    my_assets = [{"type": "pick", "year": 2026, "round": 1}]
    their_assets = [{"type": "pick", "year": 2026, "round": 1}]
    
    response = analyze_trade_pvo(my_assets, their_assets)
    assert response["delta_status"] == "Within_Model_Error"

def test_te_experimental_caveat():
    """Prove TE assets carry the experimental caveat."""
    my_assets = [{"type": "player", "name": "Travis Kelce", "position": "TE", "age": 34}]
    their_assets = []
    
    response = analyze_trade_pvo(my_assets, their_assets)
    te_pvo = response["my_assets"][0]
    assert "engine_b_experimental_v1_fallback" in te_pvo["caveats"]

def test_market_overlay_none():
    """Prove market_overlay is None on all asset PVOs."""
    my_assets = [{"type": "player", "name": "CeeDee Lamb", "position": "WR", "age": 25}]
    their_assets = []
    
    response = analyze_trade_pvo(my_assets, their_assets)
    assert response["my_assets"][0]["market_overlay"] is None

def test_delta_status_likely_favors_you():
    """Prove Likely_Favors_You when my side projects materially higher."""
    # QB RMSE is 4.508. 
    # My side: 20 PPG. Band [15.492, 24.508]
    # Their side: 10 PPG. Band [5.492, 14.508]
    # 15.492 > 14.508, so my_lo > their_hi.
    my_assets = [{
        "type": "player", "name": "QB A", "position": "QB", 
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 20.0, "engine": "test", "caveats": []}
    }]
    their_assets = [{
        "type": "player", "name": "QB B", "position": "QB",
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test", "caveats": []}
    }]
    
    response = analyze_trade_pvo(my_assets, their_assets)
    assert response["delta_status"] == "Likely_Favors_You"

def test_delta_status_within_model_error_overlap():
    """Prove Within_Model_Error when overlap > 50% of narrower width."""
    # WR RMSE is 2.887. Width is 5.774.
    # My side: 10.0. Band [7.113, 12.887]
    # Their side: 11.0. Band [8.113, 13.887]
    # Overlap: [8.113, 12.887]. Width = 12.887 - 8.113 = 4.774.
    # 4.774 / 5.774 = 0.826 > 0.5.
    my_assets = [{
        "type": "player", "name": "WR A", "position": "WR", 
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 10.0, "engine": "test", "caveats": []}
    }]
    their_assets = [{
        "type": "player", "name": "WR B", "position": "WR",
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 11.0, "engine": "test", "caveats": []}
    }]
    
    response = analyze_trade_pvo(my_assets, their_assets)
    assert response["delta_status"] == "Within_Model_Error"
