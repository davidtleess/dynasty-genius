"""Ingest David's PlayerProfiler subscriber exports into the durable store.

Callable by hand. This script installs nothing and schedules nothing — PlayerProfiler has
no API, so new data arrives only when David exports it, which makes a scheduler
meaningless here rather than merely unauthorised.

The raw CSVs are PRIVATE subscriber data. They stay wherever they were downloaded; only
the derived store and content hashes exist under app/data/, and both are gitignored.

    .venv/bin/python3.14 scripts/run_playerprofiler_ingest.py --exports ~/Downloads
    .venv/bin/python3.14 scripts/run_playerprofiler_ingest.py --exports ~/Downloads --summary
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.playerprofiler import (  # noqa: E402
    DEFAULT_DB_PATH,
    PlayerProfilerStore,
    medical_blind_window,
    run_playerprofiler_ingest,
)

_PATTERNS = ("data_analysis_report*.csv", "MedicalHistory_*.csv")


def _discover(folder: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in _PATTERNS:
        found += sorted(folder.glob(pattern))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, default=Path.home() / "Downloads",
                        help="folder holding the PlayerProfiler subscriber exports")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--summary", action="store_true",
                        help="READ-ONLY: print what the store holds and ingest nothing")
    args = parser.parse_args(argv)

    if args.summary:
        # A flag whose name promises a look must never fetch or write.
        store = PlayerProfilerStore(args.db_path, season_columns=(), medical_columns=())
        print(f"\nPlayerProfiler store: {args.db_path}")
        for row in store.captures():
            cov = row.get("coverage") or {}
            print(f"  {row['stream']:<16} {row['block']:<10} {row['status']:<5} "
                  f"{row['rows_total'] or 0:>5} rows   "
                  f"not canonically identified: {cov.get('rows_not_canonically_identified')}")
        print(f"\n  medical blind window: {medical_blind_window()['blind_seasons']}")
        return 0

    paths = _discover(args.exports)
    if not paths:
        print(f"no PlayerProfiler exports found under {args.exports}")
        return 1
    status = run_playerprofiler_ingest(export_paths=paths, db_path=args.db_path)
    slim = {k: v for k, v in status.items() if k != "applied"}
    print(json.dumps(slim, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
