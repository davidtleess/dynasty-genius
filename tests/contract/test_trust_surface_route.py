from datetime import datetime, timedelta, timezone
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

client = TestClient(app)

@pytest.fixture
def mock_runs_dir(tmp_path):
    """Create a temporary directory for backtest runs."""
    runs_dir = tmp_path / "app/data/backtest/runs"
    runs_dir.mkdir(parents=True)
    return runs_dir

def create_fake_artifact(position: str, run_date: datetime) -> BacktestResult:
    """Create a valid BacktestResult for testing."""
    return BacktestResult(
        run_id=uuid4(),
        run_date=run_date,
        model_version="engine_b_v2",
        model_artifact_hash="abc123hash",
        position=position,
        ridge_alpha=500.0,
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
            g1_rank_correlation_pass=True,
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade="ACTIVE_B",
            promotion_justification="Test justification",
        )
    )

def test_get_trust_surface_404_no_runs_at_all():
    """Returns 404 when the runs directory is empty or missing."""
    with patch("app.api.routes.trust_surface.RUNS_DIR", Path("/tmp/nonexistent_runs")):
        response = client.get("/api/trust-surface/WR")
        assert response.status_code == 404
        assert "No backtest artifact found for position WR" in response.json()["detail"]

def test_get_trust_surface_404_position_not_found(mock_runs_dir):
    """Returns 404 when artifacts exist but not for the requested position."""
    # Create an artifact for QB
    qb_run_dir = mock_runs_dir / str(uuid4())
    qb_art = create_fake_artifact("QB", datetime.now(timezone.utc))
    qb_art.save(qb_run_dir)
    
    with patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir):
        response = client.get("/api/trust-surface/WR")
        assert response.status_code == 404
        assert "No backtest artifact found for position WR" in response.json()["detail"]

def test_get_trust_surface_200_latest_returned(mock_runs_dir):
    """Returns the most recent artifact when multiple runs exist for a position."""
    pos = "WR"
    now = datetime.now(timezone.utc)
    
    # Create an older run
    old_art = create_fake_artifact(pos, now - timedelta(days=1))
    old_run_dir = mock_runs_dir / str(old_art.run_id)
    old_art.save(old_run_dir)
    
    # Create a newer run
    new_art = create_fake_artifact(pos, now)
    new_run_dir = mock_runs_dir / str(new_art.run_id)
    new_art.save(new_run_dir)
    
    with patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir):
        response = client.get(f"/api/trust-surface/{pos}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(new_art.run_id)
        assert data["position"] == pos
        assert data["promotion_gate"]["overall_grade"] == "ACTIVE_B"

def test_get_trust_surface_invalid_position():
    """Returns 404 or validation error for non-existent position literal."""
    # Since position is Literal in BacktestResult, but the path param is a string.
    # The route should handle invalid positions gracefully.
    response = client.get("/api/trust-surface/K")
    assert response.status_code == 404


def test_get_trust_surface_overall_grade_at_top_level(mock_runs_dir):
    """overall_grade is hoisted to the response top level for consumer convenience."""
    art = create_fake_artifact("RB", datetime.now(timezone.utc))
    art.save(mock_runs_dir / str(art.run_id))

    with patch("app.api.routes.trust_surface.RUNS_DIR", mock_runs_dir):
        response = client.get("/api/trust-surface/RB")
        assert response.status_code == 200
        data = response.json()
        assert "overall_grade" in data, "overall_grade must be at response top level"
        assert data["overall_grade"] == art.promotion_gate.overall_grade
