from __future__ import annotations

import asyncio
from unittest.mock import patch

from src.dynasty_genius.models.engine_a_contract import (
    ALLOWED_ENRICHMENT_COLUMNS,
    POSITION_FEATURE_MATRIX,
    QB_CONTEXT_COLUMNS,
)


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


def test_qb_context_card_adds_display_only_college_annotations_when_context_present() -> None:
    from app.services.roster_auditor import QB_CONTEXT_ANNOTATION_FIELDS, run_audit

    roster = [
        {
            "player_id": "qb1",
            "full_name": "Risk QB",
            "position": "QB",
            "team": "FA",
            "age": 24,
            "td_int_ratio": 0.62,
            "all_purpose_yards": 3900,
        },
        {
            "player_id": "wr1",
            "full_name": "Young WR",
            "position": "WR",
            "team": "FA",
            "age": 24,
        },
    ]
    bridge = {
        "players": {
            "qb1": {
                "gsis_id": "00-0000001",
                "coverage": "FULL",
            }
        }
    }
    telemetry = {field: None for field in QB_CONTEXT_COLUMNS}

    with patch("app.services.roster_auditor.get_my_roster") as get_my_roster:
        with patch("app.services.roster_auditor.load_qb_identity_bridge", return_value=bridge):
            with patch("app.services.roster_auditor.fetch_qb_nfl_stats", return_value=telemetry):
                get_my_roster.return_value = roster
                result = asyncio.run(run_audit())

    assert len(result["players"]) == 2
    audited_qb = next(
        player for player in result["players"] if player["player_id"] == "qb1"
    )
    assert audited_qb["signal_drivers"] == ["age_not_near_position_cliff"]

    card = result["qb_context_cards"][0]
    assert card["context_role"] == "context_signal"
    assert card["decision_supported"] is False
    assert card["qb_context_annotations"] == [
        "low_td_int_ratio_bust_context",
        "all_purpose_yards_mobility_context",
    ]
    assert card["qb_context_caveats"] == ["p2s_context_unavailable"]
    assert card["source_qb_context_annotations"] == "cfbd_qb_context_annotations"

    for field in QB_CONTEXT_ANNOTATION_FIELDS:
        assert field not in ALLOWED_ENRICHMENT_COLUMNS
        assert field not in set(POSITION_FEATURE_MATRIX["QB"])


def test_qb_context_card_reports_missing_college_context_without_fetching_new_sources() -> None:
    from app.services.roster_auditor import run_audit

    roster = [
        {
            "player_id": "qb1",
            "full_name": "No Context QB",
            "position": "QB",
            "team": "FA",
            "age": 24,
        }
    ]
    bridge = {"players": {"qb1": {"gsis_id": "00-0000001", "coverage": "FULL"}}}
    telemetry = {field: None for field in QB_CONTEXT_COLUMNS}

    with patch("app.services.roster_auditor.get_my_roster") as get_my_roster:
        with patch("app.services.roster_auditor.load_qb_identity_bridge", return_value=bridge):
            with patch("app.services.roster_auditor.fetch_qb_nfl_stats", return_value=telemetry):
                get_my_roster.return_value = roster
                result = asyncio.run(run_audit())

    card = result["qb_context_cards"][0]
    assert card["qb_context_annotations"] == []
    assert card["qb_context_caveats"] == [
        "missing_qb_college_context",
        "p2s_context_unavailable",
    ]


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
