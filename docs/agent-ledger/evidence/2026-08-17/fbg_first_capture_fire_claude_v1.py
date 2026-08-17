"""Footballguys Phase A FIRST CAPTURE — single witnessed fire, 2026-08-17 (David's word: "lets go").

Invokes the landed Phase A intake (commit e6b6775, GREEN pin a419930b…) exactly once
over the David-downloaded Draft Dominator archive. Pins the archive by SHA-256 and
REFUSES on mismatch. Records pre/post store state. Descriptive only; the intake
writes only its own governed stores; decision_supported semantics unchanged.

Usage: .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-17/fbg_first_capture_fire_claude_v1.py <archive_path>
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_ARCHIVE_SHA256 = "d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c"
OFFERING = {
    "source": "footballguys",
    "offering_id": "fbg-offering-2026-08-09-a",
    # Archive file mtime at capture prep: 2026-08-09 00:02:50 ET (download completion).
    "retrieved_at": "2026-08-09T00:02:50-04:00",
}


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docs" / "governance").is_dir() and (parent / "app").is_dir():
            return parent
    raise SystemExit("repo root not found from script location")


def sha256_path(p: Path) -> str | None:
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def store_state(root: Path) -> dict:
    base = root / "app" / "data" / "footballguys"
    objects = base / "objects"
    return {
        "receipts_db_sha256": sha256_path(base / "receipts.db"),
        "semantics_db_sha256": sha256_path(base / "semantics.db"),
        "observations_db_exists": (base / "observations.db").exists(),
        "objects_entries": sorted(p.name for p in objects.iterdir()) if objects.is_dir() else None,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: fbg_first_capture_fire_claude_v1.py <archive_path>", file=sys.stderr)
        return 2
    root = repo_root()
    sys.path.insert(0, str(root / "src"))
    from dynasty_genius.sources.footballguys_intake import (
        ACTIVE_RETENTION_MODE,
        build_contract_driver,
    )

    archive = Path(sys.argv[1]).expanduser()
    blob = archive.read_bytes()
    measured = hashlib.sha256(blob).hexdigest()
    if measured != EXPECTED_ARCHIVE_SHA256:
        print(json.dumps({"status": "refused_archive_hash_mismatch", "measured": measured}))
        return 1

    pre = store_state(root)
    driver = build_contract_driver(
        repo_root=root,
        manifest_path=root / "app" / "config" / "backup_manifest.json",
        retention_mode=ACTIVE_RETENTION_MODE,
        # Whole-second clock: the operation-clock law reuses the canonical-instant
        # validator, which refuses fractional seconds (proven by the first invocation's
        # pre-mutation refusal, recorded in the 2026-08-17 ledger).
        clock=lambda: datetime.now(timezone.utc).replace(microsecond=0),
    )
    result = driver.intake(archive_bytes=blob, offering=dict(OFFERING))
    post = store_state(root)

    print(
        json.dumps(
            {
                "fired_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "archive_sha256": measured,
                "archive_bytes": len(blob),
                "offering": OFFERING,
                "retention_mode": ACTIVE_RETENTION_MODE,
                "result": {
                    "status": result.status,
                    "reason": result.reason,
                    "raw_retained": result.raw_retained,
                    "receipt_id": result.receipt_id,
                    "observation_id": result.observation_id,
                    "attempt_recorded": result.attempt_recorded,
                },
                "stores_pre": pre,
                "stores_post": post,
            },
            indent=2,
        )
    )
    return 0 if result.status in {"ready", "review_required", "noop"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
