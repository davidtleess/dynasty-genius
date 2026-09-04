"""DG-147 — a rookie the league did not draft gets his number and his "Rookie" word.

The roster index admitted a rookie-model (ENGINE_A) universe row only when the
league's own draft had picked him (``league_context.in_current_draft``). A 2026
rookie acquired off waivers or onto a taxi squad fell to the fallback assembler:
no number, ``is_prospect`` False, no draft class — while his card scored him.
Eight such players league-wide on 2026-09-03 (Douglas, Hibner, Benson, Joly,
Allen, Lance, Raridon, McGowan), none on David's roster; the first waiver rookie
he picks up would have been the ninth.

Three seams pin the fix:

* the roster index admits an ENGINE_A row for any ROSTERED rookie;
* ``is_prospect`` is a player fact — Sleeper's ``years_exp == 0`` (draft class as
  the tie-breaker when Sleeper is silent) — not the league's draft and not the
  engine path, on the universe path and the fallback path alike;
* ``draft_class`` rides the roster row from the universe row.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.roster_auditor import get_my_roster
from tests.contract.test_roster_audit_pvo import (
    _RB_ENGINE_B_SCORE,
    _RB_PLAYER,
    _run_with_universe,
    _universe_row_for_rookie,
)

# Caleb Douglas's shape on 2026-09-03: rostered on a taxi squad, never in this
# league's 2026 draft, scored 61.39 by the rookie model.
_WAIVER_ROOKIE_PLAYER = {
    "player_id": "13296",
    "full_name": "Caleb Douglas",
    "position": "WR",
    "team": "LV",
    "age": 22,
    "gsis_id": None,
    "years_exp": 0,
}


def _waiver_rookie_row() -> dict:
    row = _universe_row_for_rookie()
    row["sleeper_player_id"] = "13296"
    row["dg_player_id"] = "caleb_douglas_wr"
    row["identity_ids"] = {"sleeper_id": "13296"}
    row["player"].update(
        {"full_name": "Caleb Douglas", "position": "WR", "team": "LV", "age": 22.0, "years_exp": 0}
    )
    row["draft_class"] = 2026
    row["league_context"] = {
        "rostered": True,
        "roster_id": 10,
        "in_current_draft": False,
        "on_taxi": True,
    }
    row["valuation"].update({"dynasty_value_score": 61.39, "xvar": 9.1})
    return row


def _rookie(result: dict, sleeper_id: str) -> dict:
    return next(p for p in result["players"] if p["sleeper_id"] == sleeper_id)


# ── the index admits any rostered rookie ─────────────────────────────────────
def test_a_rostered_rookie_the_league_did_not_draft_gets_his_rookie_model_number(tmp_path):
    result = _run_with_universe(
        tmp_path, [_waiver_rookie_row()], roster=[_WAIVER_ROOKIE_PLAYER, _RB_PLAYER]
    )
    rookie = _rookie(result, "13296")
    assert rookie["engine_used"] == "engine_a"
    assert rookie["dynasty_value_score"] == 61.39
    assert rookie["model_grade"] == "PROSPECT_C"
    assert rookie["player_id"] == "caleb_douglas_wr"


def test_the_rookie_word_rests_on_the_player_fact_not_the_leagues_draft(tmp_path):
    result = _run_with_universe(
        tmp_path, [_waiver_rookie_row()], roster=[_WAIVER_ROOKIE_PLAYER, _RB_PLAYER]
    )
    rookie = _rookie(result, "13296")
    assert rookie["is_prospect"] is True
    assert rookie["draft_class"] == 2026


def test_a_drafted_rookie_still_carries_the_number_and_the_word(tmp_path):
    result = _run_with_universe(tmp_path, [_universe_row_for_rookie()])
    rookie = _rookie(result, "13414")
    assert rookie["engine_used"] == "engine_a"
    assert rookie["dynasty_value_score"] == 61.55
    assert rookie["is_prospect"] is True


# ── the fallback path reads the same fact ────────────────────────────────────
def test_a_veteran_on_the_fallback_path_is_not_a_rookie(tmp_path):
    veteran = {**_RB_PLAYER, "years_exp": 5}
    result = _run_with_universe(tmp_path, [], roster=[veteran], scores=[_RB_ENGINE_B_SCORE])
    row = _rookie(result, "sleeper_rb_001")
    assert row["is_prospect"] is False
    assert row["draft_class"] is None


def test_a_rookie_with_no_model_row_still_says_rookie_on_the_fact(tmp_path):
    undrafted = {
        "player_id": "13999",
        "full_name": "Undrafted Rookie",
        "position": "WR",
        "team": "NYJ",
        "age": 22,
        "gsis_id": None,
        "years_exp": 0,
    }
    result = _run_with_universe(tmp_path, [], roster=[undrafted, _RB_PLAYER])
    row = _rookie(result, "13999")
    assert row["is_prospect"] is True
    assert row["dynasty_value_score"] is None


# ── the live roster row carries Sleeper's fact ───────────────────────────────
def test_get_my_roster_carries_sleepers_years_of_experience():
    config = {
        "user_id": "user-1",
        "league_id": "league-1",
        "season": "2026",
        "username": None,
        "league_name": None,
    }
    rosters = [{"owner_id": "user-1", "roster_id": 10, "players": ["13296", "4017"]}]
    players = {
        "13296": {
            "first_name": "Caleb",
            "last_name": "Douglas",
            "position": "WR",
            "team": "LV",
            "age": 22,
            "years_exp": 0,
            "gsis_id": None,
        },
        "4017": {
            "first_name": "Deshaun",
            "last_name": "Watson",
            "position": "QB",
            "team": None,
            "age": 30,
            "years_exp": 9,
            "gsis_id": "00-0033537",
        },
    }
    with (
        patch("app.services.roster_auditor._roster_config", return_value=config),
        patch("app.services.roster_auditor.get_rosters", new_callable=AsyncMock, return_value=rosters),
        patch("app.services.roster_auditor.get_all_players", new_callable=AsyncMock, return_value=players),
    ):
        roster = asyncio.run(get_my_roster())
    by_id = {p["player_id"]: p for p in roster}
    assert by_id["13296"]["years_exp"] == 0
    assert by_id["4017"]["years_exp"] == 9
