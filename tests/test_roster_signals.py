from app.services.roster_auditor import (
    age_cliff_risk,
    audit_player,
    biological_debt_score,
    liquidity_risk,
    roster_risk_summary,
)


def test_roster_signal_domain_and_caveats() -> None:
    allowed_signals = {"past_cliff", "at_cliff", "approaching_cliff", "no_age_signal"}
    samples = [
        {"player_id": "1", "full_name": "RB Past", "position": "RB", "team": "FA", "age": 28},
        {"player_id": "2", "full_name": "WR At", "position": "WR", "team": "FA", "age": 28},
        {"player_id": "3", "full_name": "TE Near", "position": "TE", "team": "FA", "age": 29},
        {"player_id": "4", "full_name": "QB Safe", "position": "QB", "team": "FA", "age": 25},
    ]

    audited = [audit_player(player) for player in samples]

    for item in audited:
        assert item is not None
        assert item["signal"] in allowed_signals
        assert "action" not in item
        rendered = str(item)
        assert "Sell now" not in rendered
        assert "Hold" not in rendered
        caveats = item["caveats"]
        assert "age_curve_only" in caveats
        assert "no_usage_signal" in caveats


def test_age_cliff_risk_matches_gold_sql_curve() -> None:
    assert age_cliff_risk("RB", 23) == 0.0
    assert age_cliff_risk("RB", 24.5) == 0.5
    assert age_cliff_risk("RB", 26) == 1.0
    assert age_cliff_risk("WR", 26) == 0.3333
    assert age_cliff_risk("QB", None) is None


def test_biological_debt_uses_internal_value_not_market_value() -> None:
    player = {
        "player_id": "cmc",
        "full_name": "RB Cliff",
        "position": "RB",
        "age": 26,
        "internal_valuation": 80,
        "ktc_market_value": 9999,
    }

    assert biological_debt_score(player) == 80.0
    audited = audit_player(player)
    assert audited is not None
    assert audited["age_cliff_risk"] == 1.0
    assert audited["biological_debt_score"] == 80.0
    assert "ktc_market_value" in player


def test_liquidity_risk_uses_second_round_escape_hatches() -> None:
    assert liquidity_risk(False, False) == "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"
    assert liquidity_risk(True, False) == "MEDIUM_LIMITED_ESCAPE_HATCH"
    assert liquidity_risk(False, True) == "MEDIUM_LIMITED_ESCAPE_HATCH"
    assert liquidity_risk(True, True) == "LOW"


def test_roster_risk_summary_value_weights_biological_debt() -> None:
    players = [
        {"player_id": "1", "full_name": "RB Cliff", "position": "RB", "age": 26, "internal_value": 80},
        {"player_id": "2", "full_name": "WR Safe", "position": "WR", "age": 24, "internal_value": 20},
        {"player_id": "3", "full_name": "QB Missing", "position": "QB", "age": 31},
    ]

    summary = roster_risk_summary(players, has_2026_2nd=False, has_2027_2nd=True)

    assert summary["biological_debt_value"] == 80.0
    assert summary["biological_debt_ratio"] == 0.8
    assert summary["biological_debt_players"] == ["RB Cliff"]
    assert summary["incomplete_biological_debt_players"] == ["QB Missing"]
    assert summary["liquidity_risk"] == "MEDIUM_LIMITED_ESCAPE_HATCH"
    assert summary["decision_supported"] is False
    assert "no_market_derived_inputs" in summary["caveats"]
