"""Harness Trust Completion W3.3 RED: nullable OOS R2 in model cards."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from scripts.generate_model_cards import generate_card_for_position
from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)
from src.dynasty_genius.eval.model_card import ModelCardMetrics


def _metrics(**overrides: object) -> ModelCardMetrics:
    data: dict[str, object] = {
        "rmse_mean": 3.2,
        "rmse_per_fold": [3.0, 3.1, 3.3, 3.4],
        "kendall_tau_mean": 0.72,
        "kendall_tau_per_fold": [0.70, 0.71, 0.73, 0.74],
        "spearman_rho_mean": 0.81,
        "spearman_rho_per_fold": [0.80, 0.80, 0.82, 0.82],
        "g1_pass": True,
        "g2_pass": True,
        "g3_pass": "deferred",
        "g4_pass": "deferred",
        "overall_grade": "ACTIVE_B",
    }
    data.update(overrides)
    return ModelCardMetrics(**data)


def _fold(fold_index: int, r2_oos: float | None) -> FoldResult:
    return FoldResult(
        fold_index=fold_index,
        train_years=[2018, 2019],
        test_year=2019 + fold_index,
        outcome_seasons=[2020 + fold_index, 2021 + fold_index],
        n_train=100,
        n_test=50,
        kendall_tau=0.4,
        kendall_tau_bca_ci95=(0.2, 0.6),
        spearman_rho=0.5,
        spearman_rho_bca_ci95=(0.3, 0.7),
        rank_ic=0.5,
        rmse=3.0,
        mae=2.0,
        r2_oos=r2_oos,
    )


def _write_backtest_result(tmp_path, r2_values: list[float | None]) -> None:
    folds = [_fold(idx + 1, r2_oos) for idx, r2_oos in enumerate(r2_values)]
    run_id = uuid4()
    result = BacktestResult(
        run_id=run_id,
        run_date=datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="deadbeef" * 8,
        position="QB",
        ridge_alpha=200.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=folds,
        rmse_stability=StabilityResult(
            rmse_per_fold=[fold.rmse for fold in folds],
            rmse_mean=3.0,
            rmse_cv=0.0,
            rmse_max_deviation_pct=0.0,
        ),
        market_source="unavailable",
        promotion_gate=GateResult(
            g1_rank_correlation_pass=True,
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade="ACTIVE_B",
            promotion_justification="contract fixture",
        ),
    )
    result.save(tmp_path / "runs" / str(run_id))


def test_model_card_metrics_defaults_nullable_r2_fields_when_absent() -> None:
    metrics = _metrics()

    assert metrics.r2_oos_mean is None
    assert metrics.r2_oos_per_fold == []


def test_model_card_metrics_accepts_null_and_negative_r2_per_fold() -> None:
    metrics = _metrics(
        r2_oos_mean=-0.05,
        r2_oos_per_fold=[0.1, None, -0.2, None],
    )

    assert metrics.r2_oos_mean == -0.05
    assert metrics.r2_oos_per_fold == [0.1, None, -0.2, None]


def test_generate_model_card_averages_non_null_r2_folds(tmp_path) -> None:
    _write_backtest_result(tmp_path, [0.1, None, -0.2, None])

    card, _ = generate_card_for_position(
        "QB",
        runs_dir=tmp_path / "runs",
        output_dir=tmp_path / "cards",
    )

    assert card.metrics.r2_oos_per_fold == [0.1, None, -0.2, None]
    assert card.metrics.r2_oos_mean == pytest.approx(-0.05, abs=1e-12)


def test_generate_model_card_keeps_r2_mean_null_when_all_folds_null(tmp_path) -> None:
    _write_backtest_result(tmp_path, [None, None, None, None])

    card, _ = generate_card_for_position(
        "QB",
        runs_dir=tmp_path / "runs",
        output_dir=tmp_path / "cards",
    )

    assert card.metrics.r2_oos_per_fold == [None, None, None, None]
    assert card.metrics.r2_oos_mean is None
