# Sprint-Closeout Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: this project uses the **cockpit TDD loop** (Codex authors RED tests → Claude makes them GREEN → Codex technical + Gemini governance dual-CLEAR → David-authorized commit → zero-divergence post-commit audit), NOT the superpowers subagent dispatch. Steps use checkbox (`- [ ]`) syntax. Route each task's RED and GREEN through the cockpit before the next.

**Goal:** Build `scripts/verify_sprint_closeout.py` — a repo-general, agent-agnostic pre-ship verification tollgate (three-tier ENFORCE/REPORT/REMIND) — plus a surgical `docs/governance/02-agent-operating-loop.md` amendment mandating it.

**Architecture:** A single module of small, pure-ish functions: surface detection (over the union of committed+staged+unstaged+untracked changed paths) → ENFORCE check runners (full suite, ruff, FE gate, standalone-script load) with the subprocess runner **injected** for testability → REPORT generators → a static REMIND checklist → orchestration that selects checks per detected surface, aggregates the exit code, and renders text. No network, no installs, no mutation of source/artifacts/git.

**Tech Stack:** Python 3.14 stdlib only (`argparse`, `subprocess`, `dataclasses`, `pathlib`, `json`, `tempfile`); pytest. Spec: `docs/superpowers/specs/2026-06-14-sprint-closeout-verifier-design.md` (v2, dual-CLEAR).

**Plan v2 — round-1 Codex findings integrated:** F1 standalone probe now runs from a cwd OUTSIDE the repo with a sanitized `sys.path` (script-dir only; no `''`/repo-root) so it actually replicates `python scripts/foo.py` + a RED proving a bare-`import src` script fails (Task 3); F2 `added_paths` now includes staged additions `--cached --diff-filter=A` (Task 2); F3 subprocess calls fail-loud — `_subprocess_run` wraps `FileNotFoundError`, git nonzero / absent-ruff / missing-base become explicit ENFORCE/CLI failures not empty surfaces/crashes (Tasks 2,3); F4 FE gate discovers scripts from `frontend/package.json` and fails loudly on a missing required gate script (Task 3); F5 REPORT adds a per-file `--name-status` diff summary vs base (Task 4); Task-8 smoke FE wording made surface-conditional.

**Plan v3 — round-2:** R1 surface-detection failure now renders the REMIND checklist + exits 1 (REMIND-always-printed invariant) + RED `test_surface_detection_failure_still_prints_remind` (Task 6); R3 the `main()` test's `run_verification` monkeypatch accepts the `base` kwarg (`**kw`); R4 Task-8 Files line de-staled to "full Python suite + surface-conditional gates". **R2 REJECTED with evidence** — empirically a bare `import src` script FAILS the probe (`ModuleNotFoundError: No module named 'src'`) while a self-bootstrapping script PASSES (rc=0); the bootstrap RED is correct as written, because `boot.py` re-inserts repo root *during* `exec_module` (after the probe's `sys.path` sanitization).

**Constants:** `RUFF_PIN = "0.15.12"`, `RUFF_BIN = ".venv/bin/ruff"`, `PYTEST = [".venv/bin/python3.14", "-m", "pytest"]`, `ARTIFACT_DIRS = ("app/data/",)`, `FE_DIR = "frontend/"`, `FE_GATE = ("typecheck", "lint", "test", "banned-language", "build")`.

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `scripts/verify_sprint_closeout.py` | NEW — the verifier: `CheckResult`, surface detection, ENFORCE/REPORT/REMIND functions, orchestration, CLI. | Create |
| `tests/test_verify_sprint_closeout.py` | NEW — unit tests over a stubbed command-runner + synthetic changed-path sets (no real suite/git invocation). | Create |
| `docs/governance/02-agent-operating-loop.md` | Add the surgical "Sprint-closeout tollgate" subsection. | Modify |
| `tests/test_governance_tollgate_clause.py` | NEW — asserts the tollgate clause is present + references the verifier. | Create |

**Injection seam:** every function that shells out takes a `run` callable param, `run(cmd: list[str], cwd: str | None = None) -> Completedish`, where `Completedish` has `.returncode:int`, `.stdout:str`, `.stderr:str`. Default `run = _subprocess_run`. Tests pass a stub.

---

## Task 1: `CheckResult` schema + tier constants

**Files:**
- Create: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verify_sprint_closeout.py
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "vsc", Path(__file__).resolve().parents[1] / "scripts" / "verify_sprint_closeout.py"
)
vsc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vsc)


def test_checkresult_and_tiers():
    assert vsc.ENFORCE == "ENFORCE"
    assert vsc.REPORT == "REPORT"
    assert vsc.REMIND == "REMIND"
    r = vsc.CheckResult(name="x", tier=vsc.ENFORCE, passed=True, detail="ok")
    assert (r.name, r.tier, r.passed, r.detail) == ("x", "ENFORCE", True, "ok")
    # REPORT/REMIND carry passed=None (no verdict)
    rep = vsc.CheckResult(name="y", tier=vsc.REPORT, passed=None, detail="d")
    assert rep.passed is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -v`
Expected: FAIL — file `scripts/verify_sprint_closeout.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/verify_sprint_closeout.py
"""Governed sprint-closeout verifier (spec 2026-06-14). Pre-ship tollgate:
ENFORCE deterministic checks, REPORT human-audit surfaces, REMIND human-judgment
gates. Read-only; never installs/downloads or mutates source/artifacts/git."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

ENFORCE, REPORT, REMIND = "ENFORCE", "REPORT", "REMIND"


@dataclass
class CheckResult:
    name: str
    tier: str
    passed: bool | None  # None for REPORT/REMIND (no verdict)
    detail: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR + David authorization)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): CheckResult schema + tier constants"
```

---

## Task 2: Surface detection (committed + staged + unstaged + untracked)

**Files:**
- Modify: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_verify_sprint_closeout.py
def test_changed_paths_unions_all_git_sources():
    calls = []
    def run(cmd, cwd=None):
        calls.append(cmd)
        class R: pass
        r = R(); r.returncode = 0; r.stderr = ""
        if "--cached" in cmd:            r.stdout = "frontend/src/a.tsx\n"
        elif "--others" in cmd:          r.stdout = "scripts/new_tool.py\n"
        elif "diff" in cmd and "..." in " ".join(cmd):
                                          r.stdout = "app/data/x.json\nsrc/y.py\n"
        else:                             r.stdout = "src/y.py\n"   # unstaged
        return r
    paths = vsc.changed_paths(base="origin/main", run=run)
    assert paths == {"frontend/src/a.tsx", "scripts/new_tool.py", "app/data/x.json", "src/y.py"}


def test_detect_surfaces_classifies():
    s = vsc.detect_surfaces({
        "frontend/src/a.tsx", "scripts/new_tool.py", "app/data/x.json", "src/y.py",
    }, added={"scripts/new_tool.py"})
    assert s["frontend"] is True
    assert s["scripts"] == ["scripts/new_tool.py"]
    assert s["artifacts"] == ["app/data/x.json"]
    assert s["new_files"] == ["scripts/new_tool.py"]
    s2 = vsc.detect_surfaces({"src/y.py"}, added=set())
    assert s2["frontend"] is False and s2["scripts"] == [] and s2["artifacts"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "changed_paths or detect_surfaces" -v`
Expected: FAIL — `changed_paths` / `detect_surfaces` not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/verify_sprint_closeout.py
import subprocess

ARTIFACT_DIRS = ("app/data/",)
FE_DIR = "frontend/"


class _Completed:
    """Uniform result so a missing binary fails-loud (rc 127) instead of crashing (F3)."""
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _subprocess_run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd or str(_REPO_ROOT), capture_output=True, text=True)
    except FileNotFoundError as exc:
        return _Completed(127, "", f"{cmd[0]}: not found ({exc})")


def _lines(out: str) -> list[str]:
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _git(cmd: list[str], run) -> list[str]:
    """Run a git command; FAIL LOUD on nonzero (e.g., a missing --base) rather than
    returning an empty surface that would silently skip checks (F3)."""
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"git failed ({r.returncode}): {' '.join(cmd)} :: {(r.stderr or '').strip()}")
    return _lines(r.stdout)


def changed_paths(base: str = "origin/main", run=_subprocess_run) -> set[str]:
    """Union of committed (base...HEAD), staged, unstaged, and untracked paths. Fail-loud on git error."""
    paths: set[str] = set()
    paths |= set(_git(["git", "diff", "--name-only", f"{base}...HEAD"], run))
    paths |= set(_git(["git", "diff", "--name-only", "--cached"], run))
    paths |= set(_git(["git", "diff", "--name-only"], run))
    paths |= set(_git(["git", "ls-files", "--others", "--exclude-standard"], run))
    return paths


def added_paths(base: str = "origin/main", run=_subprocess_run) -> set[str]:
    """Paths added (A) vs base — committed, STAGED, and untracked (F2). Fail-loud on git error."""
    added = set(_git(["git", "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD"], run))
    added |= set(_git(["git", "diff", "--name-only", "--diff-filter=A", "--cached"], run))
    added |= set(_git(["git", "ls-files", "--others", "--exclude-standard"], run))
    return added


def detect_surfaces(paths: set[str], added: set[str]) -> dict:
    return {
        "frontend": any(p.startswith(FE_DIR) for p in paths),
        "scripts": sorted(p for p in paths if p.startswith("scripts/") and p.endswith(".py")),
        "artifacts": sorted(p for p in paths if p.startswith(ARTIFACT_DIRS)),
        "new_files": sorted(added),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "changed_paths or detect_surfaces" -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): surface detection over committed/staged/unstaged/untracked"
```

---

## Task 3: ENFORCE runners (suite, ruff, FE gate, standalone-script)

**Files:**
- Modify: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_verify_sprint_closeout.py
def _ok(stdout="", rc=0, stderr=""):
    class R: pass
    r = R(); r.returncode = rc; r.stdout = stdout; r.stderr = stderr
    return r


def test_check_python_suite_pass_and_fail():
    assert vsc.check_python_suite(run=lambda c, cwd=None: _ok(rc=0)).passed is True
    assert vsc.check_python_suite(run=lambda c, cwd=None: _ok(rc=1)).passed is False


def test_check_ruff_version_assert_then_check():
    def run(cmd, cwd=None):
        if "--version" in cmd: return _ok(stdout="ruff 0.15.12\n")
        return _ok(rc=0)
    assert vsc.check_ruff(run=run).passed is True
    # wrong version fails loud, never runs check
    def bad(cmd, cwd=None):
        if "--version" in cmd: return _ok(stdout="ruff 0.14.0\n")
        raise AssertionError("must not run check on version mismatch")
    res = vsc.check_ruff(run=bad)
    assert res.passed is False and "0.15.12" in res.detail


def test_check_fe_gate_discovers_runs_and_aggregates():
    import json
    pkg = lambda: json.dumps({"scripts": {s: "x" for s in vsc.FE_GATE}})
    seen = []
    def run(cmd, cwd=None):
        seen.append(cmd[-1]); return _ok(rc=0)
    res = vsc.check_fe_gate(run=run, read_text=pkg)
    assert res.passed is True and seen == list(vsc.FE_GATE)
    assert vsc.check_fe_gate(run=lambda c, cwd=None: _ok(rc=1), read_text=pkg).passed is False
    # F4: a missing required gate script fails loud and never runs npm
    missing = lambda: json.dumps({"scripts": {"typecheck": "x"}})
    def must_not_run(cmd, cwd=None):
        raise AssertionError("must not run npm when a gate script is missing")
    res3 = vsc.check_fe_gate(run=must_not_run, read_text=missing)
    assert res3.passed is False and "absent" in res3.detail.lower()


def test_check_standalone_scripts_detects_import_failure(tmp_path):
    good = tmp_path / "good.py"; good.write_text("import os\n")
    bad = tmp_path / "bad.py"; bad.write_text("import does_not_exist_xyz\n")
    assert vsc.check_standalone_scripts([str(good)]).passed is True
    res = vsc.check_standalone_scripts([str(bad)])
    assert res.passed is False and "bad.py" in res.detail


def test_standalone_check_catches_unbootstrapped_src_import(tmp_path):
    # F1: bare `import src` WITHOUT bootstrapping repo root must FAIL (replicates
    # `python scripts/foo.py`, where repo root is NOT on sys.path) — the exact bug
    # the default `python -c` from repo cwd would MASK.
    bare = tmp_path / "bare.py"; bare.write_text("import src\n")
    assert vsc.check_standalone_scripts([str(bare)]).passed is False
    # A script that bootstraps repo root itself must PASS.
    boot = tmp_path / "boot.py"
    boot.write_text(f"import sys; sys.path.insert(0, {str(vsc._REPO_ROOT)!r}); import src\n")
    assert vsc.check_standalone_scripts([str(boot)]).passed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "check_" -v`
Expected: FAIL — runners not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/verify_sprint_closeout.py
RUFF_BIN = ".venv/bin/ruff"
RUFF_PIN = "0.15.12"
PYTEST = [".venv/bin/python3.14", "-m", "pytest"]
FE_GATE = ("typecheck", "lint", "test", "banned-language", "build")


def check_python_suite(run=_subprocess_run) -> CheckResult:
    r = run(PYTEST)
    passed = r.returncode == 0
    return CheckResult("python-suite", ENFORCE, passed,
                       "full pytest suite" if passed else f"pytest failed (rc={r.returncode})")


def check_ruff(run=_subprocess_run) -> CheckResult:
    v = run([RUFF_BIN, "--version"])
    if RUFF_PIN not in (v.stdout or ""):
        return CheckResult("ruff", ENFORCE, False,
                           f"{RUFF_BIN} must be {RUFF_PIN} (got {v.stdout.strip() or 'absent'}); "
                           "install/update it — verifier never downloads ruff")
    r = run([RUFF_BIN, "check", "src", "app"])
    passed = r.returncode == 0
    return CheckResult("ruff", ENFORCE, passed, "ruff check src app" if passed else r.stdout.strip())


def _fe_scripts(read_text=None) -> dict:
    """Discover scripts from frontend/package.json (read_text injectable for tests) (F4)."""
    import json
    raw = (read_text or (lambda: (_REPO_ROOT / FE_DIR / "package.json").read_text(encoding="utf-8")))()
    return json.loads(raw).get("scripts", {})


def check_fe_gate(run=_subprocess_run, read_text=None) -> CheckResult:
    available = _fe_scripts(read_text)
    missing = [s for s in FE_GATE if s not in available]
    if missing:  # fail loud — do NOT run npm against a drifted gate (F4)
        return CheckResult("fe-gate", ENFORCE, False,
                           f"required FE gate script(s) absent from frontend/package.json: {', '.join(missing)}")
    failed = [s for s in FE_GATE if run(["npm", "--prefix", "frontend", "run", s]).returncode != 0]
    passed = not failed
    return CheckResult("fe-gate", ENFORCE, passed,
                       "frontend typecheck/lint/test/banned-language/build" if passed
                       else f"FE gate failed: {', '.join(failed)}")


def check_standalone_scripts(scripts: list[str], run=_subprocess_run) -> CheckResult:
    """Replicate `python <script>` faithfully (F1): the script's OWN dir on sys.path[0],
    and repo root + cwd ('') REMOVED from sys.path — the default `python -c` from repo
    cwd would leave repo root on sys.path and MASK the `No module named 'src'` class.
    Runs from a cwd OUTSIDE the repo; loads the module body only (no main()/side effects)."""
    import tempfile
    outside = tempfile.gettempdir()  # cwd outside repo so '' (if present) is not repo root
    failures = []
    for path in scripts:
        p = Path(path).resolve()
        probe = (
            "import importlib.util,sys; "
            f"repo={str(_REPO_ROOT)!r}; "
            "sys.path[:] = [x for x in sys.path if x not in ('', repo)]; "
            f"sys.path.insert(0, {str(p.parent)!r}); "
            f"s=importlib.util.spec_from_file_location('._probe', {str(p)!r}); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"
        )
        r = run([sys.executable, "-c", probe], cwd=outside)
        if r.returncode != 0:
            tail = ((r.stderr or "").strip().splitlines() or ["load failed"])[-1]
            failures.append(f"{path}: {tail}")
    passed = not failures
    return CheckResult("standalone-scripts", ENFORCE, passed,
                       "all changed scripts load standalone" if passed else "; ".join(failures))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "check_" -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): ENFORCE runners (suite, ruff version-asserted, FE gate, standalone-script)"
```

---

## Task 4: REPORT generators + REMIND checklist

**Files:**
- Modify: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_verify_sprint_closeout.py
def test_report_and_remind():
    def run(cmd, cwd=None):
        if "--name-status" in cmd:
            return _ok(stdout="M\tapp/data/x.json\n")
        return _ok(rc=0)
    rep = vsc.report_changes(artifacts=["app/data/x.json"], new_files=["scripts/new_tool.py"],
                             base="origin/main", run=run)
    assert rep.tier == vsc.REPORT and rep.passed is None
    assert "M\tapp/data/x.json" in rep.detail   # F5: per-file diff summary vs base
    assert "scripts/new_tool.py" in rep.detail

    rem = vsc.remind_checklist()
    assert rem.tier == vsc.REMIND and rem.passed is None
    low = rem.detail.lower()
    for token in ("david", "cockpit", "close the loop", "ci"):
        assert token in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "report_and_remind" -v`
Expected: FAIL — not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/verify_sprint_closeout.py
def report_changes(artifacts, new_files, base="origin/main", run=_subprocess_run) -> CheckResult:
    parts = []
    if artifacts:
        diff = run(["git", "diff", "--name-status", base, "--", *artifacts])  # F5: per-file summary vs base
        summary = diff.stdout.strip() if diff.returncode == 0 and diff.stdout.strip() else ", ".join(artifacts)
        parts.append("Tracked data artifacts changed — audit the allowed-path diff vs base:\n" + summary)
    if new_files:
        parts.append("New files added (if any sit in a guarded/allowlisted directory, confirm its "
                     "inviolate audit is green and any allowlist amendment is David-authorized): "
                     + ", ".join(new_files))
    return CheckResult("report", REPORT, None, "\n".join(parts) if parts else "no artifact/new-file changes")


def remind_checklist() -> CheckResult:
    text = (
        "Human-judgment gates (see docs/governance/02-agent-operating-loop.md — not restated here):\n"
        "- Commits, pushes, merges, branch deletes, and inviolate-surface amendments require David's "
        "explicit authorization.\n"
        "- Route decisions (spec/plan/contract/merge-strategy) through the cockpit (Codex + Gemini) "
        "before David.\n"
        "- After any hard-to-reverse op (commit/push/merge/delete), close the loop with a post-action "
        "confirmation to both reviewers.\n"
        "- CI (not local-green) is the push gate; this verifier is local pre-flight, not a CI substitute."
    )
    return CheckResult("remind", REMIND, None, text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "report_and_remind" -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): REPORT generators + REMIND checklist"
```

---

## Task 5: Orchestration + exit code + render

**Files:**
- Modify: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_verify_sprint_closeout.py
def test_run_verification_selects_checks_by_surface():
    surfaces = {"frontend": False, "scripts": [], "artifacts": ["app/data/x.json"], "new_files": []}
    names = {r.name for r in vsc.run_verification(surfaces, run=lambda c, cwd=None: _ok(rc=0))}
    assert "python-suite" in names and "ruff" in names      # always
    assert "fe-gate" not in names                            # FE not touched
    assert "standalone-scripts" not in names                 # no scripts touched
    assert "report" in names and "remind" in names


def test_run_verification_includes_conditional_checks():
    surfaces = {"frontend": True, "scripts": ["scripts/a.py"], "artifacts": [], "new_files": []}
    # stub: every ENFORCE passes; standalone uses real loader on a missing file -> guard below
    res = vsc.run_verification(surfaces, run=lambda c, cwd=None: _ok(rc=0),
                               standalone=lambda s, run=None: vsc.CheckResult("standalone-scripts", vsc.ENFORCE, True, "ok"))
    names = {r.name for r in res}
    assert "fe-gate" in names and "standalone-scripts" in names


def test_exit_code_and_render():
    passing = [vsc.CheckResult("python-suite", vsc.ENFORCE, True, "ok"),
               vsc.CheckResult("remind", vsc.REMIND, None, "x")]
    failing = passing + [vsc.CheckResult("ruff", vsc.ENFORCE, False, "bad")]
    assert vsc.exit_code(passing) == 0
    assert vsc.exit_code(failing) == 1
    out = vsc.render(failing)
    assert "ENFORCE" in out and "ruff" in out and "FAIL" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "run_verification or exit_code_and_render" -v`
Expected: FAIL — not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/verify_sprint_closeout.py
def run_verification(surfaces, base="origin/main", run=_subprocess_run, standalone=check_standalone_scripts) -> list[CheckResult]:
    results = [check_python_suite(run=run), check_ruff(run=run)]
    if surfaces["frontend"]:
        results.append(check_fe_gate(run=run))
    if surfaces["scripts"]:
        results.append(standalone(surfaces["scripts"], run=run))
    results.append(report_changes(surfaces["artifacts"], surfaces["new_files"], base=base, run=run))
    results.append(remind_checklist())
    return results


def exit_code(results: list[CheckResult]) -> int:
    return 1 if any(r.tier == ENFORCE and r.passed is False for r in results) else 0


def render(results: list[CheckResult]) -> str:
    lines = []
    for r in results:
        if r.tier == ENFORCE:
            lines.append(f"[ENFORCE] {r.name}: {'PASS' if r.passed else 'FAIL'} — {r.detail}")
    for r in results:
        if r.tier == REPORT:
            lines.append(f"[REPORT] {r.name}:\n{r.detail}")
    for r in results:
        if r.tier == REMIND:
            lines.append(f"[REMIND] {r.name}:\n{r.detail}")
    verdict = "PASS" if exit_code(results) == 0 else "FAIL"
    lines.append(f"\nENFORCE verdict: {verdict}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "run_verification or exit_code_and_render" -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): orchestration + exit code + text render"
```

---

## Task 6: CLI `main()` + standalone-invocation self-check

**Files:**
- Modify: `scripts/verify_sprint_closeout.py`
- Test: `tests/test_verify_sprint_closeout.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_verify_sprint_closeout.py
def test_main_returns_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(vsc, "changed_paths", lambda base, run=None: {"app/data/x.json"})
    monkeypatch.setattr(vsc, "added_paths", lambda base, run=None: set())
    # R3: lambda must accept the base kwarg main() now passes (run_verification(surfaces, base=...)).
    monkeypatch.setattr(vsc, "run_verification",
                        lambda surfaces, **kw: [vsc.CheckResult("python-suite", vsc.ENFORCE, False, "bad")])
    rc = vsc.main(["--base", "origin/main"])
    assert rc == 1
    assert "ENFORCE verdict: FAIL" in capsys.readouterr().out


def test_surface_detection_failure_still_prints_remind(monkeypatch, capsys):
    # R1: a git failure during surface detection must still print the REMIND checklist + exit 1.
    def boom(base, run=None):
        raise RuntimeError("git failed (128): bad base")
    monkeypatch.setattr(vsc, "changed_paths", boom)
    rc = vsc.main(["--base", "does-not-exist"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "surface-detection" in out and "FAIL" in out
    assert "[REMIND]" in out


def test_module_loads_standalone():
    # The verifier must itself pass the standalone-invocation check it enforces.
    res = vsc.check_standalone_scripts([str(vsc._REPO_ROOT / "scripts" / "verify_sprint_closeout.py")])
    assert res.passed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -k "main or standalone" -v`
Expected: FAIL — `main` not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# append to scripts/verify_sprint_closeout.py
import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sprint-closeout verification tollgate.")
    parser.add_argument("--base", default="origin/main", help="ref to diff against for surface detection")
    args = parser.parse_args(argv)
    try:  # F3: a git failure (e.g. missing --base) is a fail-loud CLI error, not an empty surface
        surfaces = detect_surfaces(changed_paths(args.base), added=added_paths(args.base))
    except RuntimeError as exc:
        # R1: REMIND is ALWAYS printed, even on surface-detection failure.
        results = [CheckResult("surface-detection", ENFORCE, False, str(exc)), remind_checklist()]
        print(render(results))
        return exit_code(results)  # 1 — an ENFORCE check failed
    results = run_verification(surfaces, base=args.base)
    print(render(results))
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -v`
Expected: PASS (all tasks' tests).

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add scripts/verify_sprint_closeout.py tests/test_verify_sprint_closeout.py
git commit -m "feat(verifier): CLI main() + module-loads-standalone self-check"
```

---

## Task 7: `02-agent-operating-loop.md` tollgate amendment

**Files:**
- Modify: `docs/governance/02-agent-operating-loop.md` (add a subsection under Postflight / Git-and-PR)
- Test: `tests/test_governance_tollgate_clause.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_governance_tollgate_clause.py
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "02-agent-operating-loop.md"


def test_tollgate_clause_present_and_references_verifier():
    text = DOC.read_text(encoding="utf-8")
    assert "Sprint-closeout tollgate" in text
    assert "scripts/verify_sprint_closeout.py" in text
    # references, does not restate philosophy: the clause points back to this doc's discipline
    assert "ENFORCE" in text and "full suite" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_governance_tollgate_clause.py -v`
Expected: FAIL — clause absent.

- [ ] **Step 3: Write minimal implementation**

Add this subsection to `docs/governance/02-agent-operating-loop.md` under the Postflight / Git-and-PR area:

```markdown
### Sprint-closeout tollgate

Before claiming a multi-task build or phase is verified/complete, and before any push or PR, run `scripts/verify_sprint_closeout.py`. Its ENFORCE checks (full Python suite — not focused slices — `.venv/bin/ruff check src app`, and the FE gate + standalone-script checks when those surfaces are touched) must pass; its REPORT items (changed tracked artifacts, new files in guarded directories) must be audited; and its REMIND human-judgment gates (David authorization, cockpit routing, close-the-loop, CI-as-gate) must be satisfied. Focused per-task test slices are acceptable mid-build, but the full suite + full FE gate run here is the binding closeout verification. This tollgate does not replace cockpit review or David's authorization — it ensures the deterministic matrix is not skipped.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_governance_tollgate_clause.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add docs/governance/02-agent-operating-loop.md tests/test_governance_tollgate_clause.py
git commit -m "docs(governance): mandate the sprint-closeout verifier at the ship/PR tollgate"
```

---

## Task 8: Falsification sweep + real-run smoke + closeout

**Files:**
- Modify: `tests/test_verify_sprint_closeout.py` (falsification rows)
- Verify: real invocation + full Python suite + surface-conditional gates (R4 — FE gate runs only if `frontend/` is touched; the verifier verifying its own repo state)

- [ ] **Step 1: Write the failing falsification tests**

```python
# append to tests/test_verify_sprint_closeout.py
def test_no_change_diff_still_runs_always_checks():
    s = vsc.detect_surfaces(set(), added=set())
    names = {r.name for r in vsc.run_verification(s, run=lambda c, cwd=None: _ok(rc=0))}
    assert {"python-suite", "ruff", "report", "remind"} <= names


def test_report_only_never_affects_exit_code():
    results = [vsc.CheckResult("report", vsc.REPORT, None, "stuff"),
               vsc.CheckResult("remind", vsc.REMIND, None, "x")]
    assert vsc.exit_code(results) == 0  # no ENFORCE failures -> 0 regardless of REPORT content


def test_ruff_absent_binary_fails_loud():
    res = vsc.check_ruff(run=lambda c, cwd=None: _ok(stdout=""))  # no version string
    assert res.passed is False and "install" in res.detail.lower()
```

- [ ] **Step 2: Run to verify (pass against Tasks 3/5 impl)**

Run: `.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py -v`
Expected: PASS; fix any gap surfaced.

- [ ] **Step 3: Real-run smoke**

Run: `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main`
Expected: runs standalone (no `ModuleNotFoundError`), prints ENFORCE/REPORT/REMIND sections + an ENFORCE verdict; exit non-zero only if a real ENFORCE check fails. NOTE (Codex non-blocking): the FE gate runs ONLY when a `frontend/` surface is detected — this verifier build touches `scripts/`+`docs/`+`tests/`, not `frontend/`, so the FE gate is correctly skipped in its own smoke; the standalone-script check WILL run (scripts/ touched) and must pass on `verify_sprint_closeout.py` itself.

- [ ] **Step 4: Full verification**

Run:
```bash
.venv/bin/python3.14 -m pytest tests/test_verify_sprint_closeout.py tests/test_governance_tollgate_clause.py -v
.venv/bin/ruff check src app    # verifier lives in scripts/, not src/app — confirms no CI-scope regression
```
Expected: all green; the verifier + governance clause are self-consistent (the verifier's own REMIND/clause text carries no banned David-facing tokens).

- [ ] **Step 5: Commit + closeout** (after dual-CLEAR)

```bash
git add tests/test_verify_sprint_closeout.py
git commit -m "test(verifier): falsification sweep (no-change, report-only, ruff-absent fail-loud)"
```

---

## Self-review checklist (run before cockpit handoff)
- [ ] Spec coverage: §2 three-tier (T1 schema, T3 ENFORCE, T4 REPORT/REMIND), §3.2 surface union (T2), §3.3 ENFORCE incl. ruff version-assert + standalone-load (T3), §3.4 REPORT (T4), §3.5 REMIND (T4), §3.6 exit semantics (T5), §3.1 CLI/--base/text-only (T6), §4 02 amendment (T7), §6 testing/falsification (all + T8). No `--phase`, no `--json` (correct).
- [ ] No placeholders: every step has real code + exact commands. `run` injection seam used throughout for stub-ability.
- [ ] Type consistency: `CheckResult(name, tier, passed, detail)` identical across tasks; `run(cmd, cwd=None)` signature consistent; `detect_surfaces` keys (`frontend/scripts/artifacts/new_files`) identical in T2/T5/T6/T8.

## Open notes for the GREEN author (not placeholders)
- T3 `check_standalone_scripts` loads via `sys.executable -c` so it works under pytest AND standalone; the probe inserts only the script's own dir (replicating direct execution), never the repo root.
- T5/T6 inject `standalone=` and monkeypatch `changed_paths/added_paths/run_verification` so tests never invoke the real suite/git — keeping the test fast + deterministic.
- T8 Step 3 is the only step that runs the REAL suite/FE gate (the verifier on its own repo); it is a smoke check, not a stubbed unit test.
