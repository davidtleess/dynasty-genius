"""T2 RED: pure model-provenance classifier.

T2 intentionally has no disk I/O. It consumes a registered artifact, observed
file facts, a pointer_status already computed by later T3 readers, and an
environment. Hashing, latest.json resolution, manifest reads, unregistered-local
reverse scans, route wiring, and OpenAPI generation are outside this slice.
"""

from __future__ import annotations

from typing import Any

import pytest


def _models():
    import app.api.routes.system_model_provenance_models as models

    return models


def _artifact(overrides: dict[str, Any] | None = None):
    models = _models()
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
        "updated_by_commit": "9fdac6a",
    }
    if overrides:
        body.update(overrides)
    return models.RegistryArtifact.model_validate(body)


def _classify(
    *,
    entry,
    artifact_present: bool,
    observed_hash: str | None,
    pointer_status: str = "referenced",
    environment: str = "development",
):
    models = _models()
    return models.classify_artifact(
        entry=entry,
        artifact_present=artifact_present,
        observed_hash=observed_hash,
        pointer_status=pointer_status,
        environment=environment,
    )


def _assert_provenance(
    provenance,
    *,
    entry,
    observed_status: str,
    severity: str,
    serving_allowed: bool,
    pointer_status: str = "referenced",
) -> None:
    assert provenance.artifact_id == entry.artifact_id
    assert provenance.path == entry.path
    assert provenance.expected_kind == entry.kind
    assert provenance.promotion_status == entry.promotion_status
    assert provenance.observed_status == observed_status
    assert provenance.pointer_status == pointer_status
    assert provenance.severity == severity
    assert provenance.serving_allowed is serving_allowed
    assert provenance.load_verification_status == "not_verified"
    assert provenance.decision_supported is False


def test_tracked_seed_hash_match_is_ok_info_and_serving_allowed() -> None:
    entry = _artifact()

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="a" * 64,
        environment="development",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="ok",
        severity="info",
        serving_allowed=True,
    )


def test_tracked_seed_hash_mismatch_blocks_even_in_development_without_override() -> None:
    entry = _artifact()

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="development",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="hash_mismatch",
        severity="integrity",
        serving_allowed=False,
    )


def test_tracked_seed_hash_mismatch_dev_override_is_the_only_tracked_escape() -> None:
    entry = _artifact({"allow_local_override": True})

    dev = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="development",
    )
    serving = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="serving",
    )

    _assert_provenance(
        dev,
        entry=entry,
        observed_status="hash_mismatch",
        severity="caveat",
        serving_allowed=True,
    )
    _assert_provenance(
        serving,
        entry=entry,
        observed_status="hash_mismatch",
        severity="integrity",
        serving_allowed=False,
    )


def test_tracked_seed_absent_is_missing_required_and_blocked() -> None:
    entry = _artifact()

    provenance = _classify(
        entry=entry,
        artifact_present=False,
        observed_hash=None,
        environment="development",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="missing_required",
        severity="integrity",
        serving_allowed=False,
    )


def test_local_operational_absent_in_ci_is_caveat_not_failure() -> None:
    entry = _artifact(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "kind": "local_operational",
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=False,
        observed_hash=None,
        pointer_status="pointer_missing",
        environment="ci",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="local_artifact_missing_ci",
        pointer_status="pointer_missing",
        severity="caveat",
        serving_allowed=True,
    )


def test_local_operational_hash_mismatch_in_development_is_info_override() -> None:
    entry = _artifact(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "kind": "local_operational",
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="development",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="local_override",
        severity="info",
        serving_allowed=True,
    )


def test_local_operational_active_required_serving_mismatch_blocks_unapproved_reality() -> None:
    entry = _artifact(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "kind": "local_operational",
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="local_override",
        severity="integrity",
        serving_allowed=False,
    )


@pytest.mark.parametrize("promotion_status", ["candidate", "parked"])
def test_local_operational_non_active_serving_mismatch_is_caveat_not_blocking(
    promotion_status: str,
) -> None:
    entry = _artifact(
        {
            "artifact_id": f"engine_b:{promotion_status}",
            "path": f"app/data/models/engine_b/runs/run/{promotion_status}.pkl",
            "kind": "local_operational",
            "promotion_status": promotion_status,
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="b" * 64,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="local_override",
        severity="caveat",
        serving_allowed=True,
    )


def test_local_operational_absent_in_required_serving_env_is_missing_required() -> None:
    entry = _artifact(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "kind": "local_operational",
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=False,
        observed_hash=None,
        pointer_status="pointer_missing",
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="missing_required",
        pointer_status="pointer_missing",
        severity="integrity",
        serving_allowed=False,
    )


def test_expected_hash_missing_active_required_serving_blocks_even_when_file_present() -> None:
    entry = _artifact({"sha256": None, "required_by_env": ["serving"]})

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="a" * 64,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="expected_hash_missing",
        severity="integrity",
        serving_allowed=False,
    )


def test_expected_hash_missing_local_absent_ci_is_caveat_200_safe() -> None:
    entry = _artifact(
        {
            "artifact_id": "engine_b:qb_v2",
            "path": "app/data/models/engine_b/runs/run/qb_v2.pkl",
            "sha256": None,
            "kind": "local_operational",
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=False,
        observed_hash=None,
        pointer_status="pointer_missing",
        environment="ci",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="expected_hash_missing",
        pointer_status="pointer_missing",
        severity="caveat",
        serving_allowed=True,
    )


@pytest.mark.parametrize("promotion_status", ["candidate", "parked"])
def test_expected_hash_missing_candidate_or_parked_is_non_blocking(
    promotion_status: str,
) -> None:
    entry = _artifact(
        {
            "artifact_id": f"engine_b:{promotion_status}",
            "path": f"app/data/models/engine_b/runs/run/{promotion_status}.pkl",
            "sha256": None,
            "kind": "local_operational",
            "promotion_status": promotion_status,
            "required_by_env": ["serving", "production"],
        }
    )

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="a" * 64,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="expected_hash_missing",
        severity="caveat",
        serving_allowed=True,
    )


@pytest.mark.parametrize(
    "pointer_status",
    ["pointer_missing", "pointer_malformed", "pointer_mismatch"],
)
def test_broken_pointer_blocks_active_required_serving_even_when_hash_matches(
    pointer_status: str,
) -> None:
    entry = _artifact({"required_by_env": ["serving"]})

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="a" * 64,
        pointer_status=pointer_status,
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="ok",
        pointer_status=pointer_status,
        severity="integrity",
        serving_allowed=False,
    )


def test_not_applicable_pointer_allows_hash_ok_artifact_to_remain_clean() -> None:
    entry = _artifact({"governing_pointer": None})

    provenance = _classify(
        entry=entry,
        artifact_present=True,
        observed_hash="a" * 64,
        pointer_status="not_applicable",
        environment="serving",
    )

    _assert_provenance(
        provenance,
        entry=entry,
        observed_status="ok",
        pointer_status="not_applicable",
        severity="info",
        serving_allowed=True,
    )
