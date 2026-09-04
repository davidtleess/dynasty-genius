"""DG-149 — two team signals on every player, in different spots.

David, 2026-09-04 07:35 ET, verbatim: "there should be a signal on every player
NFL Team (including the FA tag if they don't have a team) and Team = team they
are on in my league i.e. woodbury riders or if they are a FA they get the FA tag
there too. they should be in different spots - no you can leave it by dleess"

NFL team: the API serves the FACT — Sleeper's team, or null when he has none,
Active or not. DG-137's Active-only "FA" on the card and get_my_roster's
unconditional "FA" on the roster row both retire; the word "FA" is the
frontend's, minted once for both spots. League team: ``league_ownership`` gains
``team_name`` — the owning roster's team name from the league snapshot's users
(``metadata.team_name``), None when unowned, unknown, or never named.
"""
from __future__ import annotations

import asyncio
import json
import re
from unittest.mock import AsyncMock, patch

import app.api.routes.players as players_route
from app.main import app as main_app
from app.services.roster_auditor import get_my_roster
from tests.contract.test_dg145_league_free_agent_on_the_card import (
    SNAPSHOT_AT,
    _artifact,
    _free_agent_row,
    _rostered_row,
)
from tests.contract.test_surface3_player_detail_endpoint import (
    _client,
    _divergence,
    _pvo,
    _pvo_row,
)

# The league on 2026-09-03: 9 of 12 managers named their team; rzalika did not.
# Keyed on the manager's Sleeper user id, which is what the artifact's
# league_context.owner_user_id carries. "user-1" is _rostered_row's owner.
TEAM_NAMES: dict[str, str] = {"user-1": "Woodbury Riders"}


def _get(monkeypatch, artifact, team_names=None):
    team_names = TEAM_NAMES if team_names is None else team_names
    client = _client(
        monkeypatch, pvo=artifact, divergence=_divergence(), league_team_names=team_names
    )
    response = client.get("/api/players/13269")
    assert response.status_code == 200
    return response


# ── NFL team: the fact, on every player ─────────────────────────────────────
def test_the_card_serves_no_nfl_team_as_the_fact_for_an_active_player(monkeypatch):
    row = _pvo_row()
    row["player"]["team"] = None
    assert row["player"]["sleeper_status"] == "Active"
    assert _get(monkeypatch, _pvo(row)).json()["identity"]["team"] is None


def test_the_card_serves_no_nfl_team_as_the_fact_for_an_inactive_player(monkeypatch):
    row = _pvo_row(engine_path="INACTIVE")
    row["player"]["team"] = None
    row["player"]["sleeper_status"] = "Inactive"
    assert _get(monkeypatch, _pvo(row)).json()["identity"]["team"] is None


def test_the_card_serves_the_nfl_team_when_he_has_one(monkeypatch):
    assert _get(monkeypatch, _pvo(_pvo_row())).json()["identity"]["team"] == "LVR"


def test_get_my_roster_passes_a_missing_nfl_team_through_as_the_fact():
    """The roster row used to turn Sleeper's null into "FA" itself (since the
    first commit). The word now has one home; the row carries the fact."""
    config = {"user_id": "u1", "league_id": "L", "season": "2026", "username": None, "league_name": None}
    rosters = [{"owner_id": "u1", "roster_id": 1, "players": ["4663"]}]
    players = {
        "4663": {
            "first_name": "Austin",
            "last_name": "Ekeler",
            "position": "RB",
            "team": None,
            "age": 31,
            "years_exp": 9,
            "gsis_id": "00-0033699",
        }
    }
    with (
        patch("app.services.roster_auditor._roster_config", return_value=config),
        patch("app.services.roster_auditor.get_rosters", new_callable=AsyncMock, return_value=rosters),
        patch("app.services.roster_auditor.get_all_players", new_callable=AsyncMock, return_value=players),
    ):
        roster = asyncio.run(get_my_roster())
    assert roster[0]["team"] is None


# ── league team: the name he plays for in David's league ────────────────────
def test_an_owned_player_carries_his_league_team_name(monkeypatch):
    body = _get(monkeypatch, _artifact(_rostered_row(owner="Dleess", roster_id=1))).json()
    assert body["league_ownership"]["team_name"] == "Woodbury Riders"
    assert body["league_ownership"]["owner_display_name"] == "Dleess"
    assert body["league_ownership"]["as_of"] == SNAPSHOT_AT


def test_a_manager_who_never_named_his_team_yields_no_team_name_but_keeps_his_handle(monkeypatch):
    body = _get(
        monkeypatch, _artifact(_rostered_row(owner="rzalika", roster_id=5)), team_names={}
    ).json()
    assert body["league_ownership"]["status"] == "rostered"
    assert body["league_ownership"]["team_name"] is None
    assert body["league_ownership"]["owner_display_name"] == "rzalika"


def test_a_free_agent_carries_no_league_team_name(monkeypatch):
    body = _get(monkeypatch, _artifact(_free_agent_row())).json()
    assert body["league_ownership"]["status"] == "free_agent"
    assert body["league_ownership"]["team_name"] is None


def test_a_missing_league_snapshot_yields_no_team_name_and_still_says_rostered(monkeypatch):
    body = _get(monkeypatch, _artifact(_rostered_row(roster_id=1)), team_names={}).json()
    assert body["league_ownership"]["status"] == "rostered"
    assert body["league_ownership"]["team_name"] is None


def test_the_team_name_reader_maps_each_manager_to_his_team_name(tmp_path):
    snapshot = {
        "rosters": [{"roster_id": 1, "owner_id": "u1"}, {"roster_id": 5, "owner_id": "u5"}],
        "users": [
            {"user_id": "u1", "display_name": "Dleess", "metadata": {"team_name": "Woodbury Riders"}},
            {"user_id": "u5", "display_name": "rzalika", "metadata": {}},
            {"user_id": "u6", "display_name": "blank", "metadata": {"team_name": "   "}},
            {"user_id": "u7", "display_name": "odd", "metadata": {"team_name": 12}},
            {"display_name": "no id", "metadata": {"team_name": "Nameless"}},
        ],
    }
    assert players_route._league_team_names_from_snapshot(snapshot) == {"u1": "Woodbury Riders"}
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot))
    assert players_route._load_league_team_names(path) == {"u1": "Woodbury Riders"}
    assert players_route._load_league_team_names(tmp_path / "absent.json") == {}
    (tmp_path / "bad.json").write_text("{not json")
    assert players_route._load_league_team_names(tmp_path / "bad.json") == {}


def test_a_snapshot_of_another_vintage_cannot_hang_a_name_on_the_wrong_manager(monkeypatch):
    """The name is the MANAGER's, so a snapshot older or newer than the artifact
    yields a stale name for the right manager, never another manager's team."""
    body = _get(
        monkeypatch,
        _artifact(_rostered_row(owner="Dleess", roster_id=1)),
        team_names={"someone-else": "Florida Man"},
    ).json()
    assert body["league_ownership"]["team_name"] is None
    assert body["league_ownership"]["owner_display_name"] == "Dleess"


# ── one word, one home ───────────────────────────────────────────────────────
def test_the_api_still_never_says_the_word(monkeypatch):
    row = _free_agent_row()
    row["player"]["team"] = None
    response = _get(monkeypatch, _artifact(row))
    assert re.search(r"(?<![A-Za-z])FA(?![A-Za-z])", response.text) is None


def test_team_name_is_in_the_contract():
    schemas = main_app.openapi()["components"]["schemas"]
    assert "team_name" in schemas["PlayerLeagueOwnership"]["required"]
