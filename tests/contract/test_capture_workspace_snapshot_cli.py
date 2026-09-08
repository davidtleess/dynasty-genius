"""DG-190 — the capture CLI: archive one snapshot, print the receipt, refuse loudly.

The two behaviours worth defending here are both about not being convenient:

* every path is explicit, because a default archive location is how a local run quietly writes a shared store;
* the capture code identity is the commit ONLY when the working tree is clean, because a dirty tree means the code
  that ran is not the code that commit contains. Saying ``unknown`` is worth more later than a hash pointing at
  something else.

The source loader is root's module and may not exist yet, so it is injected here.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.capture_workspace_snapshot import capture_code_identity, main
from src.dynasty_genius.capture.workspace_snapshot_store import (
    SnapshotBundle,
    WorkspaceSnapshotError,
)
from tests.contract.test_workspace_snapshot_store import (
    artifacts,
    comparison_payload,
    ranks_payload,
)

RUN_AT = datetime(2026, 9, 8, 1, 30, tzinfo=timezone.utc)
CODE_SHA = "a85f726f23cad759d17877ce2762f93b30d9294f"


def loader(bundle: SnapshotBundle | None = None, *, record: list | None = None):
    subject = bundle or SnapshotBundle(
        artifacts=artifacts(), ranks=ranks_payload(), comparison=comparison_payload()
    )

    def load(manifest: Path, catalog: Path, companion: Path) -> SnapshotBundle:
        if record is not None:
            record.append((manifest, catalog, companion))
        return subject

    return load


def run(archive: Path, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    argv = [
        "--manifest", "/sources/market-ranks-manifest.json",
        "--catalog", "/sources/catalog.json",
        "--catalog-companion", "/sources/catalog-companion.json",
        "--archive-root", str(archive),
    ]
    code = main(
        argv,
        load=kwargs.pop("load", loader()),
        clock=kwargs.pop("clock", lambda: RUN_AT),
        code=kwargs.pop("code", CODE_SHA),
        stdout=out,
        stderr=err,
    )
    assert not kwargs, kwargs
    return code, out.getvalue(), err.getvalue()


# --- the happy path -------------------------------------------------------------------------------


def test_it_archives_the_snapshot_and_prints_the_receipt_as_json(tmp_path) -> None:
    status, out, err = run(tmp_path / "archive")
    assert status == 0 and err == ""
    result = json.loads(out)
    assert result["created"] is True
    receipt = result["snapshot"]
    assert len(receipt["snapshot_id"]) == 64
    assert receipt["saved_at"] == "2026-09-08T01:30:00+00:00"
    assert receipt["capture_code_sha"] == CODE_SHA
    assert receipt["evaluation_status"] == "ungraded"
    assert receipt["counts"]["available"] == 5


def test_it_passes_the_three_source_paths_through_to_the_loader(tmp_path) -> None:
    seen: list = []
    run(tmp_path / "archive", load=loader(record=seen))
    assert seen == [
        (Path("/sources/market-ranks-manifest.json"),
         Path("/sources/catalog.json"),
         Path("/sources/catalog-companion.json"))
    ]


def test_saving_the_same_sources_again_reports_the_original_save(tmp_path) -> None:
    archive = tmp_path / "archive"
    first = json.loads(run(archive)[1])
    status, out, _ = run(archive, clock=lambda: RUN_AT + timedelta(days=2), code="b" * 40)
    again = json.loads(out)
    assert status == 0
    assert again["created"] is False
    assert again["snapshot"]["snapshot_id"] == first["snapshot"]["snapshot_id"]
    assert again["snapshot"]["saved_at"] == first["snapshot"]["saved_at"]


# --- every path is explicit ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "drop", ["--manifest", "--catalog", "--catalog-companion", "--archive-root"]
)
def test_every_path_is_required_with_no_default(tmp_path, drop, monkeypatch) -> None:
    # even with an environment variable set, nothing is inferred: an implicit archive root is how a local run
    # quietly writes somebody else's store
    monkeypatch.setenv("DG_WORKSPACE_ARCHIVE_ROOT", str(tmp_path / "would-be-default"))
    argv = [
        "--manifest", "m.json", "--catalog", "c.json",
        "--catalog-companion", "cc.json", "--archive-root", str(tmp_path / "archive"),
    ]
    index = argv.index(drop)
    del argv[index : index + 2]
    with pytest.raises(SystemExit) as exit_status:
        main(argv, load=loader(), clock=lambda: RUN_AT, code=CODE_SHA, stderr=io.StringIO())
    assert exit_status.value.code != 0
    assert not (tmp_path / "would-be-default").exists()


# --- refusals --------------------------------------------------------------------------------------


def test_a_refused_snapshot_exits_nonzero_and_says_why_on_stderr(tmp_path) -> None:
    broken = comparison_payload()
    broken["source"]["report_run"] = "20250101T000000Z"        # disagrees with the ranks payload
    bundle = SnapshotBundle(artifacts=artifacts(), ranks=ranks_payload(), comparison=broken)
    status, out, err = run(tmp_path / "archive", load=loader(bundle))
    assert status == 1
    assert out == ""
    assert "refusing to archive" in err and "report_run" in err
    assert not (tmp_path / "archive").exists()


def test_a_source_that_cannot_be_read_exits_nonzero(tmp_path) -> None:
    def explode(*_args):
        raise OSError("the manifest is not there")

    status, out, err = run(tmp_path / "archive", load=explode)
    assert status == 1 and out == "" and "could not read" in err


def test_a_loader_refusal_is_reported_rather_than_traced(tmp_path) -> None:
    def refuse(*_args):
        raise WorkspaceSnapshotError("the catalog does not bind the served report")

    status, _, err = run(tmp_path / "archive", load=refuse)
    assert status == 1 and "does not bind" in err


def test_an_archive_root_inside_a_shared_store_is_refused(tmp_path) -> None:
    shared = tmp_path / "app" / "data" / "archive"
    shared.mkdir(parents=True)
    status, _, err = run(shared)
    assert status == 1 and "shared" in err


# --- the capture code identity -----------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
             "GIT_COMMITTER_EMAIL": "t@e", "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(repo)},
    )


def test_a_clean_tree_may_claim_its_commit_and_a_dirty_one_may_not(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    (repo / "code.py").write_text("print('one')\n")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "--quiet", "-m", "one")

    clean = capture_code_identity(repo)
    assert len(clean) == 40 and not set(clean) - set("0123456789abcdef")

    (repo / "code.py").write_text("print('two')\n")           # the running code is no longer that commit
    assert capture_code_identity(repo) == "unknown"


def test_somewhere_that_is_not_a_repository_is_unknown_rather_than_a_guess(tmp_path) -> None:
    assert capture_code_identity(tmp_path / "not-a-repo") == "unknown"


def test_the_receipt_records_unknown_rather_than_a_model_version(tmp_path) -> None:
    status, out, _ = run(tmp_path / "archive", code="unknown")
    assert status == 0
    assert json.loads(out)["snapshot"]["capture_code_sha"] == "unknown"
