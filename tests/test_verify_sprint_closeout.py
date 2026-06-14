import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "vsc",
    Path(__file__).resolve().parents[1] / "scripts" / "verify_sprint_closeout.py",
)
vsc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = vsc
_SPEC.loader.exec_module(vsc)


def test_checkresult_and_tiers():
    assert vsc.ENFORCE == "ENFORCE"
    assert vsc.REPORT == "REPORT"
    assert vsc.REMIND == "REMIND"

    result = vsc.CheckResult(
        name="x",
        tier=vsc.ENFORCE,
        passed=True,
        detail="ok",
    )
    assert (result.name, result.tier, result.passed, result.detail) == (
        "x",
        "ENFORCE",
        True,
        "ok",
    )

    report = vsc.CheckResult(
        name="y",
        tier=vsc.REPORT,
        passed=None,
        detail="d",
    )
    assert report.passed is None


def test_changed_paths_and_added_paths_union_git_sources():
    def run(cmd, cwd=None):
        class Result:
            returncode = 0
            stderr = ""

        result = Result()
        joined = " ".join(cmd)
        if "--others" in cmd:
            result.stdout = "scripts/new_tool.py\n"
        elif "--cached" in cmd and "--diff-filter=A" in cmd:
            result.stdout = "frontend/src/new_view.tsx\n"
        elif "--cached" in cmd:
            result.stdout = "frontend/src/a.tsx\n"
        elif "--diff-filter=A" in cmd and "origin/main...HEAD" in joined:
            result.stdout = "app/data/new_artifact.json\n"
        elif "origin/main...HEAD" in joined:
            result.stdout = "app/data/x.json\nsrc/y.py\n"
        else:
            result.stdout = "src/y.py\n"
        return result

    assert vsc.changed_paths(base="origin/main", run=run) == {
        "app/data/x.json",
        "frontend/src/a.tsx",
        "scripts/new_tool.py",
        "src/y.py",
    }
    assert vsc.added_paths(base="origin/main", run=run) == {
        "app/data/new_artifact.json",
        "frontend/src/new_view.tsx",
        "scripts/new_tool.py",
    }


def test_detect_surfaces_classifies_changed_paths():
    surfaces = vsc.detect_surfaces(
        {
            "app/data/x.json",
            "frontend/src/a.tsx",
            "scripts/new_tool.py",
            "src/y.py",
        },
        added={"scripts/new_tool.py"},
    )

    assert surfaces["frontend"] is True
    assert surfaces["scripts"] == ["scripts/new_tool.py"]
    assert surfaces["artifacts"] == ["app/data/x.json"]
    assert surfaces["new_files"] == ["scripts/new_tool.py"]

    source_only = vsc.detect_surfaces({"src/y.py"}, added=set())
    assert source_only["frontend"] is False
    assert source_only["scripts"] == []
    assert source_only["artifacts"] == []
    assert source_only["new_files"] == []
