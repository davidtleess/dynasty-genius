"""DG-100 — incremental offsite sync of the nflverse vintage record.

``app/data/nflverse_usage/raw/`` holds dated, immutable snapshot files — the
point-in-time vintages the replay harness re-derives ledger content from
(receipt ``replay-20260829T143201Z``: 14/14 nflverse checks reproduced). The
nightly backup deliberately excludes this tree: it re-uploads its FULL payload
every run, so 30 GB there would quadruple the nightly transfer and grow the
append-only bucket by the tree's full size every day. This channel is the
alternative the DG-100 decision records: additive-only sync of NEW files to
ONE stable prefix — each run uploads only what the remote does not hold.

Contract, mirrored from ``backup_irreplaceable_data.py``:
- Append-only: no delete, no overwrite, no mirror mutations. A local file whose
  name exists remotely with a DIFFERENT size is a named failure
  (``remote_size_mismatch:*``) — history changed, and a sync must never paper
  over that.
- Fail closed with named reasons; every terminal state writes the gitignored
  status marker at ``app/data/ops/nflverse_vintage_backup_status.json``.
- ``sha256_verified`` is earned: every uploaded object is downloaded back and
  compared against the local fingerprint taken before upload.
- All external effects are injected seams (gcloud, fingerprint, clock), so the
  committed contract tests run with no network.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Direct invocation (launchd, `python scripts/backup_nflverse_vintages.py`) puts
# scripts/ itself on sys.path, not the repo root — the sibling import below then
# fails before any marker exists to record it. Caught by the pre-land live smoke.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.backup_irreplaceable_data import (  # noqa: E402
    DEFAULT_BUCKET_URI,
    BackupError,
    _real_fingerprint,
    _real_gcloud_runner_factory,
)

MARKER_REL_PATH = "app/data/ops/nflverse_vintage_backup_status.json"
SENTINEL_REL_PATH = "app/data/ops/nflverse_vintage_sync_active.json"
RAW_REL_PATH = "app/data/nflverse_usage/raw"
DEFAULT_PREFIX_REL = "dynasty-genius/nflverse-vintages/raw"

# gcloud's no-match phrasing for a listing under a prefix that holds nothing yet.
# The FIRST run of this channel hits exactly that; it is an empty remote, not a
# failure. Any other non-zero listing is a named remote_list_failed.
_NO_MATCH_FRAGMENTS = ("matched no objects", "One or more URLs matched no objects")


class SyncScanError(BackupError):
    """Every conflict found in one scan, sorted — the reported set is a property
    of the tree's content, never of iteration order (the ManifestScanError
    lesson from the nightly runner)."""

    def __init__(self, reasons: list[str]) -> None:
        self._reasons = sorted(reasons)
        super().__init__("; ".join(self._reasons))

    @property
    def reasons(self) -> list[str]:
        return list(self._reasons)


def _scan_local(raw_root: Path) -> list[tuple[str, Path]]:
    """(relative key, path) for every regular file under raw_root, sorted.

    Symlinks are rejected loudly: this channel protects the record, and a link
    that points elsewhere would upload bytes the tree does not actually hold
    (the DG-048 lesson — writers and readers crossing symlinks bite).
    An empty tree is a named failure: on this machine the capture writes daily,
    so nothing-to-protect means something upstream is wrong (the DGX-02
    empty-inventory principle).
    """
    if not raw_root.is_dir():
        raise BackupError(f"missing_raw_root:{raw_root}")
    files: list[tuple[str, Path]] = []
    symlinks: list[str] = []
    for member in sorted(raw_root.rglob("*")):
        rel = member.relative_to(raw_root).as_posix()
        if member.is_symlink():
            symlinks.append(f"raw_symlink:{rel}")
            continue
        if member.is_file():
            files.append((rel, member))
    if symlinks:
        raise SyncScanError(symlinks)
    if not files:
        raise BackupError("empty_local_raw")
    return files


def _list_remote(
    gcloud_runner: Callable[[list[str]], Any], prefix: str
) -> dict[str, int]:
    """{relative key: size} for every object under the stable prefix."""
    listing = gcloud_runner(["storage", "ls", "--long", f"{prefix}/**"])
    if getattr(listing, "returncode", 1) != 0:
        stderr = getattr(listing, "stderr", "") or ""
        if any(fragment in stderr for fragment in _NO_MATCH_FRAGMENTS):
            return {}
        raise BackupError("remote_list_failed")
    remote: dict[str, int] = {}
    for line in (getattr(listing, "stdout", "") or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[-1].startswith("gs://"):
            url = parts[-1]
            if url.startswith(prefix + "/"):
                remote[url[len(prefix) + 1 :]] = int(parts[0])
    return remote


def run_vintage_sync(
    *,
    repo_root: Path,
    raw_root: Path,
    bucket_uri: str,
    prefix_rel: str = DEFAULT_PREFIX_REL,
    gcloud_runner: Callable[[list[str]], Any] | None = None,
    gcloud_runner_factory: Callable[[], Callable[[list[str]], Any]] | None = None,
    file_fingerprint: Callable[[Path], tuple[int, str]],
    now_utc: Callable[[], datetime],
    dry_run: bool = False,
    max_uploads: int | None = None,
) -> dict[str, Any]:
    started = now_utc()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    prefix = f"{bucket_uri}/{prefix_rel}"
    failures: list[str] = []
    status = "failed"
    uploaded: list[dict[str, Any]] = []
    files_local = files_remote_before = files_already = files_capped = 0

    sentinel_path = repo_root / SENTINEL_REL_PATH
    if not dry_run:
        # Written before any work that can die; overwritten by the next run,
        # never deleted (the nightly runner's sentinel rationale applies whole).
        try:
            sentinel_path.parent.mkdir(parents=True, exist_ok=True)
            sentinel_path.write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "started_at": started.isoformat(),
                        "pid": os.getpid(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        except OSError:
            failures.append("sentinel_write_failed")

    try:
        local = _scan_local(raw_root)
        files_local = len(local)

        if gcloud_runner is None:
            if gcloud_runner_factory is None:
                raise BackupError("gcloud_runner_unconfigured")
            gcloud_runner = gcloud_runner_factory()

        remote = _list_remote(gcloud_runner, prefix)
        files_remote_before = len(remote)

        plan: list[tuple[str, Path]] = []
        conflicts: list[str] = []
        for rel, path in local:
            if rel not in remote:
                plan.append((rel, path))
                continue
            size, _ = file_fingerprint(path)
            if remote[rel] != size:
                conflicts.append(f"remote_size_mismatch:{rel}")
            else:
                files_already += 1
        if conflicts:
            # History diverged. Upload NOTHING — a partial sync beside a
            # corrupted record reads as health.
            raise SyncScanError(conflicts)

        if max_uploads is not None and len(plan) > max_uploads:
            # Never a silent cap: the marker carries exactly what was deferred.
            files_capped = len(plan) - max_uploads
            plan = plan[:max_uploads]

        if dry_run:
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "prefix": prefix,
                        "files_local": files_local,
                        "files_remote_before": files_remote_before,
                        "files_already_synced": files_already,
                        "planned_uploads": [rel for rel, _ in plan],
                        "files_skipped_by_cap": files_capped,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return {"status": "dry_run", "exit_code": 0}

        auth = gcloud_runner(["auth", "print-access-token"])
        if getattr(auth, "returncode", 1) != 0:
            raise BackupError("auth_unavailable")

        verify_dir = Path(tempfile.mkdtemp(prefix="dg-vintage-verify-"))
        try:
            for rel, path in plan:
                size, digest = file_fingerprint(path)
                upload = gcloud_runner(
                    ["storage", "cp", str(path), f"{prefix}/{rel}"]
                )
                if getattr(upload, "returncode", 1) != 0:
                    raise BackupError(f"upload_failed:{rel}")
                restored = verify_dir / rel
                restored.parent.mkdir(parents=True, exist_ok=True)
                download = gcloud_runner(
                    ["storage", "cp", f"{prefix}/{rel}", str(restored)]
                )
                if getattr(download, "returncode", 1) != 0:
                    raise BackupError(f"verify_download_failed:{rel}")
                r_size, r_digest = file_fingerprint(restored)
                if (r_size, r_digest) != (size, digest):
                    raise BackupError(f"verify_mismatch:{rel}")
                restored.unlink()
                uploaded.append({"path": rel, "bytes": size, "sha256": digest})
                print(f"synced {rel} ({size} bytes)")
        finally:
            shutil.rmtree(verify_dir, ignore_errors=True)

        status = "completed"
    except BackupError as exc:
        failures.extend(exc.reasons)
    except Exception as exc:  # fail closed on anything unforeseen
        failures.append(f"unexpected:{type(exc).__name__}")

    finished = now_utc()
    marker = {
        "schema_version": "nflverse_vintage_backup.v1",
        "status": status,
        "run_id": run_id,
        "prefix": prefix if status == "completed" else None,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "files_local": files_local,
        "files_remote_before": files_remote_before,
        "files_already_synced": files_already,
        "files_uploaded": len(uploaded),
        "bytes_uploaded": sum(item["bytes"] for item in uploaded),
        "files_skipped_by_cap": files_capped,
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
        marker["prefix"] = None

    return {**marker, "exit_code": 0 if status == "completed" else 1}


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET_URI)
    parser.add_argument("--prefix-rel", default=DEFAULT_PREFIX_REL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-uploads", type=int, default=None)
    args = parser.parse_args(argv)

    raw_root = args.raw_root if args.raw_root is not None else args.repo_root / RAW_REL_PATH
    result = run_vintage_sync(
        repo_root=args.repo_root,
        raw_root=raw_root,
        bucket_uri=args.bucket,
        prefix_rel=args.prefix_rel,
        gcloud_runner_factory=_real_gcloud_runner_factory,
        file_fingerprint=_real_fingerprint,
        now_utc=lambda: datetime.now(timezone.utc),
        dry_run=args.dry_run,
        max_uploads=args.max_uploads,
    )
    if result.get("status") != "dry_run":
        print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
