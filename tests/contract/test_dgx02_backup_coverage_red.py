"""RED contract for DGX-02 — backup coverage expansion + silent-failure guard.

Two halves, both required by the ticket:

(a) Coverage. The four named irreplaceable files, the ``app/data/league_snapshots/``
    snapshot + coverage globs, and the raw PFF exports must be inside the manifest.
    Sleeper's players API exposes only the current date, so an unbacked past
    snapshot is gone forever.

(b) The silent-failure guard. A run that stages ZERO files protects nothing, and
    a backup that protects nothing must say so: it must fail loudly, non-zero,
    with ``sha256_verified`` false and no ``latest.json`` pointer advance.

    Before this contract the opposite was true and was pinned by a committed test
    (``test_backup_directory_red.py::test_empty_existing_directory_is_a_verified_
    empty_inventory``): a manifest expanding to nothing returned ``completed``,
    ``files == 0``, ``sha256_verified == true``, exit 0 — the exact shape of a
    backup that silently protects nothing. That row is inverted by this contract
    under David's 2026-07-27 word.

Coverage assertions are structural (they read the committed manifest) plus a
live-state sweep that is vacuously true in a fresh clone, so the suite never
depends on gitignored artifacts being present.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_MANIFEST = REPO_ROOT / "app" / "config" / "backup_manifest.json"
MODULE_NAME = "scripts.backup_irreplaceable_data"
BUCKET = "gs://dynasty-genius-backup-dtl"

# The ticket's five entries: four named files, plus the league-snapshot glob set.
DGX02_NAMED_FILES = (
    "app/data/prospect_identity_review.jsonl",
    "app/data/pff_exports/phase16_wr_manual_review.csv",
    "app/data/pff_exports/phase16_wr_manifest.json",
    "app/data/pff_exports/phase13_te_v10_plus_manifest.json",
)
LEAGUE_SNAPSHOT_DIR = "app/data/league_snapshots"
PFF_EXPORT_DIR = "app/data/pff_exports"


def _backup_module():
    return importlib.import_module(MODULE_NAME)


def _manifest_payload() -> dict[str, Any]:
    return json.loads(BACKUP_MANIFEST.read_text())


def _required_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry for entry in payload["required"] if entry.get("required") is True]


def _covered_by_required(rel_path: str, payload: dict[str, Any]) -> bool:
    """True when a required entry protects ``rel_path`` exactly or as an ancestor."""
    for entry in _required_entries(payload):
        entry_path = entry["path"]
        if entry_path == rel_path:
            return True
        if entry["kind"] == "directory" and rel_path.startswith(entry_path + "/"):
            return True
    return False


# ── (a) coverage ─────────────────────────────────────────────────────────────


def test_manifest_covers_the_four_named_irreplaceable_files() -> None:
    payload = _manifest_payload()
    uncovered = [
        path for path in DGX02_NAMED_FILES if not _covered_by_required(path, payload)
    ]
    assert uncovered == [], f"DGX-02 named files outside the backup manifest: {uncovered}"


def test_manifest_covers_the_league_snapshot_and_coverage_glob_set() -> None:
    payload = _manifest_payload()
    probe = f"{LEAGUE_SNAPSHOT_DIR}/sleeper_universe_snapshot_phase17-20260522T024055Z.json"
    coverage_probe = f"{LEAGUE_SNAPSHOT_DIR}/sleeper_universe_coverage_latest.json"
    assert _covered_by_required(probe, payload), (
        "past league snapshots are unobtainable from Sleeper and must be covered"
    )
    assert _covered_by_required(coverage_probe, payload)


def test_manifest_covers_the_raw_pff_export_tree() -> None:
    payload = _manifest_payload()
    probe = f"{PFF_EXPORT_DIR}/some_future_raw_export.csv"
    assert _covered_by_required(probe, payload), (
        "the raw PFF export tree must be covered as a tree, not file-by-file"
    )


def test_every_present_file_in_the_named_trees_is_covered() -> None:
    """Live sweep. Vacuously true in a fresh clone; binding on the backup host."""
    payload = _manifest_payload()
    uncovered: list[str] = []
    for tree in (LEAGUE_SNAPSHOT_DIR, PFF_EXPORT_DIR):
        root = REPO_ROOT / tree
        if not root.is_dir():
            continue
        for member in sorted(root.rglob("*")):
            if member.is_file():
                rel = member.relative_to(REPO_ROOT).as_posix()
                if not _covered_by_required(rel, payload):
                    uncovered.append(rel)
    assert uncovered == [], f"present irreplaceable files outside the manifest: {uncovered}"


# ── (b) the silent-failure guard ─────────────────────────────────────────────


class FakeGcloud:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> SimpleNamespace:
        self.calls.append([str(value) for value in args])
        return SimpleNamespace(returncode=0, stdout="token\n", stderr="")


def _write_manifest(repo: Path, required: list[dict[str, Any]], optional=None) -> Path:
    path = repo / "app" / "config" / "backup_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "backup_manifest.v2",
                "required": required,
                "optional": optional or [],
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


def _run(repo: Path, manifest: Path, *, gcloud: FakeGcloud) -> dict[str, Any]:
    backup = _backup_module()
    return backup.run_backup(
        repo_root=repo,
        manifest_path=manifest,
        bucket_uri=BUCKET,
        staging_root=repo / "tmp" / "backup-staging",
        gcloud_runner=gcloud,
        sqlite_backup_runner=lambda _source, _destination: None,
        file_fingerprint=lambda path: (
            len(path.read_bytes()),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        ),
        upload_verifier=lambda **_kwargs: True,
        sleep=lambda _seconds: None,
        now_utc=lambda: datetime(2026, 7, 27, 14, 15, tzinfo=timezone.utc),
    )


def _empty_optional_directory(repo: Path) -> list[dict[str, Any]]:
    """An OPTIONAL empty directory: expands to zero units without its own failure,
    so it isolates the run-wide empty-inventory guard from the per-store one."""
    (repo / "app" / "data" / "league_snapshots").mkdir(parents=True)
    return [
        {"path": "app/data/league_snapshots", "required": False, "kind": "directory"}
    ]


def test_run_staging_zero_files_fails_loudly_and_non_zero(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    manifest = _write_manifest(repo, [], optional=_empty_optional_directory(repo))
    gcloud = FakeGcloud()

    result = _run(repo, manifest, gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert result["sha256_verified"] is False
    assert result["failures"] == ["empty_inventory"]


def test_zero_file_run_touches_no_bucket_at_all(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    manifest = _write_manifest(repo, [], optional=_empty_optional_directory(repo))
    gcloud = FakeGcloud()

    _run(repo, manifest, gcloud=gcloud)

    assert gcloud.calls == [], "a run protecting nothing must not advance latest.json"


# ── the fold-in: per-required-store coverage ─────────────────────────────────
#
# David's word, TW27G, 2026-07-27: "FOLD IN the required-directory-empty gap now.
# Your §4: a required directory that expands to zero files must fail loudly, not
# ride along silently while other entries contribute files."


def test_required_directory_expanding_to_zero_files_fails_loudly(tmp_path: Path) -> None:
    """The disaster this ticket exists to survive.

    If ``app/data/league_snapshots/`` were emptied, the run-wide empty-inventory
    guard would NOT fire — the other entries still contribute files — so the run
    would report completed with sha256_verified true while protecting nothing of
    that store. A required entry asserts "this store must be protected"; zero
    files means it is not.
    """
    repo = tmp_path / "repo"
    (repo / "app" / "data" / "league_snapshots").mkdir(parents=True)
    real = repo / "app" / "data" / "prospect_identity_review.jsonl"
    real.write_bytes(b'{"player": 1}\n')
    manifest = _write_manifest(
        repo,
        [
            {"path": "app/data/league_snapshots", "required": True, "kind": "directory"},
            {
                "path": "app/data/prospect_identity_review.jsonl",
                "required": True,
                "kind": "file",
            },
        ],
    )
    gcloud = FakeGcloud()

    result = _run(repo, manifest, gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert result["sha256_verified"] is False
    assert result["failures"] == ["directory_empty_required:app/data/league_snapshots"]
    assert gcloud.calls == [], "an unprotected required store must not advance the pointer"


# ── r3: required-store truth must not depend on manifest order ───────────────
#
# Codex r2 NOT CLEAR (HIGH): the per-directory guard raised inside the entry loop,
# so the FIRST failing required entry was the only one reported and every later
# required entry went unvalidated. Reversing manifest order reversed the reported
# reason — a required-store defect could go silent purely because another entry
# was declared before it. That is the disease this ticket exists to cure,
# reintroduced by its own fix.


def _failing_entries(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """One empty required directory and one missing required file."""
    (repo / "app" / "data" / "empty").mkdir(parents=True)
    return (
        {"path": "app/data/empty", "required": True, "kind": "directory"},
        {"path": "app/data/missing.json", "required": True, "kind": "file"},
    )


def test_required_failures_do_not_depend_on_manifest_order(tmp_path: Path) -> None:
    """Codex's exact reproduction: reversing declaration order must change nothing."""
    forward_repo = tmp_path / "forward"
    empty_dir, missing_file = _failing_entries(forward_repo)
    forward = _run(
        forward_repo,
        _write_manifest(forward_repo, [empty_dir, missing_file]),
        gcloud=FakeGcloud(),
    )

    reverse_repo = tmp_path / "reverse"
    empty_dir, missing_file = _failing_entries(reverse_repo)
    reverse = _run(
        reverse_repo,
        _write_manifest(reverse_repo, [missing_file, empty_dir]),
        gcloud=FakeGcloud(),
    )

    assert forward["failures"] == reverse["failures"], (
        "manifest ordering must not decide which required-store failure is reported"
    )
    assert forward["status"] == reverse["status"] == "failed"


def test_every_required_store_failure_is_reported_not_just_the_first(
    tmp_path: Path,
) -> None:
    """Three simultaneous required-store defects; the marker must name all three."""
    repo = tmp_path / "repo"
    (repo / "app" / "data" / "empty").mkdir(parents=True)
    wrong_kind = repo / "app" / "data" / "wrong"
    wrong_kind.parent.mkdir(parents=True, exist_ok=True)
    wrong_kind.write_bytes(b"i am a file, declared a directory")
    manifest = _write_manifest(
        repo,
        [
            {"path": "app/data/empty", "required": True, "kind": "directory"},
            {"path": "app/data/missing.json", "required": True, "kind": "file"},
            {"path": "app/data/wrong", "required": True, "kind": "directory"},
        ],
    )

    result = _run(repo, manifest, gcloud=FakeGcloud())

    assert result["status"] == "failed"
    assert set(result["failures"]) == {
        "directory_empty_required:app/data/empty",
        "missing_required:app/data/missing.json",
        "directory_not_directory:app/data/wrong",
    }


def test_a_single_required_failure_still_reports_exactly_one_reason(
    tmp_path: Path,
) -> None:
    """Regression guard: collecting failures must not inflate the single-failure shape,
    which the pre-existing horizon0 contract rows assert exactly."""
    repo = tmp_path / "repo"
    (repo / "app" / "data").mkdir(parents=True)
    manifest = _write_manifest(
        repo,
        [{"path": "app/data/missing.json", "required": True, "kind": "file"}],
    )

    result = _run(repo, manifest, gcloud=FakeGcloud())

    assert result["failures"] == ["missing_required:app/data/missing.json"]


def test_optional_directory_expanding_to_zero_files_is_tolerated(tmp_path: Path) -> None:
    """`required: false` means exactly that — an empty optional store is not a failure."""
    repo = tmp_path / "repo"
    (repo / "app" / "data" / "league_snapshots").mkdir(parents=True)
    real = repo / "app" / "data" / "prospect_identity_review.jsonl"
    real.write_bytes(b'{"player": 1}\n')
    manifest = _write_manifest(
        repo,
        [
            {
                "path": "app/data/prospect_identity_review.jsonl",
                "required": True,
                "kind": "file",
            }
        ],
        optional=[
            {"path": "app/data/league_snapshots", "required": False, "kind": "directory"}
        ],
    )

    result = _run(repo, manifest, gcloud=FakeGcloud())

    assert result["status"] == "completed"
    assert result["files"] == 1


def test_manifest_with_no_entries_fails_loudly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    manifest = _write_manifest(repo, [])
    gcloud = FakeGcloud()

    result = _run(repo, manifest, gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["failures"] == ["empty_inventory"]


def test_all_optional_sources_missing_fails_loudly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    manifest = _write_manifest(
        repo,
        [],
        optional=[
            {"path": "app/data/absent.csv", "required": False, "kind": "file"},
        ],
    )
    gcloud = FakeGcloud()

    result = _run(repo, manifest, gcloud=gcloud)

    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert result["sha256_verified"] is False
    assert "empty_inventory" in result["failures"]


def test_zero_file_marker_on_disk_says_failed_and_unverified(tmp_path: Path) -> None:
    """The marker is the truth surface — it must carry the failure, not just the return."""
    repo = tmp_path / "repo"
    manifest = _write_manifest(repo, [], optional=_empty_optional_directory(repo))

    _run(repo, manifest, gcloud=FakeGcloud())

    marker = json.loads((repo / "app/data/ops/backup_status_latest.json").read_text())
    assert marker["status"] == "failed"
    assert marker["sha256_verified"] is False
    assert marker["files"] == 0
    assert marker["run_prefix"] is None
    assert "empty_inventory" in marker["failures"]


def test_a_run_that_protects_every_declared_store_completes(tmp_path: Path) -> None:
    """The two guards must not swallow a legitimate run.

    Supersedes an earlier row in this file that asserted a REQUIRED empty directory
    beside a real file still completes — David's TW27G fold-in makes that exact case
    fail (see ``test_required_directory_expanding_to_zero_files_fails_loudly``). The
    honest half of that row survives as
    ``test_optional_directory_expanding_to_zero_files_is_tolerated``.
    """
    repo = tmp_path / "repo"
    snapshots = repo / "app" / "data" / "league_snapshots"
    snapshots.mkdir(parents=True)
    (snapshots / "sleeper_universe_snapshot_phase17-20260522T024055Z.json").write_bytes(
        b'{"players": []}'
    )
    real = repo / "app" / "data" / "prospect_identity_review.jsonl"
    real.write_bytes(b'{"player": 1}\n')
    manifest = _write_manifest(
        repo,
        [
            {"path": "app/data/league_snapshots", "required": True, "kind": "directory"},
            {
                "path": "app/data/prospect_identity_review.jsonl",
                "required": True,
                "kind": "file",
            },
        ],
    )

    result = _run(repo, manifest, gcloud=FakeGcloud())

    assert result["status"] == "completed"
    assert result["files"] == 2
    assert result["sha256_verified"] is True
