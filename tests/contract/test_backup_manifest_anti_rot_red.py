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


def _covered_manifest_entries(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """(path, kind) for every required/optional manifest entry."""
    entries: list[tuple[str, str]] = []
    for section in ("required", "optional"):
        for entry in payload.get(section, []):
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                entries.append((entry["path"], str(entry.get("kind") or "file")))
    return entries


def _covered_manifest_paths(payload: dict[str, Any]) -> set[str]:
    return {path for path, _ in _covered_manifest_entries(payload)}


def _is_covered(path: str, entries: list[tuple[str, str]]) -> bool:
    """True if ``path`` is exactly a manifest entry, or a true descendant of a
    declared DIRECTORY entry.

    Directory scope mirrors what the backup runner actually does:
    ``backup_irreplaceable_data.py`` expands a ``kind="directory"`` entry via
    ``rglob("*")``, so every regular file beneath it is genuinely staged and uploaded.
    Exact-string coverage was therefore a FALSE NEGATIVE — it reported
    ``app/data/pff_exports/pff_metadata.db`` as uncovered while the runner was already
    backing it up, and the "fix" it invited (adding the DB as a second required entry)
    would have staged and uploaded the same file TWICE, because the runner does not
    deduplicate staging units.

    Scope is granted from the DECLARED ``kind``, not guessed from the path string, and
    FILE entries stay exact-only so a store nested under a file-shaped path is never
    silently exempted. The ``+ "/"`` boundary keeps a similarly prefixed sibling
    (``app/data/pff_exports_OTHER/x.db``) uncovered.
    """
    for entry_path, kind in entries:
        if path == entry_path:
            return True
        if kind == "directory" and path.startswith(entry_path.rstrip("/") + "/"):
            return True
    return False


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


def _is_excluded(path: str, excluded: set[str]) -> bool:
    """True if ``path`` is exactly an exclusion, or is a true descendant of an
    excluded DIRECTORY.

    Directory scope (recursive descendants) is granted ONLY to entries the manifest
    declares as directories — a trailing slash (``app/data/assets/``) or an
    extensionless final segment (``app/data/ops/backup_staging``). A FILE exclusion
    carries a file extension (``backup_status_latest.json``) and stays EXACT-only,
    so a real store nested under a file-exclusion path string is never silently
    exempted (an anti-rot false-negative). The ``+ "/"`` boundary keeps a similarly
    prefixed sibling (``backup_staging_OTHER``) uncovered.
    """
    for entry in excluded:
        normalized = entry.rstrip("/")
        if path == normalized:
            return True
        is_directory = entry.endswith("/") or "." not in normalized.rsplit("/", 1)[-1]
        if is_directory and path.startswith(normalized + "/"):
            return True
    return False


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
    entries = _covered_manifest_entries(payload)
    excluded = _excluded_manifest_paths(payload)

    required_coverage = _present_app_data_dbs() | _registry_referenced_paths()
    uncovered = sorted(
        path
        for path in required_coverage
        if not _is_covered(path, entries) and not _is_excluded(path, excluded)
    )

    assert uncovered == [], (
        "backup manifest rot: every present app/data/*.db and every "
        "model_registry.json-referenced artifact/pointer path must be backed up or "
        f"explicitly excluded with reason; uncovered={uncovered}"
    )


def test_backup_manifest_excludes_files_nested_under_excluded_directories() -> None:
    """A directory-level manifest exclusion must exclude files NESTED under it.

    The manifest declares `app/data/ops/backup_staging` excluded (with a reason),
    but the anti-rot scan discovers DBs recursively (`rglob`) — so a transient
    staging copy at `.../backup_staging/<run_id>/app/data/x.db` must be treated as
    excluded, not flagged uncovered. Exact-string exclusion matching (the prior
    bug) wrongly re-flagged those copies whenever a daily backup had staged them.
    """
    excluded = _excluded_manifest_paths(_manifest_payload())

    nested_staging = "app/data/ops/backup_staging/20260724T141500Z/app/data/fc_snapshots.db"
    assert nested_staging not in excluded, "sanity: the deep path is not an exact exclusion entry"
    assert _is_excluded(nested_staging, excluded), "nested file under an excluded directory must be excluded"

    # A real top-level store is NOT excluded (the fix must not over-exclude).
    assert not _is_excluded("app/data/fc_snapshots.db", excluded)
    # An exact-file exclusion still matches.
    assert _is_excluded("app/data/ops/backup_status_latest.json", excluded)


def test_backup_manifest_exact_file_exclusion_stays_exact_only() -> None:
    """A FILE exclusion must match exactly — it must NOT gain directory-prefix
    semantics, or a real store nested under its path string (e.g. a future
    registry-referenced path) would be silently exempted from anti-rot coverage.

    Directory scope (recursive descendants) is granted only to entries the
    manifest declares as directories — a trailing slash (`app/data/assets/`) or an
    extensionless final segment (`app/data/ops/backup_staging`). A file exclusion
    carries a file extension (`backup_status_latest.json`) and stays exact-only.
    """
    excluded = _excluded_manifest_paths(_manifest_payload())

    status_marker = "app/data/ops/backup_status_latest.json"
    assert _is_excluded(status_marker, excluded)  # the exact file still matches
    assert not _is_excluded(status_marker + "/hidden_store.db", excluded)  # descendants do NOT

    # The staging DIRECTORY keeps recursive semantics; a prefixed sibling does not.
    assert _is_excluded("app/data/ops/backup_staging/run/app/data/copy.db", excluded)
    assert not _is_excluded("app/data/ops/backup_staging_OTHER/store.db", excluded)


def test_a_required_directory_entry_covers_its_descendants_but_not_a_prefixed_sibling() -> None:
    """Regression for the false negative that this helper produced.

    `app/data/pff_exports` is a required DIRECTORY entry, and the backup runner expands it with
    `rglob("*")`, so the metadata ledger beneath it is genuinely staged. Exact-string coverage
    reported it uncovered anyway — and the repair that reading invited (a second required entry for
    the DB itself) would have uploaded the same file twice, since the runner does not deduplicate.

    A similarly prefixed SIBLING directory must still be uncovered: the slash boundary is the whole
    point, and without it `app/data/pff_exports_OTHER/x.db` would be silently exempted.
    """
    payload = _manifest_payload()
    entries = _covered_manifest_entries(payload)

    assert ("app/data/pff_exports", "directory") in entries, (
        "fixture precondition: pff_exports is a required directory entry"
    )
    assert _is_covered("app/data/pff_exports/pff_metadata.db", entries), (
        "a file beneath a required DIRECTORY entry is backed up and must read as covered"
    )
    assert not _is_covered("app/data/pff_exports_OTHER/x.db", entries), (
        "a similarly prefixed sibling directory must NOT be covered"
    )
    assert not _is_covered("app/data/pff_exports", [("app/data/pff_exports/x.db", "sqlite")]), (
        "a FILE entry grants no directory scope"
    )
