"""DG-178: build the immutable available-player catalog from the ACCEPTED audit report, the SAME
census bytes it bound, the verified league snapshot and the producers' frozen CSVs. Writes
runs/<UTC>/dg178_available_catalog/{catalog.json, catalog.csv, report.json}. Reads only; the
825 accepted forecasts are never touched. Refuses a mutable 'latest' path anywhere."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.ranking.available_catalog import AvailableCatalog  # noqa: E402
from src.dynasty_genius.ranking.cold_start_consumer import (
    ColdStartSidecar,  # noqa: E402
)


def _git(*args: str, cwd: Path = REPO):
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def git_state(repo: Path = REPO) -> dict:
    """The ACTUAL working-tree state: tracked modifications and untracked paths separately, and
    dirty = either. Untracked implementation files must never read as a clean tree."""
    try:
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo,
                                capture_output=True, text=True, check=True).stdout
    except Exception:
        return {"dirty": None, "tracked_modified": [], "untracked": [], "error": "git status unavailable"}
    tracked, untracked = [], []
    for line in status.splitlines():          # never strip: a leading space is the porcelain index column
        if not line.strip():
            continue
        (untracked if line.startswith("??") else tracked).append(line[3:].strip())
    return {"dirty": bool(tracked or untracked), "tracked_modified": tracked, "untracked": untracked}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, type=Path, help="the accepted audit report.json (immutable run)")
    ap.add_argument("--census-dir", required=True, type=Path, help="the dg178_current_census run the report bound")
    ap.add_argument("--snapshot", required=True, type=Path, help="the league snapshot the report records")
    ap.add_argument("--producer-csv", type=Path, action="append", default=[], required=True,
                    help="a producer CSV the report records (bytes checked against its recorded sha256)")
    ap.add_argument("--cold-start-dir", type=Path, default=None,
                    help="root-accepted DG-165 cold-start sidecar run dir (new-only starting estimates); needs both hashes")
    ap.add_argument("--cold-start-manifest-sha256", default=None, help="the manifest.json sha256 root accepted")
    ap.add_argument("--cold-start-estimates-sha256", default=None, help="the cold_start_estimates.csv sha256 root accepted")
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    a = ap.parse_args()
    cold = None
    if a.cold_start_dir or a.cold_start_manifest_sha256 or a.cold_start_estimates_sha256:
        if not (a.cold_start_dir and a.cold_start_manifest_sha256 and a.cold_start_estimates_sha256):
            raise SystemExit("--cold-start-dir, --cold-start-manifest-sha256 and --cold-start-estimates-sha256 are required together")
        if "latest" in a.cold_start_dir.as_posix().lower():
            raise SystemExit(f"{a.cold_start_dir}: a mutable 'latest' path is not an input; bind the explicit immutable run")
        cold = ColdStartSidecar.load(a.cold_start_dir, manifest_sha256=a.cold_start_manifest_sha256,
                                     estimates_sha256=a.cold_start_estimates_sha256)
    for p in (a.report, a.census_dir, a.snapshot, *a.producer_csv):
        if "latest" in Path(p).as_posix().lower():
            raise SystemExit(f"{p}: a mutable 'latest' path is not an input; bind explicit immutable runs")
    catalog = AvailableCatalog.build(a.report, a.census_dir, a.producer_csv, snapshot_path=a.snapshot, cold_start=cold)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_available_catalog"
    out.mkdir(parents=True)
    rep = catalog.report()
    state = git_state()
    rep["provenance"] = {"git_head": _git("rev-parse", "HEAD"), "git_dirty": state["dirty"], "git_state": state,
                         "argv": sys.argv[1:], "script": str(Path(__file__).resolve().relative_to(REPO)),
                         "generated_at": datetime.now(timezone.utc).isoformat()}
    rep["run"] = stamp
    (out / "catalog.json").write_text(json.dumps(catalog.to_json() | {"run": stamp, "provenance": rep["provenance"]}, indent=1, default=str))
    rows = [r.to_dict() for r in catalog.rows]
    cols = ["sleeper_id", "player_id", "name", "league_position", "fantasy_positions", "availability_class", "population",
            "nfl_team", "nfl_status_raw", "join_basis", "identity_conflict", "readiness", "now_points", "future_points",
            "future_reason", "missing_reason", "impact_h2", "impact_h5", "producer", "forecast_join_id", "forecast_path_status", "recovered",
            "starting_estimate", "estimate_classes",
            *[f"e_points_{y}" for y in rep["forecast_years"]], *[f"p_appear_{y}" for y in rep["forecast_years"]]]
    with (out / "catalog.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            flat = {c: r.get(c) for c in cols if c in r}
            flat["impact_h2"], flat["impact_h5"] = r["impact"].get("h2"), r["impact"].get("h5")
            fc = r.get("forecast") or {}
            flat["producer"], flat["forecast_join_id"] = fc.get("producer"), fc.get("join_id")
            flat["forecast_path_status"], flat["recovered"] = (r.get("forecast_path") or {}).get("status"), r.get("recovered")
            flat["starting_estimate"] = r.get("starting_estimate")
            flat["estimate_classes"] = json.dumps(r.get("estimate_classes")) if r.get("estimate_classes") else None
            for s in fc.get("seasons") or []:
                flat[f"e_points_{s['season']}"] = s["e_points"]
                flat[f"p_appear_{s['season']}"] = s["p_appear"]
            w.writerow(flat)
    rep["outputs_sha256"] = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in ("catalog.json", "catalog.csv")}
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    pops = rep["populations"]
    print("populations:", {k: (v["total"], v["with_forecast"], v["without_forecast"]) for k, v in pops.items()})
    print("recovered:", rep["recovered"]["count"], "| starting estimates:", rep["starting_estimates"]["count"])
    print("default by class:", pops["default"]["by_class"], "| disclosures:", {k: v for k, v in rep["disclosures"].items() if k != "note"})
    print("ownership as of", rep["ownership_as_of"], "| NFL status as of", rep["nfl_status_as_of"])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
