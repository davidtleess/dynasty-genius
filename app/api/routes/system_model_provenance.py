"""DEBT-6 Slice 1 — T4: the read-only model-provenance route.

``GET /api/system/model-provenance`` assembles the checked-in registry
(T1 loader), the disk-truth layer (T3 pointer health, streamed hashing, scoped
unregistered scan), and the pure classifier (T2) into one descriptive response:
is every served model artifact the exact bytes David approved?

Fail-closed: any provenance configuration failure — registry absent, malformed,
schema-invalid, empty, duplicate ids, or an invalid explicit runtime env —
returns a sanitized 503 (`ModelProvenanceErrorResponse`). A provenance endpoint
with no source of truth must not report health (spec §3.6); the 503 body never
echoes exception text, absolute paths, or tracebacks. Descriptive only:
`decision_supported=false` at the root and every node; `load_verification_status`
stays ``not_verified`` (pointer provenance, never a resolver-selection claim).

Spec: docs/superpowers/specs/2026-07-01-debt6-model-provenance-slice1-design.md
Plan: docs/superpowers/plans/2026-07-01-debt6-model-provenance-slice1-plan.md
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.system_model_provenance_models import (
    ArtifactProvenance,
    ModelProvenanceErrorResponse,
    ModelProvenanceResponse,
    ProvenanceConfigError,
    inspect_registered_artifact,
    load_model_registry,
    resolve_runtime_environment,
    scan_unregistered_local_artifacts,
)

# Module-level so tests monkeypatch these; the handler reads them at request
# time (never captured as defaults).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_PATH = _REPO_ROOT / "app" / "config" / "model_registry.json"
_ENVIRON: Mapping[str, str] = os.environ

_SANITIZED_MESSAGE = "model provenance configuration unavailable"

router = APIRouter(prefix="/system", tags=["system"])


def _config_unavailable_503() -> JSONResponse:
    """One fixed 503 body for every config failure — no internal detail leaks."""

    body = ModelProvenanceErrorResponse(
        error="model_provenance_unavailable",
        message=_SANITIZED_MESSAGE,
        decision_supported=False,
    )
    return JSONResponse(status_code=503, content=body.model_dump())


def _overall_status(rows: list[ArtifactProvenance]) -> str:
    """Roll rows up per spec §3.4.

    Only ``active`` rows can drive ``blocked`` (candidate/parked deviations are
    visible but never block; a blocked SCAN row is ``active`` by construction —
    a pointer actively selecting unregistered bytes). Any non-info deviation,
    including from candidate/parked rows, is at least ``degraded``.
    """

    if any(not row.serving_allowed and row.promotion_status == "active" for row in rows):
        return "blocked"
    if any(row.severity != "info" for row in rows):
        return "degraded"
    return "ok"


@router.get(
    "/model-provenance",
    response_model=ModelProvenanceResponse,
    responses={503: {"model": ModelProvenanceErrorResponse}},
)
def get_model_provenance():
    try:
        registry = load_model_registry(registry_path=_REGISTRY_PATH)
        environment = resolve_runtime_environment(environ=_ENVIRON)
    except ProvenanceConfigError:
        return _config_unavailable_503()

    rows = [
        inspect_registered_artifact(
            entry=entry, repo_root=_REPO_ROOT, environment=environment
        )
        for entry in registry.artifacts
    ]
    rows.extend(
        scan_unregistered_local_artifacts(
            registry=registry, repo_root=_REPO_ROOT, environment=environment
        )
    )
    return ModelProvenanceResponse(
        overall_status=_overall_status(rows),  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        registry_version=registry.registry_version,
        artifacts=rows,
        decision_supported=False,
    )
