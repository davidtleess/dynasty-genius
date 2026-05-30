"""Harness Trust Completion W3.2 RED: R2 fields propagate through folds."""

from __future__ import annotations

from src.dynasty_genius.eval.backtest_artifact import FoldResult
from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver


def _fold_result(**overrides: object) -> FoldResult:
    data: dict[str, object] = {
        "fold_index": 1,
        "train_years": [2018, 2019],
        "test_year": 2020,
        "outcome_seasons": [2021, 2022],
        "n_train": 10,
        "n_test": 5,
        "kendall_tau": 0.25,
        "kendall_tau_bca_ci95": (0.1, 0.4),
        "spearman_rho": 0.3,
        "spearman_rho_bca_ci95": (0.05, 0.5),
        "rank_ic": 0.3,
        "rmse": 1.25,
        "mae": 0.9,
    }
    data.update(overrides)
    return FoldResult(**data)


def test_foldresult_has_r2_oos_and_metric_caveats_with_safe_defaults() -> None:
    fold = _fold_result()

    assert fold.r2_oos is None
    assert fold.metric_caveats == []


def test_foldresult_accepts_negative_r2_and_caveat_tokens() -> None:
    fold = _fold_result(
        r2_oos=-0.208,
        metric_caveats=["r2_oos_small_sample"],
    )

    assert fold.r2_oos == -0.208
    assert fold.metric_caveats == ["r2_oos_small_sample"]


def test_run_populates_r2_oos_and_metric_caveats_on_each_qb_fold() -> None:
    result = WalkForwardDriver(position="QB").run()

    assert len(result.folds) == 4
    assert [fold.n_test for fold in result.folds] == [43, 46, 46, 49]
    for fold in result.folds:
        assert fold.r2_oos is None or isinstance(fold.r2_oos, float)
        assert isinstance(fold.metric_caveats, list)
    assert any(
        "r2_oos_small_sample" in fold.metric_caveats
        or "r2_oos_unavailable" in fold.metric_caveats
        for fold in result.folds
    )
