from app.services.roster_auditor import audit_player


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
