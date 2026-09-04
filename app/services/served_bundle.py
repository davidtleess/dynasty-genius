"""DG-121 — the two facts about what David is actually looking at.

DG-076 gave the built bundle a manifest (``source_sha``, ``source_dirty``,
``built_at``, ``openapi_sha256``) and deferred the half that *checks* it. The
manifest can say what the bundle was built from; nothing compared it to what the
server is running. That gap cost a week: on 2026-08-29 the served bundle was
eight days stale, five landed UI tickets were not on screen, and nothing said so.
The remedy adopted then was a README ritual, and a ritual is not a detector.

**Two axes, deliberately not collapsed into one word.** They answer different
questions and neither can be inferred from the other:

* ``bundle_vs_checkout`` — is the running app built from THIS checkout's code?
* ``checkout_vs_origin`` — is this checkout the work that has been landed?

Measured 2026-09-04 08:5x ET, which is why both exist: the served manifest and
the checkout were the same commit (so the first axis alone reads "fine") while
the checkout sat EIGHT commits behind origin — three of David's own rulings
landed and invisible. A detector reporting only the first axis would have said
"current" on exactly the morning this ticket exists to catch.

**This module reports facts, never a verdict.** No status enum, no cause word:
David can be dirty-and-current, clean-and-behind, or both at once, and a single
enum would have to pick one. What the numbers MEAN on screen is a live design
question (his 2026-09-04 ruling that status is "glyphs and symbols, not full
sentences"), and a word chosen here would constrain that choice.

**It fails loudly by failing empty.** Every value it cannot establish is ``None``
and every comparison it cannot make is ``None``, never ``False`` and never a
reassuring default — the original defect was silence that read as health.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_RELATIVE = Path("frontend/dist/assets/build-manifest.json")
_SHA_LENGTH = 40
_GIT_TIMEOUT_SECONDS = 5.0


def _git(args: list[str], repo_root: Path) -> Optional[str]:
    """A git read, or ``None``. Never raises: a missing git, a non-repo directory
    and a non-zero exit are all "cannot establish", which is a fact this module
    is required to report rather than paper over."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def _git_succeeds(args: list[str], repo_root: Path) -> bool:
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _count(args: list[str], repo_root: Path) -> Optional[int]:
    raw = _git(args, repo_root)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA_LENGTH
        and all(c in "0123456789abcdef" for c in value)
    )


def read_manifest(repo_root: Path) -> Optional[dict[str, Any]]:
    """The served bundle's manifest, or ``None`` when there is not a trustworthy
    one. Absent, unreadable and shape-drifted are one answer on purpose: all
    three mean the bundle cannot identify itself, and the distinction between
    them is an operator's question, not David's."""
    path = repo_root / _MANIFEST_RELATIVE
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    if not _is_sha(raw.get("source_sha")):
        return None
    if not isinstance(raw.get("source_dirty"), bool):
        return None
    return raw


def _fetch_head_written_at(repo_root: Path) -> Optional[str]:
    """When this checkout last heard from the remote. The behind-count is read
    from a remote-tracking ref that only a fetch updates, so without this the
    number could say "nothing to catch up on" when nobody had asked in days."""
    # BOTH git dirs, newest wins. FETCH_HEAD is a PER-WORKTREE file while the
    # remote-tracking ref the behind-count reads is SHARED, so a fetch from any
    # worktree refreshes the number — and reading only one directory gets it
    # wrong in opposite directions. Measured on this machine, where the serving
    # checkout is itself a linked worktree: the private dir alone missed the
    # main checkout's fetch, and the common dir alone reported yesterday while
    # this tree had fetched minutes earlier.
    candidates: list[float] = []
    for flag in ("--git-dir", "--git-common-dir"):
        git_dir = _git(["rev-parse", flag], repo_root)
        if git_dir is None:
            continue
        path = Path(git_dir)
        if not path.is_absolute():
            path = repo_root / path
        try:
            candidates.append((path / "FETCH_HEAD").stat().st_mtime)
        except OSError:
            continue
    if not candidates:
        return None
    return datetime.fromtimestamp(max(candidates), tz=timezone.utc).isoformat()


def bundle_vs_checkout(repo_root: Optional[Path] = None) -> dict[str, Any]:
    """Is the running app built from this checkout's code?

    ``sha_matches_head`` is ``None``, never ``False``, whenever either side is
    unknown. ``source_dirty`` is reported beside the comparison rather than
    folded into it: a dirty build's commit is an anchor, not an identity, so it
    can be simultaneously "the same sha" and "not that code" — DG-076's panel
    fought for that distinction and it is true of the live bundle today.
    """
    root = repo_root if repo_root is not None else _ROOT
    manifest = read_manifest(root)
    head = _git(["rev-parse", "HEAD"], root)
    head_sha = head if _is_sha(head) else None

    source_sha: Optional[str] = None
    source_dirty: Optional[bool] = None
    built_at: Optional[str] = None
    if manifest is not None:
        source_sha = str(manifest["source_sha"])
        source_dirty = bool(manifest["source_dirty"])
        raw_built_at = manifest.get("built_at")
        built_at = raw_built_at if isinstance(raw_built_at, str) else None

    sha_known_to_repo: Optional[bool] = None
    commits_head_ahead: Optional[int] = None
    if source_sha is not None:
        sha_known_to_repo = _git_succeeds(
            ["cat-file", "-e", f"{source_sha}^{{commit}}"], root
        )
        if sha_known_to_repo and head_sha is not None:
            commits_head_ahead = _count(
                ["rev-list", "--count", f"{source_sha}..HEAD"], root
            )

    sha_matches_head: Optional[bool] = None
    if source_sha is not None and head_sha is not None:
        sha_matches_head = source_sha == head_sha

    return {
        "manifest_present": manifest is not None,
        "manifest_source_sha": source_sha,
        "manifest_source_dirty": source_dirty,
        "manifest_built_at": built_at,
        "manifest_sha_known_to_repo": sha_known_to_repo,
        "head_sha": head_sha,
        "sha_matches_head": sha_matches_head,
        "commits_head_ahead_of_bundle": commits_head_ahead,
    }


def checkout_vs_origin(repo_root: Optional[Path] = None) -> dict[str, Any]:
    """Is this checkout the work that has been landed?

    Read entirely from local refs — a health endpoint does not reach the network
    — so the count is only as current as the last fetch, and
    ``remote_last_fetched_at`` ships beside it so nothing can read the number as
    live. A checkout with no upstream answers ``None`` throughout.
    """
    root = repo_root if repo_root is not None else _ROOT
    head = _git(["rev-parse", "HEAD"], root)
    head_sha = head if _is_sha(head) else None

    upstream_ref = _git(["rev-parse", "--abbrev-ref", "@{upstream}"], root)
    upstream_sha: Optional[str] = None
    commits_behind: Optional[int] = None
    if upstream_ref is not None:
        raw = _git(["rev-parse", "@{upstream}"], root)
        upstream_sha = raw if _is_sha(raw) else None
        if upstream_sha is not None and head_sha is not None:
            commits_behind = _count(
                ["rev-list", "--count", "HEAD..@{upstream}"], root
            )

    return {
        "head_sha": head_sha,
        "remote_ref": upstream_ref,
        "remote_sha": upstream_sha,
        "commits_behind_remote": commits_behind,
        "remote_last_fetched_at": _fetch_head_written_at(root),
    }
