from typing import Optional

from src.dynasty_genius.eval.backtest_artifact import (
    DivergenceResult,
    FoldResult,
    StabilityResult,
)
from src.dynasty_genius.eval.backtest_harness import evaluate_promotion_gates


def build_mock_fold(
    tau: float = 0.45,
    tau_ci_low: float = 0.25,
    model_ndcg: Optional[float] = 0.85,
    market_ndcg: Optional[float] = 0.80,
) -> FoldResult:
    return FoldResult(
        fold_index=1,
        train_years=[2018],
        test_year=2020,
        outcome_seasons=[2021, 2022],
        n_train=100,
        n_test=50,
        kendall_tau=tau,
        kendall_tau_bca_ci95=(tau_ci_low, tau + 0.1),
        spearman_rho=0.6,
        spearman_rho_bca_ci95=(0.5, 0.7),
        rank_ic=0.6,
        rmse=3.5,
        mae=2.8,
        ndcg_at_24_model=model_ndcg,
        ndcg_at_24_market=market_ndcg,
    )


def build_mock_stability(
    max_dev: float = 15.0,
    dm_p: Optional[float] = 0.05,
) -> StabilityResult:
    return StabilityResult(
        rmse_per_fold=[3.2, 3.5, 3.8, 3.4],
        rmse_mean=3.475,
        rmse_cv=0.07,
        rmse_max_deviation_pct=max_dev,
        dm_hln_pvalue=dm_p,
    )


def build_mock_divergence(
    n_flagged: int = 40,
    mw_p: float = 0.05,
    diff_ci_low: float = 0.05,
    hit_rate_ci_low: float = 0.55,
) -> DivergenceResult:
    return DivergenceResult(
        n_flagged=n_flagged,
        n_excluded_injury=0,
        forward_horizon_days=180,
        position_beta=0.1,
        mean_alpha_flagged=0.15,
        mean_alpha_control=0.05,
        diff_bca_ci95=(diff_ci_low, 0.15),
        mann_whitney_u=150.0,
        mann_whitney_p=mw_p,
        mann_whitney_method="asymptotic",
        hit_rate=0.65,
        hit_rate_wilson_ci95=(hit_rate_ci_low, 0.75),
    )


def test_g1_pass_logic():
    # Pass WR: mean tau >= 0.40 and 3/4 CIs >= 0.20
    folds = [
        build_mock_fold(tau=0.45, tau_ci_low=0.25),
        build_mock_fold(tau=0.42, tau_ci_low=0.22),
        build_mock_fold(tau=0.40, tau_ci_low=0.21),
        build_mock_fold(tau=0.35, tau_ci_low=0.15),
    ]
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is True

    # Fail WR: mean tau < 0.40
    folds[0].kendall_tau = 0.35
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is False

    # Fail WR: only 2/4 CIs >= 0.20
    folds = [
        build_mock_fold(tau=0.50, tau_ci_low=0.25),
        build_mock_fold(tau=0.50, tau_ci_low=0.25),
        build_mock_fold(tau=0.50, tau_ci_low=0.15),
        build_mock_fold(tau=0.50, tau_ci_low=0.15),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is False

    # Pass QB: mean tau >= 0.30
    folds = [build_mock_fold(tau=0.31, tau_ci_low=0.21)] * 4
    gate = evaluate_promotion_gates(folds, stability, "QB")
    assert gate.g1_rank_correlation_pass is True


def test_g2_stability_logic():
    folds = [build_mock_fold()] * 4
    
    # Pass: dev <= 25% and dm_p <= 0.10
    stability = build_mock_stability(max_dev=20.0, dm_p=0.08)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is True

    # Fail: dev > 25%
    stability = build_mock_stability(max_dev=26.0, dm_p=0.05)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is False

    # Fail: dm_p > 0.10
    stability = build_mock_stability(max_dev=10.0, dm_p=0.11)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is False


def test_g3_market_superiority_logic():
    stability = build_mock_stability()
    
    # Pass: 3/4 wins
    folds = [
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.80, market_ndcg=0.85),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass is True
    assert gate.g4_divergence_validity_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # Fail: 2/4 wins
    folds[2].ndcg_at_24_model = 0.80
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass is False
    assert gate.overall_grade == "ACTIVE_B"

    # Deferred: all market data None
    folds = [build_mock_fold(market_ndcg=None)] * 4
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass == "deferred"
    assert gate.g4_divergence_validity_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B"

    # Fail: only 2 folds available, even if we win both (need 3 wins)
    folds = [
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=None, market_ndcg=None),
        build_mock_fold(model_ndcg=None, market_ndcg=None),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass is False
    assert gate.overall_grade == "ACTIVE_B"


def test_g4_divergence_logic():
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    
    # Pass all G1-G3
    # G4 Pass -> DECISION_GRADE
    div = build_mock_divergence(
        n_flagged=40,
        mw_p=0.05,
        diff_ci_low=0.01,
        hit_rate_ci_low=0.51,
    )
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass is True
    assert gate.overall_grade == "DECISION_GRADE"

    # G4 Fail: p > 0.10
    div = build_mock_divergence(mw_p=0.11)
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass is False
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # G4 Insufficient Data: n < 30
    div = build_mock_divergence(n_flagged=25)
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass == "insufficient_data"
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"


def test_grade_hierarchy():
    # G1 fail -> ACTIVE_B even if others pass
    folds = [build_mock_fold(tau=0.1)] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.overall_grade == "ACTIVE_B"

    # G2 fail -> ACTIVE_B
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability(max_dev=50.0)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.overall_grade == "ACTIVE_B"

    # TE position can now clear EXPERIMENTAL when G1/G2 pass.
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "TE")
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # TE remains EXPERIMENTAL when a core gate fails.
    folds = [build_mock_fold(tau=0.1)] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "TE")
    assert gate.overall_grade == "EXPERIMENTAL"


def test_gate_version_field_is_v1():
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.gate_version == "1.0"
