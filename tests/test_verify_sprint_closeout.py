import importlib.util
import re
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


def _ok(stdout="", rc=0, stderr=""):
    class Result:
        pass

    result = Result()
    result.returncode = rc
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_check_python_suite_pass_and_fail():
    assert vsc.check_python_suite(run=lambda cmd, cwd=None: _ok(rc=0)).passed is True
    assert vsc.check_python_suite(run=lambda cmd, cwd=None: _ok(rc=1)).passed is False


def test_check_ruff_version_assert_then_check():
    def run(cmd, cwd=None):
        if "--version" in cmd:
            return _ok(stdout="ruff 0.15.12\n")
        return _ok(rc=0)

    assert vsc.check_ruff(run=run).passed is True

    def wrong_version(cmd, cwd=None):
        if "--version" in cmd:
            return _ok(stdout="ruff 0.14.0\n")
        raise AssertionError("must not run check on version mismatch")

    result = vsc.check_ruff(run=wrong_version)
    assert result.passed is False
    assert "0.15.12" in result.detail

    def misleading_prefix_version(cmd, cwd=None):
        if "--version" in cmd:
            return _ok(stdout="ruff 0.15.120\n")
        raise AssertionError("must not run check on near-match version mismatch")

    near_match = vsc.check_ruff(run=misleading_prefix_version)
    assert near_match.passed is False
    assert "0.15.12" in near_match.detail


def test_check_fe_gate_discovers_runs_and_aggregates():
    import json

    def package_json():
        return json.dumps({"scripts": {script: "x" for script in vsc.FE_GATE}})
    seen = []

    def run(cmd, cwd=None):
        seen.append(cmd[-1])
        return _ok(rc=0)

    result = vsc.check_fe_gate(run=run, read_text=package_json)
    assert result.passed is True
    assert seen == list(vsc.FE_GATE)

    assert (
        vsc.check_fe_gate(run=lambda cmd, cwd=None: _ok(rc=1), read_text=package_json).passed
        is False
    )

    def missing():
        return json.dumps({"scripts": {"typecheck": "x"}})

    def must_not_run(cmd, cwd=None):
        raise AssertionError("must not run npm when a gate script is missing")

    missing_result = vsc.check_fe_gate(run=must_not_run, read_text=missing)
    assert missing_result.passed is False
    assert "absent" in missing_result.detail.lower()

    def missing_package_json():
        raise FileNotFoundError("frontend/package.json")

    missing_file_result = vsc.check_fe_gate(
        run=must_not_run,
        read_text=missing_package_json,
    )
    assert missing_file_result.passed is False
    assert "package.json" in missing_file_result.detail

    def malformed_package_json():
        return "{not-json"

    malformed_result = vsc.check_fe_gate(
        run=must_not_run,
        read_text=malformed_package_json,
    )
    assert malformed_result.passed is False
    assert "package.json" in malformed_result.detail


def test_check_standalone_scripts_detects_import_failure(tmp_path):
    good = tmp_path / "good.py"
    good.write_text("import os\n")
    bad = tmp_path / "bad.py"
    bad.write_text("import does_not_exist_xyz\n")

    assert vsc.check_standalone_scripts([str(good)]).passed is True
    result = vsc.check_standalone_scripts([str(bad)])
    assert result.passed is False
    assert "bad.py" in result.detail


def test_standalone_check_catches_unbootstrapped_src_import(tmp_path):
    bare = tmp_path / "bare.py"
    bare.write_text("import src\n")
    assert vsc.check_standalone_scripts([str(bare)]).passed is False

    boot = tmp_path / "boot.py"
    boot.write_text(
        f"import sys; sys.path.insert(0, {str(vsc._REPO_ROOT)!r}); import src\n"
    )
    assert vsc.check_standalone_scripts([str(boot)]).passed is True


def test_standalone_check_allows_future_annotations_dataclass(tmp_path):
    script = tmp_path / "future_dataclass.py"
    script.write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class Probe:\n"
        "    value: bool | None\n"
    )

    assert vsc.check_standalone_scripts([str(script)]).passed is True


def test_report_and_remind():
    def run(cmd, cwd=None):
        if "--name-status" in cmd:
            return _ok(stdout="M\tapp/data/x.json\n")
        return _ok(rc=0)

    report = vsc.report_changes(
        artifacts=["app/data/x.json"],
        new_files=["scripts/new_tool.py"],
        base="origin/main",
        run=run,
    )

    assert report.tier == vsc.REPORT
    assert report.passed is None
    assert "M\tapp/data/x.json" in report.detail
    assert "scripts/new_tool.py" in report.detail

    remind = vsc.remind_checklist()
    assert remind.tier == vsc.REMIND
    assert remind.passed is None
    detail = remind.detail.lower()
    for token in ("david", "cockpit", "close the loop", "ci"):
        assert token in detail
    for banned_token in ("win", "loss", "buy", "sell", "elite", "bust"):
        assert re.search(rf"\b{banned_token}\b", detail) is None


def test_run_verification_selects_checks_by_surface():
    surfaces = {
        "frontend": False,
        "scripts": [],
        "artifacts": ["app/data/x.json"],
        "new_files": [],
    }

    results = vsc.run_verification(surfaces, run=lambda cmd, cwd=None: _ok(rc=0))
    names = {result.name for result in results}

    assert "python-suite" in names
    assert "ruff" in names
    assert "fe-gate" not in names
    assert "standalone-scripts" not in names
    assert "report" in names
    assert "remind" in names


def test_run_verification_includes_conditional_checks():
    surfaces = {
        "frontend": True,
        "scripts": ["scripts/a.py"],
        "artifacts": [],
        "new_files": [],
    }

    def standalone(scripts, run=None):
        assert scripts == ["scripts/a.py"]
        return vsc.CheckResult("standalone-scripts", vsc.ENFORCE, True, "ok")

    results = vsc.run_verification(
        surfaces,
        run=lambda cmd, cwd=None: _ok(rc=0),
        standalone=standalone,
    )
    names = {result.name for result in results}

    assert "fe-gate" in names
    assert "standalone-scripts" in names


def test_exit_code_and_render():
    passing = [
        vsc.CheckResult("python-suite", vsc.ENFORCE, True, "ok"),
        vsc.CheckResult("remind", vsc.REMIND, None, "x"),
    ]
    failing = passing + [vsc.CheckResult("ruff", vsc.ENFORCE, False, "bad")]

    assert vsc.exit_code(passing) == 0
    assert vsc.exit_code(failing) == 1

    out = vsc.render(failing)
    assert "ENFORCE" in out
    assert "ruff" in out
    assert "FAIL" in out


def test_main_returns_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(vsc, "changed_paths", lambda base, run=None: {"app/data/x.json"})
    monkeypatch.setattr(vsc, "added_paths", lambda base, run=None: set())
    monkeypatch.setattr(
        vsc,
        "run_verification",
        lambda surfaces, **kw: [
            vsc.CheckResult("python-suite", vsc.ENFORCE, False, "bad")
        ],
    )

    rc = vsc.main(["--base", "origin/main"])

    assert rc == 1
    assert "ENFORCE verdict: FAIL" in capsys.readouterr().out


def test_surface_detection_failure_still_prints_remind(monkeypatch, capsys):
    def boom(base, run=None):
        raise RuntimeError("git failed (128): bad base")

    monkeypatch.setattr(vsc, "changed_paths", boom)

    rc = vsc.main(["--base", "does-not-exist"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "surface-detection" in out
    assert "FAIL" in out
    assert "[REMIND]" in out
    for banned_token in ("win", "loss", "buy", "sell", "elite", "bust"):
        assert re.search(rf"\b{banned_token}\b", out.lower()) is None


def test_module_loads_standalone():
    result = vsc.check_standalone_scripts(
        [str(vsc._REPO_ROOT / "scripts" / "verify_sprint_closeout.py")]
    )

    assert result.passed is True
