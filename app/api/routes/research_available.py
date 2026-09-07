"""DG-178 available-player discovery (plan T3, 2026-09-06): a read-only route that serves the
newest immutable available-player catalog built from the SAME accepted report the research
preview serves. Local research runs only; the live artifact is never read here."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from src.dynasty_genius.ranking.roster_comparison import (
    ComparisonSourceError,
    build_comparison,
)

router = APIRouter(prefix="/research")

NOTES = {
    "ownership": ("Ownership filters availability only: it never changes a player's forecast. Unowned means nobody in "
                  "David's league owned him in the dated snapshot; it is not the same as being an NFL free agent."),
    "now": ("Now = the 2026 projected points over the championship window (NFL weeks 1–17), the producer's own expected "
            "season points; not weekly start advice."),
    "future": ("Future = the projected points for 2027–2030 summed, named years only; undefined when any of those years has "
               "no forecast — never zero, never a partial total; not a breakout probability."),
    "appearance": "P(appears) is the producer's probability of at least one stat record in the window; it is not P(becomes useful).",
    "sorting": "Sorting states its basis beside the control; raw points are not cross-position dynasty value and no overall rank is claimed.",
    "watchlist": "The watchlist is David's own shortlist saved in this browser; it is not a model nomination.",
    "starting_estimate": ("A starting estimate is a research candidate for a drafted player with no rookie-season record: year 1 "
                          "from a draft-capital model where the producer's paired evaluation selected it, later years from the "
                          "position's historical baseline; not conditioned on remaining on a current roster, not a breakout "
                          "probability, no impact number."),
}


def _runs_root() -> Path:
    return Path(os.environ.get("DG178_RUNS_ROOT") or (Path(__file__).resolve().parents[3] / "runs"))


def _served_report(run: Optional[str]) -> tuple[str, Path, bool]:
    root = _runs_root()
    pinned = os.environ.get("DG178_PREVIEW_RUN") or None
    wanted = run or pinned
    candidates = sorted(p for p in root.glob("*/dg178_audit/report.json") if wanted is None or p.parent.parent.name == wanted)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"no research run named {wanted} under the runs directory" if wanted
                            else "no research run found under the runs directory")
    return candidates[-1].parent.parent.name, candidates[-1], (run is None and pinned is not None)


def _refuse(run_name: str, why: str) -> HTTPException:
    return HTTPException(status_code=500, detail=(f"available-player catalog {run_name} failed its integrity check: {why}; "
                                                  f"refusing to serve it and not falling back to an older catalog"))


def _claimed_report_run(catalog_path: Path) -> Optional[str]:
    """What report a catalog says it was built from; None when the file cannot be read as JSON."""
    try:
        return str(json.loads(catalog_path.read_text()).get("source_report_run"))
    except (OSError, ValueError):
        return None


def _catalog_for(report_run: str, report_path: Path, catalog_run: Optional[str]) -> tuple[str, dict]:
    """The newest immutable catalog built from the SERVED report. The run name alone is never the
    binding: the companion report.json must record the catalog.json bytes, and the catalog must
    record the sha256 of the report bytes actually served. Any failure on the newest candidate
    (or the explicitly requested one) is an explicit error — tampered or malformed data is never
    served, and an older catalog is never substituted silently."""
    root = _runs_root()
    candidates: list[tuple[str, Path, Optional[str]]] = []      # (run name, dir, problem)
    for d in sorted(root.glob("*/dg178_available_catalog")):
        run_name = d.parent.name
        if catalog_run is not None and run_name != catalog_run:
            continue
        companion = d / "report.json"
        if not companion.exists():
            claimed = _claimed_report_run(d / "catalog.json")
            if claimed is None:
                candidates.append((run_name, d, "catalog.json is not readable JSON and there is no companion report.json"))
            elif claimed == report_run:
                candidates.append((run_name, d, "no companion report.json records the catalog bytes (outputs_sha256)"))
            continue
        try:
            cdoc = json.loads(companion.read_text())
        except (OSError, ValueError):
            candidates.append((run_name, d, "the companion report.json is not readable JSON"))
            continue
        if str(cdoc.get("source_report_run")) == report_run:
            candidates.append((run_name, d, None))
    if not candidates:
        raise HTTPException(status_code=404, detail=(f"no available-player catalog built from the served research run "
                                                     f"{report_run}" + (f" named {catalog_run}" if catalog_run else "")
                                                     + "; build one with scripts/dg178/build_available_catalog.py"))
    run_name, d, problem = candidates[-1]
    if problem:
        raise _refuse(run_name, problem)
    cdoc = json.loads((d / "report.json").read_text())
    catalog_bytes = (d / "catalog.json").read_bytes()
    recorded = str(((cdoc.get("outputs_sha256") or {}).get("catalog.json")) or "").lower()
    actual = hashlib.sha256(catalog_bytes).hexdigest()
    if recorded != actual:
        raise _refuse(run_name, f"catalog.json bytes ({actual[:12]}…) differ from the companion record outputs_sha256 ({recorded[:12] or 'absent'}…)")
    try:
        doc = json.loads(catalog_bytes)
    except ValueError:
        raise _refuse(run_name, "catalog.json is not readable JSON")
    if str(doc.get("source_report_run")) != report_run:
        raise _refuse(run_name, f"catalog.json claims report {doc.get('source_report_run')} while its companion claims {report_run}")
    served_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    bound_sha = str((doc.get("sources") or {}).get("report_sha256") or "").lower()
    if bound_sha != served_sha:
        raise _refuse(run_name, f"its sources.report_sha256 ({bound_sha[:12] or 'absent'}…) is not the sha256 of the served report "
                                f"{report_run} bytes ({served_sha[:12]}…)")
    return run_name, doc


@router.get("/available")
def research_available(run: Optional[str] = Query(default=None), catalog: Optional[str] = Query(default=None)) -> dict[str, Any]:
    report_run, report_path, pinned = _served_report(run)
    catalog_run, doc = _catalog_for(report_run, report_path, catalog)
    ownership_as_of = doc.get("ownership_as_of")
    nfl_as_of = doc.get("nfl_status_as_of")
    return {
        "source": {"kind": "local_research_catalog", "catalog_run": catalog_run, "report_run": report_run, "pinned": pinned,
                   "census_run_id": doc.get("census_run_id"), "report_sha256": (doc.get("sources") or {}).get("report_sha256"),
                   "integrity": "catalog bytes verified against the companion record; report_sha256 verified against the served report bytes",
                   "provenance": doc.get("provenance")},
        "freshness": {"ownership_as_of": ownership_as_of, "nfl_status_as_of": nfl_as_of,
                      "caveat": (f"Ownership is as of the league snapshot captured {ownership_as_of}; NFL roster status is as of the "
                                 f"roster capture dated {nfl_as_of}. Both may have changed since; nothing here is live.")},
        "populations": doc.get("populations") or {},
        "populations_note": doc.get("populations_note"),
        "disclosures": doc.get("disclosures") or {},
        "forecast_note": doc.get("forecast_note"),
        "recovered": doc.get("recovered"),
        "starting_estimates": doc.get("starting_estimates") or {"count": 0, "rows": [], "source": None, "evidence": None},
        "forecast_years": doc.get("forecast_years"), "future_years": doc.get("future_years"),
        "notes": NOTES,
        "rows": doc.get("rows_detail") or [],
    }


@router.get("/comparison")
def research_comparison(run: Optional[str] = Query(default=None), catalog: Optional[str] = Query(default=None)) -> dict[str, Any]:
    """DG-182: the roster-spot comparison — David's roster from the served report's five-year view
    beside the unowned rows of the catalog bound to that report. The catalog document is the one
    `_catalog_for` verified against its companion record; the report bytes are hashed and parsed
    by the adapter from one buffer and must match the sha256 the catalog binds, so a file that
    changed between the two reads is refused rather than served."""
    report_run, report_path, _pinned = _served_report(run)
    catalog_run, doc = _catalog_for(report_run, report_path, catalog)
    try:
        return build_comparison(report_path.read_bytes(), doc, report_run=report_run, catalog_run=catalog_run)
    except ComparisonSourceError as e:
        raise HTTPException(status_code=500, detail=(f"roster comparison from report {report_run} and catalog {catalog_run} refused: {e}; "
                                                     "not serving a partial or older comparison"))
