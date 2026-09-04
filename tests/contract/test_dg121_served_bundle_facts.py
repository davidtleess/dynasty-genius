"""DG-121 — the served bundle's two facts, and what they must never claim.

DG-076 emitted a build manifest and deferred the check. Nothing compared the
manifest to the running code, which is how a bundle sat eight days stale on
2026-08-29 with five landed tickets invisible and nothing saying so.

The rule these tests exist to hold: **the detector fails empty, never
reassuring.** Anything it cannot establish is ``None`` — never ``False``, never
a default that reads as health — because the original defect was silence that
looked like health. And the two axes stay separate: a bundle can be the same
commit as the checkout while the checkout is a week behind the team.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.served_bundle import (
    bundle_vs_checkout,
    checkout_vs_origin,
    read_manifest,
)

SHA_A = "0" * 40


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


def _repo(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "t@example.com"], root)
    _run(["git", "config", "user.name", "T"], root)
    (root / "seed.txt").write_text("seed\n")
    _run(["git", "add", "seed.txt"], root)
    _run(["git", "commit", "-qm", "seed"], root)
    return root


def _head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True, check=True
    ).stdout.strip()


def _write_manifest(root: Path, **fields: object) -> None:
    path = root / "frontend" / "dist" / "assets"
    path.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {
        "built_at": "2026-09-04T12:15:09.477Z",
        "openapi_sha256": "f" * 64,
        "source_dirty": False,
        "source_sha": _head(root),
    }
    body.update(fields)
    (path / "build-manifest.json").write_text(json.dumps(body))


# ── the manifest reader refuses to guess an identity ────────────────────────
def test_no_manifest_is_no_manifest(tmp_path):
    assert read_manifest(_repo(tmp_path)) is None


def test_unreadable_and_shape_drifted_manifests_are_no_manifest(tmp_path):
    root = _repo(tmp_path)
    assets = root / "frontend" / "dist" / "assets"
    assets.mkdir(parents=True)
    (assets / "build-manifest.json").write_text("{not json")
    assert read_manifest(root) is None
    # A manifest that cannot say whether its tree was clean has unknown
    # provenance; reading it would silently assert "clean" (DG-076's rule).
    (assets / "build-manifest.json").write_text(json.dumps({"source_sha": SHA_A}))
    assert read_manifest(root) is None
    (assets / "build-manifest.json").write_text(
        json.dumps({"source_sha": "not-a-sha", "source_dirty": False})
    )
    assert read_manifest(root) is None


# ── axis 1: is the running app this checkout's code? ────────────────────────
def test_a_clean_build_of_head_is_reported_as_matching(tmp_path):
    root = _repo(tmp_path)
    _write_manifest(root)
    facts = bundle_vs_checkout(root)
    assert facts["manifest_present"] is True
    assert facts["sha_matches_head"] is True
    assert facts["manifest_source_dirty"] is False
    assert facts["commits_head_ahead_of_bundle"] == 0


def test_a_dirty_build_reports_its_dirtiness_beside_a_matching_sha(tmp_path):
    """The live case on 2026-09-04: same commit, built from an uncommitted tree.
    The sha match is true AND the build is not that code; both facts ship."""
    root = _repo(tmp_path)
    _write_manifest(root, source_dirty=True)
    facts = bundle_vs_checkout(root)
    assert facts["sha_matches_head"] is True
    assert facts["manifest_source_dirty"] is True


def test_a_bundle_behind_head_reports_how_far(tmp_path):
    root = _repo(tmp_path)
    built_from = _head(root)
    for n in range(3):
        (root / f"f{n}.txt").write_text("x\n")
        _run(["git", "add", "-A"], root)
        _run(["git", "commit", "-qm", f"c{n}"], root)
    _write_manifest(root, source_sha=built_from)
    facts = bundle_vs_checkout(root)
    assert facts["sha_matches_head"] is False
    assert facts["commits_head_ahead_of_bundle"] == 3
    assert facts["manifest_sha_known_to_repo"] is True


def test_a_sha_this_repo_never_heard_of_is_unknown_not_current(tmp_path):
    """A bundle built somewhere else. The comparison is answerable (the shas
    differ) but the distance is not, and it must not default to zero."""
    root = _repo(tmp_path)
    _write_manifest(root, source_sha=SHA_A)
    facts = bundle_vs_checkout(root)
    assert facts["manifest_sha_known_to_repo"] is False
    assert facts["commits_head_ahead_of_bundle"] is None
    assert facts["sha_matches_head"] is False


def test_no_manifest_leaves_every_comparison_unknown_never_false(tmp_path):
    facts = bundle_vs_checkout(_repo(tmp_path))
    assert facts["manifest_present"] is False
    assert facts["manifest_source_sha"] is None
    assert facts["manifest_source_dirty"] is None
    assert facts["sha_matches_head"] is None
    assert facts["manifest_sha_known_to_repo"] is None
    assert facts["commits_head_ahead_of_bundle"] is None


def test_outside_a_repository_nothing_is_asserted(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    facts = bundle_vs_checkout(plain)
    assert facts["head_sha"] is None
    assert facts["sha_matches_head"] is None


# ── axis 2: is this checkout the work that has been landed? ─────────────────
def test_a_checkout_behind_its_remote_says_how_far_and_when_it_last_looked(tmp_path):
    origin = _repo(tmp_path, "origin")
    _run(["git", "config", "receive.denyCurrentBranch", "ignore"], origin)
    clone = tmp_path / "clone"
    _run(["git", "clone", "-q", str(origin), str(clone)], tmp_path)
    _run(["git", "config", "user.email", "t@example.com"], clone)
    _run(["git", "config", "user.name", "T"], clone)
    for n in range(2):
        (origin / f"o{n}.txt").write_text("x\n")
        _run(["git", "add", "-A"], origin)
        _run(["git", "commit", "-qm", f"o{n}"], origin)
    _run(["git", "fetch", "-q"], clone)

    facts = checkout_vs_origin(clone)
    assert facts["remote_ref"] == "origin/main"
    assert facts["commits_behind_remote"] == 2
    assert facts["remote_sha"] == _head(origin)
    # The count is only as current as the last fetch, so it ships with its age.
    assert facts["remote_last_fetched_at"] is not None


def test_a_worktree_still_knows_when_it_last_heard_from_the_remote(tmp_path):
    """Every lane on this machine works in a git worktree, where the private
    git-dir has no FETCH_HEAD — only the shared one does. Reading the wrong
    directory leaves a behind-count with no age beside it."""
    origin = _repo(tmp_path, "origin")
    clone = tmp_path / "clone"
    _run(["git", "clone", "-q", str(origin), str(clone)], tmp_path)
    _run(["git", "fetch", "-q"], clone)
    tree = tmp_path / "tree"
    _run(["git", "worktree", "add", "-q", "-b", "side", str(tree)], clone)

    facts = checkout_vs_origin(tree)
    assert facts["remote_last_fetched_at"] is not None


def test_a_worktrees_own_fetch_wins_over_an_older_shared_one(tmp_path):
    """The other direction: the serving checkout on this machine IS a linked
    worktree, and reading only the shared dir reported yesterday while this tree
    had fetched minutes before. The remote-tracking ref is shared, so the newest
    fetch from either place is the honest answer."""
    origin = _repo(tmp_path, "origin")
    clone = tmp_path / "clone"
    _run(["git", "clone", "-q", str(origin), str(clone)], tmp_path)
    tree = tmp_path / "tree"
    _run(["git", "worktree", "add", "-q", "-b", "side", str(tree)], clone)
    common = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=str(tree),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    shared_fetch_head = Path(common)
    if not shared_fetch_head.is_absolute():
        shared_fetch_head = tree / shared_fetch_head
    shared_fetch_head = shared_fetch_head / "FETCH_HEAD"
    if shared_fetch_head.exists():
        import os
        os.utime(shared_fetch_head, (0, 0))

    _run(["git", "fetch", "-q"], tree)

    stamp = checkout_vs_origin(tree)["remote_last_fetched_at"]
    assert stamp is not None
    assert not stamp.startswith("1970"), stamp


def test_a_checkout_with_no_upstream_claims_nothing(tmp_path):
    facts = checkout_vs_origin(_repo(tmp_path))
    assert facts["remote_ref"] is None
    assert facts["remote_sha"] is None
    assert facts["commits_behind_remote"] is None


def test_the_two_axes_are_independent(tmp_path):
    """The morning that made this ticket urgent: the bundle IS the checkout's
    code, and the checkout is behind the work. One axis alone reads as fine."""
    origin = _repo(tmp_path, "origin")
    clone = tmp_path / "clone"
    _run(["git", "clone", "-q", str(origin), str(clone)], tmp_path)
    for n in range(3):
        (origin / f"o{n}.txt").write_text("x\n")
        _run(["git", "add", "-A"], origin)
        _run(["git", "commit", "-qm", f"o{n}"], origin)
    _run(["git", "fetch", "-q"], clone)
    _write_manifest(clone)

    assert bundle_vs_checkout(clone)["sha_matches_head"] is True
    assert checkout_vs_origin(clone)["commits_behind_remote"] == 3


# ── the honesty lens, made concrete ─────────────────────────────────────────
# DG-121's adversarial review died on the account spend limit three times, so
# the questions it would have asked are pinned here instead of argued.
def test_a_detached_head_reports_the_commit_and_claims_no_remote(tmp_path):
    root = _repo(tmp_path)
    _run(["git", "checkout", "-q", "--detach"], root)
    _write_manifest(root)
    assert bundle_vs_checkout(root)["sha_matches_head"] is True
    origin = checkout_vs_origin(root)
    assert origin["head_sha"] is not None
    assert origin["remote_ref"] is None
    assert origin["commits_behind_remote"] is None


def test_a_repository_with_no_commits_asserts_nothing(tmp_path):
    root = tmp_path / "unborn"
    root.mkdir()
    _run(["git", "init", "-q", "-b", "main"], root)
    facts = bundle_vs_checkout(root)
    assert facts["head_sha"] is None
    assert facts["sha_matches_head"] is None
    assert checkout_vs_origin(root)["commits_behind_remote"] is None


def test_a_manifest_that_is_not_text_is_no_manifest(tmp_path):
    root = _repo(tmp_path)
    assets = root / "frontend" / "dist" / "assets"
    assets.mkdir(parents=True)
    (assets / "build-manifest.json").write_bytes(b"\xff\xfe\x00binary")
    assert read_manifest(root) is None
    assert bundle_vs_checkout(root)["manifest_present"] is False


def test_without_git_on_the_path_nothing_is_claimed(tmp_path, monkeypatch):
    """A serving environment with no git must degrade to unknown, not to
    "current" — the whole point is that it fails where the ritual failed."""
    root = _repo(tmp_path)
    _write_manifest(root)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    facts = bundle_vs_checkout(root)
    assert facts["manifest_present"] is True
    assert facts["head_sha"] is None
    assert facts["sha_matches_head"] is None
    # "git is not here" is not "this repo never heard of that commit". Only the
    # second is a fact, and reporting False for the first is the same collapse
    # of silence into an answer that this whole module exists to end.
    assert facts["manifest_sha_known_to_repo"] is None
    assert facts["commits_head_ahead_of_bundle"] is None
    assert checkout_vs_origin(root)["commits_behind_remote"] is None


def test_the_tickets_four_states_are_all_derivable_from_the_facts(tmp_path):
    """DG-121 asked for current / drifted / dirty / unknown. This commit ships
    facts instead, because the presentation is David's open design question —
    but every state it named must still be computable without guessing."""
    root = _repo(tmp_path)

    def state(facts: dict) -> str:
        if not facts["manifest_present"] or facts["head_sha"] is None:
            return "unknown"
        if facts["manifest_source_dirty"]:
            return "dirty"
        return "current" if facts["sha_matches_head"] else "drifted"

    assert state(bundle_vs_checkout(root)) == "unknown"
    _write_manifest(root)
    assert state(bundle_vs_checkout(root)) == "current"
    _write_manifest(root, source_dirty=True)
    assert state(bundle_vs_checkout(root)) == "dirty"
    (root / "later.txt").write_text("x\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-qm", "later"], root)
    _write_manifest(root, source_sha=SHA_A)
    assert state(bundle_vs_checkout(root)) == "drifted"
