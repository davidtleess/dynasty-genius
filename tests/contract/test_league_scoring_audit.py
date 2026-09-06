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
