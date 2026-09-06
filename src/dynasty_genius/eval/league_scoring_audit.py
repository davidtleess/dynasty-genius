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

import hashlib
import json
from pathlib import Path

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


# ── Sleeper ground truth, identity mapping, settings check, reconciliation ────────────────────

TOL = 0.005
RECON_NO_IDENTITY = "no_identity"
RECON_NO_STAT_ROW = "no_stat_row_nonzero_points"
RECON_CONFLICT = "conflicting_duplicate"
RECON_COMPONENT = "component_attribution_unresolved"
RECON_SOURCE = "source_difference"


def load_sleeper_week_points(season_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(season_dir).glob("matchups_week_*.json")):
        week = int(f.stem.rsplit("_", 1)[1])
        for m in json.loads(f.read_bytes())["payload"]:
            for pid, pts in (m.get("players_points") or {}).items():
                rows.append({"week": week, "sleeper_id": str(pid), "sleeper_points": float(pts), "roster_id": m.get("roster_id")})
    df = pd.DataFrame(rows, columns=["week", "sleeper_id", "sleeper_points", "roster_id"])
    if not len(df):
        df["status"] = pd.Series(dtype=object)
        df["duplicates_collapsed"] = pd.Series(dtype=int)
        return df
    n_distinct = df.groupby(["week", "sleeper_id"])["sleeper_points"].transform("nunique")
    n_obs = df.groupby(["week", "sleeper_id"])["sleeper_points"].transform("size")
    df["status"] = np.where(n_distinct > 1, RECON_CONFLICT, "ok")
    df["duplicates_collapsed"] = (n_obs - 1).astype(int)     # equal observations collapsed EXPLICITLY, never double counted
    return df.drop_duplicates(["week", "sleeper_id"], keep="first").reset_index(drop=True)


def load_sleeper_settings(season_dir: Path) -> dict:
    return json.loads((Path(season_dir) / "league.json").read_bytes())["payload"]["scoring_settings"]


def settings_sha256(settings: dict) -> str:
    return hashlib.sha256(json.dumps(settings, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def assert_settings_match(saved: dict, season: dict) -> None:
    diff = sorted(k for k in set(saved) | set(season) if saved.get(k) != season.get(k))
    if diff:
        raise ScoringAuditError(f"season scoring settings differ from the saved snapshot on {diff}")


def map_sleeper_ids(sleeper_ids: pd.Series, idmap: pd.DataFrame) -> pd.DataFrame:
    m = idmap.dropna(subset=["sleeper_id", "gsis_id"]).astype({"sleeper_id": str, "gsis_id": str})
    m = m[(m.sleeper_id.str.strip() != "") & (m.gsis_id.str.strip() != "")].drop_duplicates(["sleeper_id", "gsis_id"])
    counts = m.groupby("sleeper_id")["gsis_id"].nunique()
    one = m[m.sleeper_id.map(counts) == 1].set_index("sleeper_id")["gsis_id"]
    out = pd.DataFrame({"sleeper_id": pd.Series(sleeper_ids.astype(str).unique())})
    out["gsis_id"] = out.sleeper_id.map(one)
    out["identity_status"] = np.select([out.sleeper_id.isin(counts[counts > 1].index), out.gsis_id.notna()],
                                       ["ambiguous", "resolved"], default="unmapped")
    return out


def reconcile(components: pd.DataFrame, sleeper: pd.DataFrame, identity: pd.DataFrame, settings: dict) -> pd.DataFrame:
    comps = components.copy()
    comps["research_ppr"] = research_ppr_from_components(comps)
    comps["league_points"] = league_points(comps, settings)
    keep = ["player_id", "week", "research_ppr", "league_points", "attribution_status", "unresolved_reason"]
    r = sleeper.merge(identity, on="sleeper_id", how="left")
    r = r.merge(comps[keep], left_on=["gsis_id", "week"], right_on=["player_id", "week"], how="left")
    r["championship_window"] = r["week"].isin(list(CHAMPIONSHIP_WEEKS))
    r["diff_vs_research"] = r.sleeper_points - r.research_ppr
    r["diff_vs_league"] = r.sleeper_points - r.league_points
    has_row = r.player_id.notna()
    has_id = r.identity_status.eq("resolved")
    conflict = r.status.eq(RECON_CONFLICT)
    attributed = r.attribution_status.eq("attributed")
    league_ok = has_row & (r.diff_vs_league.abs() <= TOL)
    research_ok = has_row & (r.diff_vs_research.abs() <= TOL)
    absent_zero = ~has_row & (r.sleeper_points.abs() <= TOL)
    reason = np.select(
        [conflict, ~has_id & ~absent_zero, has_id & ~has_row & ~absent_zero, has_row & ~attributed, has_row & attributed & ~league_ok],
        [RECON_CONFLICT, RECON_NO_IDENTITY, RECON_NO_STAT_ROW, RECON_COMPONENT, RECON_SOURCE], default="")
    r["reconciliation_reason"] = reason
    ok = (reason == "")
    r["status"] = np.select([ok & has_row & research_ok, ok & has_row & ~research_ok, ok & absent_zero],
                            ["exact", "attributed_difference", "absent_zero"], default="unresolved")
    cols = ["week", "sleeper_id", "gsis_id", "identity_status", "roster_id", "sleeper_points", "research_ppr", "league_points",
            "diff_vs_research", "diff_vs_league", "attribution_status", "unresolved_reason", "reconciliation_reason",
            "championship_window", "status"]
    return r[cols].sort_values(["week", "sleeper_id"]).reset_index(drop=True)


# ── quarantine re-audit, coverage counts, exact qualification, manifest ───────────────────────

POPULATION_NOTE = "rostered player-weeks only; not full-universe proof"
SCHEMA_VERSION = "dg177_league_scoring_audit_v1"


def audit_quarantine(quarantine: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Re-score the PPR quarantine under the league's individual keys. Every original column
    (including the original quarantine reason / exception) is kept; no play-by-play split is
    attempted for unidentified rows, so only weekly-count components can move them."""
    q = quarantine.copy()
    for c in WEEKLY_COMPONENT_COLUMNS:
        q[c] = _num(q, c) if c in q else 0.0
    q["extra_fumbles_lost"] = (q["fumbles_lost_total"] - q["sack_fumbles_lost"] - q["rushing_fumbles_lost"]
                              - q["receiving_fumbles_lost"]).clip(lower=0)
    for c in SPLIT_COLUMNS:
        q[c] = 0
    q["league_points_if_scored"] = league_points(q, settings)
    q["nonzero_under_league_keys"] = q["league_points_if_scored"].abs() > TOL
    return q


def coverage_counts(components: pd.DataFrame, reconciliation: pd.DataFrame, sleeper: pd.DataFrame, identity: pd.DataFrame) -> dict:
    st = reconciliation["status"].value_counts()
    champ = reconciliation[reconciliation["championship_window"]]["status"].value_counts()
    unresolved = components.loc[components["attribution_status"] == "unresolved", "unresolved_reason"].value_counts()
    return {
        "weekly_player_weeks_reg": int(len(components)),
        "weekly_player_weeks_championship": int(components["championship_window"].sum()),
        "sleeper_player_weeks": int(len(sleeper)),
        "sleeper_player_weeks_championship": int(sleeper["week"].isin(list(CHAMPIONSHIP_WEEKS)).sum()),
        "sleeper_players": int(sleeper["sleeper_id"].nunique()),
        "identity_resolved": int((identity["identity_status"] == "resolved").sum()),
        "identity_unmapped": int((identity["identity_status"] == "unmapped").sum()),
        "identity_ambiguous": int((identity["identity_status"] == "ambiguous").sum()),
        "status_exact": int(st.get("exact", 0)), "status_attributed_difference": int(st.get("attributed_difference", 0)),
        "status_absent_zero": int(st.get("absent_zero", 0)), "status_unresolved": int(st.get("unresolved", 0)),
        "status_exact_championship": int(champ.get("exact", 0)),
        "status_attributed_difference_championship": int(champ.get("attributed_difference", 0)),
        "status_absent_zero_championship": int(champ.get("absent_zero", 0)),
        "status_unresolved_championship": int(champ.get("unresolved", 0)),
        "reconciliation_unresolved_by_reason": {k: int(v) for k, v in
                                               reconciliation.loc[reconciliation["status"] == "unresolved", "reconciliation_reason"].value_counts().items()},
        "components_unresolved_by_reason": {k: int(v) for k, v in unresolved.items()},
        "sleeper_duplicate_observations_collapsed": int(sleeper["duplicates_collapsed"].sum()) if "duplicates_collapsed" in sleeper else 0,
        "sleeper_conflicting_duplicates": int((sleeper["status"] == RECON_CONFLICT).sum()),
        "population_note": POPULATION_NOTE,
    }


def exact_qualification(classification: dict, counts: dict, kicker_rows_present: bool) -> dict:
    """Always False in this increment; the reasons are named so a later increment cannot inherit
    a qualification it did not earn."""
    reasons = [POPULATION_NOTE]
    if classification.get("unknown"):
        reasons.append(f"unknown_scoring_keys: {classification['unknown']}")
    reasons.append(f"unresolved_player_weeks: {int(counts.get('status_unresolved', 0))}")
    if kicker_rows_present and classification.get("kicker"):
        reasons.append("kicker_keys_unsupported_for_present_kickers")
    return {"league_scoring_exact": False, "reasons": reasons}


def build_audit_manifest(*, sources: dict, settings: dict, classification: dict, counts: dict, qualification: dict,
                         launch: dict, outputs: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "producer": "DG-177 league scoring component audit (report-only)",
        "sources": sources, "settings_sha256": settings_sha256(settings), "scoring_settings": settings,
        "key_classification": classification, "research_preset": RESEARCH_PPR_PRESET,
        "individual_keys_credited": sorted(INDIVIDUAL_KEYS & set(settings)),
        "team_keys_never_applied_to_individuals": sorted(TEAM_KEYS & set(settings)),
        "event_grain": ["game_id", "play_id", "event_slot", "event_type", "player_id"],
        "special_teams_classification": "special_teams_play == 1 AND play type in {punt, kickoff, field_goal, extra_point}; "
                                        "a disagreement marks every event of the play ambiguous (st_classifier_conflict)",
        "slot_capacity_policy": "the two numbered fumble slots are not a universal ledger; more FUMBLES tokens than slots, an "
                                "unpaired recovery slot, or a play-level lost flag disagreeing with every slot marks the play "
                                "ambiguous (slot_capacity); the weekly lost total stays the scoring authority",
        "championship_window": {"weeks": [CHAMPIONSHIP_WEEKS.start, CHAMPIONSHIP_WEEKS.stop - 1], "week_18_included": False},
        "coverage": counts, "league_scoring_exact": qualification["league_scoring_exact"],
        "qualification_reasons": qualification["reasons"], "launch": launch, "outputs": outputs,
        "meaning": "Counts come from the weekly source; play-by-play supplies the special-teams / own-vs-opponent / lost split. "
                   "A disagreement is unresolved, never patched. The Sleeper comparison covers rostered players only.",
    }
