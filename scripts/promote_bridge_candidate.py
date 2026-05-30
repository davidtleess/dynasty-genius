"""Subsystem 4 — bridge promotion CLI (the only blessed write path).

Usage:
    .venv/bin/python3.14 scripts/promote_bridge_candidate.py \\
        --identity-dir app/data/identity --draft-year 2025 \\
        --decision confirm --review-id rev_1 \\
        --prospect-uuid cpr_... --gsis-id 00-0001 --pfr-id ManningArch01 \\
        --draft-pick-no 1 --draft-round 1 --nfl-team CAR \\
        --evidence "..." --reviewer davidleess

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §3.3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.dynasty_genius.identity.prospect_nfl_bridge import (
    PromotionDecision,
    ProspectNflBridgeEntry,
    promote_bridge_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a bridge candidate (spec §3.3).")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument(
        "--decision",
        type=str,
        required=True,
        choices=["confirm", "udfa", "reject", "defer"],
    )
    parser.add_argument("--review-id", type=str, default=None)
    parser.add_argument("--prospect-uuid", type=str, required=True)

    # Confirm/UDFA entry fields
    parser.add_argument("--gsis-id", type=str, default=None)
    parser.add_argument("--pfr-id", type=str, default=None)
    parser.add_argument("--draft-pick-no", type=int, default=None)
    parser.add_argument("--draft-round", type=int, default=None)
    parser.add_argument("--nfl-team", type=str, default=None)

    # Provenance (required for confirm/udfa; passed through from a discovery run)
    parser.add_argument("--nflreadr-source", type=str, default="nflreadpy.draft_picks")
    parser.add_argument("--nflreadr-season", type=int, default=None)
    parser.add_argument("--draft-truth-content-hash", type=str, default="")
    parser.add_argument("--nflreadr-fetched-at", type=str, default="")

    parser.add_argument("--evidence", type=str, default=None)
    parser.add_argument("--note", type=str, default=None)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    decision_kind = args.decision
    s3_registry = None  # only loaded when needed
    if decision_kind in ("confirm", "udfa"):
        # Round 2 patch 1: load S3 for accepted-decision validation
        from src.dynasty_genius.identity.college_prospect_identity import load_registry
        s3_registry = load_registry(args.identity_dir / "college_prospect_registry.json")
        udfa = decision_kind == "udfa"
        entry = ProspectNflBridgeEntry.model_validate({
            "prospect_uuid": args.prospect_uuid,
            "gsis_id": args.gsis_id,
            "pfr_id": args.pfr_id,
            "draft_year": args.draft_year,
            "draft_pick_no": args.draft_pick_no,
            "draft_round": args.draft_round,
            "nfl_team": args.nfl_team,
            "udfa": udfa,
            "nflreadr_source": args.nflreadr_source,
            "nflreadr_season": args.nflreadr_season or args.draft_year,
            "draft_truth_content_hash": args.draft_truth_content_hash,
            "nflreadr_fetched_at": args.nflreadr_fetched_at,
            "evidence_snapshot": None,
            "event_id": "placeholder",
            "decided_at": "placeholder",
            "reviewer_id": args.reviewer,
            "decision": "confirm" if not udfa else "udfa",
            "note": args.note,
        })
        decision = PromotionDecision(kind=decision_kind, entry=entry)
    else:
        decision = PromotionDecision(kind=decision_kind, prospect_uuid=args.prospect_uuid)

    result = promote_bridge_candidate(
        review_id=args.review_id,
        decision=decision,
        identity_dir=args.identity_dir,
        draft_year=args.draft_year,
        reviewer_id=args.reviewer,
        evidence=args.evidence,
        note=args.note,
        s3_registry=s3_registry,
    )
    print(f"exit_code={result.exit_code} event_id={result.event_id}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
