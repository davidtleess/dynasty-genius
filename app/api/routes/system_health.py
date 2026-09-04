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
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.system_health_models import (
    DISCLAIMER,
    BundleVsCheckout,
    CheckoutVsOrigin,
    HealthConfigError,
    ServedBundleFacts,
    SubsystemHealth,
    SystemHealthErrorResponse,
    SystemHealthResponse,
    evaluate_report_freshness,
    load_report_freshness,
    read_report_artifact_facts,
    rollup_health_status,
)
from app.api.routes.system_tier_readiness import (
    _default_model_provenance_status,
)
from app.services.served_bundle import bundle_vs_checkout, checkout_vs_origin

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _REPO_ROOT / "app" / "config" / "report_freshness.json"


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _default_tier_readiness_status():
    """Live tier-readiness status AND the reason, computed in-process (fail-closed).

    Returns ``(status, reason)``. The reason names the surfaces that are not ok and
    quotes each one's own ``basis`` — which is a required non-empty field precisely
    so a rollup can never launder it into silence. Previously this returned the bare
    overall status and the health light rendered ``adapter_status:degraded``, which
    restates the status and says nothing about what to do.
    """

    try:
        from app.api.routes import system_tier_readiness as str_mod

        response = str_mod.get_tier_readiness()
        if isinstance(response, JSONResponse):
            return "unavailable", "tier_readiness_route_unavailable"
        status = response.overall_status
        if status == "ok":
            return status, f"all {len(response.surfaces)} surfaces ready"
        blockers = [
            f"{surface.surface_id}: {surface.basis}"
            for surface in response.surfaces
            if surface.tier_status != "ok"
        ]
        return status, ("; ".join(blockers) if blockers else "no surface named a reason")
    except Exception:
        return "unavailable", "tier_readiness_uncomputable"


def _store_reason(store: Any) -> str:
    """Say WHY one capture store is degraded, in facts a person can act on.

    A store degrades on any of: missing capture days, staleness, sub-floor row
    density, or a class-B caveat. Reporting only the word "degraded" — or only the
    caveat list, which is empty in the common case — hides the one thing worth
    knowing. `model_forward_capture` reads degraded today solely because a single
    day (2026-08-12) never captured, and that one gap is what blocks two surfaces
    downstream; a message that does not name the date cannot be acted on.
    """
    bits: list[str] = []
    timeline = getattr(store, "timeline", None)
    missing_count = getattr(timeline, "missing_dates_count", 0) or 0
    if missing_count:
        ranges = getattr(timeline, "missing_ranges", []) or []
        dates = ", ".join(
            r.from_date if r.from_date == r.to_date else f"{r.from_date}..{r.to_date}"
            for r in ranges[:4]
        )
        expected = getattr(timeline, "expected_days", None)
        scope = f"{missing_count} of {expected} days" if expected else f"{missing_count} days"
        bits.append(f"missing {scope}" + (f" ({dates})" if dates else ""))
    staleness = getattr(store, "staleness", None)
    if getattr(staleness, "stale", False):
        bits.append(f"stale since {getattr(staleness, 'last_capture_date', 'unknown')}")
    density = getattr(store, "density", None)
    sub_floor = getattr(density, "sub_floor_dates", []) or []
    if sub_floor:
        bits.append(f"{len(sub_floor)} days below the {getattr(density, 'floor_pct', '?')}% row floor")
    if getattr(store, "caveats", None):
        bits.append(", ".join(store.caveats))
    return "; ".join(bits) if bits else "degraded (no sub-signal named it)"


def _default_capture_health_status_with_reason():
    """Live capture-health status AND the reason (fail-closed).

    Names the degraded stores and their own caveats instead of collapsing every
    store in the system to one word.
    """

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
        degraded = [store for store in stores if store.store_status == "degraded"]
        if not degraded:
            return "ok", f"all {len(stores)} capture stores healthy"
        return "degraded", f"{len(degraded)} of {len(stores)} stores degraded — " + "; ".join(
            f"{store.store_id}: {_store_reason(store)}" for store in degraded
        )
    except Exception:
        return "unavailable", "capture_health_uncomputable"


# Module-level seams so tests monkeypatch deterministically (R9).
_CLOCK: Callable[[], datetime] = _now_utc
_MODEL_PROVENANCE_ADAPTER: Callable[[], str] = _default_model_provenance_status
_CAPTURE_HEALTH_ADAPTER: Callable[[], Any] = _default_capture_health_status_with_reason
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

    # DG-121: the two facts about what David is actually looking at. Guard-of-
    # guards, the same rule the subsystem adapters follow: a crashing check
    # reads as "nothing established" and can never 500 the health light or leak
    # a filesystem path. Failing EMPTY is the point — the defect this replaces
    # was silence that read as health.
    try:
        bundle_facts = BundleVsCheckout(**bundle_vs_checkout())
    except Exception:
        bundle_facts = BundleVsCheckout(
            manifest_present=False,
            manifest_source_sha=None,
            manifest_source_dirty=None,
            manifest_built_at=None,
            manifest_sha_known_to_repo=None,
            head_sha=None,
            sha_matches_head=None,
            commits_head_ahead_of_bundle=None,
        )
    try:
        origin_facts = CheckoutVsOrigin(**checkout_vs_origin())
    except Exception:
        origin_facts = CheckoutVsOrigin(
            head_sha=None,
            remote_ref=None,
            remote_sha=None,
            commits_behind_remote=None,
            remote_last_fetched_at=None,
        )
    served_bundle = ServedBundleFacts(
        bundle_vs_checkout=bundle_facts, checkout_vs_origin=origin_facts
    )

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
        # Adapters may return a bare status (legacy seam, still honoured so tests and
        # any other caller keep working) or `(status, reason)`. The reason is the
        # point: `adapter_status:degraded` restated the status and named nothing, so
        # the light said "something is wrong" and refused to say what — unreadable
        # after a few mornings, which is worse than no light.
        if isinstance(raw, tuple) and len(raw) == 2:
            raw_status, reason = str(raw[0]), str(raw[1])
        else:
            raw_status, reason = str(raw), ""
        status = raw_status if raw_status in ("ok", "unavailable") else "degraded"
        tier = _SUBSYSTEM_TIERS[subsystem_id]
        subsystems.append(
            SubsystemHealth(
                subsystem_id=subsystem_id,
                status=status,  # type: ignore[arg-type]
                basis=reason or f"adapter_status:{status}",
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
        served_bundle=served_bundle,
        disclaimer=DISCLAIMER,  # type: ignore[arg-type]
        decision_supported=False,
    )
