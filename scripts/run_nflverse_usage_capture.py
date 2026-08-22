"""Capture Next Gen Stats, snap counts and the injury report into the durable usage store.

Five streams: three Next Gen Stats specs, snap counts, and the weekly injury report added
2026-08-01. Free, no credential. This script installs nothing, schedules nothing, and touches no other producer —
adding a LaunchAgent is a separate decision and a separate word.

    .venv/bin/python3.14 scripts/run_nflverse_usage_capture.py
    .venv/bin/python3.14 scripts/run_nflverse_usage_capture.py --seasons 2023 2024 2025
    .venv/bin/python3.14 scripts/run_nflverse_usage_capture.py --summary   # read-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.nflverse_usage import (  # noqa: E402
    DEFAULT_DB_PATH,
    default_capture_seasons,
    read_only_summary,
    run_usage_capture,
)

#: The LaunchAgent passes NO flags — `ProgramArguments` is exactly
#: `[.venv/bin/python3.14, scripts/run_nflverse_usage_capture.py]` — so this default IS the
#: schedule. It was the literal `(2023, 2024, 2025)` until 2026-08-21, which meant the 06:15 job
#: re-fetched three finished seasons every morning and requested the live season from nothing.
#: Derived, so the rollover needs no code change in any later year.
DEFAULT_SEASONS = default_capture_seasons()


def capture_is_healthy(status: Mapping[str, Any]) -> bool:
    """0 = healthy, 1 = anything else. SR-09's dependency edges read this as a boolean.

    Unlike the transaction capture, `status == "ok"` IS sufficient here: a stream that fails
    raises out of `run_usage_capture`, so a returned "ok" already means all thirteen streams
    were reached.

    **A recorded `not_yet_available` skip is HEALTHY and must stay that way.** Until nflverse
    publishes 2026, most streams are skipped every single morning — that is the designed
    behaviour SR-06 landed, not a fault. Counting a skip as failure would exit non-zero every
    day until week 1, poisoning SR-09's dependency edges and SR-11's alert from the day they
    land, and an alert that is wrong every morning is one nobody reads by September.
    """
    return status.get("status") == "ok"


def _print_summary(db_path: Path) -> None:
    """Read-only, and now provably so — see read_only_summary()."""
    snapshot = read_only_summary(db_path)
    print("\nWhat the usage store holds:\n")
    for row in snapshot["captures"]:
        coverage = row.get("coverage") or {}
        unresolved = coverage.get("rows_not_canonically_identified")
        conflicts = coverage.get("rows_conflict")
        print(
            f"  {row['stream']:<14} {row['season']}  {row['status']:<6} "
            f"{row['rows_total'] or 0:>6} rows   "
            f"not canonically identified: {unresolved}  (conflicts: {conflicts})"
        )
    print()
    for table, count in snapshot["tables"].items():
        shown = "absent" if count is None else f"{count:>7} rows stored"
        print(f"  {table:<24} {shown}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", nargs="+", type=int, default=list(DEFAULT_SEASONS))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument(
        "--summary",
        action="store_true",
        help="READ-ONLY: print what the store already holds and fetch nothing",
    )
    args = parser.parse_args()

    # `--summary` is read-only, full stop. Adding a second opt-out flag while leaving --summary
    # capture-first would have preserved the original trap rather than removing it — a flag whose
    # name promises a look must never open a socket (Codex, TW30N blocker 1, accepted in full).
    if args.summary:
        _print_summary(Path(args.db_path))
        return 0

    status = run_usage_capture(seasons=args.seasons, db_path=Path(args.db_path))
    slim = {k: v for k, v in status.items() if k != "results"}
    slim["totals"] = {
        k: v for k, v in status["totals"].items() if k != "by_stream_season"
    }
    print(json.dumps(slim, indent=1, sort_keys=True, default=str))
    return 0 if capture_is_healthy(status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
