"""Prepare the identified weekly source for the common outcomes (DG-179) — Codex's 2026-09-06 contract.

    .venv/bin/python scripts/dg165/prepare_identified_weekly.py --capture runs/<UTC>/weekly_source_capture

Writes ONE immutable run directory runs/<UTC>/source_preparation/:
    raw/games.csv                  the official nfldata schedule, captured once (gitignored; URL, time, sha256 in the manifest)
    identified_weekly.parquet      admitted seasons 2001-2025, rows WITH a player id, all original columns + provenance
    quarantine.parquet / .csv      admitted-season rows WITHOUT a player id, in full, with source row index and raw file hash
    preparation_manifest.json      schema dg179_source_preparation_v1 with every required key
    PREPARATION.md                 the record, rendered
Refuses (exit 2) if exact REG game ids disagree with the schedule in an admitted season, or if any
nonzero unidentified row is not one of the exactly reviewed records. No shared writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.source_preparation import (  # noqa: E402
    SCHEDULE_URL,
    game_coverage,
    preparation_manifest,
    split_identified,
    verify_quarantine,
)

ADMITTED = range(2001, 2026)
EXCLUDED = (1999, 2000)
CANCELLED = {"2022_17_BUF_CIN"}
# Codex's exactly reviewed nonzero unidentified records (research-only exception; not a tolerance).
REVIEWED_NONZERO = [
    {"season": 2001, "week": 11, "team": "GB", "opponent_team": "DET", "player_name": "Team", "fantasy_points_ppr": 1.68},
    {"season": 2001, "week": 14, "team": "ARI", "opponent_team": "NYG", "player_name": None, "fantasy_points_ppr": -2.0},
    {"season": 2001, "week": 16, "team": "BAL", "opponent_team": "TB", "player_name": None, "fantasy_points_ppr": -2.0},
    {"season": 2003, "week": 4, "team": "PHI", "opponent_team": "BUF", "player_name": "Team", "fantasy_points_ppr": -0.1},
    {"season": 2005, "week": 1, "team": "LV", "opponent_team": "NE", "player_name": "Team", "fantasy_points_ppr": 6.0},
    {"season": 2012, "week": 6, "team": "TEN", "opponent_team": "PIT", "player_name": "D.Bryant", "fantasy_points_ppr": 3.1},
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", type=Path, required=True)
    ap.add_argument("--runs-root", type=Path, default=REPO / "runs")
    a = ap.parse_args(argv)
    capture_manifest = json.loads((a.capture / "manifest.json").read_text())
    run_dir = create_run_dir(a.runs_root, name="source_preparation")
    (run_dir / "raw").mkdir()
    (run_dir / ".gitignore").write_text("raw/\n")

    # ---- schedule, captured once
    acquired = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(SCHEDULE_URL, headers={"User-Agent": "dynasty-genius DG-165 read-only source capture"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items() if k.lower() in ("etag", "last-modified", "content-length")}
    schedule_path = run_dir / "raw" / "games.csv"
    schedule_path.write_bytes(body)
    schedule = pd.read_csv(schedule_path)

    # ---- weekly rows with provenance (file name + original row index), all columns
    file_hashes = {f["path"].split("/")[-1]: f["sha256"] for f in capture_manifest["files"]}
    frames = []
    for f in capture_manifest["files"]:
        path = a.capture / f["path"]
        frame = pd.read_parquet(path)
        if sha(path) != f["sha256"]:
            raise SystemExit(f"raw file {path.name} does not match the capture manifest hash")
        frame["source_file"] = path.name
        frame["source_row_index"] = range(len(frame))
        frames.append(frame)
    weekly = pd.concat(frames, ignore_index=True)
    original_columns = [c for c in weekly.columns if c not in ("source_file", "source_row_index")]

    # ---- game coverage BEFORE any filter: admitted seasons must verify; excluded seasons are reported
    coverage = game_coverage(schedule, weekly, admitted_seasons=ADMITTED, cancelled_game_ids=CANCELLED)
    excluded_cov = game_coverage(schedule, weekly, admitted_seasons=EXCLUDED)
    excluded = {p["season"]: p["missing"] for p in excluded_cov["per_season"]}
    print("game coverage admitted:", "verified" if coverage["verified"] else "FAILED", "| missing", coverage["missing_game_ids"], "| unexpected", coverage["unexpected_game_ids"])
    print("excluded seasons missing ids:", excluded)
    if not coverage["verified"]:
        (run_dir / "COVERAGE_FAILURE.json").write_text(json.dumps(coverage, indent=1))
        return 2

    # ---- split and verify
    identified, quarantine = split_identified(weekly, admitted_seasons=ADMITTED, file_hashes=file_hashes)
    q_report = verify_quarantine(quarantine, reviewed_nonzero=REVIEWED_NONZERO)  # raises on any deviation
    ident_path = run_dir / "identified_weekly.parquet"
    identified.to_parquet(ident_path, index=False)
    q_path = run_dir / "quarantine.parquet"
    quarantine.to_parquet(q_path, index=False)
    quarantine.to_csv(run_dir / "quarantine.csv", index=False)
    print(f"identified rows {len(identified):,} ({len(original_columns)} original columns + 3 provenance) | quarantine rows {len(quarantine)} "
          f"(nonzero {len(q_report['nonzero_rows'])}) | signed/absolute exclusions by season: "
          + ", ".join(f"{s}: {v['signed_points']:+.2f}/{v['absolute_points']:.2f}" for s, v in q_report['point_totals_by_season'].items() if v['nonzero_rows']))

    inputs = [{"path": str(a.capture / "manifest.json"), "sha256": sha(a.capture / "manifest.json"), "bytes": (a.capture / "manifest.json").stat().st_size,
               "role": "weekly source capture manifest"}]
    inputs += [{"path": str(a.capture / f["path"]), "sha256": f["sha256"], "bytes": f["bytes"], "url": f["url"], "role": f"raw weekly {f['season']}"}
               for f in capture_manifest["files"]]
    inputs.append({"path": "raw/games.csv", "sha256": sha(schedule_path), "bytes": len(body), "url": SCHEDULE_URL, "acquired_at": acquired,
                   "headers": headers, "role": "official nfldata schedule"})
    manifest = preparation_manifest(
        admitted_seasons=ADMITTED, excluded_seasons=excluded, identified_weekly_sha256=sha(ident_path),
        identified_rows=len(identified), identified_columns=len(original_columns),
        game_coverage=coverage,
        quarantine={"path": "quarantine.parquet", "sha256": sha(q_path), "csv_sha256": sha(run_dir / "quarantine.csv"), **q_report},
        inputs=inputs,
        extra={"prepared_at": datetime.now(timezone.utc).isoformat(), "capture_run": str(a.capture),
               "provenance_columns": ["source_file", "source_row_index", "source_file_sha256"],
               "original_columns": original_columns,
               "schedule_capture": {"url": SCHEDULE_URL, "acquired_at": acquired, "sha256": sha(schedule_path), "bytes": len(body), "headers": headers},
               "cancelled_games": sorted(CANCELLED),
               "reviewed_nonzero_records": REVIEWED_NONZERO},
    )
    manifest["outputs_sha256"] = {p.name: sha(p) for p in sorted(run_dir.iterdir()) if p.is_file() and p.name != "preparation_manifest.json"}
    (run_dir / "preparation_manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    lines = ["# Source preparation for the common outcomes (dg179_source_preparation_v1)", "",
             f"Capture `{a.capture}`; schedule `{SCHEDULE_URL}` captured {acquired} (sha256 `{sha(schedule_path)[:12]}…`).", "",
             f"Admitted seasons 2001–2025; excluded {dict(excluded)} (never zero-labelled). Cancelled and excluded explicitly: {sorted(CANCELLED)}.", "",
             "| season | schedule REG | cancelled | completed | weekly REG | missing | unexpected |", "|---|---:|---|---:|---:|---|---|"]
    for p in coverage["per_season"]:
        lines.append(f"| {p['season']} | {p['schedule_reg_games']} | {p['cancelled']} | {p['completed_games']} | {p['weekly_reg_games']} | {p['missing']} | {p['unexpected']} |")
    lines += ["", f"identified_weekly.parquet: {len(identified):,} rows, {len(original_columns)} original columns, sha256 `{manifest['identified_weekly_sha256'][:12]}…`", "",
              f"Quarantine: {q_report['row_count']} rows ({q_report['zero_placeholder_rows']} zero placeholders, {len(q_report['nonzero_rows'])} reviewed nonzero). "
              "Signed / absolute point exclusions by season:", "", "| season | rows | signed | absolute | nonzero rows |", "|---|---:|---:|---:|---:|"]
    for s, v in q_report["point_totals_by_season"].items():
        lines.append(f"| {s} | {v['rows']} | {v['signed_points']:+.2f} | {v['absolute_points']:.2f} | {v['nonzero_rows']} |")
    lines += ["", "Reviewed nonzero records (research-only exception, not a tolerance):", ""]
    for r in q_report["nonzero_rows"]:
        lines.append(f"- {r['season']} w{r['week']} {r['team']} vs {r['opponent_team']} {r['player_name'] or 'unnamed'} {r['fantasy_points_ppr']:+.2f} (row {r['source_row_index']}, file sha {r['source_file_sha256'][:12]}…)")
    lines += ["", "research_qualified = true; individual_stat_completeness_proven = false; no exact-league scoring claim."]
    (run_dir / "PREPARATION.md").write_text("\n".join(lines) + "\n")
    print(f"run dir: {run_dir} | identified sha {manifest['identified_weekly_sha256'][:12]} | manifest sha {sha(run_dir / 'preparation_manifest.json')[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
