"""BUILD-1 Increment 1 — T3: the read-only tier-readiness route.

``GET /api/system/tier-readiness`` serves the Diagnostic Grade ladder: per
registered surface, the pure evaluator's verdict over (a) live guard statuses
from IN-PROCESS adapters over the DEBT-6 assemblies (never HTTP self-calls —
R9), (b) component states derived here (evidence existence → fail with the
missing path named; the MIF breaker reports ``insufficient_data`` off-season
— a presence probe, never a default pass), and (c) a producer-artifact
runtime overlay (a gitignored `_latest` artifact absent at request time
downgrades the surface — R8 — never a config error).

Tier-1 never flips ``decision_supported``. Registry corruption returns one
sanitized fixed 503.

Spec: docs/superpowers/specs/2026-07-02-build1-tier1-graduation-increment1-design.md
Plan: docs/superpowers/plans/2026-07-02-build1-tier1-graduation-increment1-plan.md
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.system_tier_readiness_models import (
    TierReadinessConfigError,
    TierReadinessErrorResponse,
    TierReadinessResponse,
    TierSurfaceConfig,
    evaluate_surface_readiness,
    load_tier_readiness,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_PATH = _REPO_ROOT / "app" / "config" / "tier_readiness.json"

_SANITIZED_MESSAGE = "tier readiness configuration unavailable"
_ACTIVE_STATUSES = ("diagnostic_grade_active", "diagnostic_grade_active_limited")

router = APIRouter(prefix="/system", tags=["system"])


def _default_model_provenance_status() -> str:
    """Live provenance overall status, computed in-process (fail-closed)."""

    try:
        from app.api.routes import system_model_provenance as smp
        from app.api.routes.system_model_provenance_models import (
            inspect_registered_artifact,
            load_model_registry,
            resolve_runtime_environment,
            scan_unregistered_local_artifacts,
        )

        registry = load_model_registry(registry_path=smp._REGISTRY_PATH)
        environment = resolve_runtime_environment(environ=smp._ENVIRON)
        rows = [
            inspect_registered_artifact(
                entry=entry, repo_root=smp._REPO_ROOT, environment=environment
            )
            for entry in registry.artifacts
        ]
        rows.extend(
            scan_unregistered_local_artifacts(
                registry=registry, repo_root=smp._REPO_ROOT, environment=environment
            )
        )
        return smp._overall_status(rows)
    except Exception:
        return "unavailable"


def _default_capture_health_status() -> str:
    """Live capture-health overall status, computed in-process (fail-closed)."""

    try:
        from app.api.routes import system_capture_health as sch
        from app.api.routes.system_capture_health_models import (
            inspect_capture_store,
            load_capture_cadence,
        )

        config = load_capture_cadence(config_path=sch._CONFIG_PATH)
        now = sch._CLOCK()
        stores = [
            inspect_capture_store(
                store_config=store_config,
                repo_root=sch._REPO_ROOT,
                now=now,
                timezone=config.timezone,
                season_windows=config.season_windows,
            )
            for store_config in config.stores
        ]
        return (
            "degraded"
            if any(store.store_status == "degraded" for store in stores)
            else "ok"
        )
    except Exception:
        return "unavailable"


# Module-level so tests monkeypatch these with deterministic seams (R9).
_MODEL_PROVENANCE_ADAPTER: Callable[[], str] = _default_model_provenance_status
_CAPTURE_HEALTH_ADAPTER: Callable[[], str] = _default_capture_health_status


def _config_unavailable_503() -> JSONResponse:
    body = TierReadinessErrorResponse(
        error="tier_readiness_unavailable",
        message=_SANITIZED_MESSAGE,
        decision_supported=False,
    )
    return JSONResponse(status_code=503, content=body.model_dump())


def _derive_component_states(
    surface: TierSurfaceConfig, repo_root: Path
) -> dict[str, dict[str, str]]:
    """Derive component states from disk facts (evidence existence + MIF probe).

    Evidence existence is the runtime floor (spec §3.3); the semantic depth of
    each claim is owned by the T4 CI tripwire. The MIF breaker never default-
    passes: off-season it reports ``insufficient_data`` after the presence
    probe (its evidence paths exist), per Gemini seed B and David's ratified
    option (a).
    """

    states: dict[str, dict[str, str]] = {}
    for component in surface.gate_components:
        missing = [
            evidence
            for evidence in component.evidence
            if not (repo_root / evidence).is_file()
        ]
        if missing:
            states[component.component] = {
                "component_status": "fail",
                "basis": "; ".join(f"evidence_missing:{path}" for path in missing),
            }
        elif component.component == "mif_breaker":
            states[component.component] = {
                "component_status": "insufficient_data",
                "basis": (
                    "off_season_presence_probe_only: declared evidence present; "
                    "active-role deviation not evaluable until in-season data accrues"
                ),
            }
        else:
            states[component.component] = {
                "component_status": "pass",
                "basis": "declared evidence files present",
            }
    return states


@router.get(
    "/tier-readiness",
    response_model=TierReadinessResponse,
    responses={503: {"model": TierReadinessErrorResponse}},
)
def get_tier_readiness():
    try:
        registry = load_tier_readiness(
            registry_path=_REGISTRY_PATH, repo_root=_REPO_ROOT
        )
    except TierReadinessConfigError:
        return _config_unavailable_503()

    # The seam itself fails closed (Codex T3 defect): a raising adapter —
    # injected or real — reads as "unavailable" (≠ ok → degrades), never a 500.
    def _guarded(adapter: Callable[[], str]) -> str:
        try:
            return adapter()
        except Exception:
            return "unavailable"

    live = {
        "model_provenance_ok": _guarded(_MODEL_PROVENANCE_ADAPTER),
        "capture_health_ok": _guarded(_CAPTURE_HEALTH_ADAPTER),
    }

    surfaces = []
    for surface_config in registry.surfaces:
        readiness = evaluate_surface_readiness(
            surface_config=surface_config,
            live_precondition_statuses={
                name: live.get(name, "unavailable")
                for name in surface_config.live_preconditions
            },
            component_states=_derive_component_states(surface_config, _REPO_ROOT),
        )
        # R8 overlay: an active surface whose gitignored producer artifact is
        # absent at request time downgrades — never a config error.
        if readiness.tier_status in _ACTIVE_STATUSES:
            missing_artifact = next(
                (
                    artifact
                    for artifact in surface_config.producer_artifacts
                    if not (_REPO_ROOT / artifact).is_file()
                ),
                None,
            )
            if missing_artifact is not None:
                readiness = readiness.model_copy(
                    update={
                        "tier_status": "not_graduated",
                        "basis": f"producer_artifact_missing:{missing_artifact}",
                    }
                )
        surfaces.append(readiness)

    overall = (
        "ok"
        if all(surface.tier_status in _ACTIVE_STATUSES for surface in surfaces)
        else "degraded"
    )
    return TierReadinessResponse(
        overall_status=overall,  # type: ignore[arg-type]
        registry_version=registry.registry_version,
        surfaces=surfaces,
        decision_supported=False,
    )
