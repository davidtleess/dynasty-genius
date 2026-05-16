#!/usr/bin/env python3
"""Identity coverage audit runner — Task 13.1.1.

Loads a player cohort fixture and source-ID lookup fixtures, runs the
deterministic resolution cascade, writes coverage matrix, review queue,
failure report, identity snapshot, and (when the gate passes) the PFF
materialization eligibility manifest.

Usage:
  .venv/bin/python3.14 scripts/run_identity_audit.py \\
      --cohort app/data/identity/_runs/te_cohort_2018_2025.json \\
      --ff-playerids app/data/identity/_runs/ff_playerids_<date>.json \\
      --alias-bridge app/data/prospect_alias_bridge.json \\
      --composite-registry app/data/identity/_runs/composite_registry.json \\
      --prospect-registry app/data/identity/_runs/prospect_registry.json \\
      --out-dir app/data/identity/_runs \\
      --max-loss-rate 0.02 \\
      --run-id te_2018_2025_<YYYYMMDD>

Fixture formats:
  cohort_fixture.json         — {"entries": [IdentityAuditRow fields as dicts, ...]}
  ff_playerids_fixture.json   — {"entries": [{"gsis_id": ..., "sleeper_id": ..., ...}, ...]}
  prospect_alias_bridge.json  — existing bridge format {"entries": [...]}
  composite_registry.json     — {"entries": [{"normalized_name": ..., "date_of_birth": ...,
                                              "position": ..., "draft_year": ...,
                                              "player_id": ...}, ...]}
  prospect_registry.json      — {"entries": [{"normalized_name": ..., "college": ...,
                                              "position": ..., "draft_year": ...,
                                              "player_id": ...}, ...]}

Outputs (written to --out-dir):
  identity_coverage_matrix_{run_id}.json
  identity_review_queue_{run_id}.jsonl
  identity_failure_report_{run_id}.md
  identity_snapshot_{run_id}.json          (gate must pass)
  pff_te_eligible_{run_id}.json            (gate must pass)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.audit.identity_coverage_matrix import (
    AuditResult,
    CoverageMatrix,
    IdentityAuditRow,
    ResolutionStage,
    run_audit,
)
from src.dynasty_genius.audit.identity_snapshot_generator import (
    IdentitySnapshotRow,
    generate_identity_snapshot,
    write_identity_snapshot,
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

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
    """Return dict keyed by (normalized_name, position, draft_year) → sleeper_id."""
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


def _load_composite_registry(path: Path) -> dict[tuple, str]:
    """Return dict keyed by (normalized_name, dob, position, draft_year) → player_id."""
    import re

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()

    data = json.loads(path.read_text())
    registry: dict[tuple, str] = {}
    for entry in data.get("entries", []):
        norm = entry.get("normalized_name") or normalize(entry.get("name", ""))
        dob = entry.get("date_of_birth", "")
        pos = entry.get("position", "").upper()
        dy = entry.get("draft_year")
        pid = entry.get("player_id")
        if norm and dob and pos and dy and pid:
            registry[(norm, dob, pos, int(dy))] = pid
    return registry


def _load_prospect_registry(path: Path) -> dict[tuple, str]:
    """Return dict keyed by (normalized_name, college, position, draft_year) → player_id."""
    import re

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()

    data = json.loads(path.read_text())
    registry: dict[tuple, str] = {}
    for entry in data.get("entries", []):
        norm = entry.get("normalized_name") or normalize(entry.get("name", ""))
        college = entry.get("college", "").lower()
        pos = entry.get("position", "").upper()
        dy = entry.get("draft_year")
        pid = entry.get("player_id")
        if norm and college and pos and dy and pid:
            registry[(norm, college, pos, int(dy))] = pid
    return registry


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _write_failure_report(
    path: Path,
    results: list[AuditResult],
    matrix: CoverageMatrix,
    run_id: str,
) -> None:
    """Write a human-readable Markdown failure report grouped by terminal stage."""
    unresolved = [r for r in results if not r.resolved]

    by_stage: dict[str, list[AuditResult]] = defaultdict(list)
    for r in unresolved:
        by_stage[r.stage.value].append(r)

    lines = [
        f"# Identity Failure Report — {run_id}",
        "",
        f"**Run ID:** {run_id}  ",
        f"**Timestamp:** {matrix.run_timestamp}  ",
        f"**Total input rows:** {matrix.total_input_rows}  ",
        f"**Unresolved rows:** {len(unresolved)}  ",
        "",
    ]

    for cov in matrix.cohort_summary:
        lines.append(
            f"**{cov.cohort}:** {cov.resolved}/{cov.total} resolved "
            f"({cov.loss_rate * 100:.1f}% loss rate)"
        )
    lines.append("")

    if not unresolved:
        lines.append("No unresolved rows. Gate passes.")
    else:
        lines.append("## Unresolved Rows by Terminal Stage")
        lines.append("")
        for stage_val, stage_results in sorted(by_stage.items()):
            lines.append(f"### {stage_val} ({len(stage_results)} rows)")
            lines.append("")
            for r in stage_results:
                row = r.input_row
                ids = ", ".join(
                    f"{f}={getattr(row, f)}"
                    for f in ("gsis_id", "sleeper_id", "player_id", "pff_id")
                    if getattr(row, f)
                )
                lines.append(f"- **{row.name}** ({row.position}, {row.draft_year}) — {ids or 'no source IDs'}")
                if r.notes:
                    lines.append(f"  - Note: {r.notes}")
            lines.append("")

    if matrix.duplicate_conflicts:
        lines.append("## Duplicate ID Conflicts")
        lines.append("")
        for d in matrix.duplicate_conflicts:
            lines.append(f"- `{d.field}={d.value}`: {', '.join(d.player_names)}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_pff_eligible_manifest(
    path: Path,
    results: list[AuditResult],
    run_id: str,
    run_timestamp: str,
) -> None:
    """Write the PFF materialization eligibility manifest.

    Eligible rows: deterministic resolutions (r.resolved is True, any Stage 1-6)
    plus manual approvals from the override registry (not yet wired here —
    override registry entries with review_status == "APPROVED" should be
    added by the caller if available).
    """
    eligible = []
    for r in results:
        if not r.resolved:
            continue
        entry: dict = {
            "player_id": r.resolved_player_id,
            "sleeper_id": r.resolved_sleeper_id,
            "gsis_id": r.resolved_gsis_id,
            "name": r.input_row.name,
            "resolution_stage": r.stage.value,
            "pff_id": r.input_row.pff_id,
        }
        eligible.append(entry)

    manifest = {
        "run_id": run_id,
        "generated_at": run_timestamp,
        "eligible_count": len(eligible),
        "note": (
            "Rows with r.resolved=True (deterministic Stages 1-6). "
            "Override registry APPROVED entries should be merged in separately."
        ),
        "eligible": eligible,
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run identity coverage audit.")
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--ff-playerids", type=Path, default=None)
    parser.add_argument("--alias-bridge", type=Path, default=None)
    parser.add_argument("--composite-registry", type=Path, default=None,
                        help="JSON fixture for composite name+DOB+pos+draft_year → player_id")
    parser.add_argument("--prospect-registry", type=Path, default=None,
                        help="JSON fixture for composite name+college+pos+draft_year → player_id")
    parser.add_argument("--out-dir", type=Path, default=Path("app/data/identity"))
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument(
        "--max-loss-rate",
        type=float,
        default=None,
        help="Acceptable loss rate per cohort (e.g. 0.02 for 98%% resolved). "
             "If set, exit 1 when any cohort exceeds this threshold. "
             "If not set, exit 1 when any rows are unresolved.",
    )
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

    composite_registry: dict[tuple, str] = {}
    if args.composite_registry and args.composite_registry.exists():
        composite_registry = _load_composite_registry(args.composite_registry)

    prospect_registry: dict[tuple, str] = {}
    if args.prospect_registry and args.prospect_registry.exists():
        prospect_registry = _load_prospect_registry(args.prospect_registry)

    results, matrix = run_audit(
        rows,
        ff_playerids=ff_playerids,
        sleeper_passthrough=sleeper_passthrough,
        alias_bridge=alias_bridge,
        composite_registry=composite_registry,
        prospect_registry=prospect_registry,
        run_id=args.run_id,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_id = matrix.run_id

    # --- Core artifacts (always written) ---
    matrix_path = args.out_dir / f"identity_coverage_matrix_{run_id}.json"
    matrix_path.write_text(json.dumps(matrix.as_dict(), indent=2))

    queue_path = args.out_dir / f"identity_review_queue_{run_id}.jsonl"
    with queue_path.open("w") as f:
        for r in results:
            if not r.resolved:
                f.write(json.dumps(r.as_dict()) + "\n")

    failure_report_path = args.out_dir / f"identity_failure_report_{run_id}.md"
    _write_failure_report(failure_report_path, results, matrix, run_id)

    # --- Print summary ---
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
    print(f"  {failure_report_path}")

    # --- Gate evaluation ---
    gate_fails = False
    if args.max_loss_rate is not None:
        for cov in matrix.cohort_summary:
            if not cov.passes_gate(args.max_loss_rate):
                print(
                    f"\nGATE FAIL: cohort '{cov.cohort}' loss_rate={cov.loss_rate:.4f} "
                    f"exceeds max={args.max_loss_rate:.4f}"
                )
                gate_fails = True
        if matrix.duplicate_conflicts:
            print(f"\nGATE FAIL: {len(matrix.duplicate_conflicts)} duplicate ID conflict(s)")
            gate_fails = True
    else:
        unresolved_count = sum(1 for r in results if not r.resolved)
        if unresolved_count > 0:
            gate_fails = True

    # --- Gate-gated artifacts (snapshot + eligibility manifest) ---
    if not gate_fails and not matrix.duplicate_conflicts:
        # Identity snapshot — refuses to overwrite; immutable once written
        snapshot_rows = [
            IdentitySnapshotRow(
                player_id=r.resolved_player_id or f"_unkeyed_{r.input_row.name}",
                gsis_id=r.resolved_gsis_id,
                sleeper_id=r.resolved_sleeper_id,
                pff_id=r.input_row.pff_id,
                pfr_id=r.input_row.pfr_id,
                cfbref_id=r.input_row.cfbref_id,
                espn_id=r.input_row.espn_id,
                yahoo_id=r.input_row.yahoo_id,
                sportradar_id=r.input_row.sportradar_id,
                fantasypros_id=r.input_row.fantasypros_id,
                rotowire_id=r.input_row.rotowire_id,
                fantasy_data_id=r.input_row.fantasy_data_id,
            )
            for r in results
            if r.resolved and r.resolved_player_id
        ]
        snapshot = generate_identity_snapshot(snapshot_rows, run_id=run_id)
        snapshot_path = args.out_dir / f"identity_snapshot_{run_id}.json"
        write_identity_snapshot(snapshot_path, snapshot)
        print(f"  {snapshot_path}")

        # PFF eligibility manifest
        eligible_path = args.out_dir / f"pff_te_eligible_{run_id}.json"
        _write_pff_eligible_manifest(eligible_path, results, run_id, matrix.run_timestamp)
        print(f"  {eligible_path}")

        print(f"\nGate PASSED (run_id={run_id})")
    else:
        print(f"\nGate FAILED — snapshot and eligibility manifest not written.")
        print("Triage the review queue and failure report, remediate, then re-run.")

    return 1 if gate_fails or matrix.duplicate_conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
