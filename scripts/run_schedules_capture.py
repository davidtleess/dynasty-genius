"""Capture the nflverse global `schedules` offering (catalog row B21).

One retrieval of one global Parquet asset, hashed before it is interpreted, retained with its
provenance. Free, no credential. This script installs nothing, schedules nothing, and rewires no
consumer — adding a LaunchAgent or pointing the Realized Outcome job at this store are separate
decisions and separate words.

    .venv/bin/python3.14 scripts/run_schedules_capture.py
    .venv/bin/python3.14 scripts/run_schedules_capture.py --summary          # read-only
    .venv/bin/python3.14 scripts/run_schedules_capture.py --root /tmp/b21    # sandboxed

IT MAKES NO FINALITY CLAIM. The feed has no terminal-status field and no end-time, so a populated
score proves play was observed, never that it ended. The route records
`finality_capability=unverified` and emits no derived status.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.sources import schedules_capture as sc  # noqa: E402


def _summary(store: sc.ScheduleStore) -> int:
    marker = store.marker()
    print("\nWhat the B21 schedules store holds:\n")
    print(f"  root                {store.root}")
    print(f"  content vintages    {store.vintage_count()}")
    print(f"  successful checks   {store.successful_check_count()}")
    print(f"  failed attempts     {store.failed_check_count()}")
    if marker is None:
        print("\n  no ready marker — nothing has been captured yet\n")
        return 0
    print(f"\n  last checked        {marker['last_checked_at']}")
    print(f"  last changed        {marker['last_changed_at']}")
    print(f"  raw sha256          {marker['raw_sha256']}")
    print(f"  bytes               {marker['byte_count']}")
    print(f"  schema hash         {marker['schema_hash']}")
    print(f"  finality            {marker['finality_capability']}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(sc.DEFAULT_ROOT),
                        help="capture root (defaults to the governed store)")
    parser.add_argument("--observed-at", default=None,
                        help="ISO-8601 instant WITH offset; defaults to now")
    parser.add_argument("--summary", action="store_true",
                        help="READ-ONLY: print what the store holds and fetch nothing")
    args = parser.parse_args(argv)

    store = sc.ScheduleStore(root=Path(args.root))
    if args.summary:
        return _summary(store)

    observed_at = args.observed_at or datetime.now().astimezone().isoformat()
    try:
        # Resolved through the module at call time, so a caller can substitute a transport without
        # this script knowing anything about it.
        record = store.capture(fetcher=sc.default_fetcher(), observed_at=observed_at)
    except (sc.CaptureError, sc.PublishError) as exc:
        # Named, non-zero, and audited. A route that fails silently with exit 0 is worse than one
        # that never ran: the scheduler and the daily controller both read exit state.
        # BOTH classes, because a storage failure is not a `CaptureError` — catching only the latter
        # turned a disk-full publication into a traceback instead of the named failure promised here.
        # `CaptureError.__str__` already leads with the code — printing it again read
        # "fetch_failed: fetch_failed: connection reset" in the first live smoke run.
        print(f"b21_schedules capture failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "route": sc.route_descriptor().name,
        "check_id": record.check_id,
        "vintage_id": record.vintage_id,
        "created_vintage": record.created_vintage,
        "raw_sha256": record.raw_sha256,
        "byte_count": record.byte_count,
        "schema_hash": record.schema_hash,
        "retrieved_at": record.retrieved_at,
        "source_url": record.source_url,
        "finality_capability": sc.route_descriptor().finality_capability,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
