"""The preflight write plan: what a runner will write, and whether any of it is live.

Pins the behaviour that a flat settings dump could not express, and that its absence
let a careful operator publish to production on 2026-08-31 believing they had sandboxed
the run.
"""

from __future__ import annotations

from pathlib import Path

from src.dynasty_genius.write_plan import LIVE, SANDBOX, classify, write_plan


def test_paths_inside_the_app_tree_are_live(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app" / "data").mkdir(parents=True)
    assert classify("app/data/valuation/latest.json", repo_root=repo) == LIVE
    assert classify(repo / "app" / "data" / "x.db", repo_root=repo) == LIVE


def test_paths_outside_the_app_tree_are_sandboxed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    assert classify(scratch / "out.json", repo_root=repo) == SANDBOX
    # a sibling of app/, still inside the repo, is not the serving tree
    assert classify("docs/notes.md", repo_root=repo) == SANDBOX


def test_a_symlink_is_classified_by_where_it_lands(tmp_path: Path) -> None:
    """The 2026-08-31 head_a destruction was a write that reached the trunk THROUGH a
    symlink. A plan that judged the spelling rather than the destination would have
    called that write sandboxed."""
    repo = tmp_path / "repo"
    (repo / "app" / "data").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    link = scratch / "looks_sandboxed"
    link.symlink_to(repo / "app" / "data")
    assert classify(link / "victim.json", repo_root=repo) == LIVE


def test_live_writes_are_counted_and_the_verdict_says_so(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app" / "data").mkdir(parents=True)
    plan = write_plan(
        writes={
            "latest": "app/data/latest.json",
            "history": "app/data/history.db",
            "report": tmp_path / "scratch" / "report.json",
        },
        reads={"seed": "app/data/seed.json"},
        repo_root=repo,
    )
    assert plan["preflight"] is True
    assert plan["live_writes"] == 2
    assert "WILL OVERWRITE 2 LIVE SERVING ARTIFACTS" in plan["verdict"]
    assert "NOT a sandboxed run" in plan["verdict"]
    assert [w["role"] for w in plan["writes"]] == ["history", "latest", "report"]
    assert [r["role"] for r in plan["reads"]] == ["seed"]


def test_singular_wording_for_one_live_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    plan = write_plan(writes={"only": "app/one.json"}, repo_root=repo)
    assert "1 LIVE SERVING ARTIFACT." in plan["verdict"]


def test_a_fully_redirected_run_reports_no_live_writes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    plan = write_plan(
        writes={"a": scratch / "a.json", "b": scratch / "b.json"},
        repo_root=repo,
    )
    assert plan["live_writes"] == 0
    assert "No live writes" in plan["verdict"]
    assert "NOT a sandboxed run" not in plan["verdict"]


def test_none_paths_are_dropped_as_not_in_play(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    plan = write_plan(
        writes={"used": "app/x.json", "unused": None},
        reads={"absent": None},
        repo_root=repo,
    )
    assert [w["role"] for w in plan["writes"]] == ["used"]
    assert plan["reads"] == []
