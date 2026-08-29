"""DG-100 — contract tests for the nflverse vintage-record sync channel.

The channel is additive-only against one stable prefix: each run uploads only
files the remote does not hold, verifies every upload by download + sha256,
never deletes, never overwrites, and fails closed with named reasons when
history appears to have changed (a remote object whose size differs from the
local file of the same name).

All gcloud interaction is a fake runner over an in-memory object store — no
network, no gitignored artifacts. The docstring for each test is the clause it
pins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.backup_irreplaceable_data import _real_fingerprint
from scripts.backup_nflverse_vintages import (
    MARKER_REL_PATH,
    SENTINEL_REL_PATH,
    run_vintage_sync,
)


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeGcloud:
    """In-memory gs:// object store speaking the four verbs the channel uses."""

    def __init__(self, remote: dict[str, bytes] | None = None) -> None:
        self.remote: dict[str, bytes] = dict(remote or {})
        self.calls: list[list[str]] = []
        self.fail_upload_for: set[str] = set()
        self.corrupt_download_for: set[str] = set()
        self.fail_listing = False
        self.empty_listing_error = False

    def __call__(self, args: list[str]) -> _Result:
        self.calls.append(list(args))
        if args[:2] == ["auth", "print-access-token"]:
            return _Result(0, "token")
        if args[:2] == ["storage", "ls"]:
            if self.fail_listing:
                return _Result(1, "", "PERMISSION_DENIED")
            if self.empty_listing_error or not self.remote:
                return _Result(1, "", "One or more URLs matched no objects.")
            lines = [
                f"{len(body)}  2026-08-29T00:00:00Z  {url}"
                for url, body in sorted(self.remote.items())
            ]
            return _Result(0, "\n".join(lines))
        if args[:2] == ["storage", "cp"]:
            source, destination = args[2], args[3]
            if destination.startswith("gs://"):  # upload
                if destination in self.fail_upload_for:
                    return _Result(1, "", "upload exploded")
                self.remote[destination] = Path(source).read_bytes()
                return _Result(0)
            # download
            if source in self.corrupt_download_for:
                body = b"corrupted-by-transit"
            elif source in self.remote:
                body = self.remote[source]
            else:
                return _Result(1, "", "no such object")
            Path(destination).parent.mkdir(parents=True, exist_ok=True)
            Path(destination).write_bytes(body)
            return _Result(0)
        raise AssertionError(f"unexpected gcloud verb: {args}")


BUCKET = "gs://test-bucket"
PREFIX = f"{BUCKET}/dynasty-genius/nflverse-vintages/raw"


def _fixed_now():
    from datetime import datetime, timezone

    return datetime(2026, 8, 29, 23, 0, 0, tzinfo=timezone.utc)


def _make_raw(tmp_path: Path, files: dict[str, bytes]) -> Path:
    raw = tmp_path / "repo" / "app" / "data" / "nflverse_usage" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        target = raw / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    return raw


def _run(tmp_path: Path, gcloud: FakeGcloud, **overrides: Any) -> dict[str, Any]:
    repo_root = tmp_path / "repo"
    kwargs: dict[str, Any] = dict(
        repo_root=repo_root,
        raw_root=repo_root / "app" / "data" / "nflverse_usage" / "raw",
        bucket_uri=BUCKET,
        gcloud_runner=gcloud,
        file_fingerprint=_real_fingerprint,
        now_utc=_fixed_now,
    )
    kwargs.update(overrides)
    return run_vintage_sync(**kwargs)


def _marker(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "repo" / MARKER_REL_PATH).read_text())


def test_first_sync_uploads_all_files_and_earns_verification(tmp_path: Path) -> None:
    """An empty remote receives every local file, each verified by download."""
    _make_raw(tmp_path, {"a_2025_x.json": b"aaa", "b_2026_y.json": b"bbbb"})
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud)

    assert result["status"] == "completed"
    assert result["exit_code"] == 0
    assert result["files_uploaded"] == 2
    assert result["bytes_uploaded"] == 7
    assert result["sha256_verified"] is True
    assert gcloud.remote[f"{PREFIX}/a_2025_x.json"] == b"aaa"
    assert gcloud.remote[f"{PREFIX}/b_2026_y.json"] == b"bbbb"
    marker = _marker(tmp_path)
    assert marker["status"] == "completed"
    assert marker["files_uploaded"] == 2


def test_second_sync_uploads_nothing(tmp_path: Path) -> None:
    """Idempotence: a remote that already holds every file gets zero uploads."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud({f"{PREFIX}/a.json": b"aaa"})
    result = _run(tmp_path, gcloud)

    assert result["status"] == "completed"
    assert result["files_uploaded"] == 0
    assert result["files_already_synced"] == 1
    assert not any(
        call[:2] == ["storage", "cp"] and call[3].startswith("gs://")
        for call in gcloud.calls
    )


def test_remote_size_mismatch_fails_closed_and_uploads_nothing(tmp_path: Path) -> None:
    """A same-name object with a different size means history changed — the run
    reports every such conflict, uploads NOTHING, and exits non-zero."""
    _make_raw(tmp_path, {"a.json": b"aaa", "b.json": b"bb", "new.json": b"n"})
    gcloud = FakeGcloud(
        {f"{PREFIX}/a.json": b"DIFFERENT-SIZE", f"{PREFIX}/b.json": b"xx"}
    )
    result = _run(tmp_path, gcloud)

    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert result["failures"] == ["remote_size_mismatch:a.json"]
    assert result["files_uploaded"] == 0
    assert f"{PREFIX}/new.json" not in gcloud.remote
    assert _marker(tmp_path)["sha256_verified"] is False


def test_upload_failure_is_named_and_non_zero(tmp_path: Path) -> None:
    """A failed upload is upload_failed:<key>, exit 1, failed marker."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud()
    gcloud.fail_upload_for.add(f"{PREFIX}/a.json")
    result = _run(tmp_path, gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["upload_failed:a.json"]
    assert result["exit_code"] == 1


def test_verify_download_mismatch_is_named(tmp_path: Path) -> None:
    """sha256_verified is earned: a download that does not match the local
    fingerprint fails the run with verify_mismatch:<key>."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud()
    gcloud.corrupt_download_for.add(f"{PREFIX}/a.json")
    result = _run(tmp_path, gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["verify_mismatch:a.json"]
    assert _marker(tmp_path)["sha256_verified"] is False


def test_empty_local_raw_is_a_loud_failure(tmp_path: Path) -> None:
    """The capture writes daily; an empty tree means something upstream broke.
    Protecting nothing must never read as success (the DGX-02 principle)."""
    _make_raw(tmp_path, {})
    result = _run(tmp_path, FakeGcloud())

    assert result["status"] == "failed"
    assert result["failures"] == ["empty_local_raw"]


def test_missing_raw_root_is_named(tmp_path: Path) -> None:
    """A missing tree is missing_raw_root:*, never a bare traceback."""
    (tmp_path / "repo").mkdir()
    result = _run(tmp_path, FakeGcloud())

    assert result["status"] == "failed"
    assert result["failures"] and result["failures"][0].startswith("missing_raw_root:")


def test_dry_run_uploads_nothing_and_writes_no_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run prints the plan and mutates nothing: no uploads, no marker,
    no sentinel."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud, dry_run=True)

    assert result == {"status": "dry_run", "exit_code": 0}
    plan = json.loads(capsys.readouterr().out)
    assert plan["planned_uploads"] == ["a.json"]
    assert gcloud.remote == {}
    assert not (tmp_path / "repo" / MARKER_REL_PATH).exists()
    assert not (tmp_path / "repo" / SENTINEL_REL_PATH).exists()


def test_failing_dry_run_writes_no_marker_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dry run that finds a conflict reports it and exits 1 — but still
    mutates NOTHING: no marker (it would clobber the last real run's record),
    no sentinel, no uploads."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud({f"{PREFIX}/a.json": b"DIFFERENT-SIZE"})
    result = _run(tmp_path, gcloud, dry_run=True)

    assert result["status"] == "dry_run_failed"
    assert result["exit_code"] == 1
    assert result["failures"] == ["remote_size_mismatch:a.json"]
    report = json.loads(capsys.readouterr().out)
    assert report["failures"] == ["remote_size_mismatch:a.json"]
    assert not (tmp_path / "repo" / MARKER_REL_PATH).exists()
    assert not (tmp_path / "repo" / SENTINEL_REL_PATH).exists()


def test_no_match_listing_is_an_empty_remote_not_a_failure(tmp_path: Path) -> None:
    """gcloud's 'matched no objects' on the first-ever run is the empty remote,
    not remote_list_failed."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud()
    gcloud.empty_listing_error = True
    result = _run(tmp_path, gcloud)

    assert result["status"] == "completed"
    assert result["files_uploaded"] == 1


def test_listing_failure_is_named(tmp_path: Path) -> None:
    """Any other non-zero listing is remote_list_failed — never treated empty,
    or every run would re-upload the world."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud({f"{PREFIX}/a.json": b"aaa"})
    gcloud.fail_listing = True
    result = _run(tmp_path, gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["remote_list_failed"]


def test_unexpected_exception_still_writes_the_marker(tmp_path: Path) -> None:
    """Fail closed on anything unforeseen: unexpected:<type>, marker written."""
    _make_raw(tmp_path, {"a.json": b"aaa"})

    def _exploding_runner(args: list[str]) -> Any:
        raise RuntimeError("boom")

    result = _run(tmp_path, _exploding_runner)

    assert result["status"] == "failed"
    assert result["failures"] == ["unexpected:RuntimeError"]
    assert _marker(tmp_path)["status"] == "failed"


def test_symlink_in_raw_is_rejected(tmp_path: Path) -> None:
    """A symlink under raw/ would upload bytes the tree does not hold — every
    one is reported, nothing uploads (the DG-048 symlink lesson)."""
    raw = _make_raw(tmp_path, {"a.json": b"aaa"})
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    (raw / "link.json").symlink_to(outside)
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["raw_symlink:link.json"]
    assert gcloud.remote == {}


def test_max_uploads_cap_is_recorded_never_silent(tmp_path: Path) -> None:
    """A capped run says exactly how many files it deferred — a bounded smoke
    run must never read as full coverage."""
    _make_raw(tmp_path, {"a.json": b"a", "b.json": b"b", "c.json": b"c"})
    result = _run(tmp_path, FakeGcloud(), max_uploads=2)

    assert result["status"] == "completed"
    assert result["files_uploaded"] == 2
    assert result["files_skipped_by_cap"] == 1
    assert _marker(tmp_path)["files_skipped_by_cap"] == 1


def test_nested_files_keep_their_relative_keys(tmp_path: Path) -> None:
    """If the raw tree ever nests, keys mirror the tree — no flattening."""
    _make_raw(tmp_path, {"2027/a.json": b"aaa"})
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud)

    assert result["status"] == "completed"
    assert f"{PREFIX}/2027/a.json" in gcloud.remote


def test_sentinel_written_before_work_and_survives(tmp_path: Path) -> None:
    """The run-active sentinel is written at start and never deleted — the
    only local record that a killed run ever began."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    _run(tmp_path, FakeGcloud())

    sentinel = json.loads((tmp_path / "repo" / SENTINEL_REL_PATH).read_text())
    assert sentinel["run_id"] == "20260829T230000Z"
    assert isinstance(sentinel["pid"], int)
