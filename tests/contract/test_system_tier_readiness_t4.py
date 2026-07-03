"""BUILD-1 T4 RED: real tier-readiness registry + CI tripwire.

This is the one tier-readiness test that intentionally reads the real
checked-in ``app/config/tier_readiness.json``. It must never depend on
gitignored producer artifacts or live stores. Its job is to fail CI if a
Tier-1 registered surface loses the concrete contract evidence that justified
the readiness claim.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes.system_tier_readiness_models import (
    SurfaceReadiness,
    TierReadinessResponse,
    load_tier_readiness,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "app" / "config" / "tier_readiness.json"
OPENAPI_PATH = REPO_ROOT / "frontend" / "openapi.json"
BANNED_RESPONSE_RE = re.compile(
    r"\b(certified|validated|trusted|approved|safe|recommended|buy|sell|hold|start|sit)\b",
    re.IGNORECASE,
)


def test_real_tier_readiness_registry_loads_and_names_roster_capacity_contract() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)

    assert registry.registry_version == 1
    assert [surface.surface_id for surface in registry.surfaces] == [
        "roster_capacity"
    ]
    surface = registry.surfaces[0]
    assert surface.ratified_by == "David"
    assert surface.ratified_date == "2026-07-02"
    assert surface.route_ids == ["/api/roster/capacity"]
    assert surface.live_preconditions == ["model_provenance_ok", "capture_health_ok"]
    assert [component.component for component in surface.gate_components] == [
        "audit_hygiene",
        "deterministic_range_disclosure",
        "mif_breaker",
        "no_directive_copy",
    ]


def test_every_registered_route_id_is_mounted_in_app_main() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)
    openapi_paths = set(json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["paths"])

    for surface in registry.surfaces:
        for route_id in surface.route_ids:
            assert route_id in openapi_paths


def test_every_evidence_path_exists_but_producer_artifacts_are_not_ci_checked() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)

    for surface in registry.surfaces:
        for component in surface.gate_components:
            for evidence in component.evidence:
                assert (REPO_ROOT / evidence).exists(), evidence

        # Producer artifacts are gitignored runtime status inputs (R8), not CI
        # tripwire evidence. This assertion catches accidental promotion of the
        # runtime-only `_latest` artifact to an evidence path.
        producer_artifacts = set(surface.producer_artifacts)
        evidence_paths = {
            evidence
            for component in surface.gate_components
            for evidence in component.evidence
        }
        assert producer_artifacts.isdisjoint(evidence_paths)


def test_roster_capacity_evidence_names_semantic_contract_tests() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)
    surface = registry.surfaces[0]
    evidence_paths = {
        evidence
        for component in surface.gate_components
        for evidence in component.evidence
    }

    assert "tests/contract/test_roster_capacity_route.py" in evidence_paths
    assert "tests/contract/test_roster_capacity_simulator.py" in evidence_paths
    assert "frontend/scripts/check-banned-language.mjs" in evidence_paths

    route_test = (REPO_ROOT / "tests/contract/test_roster_capacity_route.py").read_text(
        encoding="utf-8"
    )
    simulator_test = (
        REPO_ROOT / "tests/contract/test_roster_capacity_simulator.py"
    ).read_text(encoding="utf-8")

    assert "cumulative_value_at_risk" in route_test
    assert "marginal_next_candidate_cost" in route_test
    assert "marginal_next_candidate_player_id" in route_test
    assert '"recommendation"' in route_test
    assert "_decision_supported_true_count(body) == 0" in route_test
    assert "test_mixed_position_zero_crossing_cumulative_range_is_unclamped" in (
        simulator_test
    )
    assert "marginal_next_candidate_id" in simulator_test
    assert "scenario.cumulative_value_at_risk[0] < 0" in simulator_test
    assert "_decision_supported_true_count(result) == 0" in simulator_test


def test_response_models_remain_strict_recursive_false_and_verdict_free() -> None:
    component = {
        "component": "mif_breaker",
        "component_status": "insufficient_data",
        "basis": "off-season presence probe only",
        "decision_supported": False,
    }
    surface = {
        "surface_id": "roster_capacity",
        "display_name": "Roster Capacity",
        "tier_status": "diagnostic_grade_active_limited",
        "basis": "readiness_active_with_insufficient_data",
        "components": [component],
        "insufficient_data_count": 1,
        "insufficient_data_components": ["mif_breaker"],
        "all_components_evaluable": False,
        "live_preconditions": {
            "model_provenance_ok": "ok",
            "capture_health_ok": "ok",
        },
        "decision_supported": False,
    }
    response = TierReadinessResponse.model_validate(
        {
            "overall_status": "ok",
            "registry_version": 1,
            "surfaces": [surface],
            "decision_supported": False,
        }
    )

    _assert_decision_supported_false_recursive(response.model_dump())
    _assert_no_banned_response_language(response.model_dump())

    with pytest.raises(ValidationError):
        SurfaceReadiness.model_validate(surface | {"verdict": "ready"})
    with pytest.raises(ValidationError):
        SurfaceReadiness.model_validate(surface | {"decision_supported": True})
    nested = json.loads(json.dumps(response.model_dump()))
    nested["surfaces"][0]["components"][0]["recommendation"] = "use this surface"
    with pytest.raises(ValidationError):
        TierReadinessResponse.model_validate(nested)


def test_tier_readiness_route_openapi_exposes_200_and_503_schema_refs() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/system/tier-readiness"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("TierReadinessResponse")
    assert operation["responses"]["503"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("TierReadinessErrorResponse")


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _assert_no_banned_response_language(value: Any) -> None:
    flattened = json.dumps(value, sort_keys=True)
    assert not BANNED_RESPONSE_RE.search(flattened)
