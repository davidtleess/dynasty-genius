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


class ProvenanceConfigError(Exception):
    """Base for provenance configuration failures (registry + runtime env).

    One family so the route (T4) can map any of them to a fail-closed 503: a
    provenance endpoint whose own configuration is broken must not report health.
    """


class ModelRegistryLoadError(ProvenanceConfigError):
    """Raised when the checked-in registry is missing, malformed, or invalid.

    The route maps this to a 503: a provenance endpoint with no source of truth
    must not report health (spec §3.6).
    """


class RuntimeEnvironmentError(ProvenanceConfigError):
    """Raised when ``DG_RUNTIME_ENV`` is set to a value outside the valid set.

    An explicitly-set-but-invalid runtime env is configuration corruption, not
    "unset": it must fail closed rather than silently demote a misconfigured
    serving host to ``development`` (spec §3.1, Codex T1 R7).
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

    if "DG_RUNTIME_ENV" in environ:
        explicit = environ["DG_RUNTIME_ENV"]
        if explicit not in _VALID_ENVIRONMENTS:
            raise RuntimeEnvironmentError(
                "DG_RUNTIME_ENV is set to an invalid value "
                f"{explicit!r}; expected one of {sorted(_VALID_ENVIRONMENTS)}"
            )
        return explicit
    if "CI" in environ:
        return "ci"
    return "development"


# --- classifier (pure; spec §3.2–§3.4) ---------------------------------------

_SEVERITY_ORDER: dict[str, int] = {"info": 0, "caveat": 1, "integrity": 2}
_SERVING_ENVS: frozenset[str] = frozenset(("serving", "production"))
_BROKEN_POINTER: frozenset[str] = frozenset(
    ("pointer_missing", "pointer_malformed", "pointer_mismatch")
)


def _max_severity(a: str, b: str) -> str:
    return a if _SEVERITY_ORDER[a] >= _SEVERITY_ORDER[b] else b


def _serving_active_required(entry: RegistryArtifact, environment: str) -> bool:
    """True when this artifact is the ACTIVE, required model in a serving env.

    The only context where a deviation must hard-block: a mismatched/absent/
    unverifiable/pointer-broken *active* model that a serving host is required to
    load is unapproved serving reality, not a caveat.
    """

    return (
        entry.promotion_status == "active"
        and environment in _SERVING_ENVS
        and environment in entry.required_by_env
    )


def _observed_severity(
    entry: RegistryArtifact, observed_status: str, environment: str
) -> tuple[str, bool]:
    """Map an observed_status to (severity, serving_allowed) — the env's judgment."""

    if observed_status == "ok":
        return "info", True
    if observed_status == "hash_mismatch":
        # Tracked bytes differ from the approved hash: block even in dev, unless
        # an explicit dev-only override is set (the only tracked escape).
        if entry.allow_local_override and environment == "development":
            return "caveat", True
        return "integrity", False
    if observed_status == "missing_required":
        return "integrity", False
    if observed_status == "local_artifact_missing_ci":
        return "caveat", True
    if observed_status == "local_override":
        # Local bytes differ from last-promoted expected. Info in dev; unapproved
        # serving reality (integrity) only for an active+required serving model.
        if environment == "development":
            return "info", True
        if _serving_active_required(entry, environment):
            return "integrity", False
        return "caveat", True
    if observed_status == "expected_hash_missing":
        # No approved hash to verify against: never ok. Blocks an active+required
        # serving model; a caveat elsewhere (candidate/parked, ci/dev absence).
        if _serving_active_required(entry, environment):
            return "integrity", False
        return "caveat", True
    # Defensive: an unmapped status must fail closed, not silently pass.
    return "integrity", False


def classify_artifact(
    *,
    entry: RegistryArtifact,
    artifact_present: bool,
    observed_hash: str | None,
    pointer_status: str = "referenced",
    environment: str,
) -> ArtifactProvenance:
    """Classify one registered artifact into provenance (pure — no disk I/O).

    Derives ``observed_status`` (the technical fact) from the registry entry and
    the observed file facts, then maps ``severity`` + ``serving_allowed`` (the
    environment's judgment) with the fail-closed overlays of spec §3.4. The
    governing-pointer health (``pointer_status``) is supplied by the T3 readers;
    here it only gates severity: a broken pointer means the bytes may be valid
    but unreachable/misselected, so an active+required serving artifact blocks
    even when ``observed_status == "ok"``. ``load_verification_status`` is always
    ``"not_verified"`` in Slice 1 (pointer provenance, not proven resolver load).
    """

    # Fail closed on a bad caller: an invalid environment must not classify as
    # healthy (T1's resolver guards the HTTP path, but this pure function is
    # public and must guard itself — Codex T2 R8).
    if environment not in _VALID_ENVIRONMENTS:
        raise RuntimeEnvironmentError(
            f"classify_artifact received an invalid environment {environment!r}; "
            f"expected one of {sorted(_VALID_ENVIRONMENTS)}"
        )

    # observed_status — the technical fact
    if entry.sha256 is None:
        observed_status = "expected_hash_missing"
    elif not artifact_present:
        if entry.kind == "tracked_seed" or environment in entry.required_by_env:
            observed_status = "missing_required"
        else:
            observed_status = "local_artifact_missing_ci"
    elif observed_hash == entry.sha256:
        observed_status = "ok"
    elif entry.kind == "tracked_seed":
        observed_status = "hash_mismatch"
    else:
        observed_status = "local_override"

    # severity + serving_allowed — the environment's judgment
    severity, serving_allowed = _observed_severity(entry, observed_status, environment)

    # pointer clean-gate overlay (§3.4): valid bytes behind a broken governing
    # pointer are not clean. Hard-block only for an active+required serving model;
    # elsewhere a broken (typically gitignored, ci/dev-absent) manifest is a caveat.
    if pointer_status in _BROKEN_POINTER:
        if _serving_active_required(entry, environment):
            severity, serving_allowed = "integrity", False
        else:
            severity = _max_severity(severity, "caveat")

    return ArtifactProvenance(
        artifact_id=entry.artifact_id,
        path=entry.path,
        expected_kind=entry.kind,
        promotion_status=entry.promotion_status,
        observed_status=observed_status,  # type: ignore[arg-type]
        pointer_status=pointer_status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        load_verification_status="not_verified",
        serving_allowed=serving_allowed,
        decision_supported=False,
    )
