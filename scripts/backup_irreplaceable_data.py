"""H0-0a — offsite backup of irreplaceable data (spec 2026-07-04 v2).

Append-only by contract: each run uploads one immutable prefix under
``dynasty-genius/runs/<run_id>/`` and constructs NO delete or mirror
mutations (seed 11). The ``dynasty-genius/latest.json`` pointer object is
updated only after upload verification passes. Every terminal state writes
the gitignored status marker at ``app/data/ops/backup_status_latest.json``
(hard-excluded from the protected payload).

All external effects are injected seams (gcloud, sqlite backup, fingerprint,
upload verification, clock, sleep) so the committed contract tests run with
no network and no gitignored artifacts. ``main()`` binds the real runners.

The real verifier is a daily restore drill: it lists the run prefix
(count + byte parity), then downloads every backed-up object and compares
its sha256 against the staging inventory before the latest.json pointer is
allowed to advance. ``sha256_verified`` in the marker is earned, not implied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "backup_manifest.v1"
MARKER_REL_PATH = "app/data/ops/backup_status_latest.json"
ALLOWED_ROOTS = ("app/data", "app/config")
_MANIFEST_KEYS = {"schema_version", "required", "optional", "exclude_paths"}
_ENTRY_KEYS = {"path", "required", "kind"}
_ENTRY_KINDS = {"sqlite", "file"}
_STABILITY_ATTEMPTS = 2
_STABILITY_INTERVAL_SECONDS = 2.0

DEFAULT_BUCKET_URI = "gs://dynasty-genius-backup-dtl"


class BackupError(Exception):
    """A named, fail-closed backup failure. str(exc) is the marker reason."""


def _validate_manifest_shape(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BackupError("manifest_malformed:not_an_object")
    unknown = set(payload) - _MANIFEST_KEYS
    if unknown:
        raise BackupError(f"manifest_malformed:unknown_keys:{sorted(unknown)}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise BackupError("manifest_malformed:schema_version")
    for section in ("required", "optional", "exclude_paths"):
        if section not in payload:
            raise BackupError(f"manifest_malformed:missing_section:{section}")
    if not isinstance(payload["exclude_paths"], list) or not all(
        isinstance(item, str) for item in payload["exclude_paths"]
    ):
        raise BackupError("manifest_malformed:exclude_paths")
    entries: list[dict[str, Any]] = []
    for section in ("required", "optional"):
        section_entries = payload[section]
        if not isinstance(section_entries, list):
            raise BackupError(f"manifest_malformed:section_not_list:{section}")
        for entry in section_entries:
            if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
                raise BackupError("manifest_malformed:entry_keys")
            if entry["kind"] not in _ENTRY_KINDS:
                raise BackupError(f"manifest_malformed:entry_kind:{entry['kind']}")
            if not isinstance(entry["path"], str) or not entry["path"]:
                raise BackupError("manifest_malformed:entry_path")
            if not isinstance(entry["required"], bool):
                raise BackupError("manifest_malformed:entry_required_not_bool")
            if entry["path"] in payload["exclude_paths"]:
                raise BackupError(f"manifest_malformed:entry_excluded:{entry['path']}")
            entries.append(
                {
                    "path": entry["path"],
                    "required": bool(entry["required"]) and section == "required",
                    "kind": entry["kind"],
                }
            )
    return {"entries": entries}


def _validate_entry_path(rel_path: str, repo_root: Path) -> Path:
    """Path safety (seed 6): repo-relative, confined, no traversal/symlink escape."""
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise BackupError(f"path_not_relative:{rel_path}")
    if ".." in candidate.parts:
        raise BackupError(f"path_traversal:{rel_path}")
    if not any(
        rel_path == root or rel_path.startswith(root + "/") for root in ALLOWED_ROOTS
    ):
        raise BackupError(f"path_outside_allowed_roots:{rel_path}")
    repo_resolved = repo_root.resolve()
    resolved = (repo_root / candidate).resolve()
    if not resolved.is_relative_to(repo_resolved):
        raise BackupError(f"path_escapes_repo:{rel_path}")
    return repo_root / candidate


def _stage_stable_file(
    source: Path,
    destination: Path,
    file_fingerprint: Callable[[Path], tuple[int, str]],
    sleep: Callable[[float], None],
) -> tuple[int, str]:
    """Copy a non-DB file only once its (size, digest) is stable (seed 3)."""
    for attempt in range(_STABILITY_ATTEMPTS):
        before = file_fingerprint(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        after = file_fingerprint(source)
        if before == after:
            return after
        if attempt < _STABILITY_ATTEMPTS - 1:
            sleep(_STABILITY_INTERVAL_SECONDS)
    raise BackupError(f"unstable_file:{source.name}")


def run_backup(
    *,
    repo_root: Path,
    manifest_path: Path,
    bucket_uri: str,
    staging_root: Path,
    gcloud_runner: Callable[[list[str]], Any],
    sqlite_backup_runner: Callable[[Path, Path], None],
    file_fingerprint: Callable[[Path], tuple[int, str]],
    upload_verifier: Callable[..., bool],
    sleep: Callable[[float], None],
    now_utc: Callable[[], datetime],
) -> dict[str, Any]:
    started = now_utc()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    run_staging = staging_root / run_id
    run_prefix = f"{bucket_uri}/dynasty-genius/runs/{run_id}"
    inventory: list[dict[str, Any]] = []
    failures: list[str] = []
    status = "failed"

    try:
        try:
            manifest_payload = json.loads(manifest_path.read_text())
        except (OSError, ValueError) as exc:
            raise BackupError(f"manifest_unreadable:{type(exc).__name__}") from exc
        entries = _validate_manifest_shape(manifest_payload)["entries"]

        resolved: list[tuple[dict[str, Any], Path]] = []
        for entry in entries:
            source = _validate_entry_path(entry["path"], repo_root)
            if not source.exists():
                if entry["required"]:
                    raise BackupError(f"missing_required:{entry['path']}")
                failures.append(f"missing_optional:{entry['path']}")
                continue
            resolved.append((entry, source))

        auth = gcloud_runner(["auth", "print-access-token"])
        if getattr(auth, "returncode", 1) != 0:
            raise BackupError("auth_unavailable")

        for entry, source in resolved:
            destination = run_staging / entry["path"]
            if entry["kind"] == "sqlite":
                destination.parent.mkdir(parents=True, exist_ok=True)
                sqlite_backup_runner(source, destination)
                size, digest = file_fingerprint(destination)
            else:
                size, digest = _stage_stable_file(
                    source, destination, file_fingerprint, sleep
                )
            inventory.append(
                {"path": entry["path"], "bytes": size, "sha256": digest}
            )

        run_inventory = {
            "schema_version": "backup_run_inventory.v1",
            "run_id": run_id,
            "started_at": started.isoformat(),
            "files": inventory,
        }
        run_staging.mkdir(parents=True, exist_ok=True)
        (run_staging / "run_inventory.json").write_text(
            json.dumps(run_inventory, indent=2, sort_keys=True)
        )

        # Append-only, per-file upload to exact immutable keys (seed 11: no
        # rsync, no rm, no delete flags, no recursive-cp layout ambiguity —
        # every object lands at runs/<run_id>/<manifest_path>).
        for item in inventory:
            upload = gcloud_runner(
                [
                    "storage",
                    "cp",
                    str(run_staging / item["path"]),
                    f"{run_prefix}/{item['path']}",
                ]
            )
            if getattr(upload, "returncode", 1) != 0:
                raise BackupError(f"upload_failed:{item['path']}")
        inventory_upload = gcloud_runner(
            [
                "storage",
                "cp",
                str(run_staging / "run_inventory.json"),
                f"{run_prefix}/run_inventory.json",
            ]
        )
        if getattr(inventory_upload, "returncode", 1) != 0:
            raise BackupError("upload_failed:run_inventory.json")

        if not upload_verifier(
            gcloud_runner=gcloud_runner,
            run_prefix=run_prefix,
            inventory=inventory,
        ):
            raise BackupError("upload_verification_mismatch")

        pointer_path = run_staging / "latest_pointer.json"
        pointer_path.write_text(
            json.dumps(
                {
                    "schema_version": "backup_latest_pointer.v1",
                    "run_id": run_id,
                    "run_prefix": run_prefix,
                    "verified": True,
                    "generated_at": now_utc().isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        pointer = gcloud_runner(
            [
                "storage",
                "cp",
                str(pointer_path),
                f"{bucket_uri}/dynasty-genius/latest.json",
            ]
        )
        if getattr(pointer, "returncode", 1) != 0:
            raise BackupError("latest_pointer_update_failed")

        status = "completed"
    except BackupError as exc:
        failures.append(str(exc))
    except Exception as exc:  # fail closed on anything unforeseen
        failures.append(f"unexpected:{type(exc).__name__}")
    finally:
        shutil.rmtree(run_staging, ignore_errors=True)

    finished = now_utc()
    marker = {
        "schema_version": "backup_status.v1",
        "status": status,
        "run_id": run_id,
        "run_prefix": run_prefix if status == "completed" else None,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "files": len(inventory),
        "bytes": sum(item["bytes"] for item in inventory),
        "sha256_verified": status == "completed",
        "failures": failures,
    }
    marker_path = repo_root / MARKER_REL_PATH
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True))
    except OSError:
        status = "failed"
        failures.append("marker_write_failed")
        marker["status"] = status
        marker["sha256_verified"] = False

    return {**marker, "exit_code": 0 if status == "completed" else 1}


# ── Real runners (bound only by main(); tests inject fakes) ───────────────────


def _real_gcloud_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"}
    return subprocess.run(
        ["gcloud", *args], capture_output=True, text=True, env=env, check=False
    )


def _real_sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        sqlite3.connect(f"file:{source}?mode=ro", uri=True) as src,
        sqlite3.connect(destination) as dst,
    ):
        src.backup(dst)


def _real_fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _real_upload_verifier(
    *, gcloud_runner: Callable[[list[str]], Any], run_prefix: str, inventory: list[dict[str, Any]]
) -> bool:
    """Daily restore drill: list-parity, then download every object and
    sha256-compare against the staging inventory. The latest.json pointer
    only advances past this gate — sha256_verified is earned, not implied.
    """
    listing = gcloud_runner(["storage", "ls", "--long", f"{run_prefix}/**"])
    if getattr(listing, "returncode", 1) != 0:
        return False
    remote_sizes: dict[str, int] = {}
    for line in listing.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[-1].startswith("gs://"):
            remote_sizes[parts[-1]] = int(parts[0])
    expected_objects = len(inventory) + 1  # + run_inventory.json
    if len(remote_sizes) != expected_objects:
        return False
    for item in inventory:
        if remote_sizes.get(f"{run_prefix}/{item['path']}") != item["bytes"]:
            return False
    restore_dir = Path(tempfile.mkdtemp(prefix="dg-backup-verify-"))
    try:
        for item in inventory:
            restored = restore_dir / item["path"]
            download = gcloud_runner(
                ["storage", "cp", f"{run_prefix}/{item['path']}", str(restored)]
            )
            if getattr(download, "returncode", 1) != 0:
                return False
            size, digest = _real_fingerprint(restored)
            if size != item["bytes"] or digest != item["sha256"]:
                return False
        return True
    finally:
        shutil.rmtree(restore_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--manifest", type=Path, default=repo_root / "app/config/backup_manifest.json"
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET_URI)
    parser.add_argument(
        "--staging", type=Path, default=repo_root / "app/data/ops/backup_staging"
    )
    args = parser.parse_args(argv)

    result = run_backup(
        repo_root=args.repo_root,
        manifest_path=args.manifest,
        bucket_uri=args.bucket,
        staging_root=args.staging,
        gcloud_runner=_real_gcloud_runner,
        sqlite_backup_runner=_real_sqlite_backup,
        file_fingerprint=_real_fingerprint,
        upload_verifier=_real_upload_verifier,
        sleep=time.sleep,
        now_utc=lambda: datetime.now(timezone.utc),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
