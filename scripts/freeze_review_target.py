"""Freeze and verify an exact, scoped code-review target.

`create` records a base commit, a binary-safe patch (including untracked scoped files),
and the expected post-patch file hashes. `verify` checks a detached worktree after the patch
is applied. Reviewers can therefore inspect a surface that concurrent edits cannot move.

This helper never creates or removes a worktree itself. Git worktree lifecycle remains an
explicit operator action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

MANIFEST_VERSION = "frozen-review-target.v1"
PATCH_NAME = "target.patch"
MANIFEST_NAME = "manifest.json"
_PRIVATE_PREFIXES = (
    PurePosixPath("app/data/pff_exports"),
    PurePosixPath("app/data/playerprofiler"),
)


class ReviewTargetError(RuntimeError):
    """The target cannot be frozen or verified exactly."""


def _run_git(
    repo: Path, args: Sequence[str], *, allow_diff: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    allowed = {0, 1} if allow_diff else {0}
    if result.returncode not in allowed:
        raise ReviewTargetError(
            f"git_failed: git {' '.join(args)}: {result.stderr.strip()}"
        )
    return result


def _repo_root(repo: Path) -> Path:
    result = _run_git(repo, ["rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _normalise_scope(root: Path, values: Sequence[str]) -> list[str]:
    if not values:
        raise ReviewTargetError("review_scope_empty")
    out = []
    for raw in values:
        candidate = (
            (root / raw).resolve()
            if not Path(raw).is_absolute()
            else Path(raw).resolve()
        )
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ReviewTargetError(f"review_scope_outside_repo: {raw}") from exc
        path = PurePosixPath(relative.as_posix())
        if not path.parts or ".git" in path.parts:
            raise ReviewTargetError(f"review_scope_forbidden: {raw}")
        if any(
            path == prefix or prefix in path.parents for prefix in _PRIVATE_PREFIXES
        ):
            raise ReviewTargetError(f"review_scope_private_data: {raw}")
        out.append(path.as_posix())
    return sorted(set(out))


def _lines(output: str) -> set[str]:
    return {line.strip() for line in output.splitlines() if line.strip()}


def _scoped_files(
    root: Path, base_sha: str, scope: Sequence[str]
) -> tuple[list[str], list[str]]:
    tracked_or_untracked = _lines(
        _run_git(
            root,
            ["ls-files", "--cached", "--others", "--exclude-standard", "--", *scope],
        ).stdout
    )
    changed = _lines(
        _run_git(root, ["diff", "--name-only", base_sha, "--", *scope]).stdout
    )
    files = sorted(tracked_or_untracked | changed)
    deleted = sorted(path for path in files if not (root / path).exists())
    return files, deleted


def create_target(
    *, repo: Path, base: str, output: Path, scope_values: Sequence[str], created_at: str
) -> dict[str, Any]:
    root = _repo_root(repo)
    scope = _normalise_scope(root, scope_values)
    base_sha = _run_git(root, ["rev-parse", f"{base}^{{commit}}"]).stdout.strip()

    ignored = sorted(
        _lines(
            _run_git(
                root,
                [
                    "ls-files",
                    "--others",
                    "--ignored",
                    "--exclude-standard",
                    "--",
                    *scope,
                ],
            ).stdout
        )
    )
    if ignored:
        raise ReviewTargetError(
            "review_scope_contains_ignored_files: an exact target cannot silently omit "
            f"ignored in-scope files: {ignored}"
        )

    tracked_patch = _run_git(
        root, ["diff", "--binary", "--full-index", base_sha, "--", *scope]
    ).stdout
    untracked = sorted(
        _lines(
            _run_git(
                root, ["ls-files", "--others", "--exclude-standard", "--", *scope]
            ).stdout
        )
    )
    patch_parts = [tracked_patch]
    for path in untracked:
        result = _run_git(
            root,
            ["diff", "--no-index", "--binary", "--full-index", "--", "/dev/null", path],
            allow_diff=True,
        )
        patch_parts.append(result.stdout)
    patch = "".join(part for part in patch_parts if part)
    if not patch:
        raise ReviewTargetError("review_target_has_no_changes")

    files, deleted = _scoped_files(root, base_sha, scope)
    file_hashes = {
        path: _sha256_file(root / path)
        for path in files
        if path not in deleted and (root / path).is_file()
    }
    if not file_hashes and not deleted:
        raise ReviewTargetError("review_target_has_no_files")

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    patch_path = output / PATCH_NAME
    patch_path.write_text(patch, encoding="utf-8")
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": created_at,
        "base_sha": base_sha,
        "scope": scope,
        "scope_files": files,
        "deleted_files": deleted,
        "file_sha256": dict(sorted(file_hashes.items())),
        "patch_file": PATCH_NAME,
        "patch_sha256": _sha256_file(patch_path),
        "materialize": [
            f"git worktree add --detach <review-worktree> {base_sha}",
            f"git -C <review-worktree> apply --binary <target-dir>/{PATCH_NAME}",
            (
                ".venv/bin/python3.14 scripts/freeze_review_target.py verify "
                f"--manifest <target-dir>/{MANIFEST_NAME} --worktree <review-worktree>"
            ),
        ],
    }
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def verify_target(*, manifest_path: Path, worktree: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ReviewTargetError("review_manifest_version_unknown")
    patch_path = manifest_path.parent / str(manifest.get("patch_file") or "")
    if not patch_path.is_file() or _sha256_file(patch_path) != manifest.get(
        "patch_sha256"
    ):
        raise ReviewTargetError("review_patch_hash_mismatch")

    root = _repo_root(worktree)
    head_sha = _run_git(root, ["rev-parse", "HEAD"]).stdout.strip()
    if head_sha != manifest.get("base_sha"):
        raise ReviewTargetError(
            f"review_base_sha_mismatch: expected {manifest.get('base_sha')}, got {head_sha}"
        )
    mismatches = []
    for relative, expected in (manifest.get("file_sha256") or {}).items():
        path = root / relative
        actual = _sha256_file(path) if path.is_file() else None
        if actual != expected:
            mismatches.append(
                {"path": relative, "expected": expected, "actual": actual}
            )
    for relative in manifest.get("deleted_files") or []:
        if (root / relative).exists():
            mismatches.append({"path": relative, "expected": None, "actual": "exists"})
    if mismatches:
        raise ReviewTargetError(f"review_file_hash_mismatch: {mismatches}")
    return {
        "status": "ok",
        "base_sha": head_sha,
        "patch_sha256": manifest["patch_sha256"],
        "files_verified": len(manifest.get("file_sha256") or {}),
        "deletions_verified": len(manifest.get("deleted_files") or []),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--repo", type=Path, default=Path.cwd())
    create.add_argument("--base", default="HEAD")
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--path", action="append", required=True, dest="paths")
    create.add_argument("--created-at")

    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", required=True, type=Path)
    verify.add_argument("--worktree", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "create":
        payload = create_target(
            repo=args.repo,
            base=args.base,
            output=args.output,
            scope_values=args.paths,
            created_at=args.created_at or datetime.now(timezone.utc).isoformat(),
        )
    else:
        payload = verify_target(manifest_path=args.manifest, worktree=args.worktree)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
