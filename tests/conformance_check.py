from __future__ import annotations

from app.services import trade_analyzer
from app.services.rookie_evaluator import (
    TIER_1_2026_PROSPECT_MAP,
    decision_weights_for_round,
)
from app.services.roster_auditor import audit_player

def _walk_keys(value: object) -> list[str]:
    if isinstance(value, dict):
        keys = list(value.keys())
        for nested in value.values():
            keys.extend(_walk_keys(nested))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for item in value:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _player_asset(response: dict, name: str) -> dict:
    assets = response["my_assets_breakdown"] + response["their_assets_breakdown"]
    return next(asset for asset in assets if asset.get("name") == name)


def test_trade_output_flags_age_curve_sells_with_protocol_support() -> None:
    response = trade_analyzer.analyze_trade(
        my_assets=[
            {
                "type": "player",
                "name": "Jonathan Taylor",
                "position": "RB",
                "age": 26,
                "pick": 41,
                "round": 2,
                "yards_after_contact_per_attempt": 2.4,
                "ground_truth": {
                    "nfl_status": "active",
                    "current_team": "IND",
                    "years_experience": 6,
                    "source": "ground_truth_fixture",
                },
            }
        ],
        their_assets=[
            {
                "type": "player",
                "name": "Age Cliff WR",
                "position": "WR",
                "age": 28,
                "pick": 12,
                "round": 1,
                "ground_truth": {
                    "nfl_status": "active",
                    "current_team": "SEA",
                    "years_experience": 7,
                    "source": "ground_truth_fixture",
                },
            }
        ],
    )

    for name in ("Jonathan Taylor", "Age Cliff WR"):
        asset = _player_asset(response, name)
        assert asset["asset_management_signal"] == "Sell"
        assert asset["ground_truth_check"]["status"] == "verified"
        assert asset["ground_truth_check"]["classification"] == "active_nfl_veteran"
        assert "active_nfl_veteran_not_rookie_prospect" in asset["caveats"]
        assert asset["valuation_status"] == trade_analyzer.VALUATION_STATUS_PENDING_ENGINE_B
        assert asset["dvu"] is None
        assert asset["compliance_header"] == "Compliance: 100% / 0% (PASS)"
        assert "strongest case against selling" in asset["counter_argument"]


def test_roster_auditor_applies_elite_rb_yac_exception() -> None:
    result = audit_player(
        {
            "player_id": "breece_fixture",
            "full_name": "Elite 26-Year-Old RB",
            "position": "RB",
            "team": "NYJ",
            "age": 26,
            "yards_after_contact_per_attempt": 3.0,
        }
    )

    assert result is not None
    assert result["signal"] == "elite_exception_hold"
    assert result["cliff_status"] == "Elite Exception: HOLD"
    assert result["asset_management_signal"] == "ELITE_HOLD"
    assert result["compliance_header"] == "Compliance: 100% / 0% (PASS)"
    assert result["decision_supported"] is False
    assert "elite_yards_after_contact_exception" in result["signal_drivers"]


def test_rookie_decision_weights_keep_draft_capital_first() -> None:
    r1 = decision_weights_for_round(1)
    r2 = decision_weights_for_round(2)
    r3 = decision_weights_for_round(3)
    r4 = decision_weights_for_round(4)

    assert r1["draft_capital"] == 0.70
    assert r1["draft_capital_locked"] is True
    assert r1["draft_capital_influence_tier"] == "draft_capital_locked_70_percent_round_1_2"
    assert r2["draft_capital"] == 0.70
    assert r3["draft_capital"] == 0.50
    assert r4["draft_capital"] == 0.30

    for weights in (r1, r2, r3):
        assert weights["landing_spot_context"] <= weights["draft_capital"]
        assert weights["applied_to_model_score"] is False


def test_2026_tier_1_prospect_map_is_ground_truth_anchored() -> None:
    love = TIER_1_2026_PROSPECT_MAP["jeremiyah love"]
    jeanty = TIER_1_2026_PROSPECT_MAP["ashton jeanty"]
    sadiq = TIER_1_2026_PROSPECT_MAP["kenyon sadiq"]

    assert love["position"] == "RB"
    assert love["dominator_rating"] == 0.32
    assert love["ras"] == 9.8
    assert jeanty["dominator_rating"] == 0.343
    assert jeanty["bmi"] == 32.1
    assert sadiq["position"] == "TE"
    assert sadiq["ras"] == 9.59
    assert {love["source"], jeanty["source"], sadiq["source"]} == {"DYNASTY_GENIUS_CORE.rtf"}


def test_trade_output_blocks_verdict_until_unified_valuation_layer() -> None:
    response = trade_analyzer.analyze_trade(
        my_assets=[{"type": "pick", "year": 2027, "round": 1}],
        their_assets=[
            {
                "type": "player",
                "name": "Verified Veteran",
                "position": "TE",
                "age": 29,
                "pick": 35,
                "round": 2,
                "ground_truth": {
                    "nfl_status": "active",
                    "current_team": "LV",
                    "years_experience": 6,
                    "source": "ground_truth_fixture",
                },
            }
        ],
    )

    assert response["decision_supported"] is False
    assert response["compliance_header"] == "Compliance: 100% / 0% (PASS)"
    assert "unified_valuation_layer_for_all_assets" in response["required_before_decision_grade"]
    assert "verdict" not in {key.lower() for key in _walk_keys(response)}


def test_trade_market_values_normalize_to_dvu_before_aggregation() -> None:
    response = trade_analyzer.analyze_trade(
        my_assets=[
            {
                "type": "pick",
                "year": 2026,
                "round": 1,
                "market_value": 0.5,
                "market_value_scale": "one_oh_one_ratio",
            }
        ],
        their_assets=[{"type": "pick", "year": 2026, "round": 1}],
    )

    mine = response["my_assets_breakdown"][0]
    assert mine["dvu"] == 50.0
    assert mine["scoring_method"] == "market_value_101_pick_ratio"
    assert response["dvu_normalization"]["one_oh_one_rookie_pick_value"] == 100.0
    assert response["dvu_normalization"]["my_assets_dvu_total"] == 50.0


def test_2027_first_round_picks_use_generational_anchor_floor() -> None:
    response = trade_analyzer.analyze_trade(
        my_assets=[{"type": "pick", "year": 2027, "round": 1}],
        their_assets=[],
    )

    pick = response["my_assets_breakdown"][0]
    assert pick["dvu"] == 120.0
    assert "generational_anchor_2027_first_floor_120_dvu" in pick["caveats"]
