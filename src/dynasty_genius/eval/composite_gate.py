"""Step 0.5 — pure helpers for the unified composite validity gate.

Spec: docs/superpowers/specs/2026-06-12-step-0-5-composite-validation-gate-design.md

This module holds only side-effect-free predicates over ``FoldResult`` (no I/O, no
model calls, no harness/market imports). The recency-aware status function
(``compute_model_status``) is added in a later task; this file currently provides
the per-fold predicates and the fail-loud cold-start identifier.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from src.dynasty_genius.eval.backtest_artifact import FoldResult

# Locked thresholds (spec §10, three-way cockpit consensus).
SPEARMAN_THRESHOLD = 0.55
R2_FLOOR = 0.0
CI_WIDTH_MAX = 0.30


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
