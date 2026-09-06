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

import numpy as np
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


# ── player-week components: weekly counts are the authority, play-by-play supplies the split ───

CHAMPIONSHIP_WEEKS = range(1, 18)
UNRESOLVED_LOST = "pbp_lost_count_disagrees_with_weekly"
UNRESOLVED_TD = "pbp_recovery_td_count_disagrees_with_weekly"
UNRESOLVED_ST_TD = "recovery_td_on_special_teams_no_ground_truth"
UNRESOLVED_EVENT = "event_ambiguous_or_missing_id"
SPLIT_COLUMNS = ("pbp_fumbles_lost", "pbp_recovery_tds", "st_forced_fumbles", "st_opp_recoveries", "st_own_recoveries",
                 "non_st_forced_fumbles", "non_st_opp_recoveries", "own_recoveries", "st_recovery_tds",
                 "problem_events", "capacity_plays", "capacity_plays_needing_split")


def _count(events: pd.DataFrame, mask: pd.Series) -> pd.Series:
    sub = events[mask].dropna(subset=["player_id"])
    return sub.groupby(["player_id", "week"]).size()


def player_week_components(weekly: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    w = weekly[weekly["season_type"] == "REG"].copy()
    if w.duplicated(["player_id", "week"]).any():
        raise ScoringAuditError("duplicate (player_id, week) rows in the weekly source")
    for c in WEEKLY_COMPONENT_COLUMNS:
        w[c] = _num(w, c)
    w["extra_fumbles_lost"] = (w["fumbles_lost_total"] - w["sack_fumbles_lost"] - w["rushing_fumbles_lost"]
                              - w["receiving_fumbles_lost"]).clip(lower=0)
    idx = pd.MultiIndex.from_frame(w[["player_id", "week"]])

    def col(series: pd.Series) -> np.ndarray:
        return series.reindex(idx).fillna(0).to_numpy(dtype=int) if len(series) else np.zeros(len(w), dtype=int)

    for c in SPLIT_COLUMNS:
        w[c] = 0
    live = events[events["status"] != "nullified"] if len(events) else events
    ok = live[live["status"] == "attributed"] if len(live) else live
    if len(ok):
        is_fum, is_rec, is_ff, is_td = (ok.event_type == t for t in ("fumble", "recovery", "forced_fumble", "recovery_td"))
        st = ok.special_teams.astype(bool)
        own = ok.own_team.fillna(False).astype(bool)
        w["pbp_fumbles_lost"] = col(_count(ok, is_fum & ok.lost.fillna(False).astype(bool)))
        w["pbp_recovery_tds"] = col(_count(ok, is_td))
        w["st_recovery_tds"] = col(_count(ok, is_td & st))
        w["st_forced_fumbles"] = col(_count(ok, is_ff & st))
        w["st_opp_recoveries"] = col(_count(ok, is_rec & st & ~own))
        w["st_own_recoveries"] = col(_count(ok, is_rec & st & own))
        w["non_st_forced_fumbles"] = col(_count(ok, is_ff & ~st))
        w["non_st_opp_recoveries"] = col(_count(ok, is_rec & ~st & ~own))
        w["own_recoveries"] = col(_count(ok, is_rec & own))
    if len(live):
        cap = live[(live.status == "ambiguous") & (live.ambiguity_reason == AMBIGUITY_CAPACITY)]
        # only special-teams credits depend on the slot pairing (own vs opponent ball); on offensive plays
        # no recovery or forced fumble is ever credited, and the weekly counts stay the authority
        cap_needs_split = cap[cap.special_teams.astype(bool)]
        other_bad = live[live.status.isin(["missing_id", "ambiguous"]) & (live.ambiguity_reason != AMBIGUITY_CAPACITY)]
        w["capacity_plays"] = col(_count(cap, pd.Series(True, index=cap.index))) if len(cap) else 0
        w["capacity_plays_needing_split"] = col(_count(cap_needs_split, pd.Series(True, index=cap_needs_split.index))) if len(cap_needs_split) else 0
        w["problem_events"] = col(_count(other_bad, pd.Series(True, index=other_bad.index))) if len(other_bad) else 0
    w["championship_window"] = w["week"].isin(list(CHAMPIONSHIP_WEEKS))
    skip = w["capacity_plays"] > 0
    lost_ok = w["pbp_fumbles_lost"] == w["fumbles_lost_total"]
    w["cross_check"] = np.select([skip, lost_ok], ["skipped_capacity_ambiguity", "ok"], default="disagrees")
    reason = pd.Series("", index=w.index, dtype=object)
    reason[((w["problem_events"] > 0) | (w["capacity_plays_needing_split"] > 0)) & (reason == "")] = UNRESOLVED_EVENT
    reason[(w["cross_check"] == "disagrees") & (reason == "")] = UNRESOLVED_LOST
    reason[(~skip) & (w["pbp_recovery_tds"] != w["fumble_recovery_tds"]) & (reason == "")] = UNRESOLVED_TD
    reason[(w["st_recovery_tds"] > 0) & (reason == "")] = UNRESOLVED_ST_TD
    w["unresolved_reason"] = reason
    w["attribution_status"] = np.where(reason == "", "attributed", "unresolved")
    return w.reset_index(drop=True)


# ── league points: individual keys only, weights read from the saved settings ─────────────────

def league_points(components: pd.DataFrame, settings: dict) -> pd.Series:
    """Individual keys only. A team or kicker key present in `settings` is ignored for a player;
    an IDP setting is never inferred from a DST key."""
    s = {k: float(v) for k, v in settings.items() if k in INDIVIDUAL_KEYS}
    c = components

    def g(key: str) -> float:
        return s.get(key, 0.0)

    lost = (_num(c, "sack_fumbles_lost") + _num(c, "rushing_fumbles_lost") + _num(c, "receiving_fumbles_lost")
            + _num(c, "extra_fumbles_lost"))
    return (g("pass_yd") * _num(c, "passing_yards") + g("pass_td") * _num(c, "passing_tds")
            + g("pass_int") * _num(c, "passing_interceptions") + g("pass_2pt") * _num(c, "passing_2pt_conversions")
            + g("rush_yd") * _num(c, "rushing_yards") + g("rush_td") * _num(c, "rushing_tds")
            + g("rush_2pt") * _num(c, "rushing_2pt_conversions")
            + g("rec") * _num(c, "receptions") + g("rec_yd") * _num(c, "receiving_yards") + g("rec_td") * _num(c, "receiving_tds")
            + g("rec_2pt") * _num(c, "receiving_2pt_conversions")
            + g("fum") * _num(c, "fumbles_total") + g("fum_lost") * lost
            + g("fum_rec_td") * _num(c, "fumble_recovery_tds") + g("st_td") * _num(c, "special_teams_tds")
            + g("st_ff") * _num(c, "st_forced_fumbles") + g("st_fum_rec") * _num(c, "st_opp_recoveries"))
