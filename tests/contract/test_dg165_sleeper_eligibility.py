"""DG-165 — Sleeper fantasy eligibility capture: extraction, classification, reconciliation.

Synthetic payloads only (no network). What each test would catch:
* a missing ``fantasy_positions`` must read as UNKNOWN, never be inferred from an NFL position;
* a rostered player is always in the universe whatever Sleeper's flags say;
* a dubious ``active`` flag classifies, it never suppresses;
* rookies match by gsis first, then by name + position, and the basis is recorded.
"""
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.rookie.sleeper_eligibility import (
    classify_availability,
    extract_players,
    reconcile,
)

PAYLOAD = {
    "13516": {"player_id": "13516", "full_name": "Max Bredeson", "position": "TE", "fantasy_positions": ["RB"],
              "active": True, "status": "Active", "team": "MIN", "injury_status": None, "years_exp": 0, "gsis_id": None},
    "12530": {"player_id": "12530", "full_name": "Travis Hunter", "position": "DB", "fantasy_positions": ["WR", "DB"],
              "active": True, "status": "Active", "team": "JAX", "injury_status": None, "years_exp": 1, "gsis_id": "00-0039999"},
    "9999": {"player_id": "9999", "full_name": "Old Back", "position": "RB", "fantasy_positions": ["RB"],
             "active": False, "status": "Inactive", "team": None, "injury_status": None, "years_exp": 12, "gsis_id": "00-0011111"},
    "7777": {"player_id": "7777", "full_name": "Hurt Receiver", "position": "WR", "fantasy_positions": ["WR"],
             "active": True, "status": "Injured Reserve", "team": "DAL", "injury_status": "IR", "years_exp": 3, "gsis_id": "00-0033333"},
    # suffix and nickname variants seen live: "Omar Cooper Jr." vs "Omar Cooper", "Matthew Hibner" vs "Matt Hibner"
    "13276": {"player_id": "13276", "full_name": "Omar Cooper", "position": "WR", "fantasy_positions": ["WR"], "active": True,
              "status": "Active", "team": "NYJ", "years_exp": 0, "gsis_id": None, "last_name": "Cooper"},
    "13324": {"player_id": "13324", "full_name": "Matt Hibner", "position": "TE", "fantasy_positions": ["TE"], "active": True,
              "status": "Active", "team": "BAL", "years_exp": 0, "gsis_id": None, "last_name": "Hibner"},
    "13345": {"player_id": "13345", "full_name": "Jonah Coleman", "position": "RB", "fantasy_positions": ["RB"], "active": True,
              "status": "Active", "team": "DEN", "years_exp": 0, "gsis_id": None, "last_name": "Coleman"},
    "8888": {"player_id": "8888", "full_name": "No Flags", "position": "WR", "active": None, "status": None, "team": "FA",
             "gsis_id": "00-0022222"},
    # Sleeper pads some gsis ids with a leading space (seen live: " 00-0035057"); it must still match.
    "13269": {"player_id": "13269", "full_name": "Fernando Mendoza", "position": "QB", "fantasy_positions": ["QB"],
              "active": True, "status": "Active", "team": "LV", "years_exp": 0, "gsis_id": " 00-0041562"},
    "MIN": {"player_id": "MIN", "position": "DEF", "fantasy_positions": ["DEF"], "active": True},
}


def test_extract_reads_only_the_eligibility_fields_and_keeps_missing_as_unknown():
    frame = extract_players(PAYLOAD).set_index("sleeper_id")
    assert list(frame.columns) == ["full_name", "position", "fantasy_positions", "active", "status", "team",
                                   "injury_status", "years_exp", "gsis_id"]
    assert frame.loc["13516", "fantasy_positions"] == "RB"
    assert frame.loc["12530", "fantasy_positions"] == "WR|DB"
    assert frame.loc["8888", "fantasy_positions"] is None and frame.loc["8888", "active"] is None
    assert "MIN" in frame.index  # team defenses are kept as rows; nothing is silently dropped


def test_classification_keeps_rostered_players_and_never_suppresses_on_a_flag():
    frame = extract_players(PAYLOAD).set_index("sleeper_id")
    rostered = {"9999"}
    assert classify_availability(frame.loc["9999"], rostered) == "rostered"           # inactive flag irrelevant
    assert classify_availability(frame.loc["13516"], rostered) == "active_free"
    assert classify_availability(frame.loc["7777"], rostered) == "active_free"        # injured reserve is an NFL roster status
    assert classify_availability(frame.loc["8888"], rostered) == "unknown_free"       # flags missing → unknown
    assert classify_availability(frame.loc["9999"], set()) == "inactive_free"         # active False / status Inactive


def test_reconcile_matches_rookies_by_gsis_then_name_and_reports_eligibility_from_fantasy_positions_only():
    players = extract_players(PAYLOAD)
    rookies = pd.DataFrame({
        "gsis_id": ["00-0041562", "00-0041081", "00-0041511", "00-0040879", "00-0041529"],
        "name": ["Fernando Mendoza", "Max Bredeson", "Omar Cooper Jr.", "Matthew Hibner", "Kevin Coleman Jr."],
        "position": ["QB", "TE", "WR", "TE", "WR"], "position_current": ["QB", "RB", "WR", "TE", "WR"],
        "pick": [1, 159, 30, 133, 177], "draft_season": [2026] * 5, "team": ["LV", "MIN", "NYJ", "BAL", "MIA"],
    })
    out = reconcile(players, rookies=rookies, extra_ids={"12530", "8888"}, pool_ids=set(), rostered_ids={"12530"})
    got = out.set_index("sleeper_id")
    assert got.loc["13269", "match_basis"] == "gsis_id" and got.loc["13516", "match_basis"] == "name+position"
    assert got.loc["13276", "match_basis"] == "name+position"                      # suffix "Jr." ignored
    assert got.loc["13324", "match_basis"] == "last_name+team+position+rookie"     # Matthew vs Matt
    # Kevin Coleman Jr. has no Sleeper row here and Jonah Coleman must NOT be taken for him
    unmatched = out.loc[out["match_basis"] == "unmatched", "name"].tolist()
    assert unmatched == ["Kevin Coleman Jr."]
    assert got.loc["13516", "league_eligibility"] == "RB"            # Sleeper fantasy_positions, not TE/FB
    assert got.loc["12530", "league_eligibility"] == "WR|DB" and got.loc["12530", "availability_class"] == "rostered"
    assert got.loc["8888", "league_eligibility"] == "unknown"        # missing field stays unknown
    assert got.loc["13516", "draft_position"] == "TE" and got.loc["13516", "position_current_nflverse"] == "RB"
    assert set(got["source"]) == {"rookie", "extra"}
