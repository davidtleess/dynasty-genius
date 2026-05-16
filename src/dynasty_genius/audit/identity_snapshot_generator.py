"""Immutable identity snapshot artifacts for Phase 13 audits.

Snapshots capture the canonical identity map used by a validation run. They
are intentionally simple JSON artifacts so later draft-capital and TE/PFF
work can point to the exact source-ID mapping state that gated training rows.
"""
from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IdentitySnapshotError(ValueError):
    """Raised when an identity snapshot cannot be generated or loaded."""


@dataclasses.dataclass(frozen=True)
class IdentitySnapshotRow:
    """One canonical player and its source-ID mappings."""

    player_id: str
    gsis_id: str | None = None
    sleeper_id: str | None = None
    pff_id: str | None = None
    pfr_id: str | None = None
    cfbref_id: str | None = None
    espn_id: str | None = None
    yahoo_id: str | None = None
    sportradar_id: str | None = None
    fantasypros_id: str | None = None
    rotowire_id: str | None = None
    fantasy_data_id: str | None = None

    def mapping_dict(self) -> dict[str, str]:
        values = dataclasses.asdict(self)
        values.pop("player_id")
        return {key: value for key, value in values.items() if value is not None}


@dataclasses.dataclass(frozen=True)
class IdentitySnapshot:
    run_id: str
    timestamp: str
    mapping_version: str
    mappings: dict[str, dict[str, str]]
    immutable: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "immutable": self.immutable,
            "mapping_version": self.mapping_version,
            "mappings": self.mappings,
        }


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_identity_snapshot(
    rows: list[IdentitySnapshotRow],
    *,
    run_id: str | None = None,
    created_at: str | None = None,
    mapping_version: str = "1.0.0",
) -> IdentitySnapshot:
    """Build an immutable snapshot from canonical identity rows."""

    run_id = run_id or uuid.uuid4().hex[:8]
    timestamp = created_at or _utc_timestamp()

    mappings: dict[str, dict[str, str]] = {}
    for row in rows:
        if not row.player_id:
            raise IdentitySnapshotError("player_id is required for every snapshot row")
        if row.player_id in mappings:
            raise IdentitySnapshotError(
                f"duplicate player_id in identity snapshot: {row.player_id}"
            )
        mappings[row.player_id] = row.mapping_dict()

    return IdentitySnapshot(
        run_id=run_id,
        timestamp=timestamp,
        immutable=True,
        mapping_version=mapping_version,
        mappings=mappings,
    )


def write_identity_snapshot(path: str | Path, snapshot: IdentitySnapshot) -> None:
    """Write a snapshot JSON file, refusing to overwrite existing artifacts."""

    target = Path(path)
    if target.exists():
        raise IdentitySnapshotError(f"identity snapshot already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_identity_snapshot(path: str | Path) -> dict[str, Any]:
    """Load and validate the immutable snapshot envelope."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("immutable") is not True:
        raise IdentitySnapshotError("identity snapshot must set immutable=true")
    if not data.get("run_id"):
        raise IdentitySnapshotError("identity snapshot missing run_id")
    if not data.get("timestamp"):
        raise IdentitySnapshotError("identity snapshot missing timestamp")
    if not data.get("mapping_version"):
        raise IdentitySnapshotError("identity snapshot missing mapping_version")
    if not isinstance(data.get("mappings"), dict):
        raise IdentitySnapshotError("identity snapshot mappings must be an object")
    return data
