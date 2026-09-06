"""DG-177 league scoring component audit: pure attribution/scoring contract tests.

Fixtures use synthetic ids (P1, P2, ...) and teams (AAA, BBB). No player names, no real data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dynasty_genius.eval import league_scoring_audit as lsa

SETTINGS = {  # the saved league settings, verbatim from league-20260906T130052Z/snapshot.json
    "blk_kick": 2.0, "def_st_ff": 1.0, "def_st_fum_rec": 1.0, "def_st_td": 6.0, "def_td": 6.0, "ff": 1.0,
    "fgm_0_19": 3.0, "fgm_20_29": 3.0, "fgm_30_39": 3.0, "fgm_40_49": 4.0, "fgm_50p": 5.0, "fgmiss": -1.0,
    "fum": 0.0, "fum_lost": -2.0, "fum_rec": 2.0, "fum_rec_td": 6.0, "int": 2.0, "pass_2pt": 2.0,
    "pass_int": -2.0, "pass_td": 4.0, "pass_yd": 0.04, "pts_allow_0": 10.0, "pts_allow_14_20": 1.0,
    "pts_allow_1_6": 7.0, "pts_allow_21_27": 0.0, "pts_allow_28_34": -1.0, "pts_allow_35p": -4.0,
    "pts_allow_7_13": 4.0, "rec": 1.0, "rec_2pt": 2.0, "rec_td": 6.0, "rec_yd": 0.1, "rush_2pt": 2.0,
    "rush_td": 6.0, "rush_yd": 0.1, "sack": 1.0, "safe": 2.0, "st_ff": 1.0, "st_fum_rec": 1.0, "st_td": 6.0,
    "xpm": 1.0, "xpmiss": -1.0,
}

WEEKLY_ZERO = {c: 0 for c in lsa.WEEKLY_COMPONENT_COLUMNS}


def weekly_row(player_id, week, *, season_type="REG", position="RB", **over):
    row = {"player_id": player_id, "season": 2025, "week": week, "season_type": season_type, "position": position,
           **WEEKLY_ZERO}
    row.update(over)
    return row


def weekly(rows):
    return pd.DataFrame([weekly_row(**r) if isinstance(r, dict) else r for r in rows])


PBP_DEFAULTS = {"season_type": "REG", "play_type": "run", "special_teams_play": 0, "fumble": 1, "fumble_lost": 0,
                "fumble_out_of_bounds": 0, "play_deleted": 0, "touchdown": 0, "rush_touchdown": 0, "pass_touchdown": 0,
                "return_touchdown": 0, "td_player_id": None, "td_team": None,
                "fumbled_1_player_id": None, "fumbled_1_team": None, "fumbled_2_player_id": None, "fumbled_2_team": None,
                "forced_fumble_player_1_player_id": None, "forced_fumble_player_1_team": None,
                "forced_fumble_player_2_player_id": None, "forced_fumble_player_2_team": None,
                "fumble_recovery_1_player_id": None, "fumble_recovery_1_team": None,
                "fumble_recovery_2_player_id": None, "fumble_recovery_2_team": None, "desc": ""}


def play(game_id, play_id, week, **over):
    row = {"game_id": game_id, "play_id": play_id, "week": week, **PBP_DEFAULTS}
    row.update(over)
    return row


def pbp(rows):
    return pd.DataFrame(rows, columns=list(PBP_DEFAULTS) + ["game_id", "play_id", "week"] if not rows else None)


# ── Task 2: key classification and exact research-PPR reproduction ────────────────────────────

def test_every_saved_key_is_classified_and_unknown_keys_are_named():
    c = lsa.classify_scoring_keys(SETTINGS)
    assert set(c["individual"]) == {"fum", "fum_lost", "fum_rec_td", "pass_2pt", "pass_int", "pass_td", "pass_yd",
                                    "rec", "rec_2pt", "rec_td", "rec_yd", "rush_2pt", "rush_td", "rush_yd",
                                    "st_ff", "st_fum_rec", "st_td"}
    assert set(c["kicker"]) == {"fgm_0_19", "fgm_20_29", "fgm_30_39", "fgm_40_49", "fgm_50p", "fgmiss", "xpm", "xpmiss"}
    assert {"ff", "fum_rec", "int", "sack", "safe", "blk_kick", "def_td"} <= set(c["team"])
    assert c["unknown"] == []
    assert lsa.classify_scoring_keys({**SETTINGS, "bonus_rec_te": 0.5})["unknown"] == ["bonus_rec_te"]


def test_research_ppr_reproduces_exactly_from_the_component_columns():
    w = weekly([
        dict(player_id="P1", week=1, passing_yards=250, passing_tds=2, passing_interceptions=1, rushing_yards=12,
             sack_fumbles_lost=1, passing_2pt_conversions=1, fantasy_points_ppr=250 * 0.04 + 8 - 2 + 1.2 - 2 + 2),
        dict(player_id="P2", week=1, receptions=5, receiving_yards=63, receiving_tds=1, receiving_fumbles_lost=1,
             special_teams_tds=1, fantasy_points_ppr=5 + 6.3 + 6 - 2 + 6),
    ])
    got = lsa.research_ppr_from_components(w)
    assert np.allclose(got.to_numpy(), w["fantasy_points_ppr"].to_numpy(), atol=1e-9)


def test_research_ppr_does_not_use_fumbles_lost_total_or_recovery_fields():
    w = weekly([dict(player_id="P1", week=1, fumbles_lost_total=1, fumble_recovery_own=2, fumble_recovery_tds=1,
                     def_fumbles_forced=1, fantasy_points_ppr=0.0)])
    assert float(lsa.research_ppr_from_components(w).iloc[0]) == 0.0


# ── Task 3: fumble events at (game_id, play_id, event_slot, player_id) ────────────────────────

def test_events_have_unique_grain_and_deterministic_order():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 20, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", forced_fumble_player_1_player_id="D1",
             forced_fumble_player_1_team="BBB", fumble_recovery_1_player_id="D2", fumble_recovery_1_team="BBB", fumble_lost=1),
        play("G1", 10, 1, fumbled_1_player_id="P2", fumbled_1_team="AAA", fumble_recovery_1_player_id="P2",
             fumble_recovery_1_team="AAA"),
    ]))
    # the same player can fumble AND recover in one slot, so the unique grain carries the event type
    assert not ev.duplicated(["game_id", "play_id", "event_slot", "event_type", "player_id"]).any()
    assert ev[["game_id", "play_id"]].drop_duplicates().play_id.tolist() == [10, 20]
    assert set(ev.event_type) == {"fumble", "forced_fumble", "recovery"}


def test_multi_fumble_play_pairs_slot_two_with_its_own_recovery():
    ev = lsa.extract_fumble_events(pbp([play(
        "G1", 5, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
        fumbled_2_player_id="D1", fumbled_2_team="BBB", fumble_recovery_2_player_id="P3", fumble_recovery_2_team="AAA", fumble_lost=1,
        desc="P1 FUMBLES, RECOVERED by BBB-D1. D1 FUMBLES, RECOVERED by AAA-P3.")]))
    f = ev[ev.event_type == "fumble"].set_index("event_slot")
    assert bool(f.loc[1, "lost"]) is True and f.loc[1, "player_id"] == "P1"
    assert bool(f.loc[2, "lost"]) is True and f.loc[2, "player_id"] == "D1"
    r = ev[ev.event_type == "recovery"].set_index("event_slot")
    assert bool(r.loc[1, "own_team"]) is False and bool(r.loc[2, "own_team"]) is False
    assert set(ev.status) == {"attributed"}


def test_nullified_plays_yield_nullified_events_and_no_credit():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, play_type="no_play", fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1),
        play("G1", 2, 1, play_deleted=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA"),
    ]))
    assert set(ev.status) == {"nullified"} and len(ev) == 4


def test_missing_recovery_id_is_recorded_not_dropped():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                                               fumble_recovery_1_player_id=None, fumble_recovery_1_team="BBB", fumble_lost=1)]))
    rec = ev[ev.event_type == "recovery"]
    assert len(rec) == 1 and rec.iloc[0].status == "missing_id" and pd.isna(rec.iloc[0].player_id)
    assert bool(ev[ev.event_type == "fumble"].iloc[0].lost) is True


def test_muffed_punt_is_a_special_teams_lost_fumble_and_out_of_bounds_kept_ball_is_not_lost():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1, desc="MUFFS catch"),
        play("G1", 2, 1, fumbled_1_player_id="P2", fumbled_1_team="AAA", fumble_out_of_bounds=1, fumble_lost=0),
    ]))
    f = ev[ev.event_type == "fumble"].set_index("player_id")
    assert bool(f.loc["P1", "special_teams"]) and bool(f.loc["P1", "lost"]) is True
    assert bool(f.loc["P2", "lost"]) is False and f.loc["P2", "status"] == "attributed"


def test_end_zone_out_of_bounds_loss_is_lost_with_no_invented_recovery_player():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_out_of_bounds=1,
                                               fumble_lost=1, desc="FUMBLES, ball out of bounds in End Zone, TOUCHBACK. TOUCHDOWN REVERSED")]))
    assert len(ev) == 1 and ev.iloc[0].event_type == "fumble"
    assert bool(ev.iloc[0].lost) is True and ev.iloc[0].status == "attributed"


def test_fumble_with_no_recovery_and_no_play_level_flag_is_ambiguous():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_lost=None)]))
    assert ev.iloc[0].status == "ambiguous" and pd.isna(ev.iloc[0].lost)


def test_three_fumbles_in_two_slots_is_a_capacity_ambiguity_for_every_event_of_the_play():
    ev = lsa.extract_fumble_events(pbp([play(
        "G1", 1501, 17, play_type="pass", fumble_lost=1,
        fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
        fumbled_2_player_id="P1", fumbled_2_team="AAA", fumble_recovery_2_player_id="D1", fumble_recovery_2_team="BBB",
        desc="P1 FUMBLES, recovers. P1 FUMBLES, RECOVERED by BBB-D1. D1 FUMBLES, RECOVERED by AAA-P7.")]))
    assert set(ev.status) == {"ambiguous"} and set(ev.ambiguity_reason) == {"slot_capacity"}


def test_recovery_slot_without_a_paired_fumbled_slot_is_a_capacity_ambiguity():
    ev = lsa.extract_fumble_events(pbp([play("G1", 2, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                                               fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
                                               fumble_recovery_2_player_id="P3", fumble_recovery_2_team="AAA", fumble_lost=0,
                                               desc="P1 FUMBLES")]))
    assert set(ev.status) == {"ambiguous"} and set(ev.ambiguity_reason) == {"slot_capacity"}


def test_play_level_lost_flag_disagreeing_with_every_slot_is_a_capacity_ambiguity():
    ev = lsa.extract_fumble_events(pbp([play("G1", 3, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                                               fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=1,
                                               desc="P1 FUMBLES")]))
    assert set(ev.status) == {"ambiguous"} and set(ev.ambiguity_reason) == {"slot_capacity"}


def test_special_teams_classifier_conflict_is_ambiguous_and_agreement_is_special_teams():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 2504, 10, play_type="field_goal", special_teams_play=0, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1, desc="blocked, MUFFS"),
        play("G1", 2600, 10, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="P2", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1),
    ]))
    a = ev[ev.play_id == 2504]
    assert set(a.status) == {"ambiguous"} and set(a.ambiguity_reason) == {"st_classifier_conflict"}
    b = ev[ev.play_id == 2600]
    assert set(b.status) == {"attributed"} and b.special_teams.all()


def test_recovery_touchdown_is_emitted_only_without_an_overlapping_rush_or_pass_touchdown():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P1",
             fumble_recovery_1_team="AAA", touchdown=1, return_touchdown=1, td_player_id="P1", td_team="AAA", desc="P9 FUMBLES"),
        play("G1", 2, 1, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P2",
             fumble_recovery_1_team="AAA", touchdown=1, rush_touchdown=1, td_player_id="P2", td_team="AAA", desc="P9 FUMBLES"),
    ]))
    td = ev[ev.event_type == "recovery_td"]
    assert td.player_id.tolist() == ["P1"] and td.iloc[0].status == "attributed"
    p2 = ev[(ev.player_id == "P2") & (ev.event_type == "recovery")]
    assert p2.iloc[0].status == "ambiguous" and p2.iloc[0].ambiguity_reason == "overlapping_touchdown"


def test_description_touchdown_text_never_creates_a_recovery_touchdown():
    ev = lsa.extract_fumble_events(pbp([play("G1", 7, 1, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P1",
                                               fumble_recovery_1_team="AAA", touchdown=0, desc="P9 FUMBLES, RECOVERED by AAA-P1. TOUCHDOWN. REVERSED.")]))
    assert "recovery_td" not in set(ev.event_type)


def test_empty_play_by_play_yields_an_empty_ledger_with_the_full_schema():
    ev = lsa.extract_fumble_events(pbp([]))
    assert len(ev) == 0 and {"game_id", "play_id", "event_slot", "event_type", "player_id", "status", "ambiguity_reason"} <= set(ev.columns)
