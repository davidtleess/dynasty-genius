"""DG-177 league scoring component audit (2025): pure attribution + scoring + reconciliation.

Weekly nflverse totals are the authority for component COUNTS; play-by-play supplies the event
grain (game_id, play_id, event_slot, player_id) and the special-teams / own-vs-opponent / lost
split. Whenever the two disagree the player-week is `unresolved`; nothing is patched.

Only INDIVIDUAL keys are ever credited to a player. Team-defense keys (ff, fum_rec, int, sack,
safe, blk_kick, def_*, pts_allow_*) are classified `team` and never applied to an individual;
no IDP setting is inferred from them (Sleeper scores defensive stats for individuals only under
idp_* keys, which this league does not set).
"""
from __future__ import annotations

import pandas as pd


class ScoringAuditError(ValueError):
    """A source or settings condition under which the audit refuses to proceed."""


WEEKLY_COMPONENT_COLUMNS = (
    "passing_yards", "passing_tds", "passing_interceptions", "passing_2pt_conversions",
    "rushing_yards", "rushing_tds", "rushing_2pt_conversions",
    "receptions", "receiving_yards", "receiving_tds", "receiving_2pt_conversions",
    "sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost", "special_teams_tds",
    "fumbles_total", "fumbles_lost_total", "fumble_recovery_own", "fumble_recovery_opp", "fumble_recovery_tds",
    "def_fumbles_forced", "fantasy_points_ppr",
)

# nflverse's saved research preset, written out so a test can prove the reproduction is exact.
RESEARCH_PPR_PRESET = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "fum_lost_offense": -2.0,     # sack + rushing + receiving fumbles lost ONLY
    "st_td": 6.0,
}

INDIVIDUAL_KEYS = frozenset({
    "pass_yd", "pass_td", "pass_int", "pass_2pt", "rush_yd", "rush_td", "rush_2pt",
    "rec", "rec_yd", "rec_td", "rec_2pt", "fum", "fum_lost", "fum_rec_td", "st_td", "st_ff", "st_fum_rec",
})
KICKER_KEYS = frozenset({"fgm_0_19", "fgm_20_29", "fgm_30_39", "fgm_40_49", "fgm_50p", "fgmiss", "xpm", "xpmiss"})
TEAM_KEYS = frozenset({
    "ff", "fum_rec", "int", "sack", "safe", "blk_kick", "def_td",
    "def_st_ff", "def_st_fum_rec", "def_st_td",
    "pts_allow_0", "pts_allow_1_6", "pts_allow_7_13", "pts_allow_14_20", "pts_allow_21_27", "pts_allow_28_34", "pts_allow_35p",
})


def classify_scoring_keys(settings: dict) -> dict:
    keys = set(settings)
    return {
        "individual": sorted(keys & INDIVIDUAL_KEYS),
        "kicker": sorted(keys & KICKER_KEYS),
        "team": sorted(keys & TEAM_KEYS),
        "unknown": sorted(keys - INDIVIDUAL_KEYS - KICKER_KEYS - TEAM_KEYS),
    }


def _num(frame: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(frame[col], errors="coerce").fillna(0.0).astype(float)


def research_ppr_from_components(weekly: pd.DataFrame) -> pd.Series:
    p = RESEARCH_PPR_PRESET
    w = weekly
    lost = _num(w, "sack_fumbles_lost") + _num(w, "rushing_fumbles_lost") + _num(w, "receiving_fumbles_lost")
    two = _num(w, "passing_2pt_conversions") + _num(w, "rushing_2pt_conversions") + _num(w, "receiving_2pt_conversions")
    return (p["pass_yd"] * _num(w, "passing_yards") + p["pass_td"] * _num(w, "passing_tds")
            + p["pass_int"] * _num(w, "passing_interceptions") + p["rush_yd"] * _num(w, "rushing_yards")
            + p["rush_td"] * _num(w, "rushing_tds") + p["rec"] * _num(w, "receptions")
            + p["rec_yd"] * _num(w, "receiving_yards") + p["rec_td"] * _num(w, "receiving_tds")
            + p["pass_2pt"] * two + p["fum_lost_offense"] * lost + p["st_td"] * _num(w, "special_teams_tds"))

