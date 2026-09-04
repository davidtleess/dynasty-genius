"""DG-145 — the card says where a player stands in David's league.

David, 2026-09-03 05:59 ET: "I think free agents should show 'FA' on the card."
Asked that evening whether "free agent" meant no NFL team or nobody in his league
(23:35 ET, verbatim): "1) nobody in the league owns."

The card route reads the universe artifact, whose rows carry ``league_context``
from the latest league roster capture, dated by the artifact's
``source_snapshot_captured_at``. The route serves the FACT — rostered by whom, or
a free agent, or unknown — dated with that capture. The word "FA" is the
frontend's, minted once in the copy dictionary; the API never says it. A missing
or non-boolean ``rostered`` flag, or an undated snapshot, is served as ``unknown``:
never a free-agent claim the capture did not make.
"""
from __future__ import annotations

import re
from typing import Any

from app.main import app as main_app
from tests.contract.test_surface3_player_detail_endpoint import (
    _client,
    _divergence,
    _pvo,
    _pvo_row,
)

SNAPSHOT_AT = "2026-09-03T13:00:45.589670+00:00"


def _league_context(**overrides: Any) -> dict[str, Any]:
    context = {
        "rostered": False,
        "roster_id": None,
        "owner_user_id": None,
        "in_starters": False,
        "on_taxi": False,
        "on_ir": False,
        "in_current_draft": False,
    }
    context.update(overrides)
    return context


def _artifact(row: dict[str, Any], *, snapshot_at: str | None = SNAPSHOT_AT) -> dict[str, Any]:
    artifact = _pvo(row)
    if snapshot_at is not None:
        artifact["source_snapshot_captured_at"] = snapshot_at
    return artifact


def _free_agent_row() -> dict[str, Any]:
    row = _pvo_row()
    row["league_context"] = _league_context()
    return row


def _rostered_row(*, owner: str | None = "Dleess", roster_id: int = 1) -> dict[str, Any]:
    row = _pvo_row()
    context = _league_context(rostered=True, roster_id=roster_id, owner_user_id="user-1")
    if owner is not None:
        context["owner_display_name"] = owner
    row["league_context"] = context
    return row


def _get(monkeypatch, artifact: dict[str, Any]):
    client = _client(monkeypatch, pvo=artifact, divergence=_divergence())
    response = client.get("/api/players/13269")
    assert response.status_code == 200
    return response


# ── the fact, dated ─────────────────────────────────────────────────────────
def test_a_player_nobody_in_the_league_owns_is_a_free_agent_dated_by_the_capture(monkeypatch):
    body = _get(monkeypatch, _artifact(_free_agent_row())).json()
    assert body["league_ownership"] == {
        "status": "free_agent",
        "owner_display_name": None,
        "roster_id": None,
        "as_of": SNAPSHOT_AT,
        "team_name": None,
    }


def test_a_rostered_player_is_served_with_his_manager(monkeypatch):
    body = _get(monkeypatch, _artifact(_rostered_row())).json()
    assert body["league_ownership"] == {
        "status": "rostered",
        "owner_display_name": "Dleess",
        "roster_id": 1,
        "as_of": SNAPSHOT_AT,
        "team_name": None,
    }


def test_a_rostered_player_whose_manager_name_is_missing_is_still_rostered(monkeypatch):
    """The users lookup can fail while the roster capture succeeds; rostered is
    the roster's own fact and stands without the name."""
    body = _get(monkeypatch, _artifact(_rostered_row(owner=None, roster_id=7))).json()
    assert body["league_ownership"] == {
        "status": "rostered",
        "owner_display_name": None,
        "roster_id": 7,
        "as_of": SNAPSHOT_AT,
        "team_name": None,
    }


# ── never a claim the capture did not make ──────────────────────────────────
def test_a_row_without_league_context_is_unknown_never_a_free_agent(monkeypatch):
    row = _pvo_row()
    assert "league_context" not in row
    body = _get(monkeypatch, _artifact(row)).json()
    assert body["league_ownership"]["status"] == "unknown"
    assert body["league_ownership"]["owner_display_name"] is None
    assert body["league_ownership"]["roster_id"] is None


def test_a_non_boolean_rostered_flag_is_unknown(monkeypatch):
    row = _pvo_row()
    row["league_context"] = _league_context(rostered=None)
    body = _get(monkeypatch, _artifact(row)).json()
    assert body["league_ownership"]["status"] == "unknown"


def test_an_undated_snapshot_never_yields_a_free_agent_claim(monkeypatch):
    """A free-agent fact with no capture time behind it cannot say how old it is,
    so it is not served as a fact at all."""
    body = _get(monkeypatch, _artifact(_free_agent_row(), snapshot_at=None)).json()
    assert body["league_ownership"] == {
        "status": "unknown",
        "owner_display_name": None,
        "roster_id": None,
        "as_of": None,
        "team_name": None,
    }


# ── one place for the word ──────────────────────────────────────────────────
def test_the_api_serves_the_fact_not_the_word(monkeypatch):
    """"FA" is minted once, in the frontend copy dictionary. The API says
    free_agent and nothing that already spells the label."""
    response = _get(monkeypatch, _artifact(_free_agent_row()))
    assert re.search(r'(?<![A-Za-z])FA(?![A-Za-z])', response.text) is None
    assert response.json()["league_ownership"]["status"] == "free_agent"


def test_league_ownership_is_a_required_part_of_the_card_contract():
    schemas = main_app.openapi()["components"]["schemas"]
    assert "league_ownership" in schemas["PlayerDetailResponse"]["required"]
    ownership = schemas["PlayerLeagueOwnership"]
    assert set(ownership["required"]) == {"status", "owner_display_name", "roster_id", "as_of", "team_name"}
    assert set(ownership["properties"]["status"]["enum"]) == {"rostered", "free_agent", "unknown"}
