from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

POSITIONS = ("QB", "RB", "WR", "TE")

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
    "subgroup_results",
    "calibration",
    "ethical_considerations",
}

client = TestClient(app)


def test_tracked_published_trust_substrate_serves_all_positions() -> None:
    """CI-real smoke over committed trust_surface/latest artifacts, no monkeypatch."""
    for position in POSITIONS:
        surface = client.get(f"/api/trust-surface/{position}")
        card = client.get(f"/api/trust-surface/{position}/model-card")

        assert surface.status_code == 200
        assert card.status_code == 200

        surface_data = surface.json()
        card_data = card.json()

        assert surface_data["position"] == position
        assert card_data["position"] == position
        assert surface_data["model_card_available"] is True
        assert card_data["backtest_run_id"] == surface_data["run_id"]

        assert set(card_data) == PUBLIC_MODEL_CARD_FIELDS
        assert FORBIDDEN_PUBLIC_KEYS.isdisjoint(card_data)
        assert card_data["is_experimental"] == surface_data["experimental"]
        assert isinstance(card_data["intended_use"], str)
        assert isinstance(card_data["out_of_scope_uses"], list)
        assert isinstance(card_data["caveats"], list)
        assert isinstance(card_data["known_failure_modes"], list)
