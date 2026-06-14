from typing import Optional

from src.dynasty_genius.eval.backtest_artifact import (
    DivergenceResult,
    FoldResult,
    StabilityResult,
)


def build_mock_fold(
    tau: float = 0.45,
    tau_ci_low: float = 0.25,
    model_ndcg: Optional[float] = 0.85,
    market_ndcg: Optional[float] = 0.80,
    model_ndcg_12: Optional[float] = 0.85,
    market_ndcg_12: Optional[float] = 0.80,
    *,
    idx: int = 1,
    test_year: int = 2020,
    train_years: Optional[list[int]] = None,
    spear: float = 0.60,
    r2: Optional[float] = None,
    ci: tuple[float, float] = (0.50, 0.70),
    null_coverage: Optional[float] = None,
) -> FoldResult:
    kwargs = dict(
        fold_index=idx,
        train_years=[2018] if train_years is None else train_years,
        test_year=test_year,
        outcome_seasons=[test_year + 1, test_year + 2],
        n_train=100,
        n_test=50,
        kendall_tau=tau,
        kendall_tau_bca_ci95=(tau_ci_low, tau + 0.1),
        spearman_rho=spear,
        spearman_rho_bca_ci95=ci,
        rank_ic=spear,
        rmse=3.5,
        mae=2.8,
        r2_oos=r2,
        ndcg_at_12_model=model_ndcg_12,
        ndcg_at_12_market=market_ndcg_12,
        ndcg_at_24_model=model_ndcg,
        ndcg_at_24_market=market_ndcg,
    )
    if null_coverage is not None:
        kwargs["null_coverage"] = null_coverage
    return FoldResult(**kwargs)


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
