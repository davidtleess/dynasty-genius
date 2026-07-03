"""BUILD-1 T2 RED: pure tier-readiness evaluator.

These tests use constructed inputs only. They do not read config files, inspect
evidence paths, call live guard adapters, mount routes, or depend on the real
tier-readiness registry. T2 covers only the pure evaluator:
``evaluate_surface_readiness(surface_config, live_precondition_statuses,
component_states, ...) -> SurfaceReadiness``.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.api.routes.system_tier_readiness_models import (
    GateComponentConfig,
    SurfaceReadiness,
    TierSurfaceConfig,
)


def _component(
    component: str,
    *,
    optional: bool = False,
) -> GateComponentConfig:
    return GateComponentConfig.model_validate(
        {
            "component": component,
            "evidence": [f"tests/contract/{component}.py"],
            "expectation": f"{component} expectation",
            "optional": optional,
        }
    )


def _surface(
    *,
    ratified_date: str | None = "2026-07-02",
    gate_components: list[GateComponentConfig] | None = None,
) -> TierSurfaceConfig:
    return TierSurfaceConfig.model_validate(
        {
            "surface_id": "roster_capacity",
            "display_name": "Roster Capacity",
            "declared_tier": "tier_1_candidate",
            "route_ids": ["/api/roster/capacity"],
            "producer_artifacts": [
                "app/data/roster_capacity/roster_capacity_latest.json"
            ],
            "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
            "gate_components": gate_components
            if gate_components is not None
            else [
                _component("audit_hygiene"),
                _component("deterministic_range_disclosure"),
                _component("mif_breaker"),
                _component("no_directive_copy"),
            ],
            "ratified_by": "David",
            "ratified_date": ratified_date,
        }
    )


def _live(
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    live = {"model_provenance_ok": "ok", "capture_health_ok": "ok"}
    if overrides:
        live.update(overrides)
    return live


def _states(overrides: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    states = {
        "audit_hygiene": {
            "component_status": "pass",
            "basis": "route contract and cordon tests present",
        },
        "deterministic_range_disclosure": {
            "component_status": "pass",
            "basis": "signed unclamped range tests present",
        },
        "mif_breaker": {
            "component_status": "pass",
            "basis": "MIF breaker evaluable and within threshold",
        },
        "no_directive_copy": {
            "component_status": "pass",
            "basis": "banned-language gate clean",
        },
    }
    if overrides:
        states.update(overrides)
    return states


def _evaluate(
    *,
    surface: TierSurfaceConfig | None = None,
    live: dict[str, str] | None = None,
    states: dict[str, dict[str, str]] | None = None,
) -> SurfaceReadiness:
    import app.api.routes.system_tier_readiness_models as models

    return models.evaluate_surface_readiness(
        surface_config=surface or _surface(),
        live_precondition_statuses=live or _live(),
        component_states=states or _states(),
    )


def test_all_pass_and_green_preconditions_yields_plain_active() -> None:
    result = _evaluate()

    assert result.tier_status == "diagnostic_grade_active"
    assert result.basis == "all_readiness_checks_passed"
    assert result.insufficient_data_count == 0
    assert result.insufficient_data_components == []
    assert result.all_components_evaluable is True
    assert result.live_preconditions == _live()
    assert [component.component for component in result.components] == [
        "audit_hygiene",
        "deterministic_range_disclosure",
        "mif_breaker",
        "no_directive_copy",
    ]
    assert all(
        component.component_status == "pass" for component in result.components
    )
    assert result.decision_supported is False
    assert all(component.decision_supported is False for component in result.components)


def test_insufficient_data_never_blocks_but_forces_limited_headline_and_root_disclosure() -> None:
    result = _evaluate(
        states=_states(
            {
                "mif_breaker": {
                    "component_status": "insufficient_data",
                    "basis": "off-season presence probe only",
                }
            }
        )
    )

    assert result.tier_status == "diagnostic_grade_active_limited"
    assert result.basis == "readiness_active_with_insufficient_data"
    assert result.insufficient_data_count == 1
    assert result.insufficient_data_components == ["mif_breaker"]
    assert result.all_components_evaluable is False
    mif = _component_by_name(result, "mif_breaker")
    assert mif.component_status == "insufficient_data"
    assert mif.basis == "off-season presence probe only"


@pytest.mark.parametrize(
    ("precondition", "status"),
    [
        ("model_provenance_ok", "degraded"),
        ("model_provenance_ok", "blocked"),
        ("capture_health_ok", "degraded"),
    ],
)
def test_any_live_precondition_not_ok_degrades_regardless_of_component_states(
    precondition: str,
    status: str,
) -> None:
    result = _evaluate(
        live=_live({precondition: status}),
        states=_states(
            {
                "audit_hygiene": {
                    "component_status": "fail",
                    "basis": "contract deleted",
                },
                "mif_breaker": {
                    "component_status": "insufficient_data",
                    "basis": "off-season presence probe only",
                },
            }
        ),
    )

    assert result.tier_status == "preconditions_degraded"
    assert result.basis == f"live_precondition_not_ok:{precondition}={status}"
    assert result.live_preconditions[precondition] == status
    assert _component_by_name(result, "audit_hygiene").component_status == "fail"
    assert result.insufficient_data_components == ["mif_breaker"]


def test_null_ratification_blocks_activation_even_when_every_check_passes() -> None:
    result = _evaluate(surface=_surface(ratified_date=None))

    assert result.tier_status == "not_graduated"
    assert result.basis == "awaiting_david_ratification"
    assert result.insufficient_data_count == 0
    assert result.all_components_evaluable is True
    assert all(
        component.component_status == "pass" for component in result.components
    )


def test_any_component_fail_auto_downgrades_not_graduated() -> None:
    result = _evaluate(
        states=_states(
            {
                "audit_hygiene": {
                    "component_status": "fail",
                    "basis": "route contract failed",
                }
            }
        )
    )

    assert result.tier_status == "not_graduated"
    assert result.basis == "component_failed:audit_hygiene"
    assert _component_by_name(result, "audit_hygiene").basis == "route contract failed"


def test_required_not_applicable_is_treated_as_fail_but_optional_not_applicable_does_not_block() -> None:
    optional_surface = _surface(
        gate_components=[
            _component("audit_hygiene"),
            _component("deterministic_range_disclosure", optional=True),
            _component("mif_breaker"),
            _component("no_directive_copy"),
        ]
    )
    optional_result = _evaluate(
        surface=optional_surface,
        states=_states(
            {
                "deterministic_range_disclosure": {
                    "component_status": "not_applicable",
                    "basis": "optional for this surface shape",
                }
            }
        ),
    )
    required_result = _evaluate(
        states=_states(
            {
                "deterministic_range_disclosure": {
                    "component_status": "not_applicable",
                    "basis": "missing required range disclosure",
                }
            }
        )
    )

    assert optional_result.tier_status == "diagnostic_grade_active"
    assert _component_by_name(
        optional_result, "deterministic_range_disclosure"
    ).component_status == "not_applicable"
    assert required_result.tier_status == "not_graduated"
    assert (
        required_result.basis
        == "required_component_not_applicable:deterministic_range_disclosure"
    )
    assert _component_by_name(
        required_result, "deterministic_range_disclosure"
    ).component_status == "fail"


def test_unknown_component_status_fails_closed_without_crashing() -> None:
    result = _evaluate(
        states=_states(
            {
                "mif_breaker": {
                    "component_status": "unknown_future_state",
                    "basis": "new unclassified status",
                }
            }
        )
    )

    assert result.tier_status == "not_graduated"
    assert result.basis == "unknown_component_status:mif_breaker"
    component = _component_by_name(result, "mif_breaker")
    assert component.component_status == "fail"
    assert "unknown_future_state" in component.basis


def test_missing_component_state_fails_closed_and_preserves_declared_order() -> None:
    states = _states()
    states.pop("no_directive_copy")

    result = _evaluate(states=states)

    assert result.tier_status == "not_graduated"
    assert result.basis == "component_state_missing:no_directive_copy"
    assert [component.component for component in result.components] == [
        "audit_hygiene",
        "deterministic_range_disclosure",
        "mif_breaker",
        "no_directive_copy",
    ]
    missing = _component_by_name(result, "no_directive_copy")
    assert missing.component_status == "fail"
    assert missing.basis == "component_state_missing"


def test_plain_active_requires_zero_insufficient_data_components() -> None:
    active = _evaluate()
    limited = _evaluate(
        states=_states(
            {
                "mif_breaker": {
                    "component_status": "insufficient_data",
                    "basis": "off-season presence probe only",
                },
                "no_directive_copy": {
                    "component_status": "insufficient_data",
                    "basis": "frontend path not yet mounted",
                },
            }
        )
    )

    assert active.tier_status == "diagnostic_grade_active"
    assert active.all_components_evaluable is True
    assert limited.tier_status == "diagnostic_grade_active_limited"
    assert limited.insufficient_data_count == 2
    assert limited.insufficient_data_components == ["mif_breaker", "no_directive_copy"]
    assert limited.all_components_evaluable is False


def test_decision_supported_false_recursive_and_tier_two_injection_rejected() -> None:
    result = _evaluate()

    assert result.decision_supported is False
    assert all(component.decision_supported is False for component in result.components)
    with pytest.raises(ValueError):
        SurfaceReadiness.model_validate(
            result.model_dump() | {"decision_supported": True}
        )


def _component_by_name(result: SurfaceReadiness, component: str):
    return next(item for item in result.components if item.component == component)
