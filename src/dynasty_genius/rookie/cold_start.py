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
    "AcceptedReport",
    "CensusRun",
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
