from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from tests.contract.test_trust_publication_audit import (
    POSITIONS,
    _write_model_card_sources,
    _write_publication,
)

client = TestClient(app)

PUBLIC_MODEL_CARD_FIELDS = {
    "position",
    "backtest_run_id",
    "generated_at",
    "is_experimental",
    "intended_use",
    "out_of_scope_uses",
    "caveats",
    "known_failure_modes",
}

FORBIDDEN_PUBLIC_KEYS = {
    "model_version",
    "model_artifact_hash",
    "git_sha",
    "metrics",
    "feature_list",
    "relevant_factors",
    "evaluation_factors",
    "evaluation_data",
    "training_data",
    "subgroup_results",
    "calibration",
    "ethical_considerations",
}


def _published_root(tmp_path: Path, *, with_sources: bool = True) -> Path:
    root = tmp_path / "trust_surface" / "latest"
    _write_publication(root)
    if with_sources:
        _write_model_card_sources(root)
    return root


def test_model_card_route_returns_curated_response_for_all_published_positions(
    tmp_path: Path,
) -> None:
    root = _published_root(tmp_path)

    with patch("app.api.routes.trust_surface.RUNS_DIR", root):
        for position in POSITIONS:
            response = client.get(f"/api/trust-surface/{position}/model-card")

            assert response.status_code == 200
            data = response.json()
            assert set(data) == PUBLIC_MODEL_CARD_FIELDS
            assert data["position"] == position
            assert data["backtest_run_id"]
            assert isinstance(data["out_of_scope_uses"], list)
            assert isinstance(data["caveats"], list)
            assert isinstance(data["known_failure_modes"], list)
            assert FORBIDDEN_PUBLIC_KEYS.isdisjoint(data)


def test_model_card_route_missing_published_source_degrades_to_404(
    tmp_path: Path,
) -> None:
    root = _published_root(tmp_path, with_sources=False)

    with patch("app.api.routes.trust_surface.RUNS_DIR", root):
        response = client.get("/api/trust-surface/QB/model-card")

    assert response.status_code == 404
    assert "No model card found for position QB" in response.json()["detail"]


def test_trust_surface_model_card_available_matches_model_card_200(
    tmp_path: Path,
) -> None:
    root = _published_root(tmp_path)

    with patch("app.api.routes.trust_surface.RUNS_DIR", root):
        for position in POSITIONS:
            surface = client.get(f"/api/trust-surface/{position}")
            card = client.get(f"/api/trust-surface/{position}/model-card")

            assert surface.status_code == 200
            assert card.status_code == 200
            assert surface.json()["model_card_available"] is True


def test_trust_surface_model_card_available_false_when_source_missing(
    tmp_path: Path,
) -> None:
    root = _published_root(tmp_path, with_sources=False)

    with patch("app.api.routes.trust_surface.RUNS_DIR", root):
        surface = client.get("/api/trust-surface/QB")
        card = client.get("/api/trust-surface/QB/model-card")

    assert surface.status_code == 200
    assert surface.json()["model_card_available"] is False
    assert card.status_code == 404
