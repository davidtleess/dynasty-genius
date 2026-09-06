"""DG-177: a run's manifest must name the code that RAN — provenance captured at launch."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from src.dynasty_genius.eval.run_provenance import launch_provenance


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    return repo


def test_launch_provenance_reports_head_branch_and_clean_state(tmp_path):
    repo = _repo(tmp_path)
    p = launch_provenance(repo_root=repo, argv=["run.py", "--x"])
    assert p["git_head"] == _git(repo, "rev-parse", "HEAD")
    assert p["git_branch"] == "main"
    assert p["git_dirty"] is False
    assert p["argv"] == ["run.py", "--x"]
    assert re.match(r"\d{4}-\d{2}-\d{2}T", p["captured_at_utc"])


def test_launch_provenance_flags_a_dirty_tree_and_does_not_move_with_later_commits(tmp_path):
    repo = _repo(tmp_path)
    (repo / "a.txt").write_text("changed\n")
    before = launch_provenance(repo_root=repo, argv=[])
    assert before["git_dirty"] is True
    _git(repo, "commit", "-q", "-am", "two")
    assert before["git_head"] == _git(repo, "rev-parse", "HEAD~1")   # a captured value, not a live lookup


def test_forecast_runners_capture_provenance_before_any_fitting():
    """Tested without rerunning the forecasts: the runners must call launch_provenance() before
    the manifest is built and must not read HEAD again at the end."""
    for path in ("scripts/experiments/dg177_basic_horizons.py", "scripts/experiments/dg177_annual_forecasts.py"):
        src = Path(path).read_text()
        body = src[src.index("def main("):]
        assert "launch_provenance(" in body, path
        assert body.index("launch_provenance(") < body.index("build_manifest("), path
        assert '_git("rev-parse", "HEAD")' not in body, path


def test_a_new_untracked_code_file_makes_the_tree_dirty_and_is_named(tmp_path):
    """Root's review: --untracked-files=no would call a tree clean while running a brand-new module."""
    repo = _repo(tmp_path)
    (repo / "new.py").write_text("x = 1\n")
    p = launch_provenance(repo_root=repo, argv=[])
    assert p["git_dirty"] is True
    assert p["tracked_dirty"] is False
    assert p["untracked_paths"] == ["new.py"]


def test_runners_record_the_argv_they_were_given_not_the_process_argv():
    for path in ("scripts/experiments/dg177_basic_horizons.py", "scripts/experiments/dg177_annual_forecasts.py"):
        body = Path(path).read_text()
        body = body[body.index("def main("):]
        assert "launch_provenance(argv=sys.argv if argv is None else argv)" in body, path
