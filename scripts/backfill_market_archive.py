#!/usr/bin/env python3.14
"""Harness Trust Completion W1.4 — point-in-time historical market backfill.

Reads an approved community FantasyCalc archive (an immutable historical capture)
and writes point-in-time-valid rows to the MarketSnapshotStore so the Phase 10/11
harness can run G3 (market superiority) at its fold snapshot dates. Market data is
OVERLAY-ONLY — never an Engine A/B feature/training input (Gate B §8.4 approval).

A row is accepted for a target snapshot_date only if ALL hold (else skipped):
  1. required fields present: sleeper_id, value, position, archive_publish_date;
  2. abs(archive_publish_date - target) <= 7 days (the store's resolve window);
  3. if the row carries updated_at, updated_at <= archive_publish_date (a newer
     updated_at = post-hoc revision → not point-in-time → reject).
Accepted rows are written via append_snapshots (immutable; no silent overwrite).

Spec: docs/superpowers/specs/2026-05-30-harness-trust-completion-design.md §5/§8.4
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from scripts.snapshot_fantasycalc import LEAGUE_SETTINGS_HASH  # noqa: E402
from src.dynasty_genius.eval.market_snapshot_store import (  # noqa: E402
    MarketSnapshotStore,
)

_REQUIRED_FIELDS = ("sleeper_id", "value", "position", "archive_publish_date")
_PIT_WINDOW_DAYS = 7
# Historical backfill provenance only — fc_native is the FORWARD W2a source and
# must never enter the archive via backfill.
_BACKFILL_SOURCES = {"ktc_community_csv", "dp_archive"}
DEFAULT_DB_PATH = Path("app/data/fc_snapshots.db")


def _is_point_in_time_valid(row: dict) -> bool:
    """Validate an EXTERNAL archive row, failing closed (skip) on any malformed field.

    Accept only if: required fields present; value is int-coercible; source (when
    present) is a backfill source; and not post-hoc revised (updated_at <= publish).
    """
    if not all(row.get(f) is not None for f in _REQUIRED_FIELDS):
        return False
    try:
        int(row["value"])  # external data — a non-int value is malformed → skip
    except (ValueError, TypeError):
        return False
    source = row.get("source")
    if source is not None and source not in _BACKFILL_SOURCES:
        return False  # fc_native (forward) or any non-backfill provenance → skip
    updated_at = row.get("updated_at")
    if updated_at is not None:
        try:
            if date.fromisoformat(updated_at) > date.fromisoformat(
                row["archive_publish_date"]
            ):
                return False  # revised after the capture → not point-in-time
        except ValueError:
            return False
    return True


def _within_window(publish_date: str, target: str) -> bool:
    try:
        delta = abs((date.fromisoformat(publish_date) - date.fromisoformat(target)).days)
    except ValueError:
        return False
    return delta <= _PIT_WINDOW_DAYS


def _to_store_row(row: dict, target: str, inserted_at: str) -> dict:
    return {
        "snapshot_date": target,
        "league_settings_hash": LEAGUE_SETTINGS_HASH,
        "sleeper_id": str(row["sleeper_id"]),
        "value": int(row["value"]),
        "overall_rank": row.get("overall_rank"),
        "position_rank": row.get("position_rank"),
        "position": row["position"],
        "trend_30day": row.get("trend_30day"),
        "source": row.get("source", "dp_archive"),
        "inserted_at": inserted_at,
    }


def backfill_market_archive(
    archive: list[dict],
    *,
    db_path: Path = DEFAULT_DB_PATH,
    snapshot_dates: list[str],
) -> dict:
    """Backfill point-in-time-valid archive rows. Returns {rows_written, rows_skipped}.

    A row is skipped if it fails point-in-time validity, or matches no target
    snapshot_date within ±7 days. Accepted rows are written immutably.
    """
    store = MarketSnapshotStore(db_path=db_path)
    inserted_at = datetime.now(timezone.utc).isoformat()

    store_rows: list[dict] = []
    written = 0
    skipped = 0
    for row in archive:
        if not _is_point_in_time_valid(row):
            skipped += 1
            continue
        matched_targets = [
            t for t in snapshot_dates
            if _within_window(row["archive_publish_date"], t)
        ]
        if not matched_targets:
            skipped += 1
            continue
        for target in matched_targets:
            store_rows.append(_to_store_row(row, target, inserted_at))
            written += 1

    if store_rows:
        store.append_snapshots(store_rows)
    return {"rows_written": written, "rows_skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill point-in-time market archive rows into the snapshot store."
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--snapshot-dates", nargs="+", required=True,
        help="Target fold snapshot dates (YYYY-MM-DD).",
    )
    # The archive itself is supplied by a caller/loader (the real FC historical
    # capture is David-approved per §8.4 and not committed); the CLI is a thin shell.
    args = parser.parse_args(argv)
    print(
        "backfill_market_archive: import and call backfill_market_archive(archive, "
        f"db_path={args.db_path}, snapshot_dates={args.snapshot_dates}) with a loaded "
        "point-in-time archive.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
