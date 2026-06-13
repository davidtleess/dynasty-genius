"""Step 0.5 — pure helpers for the unified composite validity gate.

Spec: docs/superpowers/specs/2026-06-12-step-0-5-composite-validation-gate-design.md

This module holds only side-effect-free predicates over ``FoldResult`` (no I/O, no
model calls, no harness/market imports). The recency-aware status function
(``compute_model_status``) is added in a later task; this file currently provides
the per-fold predicates and the fail-loud cold-start identifier.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from src.dynasty_genius.eval.backtest_artifact import FoldResult, StatusExplanation

# Locked thresholds (spec §10, three-way cockpit consensus).
SPEARMAN_THRESHOLD = 0.55
R2_FLOOR = 0.0
CI_WIDTH_MAX = 0.30
NULL_COVERAGE_MIN = 0.90


def ci_width(ci: Tuple[float, float]) -> float:
    """Width of a (low, high) confidence interval, rounded to absorb float noise."""
    return round(ci[1] - ci[0], 10)


def fold_rank_pass(fold: FoldResult) -> bool:
    """Per-fold rank gate: Spearman >= threshold AND R² > floor.

    R² of ``None`` fails closed (a fold with no computable R² cannot pass).
    """
    return (
        fold.spearman_rho >= SPEARMAN_THRESHOLD
        and fold.r2_oos is not None
        and fold.r2_oos > R2_FLOOR
    )


def fold_ci_adequate(fold: FoldResult) -> bool:
    """Per-fold sample adequacy: Spearman 95% BCa CI-width <= max (spec §10.1)."""
    return ci_width(fold.spearman_rho_bca_ci95) <= CI_WIDTH_MAX


def identify_cold_start_fold(folds: List[FoldResult]) -> Optional[int]:
    """Return the fold_index that is UNIQUELY both min ``test_year`` AND min train length.

    Fail-loud (spec §3.3 / §6.6): if the min-``test_year`` fold is not also uniquely
    the thinnest-train fold, return ``None`` — no cold-start excuse is granted. This
    prevents the narrow cold-start exception from degrading into a generic
    "tolerate any old fold" rule after a future fold-layout change.
    """
    if not folds:
        return None
    min_year = min(f.test_year for f in folds)
    year_min = [f for f in folds if f.test_year == min_year]
    if len(year_min) != 1:
        return None
    candidate = year_min[0]
    min_train = min(len(f.train_years) for f in folds)
    train_min = [f for f in folds if len(f.train_years) == min_train]
    if len(train_min) != 1 or train_min[0].fold_index != candidate.fold_index:
        return None
    return candidate.fold_index


def effective_rank_gate_pass(expl: StatusExplanation) -> bool:
    """Rank gate WITH cold-start tolerance: pass iff no fold failed the rank
    predicate except (optionally) the mechanically-verified cold-start fold.

    A failing fold with no cold-start excuse (``cold_start_fold_index`` is None)
    fails the gate — fail-loud.
    """
    return not expl.failed_rank_folds or all(
        fi == expl.cold_start_fold_index for fi in expl.failed_rank_folds
    )


def effective_ci_adequacy_gate_pass(expl: StatusExplanation) -> bool:
    """CI-adequacy gate with the SAME cold-start tolerance as the rank gate."""
    return not expl.failed_ci_folds or all(
        fi == expl.cold_start_fold_index for fi in expl.failed_ci_folds
    )


def compute_model_status(
    folds: List[FoldResult],
    null_coverage_min_obs: Optional[float],
    leakage_clean: bool,
) -> Tuple[str, StatusExplanation]:
    """Recency-aware validity status (spec §3.3). Returns ``(status, StatusExplanation)``.

    ``VALIDATED`` requires ALL of: every fold passes the rank + CI-adequacy gates
    EXCEPT the single fail-loud cold-start fold may be excused; the most-recent fold
    (max ``test_year``) passes both; and the hard floors hold (leakage-clean,
    null-coverage >= ``NULL_COVERAGE_MIN``, >= 2 folds). A hard-floor failure forces
    ``EXPERIMENTAL`` regardless of rank/R²/recency. Anything that clears the floors
    but misses a VALIDATED condition for a non-floor reason is ``PROVISIONAL``.

    Pure: no I/O, no market/G3 coupling. G3 market-superiority never enters here.
    """
    cold = identify_cold_start_fold(folds)
    most_recent = max(folds, key=lambda f: f.test_year) if folds else None

    failed_rank = [f.fold_index for f in folds if not fold_rank_pass(f)]
    failed_ci = [f.fold_index for f in folds if not fold_ci_adequate(f)]
    mr_pass = bool(
        most_recent is not None
        and fold_rank_pass(most_recent)
        and fold_ci_adequate(most_recent)
    )

    expl = StatusExplanation(
        failed_rank_folds=failed_rank,
        failed_ci_folds=failed_ci,
        cold_start_fold_index=cold,
        cold_start_tolerated=bool(
            cold is not None and (cold in failed_rank or cold in failed_ci)
        ),
        most_recent_fold_index=most_recent.fold_index if most_recent is not None else None,
        most_recent_fold_pass=mr_pass if most_recent is not None else None,
        null_coverage_min=null_coverage_min_obs,
        leakage_clean=leakage_clean,
    )

    # Hard safety floors first (spec §3.3 #4 / §6.3) — dominate rank/R²/recency.
    if not leakage_clean:
        expl.reason = "leakage not clean -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl
    if null_coverage_min_obs is None or null_coverage_min_obs < NULL_COVERAGE_MIN:
        expl.reason = "null-coverage below floor -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl
    if len(folds) < 2:
        expl.reason = "insufficient folds -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl

    if (
        effective_rank_gate_pass(expl)
        and effective_ci_adequacy_gate_pass(expl)
        and mr_pass
    ):
        expl.reason = (
            "all folds pass (cold-start excused if any); most-recent passes -> VALIDATED"
        )
        return "VALIDATED", expl
    expl.reason = "non-cold-start fold failure or most-recent failure -> PROVISIONAL"
    return "PROVISIONAL", expl
