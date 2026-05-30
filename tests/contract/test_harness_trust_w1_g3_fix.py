"""Harness Trust Completion W1.3 RED: G3 primary-k and under-coverage semantics."""

from __future__ import annotations

from typing import Optional

from src.dynasty_genius.eval.backtest_artifact import FoldResult, StabilityResult
from src.dynasty_genius.eval.backtest_harness import evaluate_promotion_gates


def _fold(
    *,
    ndcg_at_12_model: Optional[float] = None,
    ndcg_at_12_market: Optional[float] = None,
    ndcg_at_24_model: Optional[float] = None,
    ndcg_at_24_market: Optional[float] = None,
) -> FoldResult:
    return FoldResult(
        fold_index=1,
        train_years=[2018, 2019],
        test_year=2020,
        outcome_seasons=[2021, 2022],
        n_train=120,
        n_test=50,
        kendall_tau=0.45,
        kendall_tau_bca_ci95=(0.25, 0.60),
        spearman_rho=0.55,
        spearman_rho_bca_ci95=(0.35, 0.70),
        rank_ic=0.55,
        rmse=3.2,
        mae=2.4,
        ndcg_at_12_model=ndcg_at_12_model,
        ndcg_at_12_market=ndcg_at_12_market,
        ndcg_at_24_model=ndcg_at_24_model,
        ndcg_at_24_market=ndcg_at_24_market,
    )


def _stability() -> StabilityResult:
    return StabilityResult(
        rmse_per_fold=[3.1, 3.3, 3.2, 3.4],
        rmse_mean=3.25,
        rmse_cv=0.04,
        rmse_max_deviation_pct=12.0,
        dm_hln_pvalue=0.05,
    )


def test_g3_defers_when_only_one_market_available_fold() -> None:
    folds = [
        _fold(ndcg_at_24_model=0.90, ndcg_at_24_market=0.80),
        _fold(),
        _fold(),
        _fold(),
    ]

    gate = evaluate_promotion_gates(folds, _stability(), "WR")

    assert gate.g3_market_superiority_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B"


def test_g3_defers_when_only_two_market_available_folds_even_if_both_win() -> None:
    folds = [
        _fold(ndcg_at_24_model=0.90, ndcg_at_24_market=0.80),
        _fold(ndcg_at_24_model=0.88, ndcg_at_24_market=0.81),
        _fold(),
        _fold(),
    ]

    gate = evaluate_promotion_gates(folds, _stability(), "WR")

    assert gate.g3_market_superiority_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B"


def test_g3_uses_position_primary_k_for_qb_verdict_not_hardcoded_24() -> None:
    folds = [
        _fold(
            ndcg_at_12_model=0.90,
            ndcg_at_12_market=0.80,
            ndcg_at_24_model=0.70,
            ndcg_at_24_market=0.80,
        ),
        _fold(
            ndcg_at_12_model=0.89,
            ndcg_at_12_market=0.81,
            ndcg_at_24_model=0.70,
            ndcg_at_24_market=0.80,
        ),
        _fold(
            ndcg_at_12_model=0.88,
            ndcg_at_12_market=0.82,
            ndcg_at_24_model=0.70,
            ndcg_at_24_market=0.80,
        ),
        _fold(
            ndcg_at_12_model=0.80,
            ndcg_at_12_market=0.84,
            ndcg_at_24_model=0.70,
            ndcg_at_24_market=0.80,
        ),
    ]

    gate = evaluate_promotion_gates(folds, _stability(), "QB")

    assert gate.g3_market_superiority_pass is True
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"


def test_g3_full_coverage_genuine_loss_still_fails() -> None:
    folds = [
        _fold(ndcg_at_24_model=0.70, ndcg_at_24_market=0.80),
        _fold(ndcg_at_24_model=0.71, ndcg_at_24_market=0.80),
        _fold(ndcg_at_24_model=0.72, ndcg_at_24_market=0.80),
        _fold(ndcg_at_24_model=0.85, ndcg_at_24_market=0.80),
    ]

    gate = evaluate_promotion_gates(folds, _stability(), "WR")

    assert gate.g3_market_superiority_pass is False
    assert gate.overall_grade == "ACTIVE_B"


def test_g3_excludes_incomplete_pairs_so_missing_model_is_not_a_false_win() -> None:
    # Codex W1.3 finding: a fold with market present but MODEL None must NOT count as a
    # win (the `or 0` fallback would beat a 0.0 market). A fold is G3-evaluable only as a
    # COMPLETE (model+market) pair. Here only 2 complete pairs remain → "deferred", never
    # a false pass.
    folds = [
        _fold(ndcg_at_24_market=0.0),                          # model None, market 0.0
        _fold(ndcg_at_24_model=0.90, ndcg_at_24_market=0.80),  # complete win
        _fold(ndcg_at_24_model=0.88, ndcg_at_24_market=0.81),  # complete win
        _fold(ndcg_at_24_market=0.50),                         # model None
    ]

    gate = evaluate_promotion_gates(folds, _stability(), "WR")

    assert gate.g3_market_superiority_pass == "deferred"
