"""H0-0a offsite backup RED contracts.

The backup implementation must be testable without network access or local
gitignored artifacts. These tests define the script seam expected by the v2
design spec:

``scripts.backup_irreplaceable_data.run_backup(...)`` with injectable gcloud,
sqlite-backup, file-fingerprint, upload-verification, clock, and sleep seams.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

MODULE_NAME = "scripts.backup_irreplaceable_data"
BUCKET = "gs://dynasty-genius-backup-dtl"
BANNED_MARKER_TOKENS = ("recommended", "safe", "must", "buy", "sell", "hold")


def _backup_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None, f"Expected {MODULE_NAME} to exist for H0-0a GREEN"
    return importlib.import_module(MODULE_NAME)


class FakeGcloud:
    def __init__(self, *, auth_fails: bool = False) -> None:
        self.auth_fails = auth_fails
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> SimpleNamespace:
        normalized = [str(arg) for arg in args]
        self.calls.append(normalized)
        if "auth" in normalized and "print-access-token" in normalized:
            if self.auth_fails:
                return SimpleNamespace(
                    returncode=1, stdout="", stderr="auth unavailable"
                )
            return SimpleNamespace(returncode=0, stdout="fake-token\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def command_text(self) -> str:
        return "\n".join(" ".join(call) for call in self.calls)

    def latest_pointer_calls(self) -> list[list[str]]:
        return [call for call in self.calls if "latest.json" in " ".join(call)]


class Fingerprints:
    def __init__(self, values: dict[str, list[tuple[int, str]]] | None = None) -> None:
        self.values = {key: list(value) for key, value in (values or {}).items()}

    def __call__(self, path: Path) -> tuple[int, str]:
        key = path.name
        if key in self.values and self.values[key]:
            return self.values[key].pop(0)
        data = path.read_bytes()
        return (len(data), f"sha256:{len(data)}:{data[:12].hex()}")


class FakeRestoreGcloud:
    def __init__(
        self,
        *,
        run_prefix: str,
        remote_bytes: dict[str, bytes],
        download_fails: bool = False,
    ) -> None:
        self.run_prefix = run_prefix
        self.remote_bytes = remote_bytes
        self.download_fails = download_fails
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> SimpleNamespace:
        normalized = [str(arg) for arg in args]
        self.calls.append(normalized)
        if normalized[:3] == ["storage", "ls", "--long"]:
            lines = [
                f"{len(payload)}  2026-07-04T15:15:00Z  {remote_path}"
                for remote_path, payload in sorted(self.remote_bytes.items())
            ]
            return SimpleNamespace(returncode=0, stdout="\n".join(lines), stderr="")
        if normalized[:2] == ["storage", "cp"] and normalized[2].startswith("gs://"):
            if self.download_fails:
                return SimpleNamespace(returncode=1, stdout="", stderr="download failed")
            source = normalized[2]
            destination = Path(normalized[3])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.remote_bytes[source])
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def download_calls(self) -> list[list[str]]:
        return [
            call
            for call in self.calls
            if call[:2] == ["storage", "cp"] and call[2].startswith("gs://")
        ]


def _value(result: Any, key: str) -> Any:
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key)


def _assert_failed(result: Any) -> None:
    assert _value(result, "status") == "failed"
    assert _value(result, "exit_code") != 0


def _write_manifest(
    repo: Path,
    entries: list[dict[str, Any]],
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    manifest = {
        "schema_version": "backup_manifest.v1",
        "required": entries,
        "optional": [],
        "exclude_paths": ["app/data/ops/backup_status_latest.json"],
        **(extra or {}),
    }
    path = repo / "app" / "config" / "backup_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, sort_keys=True))
    return path


def _seed_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    data = repo / "app" / "data"
    data.mkdir(parents=True)
    db = data / "fc_forward_capture.db"
    db.write_bytes(b"sqlite fixture")
    non_db = data / "training" / "engine_b_features_v2.csv"
    non_db.parent.mkdir(parents=True)
    non_db.write_text("player_id,ppg_t\n1,12.3\n")
    return repo, db, non_db


def _entries(db: Path, non_db: Path, repo: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": db.relative_to(repo).as_posix(),
            "required": True,
            "kind": "sqlite",
        },
        {
            "path": non_db.relative_to(repo).as_posix(),
            "required": True,
            "kind": "file",
        },
    ]


def _sqlite_backup(calls: list[tuple[Path, Path]]):
    def backup(source: Path, destination: Path) -> None:
        calls.append((source, destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    return backup


def _run_backup(
    *,
    repo: Path,
    manifest: Path,
    gcloud: FakeGcloud | None = None,
    sqlite_calls: list[tuple[Path, Path]] | None = None,
    fingerprinter: Fingerprints | None = None,
    upload_verified: bool = True,
    staging_root: Path | None = None,
) -> Any:
    backup = _backup_module()
    gcloud = gcloud or FakeGcloud()
    sqlite_calls = sqlite_calls if sqlite_calls is not None else []
    return backup.run_backup(
        repo_root=repo,
        manifest_path=manifest,
        bucket_uri=BUCKET,
        staging_root=staging_root or (repo / "tmp" / "backup-staging"),
        gcloud_runner=gcloud,
        sqlite_backup_runner=_sqlite_backup(sqlite_calls),
        file_fingerprint=fingerprinter or Fingerprints(),
        upload_verifier=lambda *_args, **_kwargs: upload_verified,
        sleep=lambda _seconds: None,
        now_utc=lambda: datetime(2026, 7, 4, 15, 15, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "bad_entry",
    [
        {"path": "/private/tmp/escaped.db", "required": True, "kind": "file"},
        {"path": "../escaped.db", "required": True, "kind": "file"},
    ],
)
def test_manifest_path_safety_rejects_absolute_and_traversal_before_copy(
    tmp_path: Path, bad_entry: dict[str, Any]
) -> None:
    repo, _db, _non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, [bad_entry])
    gcloud = FakeGcloud()
    sqlite_calls: list[tuple[Path, Path]] = []

    result = _run_backup(
        repo=repo, manifest=manifest, gcloud=gcloud, sqlite_calls=sqlite_calls
    )

    _assert_failed(result)
    assert gcloud.calls == []
    assert sqlite_calls == []


def test_manifest_path_safety_rejects_symlink_escape_before_copy(tmp_path: Path) -> None:
    repo, _db, _non_db = _seed_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    escaped = outside / "secret.csv"
    escaped.write_text("do-not-copy")
    symlink = repo / "app" / "data" / "escaped.csv"
    symlink.symlink_to(escaped)
    manifest = _write_manifest(
        repo, [{"path": "app/data/escaped.csv", "required": True, "kind": "file"}]
    )
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    _assert_failed(result)
    assert gcloud.calls == []


def test_missing_required_file_fails_marker_and_does_not_upload(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    missing = repo / "app" / "data" / "missing_required.csv"
    manifest = _write_manifest(
        repo,
        [
            *_entries(db, non_db, repo),
            {
                "path": missing.relative_to(repo).as_posix(),
                "required": True,
                "kind": "file",
            },
        ],
    )
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    _assert_failed(result)
    marker = repo / "app" / "data" / "ops" / "backup_status_latest.json"
    assert json.loads(marker.read_text())["status"] == "failed"
    assert not any("storage" in call for call in gcloud.command_text().splitlines())


def test_manifest_malformed_or_unknown_keys_fail_before_copy(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(
        repo,
        _entries(db, non_db, repo),
        extra={"unexpected_key": True},
    )
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    _assert_failed(result)
    assert gcloud.calls == []


@pytest.mark.parametrize(
    "manifest_extra,entries",
    [
        (
            None,
            [{"path": "app/data/training/engine_b_features_v2.csv", "required": "yes", "kind": "file"}],
        ),
        (
            {"exclude_paths": [17]},
            [{"path": "app/data/training/engine_b_features_v2.csv", "required": True, "kind": "file"}],
        ),
    ],
)
def test_manifest_rejects_wrong_value_types_before_copy(
    tmp_path: Path,
    manifest_extra: dict[str, Any] | None,
    entries: list[dict[str, Any]],
) -> None:
    repo, _db, _non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, entries, extra=manifest_extra)
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    _assert_failed(result)
    assert gcloud.calls == []


def test_non_db_instability_after_retry_fails_without_upload_or_pointer(
    tmp_path: Path,
) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    gcloud = FakeGcloud()
    fingerprinter = Fingerprints(
        {
            non_db.name: [
                (10, "sha256:first"),
                (11, "sha256:second"),
                (12, "sha256:third"),
                (13, "sha256:fourth"),
            ]
        }
    )

    result = _run_backup(
        repo=repo,
        manifest=manifest,
        gcloud=gcloud,
        fingerprinter=fingerprinter,
    )

    _assert_failed(result)
    assert "storage" not in gcloud.command_text()
    assert gcloud.latest_pointer_calls() == []


def test_sqlite_files_use_backup_runner_for_consistent_snapshot(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    sqlite_calls: list[tuple[Path, Path]] = []

    result = _run_backup(repo=repo, manifest=manifest, sqlite_calls=sqlite_calls)

    assert _value(result, "status") == "completed"
    assert sqlite_calls
    assert sqlite_calls[0][0] == db
    assert sqlite_calls[0][1].name == db.name


def test_gcloud_auth_failure_fails_and_does_not_update_latest_pointer(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    gcloud = FakeGcloud(auth_fails=True)

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    _assert_failed(result)
    assert any("auth print-access-token" in " ".join(call) for call in gcloud.calls)
    assert gcloud.latest_pointer_calls() == []


def test_upload_verification_failure_halts_latest_pointer_update(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    gcloud = FakeGcloud()

    result = _run_backup(
        repo=repo,
        manifest=manifest,
        gcloud=gcloud,
        upload_verified=False,
    )

    _assert_failed(result)
    assert any("storage" in " ".join(call) for call in gcloud.calls)
    assert gcloud.latest_pointer_calls() == []


def test_successful_run_never_constructs_delete_or_mirror_mutations(
    tmp_path: Path,
) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    assert _value(result, "status") == "completed"
    command_text = gcloud.command_text()
    assert "--delete-unmatched-destination-objects" not in command_text
    assert " rsync " not in f" {command_text} "
    assert " rm " not in f" {command_text} "
    assert gcloud.latest_pointer_calls(), "latest pointer updates only after verification"


def test_successful_run_uploads_each_file_to_exact_manifest_key(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    gcloud = FakeGcloud()

    result = _run_backup(repo=repo, manifest=manifest, gcloud=gcloud)

    assert _value(result, "status") == "completed"
    run_prefix = f"{BUCKET}/dynasty-genius/runs/20260704T151500Z"
    storage_cp_calls = [
        call for call in gcloud.calls if call[:2] == ["storage", "cp"]
    ]
    payload_uploads = [
        call for call in storage_cp_calls if call[-1].startswith(run_prefix + "/")
    ]
    assert ["storage", "cp", "--recursive", str(repo / "tmp" / "backup-staging" / "20260704T151500Z"), run_prefix] not in gcloud.calls
    assert sorted(call[-1] for call in payload_uploads) == sorted(
        [
            f"{run_prefix}/app/data/fc_forward_capture.db",
            f"{run_prefix}/app/data/training/engine_b_features_v2.csv",
            f"{run_prefix}/run_inventory.json",
        ]
    )


def test_marker_write_failure_returns_nonzero_and_cleans_staging(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    marker_parent = repo / "app" / "data" / "ops"
    marker_parent.parent.mkdir(parents=True, exist_ok=True)
    marker_parent.write_text("not-a-directory")
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    staging_root = tmp_path / "staging"

    result = _run_backup(repo=repo, manifest=manifest, staging_root=staging_root)

    _assert_failed(result)
    assert not staging_root.exists() or not any(staging_root.iterdir())


def test_real_upload_verifier_downloads_and_compares_sha256() -> None:
    backup = _backup_module()
    run_prefix = f"{BUCKET}/dynasty-genius/runs/20260704T151500Z"
    remote_key = f"{run_prefix}/app/data/training/engine_b_features_v2.csv"
    payload = b"player_id,ppg_t\n1,12.3\n"
    gcloud = FakeRestoreGcloud(
        run_prefix=run_prefix,
        remote_bytes={
            remote_key: payload,
            f"{run_prefix}/run_inventory.json": b"{}",
        },
    )

    assert backup._real_upload_verifier(
        gcloud_runner=gcloud,
        run_prefix=run_prefix,
        inventory=[
            {
                "path": "app/data/training/engine_b_features_v2.csv",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    )
    assert gcloud.download_calls(), "real verifier must restore bytes before trusting sha256"


def test_real_upload_verifier_rejects_sha256_mismatch() -> None:
    backup = _backup_module()
    run_prefix = f"{BUCKET}/dynasty-genius/runs/20260704T151500Z"
    remote_key = f"{run_prefix}/app/data/training/engine_b_features_v2.csv"
    payload = b"same-size-wrong-content"
    gcloud = FakeRestoreGcloud(
        run_prefix=run_prefix,
        remote_bytes={
            remote_key: payload,
            f"{run_prefix}/run_inventory.json": b"{}",
        },
    )

    assert not backup._real_upload_verifier(
        gcloud_runner=gcloud,
        run_prefix=run_prefix,
        inventory=[
            {
                "path": "app/data/training/engine_b_features_v2.csv",
                "bytes": len(payload),
                "sha256": hashlib.sha256(b"different-wrong-bytes").hexdigest(),
            }
        ],
    )


def test_real_upload_verifier_rejects_download_failure() -> None:
    backup = _backup_module()
    run_prefix = f"{BUCKET}/dynasty-genius/runs/20260704T151500Z"
    remote_key = f"{run_prefix}/app/data/training/engine_b_features_v2.csv"
    payload = b"player_id,ppg_t\n1,12.3\n"
    gcloud = FakeRestoreGcloud(
        run_prefix=run_prefix,
        remote_bytes={
            remote_key: payload,
            f"{run_prefix}/run_inventory.json": b"{}",
        },
        download_fails=True,
    )

    assert not backup._real_upload_verifier(
        gcloud_runner=gcloud,
        run_prefix=run_prefix,
        inventory=[
            {
                "path": "app/data/training/engine_b_features_v2.csv",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    )


def test_gitignore_excludes_ops_marker_and_staging() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    gitignore = (repo_root / ".gitignore").read_text()

    assert "app/data/ops/" in gitignore or (
        "app/data/ops/backup_status_latest.json" in gitignore
        and "app/data/ops/backup_staging" in gitignore
    )


def test_status_marker_lives_under_ops_excludes_payload_and_avoids_banned_tokens(
    tmp_path: Path,
) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    staging_root = tmp_path / "staging"

    result = _run_backup(repo=repo, manifest=manifest, staging_root=staging_root)

    assert _value(result, "status") == "completed"
    marker = repo / "app" / "data" / "ops" / "backup_status_latest.json"
    assert marker.exists()
    marker_text = marker.read_text().lower()
    for token in BANNED_MARKER_TOKENS:
        assert token not in marker_text
    manifest_payload = json.loads(manifest.read_text())
    assert all(
        entry["path"] != "app/data/ops/backup_status_latest.json"
        for entry in manifest_payload["required"]
    )
    assert not staging_root.exists() or not any(staging_root.iterdir())
