"""Dual Daily PIT Capture T3.1 — FantasyCalc forward-capture CLI entrypoint.

Concrete executable wrapper over the dependency-injected T2 driver
(`capture_fantasycalc_snapshot`). Supplies the REAL `httpx` client, UTC clock,
sleep, and jitter so the scheduled daily run has one command to invoke; tests
inject fakes via the module-level `httpx` / `time` / `random` handles.

Does NOT import the retired legacy collector (`scripts.snapshot_fantasycalc`) or
the legacy `MarketSnapshotStore` — this is the new survivorship-complete capture
namespace (REPLACE + freeze-and-supersede; the legacy `fc_snapshots.db` archive
stays preserved read-only). The `launchctl` reload (T3.4) and the first live FC
fetch (T3.5) are separately David-gated.

Plan: docs/superpowers/plans/2026-06-24-dual-daily-pit-capture-fc-t3-operational-plan.md (T3.1)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

# Standalone-run path bootstrap: when launchd/cron runs this file directly, the repo
# root is not on sys.path, so the first-party `src` import would crash at runtime.
# Resolve the repo root from this file's location (cwd-independent) before importing.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.fc_forward_capture_driver import (  # noqa: E402
    FC_ENDPOINT,
    SETTINGS_HASH,
    SOURCE,
    capture_fantasycalc_snapshot,
)

HTTP_TIMEOUT_SECONDS = 30.0


def _fetch_json(url: str) -> object:
    """Real network fetch: GET -> raise_for_status -> json (the driver maps errors)."""
    response = httpx.get(url, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def _parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one daily FantasyCalc forward snapshot (PIT, append-only)."
    )
    parser.add_argument(
        "--db-path", required=True, help="FC forward-capture store path."
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Path for the machine-readable capture report (JSON).",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Print resolved config and exit; performs no network I/O and no writes.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    if args.preflight:
        print(
            json.dumps(
                {
                    "preflight": True,
                    "db_path": args.db_path,
                    "report_path": args.report_path,
                    "source": SOURCE,
                    "settings_hash": SETTINGS_HASH,
                    "endpoint": FC_ENDPOINT,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report_path = Path(args.report_path) if args.report_path else None
    if report_path is not None:
        # The T2 driver writes the report verbatim; ensure its parent exists so a
        # nested scheduler report path does not fail the capture (T3.1 contract).
        report_path.parent.mkdir(parents=True, exist_ok=True)

    report = capture_fantasycalc_snapshot(
        db_path=Path(args.db_path),
        report_path=report_path,
        fetch_json=_fetch_json,
        now_fn=lambda: datetime.now(timezone.utc),
        sleep_fn=lambda seconds: time.sleep(seconds),
        jitter_fn=lambda: random.random(),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
