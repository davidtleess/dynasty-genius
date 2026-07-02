"""BUILD-1 Increment 1 — tier-readiness registry models and fail-closed loader.

T1: strict Pydantic models (registry + response; no field or status value
can express `decision_supported=true`, and the R10 vocabulary ban applies to
model field/enum names themselves) and the fail-closed registry loader. The
live adapters + route (T3) and CI tripwire + real registry + OpenAPI (T4)
are later tasks. T2: the pure readiness evaluator.

Tier-1 is DIAGNOSTIC grade: it never flips `decision_supported` — there is no
Tier-2 pathway constructible from these models by design.

Spec: docs/superpowers/specs/2026-07-02-build1-tier1-graduation-increment1-design.md
Plan: docs/superpowers/plans/2026-07-02-build1-tier1-graduation-increment1-plan.md
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ComponentStatus = Literal["pass", "insufficient_data", "fail", "not_applicable"]
TierStatus = Literal[
    "diagnostic_grade_active",
    "diagnostic_grade_active_limited",
    "preconditions_degraded",
    "not_graduated",
]
OverallStatus = Literal["ok", "degraded"]

# Closed id sets: an unknown component or precondition in the checked-in
# registry is config corruption (fail-closed), not a silent no-op.
_KNOWN_COMPONENTS: frozenset[str] = frozenset(
    (
        "audit_hygiene",
        "deterministic_range_disclosure",
        "mif_breaker",
        "no_directive_copy",
    )
)
_KNOWN_PRECONDITIONS: frozenset[str] = frozenset(
    ("model_provenance_ok", "capture_health_ok")
)


class _Strict(BaseModel):
    """Reject unknown fields AND type coercion (the capture-health precedent)."""

    model_config = ConfigDict(extra="forbid", strict=True)


# --- registry (checked-in readiness declarations) ------------------------------


class GateComponentConfig(_Strict):
    """One gate component with its evidence references.

    ``optional`` gates R6 semantics: ``not_applicable`` is a legal runtime
    status ONLY for components declared optional; on a required component the
    evaluator treats it as ``fail`` — never a silent pass.
    """

    component: str
    evidence: list[str]
    expectation: str
    optional: bool = False


class TierSurfaceConfig(_Strict):
    """One surface's readiness declaration. ``ratified_date: null`` blocks any
    active status (R5 — David's DECIDE-1 stamp is structurally required)."""

    surface_id: str
    display_name: str
    declared_tier: Literal["tier_1_candidate"]
    route_ids: list[str]
    producer_artifacts: list[str]
    live_preconditions: list[str]
    gate_components: list[GateComponentConfig]
    ratified_by: str
    ratified_date: str | None


class TierReadinessRegistry(_Strict):
    registry_version: int
    surfaces: list[TierSurfaceConfig]


# --- response models ------------------------------------------------------------


class ComponentReadiness(_Strict):
    component: str
    component_status: ComponentStatus
    basis: str
    decision_supported: Literal[False]


class SurfaceReadiness(_Strict):
    """Runtime readiness for one surface. Root-level dormancy disclosure is
    mandatory (R2): the headline `_limited` status plus machine-readable
    counts, so a UI can never render an unqualified badge over dormant
    components."""

    surface_id: str
    display_name: str
    tier_status: TierStatus
    # Surface-level rollup reason — REQUIRED and non-empty (Codex T2 redline):
    # awaiting_david_ratification / precondition / defect reasons are
    # load-bearing and must never be omittable.
    basis: str = Field(min_length=1)
    components: list[ComponentReadiness]
    insufficient_data_count: int
    insufficient_data_components: list[str]
    all_components_evaluable: bool
    live_preconditions: dict[str, str]
    decision_supported: Literal[False]


class TierReadinessResponse(_Strict):
    overall_status: OverallStatus
    registry_version: int
    surfaces: list[SurfaceReadiness]
    decision_supported: Literal[False]


class TierReadinessErrorResponse(_Strict):
    error: str
    message: str
    decision_supported: Literal[False]


# --- loader (fail-closed) --------------------------------------------------------


class TierReadinessConfigError(Exception):
    """Raised when the checked-in tier-readiness registry cannot serve as truth.

    The route (T3) maps this family to a sanitized 503: a readiness endpoint
    whose own registry is broken must not report readiness.
    """


def _reject(reason: str) -> TierReadinessConfigError:
    return TierReadinessConfigError(f"tier readiness registry {reason}")


def _validate_evidence_path(surface_id: str, evidence: str) -> None:
    # Repo-relative POSIX only: backslashes, absolute paths, drive prefixes,
    # and any `..` segment are confinement violations (the R3-style guard).
    if "\\" in evidence:
        raise _reject(
            f"invalid for surface {surface_id!r}: evidence path {evidence!r} "
            "must be a POSIX relative path"
        )
    parts = PurePosixPath(evidence).parts
    if PurePosixPath(evidence).is_absolute() or (parts and parts[0].endswith(":")):
        raise _reject(
            f"invalid for surface {surface_id!r}: evidence path {evidence!r} "
            "must be relative"
        )
    if ".." in parts:
        raise _reject(
            f"invalid for surface {surface_id!r}: evidence path {evidence!r} "
            "must not escape the repo root"
        )


def load_tier_readiness(
    *, registry_path: Path, repo_root: Path
) -> TierReadinessRegistry:
    """Load and validate the checked-in tier-readiness registry.

    Fail-closed: absent, malformed, schema-invalid, empty, duplicate-id,
    unknown component/precondition id, or evidence-path-escaping registries
    raise :class:`TierReadinessConfigError`. Paths are injectable so tests
    never touch the real ``app/config``. Evidence EXISTENCE is a runtime
    concern (T3) — the loader confines paths lexically under ``repo_root``.
    """

    if not registry_path.exists():
        raise _reject(f"missing at {registry_path}")

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _reject(f"malformed JSON at {registry_path}: {exc}") from exc

    try:
        registry = TierReadinessRegistry.model_validate(raw)
    except ValidationError as exc:
        raise _reject(f"schema invalid at {registry_path}: {exc}") from exc

    if not registry.surfaces:
        raise _reject(f"declares an empty surfaces list at {registry_path}")

    seen_surfaces: set[str] = set()
    for surface in registry.surfaces:
        if surface.surface_id in seen_surfaces:
            raise _reject(f"has duplicate surface_id {surface.surface_id!r}")
        seen_surfaces.add(surface.surface_id)

        # A registered surface declaring no routes, no live guards, no gate
        # components, or evidence-free components is a false-green vacuum:
        # it could "graduate" while asserting nothing (Codex T1 hold).
        if not surface.route_ids:
            raise _reject(
                f"declares an empty route_ids list on surface "
                f"{surface.surface_id!r}"
            )
        if not surface.live_preconditions:
            raise _reject(
                f"declares an empty live_preconditions list on surface "
                f"{surface.surface_id!r}"
            )
        if not surface.gate_components:
            raise _reject(
                f"declares an empty gate_components list on surface "
                f"{surface.surface_id!r}"
            )

        seen_preconditions: set[str] = set()
        for precondition in surface.live_preconditions:
            if precondition not in _KNOWN_PRECONDITIONS:
                raise _reject(
                    f"has unknown live precondition {precondition!r} on "
                    f"surface {surface.surface_id!r}"
                )
            if precondition in seen_preconditions:
                raise _reject(
                    f"has duplicate live precondition {precondition!r} on "
                    f"surface {surface.surface_id!r}"
                )
            seen_preconditions.add(precondition)

        seen_components: set[str] = set()
        for component in surface.gate_components:
            if component.component not in _KNOWN_COMPONENTS:
                raise _reject(
                    f"has unknown gate component {component.component!r} on "
                    f"surface {surface.surface_id!r}"
                )
            if component.component in seen_components:
                raise _reject(
                    f"has duplicate gate component {component.component!r} on "
                    f"surface {surface.surface_id!r}"
                )
            seen_components.add(component.component)
            if not component.evidence:
                raise _reject(
                    f"declares an empty evidence list for component "
                    f"{component.component!r} on surface {surface.surface_id!r}"
                )
            for evidence in component.evidence:
                _validate_evidence_path(surface.surface_id, evidence)
                resolved = (repo_root / evidence).resolve()
                if not resolved.is_relative_to(repo_root.resolve()):
                    raise _reject(
                        f"invalid for surface {surface.surface_id!r}: evidence "
                        f"path {evidence!r} resolves outside the repo root"
                    )
    return registry


# --- T2: pure readiness evaluator (spec §3.1–§3.3, DECIDE-1 option (a)-as-amended)

_KNOWN_COMPONENT_STATUSES: frozenset[str] = frozenset(
    ("pass", "insufficient_data", "fail", "not_applicable")
)


def evaluate_surface_readiness(
    *,
    surface_config: TierSurfaceConfig,
    live_precondition_statuses: dict[str, str],
    component_states: dict[str, dict[str, str]],
) -> SurfaceReadiness:
    """Evaluate one surface's runtime tier status (pure — no disk, no adapters).

    Precedence (spec §3.1–§3.2b):
    1. Integrity cascade — ANY live precondition not ``ok`` wins outright:
       no diagnostic-grade metrics on top of degraded substrate.
    2. Component defects — first declared component that resolves to ``fail``
       (explicit fail, required ``not_applicable``, unknown status, or missing
       state — all fail-closed) drives ``not_graduated`` with a named basis.
    3. Ratification gate — ``ratified_date: null`` blocks activation even when
       every check passes (David's DECIDE-1 stamp is structurally required).
    4. Dormancy — any ``insufficient_data`` forces the ``_limited`` headline
       with root disclosure; plain active requires all components evaluable.
    """

    components: list[ComponentReadiness] = []
    first_defect_basis: str | None = None
    insufficient: list[str] = []

    for declared in surface_config.gate_components:
        state = component_states.get(declared.component)
        if state is None:
            status, basis = "fail", "component_state_missing"
            defect = f"component_state_missing:{declared.component}"
        else:
            raw_status = state.get("component_status", "")
            basis = state.get("basis", "")
            if raw_status not in _KNOWN_COMPONENT_STATUSES:
                status = "fail"
                basis = f"unknown component status {raw_status!r}: {basis}"
                defect = f"unknown_component_status:{declared.component}"
            elif raw_status == "not_applicable" and not declared.optional:
                # R6: not_applicable is legal only on optional components.
                status = "fail"
                defect = (
                    f"required_component_not_applicable:{declared.component}"
                )
            elif raw_status == "fail":
                status = "fail"
                defect = f"component_failed:{declared.component}"
            else:
                status = raw_status
                defect = None
        if status == "insufficient_data":
            insufficient.append(declared.component)
        if status == "fail" and first_defect_basis is None:
            first_defect_basis = defect
        components.append(
            ComponentReadiness(
                component=declared.component,
                component_status=status,  # type: ignore[arg-type]
                basis=basis,
                decision_supported=False,
            )
        )

    degraded_precondition = next(
        (
            name
            for name in surface_config.live_preconditions
            if live_precondition_statuses.get(name) != "ok"
        ),
        None,
    )

    if degraded_precondition is not None:
        observed = live_precondition_statuses.get(degraded_precondition)
        tier_status = "preconditions_degraded"
        surface_basis = (
            f"live_precondition_not_ok:{degraded_precondition}={observed}"
        )
    elif first_defect_basis is not None:
        tier_status = "not_graduated"
        surface_basis = first_defect_basis
    elif surface_config.ratified_date is None:
        tier_status = "not_graduated"
        surface_basis = "awaiting_david_ratification"
    elif insufficient:
        tier_status = "diagnostic_grade_active_limited"
        surface_basis = "readiness_active_with_insufficient_data"
    else:
        tier_status = "diagnostic_grade_active"
        surface_basis = "all_readiness_checks_passed"

    return SurfaceReadiness(
        surface_id=surface_config.surface_id,
        display_name=surface_config.display_name,
        tier_status=tier_status,  # type: ignore[arg-type]
        basis=surface_basis,
        components=components,
        insufficient_data_count=len(insufficient),
        insufficient_data_components=insufficient,
        all_components_evaluable=not insufficient,
        live_preconditions=dict(live_precondition_statuses),
        decision_supported=False,
    )
