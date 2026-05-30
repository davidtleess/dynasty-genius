"""Harness Trust Completion W4.1 RED: QB-only reliability stamp."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)

client = TestClient(app)

BANNED_RELIABILITY_WORDS = re.compile(
    r"\b(buy|sell|hold|start|drop|verdict|tier|grade)\b",
    re.IGNORECASE,
)


def _fold(*, r2_oos: float | None, spearman_rho: float) -> FoldResult:
    return FoldResult(
        fold_index=1,
        train_years=[2018, 2019],
        test_year=2020,
        outcome_seasons=[2021, 2022],
        n_train=100,
        n_test=50,
        kendall_tau=0.40,
        kendall_tau_bca_ci95=(0.25, 0.55),
        spearman_rho=spearman_rho,
        spearman_rho_bca_ci95=(0.30, 0.70),
        rank_ic=spearman_rho,
        rmse=3.0,
        mae=2.5,
        r2_oos=r2_oos,
    )


def _result(position: str, folds: list[FoldResult]) -> BacktestResult:
    return BacktestResult(
        run_id=uuid4(),
        run_date=datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="abc123hash",
        position=position,  # type: ignore[arg-type]
        ridge_alpha=1000.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=folds,
        rmse_stability=StabilityResult(
            rmse_per_fold=[3.0 for _ in folds],
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
            promotion_justification="test fixture",
        ),
    )


def _write_result(runs_dir: Path, result: BacktestResult) -> None:
    result.save(runs_dir / str(result.run_id))


def test_qb_trust_surface_includes_model_reliability_from_folds(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    cards_dir = tmp_path / "cards"
    runs_dir.mkdir()
    cards_dir.mkdir()
    _write_result(
        runs_dir,
        _result(
            "QB",
            [
                _fold(r2_oos=0.10, spearman_rho=0.40),
                _fold(r2_oos=None, spearman_rho=0.50),
                _fold(r2_oos=-0.20, spearman_rho=0.60),
                _fold(r2_oos=0.00, spearman_rho=0.70),
            ],
        ),
    )

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", cards_dir),
    ):
        response = client.get("/api/trust-surface/QB")

    assert response.status_code == 200
    reliability = response.json()["model_reliability"]
    assert reliability["position"] == "QB"
    assert reliability["r2_oos_mean"] == -0.03333333333333333
    assert reliability["spearman_rho_mean"] == 0.55
    assert isinstance(reliability["caveat"], str)
    assert not BANNED_RELIABILITY_WORDS.search(reliability["caveat"])


def test_qb_reliability_handles_all_null_r2_without_crashing(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    cards_dir = tmp_path / "cards"
    runs_dir.mkdir()
    cards_dir.mkdir()
    _write_result(
        runs_dir,
        _result(
            "QB",
            [
                _fold(r2_oos=None, spearman_rho=0.40),
                _fold(r2_oos=None, spearman_rho=0.50),
            ],
        ),
    )

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", cards_dir),
    ):
        response = client.get("/api/trust-surface/QB")

    assert response.status_code == 200
    reliability = response.json()["model_reliability"]
    assert reliability["r2_oos_mean"] is None
    assert reliability["spearman_rho_mean"] == 0.45
    assert "n/a" in reliability["caveat"].lower()
    assert not BANNED_RELIABILITY_WORDS.search(reliability["caveat"])


def test_non_qb_trust_surface_does_not_include_model_reliability(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    cards_dir = tmp_path / "cards"
    runs_dir.mkdir()
    cards_dir.mkdir()
    _write_result(
        runs_dir,
        _result(
            "RB",
            [
                _fold(r2_oos=0.20, spearman_rho=0.55),
                _fold(r2_oos=0.10, spearman_rho=0.45),
            ],
        ),
    )

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", cards_dir),
    ):
        response = client.get("/api/trust-surface/RB")

    assert response.status_code == 200
    assert "model_reliability" not in response.json()


def test_reliability_banned_language_scan_uses_word_boundaries() -> None:
    assert not BANNED_RELIABILITY_WORDS.search("upgrade path is descriptive")
    assert BANNED_RELIABILITY_WORDS.search("grade")
