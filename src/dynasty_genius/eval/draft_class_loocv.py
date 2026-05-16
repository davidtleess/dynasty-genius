"""Draft-class leave-one-class-out validation harness for Phase 13.2.

The harness evaluates already-scored candidate rows. It does not fit models,
transform Engine A features, or promote candidates.
"""
from __future__ import annotations

import dataclasses
import math
from statistics import mean
from typing import Optional

from src.dynasty_genius.eval.backtest_metrics import compute_subgroup_metrics
from src.dynasty_genius.eval.draft_capital_manifest import PROHIBITED_INPUTS


class DraftClassLOOCVError(ValueError):
    """Raised when LOOCV inputs violate the Phase 13 validation contract."""


@dataclasses.dataclass(frozen=True)
class DraftClassEvaluationRow:
    candidate_name: str
    player_id: str
    position: str
    draft_year: int
    predicted_score: float
    realized_value: float
    source_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.player_id:
            raise DraftClassLOOCVError("player_id is required for draft-class validation")
        if not self.position:
            raise DraftClassLOOCVError("position is required for draft-class validation")


@dataclasses.dataclass(frozen=True)
class DraftClassFold:
    test_year: int
    train_years: tuple[int, ...]
    train_rows: tuple[DraftClassEvaluationRow, ...]
    test_rows: tuple[DraftClassEvaluationRow, ...]


@dataclasses.dataclass(frozen=True)
class DraftClassFoldResult:
    test_year: int
    train_years: tuple[int, ...]
    n_train: int
    n_test: int
    within_class_kendall_tau: Optional[float]
    within_class_spearman_rho: Optional[float]
    rmse: Optional[float]

    def as_dict(self) -> dict:
        return {
            "test_year": self.test_year,
            "train_years": list(self.train_years),
            "n_train": self.n_train,
            "n_test": self.n_test,
            "within_class_kendall_tau": self.within_class_kendall_tau,
            "within_class_spearman_rho": self.within_class_spearman_rho,
            "rmse": self.rmse,
        }


@dataclasses.dataclass(frozen=True)
class DraftClassLOOCVResult:
    candidate_name: str
    position: str
    fold_strategy: str
    folds: tuple[DraftClassFoldResult, ...]

    @property
    def mean_kendall_tau(self) -> Optional[float]:
        return _mean_present([fold.within_class_kendall_tau for fold in self.folds])

    @property
    def mean_spearman_rho(self) -> Optional[float]:
        return _mean_present([fold.within_class_spearman_rho for fold in self.folds])

    @property
    def mean_rmse(self) -> Optional[float]:
        return _mean_present([fold.rmse for fold in self.folds])

    def as_dict(self) -> dict:
        return {
            "candidate_name": self.candidate_name,
            "position": self.position,
            "fold_strategy": self.fold_strategy,
            "mean_kendall_tau": self.mean_kendall_tau,
            "mean_spearman_rho": self.mean_spearman_rho,
            "mean_rmse": self.mean_rmse,
            "folds": [fold.as_dict() for fold in self.folds],
        }


def _mean_present(values: list[Optional[float]]) -> Optional[float]:
    present = [value for value in values if value is not None and not math.isnan(value)]
    if not present:
        return None
    return float(mean(present))


def _filtered_rows(
    rows: list[DraftClassEvaluationRow],
    *,
    candidate_name: str,
    position: str,
) -> list[DraftClassEvaluationRow]:
    selected = [
        row for row in rows
        if row.candidate_name == candidate_name and row.position.upper() == position.upper()
    ]
    if not selected:
        raise DraftClassLOOCVError(
            f"no rows for candidate={candidate_name!r} position={position!r}"
        )
    return selected


def _assert_no_market_fields(rows: list[DraftClassEvaluationRow]) -> None:
    prohibited = {
        field
        for row in rows
        for field in row.source_fields
        if field.lower() in PROHIBITED_INPUTS
        or field.lower().startswith("ktc_")
        or field.lower().startswith("market_")
        or field.lower().startswith("fantasycalc_")
        or field.lower().startswith("adp")
    }
    if prohibited:
        raise DraftClassLOOCVError(
            f"market-derived source fields are prohibited in draft-capital validation: {sorted(prohibited)}"
        )


def build_loocv_folds(
    rows: list[DraftClassEvaluationRow],
    *,
    candidate_name: str,
    position: str,
) -> list[DraftClassFold]:
    """Build one fold per held-out draft class for a candidate and position."""
    selected = _filtered_rows(rows, candidate_name=candidate_name, position=position)
    _assert_no_market_fields(selected)

    years = tuple(sorted({row.draft_year for row in selected}))
    if len(years) < 2:
        raise DraftClassLOOCVError("leave-one-class-out requires at least two draft classes")

    folds: list[DraftClassFold] = []
    for test_year in years:
        test_rows = tuple(row for row in selected if row.draft_year == test_year)
        train_rows = tuple(row for row in selected if row.draft_year != test_year)
        train_years = tuple(year for year in years if year != test_year)
        folds.append(
            DraftClassFold(
                test_year=test_year,
                train_years=train_years,
                train_rows=train_rows,
                test_rows=test_rows,
            )
        )
    return folds


def evaluate_candidate_loocv(
    rows: list[DraftClassEvaluationRow],
    *,
    candidate_name: str,
    position: str,
) -> DraftClassLOOCVResult:
    """Evaluate within-class rank metrics over leave-one-draft-class-out folds."""
    folds = build_loocv_folds(rows, candidate_name=candidate_name, position=position)
    fold_results: list[DraftClassFoldResult] = []

    for fold in folds:
        predicted = [row.predicted_score for row in fold.test_rows]
        realized = [row.realized_value for row in fold.test_rows]
        metrics = compute_subgroup_metrics(predicted, realized)
        fold_results.append(
            DraftClassFoldResult(
                test_year=fold.test_year,
                train_years=fold.train_years,
                n_train=len(fold.train_rows),
                n_test=len(fold.test_rows),
                within_class_kendall_tau=metrics["kendall_tau"],
                within_class_spearman_rho=metrics["spearman_rho"],
                rmse=metrics["rmse"],
            )
        )

    return DraftClassLOOCVResult(
        candidate_name=candidate_name,
        position=position.upper(),
        fold_strategy="leave_one_draft_class_out",
        folds=tuple(fold_results),
    )
