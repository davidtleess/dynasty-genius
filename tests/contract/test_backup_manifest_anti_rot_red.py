from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_MANIFEST = REPO_ROOT / "app" / "config" / "backup_manifest.json"
MODEL_REGISTRY = REPO_ROOT / "app" / "config" / "model_registry.json"


def _read_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing required config file: {path.relative_to(REPO_ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_payload() -> dict[str, Any]:
    return _read_json(BACKUP_MANIFEST)


def _covered_manifest_paths(payload: dict[str, Any]) -> set[str]:
    covered: set[str] = set()
    for section in ("required", "optional"):
        for entry in payload.get(section, []):
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                covered.add(entry["path"])
    return covered


def _excluded_manifest_paths(payload: dict[str, Any]) -> set[str]:
    exclusions = payload.get("exclusions")
    assert isinstance(exclusions, list), (
        "backup_manifest.json must expose schema-versioned exclusions with reasons; "
        "plain exclude_paths is not enough to guard manifest rot"
    )

    excluded: set[str] = set()
    for item in exclusions:
        assert isinstance(item, dict), "each backup exclusion must be an object"
        assert isinstance(item.get("path"), str) and item["path"], (
            "each backup exclusion needs a non-empty path"
        )
        assert isinstance(item.get("reason"), str) and item["reason"].strip(), (
            f"backup exclusion {item.get('path')!r} needs an explicit reason"
        )
        excluded.add(item["path"])
    return excluded


def _registry_referenced_paths() -> set[str]:
    registry = _read_json(MODEL_REGISTRY)
    paths = {"app/config/model_registry.json"}

    for artifact in registry.get("artifacts", []):
        assert isinstance(artifact, dict), "model registry artifacts must be objects"
        raw_path = artifact.get("path")
        if isinstance(raw_path, str) and raw_path.startswith("app/"):
            paths.add(raw_path)

        pointer = artifact.get("governing_pointer")
        if isinstance(pointer, str) and pointer.startswith("app/"):
            paths.add(pointer)

    return paths


def _present_app_data_dbs() -> set[str]:
    app_data = REPO_ROOT / "app" / "data"
    if not app_data.exists():
        return set()
    return {
        path.relative_to(REPO_ROOT).as_posix()
        for path in app_data.rglob("*.db")
        if path.is_file()
    }


def test_backup_manifest_has_schema_versioned_exclusions_with_reasons() -> None:
    payload = _manifest_payload()

    assert payload["schema_version"] == "backup_manifest.v2"
    _excluded_manifest_paths(payload)


def test_backup_manifest_covers_present_dbs_and_registry_references() -> None:
    payload = _manifest_payload()
    covered = _covered_manifest_paths(payload)
    excluded = _excluded_manifest_paths(payload)

    required_coverage = _present_app_data_dbs() | _registry_referenced_paths()
    uncovered = sorted(required_coverage - covered - excluded)

    assert uncovered == [], (
        "backup manifest rot: every present app/data/*.db and every "
        "model_registry.json-referenced artifact/pointer path must be backed up or "
        f"explicitly excluded with reason; uncovered={uncovered}"
    )
