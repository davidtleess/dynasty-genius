"""DG-178: the current-player census — a dated NFL roster capture joined to the full Sleeper
eligibility snapshot and David's league snapshot. Writes runs/<UTC>/dg178_current_census/
{census.csv, uncovered.csv, report.json}. Reads only; nothing shared is written."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.ranking.nfl_census import (  # noqa: E402
    build_census,
    load_nfl_roster,
    merge_identity_bridges,
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nfl-roster", required=True, type=Path, help="roster_<season>.csv from capture_nfl_roster.py")
    ap.add_argument("--sleeper-eligibility", required=True, type=Path, help="lane 24974's sleeper_eligibility.csv")
    ap.add_argument("--snapshot", required=True, type=Path, help="the league snapshot (rosters -> owned Sleeper ids)")
    ap.add_argument("--identity-bridge", type=Path, action="append", default=[],
                    help="a producer's reconciliation CSV with sleeper_id and a gsis column (my_gsis_id or gsis_id); "
                         "a VERIFIED Sleeper-id -> gsis map used only when neither direct key joins")
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    a = ap.parse_args()
    nfl_manifest = a.nfl_roster.parent / "manifest.json"
    nfl_meta = json.loads(nfl_manifest.read_text())  # load_nfl_roster refuses a missing or mismatched manifest
    sl_manifest = a.sleeper_eligibility.parent / "manifest.json"
    sl_meta = json.loads(sl_manifest.read_text()) if sl_manifest.exists() else {}
    snap = json.loads(a.snapshot.read_text())
    owned = {str(pid): int(r["roster_id"]) for r in snap.get("rosters") or [] for pid in (r.get("players") or [])}
    nfl_rows = load_nfl_roster(a.nfl_roster, nfl_manifest, season=a.season)
    with a.sleeper_eligibility.open(newline="") as fh:
        sleeper_rows = list(csv.DictReader(fh))
    sources = {
        "nflverse_roster": {"path": str(a.nfl_roster), "sha256": sha(a.nfl_roster), "rows": len(nfl_rows),
                            "source_url": nfl_meta.get("source_url"), "http_last_modified": nfl_meta.get("http_last_modified"),
                            "captured_at": nfl_meta.get("captured_at"), "week": sorted({r.get("week") for r in nfl_rows})},
        "sleeper_eligibility": {"path": str(a.sleeper_eligibility), "sha256": sha(a.sleeper_eligibility), "rows": len(sleeper_rows),
                                "captured_at": sl_meta.get("captured_at"), "raw_sha256": (sl_meta.get("raw") or {}).get("sha256")},
        "league_snapshot": {"path": str(a.snapshot), "sha256": sha(a.snapshot), "captured_at": snap.get("captured_at"),
                            "owned_ids": len(owned)},
    }
    bridge_inputs = []
    bridge_sources = []
    for bp in a.identity_bridge:
        with bp.open(newline="") as fh:
            rows_b = list(csv.DictReader(fh))
        bridge_inputs.append((bp.name, rows_b))
        bridge_sources.append({"path": str(bp), "sha256": sha(bp), "rows": len(rows_b)})
    bridge = merge_identity_bridges(bridge_inputs)  # refuses duplicates and cross-file conflicts
    for src in bridge_sources:
        src["pairs_merged_total"] = len(bridge)
    sources["identity_bridge"] = bridge_sources
    census = build_census(sleeper_rows, nfl_rows, league_owned=owned, season=a.season, sources=sources,
                          identity_bridge=bridge)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_current_census"
    out.mkdir(parents=True)
    cols = list(census.rows[0].to_dict().keys()) if census.rows else []
    with (out / "census.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(census.rows, key=lambda r: (r.league_position, r.name)):
            w.writerow(r.to_dict())
    ucols = list(census.uncovered[0].to_dict().keys()) if census.uncovered else []
    with (out / "uncovered.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ucols)
        w.writeheader()
        for u in sorted(census.uncovered, key=lambda u: (u.league_position, u.name)):
            w.writerow(u.to_dict())
    rep = census.report()
    rep["run"] = stamp
    rep["census_csv"] = str(out / "census.csv")
    rep["census_csv_sha256"] = sha(out / "census.csv")
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    c = rep["counts"]
    print(f"members {c['members']} | by class {c['by_class']} | join {c['by_join_basis']} | owned {c['league_owned']} | "
          f"conflicts {c['identity_conflicts']} | uncovered {c['uncovered']} {c['uncovered_by_position']} | "
          f"nfl rows unclaimed {c['nfl_rows_unclaimed']}")
    for pos, d in sorted(rep["counts"]["by_class_and_position"].items()):
        print(f"  {pos}: {d}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
