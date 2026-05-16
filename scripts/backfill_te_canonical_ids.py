#!/usr/bin/env python3
"""Backfill deterministic DG canonical IDs for the Phase 13 TE cohort.

This is a post-gate utility. It reads the promoted TE source-ID eligibility
manifest, assigns deterministic Dynasty Genius `player_id` values, and writes
new canonical artifacts without mutating the original immutable snapshot.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.audit.identity_snapshot_generator import (
    IdentitySnapshotRow,
    generate_identity_snapshot,
    write_identity_snapshot,
)
from src.dynasty_genius.identity import assign_collision_suffixes, generate_dg_id


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("name") or ""),
        str(row.get("gsis_id") or ""),
        str(row.get("sleeper_id") or ""),
    )


def build_canonical_te_registry(
    eligible_manifest: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic canonical-ID registry for TE source-ID rows."""

    generated_at = generated_at or _utc_timestamp()
    source_run_id = str(eligible_manifest["run_id"])
    source_rows = sorted(eligible_manifest.get("eligible", []), key=_sort_key)

    base_ids = [generate_dg_id(str(row["name"]), "TE") for row in source_rows]
    canonical_ids = assign_collision_suffixes(base_ids)

    players: dict[str, dict[str, Any]] = {}
    for canonical_id, row in zip(canonical_ids, source_rows):
        players[canonical_id] = {
            "player_id": canonical_id,
            "name": row.get("name"),
            "position": "TE",
            "gsis_id": row.get("gsis_id"),
            "sleeper_id": row.get("sleeper_id"),
            "pff_id": row.get("pff_id"),
            "resolution_stage": row.get("resolution_stage"),
            "canonical_player_id_source": "deterministic_name_position",
        }

    return {
        "metadata": {
            "source_run_id": source_run_id,
            "generated_at": generated_at,
            "method": "generate_dg_id(name, TE) with deterministic collision suffixes",
            "count": len(players),
        },
        "players": players,
    }


def _canonical_eligible_manifest(
    source_manifest: dict[str, Any],
    registry: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    by_source_key = {
        (player["name"], player["gsis_id"], player["sleeper_id"]): player
        for player in registry["players"].values()
    }

    eligible: list[dict[str, Any]] = []
    for row in sorted(source_manifest.get("eligible", []), key=_sort_key):
        player = by_source_key[(row.get("name"), row.get("gsis_id"), row.get("sleeper_id"))]
        canonical_row = dict(row)
        canonical_row["player_id"] = player["player_id"]
        canonical_row["canonical_player_id_source"] = player["canonical_player_id_source"]
        eligible.append(canonical_row)

    return {
        "run_id": f"{source_manifest['run_id']}_canonical",
        "source_run_id": source_manifest["run_id"],
        "generated_at": generated_at,
        "eligible_count": len(eligible),
        "note": "Canonical DG player_ids assigned post source-ID coverage gate; original snapshot left immutable.",
        "eligible": eligible,
    }


def _snapshot_rows(registry: dict[str, Any]) -> list[IdentitySnapshotRow]:
    return [
        IdentitySnapshotRow(
            player_id=player["player_id"],
            gsis_id=player.get("gsis_id"),
            sleeper_id=player.get("sleeper_id"),
            pff_id=player.get("pff_id"),
        )
        for player in registry["players"].values()
    ]


def write_canonical_te_artifacts(
    eligible_manifest_path: str | Path,
    *,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> dict[str, Path]:
    """Write canonical registry, snapshot, and eligibility artifacts."""

    source_path = Path(eligible_manifest_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated_at = generated_at or _utc_timestamp()

    source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
    source_run_id = str(source_manifest["run_id"])
    canonical_run_id = f"{source_run_id}_canonical"

    registry = build_canonical_te_registry(source_manifest, generated_at=generated_at)

    registry_path = out / f"te_canonical_player_ids_{source_run_id}.json"
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    snapshot = generate_identity_snapshot(
        _snapshot_rows(registry),
        run_id=canonical_run_id,
        created_at=generated_at,
    )
    snapshot_path = out / f"identity_snapshot_{canonical_run_id}.json"
    write_identity_snapshot(snapshot_path, snapshot)

    eligible = _canonical_eligible_manifest(
        source_manifest,
        registry,
        generated_at=generated_at,
    )
    eligible_path = out / f"pff_te_eligible_{canonical_run_id}.json"
    eligible_path.write_text(json.dumps(eligible, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "registry": registry_path,
        "snapshot": snapshot_path,
        "eligible": eligible_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill DG canonical IDs for the TE identity cohort.")
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("app/data/identity"))
    args = parser.parse_args(argv)

    written = write_canonical_te_artifacts(args.eligible_manifest, out_dir=args.out_dir)
    print("Canonical TE identity artifacts written:")
    for path in written.values():
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
