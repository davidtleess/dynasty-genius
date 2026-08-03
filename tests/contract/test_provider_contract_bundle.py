"""Contract for authoritative provider evidence and immovable review targets."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.build_provider_contract_bundle import (
    BUNDLE_VERSION,
    ProviderContractError,
    _extract_swagger_doc,
)
from scripts.freeze_review_target import ReviewTargetError, create_target, verify_target

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "docs" / "provider-contracts"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cfbd_openapi_pins_the_routes_the_adapter_actually_uses() -> None:
    manifest = _json(CONTRACTS / "cfbd" / "manifest.json")
    openapi_path = CONTRACTS / "cfbd" / "openapi.json"
    openapi = _json(openapi_path)

    assert manifest["contract_version"] == BUNDLE_VERSION
    assert manifest["openapi_sha256"] == _sha256(openapi_path)
    assert manifest["openapi_version"] == openapi["info"]["version"]
    assert set(manifest["required_paths"]) <= set(openapi["paths"])
    assert set(manifest["known_invalid_paths"]).isdisjoint(openapi["paths"])
    for path in manifest["required_paths"]:
        response = openapi["paths"][path]["get"]["responses"]["200"]
        assert "application/json" in response["content"], path


def test_cfbd_dynamic_stat_evidence_closes_the_openapi_gap() -> None:
    manifest = _json(CONTRACTS / "cfbd" / "manifest.json")
    catalog_path = CONTRACTS / "cfbd" / "team-stat-catalog.json"
    catalog = _json(catalog_path)
    names = {row["stat_name"] for row in catalog["stats"]}

    assert manifest["team_stat_catalog_sha256"] == _sha256(catalog_path)
    assert set(manifest["required_dynamic_stat_names"]) <= names
    assert set(manifest["known_invalid_dynamic_stat_names"]).isdisjoint(names)
    assert catalog["endpoint"] == "/stats/season"
    assert catalog["raw_files_examined"] > 0
    assert catalog["unique_payloads_examined"] > 0
    assert "statValue" not in catalog_path.read_text(encoding="utf-8")


def test_cfbd_response_identity_bindings_exist_in_the_pinned_schema() -> None:
    manifest = _json(CONTRACTS / "cfbd" / "manifest.json")
    openapi = _json(CONTRACTS / "cfbd" / "openapi.json")
    schemas = openapi["components"]["schemas"]

    for path, binding in manifest["response_identity_fields"].items():
        response = openapi["paths"][path]["get"]["responses"]["200"]
        response_schema = response["content"]["application/json"]["schema"]
        reference = response_schema["items"]["$ref"]
        properties = schemas[reference.rsplit("/", 1)[-1]]["properties"]
        for field in binding.split("+"):
            assert field in properties, (path, field)


@pytest.mark.parametrize(
    ("provider", "expected_schemas", "expected_payloads"),
    (("pff", 12, 149), ("playerprofiler", 16, 56)),
)
def test_paid_provider_manifests_pin_shapes_without_publishing_paid_data(
    provider: str, expected_schemas: int, expected_payloads: int
) -> None:
    path = CONTRACTS / provider / "header-manifest.json"
    payload = _json(path)
    text = path.read_text(encoding="utf-8")

    assert payload["contract_version"] == BUNDLE_VERSION
    assert payload["schema_count"] == expected_schemas
    count_key = "payload_count" if provider == "pff" else "source_file_count"
    assert payload[count_key] == expected_payloads
    sample_key = (
        "value_profile_sample_rows_per_payload"
        if provider == "pff"
        else "value_profile_sample_rows_per_file"
    )
    assert payload[sample_key] == 200
    assert payload["privacy"] == {
        **payload["privacy"],
        "raw_values_committed": False,
        "complete_headers_committed": False,
        "source_filenames_committed": False,
    }
    assert "/Users/" not in text
    assert "Downloads" not in text
    assert "field_names" not in text

    allowed_schema_keys = {
        "header_sha256",
        "column_count",
        "value_kind_profile_sha256",
        "value_kind_column_counts",
        "payload_count",
        "reports",
        "leagues",
        "scopes",
        "seasons",
        "stream",
        "source_file_count",
        "positions",
    }
    for schema in payload["schemas"]:
        assert set(schema) <= allowed_schema_keys
        assert len(schema["header_sha256"]) == 64
        assert len(schema["value_kind_profile_sha256"]) == 64
        assert schema["column_count"] > 0


def test_playerprofiler_manifest_covers_all_five_manual_streams() -> None:
    payload = _json(CONTRACTS / "playerprofiler" / "header-manifest.json")
    assert {schema["stream"] for schema in payload["schemas"]} == {
        "player_season",
        "medical_history",
        "weekly_roster_key",
        "advanced_gamelog",
        "advanced_pbp",
    }


def test_swagger_extractor_refuses_a_ui_without_an_embedded_contract(
    tmp_path: Path,
) -> None:
    path = tmp_path / "swagger-ui-init.js"
    path.write_text("window.onload = function () {};\n", encoding="utf-8")
    with pytest.raises(ProviderContractError, match="cfbd_swagger_doc_missing"):
        _extract_swagger_doc(path)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def test_frozen_review_target_materializes_and_detects_later_drift(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "review@example.invalid")
    _git(repo, "config", "user.name", "Review Test")
    (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD")

    (repo / "tracked.txt").write_text("after\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    target_dir = tmp_path / "target"
    manifest = create_target(
        repo=repo,
        base="HEAD",
        output=target_dir,
        scope_values=["tracked.txt", "new.txt"],
        created_at="2026-08-02T07:00:00Z",
    )
    assert manifest["base_sha"] == base_sha
    assert set(manifest["file_sha256"]) == {"new.txt", "tracked.txt"}

    review = tmp_path / "review"
    _git(tmp_path, "clone", "-q", str(repo), str(review))
    _git(review, "reset", "--hard", base_sha)
    _git(review, "apply", "--binary", str(target_dir / "target.patch"))
    result = verify_target(manifest_path=target_dir / "manifest.json", worktree=review)
    assert result["status"] == "ok"
    assert result["files_verified"] == 2

    (review / "tracked.txt").write_text("moved again\n", encoding="utf-8")
    with pytest.raises(ReviewTargetError, match="review_file_hash_mismatch"):
        verify_target(manifest_path=target_dir / "manifest.json", worktree=review)


def test_frozen_review_target_refuses_private_paid_data(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "review@example.invalid")
    _git(repo, "config", "user.name", "Review Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-qm", "base")
    with pytest.raises(ReviewTargetError, match="review_scope_private_data"):
        create_target(
            repo=repo,
            base="HEAD",
            output=tmp_path / "target",
            scope_values=["app/data/pff_exports/private.csv"],
            created_at="2026-08-02T07:00:00Z",
        )


def test_frozen_review_target_refuses_ignored_files_inside_scope(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "review@example.invalid")
    _git(repo, "config", "user.name", "Review Test")
    (repo / ".gitignore").write_text("docs/contracts/ignored.json\n", encoding="utf-8")
    (repo / "docs" / "contracts").mkdir(parents=True)
    (repo / "docs" / "contracts" / "tracked.json").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "docs/contracts/tracked.json")
    _git(repo, "commit", "-qm", "base")

    (repo / "docs" / "contracts" / "tracked.json").write_text(
        '{"changed": true}\n', encoding="utf-8"
    )
    (repo / "docs" / "contracts" / "ignored.json").write_text(
        '{"invisible": true}\n', encoding="utf-8"
    )
    with pytest.raises(ReviewTargetError, match="review_scope_contains_ignored_files"):
        create_target(
            repo=repo,
            base="HEAD",
            output=tmp_path / "target",
            scope_values=["docs/contracts"],
            created_at="2026-08-02T07:00:00Z",
        )
