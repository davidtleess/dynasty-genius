"""DG-053: capture the ff_playerids crosswalk on cadence, content-addressed.

The product's canonical identity keys off ONE frozen crosswalk snapshot
(``app/data/identity/_runs/ff_playerids_20260516.json``). In-season the upstream
crosswalk changes weekly — rookies signed, ids minted, team corrections — and an
unsnapshotted week is identity truth the 2027 rebuild's as-of joins can never
recover. This job snapshots the crosswalk daily into an append-only,
content-addressed store. It NEVER touches the frozen snapshot or any consumer:
capture only, so its blast radius is one new directory.

Idempotent by content: an unchanged crosswalk writes no new snapshot (the marker
still records the run). Exit codes follow the house convention — 0 healthy,
1 anything else — so launchd and the SR-11 alert can read this job like every
other producer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SNAPSHOTS_DIR = ROOT / "app" / "data" / "identity_snapshots"
DEFAULT_MARKER_PATH = ROOT / "app" / "data" / "ops" / "ff_playerids_snapshot_status_latest.json"

_SCHEMA = 1


def _fetch_upstream() -> list[dict[str, Any]]:
    """The real fetch: nflreadpy's governed loader, rows as plain dicts."""
    from nflreadpy import load_ff_playerids

    return load_ff_playerids().to_dicts()


def canonical_payload(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Deterministic (rows, sha256): row order and key order never change the hash.

    ``default=str`` makes dates and other scalars stable text; the sort key is the
    row's own canonical serialization, a total order that needs no schema knowledge.
    """
    ordered = sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, default=str))
    blob = json.dumps(
        {"rows": ordered}, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return ordered, hashlib.sha256(blob).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_capture(
    *,
    snapshots_dir: Path,
    marker_path: Path,
    today: str,
    fetch_fn: Callable[[], list[dict[str, Any]]] | None = None,
) -> int:
    fetch_fn = fetch_fn or _fetch_upstream
    finished_at = datetime.now(UTC).isoformat()
    try:
        rows, sha = canonical_payload(fetch_fn())
    except Exception as exc:  # noqa: BLE001 — every upstream failure is the same story
        _write_json_atomic(
            marker_path,
            {
                "status": "failed",
                "failure_reason": f"{type(exc).__name__}: {exc}",
                "captured_on": today,
                "finished_at": finished_at,
            },
        )
        return 1

    latest_path = snapshots_dir / "latest.json"
    previous_sha = None
    if latest_path.is_file():
        try:
            previous_sha = json.loads(latest_path.read_text(encoding="utf-8")).get(
                "content_sha256"
            )
        except (json.JSONDecodeError, OSError):
            previous_sha = None

    changed = sha != previous_sha
    if changed:
        snapshot_name = f"ff_playerids_{today.replace('-', '')}_{sha[:12]}.json"
        _write_json_atomic(
            snapshots_dir / snapshot_name,
            {"schema": _SCHEMA, "content_sha256": sha, "rows": rows},
        )
        _write_json_atomic(
            latest_path,
            {
                "snapshot_file": snapshot_name,
                "content_sha256": sha,
                "rows": len(rows),
                "captured_on": today,
            },
        )

    _write_json_atomic(
        marker_path,
        {
            "status": "ok",
            "changed": changed,
            "content_sha256": sha,
            "rows": len(rows),
            "captured_on": today,
            "finished_at": finished_at,
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Snapshot the ff_playerids crosswalk, content-addressed (DG-053)."
    )
    parser.add_argument("--snapshots-dir", type=Path, default=DEFAULT_SNAPSHOTS_DIR)
    parser.add_argument("--marker-path", type=Path, default=DEFAULT_MARKER_PATH)
    parser.add_argument(
        "--today", default=datetime.now(UTC).date().isoformat(), help="capture date stamp"
    )
    args = parser.parse_args(argv)
    return run_capture(
        snapshots_dir=args.snapshots_dir,
        marker_path=args.marker_path,
        today=args.today,
    )


if __name__ == "__main__":
    raise SystemExit(main())
