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



# ── fumble events at (game_id, play_id, event_slot, player_id) ─────────────────────────────────

EVENT_GRAIN = ["game_id", "play_id", "event_slot", "player_id"]
EVENT_COLUMNS = ["game_id", "play_id", "event_slot", "event_type", "player_id", "team", "week", "season_type",
                 "special_teams", "own_team", "lost", "status", "ambiguity_reason", "desc"]
ST_PLAY_TYPES = frozenset({"punt", "kickoff", "field_goal", "extra_point"})
AMBIGUITY_CAPACITY = "slot_capacity"
AMBIGUITY_ST_CONFLICT = "st_classifier_conflict"
AMBIGUITY_OVERLAPPING_TD = "overlapping_touchdown"
AMBIGUITY_NO_RECOVERY_INFO = "no_recovery_and_no_lost_flag"


def _isna(v) -> bool:
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _flag(row, col) -> bool:
    v = row.get(col)
    return (not _isna(v)) and bool(v)


def _play_events(p: pd.Series) -> list[dict]:
    """Events of ONE fumble play. Slot k pairs fumbled_k with fumble_recovery_k; the numbered
    slots are not a universal ledger, so capacity problems mark the whole play ambiguous."""
    nullified = _flag(p, "play_deleted") or p.get("play_type") == "no_play"
    st_flag, st_type = _flag(p, "special_teams_play"), p.get("play_type") in ST_PLAY_TYPES
    desc = p.get("desc", "")
    base = {"game_id": p["game_id"], "play_id": int(p["play_id"]), "week": int(p["week"]), "season_type": p.get("season_type"),
            "special_teams": bool(st_flag and st_type), "desc": "" if _isna(desc) else str(desc)}
    lost_flag = p.get("fumble_lost")
    rows: list[dict] = []
    slot_lost: list[bool | None] = []
    n_fumbled = n_rec_unpaired = 0
    for k in (1, 2):
        fum_id, fum_team = p.get(f"fumbled_{k}_player_id"), p.get(f"fumbled_{k}_team")
        rec_id, rec_team = p.get(f"fumble_recovery_{k}_player_id"), p.get(f"fumble_recovery_{k}_team")
        has_fum, has_rec = not _isna(fum_id), not (_isna(rec_id) and _isna(rec_team))
        if not has_fum and not has_rec:
            continue
        if has_rec and not has_fum:
            n_rec_unpaired += 1
        if has_rec:
            lost = None if _isna(rec_team) or _isna(fum_team) else bool(rec_team != fum_team)
        elif not _isna(lost_flag):
            lost = bool(lost_flag)                      # touchback / out of bounds: the play-level flag decides
        else:
            lost = None
        if has_fum:
            n_fumbled += 1
            slot_lost.append(lost)
            rows.append({**base, "event_slot": k, "event_type": "fumble", "player_id": fum_id, "team": fum_team,
                         "own_team": pd.NA, "lost": pd.NA if lost is None else lost,
                         "status": "attributed" if lost is not None else "ambiguous",
                         "ambiguity_reason": "" if lost is not None else AMBIGUITY_NO_RECOVERY_INFO})
        if has_rec:
            own = None if _isna(rec_team) or _isna(fum_team) else bool(rec_team == fum_team)
            is_td = (_flag(p, "touchdown") and not _isna(rec_id) and p.get("td_player_id") == rec_id
                     and p.get("td_team") == rec_team)
            overlapping = is_td and (_flag(p, "rush_touchdown") or _flag(p, "pass_touchdown"))
            status, reason = "attributed", ""
            if _isna(rec_id):
                status = "missing_id"
            elif overlapping:
                status, reason = "ambiguous", AMBIGUITY_OVERLAPPING_TD
            rows.append({**base, "event_slot": k, "event_type": "recovery", "player_id": rec_id, "team": rec_team,
                         "own_team": pd.NA if own is None else own, "lost": pd.NA, "status": status, "ambiguity_reason": reason})
            if is_td and not overlapping:
                rows.append({**base, "event_slot": k, "event_type": "recovery_td", "player_id": rec_id, "team": rec_team,
                             "own_team": pd.NA if own is None else own, "lost": pd.NA, "status": "attributed", "ambiguity_reason": ""})
        ff_id, ff_team = p.get(f"forced_fumble_player_{k}_player_id"), p.get(f"forced_fumble_player_{k}_team")
        if not (_isna(ff_id) and _isna(ff_team)):
            rows.append({**base, "event_slot": k, "event_type": "forced_fumble", "player_id": ff_id, "team": ff_team,
                         "own_team": pd.NA, "lost": pd.NA, "status": "missing_id" if _isna(ff_id) else "attributed",
                         "ambiguity_reason": ""})
    tokens = base["desc"].upper().count("FUMBLES")
    derived_lost = [x for x in slot_lost if x is not None]
    flag_disagrees = (not _isna(lost_flag)) and bool(derived_lost) and (bool(lost_flag) != any(derived_lost))
    capacity = tokens > n_fumbled or n_rec_unpaired > 0 or flag_disagrees
    conflict = st_flag != st_type
    for r in rows:
        if nullified:
            r["status"], r["ambiguity_reason"] = "nullified", ""
        elif capacity:
            r["status"], r["ambiguity_reason"] = "ambiguous", AMBIGUITY_CAPACITY
        elif conflict:
            r["status"], r["ambiguity_reason"] = "ambiguous", AMBIGUITY_ST_CONFLICT
    return rows


def extract_fumble_events(pbp: pd.DataFrame) -> pd.DataFrame:
    if not len(pbp):
        return pd.DataFrame(columns=EVENT_COLUMNS)
    plays = pbp[pd.to_numeric(pbp["fumble"], errors="coerce").fillna(0) == 1]
    rows = [r for _, p in plays.iterrows() for r in _play_events(p)]
    out = pd.DataFrame(rows, columns=EVENT_COLUMNS)
    out = out.sort_values(["game_id", "play_id", "event_slot", "event_type", "player_id"], na_position="last").reset_index(drop=True)
    dup = out.dropna(subset=["player_id"]).duplicated(EVENT_GRAIN + ["event_type"])
    if dup.any():
        raise ScoringAuditError(f"{int(dup.sum())} duplicate events at the event grain")
    return out
