"""BUILD-1 Increment 1 — tier-readiness registry models and fail-closed loader.

T1 scope: strict Pydantic models (registry + response; no field or status value
can express `decision_supported=true`, and the R10 vocabulary ban applies to
model field/enum names themselves) and the fail-closed registry loader. The
readiness evaluator (T2), live adapters + route (T3), and CI tripwire + real
registry + OpenAPI (T4) are later tasks.

Tier-1 is DIAGNOSTIC grade: it never flips `decision_supported` — there is no
Tier-2 pathway constructible from these models by design.

Spec: docs/superpowers/specs/2026-07-02-build1-tier1-graduation-increment1-design.md
Plan: docs/superpowers/plans/2026-07-02-build1-tier1-graduation-increment1-plan.md
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

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
