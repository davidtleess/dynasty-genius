"""Capture the FULL nflverse weekly player-stats source once, 1999-2025, unfiltered (DG-165 / DG-179).

    .venv/bin/python scripts/dg165/capture_weekly_source.py [--seasons 1999 2025]

Writes ONE immutable run directory runs/<UTC>/weekly_source_capture/:
    raw/stats_player_week_<season>.parquet   the release files, byte-for-byte (gitignored; sha256 in the manifest)
    coverage.csv / COVERAGE.md               rows, players, weeks, positions, missing-id rows per season x season_type
    schema.csv / SCHEMA.md                    every column across all files with dtype and null counts; per-file column sets
    manifest.json                             URLs, acquisition time, HTTP headers (etag / last-modified), sha256, bytes, rows
Nothing under the shared cache or app/data is touched. No filtering, no cleanup, no fill.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.weekly_source import (  # noqa: E402
    RELEASE,
    coverage_report,
    release_url,
    schema_report,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seasons", type=int, nargs=2, default=[1999, 2025])
    ap.add_argument("--runs-root", type=Path, default=REPO / "runs")
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args(argv)
    seasons = list(range(a.seasons[0], a.seasons[1] + 1))

    run_dir = create_run_dir(a.runs_root, name="weekly_source_capture")
    (run_dir / "raw").mkdir()
    (run_dir / ".gitignore").write_text("raw/\n")
    files, coverage_frames, schema_frames, per_file_columns, failures = [], [], [], {}, []
    for season in seasons:
        url = release_url(season)
        acquired = datetime.now(timezone.utc).isoformat()
        req = urllib.request.Request(url, headers={"User-Agent": "dynasty-genius DG-165 read-only source capture"})
        try:
            with urllib.request.urlopen(req, timeout=a.timeout) as resp:
                body = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items() if k.lower() in ("etag", "last-modified", "content-length", "content-type", "x-github-request-id")}
                status = resp.status
        except Exception as exc:
            failures.append({"season": season, "url": url, "error": repr(exc), "acquired_at": acquired})
            print(f"{season}: FAILED {exc!r}")
            continue
        path = run_dir / "raw" / f"stats_player_week_{season}.parquet"
        path.write_bytes(body)
        frame = pd.read_parquet(io.BytesIO(body))
        cov = coverage_report(frame)
        coverage_frames.append(cov)
        sch = schema_report(frame)
        sch.insert(0, "season", season)
        schema_frames.append(sch)
        per_file_columns[season] = list(frame.columns)
        files.append({"season": season, "url": url, "acquired_at": acquired, "http_status": status, "headers": headers,
                      "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "rows": int(len(frame)), "columns": len(frame.columns),
                      "path": f"raw/{path.name}"})
        reg = cov.loc[cov["season_type"] == "REG"]
        print(f"{season}: {len(frame):,} rows, {len(frame.columns)} cols, REG weeks {reg['week_min'].iloc[0] if len(reg) else None}-{reg['week_max'].iloc[0] if len(reg) else None} "
              f"({reg['n_weeks'].iloc[0] if len(reg) else 0}), missing-id rows {int(cov['rows_missing_player_id'].sum())}, sha {files[-1]['sha256'][:12]}")

    coverage = pd.concat(coverage_frames, ignore_index=True) if coverage_frames else pd.DataFrame()
    coverage.to_csv(run_dir / "coverage.csv", index=False)
    schema = pd.concat(schema_frames, ignore_index=True) if schema_frames else pd.DataFrame()
    schema.to_csv(run_dir / "schema.csv", index=False)
    all_columns = sorted({c for cols in per_file_columns.values() for c in cols})
    column_seasons = {c: [s for s, cols in per_file_columns.items() if c in cols] for c in all_columns}
    union = schema.groupby("column").agg(non_null=("non_null", "sum"), nulls=("nulls", "sum"), dtypes=("dtype", lambda s: "|".join(sorted(set(s))))).reset_index()
    lines = ["# Weekly source schema (union across files)", "", f"{len(all_columns)} columns; per-season column sets differ where a column lists fewer seasons.", "",
             "| column | dtypes | non-null | nulls | seasons carrying it |", "|---|---|---:|---:|---|"]
    for _, r in union.iterrows():
        seas = column_seasons[r["column"]]
        span = f"{seas[0]}–{seas[-1]}" if len(seas) == len(seasons) else f"{len(seas)} of {len(seasons)} ({seas[0]}–{seas[-1]})"
        lines.append(f"| {r['column']} | {r['dtypes']} | {r['non_null']:,} | {r['nulls']:,} | {span} |")
    (run_dir / "SCHEMA.md").write_text("\n".join(lines) + "\n")
    lines = ["# Weekly source coverage (raw, before any filter)", "",
             "| season | type | rows | players | weeks | n | positions | missing-id rows | …with points | missing PPR points |", "|---|---|---:|---:|---|---:|---|---:|---:|---:|"]
    for _, r in coverage.iterrows():
        lines.append(f"| {r['season']} | {r['season_type']} | {r['rows']:,} | {r['players']:,} | {r['week_min']}–{r['week_max']} | {r['n_weeks']} | {r['positions']} | "
                     f"{r['rows_missing_player_id']} | {r['rows_missing_player_id_with_points']} | {r['rows_missing_fantasy_points_ppr']} |")
    (run_dir / "COVERAGE.md").write_text("\n".join(lines) + "\n")
    reg = coverage.loc[coverage["season_type"] == "REG"] if len(coverage) else coverage
    manifest = {
        "ticket": "DG-165 (for DG-179 common outcomes)", "purpose": "full unfiltered nflverse weekly player-stats source, captured once",
        "release": RELEASE, "source_version": "GitHub release assets; per-file etag / last-modified recorded under files[].headers (nflverse publishes no semantic version for these assets)",
        "seasons_requested": [seasons[0], seasons[-1]], "files": files, "failures": failures,
        "totals": {"files": len(files), "rows": int(sum(f["rows"] for f in files)), "bytes": int(sum(f["bytes"] for f in files)),
                   "columns_union": len(all_columns),
                   "reg_rows": int(reg["rows"].sum()) if len(reg) else 0,
                   "reg_seasons_with_weeks_1_to_16": int(((reg["week_min"] == 1) & (reg["week_max"] >= 16)).sum()) if len(reg) else 0,
                   "rows_missing_player_id": int(coverage["rows_missing_player_id"].sum()) if len(coverage) else 0,
                   "rows_missing_player_id_with_points": int(coverage["rows_missing_player_id_with_points"].sum()) if len(coverage) else 0},
        "columns_union": all_columns,
        "scoring_note": "fantasy_points_ppr is nflverse's default-PPR total as saved in the source; it is NOT asserted to equal David's league rules "
                        "(lost-fumble scope, fum_rec_td, st_ff, st_fum_rec need fuller attribution). Every component column is retained for attribution.",
        "rules": "no filtering, no cleanup, no fill; missing-id rows are counted and kept; missing values stay missing; the shared nflreadpy cache and app/data are untouched",
        "outputs_sha256": {},
    }
    for p in sorted(run_dir.iterdir()):
        if p.is_file() and p.name != "manifest.json":
            manifest["outputs_sha256"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print(f"run dir: {run_dir} | files {len(files)} failures {len(failures)} rows {manifest['totals']['rows']:,}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
