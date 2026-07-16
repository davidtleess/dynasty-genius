"""RED contract for safe recursive directory backup.

The F1 runtime captures are immutable directories.  A directory manifest entry
must expand to regular files at their repo-relative paths; it is never a blind
recursive upload.  Each expanded file therefore retains the existing stable
copy, inventory, upload, and restore-verification guarantees.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

MODULE_NAME = "scripts.backup_irreplaceable_data"
BUCKET = "gs://dynasty-genius-backup-dtl"
RUN_PREFIX = f"{BUCKET}/dynasty-genius/runs/20260704T151500Z"


def _backup_module():
    return importlib.import_module(MODULE_NAME)


class FakeGcloud:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> SimpleNamespace:
        normalized = [str(value) for value in args]
        self.calls.append(normalized)
        return SimpleNamespace(returncode=0, stdout="token\n", stderr="")


class RestoreGcloud:
    def __init__(self, remote_bytes: dict[str, bytes]) -> None:
        self.remote_bytes = remote_bytes
        self.downloads: list[str] = []

    def __call__(self, args: list[str]) -> SimpleNamespace:
        normalized = [str(value) for value in args]
        if normalized[:3] == ["storage", "ls", "--long"]:
            lines = [
                f"{len(payload)}  2026-07-04T15:15:00Z  {path}"
                for path, payload in sorted(self.remote_bytes.items())
            ]
            return SimpleNamespace(returncode=0, stdout="\n".join(lines), stderr="")
        if normalized[:2] == ["storage", "cp"] and normalized[2].startswith("gs://"):
            source, destination = normalized[2], Path(normalized[3])
            self.downloads.append(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.remote_bytes[source])
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def _manifest(repo: Path, *, required: bool = True) -> Path:
    path = repo / "app" / "config" / "backup_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "backup_manifest.v2",
                "required": [
                    {
                        "path": "app/data/league_runtime/runs",
                        "required": required,
                        "kind": "directory",
                    }
                ],
                "optional": [],
                "exclude_paths": ["app/data/ops/backup_status_latest.json"],
                "exclusions": [
                    {
                        "path": "app/data/ops/backup_status_latest.json",
                        "reason": "Backup status is operational state, not protected payload.",
                    }
                ],
            }
        )
    )
    return path


def _runtime_file(repo: Path, relative: str, contents: bytes) -> Path:
    path = repo / "app" / "data" / "league_runtime" / "runs" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return path


def _run(repo: Path, manifest: Path, *, gcloud: FakeGcloud, verifier=None) -> dict[str, Any]:
    backup = _backup_module()
    return backup.run_backup(
        repo_root=repo,
        manifest_path=manifest,
        bucket_uri=BUCKET,
        staging_root=repo / "tmp" / "backup-staging",
        gcloud_runner=gcloud,
        sqlite_backup_runner=lambda _source, _destination: (_ for _ in ()).throw(
            AssertionError("directory files must not use sqlite backup")
        ),
        file_fingerprint=lambda path: (
            len(path.read_bytes()),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        ),
        upload_verifier=verifier or (lambda **_kwargs: True),
        sleep=lambda _seconds: None,
        now_utc=lambda: datetime(2026, 7, 4, 15, 15, tzinfo=timezone.utc),
    )


def test_required_directory_expands_to_stable_files_and_preserves_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _runtime_file(repo, "run-a/snapshot.json", b"snapshot")
    _runtime_file(repo, "run-a/nested/provenance.json", b"provenance")
    gcloud = FakeGcloud()
    verified_inventory: list[dict[str, Any]] = []

    def verify(**kwargs: Any) -> bool:
        verified_inventory.extend(kwargs["inventory"])
        return True

    result = _run(repo, _manifest(repo), gcloud=gcloud, verifier=verify)

    assert result["status"] == "completed"
    expected_paths = {
        "app/data/league_runtime/runs/run-a/snapshot.json",
        "app/data/league_runtime/runs/run-a/nested/provenance.json",
    }
    assert {item["path"] for item in verified_inventory} == expected_paths
    payload_uploads = [call[-1] for call in gcloud.calls if call[:2] == ["storage", "cp"]]
    assert expected_paths <= {path.removeprefix(RUN_PREFIX + "/") for path in payload_uploads}
    assert all("--recursive" not in call for call in gcloud.calls)
    assert not (repo / "tmp" / "backup-staging" / "20260704T151500Z").exists()


def test_required_directory_rejects_nested_symlink_before_upload(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _runtime_file(repo, "run-a/snapshot.json", b"snapshot")
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"do-not-backup")
    link = repo / "app" / "data" / "league_runtime" / "runs" / "run-a" / "escape.json"
    link.symlink_to(outside)
    gcloud = FakeGcloud()

    result = _run(repo, _manifest(repo), gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["directory_symlink:app/data/league_runtime/runs/run-a/escape.json"]
    assert gcloud.calls == []


def test_directory_entry_cannot_itself_be_an_in_repo_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    target = repo / "app" / "data" / "runtime-target"
    target.mkdir(parents=True)
    (target / "snapshot.json").write_bytes(b"snapshot")
    source = repo / "app" / "data" / "league_runtime" / "runs"
    source.parent.mkdir(parents=True)
    source.symlink_to(target, target_is_directory=True)
    gcloud = FakeGcloud()

    result = _run(repo, _manifest(repo), gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["directory_symlink:app/data/league_runtime/runs"]
    assert gcloud.calls == []


def test_required_missing_directory_fails_before_auth_or_upload(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    gcloud = FakeGcloud()

    result = _run(repo, _manifest(repo), gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["missing_required:app/data/league_runtime/runs"]
    assert gcloud.calls == []


def test_directory_entry_rejects_a_regular_file_before_auth_or_upload(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    source = repo / "app" / "data" / "league_runtime" / "runs"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"not-a-directory")
    gcloud = FakeGcloud()

    result = _run(repo, _manifest(repo), gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["directory_not_directory:app/data/league_runtime/runs"]
    assert gcloud.calls == []


def test_empty_existing_directory_is_a_verified_empty_inventory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app" / "data" / "league_runtime" / "runs").mkdir(parents=True)
    gcloud = FakeGcloud()
    seen: list[list[dict[str, Any]]] = []

    result = _run(
        repo,
        _manifest(repo),
        gcloud=gcloud,
        verifier=lambda **kwargs: seen.append(kwargs["inventory"]) is None,
    )

    assert result["status"] == "completed"
    assert result["files"] == 0
    assert seen == [[]]


def test_real_restore_verifier_checks_each_expanded_directory_member() -> None:
    backup = _backup_module()
    first_path = "app/data/league_runtime/runs/run-a/snapshot.json"
    second_path = "app/data/league_runtime/runs/run-a/nested/provenance.json"
    first, second = b"snapshot", b"provenance"
    gcloud = RestoreGcloud(
        {
            f"{RUN_PREFIX}/{first_path}": first,
            f"{RUN_PREFIX}/{second_path}": second,
            f"{RUN_PREFIX}/run_inventory.json": b"{}",
        }
    )
    inventory = [
        {"path": first_path, "bytes": len(first), "sha256": hashlib.sha256(first).hexdigest()},
        {"path": second_path, "bytes": len(second), "sha256": hashlib.sha256(second).hexdigest()},
    ]

    assert backup._real_upload_verifier(
        gcloud_runner=gcloud, run_prefix=RUN_PREFIX, inventory=inventory
    )
    assert set(gcloud.downloads) == {f"{RUN_PREFIX}/{first_path}", f"{RUN_PREFIX}/{second_path}"}
