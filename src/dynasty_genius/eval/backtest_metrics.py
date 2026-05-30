"""Pure statistical functions for the Engine B walk-forward backtest harness.

All functions are side-effect-free — no I/O, no model calls.

Reference: Harvey, Leybourne & Newbold (1997) for HLN-corrected DM test.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import stats as scipy_stats

from src.dynasty_genius.eval.backtest_artifact import TopKResult

# ── R² (coefficient of determination) ─────────────────────────────────────────


def compute_r2(y_true, y_pred) -> Optional[float]:
    """OOS coefficient of determination ``1 - SS_res/SS_tot``.

    Fail-closed → ``None``: zero-variance truth (``SS_tot == 0``); any non-finite
    value (NaN/inf) in either array (data corruption). Raises ``ValueError`` on
    API-misuse (length mismatch / empty input). Negative R² is valid and returned
    as-is (a model worse than predicting the mean).
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.shape != yp.shape:
        raise ValueError("compute_r2: y_true and y_pred must have equal length")
    if yt.size == 0:
        raise ValueError("compute_r2: empty input")
    if not (np.isfinite(yt).all() and np.isfinite(yp).all()):
        return None
    with np.errstate(over="ignore", invalid="ignore"):
        ss_tot = float(np.sum((yt - yt.mean()) ** 2))
        ss_res = float(np.sum((yt - yp) ** 2))
    if not (math.isfinite(ss_tot) and math.isfinite(ss_res)):
        return None  # finite inputs overflowed the squared sums → fail closed
    if ss_tot == 0.0:
        return None
    r2 = 1.0 - ss_res / ss_tot
    return r2 if math.isfinite(r2) else None


# ── Rank Correlation ──────────────────────────────────────────────────────────

def compute_rank_correlation(
    predicted: list[float],
    realized: list[float],
    n_bootstrap: int = 1000,
    rng_seed: int = 42,
) -> tuple[float, tuple[float, float], float, tuple[float, float]]:
    """Kendall τ-b and Spearman ρ with BCa bootstrap CIs.

    Returns (kendall_tau, kendall_bca_ci95, spearman_rho, spearman_bca_ci95).
    Returns all-nan if len(predicted) < 10.
    """
    _nan = (float("nan"), (float("nan"), float("nan")))
    if len(predicted) < 10:
        return (float("nan"), (float("nan"), float("nan")),
                float("nan"), (float("nan"), float("nan")))

    x = np.array(predicted, dtype=float)
    y = np.array(realized, dtype=float)

    tau = float(scipy_stats.kendalltau(x, y, variant="b").statistic)
    rho = float(scipy_stats.spearmanr(x, y).statistic)

    def _kendall_stat(a, b):
        return scipy_stats.kendalltau(a, b, variant="b").statistic

    def _spearman_stat(a, b):
        return scipy_stats.spearmanr(a, b).statistic

    tau_ci = _bca_ci((x, y), _kendall_stat, n_bootstrap, rng_seed)
    rho_ci = _bca_ci((x, y), _spearman_stat, n_bootstrap, rng_seed)

    return tau, tau_ci, rho, rho_ci


def _bca_ci(
    data: tuple,
    statistic,
    n_resamples: int,
    rng_seed: int,
) -> tuple[float, float]:
    """BCa bootstrap CI for a paired statistic. Returns (lo, hi)."""
    try:
        result = scipy_stats.bootstrap(
            data,
            statistic,
            n_resamples=n_resamples,
            random_state=rng_seed,
            method="BCa",
            paired=True,
            confidence_level=0.95,
        )
        lo = float(result.confidence_interval.low)
        hi = float(result.confidence_interval.high)
        # Clamp to valid correlation range
        lo = max(-1.0, lo)
        hi = min(1.0, hi)
        return (lo, hi)
    except Exception:
        # Degenerate distribution (e.g., perfect correlation) — CI collapses
        point = float(statistic(*data))
        return (point, point)


# ── NDCG ─────────────────────────────────────────────────────────────────────

def compute_ndcg(
    predicted_ranks: list[int],
    realized_ppg: list[float],
    k: int,
) -> float:
    """NDCG@k. Realized PPG is the graded relevance score.

    DCG  = sum(ppg[i] / log2(rank[i] + 1)) for players with rank <= k.
    IDCG = DCG of the ideal (perfect) ranking.
    Returns 0.0 if k > len(predicted_ranks).
    """
    n = len(predicted_ranks)
    if k > n:
        return 0.0

    ppg = np.array(realized_ppg, dtype=float)
    ranks = np.array(predicted_ranks, dtype=int)

    # DCG: sum contributions of all players ranked within top k
    mask = ranks <= k
    dcg = float(np.sum(ppg[mask] / np.log2(ranks[mask] + 1)))

    # IDCG: ideal ordering — sort PPG descending, assign ranks 1..min(k,n)
    ideal_ppg = np.sort(ppg)[::-1][:k]
    ideal_ranks = np.arange(1, len(ideal_ppg) + 1)
    idcg = float(np.sum(ideal_ppg / np.log2(ideal_ranks + 1)))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ── Precision@k ───────────────────────────────────────────────────────────────

def compute_precision_at_k(
    model_top_k: set[str],
    market_top_k: set[str],
    realized_top_k: set[str],
    k: int,
) -> TopKResult:
    """Hit rates for model and market vs. realized top-k, with Wilson CI on difference.

    Uses the Newcombe (1998) hybrid score method for the CI of the difference.
    """
    model_hits = len(model_top_k & realized_top_k)
    market_hits = len(market_top_k & realized_top_k)

    p1 = model_hits / k
    p2 = market_hits / k

    # Wilson CIs for each proportion
    lo1, hi1 = _wilson_ci(model_hits, k)
    lo2, hi2 = _wilson_ci(market_hits, k)

    # Newcombe method for CI of (p1 - p2)
    diff = p1 - p2
    margin_lo = math.sqrt((p1 - lo1) ** 2 + (hi2 - p2) ** 2)
    margin_hi = math.sqrt((hi1 - p1) ** 2 + (p2 - lo2) ** 2)
    ci_lo = max(-1.0, diff - margin_lo)
    ci_hi = min(1.0, diff + margin_hi)

    return TopKResult(
        k=k,
        model_hit_rate=p1,
        market_hit_rate=p2,
        diff_wilson_ci95=(ci_lo, ci_hi),
    )


def _wilson_ci(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 1.0)
    from scipy.stats import norm
    z = norm.ppf(1 - alpha / 2)
    p_hat = successes / n
    denom = 1 + z ** 2 / n
    centre = (p_hat + z ** 2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


# ── Calibration + Subgroup Metrics ───────────────────────────────────────────

def compute_ece(
    calibration_deciles: list[tuple[float, float, int]],
) -> float:
    """Expected Calibration Error across prediction deciles.

    Each tuple is (predicted_mean, observed_mean, n). Returns nan when there
    are no deciles or the total row count is zero.
    """
    total_n = sum(n for _, _, n in calibration_deciles)
    if total_n == 0:
        return float("nan")

    weighted_abs_error = sum(
        n * abs(float(predicted_mean) - float(observed_mean))
        for predicted_mean, observed_mean, n in calibration_deciles
    )
    return float(weighted_abs_error / total_n)


def compute_subgroup_metrics(
    predicted: list[float],
    realized: list[float],
) -> dict[str, Optional[float] | int]:
    """Rank and error metrics for a subgroup slice.

    Returns all metric values as None when n < 5 because correlations are too
    unstable for Trust Surface diagnostics at that cohort size.
    """
    n = len(predicted)
    if n < 5:
        return {
            "kendall_tau": None,
            "spearman_rho": None,
            "rmse": None,
            "n": n,
        }

    x = np.array(predicted, dtype=float)
    y = np.array(realized, dtype=float)
    residuals = x - y

    return {
        "kendall_tau": float(scipy_stats.kendalltau(x, y, variant="b").statistic),
        "spearman_rho": float(scipy_stats.spearmanr(x, y).statistic),
        "rmse": float(np.sqrt(np.mean(residuals ** 2))),
        "n": n,
    }


# ── HLN-Corrected Diebold-Mariano ─────────────────────────────────────────────

def diebold_mariano_hln(
    model_errors: list[float],
    naive_errors: list[float],
) -> tuple[float, float]:
    """HLN-corrected Diebold-Mariano test (Harvey, Leybourne & Newbold 1997).

    model_errors and naive_errors are squared errors: (y_hat - y)^2.
    Loss differential: d_t = model_error_t - naive_error_t.
    Naive baseline: prior-season PPG.

    For h=1 (1-step-ahead), the HLN correction is algebraically equivalent to
    scipy.stats.ttest_1samp(d, 0), which divides by the Bessel-corrected std
    and uses t(T-1). Both are equivalent to multiplying the DM variance by
    (T-1)/T and using t(T-1) instead of N(0,1).

    Returns (dm_statistic, p_value), two-sided.
    Returns (nan, nan) if T < 4.
    """
    T = len(model_errors)
    if T < 4:
        return (float("nan"), float("nan"))

    d = np.array(model_errors, dtype=float) - np.array(naive_errors, dtype=float)
    if d.std(ddof=1) == 0.0:
        # All differentials are identical — model and naive indistinguishable
        return (0.0, 1.0)
    stat, pvalue = scipy_stats.ttest_1samp(d, 0.0)
    return (float(stat), float(pvalue))
