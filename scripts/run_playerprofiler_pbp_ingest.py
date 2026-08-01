#!/usr/bin/env python3
"""Ingest PlayerProfiler Advanced Play-by-Play exports (charted plays + player slots).

Requires the Weekly Roster Key first — it supplies the PP-internal -> GSIS bridge.

    .venv/bin/python3.14 scripts/run_playerprofiler_pbp_ingest.py --exports ~/Downloads
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_PATTERN = "*-Advanced-PBP-Data.csv"


def _discover(folders: list[Path], pattern: str) -> list[Path]:
    found: list[Path] = []
    for folder in folders:
        folder = folder.expanduser()
        if folder.is_file():
            found.append(folder)
            continue
        found += sorted(folder.glob(pattern))
    return found


def main(argv: list[str] | None = None) -> int:
    from src.dynasty_genius.playerprofiler import DEFAULT_DB_PATH, DEFAULT_ROOT
    from src.dynasty_genius.playerprofiler_pbp import run_pbp_ingest, status_marker_path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, nargs="*", default=[])
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    if args.summary:
        marker = status_marker_path(args.root)
        if not marker.exists():
            print(f"no pbp status marker at {marker}", file=sys.stderr)
            return 1
        print(json.dumps(json.loads(marker.read_text(encoding="utf-8")), indent=1, sort_keys=True))
        return 0

    paths = _discover(args.exports, args.pattern)
    print(f"discovered {len(paths)} pbp file(s)", file=sys.stderr)
    status = run_pbp_ingest(export_paths=paths, db_path=args.db_path, root=args.root)
    print(json.dumps(status, indent=1, sort_keys=True))
    return 0 if status.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
