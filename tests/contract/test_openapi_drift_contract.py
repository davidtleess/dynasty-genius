from __future__ import annotations

import json
from pathlib import Path

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"
OPENAPI_DUMP_SCRIPT = REPO_ROOT / "scripts" / "dump_openapi.py"


def _canonical_openapi_text() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def test_openapi_snapshot_exists_with_regeneration_helper() -> None:
    assert OPENAPI_DUMP_SCRIPT.exists(), (
        "Missing scripts/dump_openapi.py; frontend OpenAPI snapshots must have one "
        "canonical regeneration path"
    )
    assert OPENAPI_SNAPSHOT.exists(), (
        "Missing frontend/openapi.json; run `npm --prefix frontend run openapi-gen` "
        "after backend OpenAPI contract changes"
    )


def test_openapi_snapshot_matches_live_app_schema() -> None:
    assert OPENAPI_SNAPSHOT.read_text(encoding="utf-8") == _canonical_openapi_text()


def test_trust_surface_route_has_typed_openapi_schema() -> None:
    schema = app.openapi()
    trust_surface_schema = schema["paths"]["/api/trust-surface/{position}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]

    assert trust_surface_schema.get("$ref", "").endswith("/TrustSurfaceResponse")

    components = schema["components"]["schemas"]
    response_schema = components["TrustSurfaceResponse"]
    properties = response_schema["properties"]

    for field_name in (
        "run_id",
        "position",
        "promotion_gate",
        "overall_grade",
        "experimental",
        "model_card_available",
        "model_reliability",
    ):
        assert field_name in properties

    assert response_schema["required"] == [
        "run_date",
        "model_version",
        "model_artifact_hash",
        "position",
        "ridge_alpha",
        "retrain_mode",
        "folds",
        "rmse_stability",
        "market_source",
        "promotion_gate",
        "overall_grade",
        "model_status",
        "experimental",
        "model_card_available",
    ]
