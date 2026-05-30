"""Harness Trust Completion W1.1 RED: paired BCa NDCG-diff bootstrap."""

from __future__ import annotations

import pytest

from src.dynasty_genius.eval import backtest_metrics as metrics


def _adequate_args() -> tuple[list[int], list[int], list[float]]:
    model_ranks = list(range(1, 31))
    market_ranks = list(range(30, 0, -1))
    realized = [float(31 - i) for i in range(1, 31)]
    return model_ranks, market_ranks, realized


def test_bootstrap_returns_point_diff_ci_and_pool_n_on_adequate_pool() -> None:
    model_ranks, market_ranks, realized = _adequate_args()

    out = metrics.compute_ndcg_diff_bootstrap(
        model_ranks,
        market_ranks,
        realized,
        k=24,
        n_bootstrap=200,
        rng_seed=12345,
    )

    assert out["pool_n"] == 30
    assert out["method"] == "bca_bootstrap"
    assert out["caveat"] is None
    assert isinstance(out["ndcg_diff"], float)
    lo, hi = out["ndcg_diff_bca_ci95"]
    assert lo <= out["ndcg_diff"] <= hi


def test_bootstrap_fails_closed_on_pool_below_threshold() -> None:
    out = metrics.compute_ndcg_diff_bootstrap(
        [1, 2, 3],
        [3, 2, 1],
        [3.0, 2.0, 1.0],
        k=24,
        n_bootstrap=200,
        rng_seed=12345,
    )

    assert out["ndcg_diff"] is None
    assert out["ndcg_diff_bca_ci95"] is None
    assert out["pool_n"] == 3
    assert out["method"] == "bca_bootstrap"
    assert out["caveat"] == "insufficient_pool_for_bootstrap"


def test_bootstrap_is_deterministic_under_fixed_seed() -> None:
    args = _adequate_args()

    a = metrics.compute_ndcg_diff_bootstrap(
        *args,
        k=24,
        n_bootstrap=200,
        rng_seed=7,
    )
    b = metrics.compute_ndcg_diff_bootstrap(
        *args,
        k=24,
        n_bootstrap=200,
        rng_seed=7,
    )

    assert a == b


def test_bootstrap_fails_closed_when_k_exceeds_pool_even_if_min_pool_is_met() -> None:
    n = 12

    out = metrics.compute_ndcg_diff_bootstrap(
        list(range(1, n + 1)),
        list(range(n, 0, -1)),
        [float(n + 1 - i) for i in range(1, n + 1)],
        k=24,
        n_bootstrap=200,
        rng_seed=12345,
        min_pool=10,
    )

    assert out["ndcg_diff"] is None
    assert out["ndcg_diff_bca_ci95"] is None
    assert out["pool_n"] == n
    assert out["caveat"] == "insufficient_pool_for_bootstrap"


def test_bootstrap_collapses_ci_to_point_on_perfect_model_market_agreement() -> None:
    ranks = list(range(1, 31))
    realized = [float(31 - i) for i in range(1, 31)]

    out = metrics.compute_ndcg_diff_bootstrap(
        ranks,
        ranks,
        realized,
        k=24,
        n_bootstrap=200,
        rng_seed=12345,
    )

    assert out["ndcg_diff"] == pytest.approx(0.0, abs=1e-12)
    assert out["ndcg_diff_bca_ci95"] == pytest.approx((0.0, 0.0), abs=1e-12)
    assert out["method"] == "bca_bootstrap"
    assert out["caveat"] is None


def test_bootstrap_fails_closed_on_nonfinite_relevance() -> None:
    model_ranks, market_ranks, realized = _adequate_args()
    realized[5] = float("nan")

    out = metrics.compute_ndcg_diff_bootstrap(
        model_ranks,
        market_ranks,
        realized,
        k=24,
        n_bootstrap=200,
        rng_seed=12345,
    )

    assert out["ndcg_diff"] is None
    assert out["ndcg_diff_bca_ci95"] is None
    assert out["pool_n"] == 30
    assert out["method"] == "bca_bootstrap"
    assert out["caveat"] == "nonfinite_input_for_bootstrap"


def test_bootstrap_raises_on_length_mismatch() -> None:
    with pytest.raises(ValueError, match="equal length"):
        metrics.compute_ndcg_diff_bootstrap(
            [1, 2, 3],
            [1, 2],
            [3.0, 2.0, 1.0],
            k=2,
        )


def test_bootstrap_fails_closed_on_invalid_rank_domain() -> None:
    # Codex W1.1 finding: rank <= 0 → compute_ndcg divides by log2(rank+1)=log2(1)=0
    # → a non-finite metric must NOT pass as a valid G3 disclosure. Fail closed.
    _, market_ranks, realized = _adequate_args()
    zero_rank = [0] + list(range(2, 31))          # rank 0 present
    out = metrics.compute_ndcg_diff_bootstrap(
        zero_rank, market_ranks, realized, k=24, n_bootstrap=200, rng_seed=12345,
    )
    assert out["ndcg_diff"] is None
    assert out["ndcg_diff_bca_ci95"] is None
    assert out["caveat"] == "invalid_rank_domain"

    neg_rank = [-1] + list(range(2, 31))          # negative rank present
    out2 = metrics.compute_ndcg_diff_bootstrap(
        neg_rank, market_ranks, realized, k=24, n_bootstrap=200, rng_seed=12345,
    )
    assert out2["ndcg_diff"] is None
    assert out2["caveat"] == "invalid_rank_domain"


def test_bootstrap_raises_on_nonpositive_k() -> None:
    # Codex W1.1 finding: k <= 0 is caller-contract misuse (NDCG@0 is meaningless) → raise.
    model_ranks, market_ranks, realized = _adequate_args()
    with pytest.raises(ValueError, match="k"):
        metrics.compute_ndcg_diff_bootstrap(model_ranks, market_ranks, realized, k=0)


def test_bootstrap_raises_on_nonpositive_n_bootstrap() -> None:
    # Codex W1.1 finding: n_bootstrap <= 0 means no bootstrap ran → 'bca_bootstrap' would
    # be misleading → raise.
    model_ranks, market_ranks, realized = _adequate_args()
    with pytest.raises(ValueError, match="n_bootstrap"):
        metrics.compute_ndcg_diff_bootstrap(
            model_ranks, market_ranks, realized, k=24, n_bootstrap=0,
        )
