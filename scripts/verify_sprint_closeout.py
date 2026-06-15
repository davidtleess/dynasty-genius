"""Governed sprint-closeout verifier (spec 2026-06-14). Pre-ship tollgate:
ENFORCE deterministic checks, REPORT human-audit surfaces, REMIND human-judgment
gates. Read-only; never installs/downloads or mutates source/artifacts/git."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
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


ARTIFACT_DIRS = ("app/data/",)
FE_DIR = "frontend/"


class _Completed:
    """Uniform result so a missing binary fails loud (rc 127) instead of crashing (F3)."""

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
    out = (v.stdout or "").strip()
    # Exact version-token match, NOT substring: `0.15.12 in "ruff 0.15.120"` is True —
    # substring membership would falsely accept 0.15.120 / 0.15.123 / 0.15.12-dev.
    parts = out.split()
    version = parts[1] if len(parts) >= 2 else ""
    if version != RUFF_PIN:
        return CheckResult("ruff", ENFORCE, False,
                           f"{RUFF_BIN} must be {RUFF_PIN} (got {out or 'absent'}); "
                           "install/update it — verifier never downloads ruff")
    r = run([RUFF_BIN, "check", "src", "app"])
    passed = r.returncode == 0
    return CheckResult("ruff", ENFORCE, passed, "ruff check src app" if passed else (r.stdout or "").strip())


def _fe_scripts(read_text=None) -> dict:
    """Discover scripts from frontend/package.json (read_text injectable for tests) (F4)."""
    raw = (read_text or (lambda: (_REPO_ROOT / FE_DIR / "package.json").read_text(encoding="utf-8")))()
    return json.loads(raw).get("scripts", {})


def check_fe_gate(run=_subprocess_run, read_text=None) -> CheckResult:
    try:  # fail loud as a clean CheckResult, not a raw traceback (spec F3 / §8 data-corruption)
        available = _fe_scripts(read_text)
    except FileNotFoundError:
        return CheckResult("fe-gate", ENFORCE, False,
                           "frontend/package.json not found (frontend surface touched but manifest absent)")
    except json.JSONDecodeError as exc:
        return CheckResult("fe-gate", ENFORCE, False,
                           f"frontend/package.json malformed: {exc}")
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
    repo root + cwd ('') REMOVED from sys.path, and the module REGISTERED in sys.modules
    before exec_module (so direct execution as __main__ — which is registered — is matched;
    without registration a valid future-annotations dataclass would falsely fail). Runs from
    a cwd OUTSIDE the repo; loads the module body only (no main()/side effects)."""
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
            "m=importlib.util.module_from_spec(s); "
            "sys.modules[s.name]=m; "
            "s.loader.exec_module(m)"
        )
        r = run([sys.executable, "-c", probe], cwd=outside)
        if r.returncode != 0:
            tail = ((r.stderr or "").strip().splitlines() or ["load failed"])[-1]
            failures.append(f"{path}: {tail}")
    passed = not failures
    return CheckResult("standalone-scripts", ENFORCE, passed,
                       "all changed scripts load standalone" if passed else "; ".join(failures))


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


def run_verification(surfaces, base="origin/main", run=_subprocess_run,
                     standalone=check_standalone_scripts) -> list[CheckResult]:
    results = [check_python_suite(run=run), check_ruff(run=run)]
    if surfaces["frontend"]:
        results.append(check_fe_gate(run=run))
    if surfaces["scripts"]:
        results.append(standalone(surfaces["scripts"], run=run))
    results.append(report_changes(surfaces["artifacts"], surfaces["new_files"], base=base, run=run))
    results.append(remind_checklist())
    return results


def exit_code(results: list[CheckResult]) -> int:
    # Only an ENFORCE failure flips the exit code; REPORT/REMIND (passed=None) never do.
    return 1 if any(r.tier == ENFORCE and r.passed is False for r in results) else 0


def render(results: list[CheckResult]) -> str:
    # Tier-segregated so a hard ENFORCE failure is visually distinct from advisory surfaces.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sprint-closeout verification tollgate.")
    parser.add_argument("--base", default="origin/main",
                        help="ref to diff against for surface detection")
    args = parser.parse_args(argv)
    try:  # F3: a git failure (e.g. a missing --base ref) is a fail-loud CLI error, not an empty surface
        surfaces = detect_surfaces(changed_paths(args.base), added=added_paths(args.base))
    except RuntimeError as exc:
        # R1: REMIND is ALWAYS printed, even on a surface-detection failure.
        results = [CheckResult("surface-detection", ENFORCE, False, str(exc)), remind_checklist()]
        print(render(results))
        return exit_code(results)  # 1 — an ENFORCE check failed
    results = run_verification(surfaces, base=args.base)
    print(render(results))
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
