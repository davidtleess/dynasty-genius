from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    GateResult,
    StabilityResult,
)
from src.dynasty_genius.eval.model_card import ModelCard, ModelCardMetrics


client = TestClient(app)


@pytest.fixture
def mock_runs_dir(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return runs_dir


@pytest.fixture
def mock_cards_dir(tmp_path):
    cards_dir = tmp_path / "model_cards"
    cards_dir.mkdir()
    return cards_dir


def _backtest_result(position: str, overall_grade: str = "ACTIVE_B") -> BacktestResult:
    return BacktestResult(
        run_id=uuid4(),
        run_date=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="abc123hash",
        position=position,  # type: ignore[arg-type]
        ridge_alpha=200.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=[],
        rmse_stability=StabilityResult(
            rmse_per_fold=[],
            rmse_mean=0.0,
            rmse_cv=0.0,
            rmse_max_deviation_pct=0.0,
        ),
        market_source="unavailable",
        promotion_gate=GateResult(
            g1_rank_correlation_pass=(overall_grade != "EXPERIMENTAL"),
            g2_rmse_stability_pass=(overall_grade != "EXPERIMENTAL"),
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade=overall_grade,
            promotion_justification="test fixture",
        ),
    )


def _write_backtest_result(runs_dir: Path, position: str, overall_grade: str = "ACTIVE_B") -> BacktestResult:
    result = _backtest_result(position, overall_grade)
    result.save(runs_dir / str(result.run_id))
    return result


def _model_card(position: str = "WR", is_experimental: bool = False) -> ModelCard:
    return ModelCard(
        generated_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        position=position,  # type: ignore[arg-type]
        backtest_run_id=str(uuid4()),
        git_sha=None,
        model_version="engine_b_v2",
        model_artifact_hash="abc123hash",
        ridge_alpha=200.0,
        training_window="2018-2023 (expanding; 4 folds)",
        feature_list=["age_at_feature_season", "prior_ppg"],
        retrain_mode="refit_per_fold_fixed_alpha",
        intended_use="Forecast 2-year average PPG for dynasty decisions.",
        out_of_scope_uses=["Single-season start/sit decisions"],
        relevant_factors=["position", "age", "sample_size", "draft_capital"],
        evaluation_factors=["age_bucket", "draft_round_bucket"],
        metrics=ModelCardMetrics(
            rmse_mean=3.0,
            rmse_per_fold=[3.0, 3.1, 2.9, 3.0],
            kendall_tau_mean=0.45,
            kendall_tau_per_fold=[0.4, 0.45, 0.5, 0.45],
            spearman_rho_mean=0.55,
            spearman_rho_per_fold=[0.5, 0.55, 0.6, 0.55],
            ece=None,
            ndcg_at_24_model_mean=None,
            ndcg_at_24_market_mean=None,
            g1_pass=True,
            g2_pass=True,
            g3_pass="deferred",
            g4_pass="deferred",
            overall_grade="ACTIVE_B",
        ),
        evaluation_data="4 expanding folds.",
        training_data="app/data/training/engine_b_features_v2.csv",
        subgroup_results=[],
        ethical_considerations="Decision aid only.",
        caveats=["Market data is an overlay only."],
        known_failure_modes=["Injury-year outliers can distort PPG labels."],
        is_experimental=is_experimental,
    )


def test_get_trust_surface_includes_experimental_flag_false_for_wr(mock_runs_dir, mock_cards_dir):
    """`experimental` is False for non-TE positions that pass G1+G2."""
    _write_backtest_result(mock_runs_dir, "WR", "ACTIVE_B")

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True),
    ):
        response = client.get("/api/trust-surface/WR")

    assert response.status_code == 200
    assert response.json()["experimental"] is False


def test_get_trust_surface_includes_experimental_flag_true_for_te(mock_runs_dir, mock_cards_dir):
    """`experimental` is True when overall_grade == "EXPERIMENTAL"."""
    _write_backtest_result(mock_runs_dir, "TE", "EXPERIMENTAL")

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True),
    ):
        response = client.get("/api/trust-surface/TE")

    assert response.status_code == 200
    assert response.json()["experimental"] is True


def test_get_trust_surface_includes_model_card_available_false_when_no_card(mock_runs_dir, mock_cards_dir):
    """`model_card_available` is False when no card file exists."""
    _write_backtest_result(mock_runs_dir, "WR", "ACTIVE_B")

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True),
    ):
        response = client.get("/api/trust-surface/WR")

    assert response.status_code == 200
    assert response.json()["model_card_available"] is False


def test_get_trust_surface_includes_model_card_available_true_when_card_exists(mock_runs_dir, mock_cards_dir):
    """`model_card_available` is True when the card file exists."""
    _write_backtest_result(mock_runs_dir, "WR", "ACTIVE_B")
    _model_card("WR").save(mock_cards_dir / "WR_model_card.json")

    with (
        patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir),
        patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True),
    ):
        response = client.get("/api/trust-surface/WR")

    assert response.status_code == 200
    assert response.json()["model_card_available"] is True


def test_get_model_card_404_when_no_card(mock_cards_dir):
    """`GET /trust-surface/WR/model-card` returns 404 when no card."""
    with patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True):
        response = client.get("/api/trust-surface/WR/model-card")

    assert response.status_code == 404
    assert "No model card found for position WR" in response.json()["detail"]


def test_get_model_card_200_returns_valid_model_card(mock_cards_dir):
    """Returns 200 with all 9 ModelCard sections in response."""
    _model_card("WR").save(mock_cards_dir / "WR_model_card.json")

    with patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True):
        response = client.get("/api/trust-surface/WR/model-card")

    assert response.status_code == 200
    data = response.json()
    assert data["position"] == "WR"
    for key in [
        "model_version",
        "intended_use",
        "relevant_factors",
        "metrics",
        "evaluation_data",
        "training_data",
        "subgroup_results",
        "ethical_considerations",
        "caveats",
        "known_failure_modes",
    ]:
        assert key in data


def test_get_model_card_is_experimental_at_top_level(mock_cards_dir):
    """`is_experimental` is present at top level of response."""
    _model_card("TE", is_experimental=True).save(mock_cards_dir / "TE_model_card.json")

    with patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True):
        response = client.get("/api/trust-surface/TE/model-card")

    assert response.status_code == 200
    assert response.json()["is_experimental"] is True


def test_get_model_card_invalid_position_404(mock_cards_dir):
    """Unknown position (e.g., K) returns 404."""
    with patch("app.api.routes.trust_surface.MODEL_CARDS_DIR", mock_cards_dir, create=True):
        response = client.get("/api/trust-surface/K/model-card")

    assert response.status_code == 404
