"""T3 RED: pointer health, disk hashing, and scoped unregistered scans.

These tests use temp model roots and dependency injection only. They never read
the real ``app/data`` model tree or the checked-in ``app/config`` registry.
T3 remains below the route layer: it derives ``pointer_status``, resolves
``latest_run_dir`` paths, hashes files by streaming, and reports scoped
``unregistered_local`` rows. HTTP response assembly belongs to T4.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest


def _models():
    import app.api.routes.system_model_provenance_models as models

    return models


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, body: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _write_bytes(path: Path, payload: bytes = b"model-bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _artifact(overrides: dict[str, Any] | None = None):
    models = _models()
    body = {
        "artifact_id": "engine_b:QB_v2",
        "path": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
        "path_resolution": "literal",
        "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
        "sha256": "a" * 64,
        "kind": "local_operational",
        "promotion_status": "active",
        "required_by_env": ["serving", "production"],
        "allow_local_override": False,
        "approved_by": "David",
        "approved_date": "2026-07-01",
        "updated_by_commit": "9ff5f86",
    }
    if overrides:
        body.update(overrides)
    return models.RegistryArtifact.model_validate(body)


def _registry(artifacts):
    models = _models()
    return models.ModelRegistry.model_validate(
        {"registry_version": 1, "artifacts": [a.model_dump() for a in artifacts]}
    )


def _assert_provenance(
    provenance,
    *,
    path: str,
    observed_status: str,
    pointer_status: str,
    severity: str,
    serving_allowed: bool,
) -> None:
    assert provenance.path == path
    assert provenance.observed_status == observed_status
    assert provenance.pointer_status == pointer_status
    assert provenance.severity == severity
    assert provenance.serving_allowed is serving_allowed
    assert provenance.load_verification_status == "not_verified"
    assert provenance.decision_supported is False


def test_latest_run_dir_resolves_run_dir_filename_and_streams_hash(
    tmp_path: Path,
) -> None:
    models = _models()
    model_path = _write_bytes(
        tmp_path / "app/data/models/runs/20260502T153931Z/QB_model.pkl",
        b"active engine a bytes",
    )
    _write_json(
        tmp_path / "app/data/models/latest.json",
        {
            "model_version": "engine_a_v1",
            "run_dir": "app/data/models/runs/20260502T153931Z",
            "validation_report": "app/data/models/runs/20260502T153931Z/report.json",
        },
    )
    root_pkl = _write_bytes(tmp_path / "app/data/models/QB_model.pkl", b"stale root")
    entry = _artifact(
        {
            "artifact_id": "engine_a:QB",
            "path": "QB_model.pkl",
            "path_resolution": "latest_run_dir",
            "governing_pointer": "app/data/models/latest.json",
            "sha256": _sha(model_path),
            "kind": "tracked_seed",
            "required_by_env": ["development", "ci", "serving", "production"],
        }
    )

    provenance = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        path="app/data/models/runs/20260502T153931Z/QB_model.pkl",
        observed_status="ok",
        pointer_status="referenced",
        severity="info",
        serving_allowed=True,
    )
    assert provenance.path != str(root_pkl.relative_to(tmp_path))


def test_pointer_health_missing_malformed_and_mismatch_block_serving_hash_ok_artifacts(
    tmp_path: Path,
) -> None:
    models = _models()
    artifact_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"
    )
    entry = _artifact({"sha256": _sha(artifact_path)})

    missing = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )
    _assert_provenance(
        missing,
        path=entry.path,
        observed_status="ok",
        pointer_status="pointer_missing",
        severity="integrity",
        serving_allowed=False,
    )

    pointer = tmp_path / "app/data/models/engine_b/v2_manifest.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text("{not-json", encoding="utf-8")
    malformed = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )
    _assert_provenance(
        malformed,
        path=entry.path,
        observed_status="ok",
        pointer_status="pointer_malformed",
        severity="integrity",
        serving_allowed=False,
    )

    _write_json(pointer, {"QB": "app/data/models/engine_b/runs/other/qb_v2.pkl"})
    mismatch = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )
    _assert_provenance(
        mismatch,
        path=entry.path,
        observed_status="ok",
        pointer_status="pointer_mismatch",
        severity="integrity",
        serving_allowed=False,
    )


def test_pointer_malformed_for_empty_or_missing_run_dir_and_path_traversal(
    tmp_path: Path,
) -> None:
    models = _models()
    entry = _artifact(
        {
            "artifact_id": "engine_a:QB",
            "path": "QB_model.pkl",
            "path_resolution": "latest_run_dir",
            "governing_pointer": "app/data/models/latest.json",
            "sha256": "a" * 64,
            "kind": "tracked_seed",
        }
    )
    pointer_path = tmp_path / "app/data/models/latest.json"

    for body in (
        {},
        {"model_version": "engine_a_v1", "run_dir": ""},
        {
            "model_version": "engine_a_v1",
            "run_dir": "../outside-model-root",
            "validation_report": "report.json",
        },
    ):
        _write_json(pointer_path, body)

        provenance = models.inspect_registered_artifact(
            entry=entry,
            repo_root=tmp_path,
            environment="serving",
        )

        _assert_provenance(
            provenance,
            path="QB_model.pkl",
            observed_status="missing_required",
            pointer_status="pointer_malformed",
            severity="integrity",
            serving_allowed=False,
        )


def test_manifest_comparison_is_strict_case_sensitive_string_comparison(
    tmp_path: Path,
) -> None:
    models = _models()
    artifact_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"
    )
    entry = _artifact({"sha256": _sha(artifact_path)})
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/20260513T012309Z/QB_v2.pkl"},
    )

    status = models.derive_pointer_status(entry=entry, repo_root=tmp_path)

    assert status == "pointer_mismatch"


def test_engine_b_and_head_a_te_v3_are_judged_against_separate_governing_pointers(
    tmp_path: Path,
) -> None:
    models = _models()
    engine_b_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260626T165649Z/te_v3.pkl",
        b"engine-b-te",
    )
    head_a_path = _write_bytes(
        tmp_path / "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl",
        b"head-a-te",
    )
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"TE": "app/data/models/engine_b/runs/20260626T165649Z/te_v3.pkl"},
    )
    _write_json(
        tmp_path / "app/data/models/head_a/v3_manifest.json",
        {"TE": "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl"},
    )
    engine_b = _artifact(
        {
            "artifact_id": "engine_b:TE_v3",
            "path": "app/data/models/engine_b/runs/20260626T165649Z/te_v3.pkl",
            "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
            "sha256": _sha(engine_b_path),
        }
    )
    head_a = _artifact(
        {
            "artifact_id": "head_a:TE_v3",
            "path": "app/data/models/head_a/runs/20260524T140748Z/te_v3.pkl",
            "governing_pointer": "app/data/models/head_a/v3_manifest.json",
            "sha256": _sha(head_a_path),
        }
    )

    engine_b_prov = models.inspect_registered_artifact(
        entry=engine_b, repo_root=tmp_path, environment="serving"
    )
    head_a_prov = models.inspect_registered_artifact(
        entry=head_a, repo_root=tmp_path, environment="serving"
    )

    assert engine_b_prov.path == engine_b.path
    assert engine_b_prov.pointer_status == "referenced"
    assert head_a_prov.path == head_a.path
    assert head_a_prov.pointer_status == "referenced"


def test_directory_or_permission_error_at_expected_artifact_fails_closed_not_crash(
    tmp_path: Path,
) -> None:
    models = _models()
    directory = tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"
    directory.mkdir(parents=True)
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"},
    )
    entry = _artifact()

    directory_result = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )
    _assert_provenance(
        directory_result,
        path=entry.path,
        observed_status="missing_required",
        pointer_status="referenced",
        severity="integrity",
        serving_allowed=False,
    )

    def raise_permission(_path: Path) -> str:
        raise PermissionError("fixture denies artifact read")

    permission_result = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
        hash_file=raise_permission,
    )
    _assert_provenance(
        permission_result,
        path=entry.path,
        observed_status="missing_required",
        pointer_status="referenced",
        severity="integrity",
        serving_allowed=False,
    )


def test_permission_error_at_pointer_is_pointer_malformed_not_raised(
    tmp_path: Path,
) -> None:
    models = _models()
    entry = _artifact()

    def raise_permission(_path: Path) -> dict[str, Any]:
        raise PermissionError("fixture denies pointer read")

    status = models.derive_pointer_status(
        entry=entry,
        repo_root=tmp_path,
        load_json=raise_permission,
    )

    assert status == "pointer_malformed"


def test_dangling_symlink_at_expected_artifact_fails_closed_without_following_outside_root(
    tmp_path: Path,
) -> None:
    models = _models()
    target = tmp_path / "outside-model-root.pkl"
    artifact_path = tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.symlink_to(target)
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"},
    )
    entry = _artifact()

    provenance = models.inspect_registered_artifact(
        entry=entry,
        repo_root=tmp_path,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        path=entry.path,
        observed_status="missing_required",
        pointer_status="referenced",
        severity="integrity",
        serving_allowed=False,
    )


def test_hash_file_sha256_reads_in_chunks_not_one_full_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = _models()
    artifact_path = _write_bytes(tmp_path / "artifact.pkl", b"abcdef")
    original_open = Path.open
    read_sizes: list[int] = []

    class TrackingReader:
        def __init__(self, wrapped):
            self._wrapped = wrapped

        def __enter__(self):
            self._fh = self._wrapped.__enter__()
            return self

        def __exit__(self, *args):
            return self._wrapped.__exit__(*args)

        def read(self, size: int = -1):
            read_sizes.append(size)
            return self._fh.read(size)

    def tracking_open(self: Path, *args, **kwargs):
        return TrackingReader(original_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", tracking_open)

    digest = models.hash_file_sha256(artifact_path)

    assert digest == hashlib.sha256(b"abcdef").hexdigest()
    assert read_sizes
    assert all(size > 0 for size in read_sizes)


def test_scoped_reverse_scan_reports_manifest_referenced_unregistered_path_as_blocking(
    tmp_path: Path,
) -> None:
    models = _models()
    registered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
        b"registered",
    )
    unregistered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/wr_v2.pkl",
        b"manifest-referenced-but-unregistered",
    )
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {
            "QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
            "WR": "app/data/models/engine_b/runs/20260513T012309Z/wr_v2.pkl",
        },
    )
    registry = _registry([_artifact({"sha256": _sha(registered_path)})])

    unregistered = models.scan_unregistered_local_artifacts(
        registry=registry,
        repo_root=tmp_path,
        environment="production",
    )

    by_path = {row.path: row for row in unregistered}
    row = by_path[str(unregistered_path.relative_to(tmp_path))]
    _assert_provenance(
        row,
        path=str(unregistered_path.relative_to(tmp_path)),
        observed_status="unregistered_local",
        pointer_status="referenced",
        severity="integrity",
        serving_allowed=False,
    )


def test_unreferenced_sibling_in_pointer_resolved_run_dir_is_info_not_blocking(
    tmp_path: Path,
) -> None:
    models = _models()
    registered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
        b"registered",
    )
    stale_sibling = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/20260513T012309Z/te_v2.pkl",
        b"stale sibling from an older manifest",
    )
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl"},
    )
    registry = _registry([_artifact({"sha256": _sha(registered_path)})])

    unregistered = models.scan_unregistered_local_artifacts(
        registry=registry,
        repo_root=tmp_path,
        environment="production",
    )

    by_path = {row.path: row for row in unregistered}
    row = by_path[str(stale_sibling.relative_to(tmp_path))]
    _assert_provenance(
        row,
        path=str(stale_sibling.relative_to(tmp_path)),
        observed_status="unregistered_local",
        pointer_status="not_applicable",
        severity="info",
        serving_allowed=True,
    )


def test_reverse_scan_does_not_walk_historical_runs_or_tests_fixtures(
    tmp_path: Path,
) -> None:
    models = _models()
    registered_path = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/current/qb_v2.pkl",
        b"registered",
    )
    historical = _write_bytes(
        tmp_path / "app/data/models/engine_b/runs/historical/old.pkl",
        b"historical",
    )
    fixture = _write_bytes(tmp_path / "tests/fixtures/app/data/models/fixture.pkl")
    _write_json(
        tmp_path / "app/data/models/engine_b/v2_manifest.json",
        {"QB": "app/data/models/engine_b/runs/current/qb_v2.pkl"},
    )
    registry = _registry(
        [
            _artifact(
                {
                    "path": "app/data/models/engine_b/runs/current/qb_v2.pkl",
                    "sha256": _sha(registered_path),
                }
            )
        ]
    )

    unregistered = models.scan_unregistered_local_artifacts(
        registry=registry,
        repo_root=tmp_path,
        environment="production",
    )

    scanned_paths = {row.path for row in unregistered}
    assert str(historical.relative_to(tmp_path)) not in scanned_paths
    assert str(fixture.relative_to(tmp_path)) not in scanned_paths
