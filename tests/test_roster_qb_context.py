from __future__ import annotations

import asyncio
from unittest.mock import patch

from src.dynasty_genius.models.engine_a_contract import QB_CONTEXT_COLUMNS


def test_run_audit_includes_qb_context_cards_without_changing_age_audit() -> None:
    from app.services.roster_auditor import run_audit

    roster = [
        {"player_id": "qb1", "full_name": "Josh Allen", "position": "QB", "team": "BUF", "age": 29},
        {"player_id": "rb1", "full_name": "Veteran RB", "position": "RB", "team": "FA", "age": 27},
    ]
    bridge = {
        "players": {
            "qb1": {
                "pfr_player_name": "Josh Allen",
                "normalized_name": "joshua_allen",
                "gsis_id": "00-0034857",
                "coverage": "FULL",
            }
        }
    }
    telemetry = {
        "epa_per_dropback": 0.21,
        "cpoe": 5.1,
        "dakota": 0.1623,
        "dropback_count": 620,
        "pass_attempts": 540,
    }

    with patch("app.services.roster_auditor.get_my_roster") as get_my_roster:
        with patch("app.services.roster_auditor.load_qb_identity_bridge", return_value=bridge):
            with patch("app.services.roster_auditor.fetch_qb_nfl_stats", return_value=telemetry):
                get_my_roster.return_value = roster
                result = asyncio.run(run_audit())

    assert result["decision_supported"] is False
    assert len(result["players"]) == 2
    assert "qb_context_cards" in result
    assert len(result["qb_context_cards"]) == 1

    card = result["qb_context_cards"][0]
    assert card["player_id"] == "qb1"
    assert card["full_name"] == "Josh Allen"
    assert card["decision_supported"] is False
    assert card["context_role"] == "context_signal"
    for field in QB_CONTEXT_COLUMNS:
        assert field in card
        assert f"source_{field}" in card
        assert card[f"source_{field}"] == "nflreadpy_qb_context"


def test_run_audit_marks_unresolved_qb_context_without_fetching() -> None:
    from app.services.roster_auditor import run_audit

    roster = [{"player_id": "qb1", "full_name": "Unknown QB", "position": "QB", "team": "FA", "age": 24}]
    bridge = {"players": {}}

    with patch("app.services.roster_auditor.get_my_roster") as get_my_roster:
        with patch("app.services.roster_auditor.load_qb_identity_bridge", return_value=bridge):
            with patch("app.services.roster_auditor.fetch_qb_nfl_stats") as fetch_qb_nfl_stats:
                get_my_roster.return_value = roster
                result = asyncio.run(run_audit())

    fetch_qb_nfl_stats.assert_not_called()
    card = result["qb_context_cards"][0]
    assert card["player_id"] == "qb1"
    assert card["identity_coverage"] == "NONE"
    assert card["decision_supported"] is False
    assert all(card[field] is None for field in QB_CONTEXT_COLUMNS)
    assert all(card[f"source_{field}"] == "nflreadpy_qb_context:unresolved_identity" for field in QB_CONTEXT_COLUMNS)


def test_run_audit_does_not_create_context_cards_for_non_qbs() -> None:
    from app.services.roster_auditor import run_audit

    roster = [{"player_id": "rb1", "full_name": "Veteran RB", "position": "RB", "team": "FA", "age": 27}]

    with patch("app.services.roster_auditor.get_my_roster") as get_my_roster:
        with patch("app.services.roster_auditor.fetch_qb_nfl_stats") as fetch_qb_nfl_stats:
            get_my_roster.return_value = roster
            result = asyncio.run(run_audit())

    fetch_qb_nfl_stats.assert_not_called()
    assert result["qb_context_cards"] == []
    assert len(result["players"]) == 1
