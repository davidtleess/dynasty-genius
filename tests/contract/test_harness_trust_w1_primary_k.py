"""Harness Trust Completion W1.2 RED: primary-k policy + FoldResult destinations."""

from __future__ import annotations

import numpy as np

from src.dynasty_genius.eval import backtest_harness as bh
from src.dynasty_genius.eval.backtest_artifact import FoldResult


def _fold_result(**overrides: object) -> FoldResult:
    data: dict[str, object] = {
        "fold_index": 1,
        "train_years": [2018, 2019],
        "test_year": 2020,
        "outcome_seasons": [2021, 2022],
        "n_train": 100,
        "n_test": 50,
        "kendall_tau": 0.4,
        "kendall_tau_bca_ci95": (0.2, 0.6),
        "spearman_rho": 0.5,
        "spearman_rho_bca_ci95": (0.3, 0.7),
        "rank_ic": 0.5,
        "rmse": 3.0,
        "mae": 2.0,
    }
    data.update(overrides)
    return FoldResult(**data)


def _market_rows(n: int, position: str = "WR") -> list[dict]:
    return [
        {
            "snapshot_date": "2021-09-08",
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": float(n - i),
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": position,
            "trend_30day": 0.0,
            "source": "fc_native",
            "inserted_at": "2026-05-30T00:00:00+00:00",
        }
        for i in range(n)
    ]


def test_primary_ndcg_k_policy_is_position_aware() -> None:
    assert bh.PRIMARY_NDCG_K == {"QB": 12, "RB": 24, "WR": 24, "TE": 12}


def test_foldresult_defaults_bootstrap_destinations_to_none() -> None:
    fold = _fold_result()

    assert fold.primary_k is None
    assert fold.market_pool_n is None
    assert fold.ndcg_diff_primary_k is None
    assert fold.ndcg_diff_bca_ci95 is None


def test_foldresult_accepts_bootstrap_destination_values() -> None:
    fold = _fold_result(
        primary_k=12,
        market_pool_n=30,
        ndcg_diff_primary_k=0.125,
        ndcg_diff_bca_ci95=(-0.05, 0.25),
    )

    assert fold.primary_k == 12
    assert fold.market_pool_n == 30
    assert fold.ndcg_diff_primary_k == 0.125
    assert fold.ndcg_diff_bca_ci95 == (-0.05, 0.25)


def test_compute_market_ndcg_pool_below_24_keeps_24_null() -> None:
    n = 15
    rng = np.random.default_rng(123)
    result = bh._compute_market_ndcg(
        y_pred=rng.random(n),
        player_ids=[f"gsis_{i}" for i in range(n)],
        y_realized=rng.random(n),
        market_rows=_market_rows(n),
        id_map={f"gsis_{i}": f"slp_{i}" for i in range(n)},
    )

    assert result["ndcg_at_12_model"] is not None
    assert result["ndcg_at_12_market"] is not None
    assert result["ndcg_at_24_model"] is None
    assert result["ndcg_at_24_market"] is None
