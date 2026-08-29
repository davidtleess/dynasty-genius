"""DG-028: the "we changed nothing" check must actually see the artifacts.

The old convention proved model-science work left production alone with::

    git diff -- app/config/model_registry.json app/data/models

but ``.gitignore`` covers the live artifacts under ``app/data/models``
(trunk ``.gitignore:60-65``), so that diff is empty whether or not the bytes
moved. The headline test reproduces the blindness in a throwaway git repo —
deliberate mutation of a live artifact, old check silent — and requires the
new guard (``scripts/check_model_no_mutation.py``) to fail loudly on the very
same mutation.

Fixture-only: every check runs against a temp repo root. The sole real file
read is the checked-in ``app/config/model_registry.json`` (tracked config;
never a gitignored artifact), asserting the real registry stays guardable.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Fixture repo layout — mirrors the real registry's two resolution shapes.
LITERAL_REL = "app/data/models/engine_b/runs/20260101T000000Z/qb_vX.pkl"
MANIFEST_REL = "app/data/models/engine_b/vX_manifest.json"
POINTER_REL = "app/data/models/latest.json"
RUN_DIR_REL = "app/data/models/runs/20260102T000000Z"
SEED_NAME = "QB_model.pkl"

LITERAL_BYTES = b"literal-model-bytes-v1"
SEED_BYTES = b"seed-model-bytes-v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact(overrides: dict) -> dict:
    body = {
        "artifact_id": "engine_a:QB",
        "path": SEED_NAME,
        "path_resolution": "latest_run_dir",
        "governing_pointer": POINTER_REL,
        "sha256": _sha(SEED_BYTES),
        "kind": "tracked_seed",
        "promotion_status": "active",
        "required_by_env": ["development", "ci", "serving", "production"],
        "allow_local_override": False,
        "approved_by": "David",
        "approved_date": "2026-08-28",
        "updated_by_commit": "abc1234",
    }
    body.update(overrides)
    return body


def _registry_body() -> dict:
    return {
        "registry_version": 1,
        "artifacts": [
            _artifact({}),
            _artifact(
                {
                    "artifact_id": "engine_b:qb_vX",
                    "path": LITERAL_REL,
                    "path_resolution": "literal",
                    "governing_pointer": MANIFEST_REL,
                    "sha256": _sha(LITERAL_BYTES),
                    "kind": "local_operational",
                    "required_by_env": ["serving", "production"],
                }
            ),
        ],
    }


def _build_repo(root: Path) -> None:
    """A minimal repo root the guard can see whole: registry + both artifacts."""

    literal = root / LITERAL_REL
    literal.parent.mkdir(parents=True)
    literal.write_bytes(LITERAL_BYTES)
    (root / MANIFEST_REL).write_text(
        json.dumps({"qb": LITERAL_REL}), encoding="utf-8"
    )
    run_dir = root / RUN_DIR_REL
    run_dir.mkdir(parents=True)
    (run_dir / SEED_NAME).write_bytes(SEED_BYTES)
    (root / POINTER_REL).write_text(
        json.dumps({"run_dir": RUN_DIR_REL}), encoding="utf-8"
    )
    config_dir = root / "app" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "model_registry.json").write_text(
        json.dumps(_registry_body()), encoding="utf-8"
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.email=dg028@test.invalid",
            "-c",
            "user.name=dg028",
            *args,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _check():
    import scripts.check_model_no_mutation as check

    return check


# --- the ticket's headline: old check blind, new check sees -------------------


def test_old_git_diff_stays_blind_while_new_check_catches_deliberate_mutation(
    tmp_path: Path,
) -> None:
    """Deliberate mutation of a live, gitignored artifact: the old
    ``git diff -- app/config/model_registry.json app/data/models`` convention
    reports NOTHING, and the new guard must fail loudly on the same bytes."""

    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)
    # Mirror the trunk's blindness: the live artifacts are gitignored.
    (repo / ".gitignore").write_text(
        "app/data/models/engine_b/vX_manifest.json\n"
        "app/data/models/engine_b/runs/\n"
        "app/data/models/runs/\n"
        "app/data/models/latest.json\n",
        encoding="utf-8",
    )
    _git(repo, "-c", "init.defaultBranch=main", "init", "-q")
    _git(repo, "add", ".gitignore", "app/config/model_registry.json")
    _git(repo, "commit", "-q", "-m", "seed")
    ignored = _git(repo, "check-ignore", LITERAL_REL)
    assert ignored.stdout.strip() == LITERAL_REL  # blindness precondition

    # The deliberate mutation: overwrite a live registry-named artifact.
    (repo / LITERAL_REL).write_bytes(b"OVERWRITTEN-model-bytes-nobody-approved")

    old_check = _git(
        repo,
        "diff",
        "--stat",
        "--",
        "app/config/model_registry.json",
        "app/data/models",
    )
    assert old_check.stdout.strip() == ""  # the old check still says "clean"

    report = check.run_check(repo_root=repo)
    assert report.clean is False
    mutated = {row.artifact_id: row for row in report.rows if not row.clean}
    assert set(mutated) == {"engine_b:qb_vX"}
    assert mutated["engine_b:qb_vX"].label == "MUTATED"


def test_cli_exits_nonzero_and_names_the_mutated_artifact(
    tmp_path: Path, capsys
) -> None:
    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)
    (repo / LITERAL_REL).write_bytes(b"OVERWRITTEN-model-bytes-nobody-approved")

    exit_code = check.main(["--repo-root", str(repo)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MUTATED" in captured.err
    assert "engine_b:qb_vX" in captured.err


# --- clean pass ---------------------------------------------------------------


def test_clean_repo_passes_with_per_artifact_receipts(
    tmp_path: Path, capsys
) -> None:
    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)

    report = check.run_check(repo_root=repo)
    assert report.clean is True
    assert [row.artifact_id for row in report.rows] == [
        "engine_a:QB",
        "engine_b:qb_vX",
    ]
    assert all(row.clean and row.label == "ok" for row in report.rows)
    # The receipt carries the observed hash — a pasteable citation, not a verdict.
    assert report.rows[1].observed_sha256 == _sha(LITERAL_BYTES)

    exit_code = check.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "engine_a:QB" in captured.out
    assert "engine_b:qb_vX" in captured.out


# --- every deviation shape fails loudly ---------------------------------------


def test_deleted_artifact_fails_loudly(tmp_path: Path) -> None:
    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)
    (repo / LITERAL_REL).unlink()

    report = check.run_check(repo_root=repo)

    assert report.clean is False
    failing = [row for row in report.rows if not row.clean]
    assert [row.artifact_id for row in failing] == ["engine_b:qb_vX"]
    assert failing[0].label == "MISSING"


def test_repointed_run_dir_fails_even_though_registered_bytes_still_exist(
    tmp_path: Path,
) -> None:
    """Redirecting latest.json at a different run is a mutation of serving
    reality even when the originally-registered bytes are untouched."""

    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)
    other_run = repo / "app" / "data" / "models" / "runs" / "20260103T000000Z"
    other_run.mkdir(parents=True)
    (other_run / SEED_NAME).write_bytes(b"a-different-model-entirely")
    (repo / POINTER_REL).write_text(
        json.dumps({"run_dir": "app/data/models/runs/20260103T000000Z"}),
        encoding="utf-8",
    )

    report = check.run_check(repo_root=repo)

    assert report.clean is False
    failing = {row.artifact_id for row in report.rows if not row.clean}
    assert "engine_a:QB" in failing


def test_null_recorded_hash_is_never_clean(tmp_path: Path) -> None:
    """A registry entry without a recorded hash cannot be vouched for —
    the guard reports it UNVERIFIABLE rather than skipping it."""

    check = _check()
    repo = tmp_path / "repo"
    repo.mkdir()
    _build_repo(repo)
    body = _registry_body()
    body["artifacts"][1]["sha256"] = None
    (repo / "app" / "config" / "model_registry.json").write_text(
        json.dumps(body), encoding="utf-8"
    )

    report = check.run_check(repo_root=repo)

    assert report.clean is False
    failing = {row.artifact_id: row.label for row in report.rows if not row.clean}
    assert failing == {"engine_b:qb_vX": "UNVERIFIABLE"}


def test_missing_registry_fails_closed_with_config_exit_code(
    tmp_path: Path, capsys
) -> None:
    check = _check()
    repo = tmp_path / "empty"
    repo.mkdir()

    exit_code = check.main(["--repo-root", str(repo)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "registry" in captured.err.lower()


# --- the real checked-in registry stays guardable -----------------------------


def test_real_registry_records_a_hash_for_every_artifact() -> None:
    """Reads ONLY the tracked config file. Every entry must carry a recorded
    sha256 — a null hash would put that artifact back outside the guard's
    sight, which is exactly the DG-028 hole."""

    from app.api.routes.system_model_provenance_models import load_model_registry

    registry = load_model_registry(
        registry_path=REPO_ROOT / "app" / "config" / "model_registry.json"
    )

    assert registry.artifacts, "real registry declares no artifacts"
    missing = [
        entry.artifact_id for entry in registry.artifacts if entry.sha256 is None
    ]
    assert missing == [], f"registry entries with no recorded hash: {missing}"
