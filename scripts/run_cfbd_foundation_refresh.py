"""Stage a full CFBD raw-to-curated refresh without mutating current inputs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.cfbd_foundation_refresh import (  # noqa: E402
    CfbdRefreshError,
    run_cfbd_foundation_refresh,
)

DEFAULT_INPUT = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_v3.csv"
DEFAULT_SOURCE_ROOT = ROOT / "app" / "data" / "sources" / "cfbd_foundation"


def _builder(output_path: Path, raw_cache_dir: Path) -> None:
    import scripts.build_w2b_cfbd as builder

    original_csv = builder.V3_CSV
    original_cache = builder.CACHE_DIR
    try:
        builder.V3_CSV = output_path
        builder.CACHE_DIR = raw_cache_dir
        builder.main(force_fetch=True, allow_degraded=False, include_rb_ypg=False)
    finally:
        builder.V3_CSV = original_csv
        builder.CACHE_DIR = original_cache


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an isolated CFBD raw snapshot and curated prospect table."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--preflight",
        action="store_true",
        help="Check key, input, and builder readiness without fetching or writing.",
    )
    action.add_argument(
        "--execute",
        action="store_true",
        help="Fetch into a new isolated raw snapshot and publish curated output.",
    )
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    has_key = bool(os.getenv("CFBD_API_KEY", "").strip())
    if args.preflight:
        ready = has_key and args.input_path.exists()
        print(
            f"preflight ready={ready} key_present={has_key} "
            f"input_present={args.input_path.exists()}"
        )
        return 0 if ready else 1
    if not has_key:
        print("refresh failed: CFBD_API_KEY is not configured")
        return 1

    try:
        result = run_cfbd_foundation_refresh(
            source_root=args.source_root,
            input_path=args.input_path,
            builder=_builder,
        )
    except (CfbdRefreshError, ConnectionError) as exc:
        print(f"refresh failed: {exc}")
        return 1
    print(
        f"{result['status']} source=cfbd "
        f"last_changed_at={result['last_changed_at']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
