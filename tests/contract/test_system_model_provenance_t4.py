"""T4 RED: system model-provenance route assembly.

These HTTP tests use temp registries and temp model roots only. They do not read
the real ``app/config/model_registry.json`` and do not depend on gitignored
model artifacts. T4 owns route wiring, response assembly, sanitized 503s, scan
row rollup, and OpenAPI exposure; model hashing/pointer details are covered by
T3 but exercised here end-to-end through ``GET /api/system/model-provenance``.

Concurrency is intentionally out of scope for this slice: hashes stream in
bounded chunks, and Dynasty Genius is a single-user product.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


def _route_module():
    from app.api.routes import system_model_provenance

    return system_model_provenance


def _client_with_temp_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    registry_path: Path,
    repo_root: Path,
    environ: dict[str, str] | None = None,
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(route, "_ENVIRON", environ if environ is not None else {})
    from app.main import app

    return TestClient(app)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bytes(path: Path, payload: bytes = b"model-bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _write_registry(path: Path, artifacts: list[dict[str, Any]]) -> Path:
    return _write_json(path, {"registry_version": 1, "artifacts": artifacts})


def _artifact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
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
        "updated_by_commit": "9ff5f86",
    }
    if overrides:
        body.update(overrides)
    return body


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _artifact_by_id(body: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    for artifact in body["artifacts"]:
        if artifact["artifact_id"] == artifact_id:
            return artifact
    raise AssertionError(f"missing artifact_id {artifact_id}")


def test_model_provenance_route_assembles_ok_registered_artifacts_and_openapi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine_a_path = _write_bytes(
        tmp_path / "app/data/models/runs/20260502T153931Z/QB_model.pkl",
        b"engine-a-qb",
    )
    literal_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
        b"engine-b-qb",
    )
    _write_json(
        tmp_path / "app/data/models/latest.json",
        {
            "model_version": "engine_a_v1",
            "run_dir": "app/data/models/runs/20260502T153931Z",
            "validation_report": "app/data/models/runs/20260502T153931Z/report.json",
        },
    )
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"},
    )
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact({"sha256": _sha(engine_a_path)}),
            _artifact(
                {
                    "artifact_id": "engine_b:QB_v2",
                    "path": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
                    "sha256": _sha(literal_path),
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            ),
            _artifact(
                {
                    "artifact_id": "standalone:candidate",
                    "path": "app/data/models/candidate.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": None,
                    "sha256": None,
                    "kind": "local_operational",
                    "promotion_status": "candidate",
                    "required_by_env": ["serving"],
                }
            ),
        ],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "serving"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["environment"] == "serving"
    assert body["registry_version"] == 1
    assert body["decision_supported"] is False
    _assert_decision_supported_false_recursive(body)
    assert all(
        artifact["load_verification_status"] == "not_verified"
        for artifact in body["artifacts"]
    )
    assert _artifact_by_id(body, "engine_a:QB") == {
        "artifact_id": "engine_a:QB",
        "path": "app/data/models/runs/20260502T153931Z/QB_model.pkl",
        "expected_kind": "tracked_seed",
        "promotion_status": "active",
        "observed_status": "ok",
        "pointer_status": "referenced",
        "severity": "info",
        "load_verification_status": "not_verified",
        "serving_allowed": True,
        "decision_supported": False,
    }
    assert _artifact_by_id(body, "engine_b:QB_v2")["observed_status"] == "ok"
    assert _artifact_by_id(body, "standalone:candidate")["pointer_status"] == (
        "not_applicable"
    )

    schema = client.get("/openapi.json").json()
    path_spec = schema["paths"]["/api/system/model-provenance"]["get"]
    assert path_spec["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("ModelProvenanceResponse")
    assert path_spec["responses"]["503"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("ModelProvenanceErrorResponse")


def test_model_provenance_ci_shape_is_200_degraded_not_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact(
                {
                    "artifact_id": "engine_b:QB_v2",
                    "path": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
                    "sha256": None,
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            ),
            _artifact(
                {
                    "artifact_id": "head_a:TE_v3",
                    "path": "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": "app/data/models/head_a/v3_manifest.json",
                    "sha256": "b" * 64,
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            ),
        ],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"CI": "true"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "ci"
    assert body["overall_status"] == "degraded"
    statuses = {row["artifact_id"]: row for row in body["artifacts"]}
    assert statuses["engine_b:QB_v2"]["observed_status"] == "expected_hash_missing"
    assert statuses["engine_b:QB_v2"]["pointer_status"] == "pointer_missing"
    assert statuses["engine_b:QB_v2"]["serving_allowed"] is True
    assert statuses["head_a:TE_v3"]["observed_status"] == "local_artifact_missing_ci"
    assert statuses["head_a:TE_v3"]["severity"] == "caveat"


def test_model_provenance_scan_rows_are_appended_and_roll_up_by_severity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/current/qb_v2.pkl",
        b"registered",
    )
    referenced_unregistered = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/current/wr_v2.pkl",
        b"referenced-unregistered",
    )
    unreferenced_sibling = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/current/te_v2.pkl",
        b"unreferenced-sibling",
    )
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {
            "QB": "app/data/models/engine_b/runs/current/qb_v2.pkl",
            "WR": "app/data/models/engine_b/runs/current/wr_v2.pkl",
        },
    )
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact(
                {
                    "artifact_id": "engine_b:QB_v2",
                    "path": "app/data/models/engine_b/runs/current/qb_v2.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
                    "sha256": _sha(registered_path),
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            )
        ],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "production"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "blocked"
    by_path = {row["path"]: row for row in body["artifacts"]}
    referenced_row = by_path[str(referenced_unregistered.relative_to(tmp_path))]
    assert referenced_row["artifact_id"].startswith("unregistered:")
    assert referenced_row["observed_status"] == "unregistered_local"
    assert referenced_row["pointer_status"] == "referenced"
    assert referenced_row["severity"] == "integrity"
    assert referenced_row["serving_allowed"] is False
    sibling_row = by_path[str(unreferenced_sibling.relative_to(tmp_path))]
    assert sibling_row["pointer_status"] == "not_applicable"
    assert sibling_row["severity"] == "info"
    assert sibling_row["serving_allowed"] is True


def test_model_provenance_referenced_unregistered_in_ci_degrades_but_does_not_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/current/qb_v2.pkl",
        b"registered",
    )
    _write_bytes(tmp_path / "app/data/models/engine_b/runs/current/wr_v2.pkl")
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {
            "QB": "app/data/models/engine_b/runs/current/qb_v2.pkl",
            "WR": "app/data/models/engine_b/runs/current/wr_v2.pkl",
        },
    )
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact(
                {
                    "artifact_id": "engine_b:QB_v2",
                    "path": "app/data/models/engine_b/runs/current/qb_v2.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
                    "sha256": _sha(registered_path),
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            )
        ],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"CI": "true"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    scan_rows = [
        row for row in body["artifacts"] if row["observed_status"] == "unregistered_local"
    ]
    assert len(scan_rows) == 1
    assert scan_rows[0]["severity"] == "caveat"
    assert scan_rows[0]["serving_allowed"] is True


@pytest.mark.parametrize(
    ("artifact_overrides", "expected_status", "expected_overall"),
    [
        ({"sha256": "b" * 64}, "hash_mismatch", "blocked"),
        ({}, "missing_required", "blocked"),
        ({"sha256": None}, "expected_hash_missing", "blocked"),
    ],
)
def test_model_provenance_registered_integrity_failures_block_at_http_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_overrides: dict[str, Any],
    expected_status: str,
    expected_overall: str,
) -> None:
    if expected_status != "missing_required":
        model_path = _write_bytes(
            tmp_path / "app/data/models/runs/20260502T153931Z/QB_model.pkl",
            b"engine-a-qb",
        )
        if "sha256" not in artifact_overrides:
            artifact_overrides["sha256"] = _sha(model_path)
    _write_json(
        tmp_path / "app/data/models/latest.json",
        {
            "model_version": "engine_a_v1",
            "run_dir": "app/data/models/runs/20260502T153931Z",
            "validation_report": "report.json",
        },
    )
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact(
                {
                    **artifact_overrides,
                    "kind": "tracked_seed",
                    "required_by_env": ["development", "ci", "serving", "production"],
                }
            )
        ],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "serving"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == expected_overall
    artifact = _artifact_by_id(body, "engine_a:QB")
    assert artifact["observed_status"] == expected_status
    assert artifact["severity"] == "integrity"
    assert artifact["serving_allowed"] is False


def test_model_provenance_candidate_and_parked_blocked_rows_never_drive_overall_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_path = _write_bytes(tmp_path / "app/data/models/candidate.pkl", b"candidate")
    parked_path = _write_bytes(tmp_path / "app/data/models/parked.pkl", b"parked")
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [
            _artifact(
                {
                    "artifact_id": "candidate:bad_hash",
                    "path": "app/data/models/candidate.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": None,
                    "sha256": "c" * 64,
                    "kind": "local_operational",
                    "promotion_status": "candidate",
                    "required_by_env": ["serving"],
                }
            ),
            _artifact(
                {
                    "artifact_id": "parked:hash_pending",
                    "path": "app/data/models/parked.pkl",
                    "path_resolution": "literal",
                    "governing_pointer": None,
                    "sha256": None,
                    "kind": "local_operational",
                    "promotion_status": "parked",
                    "required_by_env": ["serving"],
                }
            ),
        ],
    )
    assert _sha(candidate_path) != "c" * 64
    assert parked_path.is_file()
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "serving"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert _artifact_by_id(body, "candidate:bad_hash")["severity"] == "caveat"
    assert _artifact_by_id(body, "candidate:bad_hash")["serving_allowed"] is True
    assert _artifact_by_id(body, "parked:hash_pending")["severity"] == "caveat"


@pytest.mark.parametrize(
    "pointer_body",
    [
        None,
        {},
        {"model_version": "engine_a_v1", "run_dir": ""},
        {
            "model_version": "engine_a_v1",
            "run_dir": "../outside-model-root",
            "validation_report": "report.json",
        },
    ],
)
def test_model_provenance_broken_latest_pointer_blocks_hash_ok_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pointer_body: dict[str, Any] | None,
) -> None:
    model_path = _write_bytes(
        tmp_path / "app/data/models/runs/20260502T153931Z/QB_model.pkl",
        b"engine-a-qb",
    )
    if pointer_body is not None:
        _write_json(tmp_path / "app/data/models/latest.json", pointer_body)
    registry_path = _write_registry(
        tmp_path / "registry.json",
        [_artifact({"sha256": _sha(model_path)})],
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "serving"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 200
    artifact = _artifact_by_id(response.json(), "engine_a:QB")
    assert artifact["pointer_status"] in {
        "pointer_missing",
        "pointer_malformed",
    }
    assert artifact["severity"] == "integrity"
    assert artifact["serving_allowed"] is False


@pytest.mark.parametrize(
    "writer",
    [
        lambda path: None,
        lambda path: path.write_text("{not-json", encoding="utf-8"),
        lambda path: path.write_text(
            json.dumps({"registry_version": "not-a-number", "artifacts": []}),
            encoding="utf-8",
        ),
        lambda path: path.write_text(
            json.dumps({"registry_version": 1, "artifacts": []}),
            encoding="utf-8",
        ),
        lambda path: path.write_text(
            json.dumps(
                {
                    "registry_version": 1,
                    "artifacts": [
                        _artifact({"artifact_id": "duplicate:id"}),
                        _artifact({"artifact_id": "duplicate:id"}),
                    ],
                }
            ),
            encoding="utf-8",
        ),
        lambda path: path.write_text(
            json.dumps(
                {
                    "registry_version": 1,
                    "artifacts": [
                        _artifact(
                            {
                                "artifact_id": "bad:metadata",
                                "approved_date": True,
                            }
                        )
                    ],
                }
            ),
            encoding="utf-8",
        ),
    ],
)
def test_model_provenance_registry_config_errors_return_sanitized_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
) -> None:
    registry_path = tmp_path / "secret_absolute_dir" / "model_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    writer(registry_path)
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "serving"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "model_provenance_unavailable"
    assert body["decision_supported"] is False
    assert str(tmp_path) not in body["message"]
    assert "Traceback" not in body["message"]
    assert "ValidationError" not in body["message"]
    from app.api.routes.system_model_provenance_models import (
        ModelProvenanceErrorResponse,
    )

    ModelProvenanceErrorResponse.model_validate(body)


def test_model_provenance_invalid_runtime_env_returns_sanitized_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_registry(tmp_path / "registry.json", [_artifact()])
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        environ={"DG_RUNTIME_ENV": "prod"},
    )

    response = client.get("/api/system/model-provenance")

    assert response.status_code == 503
    body = response.json()
    assert body == {
        "error": "model_provenance_unavailable",
        "message": "model provenance configuration unavailable",
        "decision_supported": False,
    }


def test_model_provenance_response_models_forbid_extra_fields() -> None:
    from app.api.routes.system_model_provenance_models import (
        ArtifactProvenance,
        ModelProvenanceResponse,
    )

    valid_artifact = {
        "artifact_id": "engine_a:QB",
        "path": "app/data/models/runs/run/QB_model.pkl",
        "expected_kind": "tracked_seed",
        "promotion_status": "active",
        "observed_status": "ok",
        "pointer_status": "referenced",
        "severity": "info",
        "load_verification_status": "not_verified",
        "serving_allowed": True,
        "decision_supported": False,
    }

    with pytest.raises(ValidationError):
        ArtifactProvenance.model_validate(valid_artifact | {"verdict": "safe"})

    with pytest.raises(ValidationError):
        ModelProvenanceResponse.model_validate(
            {
                "overall_status": "ok",
                "environment": "development",
                "registry_version": 1,
                "artifacts": [valid_artifact],
                "decision_supported": False,
                "recommendation": "ship it",
            }
        )
