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
    "AcceptedReport",
    "CensusRun",
    "draft_evidence",
    "load_accepted_report",
    "load_census_run",
    "missing_default_pool",
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
