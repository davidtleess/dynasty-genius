"""T1 RED: model-provenance registry models, loader, and env resolver.

These tests are intentionally fixture-only. They use temp registry paths and an
injected environment mapping, never the checked-in app/config registry and never
gitignored app/data model artifacts. T1 covers only models, registry loading,
and environment resolution; classifier, pointer health, route wiring, and
OpenAPI generation belong to later slices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError


def _models():
    import app.api.routes.system_model_provenance_models as models

    return models


def _registry_artifact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = {
        "artifact_id": "engine_a:QB",
        "path": "QB_model.pkl",
        "path_resolution": "latest_run_dir",
        "governing_pointer": "app/data/models/latest.json",
        "sha256": "a" * 64,
        "kind": "tracked_seed",
        "promotion_status": "active",
        "required_by_env": ["development", "ci", "serving", "production"],
        "allow_local_override": False,
        "approved_by": "David",
        "approved_date": "2026-07-01",
        "updated_by_commit": "9fdac6a",
    }
    if overrides:
        artifact.update(overrides)
    return artifact


def _registry_body(artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "registry_version": 1,
        "artifacts": [artifact or _registry_artifact()],
    }


def _write_registry(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_registry_loader_reads_injected_temp_registry_without_app_config_dependency(
    tmp_path: Path,
) -> None:
    models = _models()
    registry_path = _write_registry(tmp_path / "model_registry.json", _registry_body())

    registry = models.load_model_registry(registry_path=registry_path)

    assert isinstance(registry, models.ModelRegistry)
    assert registry.registry_version == 1
    assert len(registry.artifacts) == 1
    artifact = registry.artifacts[0]
    assert artifact.artifact_id == "engine_a:QB"
    assert artifact.path == "QB_model.pkl"
    assert artifact.path_resolution == "latest_run_dir"
    assert artifact.governing_pointer == "app/data/models/latest.json"
    assert artifact.sha256 == "a" * 64
    assert artifact.kind == "tracked_seed"
    assert artifact.promotion_status == "active"
    assert artifact.required_by_env == [
        "development",
        "ci",
        "serving",
        "production",
    ]
    assert artifact.allow_local_override is False
    assert artifact.approved_by == "David"
    assert artifact.approved_date == "2026-07-01"
    assert artifact.updated_by_commit == "9fdac6a"


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (
            lambda path: path.write_text(
                json.dumps(
                    _registry_body(
                        _registry_artifact({"kind": "not_a_supported_kind"})
                    )
                ),
                encoding="utf-8",
            ),
            "schema",
        ),
    ],
)
def test_registry_loader_raises_typed_error_for_missing_malformed_or_schema_invalid(
    tmp_path: Path,
    writer,
    message_fragment: str,
) -> None:
    models = _models()
    registry_path = tmp_path / "model_registry.json"
    writer(registry_path)

    with pytest.raises(models.ModelRegistryLoadError) as exc_info:
        models.load_model_registry(registry_path=registry_path)

    assert message_fragment in str(exc_info.value).lower()


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({"DG_RUNTIME_ENV": "serving", "CI": "true"}, "serving"),
        ({"DG_RUNTIME_ENV": "production"}, "production"),
        ({"DG_RUNTIME_ENV": "ci"}, "ci"),
        ({"DG_RUNTIME_ENV": "development", "CI": "true"}, "development"),
        ({"CI": "true"}, "ci"),
        ({"CI": "1"}, "ci"),
        ({"CI": "false"}, "ci"),
        ({}, "development"),
    ],
)
def test_environment_resolution_uses_explicit_runtime_then_truthy_ci_else_development(
    environ: dict[str, str],
    expected: str,
) -> None:
    models = _models()

    assert models.resolve_runtime_environment(environ=environ) == expected


def test_registry_artifact_locks_defaults_nullable_hash_and_enums() -> None:
    models = _models()

    literal_artifact = models.RegistryArtifact.model_validate(
        _registry_artifact(
            {
                "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
                "path_resolution": "literal",
                "governing_pointer": None,
                "sha256": None,
                "kind": "local_operational",
                "promotion_status": "candidate",
                "required_by_env": ["serving"],
            }
        )
    )

    assert literal_artifact.path_resolution == "literal"
    assert literal_artifact.governing_pointer is None
    assert literal_artifact.sha256 is None
    assert literal_artifact.allow_local_override is False

    with pytest.raises(ValidationError):
        models.RegistryArtifact.model_validate(
            _registry_artifact({"path_resolution": "root_model_dir"})
        )
    with pytest.raises(ValidationError):
        models.RegistryArtifact.model_validate(_registry_artifact({"kind": "ad_hoc"}))
    with pytest.raises(ValidationError):
        models.RegistryArtifact.model_validate(
            _registry_artifact({"promotion_status": "promoted"})
        )


def test_response_models_lock_status_enums_and_decision_supported_false() -> None:
    models = _models()

    artifact = models.ArtifactProvenance.model_validate(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "expected_kind": "local_operational",
            "promotion_status": "active",
            "observed_status": "expected_hash_missing",
            "pointer_status": "pointer_missing",
            "severity": "caveat",
            "load_verification_status": "not_verified",
            "serving_allowed": True,
            "decision_supported": False,
        }
    )
    response = models.ModelProvenanceResponse.model_validate(
        {
            "overall_status": "degraded",
            "environment": "ci",
            "registry_version": 1,
            "artifacts": [artifact.model_dump()],
            "decision_supported": False,
        }
    )
    error = models.ModelProvenanceErrorResponse.model_validate(
        {
            "error": "model_registry_unavailable",
            "message": "registry malformed",
            "decision_supported": False,
        }
    )

    assert response.artifacts[0].observed_status == "expected_hash_missing"
    assert response.artifacts[0].pointer_status == "pointer_missing"
    assert response.artifacts[0].load_verification_status == "not_verified"
    assert error.decision_supported is False

    with pytest.raises(ValidationError):
        models.ArtifactProvenance.model_validate(
            artifact.model_dump() | {"observed_status": "unverifiable"}
        )
    with pytest.raises(ValidationError):
        models.ArtifactProvenance.model_validate(
            artifact.model_dump() | {"pointer_status": "resolver_selected"}
        )
    with pytest.raises(ValidationError):
        models.ArtifactProvenance.model_validate(
            artifact.model_dump() | {"load_verification_status": "assumed"}
        )
    with pytest.raises(ValidationError):
        models.ModelProvenanceResponse.model_validate(
            response.model_dump() | {"overall_status": "healthy"}
        )


@pytest.mark.parametrize(
    ("model_name", "valid_payload"),
    [
        ("RegistryArtifact", _registry_artifact()),
        ("ModelRegistry", _registry_body()),
        (
            "ArtifactProvenance",
            {
                "artifact_id": "engine_b:qb_v2",
                "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
                "expected_kind": "local_operational",
                "promotion_status": "active",
                "observed_status": "ok",
                "pointer_status": "referenced",
                "severity": "info",
                "load_verification_status": "not_verified",
                "serving_allowed": True,
                "decision_supported": False,
            },
        ),
        (
            "ModelProvenanceResponse",
            {
                "overall_status": "ok",
                "environment": "development",
                "registry_version": 1,
                "artifacts": [],
                "decision_supported": False,
            },
        ),
        (
            "ModelProvenanceErrorResponse",
            {
                "error": "model_registry_unavailable",
                "message": "registry missing",
                "decision_supported": False,
            },
        ),
    ],
)
def test_all_models_forbid_unknown_fields(
    model_name: str,
    valid_payload: dict[str, Any],
) -> None:
    models = _models()
    model_type = getattr(models, model_name)

    with pytest.raises(ValidationError):
        model_type.model_validate(valid_payload | {"recommendation": "trust this"})


@pytest.mark.parametrize(
    ("model_name", "valid_payload"),
    [
        (
            "ArtifactProvenance",
            {
                "artifact_id": "engine_b:qb_v2",
                "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
                "expected_kind": "local_operational",
                "promotion_status": "active",
                "observed_status": "ok",
                "pointer_status": "referenced",
                "severity": "info",
                "load_verification_status": "not_verified",
                "serving_allowed": True,
                "decision_supported": False,
            },
        ),
        (
            "ModelProvenanceResponse",
            {
                "overall_status": "ok",
                "environment": "development",
                "registry_version": 1,
                "artifacts": [],
                "decision_supported": False,
            },
        ),
        (
            "ModelProvenanceErrorResponse",
            {
                "error": "model_registry_unavailable",
                "message": "registry missing",
                "decision_supported": False,
            },
        ),
    ],
)
def test_decision_supported_is_literal_false(
    model_name: str,
    valid_payload: dict[str, Any],
) -> None:
    models = _models()
    model_type = getattr(models, model_name)

    with pytest.raises(ValidationError):
        model_type.model_validate(valid_payload | {"decision_supported": True})
