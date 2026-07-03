"""DEBT-6 Slice 1c — T3: the whole-app health route.

``GET /api/health`` is the first-glance light: three subsystem echoes (over
the existing system assemblies, in-process, guard-of-guards fail-closed) plus
the report-freshness layer, rolled up by criticality tier. Observability,
never a gate: ``ok | degraded`` with ``worst_affected_tier`` naming which leg
is hit; auxiliary noise cannot dim the app. Only the endpoint's OWN config
failure 503s (sanitized); a crashing subsystem degrades on a 200, never 500s.

Spec: docs/superpowers/specs/2026-07-02-debt6-health-rollup-slice1c-design.md
Plan: docs/superpowers/plans/2026-07-02-debt6-health-rollup-slice1c-plan.md
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.system_health_models import (
    DISCLAIMER,
    HealthConfigError,
    SubsystemHealth,
    SystemHealthErrorResponse,
    SystemHealthResponse,
    evaluate_report_freshness,
    load_report_freshness,
    read_report_artifact_facts,
    rollup_health_status,
)
from app.api.routes.system_tier_readiness import (
    _default_capture_health_status,
    _default_model_provenance_status,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _REPO_ROOT / "app" / "config" / "report_freshness.json"


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _default_tier_readiness_status() -> str:
    """Live tier-readiness overall status, computed in-process (fail-closed)."""

    try:
        from app.api.routes import system_tier_readiness as str_mod
        from app.api.routes.system_tier_readiness_models import load_tier_readiness

        registry = load_tier_readiness(
            registry_path=str_mod._REGISTRY_PATH, repo_root=str_mod._REPO_ROOT
        )
        response = str_mod.get_tier_readiness()
        if isinstance(response, JSONResponse):
            return "unavailable"
        del registry
        return response.overall_status
    except Exception:
        return "unavailable"


# Module-level seams so tests monkeypatch deterministically (R9).
_CLOCK: Callable[[], datetime] = _now_utc
_MODEL_PROVENANCE_ADAPTER: Callable[[], str] = _default_model_provenance_status
_CAPTURE_HEALTH_ADAPTER: Callable[[], str] = _default_capture_health_status
_TIER_READINESS_ADAPTER: Callable[[], str] = _default_tier_readiness_status

_SANITIZED_MESSAGE = "system health configuration unavailable"
_SUBSYSTEM_TIERS: dict[str, str] = {
    "model_provenance": "core_substrate",
    "capture_health": "core_substrate",
    "tier_readiness": "daily_diagnostics",
}
_TIER_RANK: dict[str, int] = {"core_substrate": 2, "daily_diagnostics": 1}

router = APIRouter(tags=["system"])


def _config_unavailable_503() -> JSONResponse:
    body = SystemHealthErrorResponse(
        error="system_health_unavailable",
        message=_SANITIZED_MESSAGE,
        decision_supported=False,
    )
    return JSONResponse(status_code=503, content=body.model_dump())


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    responses={503: {"model": SystemHealthErrorResponse}},
)
def get_system_health():
    try:
        config = load_report_freshness(config_path=_CONFIG_PATH)
    except HealthConfigError:
        return _config_unavailable_503()

    now = _CLOCK()
    facts = read_report_artifact_facts(config=config, repo_root=_REPO_ROOT)
    reports = evaluate_report_freshness(config=config, artifact_facts=facts, now=now)
    overall, worst_tier = rollup_health_status(reports=reports)

    subsystems: list[SubsystemHealth] = []
    adapters: list[tuple[str, Callable[[], str]]] = [
        ("model_provenance", _MODEL_PROVENANCE_ADAPTER),
        ("capture_health", _CAPTURE_HEALTH_ADAPTER),
        ("tier_readiness", _TIER_READINESS_ADAPTER),
    ]
    for subsystem_id, adapter in adapters:
        # Guard-of-guards: a crashing subsystem reads as unavailable and can
        # never 500 the health light or leak exception text (seed D).
        try:
            raw = adapter()
        except Exception:
            raw = "unavailable"
        status = raw if raw in ("ok", "unavailable") else "degraded"
        tier = _SUBSYSTEM_TIERS[subsystem_id]
        subsystems.append(
            SubsystemHealth(
                subsystem_id=subsystem_id,
                status=status,  # type: ignore[arg-type]
                basis=f"adapter_status:{status}",
                tier=tier,  # type: ignore[arg-type]
                decision_supported=False,
            )
        )
        if status != "ok":
            overall = "degraded"
            if _TIER_RANK[tier] > _TIER_RANK.get(worst_tier or "", 0):
                worst_tier = tier

    return SystemHealthResponse(
        overall_status=overall,  # type: ignore[arg-type]
        worst_affected_tier=worst_tier,  # type: ignore[arg-type]
        checked_at=now.isoformat(),
        config_version=config.config_version,
        subsystems=subsystems,
        reports=reports,
        disclaimer=DISCLAIMER,  # type: ignore[arg-type]
        decision_supported=False,
    )
