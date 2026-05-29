"""Subsystem 4 — bridge discovery CLI (per spec §3.3 stage i).

Usage:
    .venv/bin/python3.14 scripts/build_prospect_nfl_bridge.py \\
        --identity-dir app/data/identity --draft-year 2025 \\
        --run-id manual_2025_$(date -u +%Y%m%dT%H%MZ) \\
        [--nflreadr-fixture tests/fixtures/backtest_mock_draft/nflreadr_synthetic/2025_draft.json]

Reads S3 confirmed prospects for the ``draft_year``; fetches nflreadr draft
truth (or loads a fixture for synthetic mode); writes per-run review queue,
unmatched UDFA candidates, and coverage matrix.

Round 2 patch 6 (Codex plan review): all per-run files written via atomic
.tmp + os.replace pattern (matches bridge atomic-write discipline).

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §3.3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os as _os
import sys
from datetime import datetime
from pathlib import Path

from src.dynasty_genius.identity.college_prospect_identity import load_registry
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    NflTruthRow,
    surface_nfl_bridge_candidates,
)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    _os.replace(tmp, path)


def _load_nflreadr_draft_truth(draft_year: int, fixture_path: Path | None) -> list[NflTruthRow]:
    if fixture_path is not None:
        raw = json.loads(fixture_path.read_text())
        return [NflTruthRow.model_validate(r) for r in raw["rows"]]
    # Real nflreadr fetch
    try:
        import nflreadpy
        df = nflreadpy.load_draft_picks(seasons=[draft_year])
        rows: list[NflTruthRow] = []
        for row in df.iter_rows(named=True):
            rows.append(NflTruthRow(
                gsis_id=row.get("gsis_id", "") or "",
                pfr_id=row.get("pfr_id"),
                full_name=row.get("pfr_player_name") or row.get("full_name") or "",
                normalized_name=(row.get("pfr_player_name") or "").lower(),
                position=row.get("position", ""),
                college=row.get("college"),
                draft_year=draft_year,
                draft_pick_no=int(row.get("pick", 0)),
                draft_round=int(row.get("round", 0)),
                nfl_team=row.get("team", ""),
                fetched_at=datetime.utcnow().isoformat() + "Z",
            ))
        return rows
    except Exception as e:
        print(f"nflreadr fetch failed: {e}", file=sys.stderr)
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build prospect↔NFL bridge discovery output (spec §3.3 stage i)."
    )
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--nflreadr-fixture", type=Path, default=None,
                        help="Optional fixture path for synthetic mode")
    args = parser.parse_args(argv)

    args.identity_dir.mkdir(parents=True, exist_ok=True)

    # Load S3 confirmed prospects for this class
    s3_registry_path = args.identity_dir / "college_prospect_registry.json"
    s3_registry = load_registry(s3_registry_path)
    s3_prospects = [
        e for e in s3_registry.entries.values()
        if e.draft_class == args.draft_year and e.verification_status == "confirmed"
    ]

    # Fetch nflreadr truth
    nfl_rows = _load_nflreadr_draft_truth(args.draft_year, args.nflreadr_fixture)
    truth_content_hash = hashlib.sha256(
        json.dumps(
            [r.model_dump() for r in nfl_rows], sort_keys=True
        ).encode()
    ).hexdigest()

    # Build review queue + UDFA candidates
    review_entries: list[dict] = []
    udfa_candidates: list[dict] = []
    matched_uuids: set[str] = set()
    for prospect in s3_prospects:
        candidates = surface_nfl_bridge_candidates(prospect, nfl_rows)
        if candidates:
            matched_uuids.add(prospect.prospect_uuid)
            for cand in candidates:
                review_entries.append({
                    "run_id": args.run_id,
                    "review_id": f"{args.run_id}_review_{len(review_entries) + 1:04d}",
                    "prospect_uuid": prospect.prospect_uuid,
                    "gsis_id": cand.gsis_id,
                    "match_score": cand.match_score,
                    "score_breakdown": cand.score_breakdown,
                    "risk_flags": list(cand.risk_flags),
                    "nfl_truth_row": cand.nfl_truth_row,
                    "draft_truth_content_hash": truth_content_hash,
                    "decided_at": None,
                    "decision": None,
                    "event_id": None,
                })
        else:
            udfa_candidates.append({
                "run_id": args.run_id,
                "prospect_uuid": prospect.prospect_uuid,
                "normalized_name": prospect.normalized_name,
                "position": prospect.position,
                "current_school": prospect.current_school,
                "draft_truth_content_hash": truth_content_hash,
            })

    # Round 2 patch 6: atomic writes for per-run files
    review_path = args.identity_dir / f"prospect_nfl_review_queue_{args.draft_year}_{args.run_id}.jsonl"
    _atomic_write_text(
        review_path,
        "\n".join(json.dumps(e, sort_keys=True) for e in review_entries)
        + ("\n" if review_entries else ""),
    )

    udfa_path = (
        args.identity_dir
        / f"prospect_nfl_unmatched_udfa_candidates_{args.draft_year}_{args.run_id}.jsonl"
    )
    _atomic_write_text(
        udfa_path,
        "\n".join(json.dumps(e, sort_keys=True) for e in udfa_candidates)
        + ("\n" if udfa_candidates else ""),
    )

    coverage_path = (
        args.identity_dir / f"prospect_nfl_coverage_{args.draft_year}_{args.run_id}.json"
    )
    coverage = {
        "draft_year": args.draft_year,
        "run_id": args.run_id,
        "total_s3_confirmed_prospects": len(s3_prospects),
        "total_nfl_truth_rows": len(nfl_rows),
        "prospects_with_candidates": len(matched_uuids),
        "prospects_unmatched_as_udfa": len(udfa_candidates),
        "draft_truth_content_hash": truth_content_hash,
    }
    _atomic_write_text(coverage_path, json.dumps(coverage, indent=2, sort_keys=True))

    print(
        f"run_id={args.run_id} review_entries={len(review_entries)} "
        f"udfa_candidates={len(udfa_candidates)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
