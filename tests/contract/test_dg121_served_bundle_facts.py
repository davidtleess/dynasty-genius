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
