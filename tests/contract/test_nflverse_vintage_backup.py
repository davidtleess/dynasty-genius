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
import os
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
            # Positional operands only — the runner passes flags (--no-clobber)
            # before them, so indexing args[2:4] blindly would read a flag.
            source, destination = [a for a in args[2:] if not a.startswith("--")]
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


def _age(path: Path, seconds: float) -> None:
    """Backdate a file past the quiesce window (fixtures write files 'now')."""
    stamp = _fixed_now().timestamp() - seconds
    os.utime(path, (stamp, stamp))


def _age_tree(raw: Path, seconds: float = 3600.0) -> None:
    for member in raw.rglob("*"):
        if member.is_file() and not member.is_symlink():
            _age(member, seconds)


def _run(tmp_path: Path, gcloud: FakeGcloud, **overrides: Any) -> dict[str, Any]:
    repo_root = tmp_path / "repo"
    raw = repo_root / "app" / "data" / "nflverse_usage" / "raw"
    if raw.is_dir() and "quiesce_seconds" not in overrides:
        # Fixtures create files at wall-clock now; the run's clock is fixed at
        # 2026-08-29T23:00Z, so ages are meaningless unless backdated. Tests
        # that exercise the quiesce gate itself pass quiesce_seconds explicitly.
        _age_tree(raw)
    kwargs: dict[str, Any] = dict(
        repo_root=repo_root,
        raw_root=raw,
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


def test_a_freshly_written_snapshot_is_deferred_not_uploaded(tmp_path: Path) -> None:
    """BLOCKING-class guard: the 06:15 capture writes raw snapshots with a plain
    write_text, so a file younger than the quiesce window may hold only part of
    its bytes. Uploading it would store a truncated vintage permanently and then
    trip remote_size_mismatch forever. It is deferred to the next run instead."""
    raw = _make_raw(tmp_path, {"settled.json": b"aaa", "still_writing.json": b"partial"})
    _age(raw / "settled.json", 3600.0)  # yesterday's snapshot
    _age(raw / "still_writing.json", 5.0)  # written five seconds ago
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud, quiesce_seconds=300.0)

    assert result["status"] == "completed"
    assert result["files_uploaded"] == 1
    assert f"{PREFIX}/settled.json" in gcloud.remote
    assert f"{PREFIX}/still_writing.json" not in gcloud.remote
    assert result["deferred_unstable"] == ["still_writing.json"]
    assert _marker(tmp_path)["files_deferred_unstable"] == 1


def test_a_file_changing_during_its_fingerprint_is_deferred(tmp_path: Path) -> None:
    """The quiesce gate cannot see a write that STARTS mid-hash; the
    before/after stat comparison catches it, and it is checked before the
    upload so nothing partial is ever stored."""
    raw = _make_raw(tmp_path, {"a.json": b"aaa"})
    target = raw / "a.json"

    def _mutating_fingerprint(path: Path) -> tuple[int, str]:
        result = _real_fingerprint(path)
        if path == target:  # a writer lands while we were hashing
            path.write_bytes(b"aaaa-grown")
            _age(path, 3600.0)
        return result

    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud, file_fingerprint=_mutating_fingerprint)

    assert result["status"] == "completed"
    assert result["files_uploaded"] == 0
    assert result["deferred_unstable"] == ["a.json"]
    assert gcloud.remote == {}


def test_dotfiles_are_skipped_and_counted(tmp_path: Path) -> None:
    """Finder's .DS_Store is not a vintage. Uploading it would make a junk file
    a permanent remote object whose later size change stops the whole channel."""
    _make_raw(tmp_path, {"a.json": b"aaa", ".DS_Store": b"junk"})
    gcloud = FakeGcloud()
    result = _run(tmp_path, gcloud)

    assert result["files_uploaded"] == 1
    assert f"{PREFIX}/.DS_Store" not in gcloud.remote
    assert result["files_skipped_dotfiles"] == 1


def test_unparseable_listing_fails_closed(tmp_path: Path) -> None:
    """If gcloud's --long format ever drifts, output we cannot parse must NOT
    read as an empty remote — that would re-upload the tree over itself nightly
    and kill the remote_size_mismatch tripwire."""
    _make_raw(tmp_path, {"a.json": b"aaa"})

    class DriftedGcloud(FakeGcloud):
        def __call__(self, args: list[str]) -> _Result:
            if args[:2] == ["storage", "ls"]:
                return _Result(0, "TOTAL: 1 objects, 3 bytes\nsome-new-format-line")
            return super().__call__(args)

    result = _run(tmp_path, DriftedGcloud({f"{PREFIX}/a.json": b"aaa"}))

    assert result["status"] == "failed"
    assert result["failures"] == ["remote_list_unparseable"]


def test_uploads_pass_no_clobber(tmp_path: Path) -> None:
    """Append-only, belt and braces: an object that somehow re-enters the plan
    must be skipped by gcloud rather than overwriting stored history."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    gcloud = FakeGcloud()
    _run(tmp_path, gcloud)

    uploads = [
        call
        for call in gcloud.calls
        if call[:2] == ["storage", "cp"] and call[-1].startswith("gs://")
    ]
    assert uploads and all("--no-clobber" in call for call in uploads)


def test_sentinel_written_before_work_and_survives(tmp_path: Path) -> None:
    """The run-active sentinel is written at start and never deleted — the
    only local record that a killed run ever began."""
    _make_raw(tmp_path, {"a.json": b"aaa"})
    _run(tmp_path, FakeGcloud())

    sentinel = json.loads((tmp_path / "repo" / SENTINEL_REL_PATH).read_text())
    assert sentinel["run_id"] == "20260829T230000Z"
    assert isinstance(sentinel["pid"], int)
