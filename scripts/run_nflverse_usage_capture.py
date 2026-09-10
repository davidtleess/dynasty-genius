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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.nflverse_usage import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_RAW_ROOT,
    UsageCaptureError,
    capture_is_healthy,
    default_capture_seasons,
    default_release_inventory,
    read_only_summary,
    run_usage_capture,
    run_usage_retry,
)

#: The LaunchAgent passes NO flags — `ProgramArguments` is exactly
#: `[.venv/bin/python3.14, scripts/run_nflverse_usage_capture.py]` — so this default IS the
#: schedule. It was the literal `(2023, 2024, 2025)` until 2026-08-21, which meant the 06:15 job
#: re-fetched three finished seasons every morning and requested the live season from nothing.
#: Derived, so the rollover needs no code change in any later year.
DEFAULT_SEASONS = default_capture_seasons()


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
        "--raw-root",
        default=None,
        help="Where raw snapshots and the status marker live. Set it together with --db-path for "
             "an isolated rehearsal; --db-path alone still writes raw/export to the shared default.",
    )
    parser.add_argument("--export-root", default=None, help="Where the derived export is published.")
    parser.add_argument(
        "--retry-only",
        action="store_true",
        help="Check ONLY partitions that are waiting and whose own retry time has passed. Fetches "
             "nothing else, never recaptures snapshot-axis streams, and never narrows the receipt.",
    )
    parser.add_argument(
        "--partition",
        action="append",
        default=None,
        metavar="STREAM:SEASON",
        help="Narrow a --retry-only run to these partitions (repeatable). This is a NARROWING "
             "REQUEST, not an instruction: the capture runs the intersection of what is asked for "
             "and what is independently eligible, so neither side can widen the other.",
    )
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

    raw_root = Path(args.raw_root) if args.raw_root else DEFAULT_RAW_ROOT
    export_root = Path(args.export_root) if args.export_root else None
    if args.partition and not args.retry_only:
        parser.error("--partition narrows a --retry-only run; it has no meaning on a full capture")

    try:
        if args.retry_only:
            status = run_usage_retry(
                db_path=Path(args.db_path),
                raw_root=raw_root,
                export_root=export_root,
                only=args.partition,
                # THE REAL PATH NEEDS THIS. Without a provider the classifier has no evidence to
                # work from, so an actual absent snap_counts_2026.parquet is recorded as an error
                # and never reaches the retry queue — the whole feature is inert through the CLI
                # while every injected-fixture test still passes. The API default stays None so
                # tests remain offline by construction.
                release_inventory=default_release_inventory,
            )
        else:
            status = run_usage_capture(
                seasons=args.seasons,
                db_path=Path(args.db_path),
                raw_root=raw_root,
                export_root=export_root,
                release_inventory=default_release_inventory,
            )
    except UsageCaptureError as exc:
        # 3 is "another capture holds the lock; nothing was done" — benign, and NOT an attempt.
        # DG-216 retries on the next tick. An unbroken hour of 3 is the stale-lock signature.
        if "nflverse_capture_lock_held" in str(exc):
            print(json.dumps({"status": "lock_held", "reason": str(exc)}, indent=1))
            return 3
        raise
    slim = {k: v for k, v in status.items() if k != "results"}
    # A no-due retry, or a marker left by a crashed run, legitimately carries no `totals`. Indexing
    # it unconditionally turned "there was nothing to do" into a KeyError. Absent stays absent —
    # inventing an empty totals block here would read as a healthy run that captured nothing.
    if isinstance(status.get("totals"), dict):
        slim["totals"] = {
            k: v for k, v in status["totals"].items() if k != "by_stream_season"
        }
    print(json.dumps(slim, indent=1, sort_keys=True, default=str))
    return 0 if capture_is_healthy(status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
