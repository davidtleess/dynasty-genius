"""Unowned cold-start coverage (DG-165, available-players build 2026-09-06).

Who are the unowned default-pool players without a forecast, and why? This module proves it per
player from hash-verified captured inputs — identity, NFL/fantasy status, draft evidence from three
independent sources, NFL history from the common outcome artifact — and classifies the forecast
ROUTE each player could take. It produces no estimate itself.

Fail-closed: an unverifiable byte, an unreconciled count against the accepted report, a duplicate
identity or a missing declaration refuses. Absence is never turned into a positive claim: no draft
record is "no draft record", not "undrafted"; no stat row is "no stat row in the artifact", not
"zero production observed".
"""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

__all__ = [
    "DEFAULT_POOL",
    "DRAFT_STATUS",
    "LEDGER_COLUMNS",
    "ROUTES",
    "AcceptedReport",
    "CensusRun",
    "build_ledger",
    "draft_evidence",
    "load_accepted_report",
    "load_census_run",
    "full_nfl_source_status",
    "missing_default_pool",
    "nfl_history",
    "route_for",
]

# NFL availability classes David can actually pick up from (the brief's default relevant unowned pool).
DEFAULT_POOL = ("active", "practice_squad", "injured_reserve")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_verified(path: Path, declared: str | None, what: str) -> bytes:
    if not declared:
        raise ValueError(f"{what}: no sha256 declared for {path.name}")
    if not path.exists():
        raise ValueError(f"{what}: declared file missing: {path}")
    data = path.read_bytes()
    actual = _sha(data)
    if actual != declared:
        raise ValueError(f"{what}: sha256 mismatch for {path.name}: declared {declared[:12]}…, actual {actual[:12]}…")
    return data


@dataclass(frozen=True)
class CensusRun:
    run_dir: Path
    report: dict
    census: pd.DataFrame
    uncovered: pd.DataFrame
    census_sha256: str
    report_sha256: str


@dataclass(frozen=True)
class AcceptedReport:
    path: Path
    report: dict
    sha256: str
    forecast_sleeper_ids: frozenset
    forecast_player_ids: frozenset


def load_census_run(run_dir: Path | str) -> CensusRun:
    """DG-178's dated census run: census.csv and uncovered.csv verified against report.json's declarations."""
    run_dir = Path(run_dir)
    report_bytes = (run_dir / "report.json").read_bytes()
    report = json.loads(report_bytes)
    census_raw = _read_verified(run_dir / "census.csv", report.get("census_csv_sha256"), "census run")
    uncovered_raw = _read_verified(run_dir / "uncovered.csv", report.get("uncovered_csv_sha256"), "census run")
    census = pd.read_csv(io.BytesIO(census_raw), dtype={"sleeper_id": str, "nfl_gsis_id": str, "sleeper_gsis_id": str})
    uncovered = pd.read_csv(io.BytesIO(uncovered_raw), dtype={"sleeper_id": str})
    if census["sleeper_id"].duplicated().any():
        dup = census.loc[census["sleeper_id"].duplicated(keep=False), "sleeper_id"].head(5).tolist()
        raise ValueError(f"census run: sleeper_id is not unique, e.g. {dup}")
    return CensusRun(run_dir, report, census, uncovered, report["census_csv_sha256"], _sha(report_bytes))


def load_accepted_report(path: Path | str) -> AcceptedReport:
    """The accepted DG-178 audit report: hashed as parsed; the forecast identities it carries."""
    path = Path(path)
    raw = path.read_bytes()
    report = json.loads(raw)
    rows = (report.get("comparable_board") or {}).get("all_inspectable") or []
    sleeper_ids = frozenset(str(x["sleeper_id"]) for x in rows if x.get("sleeper_id") is not None)
    player_ids = frozenset(str(x["player_id"]) for x in rows if x.get("player_id") is not None)
    return AcceptedReport(path, report, _sha(raw), sleeper_ids, player_ids)


def _declared_pool_counts(accepted: AcceptedReport) -> dict[tuple[str, str], tuple[int, int]]:
    """(position, class) -> (with_forecast, without_forecast) as the accepted report declares them."""
    cov = ((accepted.report.get("current_census") or {}).get("coverage") or {})
    by_pos = ((cov.get("listed_unowned") or {}).get("by_position") or {})
    if not by_pos:
        raise ValueError("accepted report: current_census.coverage.listed_unowned.by_position is missing; cannot reconcile")
    out = {}
    for pos, classes in by_pos.items():
        for cls, counts in classes.items():
            out[(str(pos), str(cls))] = (int(counts.get("with_forecast", 0)), int(counts.get("without_forecast", 0)))
    return out


def missing_default_pool(census: CensusRun, accepted: AcceptedReport) -> pd.DataFrame:
    """Unowned default-pool census members without a forecast on the accepted board.

    Reconciled per (position, class) against the accepted report's own coverage block; any
    disagreement refuses, so the tool can never quietly audit a different population than the
    board describes.
    """
    declared_census = (accepted.report.get("current_census") or {}).get("census_csv_sha256")
    if declared_census != census.census_sha256:
        raise ValueError(f"accepted report describes census {str(declared_census)[:12]}…, not the loaded census {census.census_sha256[:12]}…")
    c = census.census
    unowned = c.loc[~c["league_owned"].astype(bool)].copy()
    unowned["has_forecast"] = unowned["sleeper_id"].astype(str).isin(accepted.forecast_sleeper_ids)
    declared = _declared_pool_counts(accepted)
    problems = []
    for (pos, cls), (with_fc, without_fc) in declared.items():
        if cls not in DEFAULT_POOL:
            continue
        cell = unowned.loc[(unowned["league_position"].astype(str) == pos) & (unowned["availability_class"].astype(str) == cls)]
        got = (int(cell["has_forecast"].sum()), int((~cell["has_forecast"]).sum()))
        if got != (with_fc, without_fc):
            problems.append(f"{pos}/{cls}: report {with_fc}/{without_fc} vs census {got[0]}/{got[1]}")
    for (pos, cls), cell in unowned.loc[unowned["availability_class"].isin(DEFAULT_POOL)].groupby(["league_position", "availability_class"]):
        if (str(pos), str(cls)) not in declared:
            problems.append(f"{pos}/{cls}: present in the census ({len(cell)} rows) but absent from the report's coverage")
    if problems:
        raise ValueError("default pool does not reconcile with the accepted report: " + "; ".join(problems))
    missing = unowned.loc[unowned["availability_class"].isin(DEFAULT_POOL) & ~unowned["has_forecast"]].copy()
    return missing.sort_values(["availability_class", "league_position", "name"]).drop(columns="has_forecast").reset_index(drop=True)


# ----------------------------------------------------------------------------- draft evidence

DRAFT_STATUS = (
    "drafted_verified",            # >= 1 positive draft record and every positive source agrees on season and overall pick
    "draft_sources_conflict",      # positive draft records that disagree — not verified, not "no record"
    "no_draft_record_3_sources",   # the id is known to all three sources, none carries a draft record
    "no_draft_record_2_sources",
    "no_draft_record_1_source",
    "unknown_identity",            # the id is known to no source at all
)
AGE_REFERENCE = pd.Timestamp("2026-09-01")


def _latest_roster_rows(rosters: pd.DataFrame) -> pd.DataFrame:
    r = rosters.loc[rosters["gsis_id"].notna()].copy()
    r["gsis_id"] = r["gsis_id"].astype(str)
    sort_cols = ["season"] + (["week"] if "week" in r.columns else [])
    return r.sort_values(sort_cols).groupby("gsis_id", sort=False).last()


def draft_evidence(gsis_ids: pd.Series, *, draft_picks: pd.DataFrame, players: pd.DataFrame, rosters: pd.DataFrame) -> pd.DataFrame:
    """Draft facts from three independent sources, labelled positively.

    A source is POSITIVE when its draft fields are non-null. ``drafted_verified`` needs at least one positive
    source and agreement (season and overall pick) among all positive sources. Absence of a draft record in
    every source that knows the player is ``no_draft_record_<n>_sources`` — a statement about the sources,
    never a claim that the player went undrafted.
    """
    picks = draft_picks.loc[draft_picks["gsis_id"].notna()].copy()
    picks["gsis_id"] = picks["gsis_id"].astype(str)
    picks = picks.drop_duplicates("gsis_id").set_index("gsis_id")
    pl = players.copy()
    pl["gsis_id"] = pl["gsis_id"].astype(str)
    pl = pl.drop_duplicates("gsis_id").set_index("gsis_id")
    ro = _latest_roster_rows(rosters)
    rows = []
    for pid in gsis_ids.astype(str):
        known = 0
        positive = []
        if pid in picks.index:
            known += 1
            p = picks.loc[pid]
            positive.append(("draft_picks", int(p["season"]), int(p["pick"]), int(p["round"]), str(p["position"])))
        if pid in pl.index:
            known += 1
            p = pl.loc[pid]
            if pd.notna(p.get("draft_year")) and pd.notna(p.get("draft_pick")):
                positive.append(("players", int(p["draft_year"]), int(p["draft_pick"]), int(p["draft_round"]) if pd.notna(p.get("draft_round")) else None, None))
        if pid in ro.index:
            known += 1
            p = ro.loc[pid]
            if pd.notna(p.get("draft_number")) and pd.notna(p.get("entry_year")):
                positive.append(("rosters", int(p["entry_year"]), int(p["draft_number"]), None, None))
        if known == 0:
            status = "unknown_identity"
        elif not positive:
            status = f"no_draft_record_{known}_sources" if known > 1 else "no_draft_record_1_source"
        else:
            seasons = {s for _, s, _, _, _ in positive}
            overall = {o for _, _, o, _, _ in positive}
            status = "drafted_verified" if len(seasons) == 1 and len(overall) == 1 else "draft_sources_conflict"
        first = positive[0] if positive else None
        draft_round = next((r for _, _, _, r, _ in positive if r is not None), None)
        draft_pos = next((q for _, _, _, _, q in positive if q is not None), None)
        entry = None
        rookie = None
        birth = None
        college = None
        if pid in pl.index:
            p = pl.loc[pid]
            rookie = int(p["rookie_season"]) if pd.notna(p.get("rookie_season")) else None
            birth = str(p["birth_date"]) if pd.notna(p.get("birth_date")) else None
            college = str(p["college_name"]) if pd.notna(p.get("college_name")) else None
        if pid in ro.index:
            p = ro.loc[pid]
            entry = int(p["entry_year"]) if pd.notna(p.get("entry_year")) else None
            birth = birth or (str(p["birth_date"]) if pd.notna(p.get("birth_date")) else None)
            college = college or (str(p["college"]) if pd.notna(p.get("college")) else None)
        entry_season = rookie if rookie is not None else entry
        age = None
        if birth:
            bd = pd.to_datetime(birth, errors="coerce")
            age = float((AGE_REFERENCE - bd).days / 365.25) if pd.notna(bd) else None
        rows.append({
            "gsis_id": pid, "draft_status": status, "draft_sources_positive": len(positive), "draft_sources_checked": known,
            "draft_season": first[1] if (first and status == "drafted_verified") else None,
            "draft_round": draft_round if status == "drafted_verified" else None,
            "draft_pick": first[2] if (first and status == "drafted_verified") else None,
            "draft_position": draft_pos if status == "drafted_verified" else None,
            "draft_sources_agree": (status == "drafted_verified") if positive else None,
            "draft_conflict_detail": "; ".join(f"{src}:{s}/{o}" for src, s, o, _, _ in positive) if status == "draft_sources_conflict" else None,
            "entry_season": entry_season, "rookie_season": rookie, "birth_date": birth, "age_2026": age, "college": college,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- NFL history, route, ledger

ROUTES = (
    "existing_forecast_join_failure",   # a frozen producer already forecasts this GSIS; the board's join lost it — investigate, never re-estimate
    "never_appeared_drafted",
    "never_appeared_no_draft_record",
    "dormant_drafted",
    "dormant_no_draft_record",
    "draft_sources_conflict_unresolved",   # positive draft records disagree: explicit unresolved, never a routine route
    "unknown_identity",
)
NEVER_APPEARED_REASON = ("no championship-window stat row in the common outcome artifact 2001–{last}; a statement about the "
                         "artifact's records, not a claim of zero individual production observed")


def nfl_history(gsis_ids: pd.Series, *, outcomes: pd.DataFrame, basic_cohort: pd.DataFrame, basic_forecasts: pd.DataFrame,
                rookie_scores: pd.DataFrame, last_complete_season: int) -> pd.DataFrame:
    """Appearance history from the DG-179 artifact plus whether either frozen producer already covers the id."""
    o = outcomes.loc[outcomes["appeared"].astype(bool)].copy()
    o["player_id"] = o["player_id"].astype(str)
    agg = o.groupby("player_id").agg(first=("season", "min"), last=("season", "max"), n=("season", "size"))
    last_points = o.sort_values("season").groupby("player_id").last()["points"]
    bc = basic_cohort.copy()
    bc["player_id"] = bc["player_id"].astype(str)
    bc_last = bc.groupby("player_id")["feature_season"].max()
    bc_2025 = set(bc.loc[bc["feature_season"] == last_complete_season, "player_id"])
    bf_2025 = set(basic_forecasts.loc[basic_forecasts["feature_season"] == last_complete_season, "player_id"].astype(str))
    rookies = set(rookie_scores["gsis_id"].astype(str))
    rows = []
    for pid in gsis_ids.astype(str):
        hit = pid in agg.index
        last = int(agg.loc[pid, "last"]) if hit else None
        rows.append({
            "gsis_id": pid,
            "nfl_appearance_seasons": int(agg.loc[pid, "n"]) if hit else 0,
            "first_appearance_season": int(agg.loc[pid, "first"]) if hit else None,
            "last_appearance_season": last,
            "seasons_since_last_appearance": (last_complete_season - last) if hit else None,
            "window_points_last_appearance": float(last_points.loc[pid]) if hit else None,
            "dg177_2025_feature_row": pid in bc_2025,
            "dg177_2025_forecast_row": pid in bf_2025,
            "dg177_last_feature_season": int(bc_last.loc[pid]) if pid in bc_last.index else None,
            "dg165_rookie_2026_row": pid in rookies,
        })
    return pd.DataFrame(rows)


def route_for(row) -> tuple[str, str]:
    """(route, reason) for one ledger row; rule order matters and is the same for every player."""
    status = str(row["draft_status"])
    if bool(row.get("dg177_2025_forecast_row")) or bool(row.get("dg165_rookie_2026_row")):
        which = "DG-177 2025 forecast" if bool(row.get("dg177_2025_forecast_row")) else "DG-165 2026 rookie score"
        return "existing_forecast_join_failure", f"a {which} exists under this gsis id but the accepted board carries none for the Sleeper id — a join to investigate, not a new estimate"
    if status == "unknown_identity":
        return "unknown_identity", "the NFL gsis id is known to no held source (draft picks, players table, rosters)"
    if status == "draft_sources_conflict":
        return "draft_sources_conflict_unresolved", "positive draft records disagree across sources; unresolved until a source is adjudicated"
    drafted = status == "drafted_verified"
    suffix = "drafted" if drafted else "no_draft_record"
    detail = ""
    if int(row["nfl_appearance_seasons"]) == 0:
        return f"never_appeared_{suffix}", NEVER_APPEARED_REASON.format(last=2025) + detail
    return f"dormant_{suffix}", (f"appeared in {int(row['nfl_appearance_seasons'])} window season(s), last {int(row['last_appearance_season'])}; "
                                 f"{int(row['seasons_since_last_appearance'])} season(s) absent since" + detail)


def full_nfl_source_status(sleeper_ids: pd.Series, universe_reconciliation: pd.DataFrame) -> pd.DataFrame:
    """DG-177's own reason for not forecasting a Sleeper id, read from its hash-bound universe reconciliation.

    This is the FULL-NFL-record view (any REG stat line, e.g. a week-18 record outside the championship
    window); the ledger keeps it beside the window-absence route and never relabels one with the other."""
    u = universe_reconciliation.copy()
    u["sleeper_id"] = u["sleeper_id"].astype(str)
    u = u.drop_duplicates("sleeper_id").set_index("sleeper_id")
    rows = []
    for sid in sleeper_ids.astype(str):
        if sid in u.index:
            r = u.loc[sid]
            rows.append({"sleeper_id": sid, "full_nfl_source_reason": str(r["status"]),
                         "full_nfl_last_season_seen": int(r["last_season_seen"]) if pd.notna(r.get("last_season_seen")) else None,
                         "full_nfl_games_2025": int(r["games_2025"]) if pd.notna(r.get("games_2025")) else None})
        else:
            rows.append({"sleeper_id": sid, "full_nfl_source_reason": "not_in_dg177_universe", "full_nfl_last_season_seen": None, "full_nfl_games_2025": None})
    return pd.DataFrame(rows)


LEDGER_COLUMNS = [
    "sleeper_id", "name", "league_position", "fantasy_positions", "availability_class", "nfl_team", "nfl_status_raw",
    "gsis_id", "join_basis", "sleeper_gsis_agrees", "identity_status",
    "draft_status", "draft_sources_positive", "draft_sources_checked", "draft_season", "draft_round", "draft_pick", "draft_position",
    "draft_sources_agree", "draft_conflict_detail",
    "birth_date", "age_2026", "entry_season", "rookie_season", "college",
    "nfl_appearance_seasons", "first_appearance_season", "last_appearance_season", "seasons_since_last_appearance", "window_points_last_appearance",
    "dg177_2025_feature_row", "dg177_2025_forecast_row", "dg177_last_feature_season", "dg165_rookie_2026_row",
    "full_nfl_source_reason", "full_nfl_last_season_seen", "full_nfl_games_2025",
    "route", "route_reason", "inputs_available",
]


def build_ledger(missing: pd.DataFrame, evidence: pd.DataFrame, history: pd.DataFrame,
                 full_nfl: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per missing player — exactly len(missing), asserted — with identity, draft evidence, history and route."""
    m = missing.copy()
    m["gsis_id"] = m["nfl_gsis_id"].astype(str)
    if full_nfl is not None:
        fn = full_nfl.drop_duplicates("sleeper_id").set_index(full_nfl["sleeper_id"].astype(str))
        m = m.join(fn.drop(columns=["sleeper_id"]), on=m["sleeper_id"].astype(str).rename("_sid"))
    ev = evidence.drop_duplicates("gsis_id").set_index("gsis_id")
    hi = history.drop_duplicates("gsis_id").set_index("gsis_id")
    missing_ev = sorted(set(m["gsis_id"]) - set(ev.index))
    missing_hi = sorted(set(m["gsis_id"]) - set(hi.index))
    if missing_ev or missing_hi:
        raise ValueError(f"ledger inputs incomplete: evidence lacks {missing_ev[:5]}, history lacks {missing_hi[:5]}")
    led = m.join(ev, on="gsis_id").join(hi, on="gsis_id")
    sg = led["sleeper_gsis_id"] if "sleeper_gsis_id" in led.columns else pd.Series([None] * len(led), index=led.index)
    led["sleeper_gsis_agrees"] = [None if pd.isna(s) else (str(s) == g) for s, g in zip(sg, led["gsis_id"])]
    led["identity_status"] = ["unknown" if st == "unknown_identity" else ("verified_nfl_join" if a in (True, None) else "sleeper_gsis_disagrees")
                              for st, a in zip(led["draft_status"], led["sleeper_gsis_agrees"])]
    routes = [route_for(r) for _, r in led.iterrows()]
    led["route"] = [r for r, _ in routes]
    led["route_reason"] = [why for _, why in routes]
    input_fields = ["draft_season", "birth_date", "entry_season", "college", "last_appearance_season", "dg177_last_feature_season"]
    led["inputs_available"] = [",".join(f for f in input_fields if pd.notna(r.get(f))) for _, r in led.iterrows()]
    for col in LEDGER_COLUMNS:
        if col not in led.columns:
            led[col] = None
    out = led[LEDGER_COLUMNS].reset_index(drop=True)
    if len(out) != len(missing):
        raise AssertionError("ledger rows must equal missing-player rows")
    return out
