"""BUILD-1 T1 RED: tier-readiness registry models and fail-closed loader.

These tests are fixture-only. They use temp registry files and never read the
real app/config tier-readiness registry, runtime guards, routes, or gitignored
producer artifacts. T1 covers only strict Pydantic models and the config loader;
the readiness evaluator, live adapters, route wiring, tripwire, and OpenAPI are
later tasks.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError


def _models():
    import app.api.routes.system_tier_readiness_models as models

    return models


def _component(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    component = {
        "component": "deterministic_range_disclosure",
        "evidence": ["tests/contract/test_roster_capacity_route.py"],
        "expectation": "ranges signed and unclamped",
        "optional": False,
    }
    if overrides:
        component.update(overrides)
    return component


def _surface(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    surface = {
        "surface_id": "roster_capacity",
        "display_name": "Roster Capacity",
        "declared_tier": "tier_1_candidate",
        "route_ids": ["/api/roster/capacity"],
        "producer_artifacts": [
            "app/data/roster_capacity/roster_capacity_latest.json"
        ],
        "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
        "gate_components": [
            _component(
                {
                    "component": "audit_hygiene",
                    "evidence": [
                        "tests/contract/test_roster_capacity_route.py",
                        "scripts/scan_league_opportunity_no_verdict.py",
                    ],
                    "expectation": "cordon and leakage gates enforced",
                }
            ),
            _component(),
            _component(
                {
                    "component": "mif_breaker",
                    "evidence": [
                        "src/dynasty_genius/realized_outcome/scorer.py",
                        "tests/contract/test_realized_outcome_scorecard_route.py",
                    ],
                    "expectation": "presence probe only until MIF is evaluable",
                }
            ),
            _component(
                {
                    "component": "no_directive_copy",
                    "evidence": ["frontend/scripts/check-banned-language.mjs"],
                    "expectation": "graduated path has no directive tokens",
                }
            ),
        ],
        "ratified_by": "David",
        "ratified_date": None,
    }
    if overrides:
        surface.update(overrides)
    return surface


def _registry_body(surfaces: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "registry_version": 1,
        "surfaces": surfaces if surfaces is not None else [_surface()],
    }


def _write_registry(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_loader_reads_injected_temp_registry_without_app_config_dependency(
    tmp_path: Path,
) -> None:
    models = _models()
    registry_path = _write_registry(tmp_path / "tier_readiness.json", _registry_body())

    registry = models.load_tier_readiness(
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    assert isinstance(registry, models.TierReadinessRegistry)
    assert registry.registry_version == 1
    assert len(registry.surfaces) == 1
    surface = registry.surfaces[0]
    assert surface.surface_id == "roster_capacity"
    assert surface.display_name == "Roster Capacity"
    assert surface.declared_tier == "tier_1_candidate"
    assert surface.route_ids == ["/api/roster/capacity"]
    assert surface.producer_artifacts == [
        "app/data/roster_capacity/roster_capacity_latest.json"
    ]
    assert surface.live_preconditions == ["model_provenance_ok", "capture_health_ok"]
    assert surface.ratified_by == "David"
    assert surface.ratified_date is None
    assert [component.component for component in surface.gate_components] == [
        "audit_hygiene",
        "deterministic_range_disclosure",
        "mif_breaker",
        "no_directive_copy",
    ]
    assert all(component.optional is False for component in surface.gate_components)


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (
            lambda path: path.write_text(
                json.dumps(_registry_body([_surface({"declared_tier": "tier_2"})])),
                encoding="utf-8",
            ),
            "schema",
        ),
        (
            lambda path: path.write_text(
                json.dumps(_registry_body([])),
                encoding="utf-8",
            ),
            "empty",
        ),
        (
            lambda path: path.write_text(
                json.dumps(
                    _registry_body(
                        [
                            _surface({"surface_id": "duplicate"}),
                            _surface({"surface_id": "duplicate"}),
                        ]
                    )
                ),
                encoding="utf-8",
            ),
            "duplicate",
        ),
    ],
)
def test_loader_raises_typed_error_for_registry_family_failures(
    tmp_path: Path,
    writer,
    message_fragment: str,
) -> None:
    models = _models()
    registry_path = tmp_path / "tier_readiness.json"
    writer(registry_path)

    with pytest.raises(models.TierReadinessConfigError) as exc_info:
        models.load_tier_readiness(registry_path=registry_path, repo_root=tmp_path)

    assert message_fragment in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "surface_overrides",
    [
        {"live_preconditions": ["model_provenance_ok", "unknown_guard"]},
        {"live_preconditions": ["capture_health_ok", "capture_health_ok"]},
        {
            "gate_components": [
                _component({"component": "unknown_component"}),
            ]
        },
    ],
)
def test_loader_rejects_unknown_or_duplicate_ids(
    tmp_path: Path,
    surface_overrides: dict[str, Any],
) -> None:
    models = _models()
    registry_path = _write_registry(
        tmp_path / "tier_readiness.json",
        _registry_body([_surface(surface_overrides)]),
    )

    with pytest.raises(models.TierReadinessConfigError) as exc_info:
        models.load_tier_readiness(registry_path=registry_path, repo_root=tmp_path)

    assert "unknown" in str(exc_info.value).lower() or "duplicate" in str(
        exc_info.value
    ).lower()


@pytest.mark.parametrize(
    "evidence_path",
    [
        "/tmp/outside_contract.py",
        "../outside_contract.py",
        "tests/contract/../../../../outside_contract.py",
        "tests\\contract\\test_roster_capacity_route.py",
    ],
)
def test_loader_rejects_evidence_paths_that_escape_repo_root_or_use_backslashes(
    tmp_path: Path,
    evidence_path: str,
) -> None:
    models = _models()
    registry_path = _write_registry(
        tmp_path / "tier_readiness.json",
        _registry_body(
            [
                _surface(
                    {
                        "gate_components": [
                            _component({"evidence": [evidence_path]})
                        ]
                    }
                )
            ]
        ),
    )

    with pytest.raises(models.TierReadinessConfigError) as exc_info:
        models.load_tier_readiness(registry_path=registry_path, repo_root=tmp_path)

    assert "evidence" in str(exc_info.value).lower()


def test_registry_models_forbid_extra_fields_and_strict_types() -> None:
    models = _models()

    with pytest.raises(ValidationError):
        models.TierReadinessRegistry.model_validate(
            _registry_body() | {"gate_4_ready": True}
        )
    with pytest.raises(ValidationError):
        models.TierSurfaceConfig.model_validate(
            _surface({"gate_4_ready": True})
        )
    with pytest.raises(ValidationError):
        models.GateComponentConfig.model_validate(
            _component({"gate_4_ready": True})
        )
    with pytest.raises(ValidationError):
        models.TierReadinessRegistry.model_validate(
            _registry_body() | {"registry_version": "1"}
        )
    with pytest.raises(ValidationError):
        models.GateComponentConfig.model_validate(_component({"optional": "false"}))


def test_response_models_lock_status_enums_root_disclosures_and_recursive_false(
    ) -> None:
    models = _models()

    component = models.ComponentReadiness.model_validate(
        {
            "component": "mif_breaker",
            "component_status": "insufficient_data",
            "basis": "off-season presence probe only",
            "decision_supported": False,
        }
    )
    surface = models.SurfaceReadiness.model_validate(
        {
            "surface_id": "roster_capacity",
            "display_name": "Roster Capacity",
            "tier_status": "diagnostic_grade_active_limited",
            "components": [component.model_dump()],
            "insufficient_data_count": 1,
            "insufficient_data_components": ["mif_breaker"],
            "all_components_evaluable": False,
            "live_preconditions": {
                "model_provenance_ok": "ok",
                "capture_health_ok": "ok",
            },
            "decision_supported": False,
        }
    )
    response = models.TierReadinessResponse.model_validate(
        {
            "overall_status": "ok",
            "registry_version": 1,
            "surfaces": [surface.model_dump()],
            "decision_supported": False,
        }
    )
    error = models.TierReadinessErrorResponse.model_validate(
        {
            "error": "tier_readiness_unavailable",
            "message": "tier readiness configuration is unavailable",
            "decision_supported": False,
        }
    )

    assert response.surfaces[0].tier_status == "diagnostic_grade_active_limited"
    assert response.surfaces[0].insufficient_data_count == 1
    assert response.surfaces[0].insufficient_data_components == ["mif_breaker"]
    assert response.surfaces[0].all_components_evaluable is False
    assert response.surfaces[0].components[0].decision_supported is False
    assert error.decision_supported is False

    with pytest.raises(ValidationError):
        models.ComponentReadiness.model_validate(
            component.model_dump() | {"component_status": "unknown"}
        )
    with pytest.raises(ValidationError):
        models.SurfaceReadiness.model_validate(
            surface.model_dump() | {"tier_status": "certified"}
        )
    with pytest.raises(ValidationError):
        models.TierReadinessResponse.model_validate(
            response.model_dump() | {"decision_supported": True}
        )
    with pytest.raises(ValidationError):
        models.ComponentReadiness.model_validate(
            component.model_dump() | {"recommendation": "use this surface"}
        )


def test_no_model_field_or_status_value_can_express_decision_supported_true() -> None:
    models = _models()

    with pytest.raises(ValidationError):
        models.ComponentReadiness.model_validate(
            {
                "component": "audit_hygiene",
                "component_status": "pass",
                "basis": "contract tests present",
                "decision_supported": True,
            }
        )
    with pytest.raises(ValidationError):
        models.SurfaceReadiness.model_validate(
            {
                "surface_id": "roster_capacity",
                "display_name": "Roster Capacity",
                "tier_status": "diagnostic_grade_active",
                "components": [],
                "insufficient_data_count": 0,
                "insufficient_data_components": [],
                "all_components_evaluable": True,
                "live_preconditions": {
                    "model_provenance_ok": "ok",
                    "capture_health_ok": "ok",
                },
                "decision_supported": True,
            }
        )


def test_model_field_names_and_status_values_avoid_banned_vocabulary() -> None:
    models = _models()
    banned = ("certified", "validated", "trusted", "approved", "safe", "recommended")
    model_classes = [
        models.GateComponentConfig,
        models.TierSurfaceConfig,
        models.TierReadinessRegistry,
        models.ComponentReadiness,
        models.SurfaceReadiness,
        models.TierReadinessResponse,
        models.TierReadinessErrorResponse,
    ]

    names: set[str] = set()
    for model_class in model_classes:
        names.update(model_class.model_fields)

    values = {
        *_string_values(models.ComponentStatus),
        *_string_values(models.TierStatus),
    }
    scanned = {value.lower() for value in names | values}

    for token in banned:
        assert all(token not in value for value in scanned), token


def _string_values(obj: object) -> set[str]:
    if isinstance(obj, type) and issubclass(obj, Enum):
        return {
            str(member.value)
            for member in obj
            if isinstance(member.value, str)
        }
    return {arg for arg in get_args(obj) if isinstance(arg, str)}
