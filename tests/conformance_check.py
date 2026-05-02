from __future__ import annotations

import pytest

from app.services import trade_analyzer
from app.services.rookie_evaluator import decision_weights_for_round
from app.services.roster_auditor import audit_player


@pytest.fixture(autouse=True)
def _stub_trade_player_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trade_analyzer,
        "value_player",
        lambda position, age, pick, round_num: (42.0, "conformance_fixture"),
    )


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
    assert result["decision_supported"] is False
    assert "elite_yards_after_contact_exception" in result["signal_drivers"]


def test_rookie_decision_weights_keep_draft_capital_first() -> None:
    r1 = decision_weights_for_round(1)
    r2 = decision_weights_for_round(2)
    r3 = decision_weights_for_round(3)
    r4 = decision_weights_for_round(4)

    assert r1["draft_capital"] == 0.70
    assert r2["draft_capital"] == 0.70
    assert r3["draft_capital"] == 0.50
    assert r4["draft_capital"] == 0.30

    for weights in (r1, r2, r3):
        assert weights["landing_spot_context"] <= weights["draft_capital"]
        assert weights["applied_to_model_score"] is False


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
    assert "unified_valuation_layer_for_all_assets" in response["required_before_decision_grade"]
    assert "verdict" not in {key.lower() for key in _walk_keys(response)}
