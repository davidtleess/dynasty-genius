#!/usr/bin/env python3
"""Ingest PlayerProfiler Advanced Gamelog exports (weekly player usage).

Requires the Weekly Roster Key to be ingested FIRST — it supplies the PP-internal -> GSIS
bridge without which every pre-2023 row is unidentifiable.

    .venv/bin/python3.14 scripts/run_playerprofiler_gamelog_ingest.py --exports ~/Downloads
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_PATTERN = "*-Advanced-Gamelog.csv"


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
    from src.dynasty_genius.playerprofiler_gamelog import (
        run_gamelog_ingest,
        status_marker_path,
    )

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
            print(f"no gamelog status marker at {marker}", file=sys.stderr)
            return 1
        print(json.dumps(json.loads(marker.read_text(encoding="utf-8")), indent=1, sort_keys=True))
        return 0

    paths = _discover(args.exports, args.pattern)
    print(f"discovered {len(paths)} gamelog file(s)", file=sys.stderr)
    status = run_gamelog_ingest(export_paths=paths, db_path=args.db_path, root=args.root)
    print(json.dumps(status, indent=1, sort_keys=True))
    return 0 if status.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
