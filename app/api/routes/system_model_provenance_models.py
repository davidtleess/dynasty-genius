"""DEBT-6 Slice 1 — model-provenance registry models, loader, and env resolver.

T1 scope: Pydantic v2 schema (all ``extra="forbid"`` so verdict-fields fail
closed), the checked-in-registry loader (fail-closed on missing/malformed/
schema-invalid), and runtime-environment resolution. Classifier, pointer
health, route wiring, and OpenAPI generation belong to later tasks.

Spec: docs/superpowers/specs/2026-07-01-debt6-model-provenance-slice1-design.md
Plan: docs/superpowers/plans/2026-07-01-debt6-model-provenance-slice1-plan.md
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

# --- shared enums ------------------------------------------------------------

PathResolution = Literal["literal", "latest_run_dir"]
ArtifactKind = Literal["tracked_seed", "local_operational"]
PromotionStatus = Literal["active", "candidate", "parked"]
ObservedStatus = Literal[
    "ok",
    "local_override",
    "unregistered_local",
    "hash_mismatch",
    "missing_required",
    "local_artifact_missing_ci",
    "expected_hash_missing",
]
PointerStatus = Literal[
    "referenced",
    "pointer_missing",
    "pointer_malformed",
    "pointer_mismatch",
    "not_applicable",
]
Severity = Literal["info", "caveat", "integrity"]
LoadVerificationStatus = Literal["not_verified", "verified"]
OverallStatus = Literal["ok", "degraded", "blocked"]
RuntimeEnvironment = Literal["development", "ci", "serving", "production"]

_VALID_ENVIRONMENTS: frozenset[str] = frozenset(
    ("development", "ci", "serving", "production")
)


class _Strict(BaseModel):
    """Base model: reject unknown fields so verdict-language cannot leak in."""

    model_config = ConfigDict(extra="forbid")


# --- registry (checked-in expected state) ------------------------------------


class RegistryArtifact(_Strict):
    """One declared model artifact in ``app/config/model_registry.json``.

    ``sha256`` is nullable: a ``null`` expected hash means "declared but not yet
    seeded" (T5 promotion assertion), which the classifier treats as
    ``expected_hash_missing`` — never ``ok``. ``path_resolution: latest_run_dir``
    means ``path`` is a filename resolved against ``governing_pointer``'s run dir.
    """

    artifact_id: str
    path: str
    path_resolution: PathResolution = "literal"
    governing_pointer: str | None = None
    sha256: str | None = None
    kind: ArtifactKind
    promotion_status: PromotionStatus
    required_by_env: list[str]
    allow_local_override: bool = False
    approved_by: str
    approved_date: str
    updated_by_commit: str


class ModelRegistry(_Strict):
    registry_version: int
    artifacts: list[RegistryArtifact]


# --- response (computed provenance) ------------------------------------------


class ArtifactProvenance(_Strict):
    artifact_id: str
    path: str
    expected_kind: ArtifactKind
    promotion_status: PromotionStatus
    observed_status: ObservedStatus
    pointer_status: PointerStatus
    severity: Severity
    load_verification_status: LoadVerificationStatus
    serving_allowed: bool
    decision_supported: Literal[False]


class ModelProvenanceResponse(_Strict):
    overall_status: OverallStatus
    environment: RuntimeEnvironment
    registry_version: int
    artifacts: list[ArtifactProvenance]
    decision_supported: Literal[False]


class ModelProvenanceErrorResponse(_Strict):
    error: str
    message: str
    decision_supported: Literal[False]


# --- loader (fail-closed) ----------------------------------------------------


class ModelRegistryLoadError(Exception):
    """Raised when the checked-in registry is missing, malformed, or invalid.

    The route maps this to a 503: a provenance endpoint with no source of truth
    must not report health (spec §3.6).
    """


def load_model_registry(*, registry_path: Path) -> ModelRegistry:
    """Load and validate the checked-in model registry.

    Fail-closed: an absent, malformed, or schema-invalid registry raises
    :class:`ModelRegistryLoadError` rather than returning a partial/empty
    registry. The path is injectable so tests never touch ``app/config``.
    """

    if not registry_path.exists():
        raise ModelRegistryLoadError(
            f"model registry missing at {registry_path}"
        )

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelRegistryLoadError(
            f"model registry malformed JSON at {registry_path}: {exc}"
        ) from exc

    try:
        return ModelRegistry.model_validate(raw)
    except ValidationError as exc:
        raise ModelRegistryLoadError(
            f"model registry schema invalid at {registry_path}: {exc}"
        ) from exc


# --- environment resolution --------------------------------------------------


def resolve_runtime_environment(*, environ: Mapping[str, str]) -> str:
    """Resolve the runtime environment (spec §3.1).

    Precedence: an explicit, recognized ``DG_RUNTIME_ENV`` wins; otherwise the
    mere PRESENCE of a ``CI`` variable (any value) resolves to ``ci`` — a
    fail-closed-safe default, since treating an ambiguous env as CI marks
    ``local_operational`` artifacts as expected-absent rather than
    unexpectedly-missing; otherwise ``development``.
    """

    explicit = environ.get("DG_RUNTIME_ENV")
    if explicit in _VALID_ENVIRONMENTS:
        return explicit
    if "CI" in environ:
        return "ci"
    return "development"
