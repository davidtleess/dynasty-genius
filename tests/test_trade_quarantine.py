from app.services.trade_analyzer import analyze_trade


def test_trade_quarantine_contract_fields() -> None:
    response = analyze_trade(
        my_assets=[
            {"type": "player", "name": "My Veteran", "position": "WR", "age": 27, "pick": 18, "round": 1},
            {"type": "pick", "year": 2027, "round": 2},
        ],
        their_assets=[
            {"type": "player", "name": "Their Veteran", "position": "RB", "age": 25, "pick": 36, "round": 2},
            {"type": "pick", "year": 2026, "round": 3},
        ],
    )

    forbidden_top_level = {
        "verdict",
        "my_total",
        "their_total",
        "difference",
        "experimental_totals",
        "deprecated_fields",
        "my_assets_scored",
        "their_assets_scored",
    }
    for field in forbidden_top_level:
        assert field not in response

    assert response["decision_supported"] is False

    for asset in response["my_assets_breakdown"] + response["their_assets_breakdown"]:
        caveats = asset.get("caveats", [])
        if asset.get("asset_type") == "player":
            assert "trade_player_value_requires_ground_truth" in caveats
            assert asset["valuation_status"] in {
                "VALUATION_STATUS_PENDING_ENGINE_B",
                "VALUATION_STATUS_PENDING_GROUND_TRUTH",
            }
            if asset["valuation_status"] == "VALUATION_STATUS_PENDING_ENGINE_B":
                assert asset["dvu"] is None
        elif asset.get("asset_type") == "pick":
            assert "pick_value_normalized_to_dvu" in caveats
            assert asset["dvu"] is not None
