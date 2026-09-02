"""DG-135: the 503 that DG-133 made two routes send is declared in the OpenAPI contract,
and declared in the shape the server actually sends.

Two failure modes this pins:
- the route lists only ``200`` (the pre-DG-135 state) — the generated client has no typed
  shape for the outage;
- the route declares a 503 model that does NOT validate the real body (FastAPI wraps
  ``HTTPException.detail`` as ``{"detail": ...}``; a flat model would be a contract lie).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes import engine_b as engine_b_route
from app.api.routes import roster as roster_route
from app.api.routes.dependency_unavailable_models import (
    EngineBDependencyUnavailableResponse,
    RosterDependencyUnavailableResponse,
)
from app.main import app
from src.dynasty_genius.features import inference_partition as ip

ROUTES = {
    "/api/engine-b/scores": "EngineBDependencyUnavailableResponse",
    "/api/roster/audit": "RosterDependencyUnavailableResponse",
}


@pytest.mark.parametrize(("path", "model_name"), sorted(ROUTES.items()))
def test_route_declares_200_and_503_pointing_at_its_own_model(path: str, model_name: str) -> None:
    responses = app.openapi()["paths"][path]["get"]["responses"]
    # Subset, not equality: the roster route also sends a pre-DG-133 422
    # (roster_config_error) that is not yet declared; declaring it must not fail this.
    assert {"200", "503"} <= set(responses), responses.keys()
    ref = responses["503"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == f"#/components/schemas/{model_name}"


def test_declared_503_schema_is_the_detail_envelope_not_a_flat_body() -> None:
    components = app.openapi()["components"]["schemas"]
    for model_name in ROUTES.values():
        assert components[model_name]["required"] == ["detail"]
        detail_ref = components[model_name]["properties"]["detail"]["$ref"]
        detail = components[detail_ref.rsplit("/", 1)[1]]
        assert detail["required"] == ["error", "message"]
        assert "const" in detail["properties"]["error"], "the error token must be pinned"


def test_engine_b_scores_503_body_validates_against_the_declared_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse() -> list:
        raise ip.InferencePartitionError(ip.DUPLICATE_PLAYER)

    monkeypatch.setattr(engine_b_route, "score_inference_partition", refuse)
    response = TestClient(app).get("/api/engine-b/scores")

    assert response.status_code == 503
    body = EngineBDependencyUnavailableResponse.model_validate(response.json())
    assert body.detail.message == ip.DUPLICATE_PLAYER


def test_roster_audit_partition_503_body_validates_against_the_declared_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def refuse() -> dict:
        raise ip.InferencePartitionError(ip.EMPTY)

    monkeypatch.setattr(roster_route, "run_audit_pvo", refuse)
    response = TestClient(app).get("/api/roster/audit")

    assert response.status_code == 503
    body = RosterDependencyUnavailableResponse.model_validate(response.json())
    assert body.detail.message == ip.EMPTY


def test_roster_audit_assembler_503_body_validates_against_the_declared_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The route's second 503 site: every roster row failed to map (RosterDependencyError
    from ``assemble_response``). Same declaration covers it, so the same model must fit."""

    async def all_rows_unmappable() -> dict:
        return {"status": "active", "players": [{"x": 1}, {"y": 2}], "qb_context_cards": []}

    monkeypatch.setattr(roster_route, "run_audit_pvo", all_rows_unmappable)
    response = TestClient(app).get("/api/roster/audit")

    assert response.status_code == 503
    body = RosterDependencyUnavailableResponse.model_validate(response.json())
    assert body.detail.message == "all roster rows failed to map"
