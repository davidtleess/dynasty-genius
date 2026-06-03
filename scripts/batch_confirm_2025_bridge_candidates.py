"""S4 Task-6 Step-2 — deterministic batch confirmation of EXACT single-candidate bridges.

David authorized a deterministic reviewed batch for the bridge candidates that are
unambiguous: a confirmed S3 prospect whose discovery review queue holds exactly ONE
undecided candidate, that candidate scoring an exact 1.0, with a present gsis_id and a
college that agrees with the NFL truth row. Each is confirmed through the BLESSED
``promote_bridge_candidate`` write path (decision_log -> bridge artifact -> review-queue
closure), never a hand-rolled edit.

Multi-candidate prospects (>1 undecided review row) are NOT batched — they are left for
David's manual disambiguation (skipped_non_batch_count). A single-candidate row that does
NOT clear the guards (score!=1.0, missing gsis, or college disagreement — the Kaden Prather
false-positive class) fails the batch CLOSED before any write, so a known-bad single
candidate must be rejected manually first.

College agreement is checked explicitly and alias-aware: the S3 name-similarity scorer only
awards its school bonus on exact string equality, so a 1.0 score does NOT by itself prove the
schools match (e.g. "Ole Miss" vs "Mississippi" scores 1.0 on name+position alone). This
guard closes that gap.

CLI usage:
    .venv/bin/python3.14 scripts/batch_confirm_2025_bridge_candidates.py \\
        --identity-dir app/data/identity --draft-year 2025 \\
        --run-id manual_2025_<ts> --expected-count 68 --reviewer davidleess
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    load_registry,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (  # noqa: E402
    PromotionDecision,
    ProspectNflBridgeEntry,
    promote_bridge_candidate,
)

# Batch-scoped college aliases for the college<->NFL naming gaps observed in the 2025
# cohort. The NFL draft table and the CFBD roster spell some schools differently; the S3
# scorer does not know these (exact-match school bonus only), so the college-agreement guard
# resolves them here. Normalization also strips parenthetical qualifiers ("Miami (FL)") and
# maps "St."->"State". A more complete crosswalk is a future enhancement if new gaps appear.
_SCHOOL_ALIASES: dict[str, str] = {
    "ole miss": "mississippi",
    "ucf": "central florida",
}


def _norm_school(value: str | None) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"\s*\(.*?\)\s*", " ", s)          # drop "(fl)" etc.
    s = re.sub(r"\buniversity of\b", " ", s)
    s = re.sub(r"\bst\.?\b", "state", s)          # "iowa st." -> "iowa state"
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return _SCHOOL_ALIASES.get(s, s)


def _school_agrees(registry_school: str | None, nfl_college: str | None) -> bool:
    return _norm_school(registry_school) == _norm_school(nfl_college)


@dataclass(frozen=True)
class BridgeBatchResult:
    exit_code: int
    confirmed_count: int
    skipped_non_batch_count: int


def batch_confirm_exact_single_bridge_candidates(
    *,
    identity_dir: Path,
    draft_year: int,
    run_id: str,
    expected_count: int,
    reviewer_id: str,
) -> BridgeBatchResult:
    """Confirm the exact single-candidate, college-agreeing bridges through the blessed
    promote_bridge_candidate path. Fail-closed (raises ValueError, NO writes) on a count
    mismatch or any eligible candidate failing the score/college/gsis guards."""
    registry = load_registry(identity_dir / "college_prospect_registry.json")
    review_path = identity_dir / f"prospect_nfl_review_queue_{draft_year}_{run_id}.jsonl"
    rows = [
        json.loads(line)
        for line in review_path.read_text().splitlines()
        if line.strip()
    ]

    # Group only UNDECIDED rows by prospect. A prospect with exactly one undecided
    # candidate is batch-eligible; >1 is a multi-candidate manual case (skipped).
    undecided_by_uuid: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("decision") is None:
            undecided_by_uuid.setdefault(row["prospect_uuid"], []).append(row)

    eligible = [v[0] for v in undecided_by_uuid.values() if len(v) == 1]
    skipped_non_batch_count = sum(1 for v in undecided_by_uuid.values() if len(v) > 1)

    # Count guard — refuse a surprise cohort size before touching anything.
    if len(eligible) != expected_count:
        raise ValueError(
            f"expected {expected_count} exact single-candidate bridge rows, "
            f"found {len(eligible)}"
        )

    # Per-candidate guards (fail closed BEFORE any write).
    for row in eligible:
        uuid = row["prospect_uuid"]
        if row.get("match_score") != 1.0:
            raise ValueError(
                f"refusing batch: candidate {uuid} match_score "
                f"{row.get('match_score')} is not an exact 1.0 score"
            )
        if not row.get("gsis_id"):
            raise ValueError(
                f"refusing batch: candidate {uuid} has a missing/empty gsis_id"
            )
        reg_entry = registry.get(uuid)
        nfl_college = (row.get("nfl_truth_row") or {}).get("college")
        if reg_entry is None or not _school_agrees(reg_entry.current_school, nfl_college):
            raise ValueError(
                f"refusing batch: candidate {uuid} college disagreement "
                f"(registry={getattr(reg_entry, 'current_school', None)!r} "
                f"vs nfl={nfl_college!r})"
            )

    # All guards pass — confirm each through the blessed bridge promotion path.
    confirmed_count = 0
    for row in eligible:
        truth = row["nfl_truth_row"]
        entry = ProspectNflBridgeEntry.model_validate({
            "prospect_uuid": row["prospect_uuid"],
            "gsis_id": row["gsis_id"],
            "pfr_id": truth.get("pfr_id"),
            "draft_year": draft_year,
            "draft_pick_no": truth.get("draft_pick_no"),
            "draft_round": truth.get("draft_round"),
            "nfl_team": truth.get("nfl_team"),
            "udfa": False,
            "nflreadr_source": "nflreadpy.draft_picks",
            "nflreadr_season": draft_year,
            "draft_truth_content_hash": row["draft_truth_content_hash"],
            "nflreadr_fetched_at": truth.get("fetched_at", ""),
            "evidence_snapshot": truth,
            "event_id": "placeholder",
            "decided_at": "placeholder",
            "reviewer_id": reviewer_id,
            "decision": "confirm",
            "note": "Task-6 Step-2 deterministic batch confirm (exact single-candidate, college-agree; David-authorized).",
        })
        result = promote_bridge_candidate(
            review_id=row["review_id"],
            decision=PromotionDecision(kind="confirm", entry=entry),
            identity_dir=identity_dir,
            draft_year=draft_year,
            reviewer_id=reviewer_id,
            evidence=None,
            note=None,
            s3_registry=registry,
        )
        if result.exit_code != 0:
            return BridgeBatchResult(
                exit_code=result.exit_code,
                confirmed_count=confirmed_count,
                skipped_non_batch_count=skipped_non_batch_count,
            )
        confirmed_count += 1

    return BridgeBatchResult(
        exit_code=0,
        confirmed_count=confirmed_count,
        skipped_non_batch_count=skipped_non_batch_count,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-confirm exact single-candidate 2025 prospect->NFL bridges (Task-6 Step-2)."
    )
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    result = batch_confirm_exact_single_bridge_candidates(
        identity_dir=args.identity_dir,
        draft_year=args.draft_year,
        run_id=args.run_id,
        expected_count=args.expected_count,
        reviewer_id=args.reviewer,
    )
    print(
        f"bridge batch confirm complete -> exit_code={result.exit_code} "
        f"confirmed={result.confirmed_count} skipped_non_batch={result.skipped_non_batch_count}"
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
