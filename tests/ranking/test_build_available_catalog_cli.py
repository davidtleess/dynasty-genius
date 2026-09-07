"""Root's review item 7: the immutable builder must record the ACTUAL working-tree state,
untracked files included, instead of reporting clean while the implementation is untracked."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dg178" / "build_available_catalog.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_available_catalog", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_git_state_reports_untracked_and_tracked_changes_separately(tmp_path) -> None:
    mod = _load()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "root"], check=True)
    assert mod.git_state(tmp_path) == {"dirty": False, "tracked_modified": [], "untracked": []}
    (tmp_path / "new_impl.py").write_text("x = 1\n")
    st = mod.git_state(tmp_path)
    assert st["dirty"] is True and st["untracked"] == ["new_impl.py"] and st["tracked_modified"] == []
    subprocess.run(["git", "-C", str(tmp_path), "add", "new_impl.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "add"], check=True)
    (tmp_path / "new_impl.py").write_text("x = 2\n")
    st = mod.git_state(tmp_path)
    assert st["dirty"] is True and st["tracked_modified"] == ["new_impl.py"] and st["untracked"] == []
