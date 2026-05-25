"""Draft-capital bake-off evaluator for Phase 13.2.

This module compares already-scored draft-capital candidates. It does not fit
models, mutate Engine A features, or promote a candidate.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from src.dynasty_genius.eval.draft_capital_manifest import (
    DRAFT_CAPITAL_CANDIDATE_MANIFEST,
    PROHIBITED_INPUTS,
    DraftCapitalCandidateManifest,
    candidate_names,
)
from src.dynasty_genius.eval.draft_class_loocv import (
    DraftClassEvaluationRow,
    DraftClassLOOCVResult,
    evaluate_candidate_loocv,
)


class DraftCapitalBakeoffError(ValueError):
    """Raised when a bake-off cannot be run safely."""


@dataclasses.dataclass(frozen=True)
class DraftCapitalCandidateResult:
    name: str
    role: str
    position: str
    promotion_eligible: bool
    fold_count: int
    mean_kendall_tau: Optional[float]
    mean_spearman_rho: Optional[float]
    mean_rmse: Optional[float]
    loocv_result: DraftClassLOOCVResult

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "position": self.position,
            "promotion_eligible": self.promotion_eligible,
            "fold_count": self.fold_count,
            "mean_kendall_tau": self.mean_kendall_tau,
            "mean_spearman_rho": self.mean_spearman_rho,
            "mean_rmse": self.mean_rmse,
            "loocv_result": self.loocv_result.as_dict(),
        }


@dataclasses.dataclass(frozen=True)
class DraftCapitalBakeoffResult:
    position: str
    fold_strategy: str
    candidates: tuple[DraftCapitalCandidateResult, ...]
    prohibited_inputs: tuple[str, ...]
    promotion_decision: str

    @property
    def rank_order(self) -> tuple[DraftCapitalCandidateResult, ...]:
        return tuple(
            sorted(
                self.candidates,
                key=lambda candidate: (
                    candidate.mean_kendall_tau is not None,
                    candidate.mean_kendall_tau if candidate.mean_kendall_tau is not None else float("-inf"),
                    candidate.mean_spearman_rho if candidate.mean_spearman_rho is not None else float("-inf"),
                ),
                reverse=True,
            )
        )

    @property
    def leading_candidate(self) -> Optional[DraftCapitalCandidateResult]:
        ranked = [candidate for candidate in self.rank_order if candidate.mean_kendall_tau is not None]
        return ranked[0] if ranked else None

    def as_dict(self) -> dict:
        return {
            "position": self.position,
            "fold_strategy": self.fold_strategy,
            "promotion_decision": self.promotion_decision,
            "prohibited_inputs": list(self.prohibited_inputs),
            "leading_candidate": self.leading_candidate.name if self.leading_candidate else None,
            "rank_order": [candidate.name for candidate in self.rank_order],
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }


def _assert_required_candidates_present(
    rows: list[DraftClassEvaluationRow],
    manifest: DraftCapitalCandidateManifest,
    *,
    position: str,
) -> None:
    present = {
        row.candidate_name
        for row in rows
        if row.position.upper() == position.upper()
    }
    missing = candidate_names(manifest) - present
    if missing:
        raise DraftCapitalBakeoffError(
            f"missing required draft-capital candidates for {position.upper()}: {sorted(missing)}"
        )


def run_draft_capital_bakeoff(
    rows: list[DraftClassEvaluationRow],
    *,
    position: str,
    manifest: DraftCapitalCandidateManifest = DRAFT_CAPITAL_CANDIDATE_MANIFEST,
) -> DraftCapitalBakeoffResult:
    """Run LOOCV for every manifest candidate for one position."""
    _assert_required_candidates_present(rows, manifest, position=position)

    candidate_results: list[DraftCapitalCandidateResult] = []
    for candidate in manifest.candidates:
        loocv = evaluate_candidate_loocv(
            rows,
            candidate_name=candidate.name,
            position=position,
        )
        candidate_results.append(
            DraftCapitalCandidateResult(
                name=candidate.name,
                role=candidate.role,
                position=position.upper(),
                promotion_eligible=candidate.promotion_eligible,
                fold_count=len(loocv.folds),
                mean_kendall_tau=loocv.mean_kendall_tau,
                mean_spearman_rho=loocv.mean_spearman_rho,
                mean_rmse=loocv.mean_rmse,
                loocv_result=loocv,
            )
        )

    return DraftCapitalBakeoffResult(
        position=position.upper(),
        fold_strategy=manifest.validation_protocol.fold_strategy,
        candidates=tuple(candidate_results),
        prohibited_inputs=tuple(sorted(PROHIBITED_INPUTS)),
        promotion_decision="requires_david_review",
    )
