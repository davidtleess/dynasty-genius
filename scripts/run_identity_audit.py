#!/usr/bin/env python3
"""Identity coverage audit runner — Task 13.1.1.

Loads a player cohort fixture and source-ID lookup fixtures, runs the
deterministic resolution cascade, writes coverage matrix and review queue
artifacts, and prints a summary.

Usage:
  python scripts/run_identity_audit.py \\
      --cohort app/data/identity/cohort_fixture.json \\
      --ff-playerids app/data/identity/ff_playerids_fixture.json \\
      --alias-bridge app/data/prospect_alias_bridge.json \\
      --out-dir app/data/identity

Fixture formats:
  cohort_fixture.json     — {"entries": [IdentityAuditRow fields as dicts, ...]}
  ff_playerids_fixture.json — {"entries": [{"gsis_id": ..., "sleeper_id": ..., ...}, ...]}
  prospect_alias_bridge.json — existing bridge format {"entries": [...]}

Outputs:
  app/data/identity/identity_coverage_matrix_{run_id}.json
  app/data/identity/identity_review_queue_{run_id}.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.audit.identity_coverage_matrix import (
    IdentityAuditRow,
    run_audit,
)


def _load_cohort(path: Path) -> list[IdentityAuditRow]:
    data = json.loads(path.read_text())
    rows = []
    for entry in data.get("entries", []):
        rows.append(
            IdentityAuditRow(
                cohort=entry["cohort"],
                name=entry["name"],
                position=entry["position"],
                draft_year=entry.get("draft_year"),
                college=entry.get("college"),
                date_of_birth=entry.get("date_of_birth"),
                player_id=entry.get("player_id"),
                sleeper_id=entry.get("sleeper_id"),
                gsis_id=entry.get("gsis_id"),
                pff_id=entry.get("pff_id"),
                pfr_id=entry.get("pfr_id"),
                cfbref_id=entry.get("cfbref_id"),
                espn_id=entry.get("espn_id"),
                yahoo_id=entry.get("yahoo_id"),
                sportradar_id=entry.get("sportradar_id"),
                fantasypros_id=entry.get("fantasypros_id"),
                rotowire_id=entry.get("rotowire_id"),
                fantasy_data_id=entry.get("fantasy_data_id"),
            )
        )
    return rows


def _load_ff_playerids(path: Path) -> dict[str, dict]:
    """Return dict keyed by gsis_id."""
    data = json.loads(path.read_text())
    crosswalk: dict[str, dict] = {}
    for entry in data.get("entries", []):
        gsis = entry.get("gsis_id")
        if gsis:
            crosswalk[gsis] = entry
    return crosswalk


def _load_sleeper_passthrough(path: Path) -> dict[str, dict]:
    """Return dict keyed by sleeper_id (same file as ff_playerids, different index)."""
    data = json.loads(path.read_text())
    passthrough: dict[str, dict] = {}
    for entry in data.get("entries", []):
        sid = entry.get("sleeper_id")
        if sid:
            passthrough[str(sid)] = entry
    return passthrough


def _load_alias_bridge(path: Path) -> dict[tuple, str]:
    """Return dict keyed by (normalized_name, position, draft_class) → sleeper_id."""
    import re

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()

    data = json.loads(path.read_text())
    bridge: dict[tuple, str] = {}
    for entry in data.get("entries", []):
        norm = entry.get("normalized_name") or normalize(entry.get("dg_name", ""))
        pos = entry.get("position", "").upper()
        dc = entry.get("draft_class")
        sid = entry.get("sleeper_id")
        if norm and pos and dc and sid:
            bridge[(norm, pos, int(dc))] = str(sid)
    return bridge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run identity coverage audit.")
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--ff-playerids", type=Path, default=None)
    parser.add_argument("--alias-bridge", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("app/data/identity"))
    parser.add_argument("--run-id", type=str, default=None)
    args = parser.parse_args(argv)

    rows = _load_cohort(args.cohort)

    ff_playerids: dict[str, dict] = {}
    sleeper_passthrough: dict[str, dict] = {}
    if args.ff_playerids and args.ff_playerids.exists():
        ff_playerids = _load_ff_playerids(args.ff_playerids)
        sleeper_passthrough = _load_sleeper_passthrough(args.ff_playerids)

    alias_bridge: dict[tuple, str] = {}
    if args.alias_bridge and args.alias_bridge.exists():
        alias_bridge = _load_alias_bridge(args.alias_bridge)

    results, matrix = run_audit(
        rows,
        ff_playerids=ff_playerids,
        sleeper_passthrough=sleeper_passthrough,
        alias_bridge=alias_bridge,
        run_id=args.run_id,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_id = matrix.run_id

    matrix_path = args.out_dir / f"identity_coverage_matrix_{run_id}.json"
    matrix_path.write_text(json.dumps(matrix.as_dict(), indent=2))

    queue_path = args.out_dir / f"identity_review_queue_{run_id}.jsonl"
    with queue_path.open("w") as f:
        for r in results:
            if not r.resolved:
                f.write(json.dumps(r.as_dict()) + "\n")

    # Print summary
    print(f"\nIdentity Audit — run {run_id}")
    print(f"Input rows : {matrix.total_input_rows}")
    print(f"Output rows: {matrix.total_output_rows}  (preserved: {matrix.row_count_preserved})")
    print()
    print(f"{'Cohort':<25} {'Total':>7} {'Resolved':>9} {'Queue':>7} {'Loss%':>7}")
    print("-" * 60)
    for c in matrix.cohort_summary:
        print(
            f"{c.cohort:<25} {c.total:>7} {c.resolved:>9} {c.review_queue:>7}"
            f" {c.loss_rate * 100:>6.1f}%"
        )
    if matrix.duplicate_conflicts:
        print(f"\nDuplicate conflicts detected: {len(matrix.duplicate_conflicts)}")
        for d in matrix.duplicate_conflicts:
            print(f"  {d.field}={d.value!r}: {', '.join(d.player_names)}")
    else:
        print("\nNo duplicate ID conflicts detected.")
    print(f"\nArtifacts written:")
    print(f"  {matrix_path}")
    print(f"  {queue_path}")

    unresolved_count = sum(1 for r in results if not r.resolved)
    return 1 if unresolved_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
