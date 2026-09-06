"""DG-177 league scoring component audit: pure attribution/scoring contract tests.

Fixtures use synthetic ids (P1, P2, ...) and teams (AAA, BBB). No player names, no real data.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

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


# ── Task 4: player-week components, cross-checks, championship label ──────────────────────────

def _events(rows):
    return lsa.extract_fumble_events(pbp(rows))


def test_components_split_special_teams_from_offense_and_flag_the_window():
    w = weekly([dict(player_id="P1", week=17, fumbles_lost_total=1, receiving_fumbles_lost=0),
                dict(player_id="P1", week=18, fumbles_lost_total=0)])
    ev = _events([play("G1", 1, 17, play_type="punt", special_teams_play=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                       fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1, desc="MUFFS, FUMBLES")])
    c = lsa.player_week_components(w, ev).set_index("week")
    assert int(c.loc[17, "extra_fumbles_lost"]) == 1 and int(c.loc[17, "pbp_fumbles_lost"]) == 1
    assert bool(c.loc[17, "championship_window"]) is True and bool(c.loc[18, "championship_window"]) is False
    assert c.loc[17, "attribution_status"] == "attributed" and c.loc[17, "cross_check"] == "ok"


def test_st_forced_and_opponent_recovery_by_the_same_player_count_once_each():
    w = weekly([dict(player_id="P1", week=13, def_fumbles_forced=1, fumble_recovery_opp=1)])
    ev = _events([play("G1", 722, 13, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="R1", fumbled_1_team="BBB",
                       forced_fumble_player_1_player_id="P1", forced_fumble_player_1_team="AAA",
                       fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=1, desc="FUMBLES")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert int(c.st_forced_fumbles) == 1 and int(c.st_opp_recoveries) == 1 and int(c.st_own_recoveries) == 0
    assert c.attribution_status == "attributed"


def test_own_team_special_teams_recovery_is_counted_attributed_and_never_credited():
    # root's ground truth: a kickoff recovered by a teammate of the fumbler; Sleeper paid nothing
    w = weekly([dict(player_id="P1", week=5, receptions=2, receiving_yards=27, fumble_recovery_own=1, fantasy_points_ppr=4.7)])
    ev = _events([play("G1", 1358, 5, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="P5", fumbled_1_team="AAA",
                       fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=0, desc="FUMBLES")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert int(c.st_own_recoveries) == 1 and int(c.st_opp_recoveries) == 0 and c.attribution_status == "attributed"


def test_capacity_ambiguous_offensive_play_keeps_weekly_lost_total_as_authority():
    w = weekly([dict(player_id="P1", week=17, passing_yards=200, sack_fumbles_lost=1, fumbles_lost_total=1)])
    ev = _events([play("G1", 1501, 17, play_type="pass", fumble_lost=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                       fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumbled_2_player_id="P1", fumbled_2_team="AAA",
                       fumble_recovery_2_player_id="D1", fumble_recovery_2_team="BBB",
                       desc="P1 FUMBLES, recovers. P1 FUMBLES, RECOVERED by BBB-D1. D1 FUMBLES, RECOVERED by AAA-P7.")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert c.cross_check == "skipped_capacity_ambiguity" and c.attribution_status == "attributed"
    assert int(c.extra_fumbles_lost) == 0


def test_capacity_ambiguous_special_teams_play_makes_the_week_unresolved():
    w = weekly([dict(player_id="P1", week=3, fumbles_lost_total=1)])
    ev = _events([play("G1", 9, 3, play_type="punt", special_teams_play=1, fumble_lost=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                       fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
                       desc="MUFFS, FUMBLES, FUMBLES again")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert c.attribution_status == "unresolved" and c.unresolved_reason == "event_ambiguous_or_missing_id"


def test_recovery_touchdown_on_a_special_teams_play_has_no_ground_truth_and_is_unresolved():
    w = weekly([dict(player_id="P1", week=6, special_teams_tds=1, fumble_recovery_tds=1, fumble_recovery_opp=1)])
    ev = _events([play("G1", 40, 6, play_type="punt", special_teams_play=1, fumbled_1_player_id="R1", fumbled_1_team="BBB",
                       fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=1,
                       touchdown=1, return_touchdown=1, td_player_id="P1", td_team="AAA", desc="FUMBLES")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert c.attribution_status == "unresolved" and c.unresolved_reason == "recovery_td_on_special_teams_no_ground_truth"


def test_weekly_and_pbp_lost_counts_must_agree_or_the_week_is_unresolved():
    w = weekly([dict(player_id="P1", week=3, fumbles_lost_total=2, rushing_fumbles_lost=1)])
    ev = _events([play("G1", 1, 3, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_recovery_1_player_id="D1",
                       fumble_recovery_1_team="BBB", fumble_lost=1, desc="FUMBLES")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert c.cross_check == "disagrees"
    assert c.attribution_status == "unresolved" and c.unresolved_reason == "pbp_lost_count_disagrees_with_weekly"


def test_extra_lost_fumble_with_an_uncredited_opponent_recovery_on_the_same_offensive_play():
    # root's ground truth: an interception returned and fumbled; the passer recovers (opponent ball, offensive play)
    # and later loses a fumble on a non-rush/pass play: Sleeper paid −2 and nothing for the recovery
    w = weekly([dict(player_id="P1", week=14, passing_yards=240, rushing_yards=8, fumbles_lost_total=1, fumble_recovery_opp=1)])
    ev = _events([play("G1", 1390, 14, play_type="pass", fumble_lost=1, fumbled_1_player_id="D1", fumbled_1_team="BBB",
                       forced_fumble_player_1_player_id="P8", forced_fumble_player_1_team="AAA",
                       fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
                       fumbled_2_player_id="P1", fumbled_2_team="AAA", fumble_recovery_2_player_id="D2", fumble_recovery_2_team="BBB",
                       desc="INTERCEPTED. FUMBLES, RECOVERED by AAA-P1. FUMBLES, RECOVERED by BBB-D2.")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert int(c.non_st_opp_recoveries) == 1 and int(c.pbp_fumbles_lost) == 1 and c.attribution_status == "attributed"


def test_overlapping_touchdown_makes_the_recovery_td_week_unresolved():
    w = weekly([dict(player_id="P2", week=4, rushing_tds=1, fumble_recovery_tds=1, fumble_recovery_own=1)])
    ev = _events([play("G1", 1, 4, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P2",
                       fumble_recovery_1_team="AAA", touchdown=1, rush_touchdown=1, td_player_id="P2", td_team="AAA", desc="FUMBLES")])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert c.attribution_status == "unresolved"
    assert c.unresolved_reason in ("pbp_recovery_td_count_disagrees_with_weekly", "event_ambiguous_or_missing_id")


def test_nullified_events_never_reach_components():
    w = weekly([dict(player_id="P1", week=5)])
    ev = _events([play("G1", 1, 5, play_type="no_play", fumbled_1_player_id="P1", fumbled_1_team="AAA",
                       fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1)])
    c = lsa.player_week_components(w, ev).iloc[0]
    assert int(c.pbp_fumbles_lost) == 0 and c.attribution_status == "attributed"


def test_weekly_only_lost_fumble_with_no_play_is_unresolved_not_credited_silently():
    w = weekly([dict(player_id="P1", week=2, fumbles_lost_total=1)])
    c = lsa.player_week_components(w, _events([])).iloc[0]
    assert c.attribution_status == "unresolved" and c.unresolved_reason == "pbp_lost_count_disagrees_with_weekly"


def test_duplicate_weekly_player_weeks_are_refused():
    w = weekly([dict(player_id="P1", week=1), dict(player_id="P1", week=1)])
    with pytest.raises(lsa.ScoringAuditError, match="duplicate"):
        lsa.player_week_components(w, _events([]))


# ── Task 5: league points credit individual keys only ─────────────────────────────────────────

def _components(rows, events=None):
    return lsa.player_week_components(weekly(rows), events if events is not None else lsa.extract_fumble_events(pbp([])))


def test_own_recovery_is_never_a_bonus_and_fum_rec_key_is_never_applied_to_an_individual():
    c = _components([dict(player_id="P1", week=1, rushing_yards=50, fumble_recovery_own=2)])
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == 5.0
    assert float(lsa.league_points(c, {**SETTINGS, "fum_rec": 99.0}).iloc[0]) == 5.0


def test_team_defense_keys_do_not_reach_a_two_way_player():
    c = _components([dict(player_id="P1", week=1, position="CB", receptions=3, receiving_yards=42)])
    c["def_interceptions"] = 1
    c["def_fumbles_forced"] = 1
    assert float(lsa.league_points(c, {**SETTINGS, "int": 50.0, "ff": 50.0}).iloc[0]) == pytest.approx(3 + 4.2)


def test_recovery_touchdown_scores_fum_rec_td_without_a_recovery_bonus():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 15, fumbled_1_player_id="P9", fumbled_1_team="AAA",
                                             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
                                             touchdown=1, return_touchdown=1, td_player_id="P1", td_team="AAA", desc="FUMBLES")]))
    c = _components([dict(player_id="P1", week=15, rushing_yards=30, receptions=1, receiving_yards=8,
                          fumble_recovery_own=1, fumble_recovery_tds=1)], ev)
    assert c.iloc[0].attribution_status == "attributed"
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == pytest.approx(3 + 1 + 0.8 + 6)


def test_special_teams_keys_credit_individuals_and_weights_come_from_settings():
    ev = lsa.extract_fumble_events(pbp([play("G1", 722, 13, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="R1",
                                             fumbled_1_team="BBB", forced_fumble_player_1_player_id="P1", forced_fumble_player_1_team="AAA",
                                             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=1, desc="FUMBLES")]))
    c = _components([dict(player_id="P1", week=13, def_fumbles_forced=1, fumble_recovery_opp=1)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == 2.0
    assert float(lsa.league_points(c, {**SETTINGS, "st_ff": 3.0, "st_fum_rec": 0.5}).iloc[0]) == 3.5


def test_own_team_special_teams_recovery_scores_nothing():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1358, 5, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="P5",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
                                             fumble_lost=0, desc="FUMBLES")]))
    c = _components([dict(player_id="P1", week=5, receptions=2, receiving_yards=27, fumble_recovery_own=1, fantasy_points_ppr=4.7)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == pytest.approx(4.7)


def test_muffed_return_lost_fumble_costs_fum_lost_and_negative_totals_are_preserved():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="P1",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
                                             fumble_lost=1, desc="MUFFS, FUMBLES")]))
    c = _components([dict(player_id="P1", week=1, fumbles_lost_total=1)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == -2.0
    assert float(lsa.research_ppr_from_components(c).iloc[0]) == 0.0


def test_fum_key_with_zero_weight_is_modelled_from_fumbles_total_not_dropped():
    c = _components([dict(player_id="P1", week=1, fumbles_total=2, fumble_recovery_own=2)])
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == 0.0
    assert float(lsa.league_points(c, {**SETTINGS, "fum": -1.0}).iloc[0]) == -2.0


def test_league_points_apply_the_weekly_lost_count_while_the_row_stays_unresolved():
    c = _components([dict(player_id="P1", week=3, fumbles_lost_total=2, rushing_fumbles_lost=1)])
    assert c.iloc[0].attribution_status == "unresolved"
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == -4.0


# ── Task 6: Sleeper ground truth, identity mapping, settings check, reconciliation ────────────

def _season_dir(tmp_path, weeks, settings=SETTINGS):
    d = tmp_path / "season_2025_1"
    d.mkdir()
    (d / "league.json").write_text(json.dumps({"payload": {"season": "2025", "scoring_settings": settings}}))
    for wk, matchups in weeks.items():
        (d / f"matchups_week_{wk:02d}.json").write_text(json.dumps({"payload": matchups}))
    return d


def test_sleeper_points_load_with_identical_duplicates_collapsed_and_conflicts_flagged(tmp_path):
    d = _season_dir(tmp_path, {1: [{"roster_id": 1, "players_points": {"11": 4.5, "12": 0.0}},
                                   {"roster_id": 2, "players_points": {"11": 4.5, "13": 2.0}},
                                   {"roster_id": 3, "players_points": {"13": 7.0}}]})
    s = lsa.load_sleeper_week_points(d).set_index("sleeper_id")
    assert len(s) == 3
    assert s.loc["11", "status"] == "ok" and int(s.loc["11", "duplicates_collapsed"]) == 1
    assert s.loc["12", "status"] == "ok" and int(s.loc["12", "duplicates_collapsed"]) == 0
    assert s.loc["13", "status"] == "conflicting_duplicate"


def test_settings_mismatch_is_refused_by_key_and_the_sha_is_order_independent(tmp_path):
    d = _season_dir(tmp_path, {}, settings={**SETTINGS, "rec": 0.5})
    with pytest.raises(lsa.ScoringAuditError, match="rec"):
        lsa.assert_settings_match(SETTINGS, lsa.load_sleeper_settings(d))
    assert lsa.settings_sha256(SETTINGS) == lsa.settings_sha256(dict(reversed(list(SETTINGS.items()))))
    lsa.assert_settings_match(SETTINGS, dict(SETTINGS))


def test_identity_map_marks_unmapped_and_ambiguous_ids():
    idmap = pd.DataFrame({"sleeper_id": ["11", "12", "12", "14"], "gsis_id": ["00-1", "00-2", "00-3", None]})
    m = lsa.map_sleeper_ids(pd.Series(["11", "12", "99", "14"]), idmap).set_index("sleeper_id")
    assert m.loc["11", "identity_status"] == "resolved" and m.loc["11", "gsis_id"] == "00-1"
    assert m.loc["12", "identity_status"] == "ambiguous" and pd.isna(m.loc["12", "gsis_id"])
    assert m.loc["99", "identity_status"] == "unmapped" and m.loc["14", "identity_status"] == "unmapped"


def test_reconciliation_statuses_cover_exact_attributed_unresolved_and_absent_zero():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="00-2",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
                                             fumble_lost=1, desc="MUFFS, FUMBLES")]))
    comps = _components([dict(player_id="00-1", week=1, receptions=2, receiving_yards=20, fantasy_points_ppr=4.0),
                         dict(player_id="00-2", week=1, receptions=3, receiving_yards=12, fumbles_lost_total=1, fantasy_points_ppr=4.2),
                         dict(player_id="00-3", week=1, rushing_yards=10, fantasy_points_ppr=1.0)], ev)
    sleeper = pd.DataFrame({"week": [1, 1, 1, 1, 1], "sleeper_id": ["11", "12", "13", "14", "15"],
                            "sleeper_points": [4.0, 2.2, 1.5, 0.0, 3.0], "roster_id": 1, "status": "ok", "duplicates_collapsed": 0})
    identity = pd.DataFrame({"sleeper_id": ["11", "12", "13", "14", "15"], "gsis_id": ["00-1", "00-2", "00-3", None, None],
                             "identity_status": ["resolved", "resolved", "resolved", "unmapped", "unmapped"]})
    r = lsa.reconcile(comps, sleeper, identity, SETTINGS).set_index("sleeper_id")
    assert r.loc["11", "status"] == "exact"
    assert r.loc["12", "status"] == "attributed_difference" and r.loc["12", "diff_vs_research"] == pytest.approx(-2.0)
    assert r.loc["13", "status"] == "unresolved" and r.loc["13", "reconciliation_reason"] == "source_difference"
    assert r.loc["14", "status"] == "absent_zero"
    assert r.loc["15", "status"] == "unresolved" and r.loc["15", "reconciliation_reason"] == "no_identity"


def test_reconciliation_never_credits_an_unresolved_attribution_as_exact():
    comps = _components([dict(player_id="00-1", week=3, fumbles_lost_total=2, rushing_fumbles_lost=1, fantasy_points_ppr=-2.0)])
    sleeper = pd.DataFrame({"week": [3], "sleeper_id": ["11"], "sleeper_points": [-4.0], "roster_id": 1, "status": "ok", "duplicates_collapsed": 0})
    identity = pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"], "identity_status": ["resolved"]})
    r = lsa.reconcile(comps, sleeper, identity, SETTINGS).iloc[0]
    assert r.status == "unresolved" and r.reconciliation_reason == "component_attribution_unresolved"


def test_reconciliation_flags_nonzero_points_without_a_stat_row_and_conflicting_duplicates():
    comps = _components([dict(player_id="00-1", week=2, receptions=1, fantasy_points_ppr=1.0)])
    sleeper = pd.DataFrame({"week": [2, 2], "sleeper_id": ["11", "12"], "sleeper_points": [1.0, 3.0], "roster_id": 1,
                            "status": ["conflicting_duplicate", "ok"], "duplicates_collapsed": [1, 0]})
    identity = pd.DataFrame({"sleeper_id": ["11", "12"], "gsis_id": ["00-1", "00-9"], "identity_status": ["resolved", "resolved"]})
    r = lsa.reconcile(comps, sleeper, identity, SETTINGS).set_index("sleeper_id")
    assert r.loc["11", "status"] == "unresolved" and r.loc["11", "reconciliation_reason"] == "conflicting_duplicate"
    assert r.loc["12", "status"] == "unresolved" and r.loc["12", "reconciliation_reason"] == "no_stat_row_nonzero_points"


def test_reconciliation_labels_week_18_outside_the_championship_window():
    comps = _components([dict(player_id="00-1", week=18, receptions=1, fantasy_points_ppr=1.0)])
    sleeper = pd.DataFrame({"week": [18], "sleeper_id": ["11"], "sleeper_points": [1.0], "roster_id": 1, "status": "ok", "duplicates_collapsed": 0})
    identity = pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"], "identity_status": ["resolved"]})
    r = lsa.reconcile(comps, sleeper, identity, SETTINGS).iloc[0]
    assert r.status == "exact" and bool(r.championship_window) is False


# ── Task 7: quarantine re-audit, coverage counts, exact qualification, manifest ───────────────

def test_quarantine_rows_are_rescored_under_league_keys_with_original_columns_kept():
    q = weekly([dict(player_id=None, week=14, fumbles_lost_total=1, fantasy_points_ppr=-2.0),
                dict(player_id=None, week=1, special_teams_tds=1, fantasy_points_ppr=6.0),
                dict(player_id=None, week=2, fantasy_points_ppr=0.0)])
    q["team"] = ["AAA", "BBB", "CCC"]
    q["quarantine_reason"] = ["unattributed", "unattributed", "placeholder"]
    a = lsa.audit_quarantine(q, SETTINGS)
    assert a.nonzero_under_league_keys.tolist() == [True, True, False]
    assert a.league_points_if_scored.tolist() == [-2.0, 6.0, 0.0]
    assert a.quarantine_reason.tolist() == ["unattributed", "unattributed", "placeholder"]
    assert a.team.tolist() == ["AAA", "BBB", "CCC"]


def test_exact_qualification_is_never_granted_in_this_increment_and_names_its_reasons():
    q = lsa.exact_qualification({"unknown": ["bonus_x"], "kicker": ["xpm"]}, {"status_unresolved": 3}, kicker_rows_present=True)
    assert q["league_scoring_exact"] is False
    assert "rostered player-weeks only; not full-universe proof" in q["reasons"]
    assert any(r.startswith("unknown_scoring_keys") for r in q["reasons"])
    assert "unresolved_player_weeks: 3" in q["reasons"]
    assert "kicker_keys_unsupported_for_present_kickers" in q["reasons"]
    clean = lsa.exact_qualification({"unknown": [], "kicker": []}, {"status_unresolved": 0}, kicker_rows_present=False)
    assert clean["league_scoring_exact"] is False and clean["reasons"] == ["rostered player-weeks only; not full-universe proof", "unresolved_player_weeks: 0"]


def test_coverage_counts_separate_the_championship_window_and_every_status():
    comps = _components([dict(player_id="00-1", week=17), dict(player_id="00-1", week=18)])
    sleeper = pd.DataFrame({"week": [17, 18], "sleeper_id": ["11", "11"], "sleeper_points": [0.0, 0.0], "roster_id": 1,
                            "status": "ok", "duplicates_collapsed": [1, 0]})
    identity = pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"], "identity_status": ["resolved"]})
    rec = lsa.reconcile(comps, sleeper, identity, SETTINGS)
    c = lsa.coverage_counts(comps, rec, sleeper, identity)
    assert c["weekly_player_weeks_reg"] == 2 and c["weekly_player_weeks_championship"] == 1
    assert c["sleeper_player_weeks"] == 2 and c["sleeper_player_weeks_championship"] == 1 and c["sleeper_players"] == 1
    assert c["status_exact"] == 2 and c["status_unresolved"] == 0 and c["status_exact_championship"] == 1
    assert c["sleeper_duplicate_observations_collapsed"] == 1 and c["sleeper_conflicting_duplicates"] == 0
    assert c["population_note"] == "rostered player-weeks only; not full-universe proof"


def test_manifest_carries_schema_sources_settings_sha_and_qualification():
    m = lsa.build_audit_manifest(sources={"weekly": {"path": "w", "sha256": "a" * 64, "bytes": 1}}, settings=SETTINGS,
                                 classification=lsa.classify_scoring_keys(SETTINGS), counts={"status_exact": 1},
                                 qualification={"league_scoring_exact": False, "reasons": ["x"]},
                                 launch={"git_head": "h"}, outputs={"components.csv": "b" * 64})
    assert m["schema_version"] == "dg177_league_scoring_audit_v1"
    assert m["settings_sha256"] == lsa.settings_sha256(SETTINGS)
    assert m["league_scoring_exact"] is False and m["championship_window"] == {"weeks": [1, 17], "week_18_included": False}
    assert "fum_rec" in m["team_keys_never_applied_to_individuals"] and "fum_rec" not in m["individual_keys_credited"]
