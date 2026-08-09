"""Capture one CFBD FBS season schedule offering with retained raw provenance."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.sources.cfbd_schedules_capture import (  # noqa: E402
    DEFAULT_ROOT,
    CaptureError,
    CfbdScheduleStore,
    PublishError,
    default_fetcher,
    route_descriptor,
    scrub_message,
)


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args(argv)

    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("CFBD_API_KEY", "")
    if not api_key.strip():
        print("CFBD_API_KEY is required", file=sys.stderr)
        return 2

    try:
        record = CfbdScheduleStore(Path(args.root)).capture(
            fetcher=default_fetcher(),
            api_key=api_key,
            year=args.year,
        )
    except (CaptureError, PublishError, OSError) as exc:
        safe = scrub_message(f"{type(exc).__name__}: {exc}", api_key)
        print(f"cfbd_fbs_schedules capture failed: {safe}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "route": route_descriptor(args.year).name,
                "check_id": record.check_id,
                "vintage_id": record.vintage_id,
                "created_vintage": record.created_vintage,
                "raw_sha256": record.raw_sha256,
                "raw_bytes": record.raw_bytes,
                "schema_hash": record.schema_hash,
                "retrieved_at": record.retrieved_at,
                "request_count": record.request_count,
                "call_limit_remaining_after": record.call_limit_remaining_after,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
