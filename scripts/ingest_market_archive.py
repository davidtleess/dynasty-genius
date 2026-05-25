#!/usr/bin/env python3.14
"""Community Market Archive Ingest Script.

Ingests community-maintained CSV archives of historical dynasty fantasy football
market values into the local market snapshot store.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add src to path if needed - usually handled by project structure or .venv
sys.path.append(str(Path(__file__).parent.parent))

from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

LEAGUE_SETTINGS_HASH = hashlib.sha256(
    "isDynasty=true&numQbs=2&numTeams=12&ppr=1".encode()
).hexdigest()[:16]

COLUMN_MAP = {
    "sleeper_id": ["sleeper_id", "sleeperId", "sleeper"],
    "value": ["value", "sf_value", "2qb_value", "value_2qb", "sf", "dynasty_sf"],
    "overall_rank": ["overall_rank", "rank", "overall", "overallRank"],
    "position_rank": ["position_rank", "positionRank", "pos_rank"],
    "position": ["position", "pos", "Position"],
}


def detect_columns(header: list[str]) -> dict[str, Optional[str]]:
    """Detect which CSV columns map to our target fields."""
    mapping = {}
    header_lower = [h.lower() for h in header]

    for target, variants in COLUMN_MAP.items():
        found_col = None
        for variant in variants:
            try:
                idx = header_lower.index(variant.lower())
                found_col = header[idx]
                break
            except ValueError:
                continue
        mapping[target] = found_col

    return mapping


def ingest_csv(
    csv_path: Path,
    source: str,
    snapshot_date: str,
    store: MarketSnapshotStore,
    dry_run: bool = False,
) -> dict:
    """Ingest rows from CSV into the snapshot store. Returns counts."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        datetime.strptime(snapshot_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {snapshot_date}. Use YYYY-MM-DD.")

    rows_read = 0
    rows_skipped = 0
    rows_to_upsert = []
    inserted_at = datetime.now(timezone.utc).isoformat()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV file is empty or missing header: {csv_path}")

        col_mapping = detect_columns(list(reader.fieldnames))

        # Check required columns
        if not col_mapping["sleeper_id"]:
            raise ValueError(f"Could not find sleeper_id column in CSV. Header: {reader.fieldnames}")
        if not col_mapping["value"]:
            raise ValueError(f"Could not find value column in CSV. Header: {reader.fieldnames}")

        if not dry_run:
            print("Detected columns: " + ", ".join(f"{k}={v}" for k, v in col_mapping.items() if v))

        for row in reader:
            rows_read += 1
            sleeper_id = row.get(col_mapping["sleeper_id"])  # type: ignore
            value_str = row.get(col_mapping["value"])  # type: ignore

            if not sleeper_id or not value_str:
                rows_skipped += 1
                continue

            try:
                value = int(float(value_str))
            except (ValueError, TypeError):
                rows_skipped += 1
                continue

            # Optional columns
            overall_rank = None
            if col_mapping["overall_rank"]:
                val = row.get(col_mapping["overall_rank"])
                if val:
                    try:
                        overall_rank = int(float(val))
                    except (ValueError, TypeError):
                        pass

            position_rank = None
            if col_mapping["position_rank"]:
                val = row.get(col_mapping["position_rank"])
                if val:
                    try:
                        position_rank = int(float(val))
                    except (ValueError, TypeError):
                        pass

            position = None
            if col_mapping["position"]:
                position = row.get(col_mapping["position"])

            rows_to_upsert.append({
                "snapshot_date": snapshot_date,
                "league_settings_hash": LEAGUE_SETTINGS_HASH,
                "sleeper_id": str(sleeper_id),
                "value": value,
                "overall_rank": overall_rank,
                "position_rank": position_rank,
                "position": position,
                "trend_30day": None,
                "source": source,
                "inserted_at": inserted_at,
            })

    rows_written = 0
    if not dry_run and rows_to_upsert:
        rows_written = store.upsert_snapshots(rows_to_upsert)
    elif dry_run:
        rows_written = 0

    return {
        "rows_read": rows_read,
        "rows_written": rows_written if not dry_run else len(rows_to_upsert),
        "rows_skipped": rows_skipped,
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest historical market values from CSV.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the archive CSV.")
    parser.add_argument("--source", required=True, choices=["ktc_community_csv", "dp_archive", "fc_native"],
                        help="Data source identifier.")
    parser.add_argument("--date", required=True, help="Market snapshot date (YYYY-MM-DD).")
    parser.add_argument("--db", type=Path, default=Path("app/data/fc_snapshots.db"),
                        help="Path to the SQLite database.")
    parser.add_argument("--dry-run", action="store_true", help="Report counts but write nothing.")

    args = parser.parse_args()

    try:
        store = MarketSnapshotStore(db_path=args.db)
        stats = ingest_csv(
            csv_path=args.csv,
            source=args.source,
            snapshot_date=args.date,
            store=store,
            dry_run=args.dry_run,
        )

        print(f"Reading {args.csv}...")
        print(f"Rows read: {stats['rows_read']}")
        print(f"Rows skipped: {stats['rows_skipped']} (missing sleeper_id or value)")
        if args.dry_run:
            print(f"Rows to write (dry-run): {stats['rows_written']}")
        else:
            print(f"Rows written: {stats['rows_written']}")
        print(f"Snapshot date: {args.date} | Source: {args.source}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
