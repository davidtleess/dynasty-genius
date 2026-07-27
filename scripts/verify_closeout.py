"""Governed cockpit-closeout verifier (2026-07-26 closeout-hardening amendment).

Sibling to `verify_sprint_closeout.py`, and deliberately NOT the same gate:

- `verify_sprint_closeout.py` asks "is the CODE shippable?" (pytest, ruff, FE gate).
- this script asks "is the CLOSE honest and DURABLE?" — the surface on which the
  2026-07-25/26 closeout failed while the code gate was fully green.

Every ENFORCE check maps to a defect that closeout actually had to be rescued from;
the mapping is named in each check so a later reader can tell a real gate from
ceremony. Read-only: never installs, downloads, or mutates source/artifacts/git.

THREE ENFORCE checks — durable-record, working-tree, ephemeral-locators — plus citations
as REPORT (David, 2026-07-26, "Option 2"). Citation-checking was demoted because deciding
in prose which path-shaped strings are binding citations is not decidable, and the waiver
machinery built to decide it produced four consecutive rounds of defects of its own. The
gate is smaller on purpose: what it still ENFORCEs, it can defend.

Exit contract (the whole point — it is NOT pass/fail):
  0 -> this lane MAY report `closed — clean`
  1 -> this lane MAY NOT claim clean; report `closed — parked` or `closeout-blocked`
       naming the reasons printed above. A 1 is a truthful close, not a blocked one.

Helpers are duplicated from the sibling verifier rather than imported: both scripts
must load with the repo root off sys.path (the standalone-script contract in
`verify_sprint_closeout.check_standalone_scripts`), and the sibling mutates sys.path
at import time. Twenty lines of duplication buys a hermetic gate.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

ENFORCE, REPORT, REMIND = "ENFORCE", "REPORT", "REMIND"

STATE_BOARD = "AGENT_SYNC.md"
LEDGER_DIR = "docs/agent-ledger"


@dataclass
class CheckResult:
    name: str
    tier: str
    passed: bool | None  # None for REPORT/REMIND (no verdict)
    detail: str


class _Completed:
    """Uniform result so a missing binary reports (rc 127) instead of crashing."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _subprocess_run(cmd, cwd=None, timeout=None):
    try:
        return subprocess.run(cmd, cwd=cwd or str(_REPO_ROOT), capture_output=True,
                              text=True, timeout=timeout)
    except FileNotFoundError as exc:
        return _Completed(127, "", f"{cmd[0]}: not found ({exc})")
    except subprocess.TimeoutExpired:
        return _Completed(124, "", f"{cmd[0]}: timed out")


def _lines(out: str) -> list[str]:
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _git(cmd: list[str], run) -> list[str]:
    """Fail loud on nonzero: an empty surface would silently skip the gate."""
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"git failed ({r.returncode}): {' '.join(cmd)} :: {(r.stderr or '').strip()}")
    return _lines(r.stdout)


def _exists(path: str) -> bool:
    return (_REPO_ROOT / path).exists()


def _today() -> str:
    return date.today().isoformat()


def today_ledger_path(today: str) -> str:
    return f"{LEDGER_DIR}/{today}.md"


def uncommitted_paths(run=_subprocess_run) -> list[str]:
    """Staged + unstaged + untracked. This is the set a closeout must state exactly."""
    paths: set[str] = set()
    paths |= set(_git(["git", "diff", "--name-only", "--cached"], run))
    paths |= set(_git(["git", "diff", "--name-only"], run))
    paths |= set(_git(["git", "ls-files", "--others", "--exclude-standard"], run))
    return sorted(paths)


# ------------------------------------------------------------------ ENFORCE checks


def _tracked(path: str, run=_subprocess_run) -> bool:
    return run(["git", "ls-files", "--error-unmatch", path]).returncode == 0


def check_durable_record(today: str, run=_subprocess_run, exists=_exists,
                         tracked=None) -> CheckResult:
    """Defect 1 of the 2026-07-25 close: CLOSED was declared while the postflight
    ledger and AGENT_SYNC existed only in a working tree. On disk is not durable —
    a discarded tree, a prune, or a fresh clone loses it. Committed is durable.

    Trackedness is PROVEN, never inferred from absence in the dirty set: a gitignored
    file is absent from `git ls-files --others --exclude-standard` and from the diff,
    so the inference certified a gitignored ledger as committed — a false CLEAN on the
    exact surface this gate protects (Codex r1 BLOCKER 1)."""
    is_tracked = tracked or (lambda p: _tracked(p, run=run))
    ledger = today_ledger_path(today)
    if not exists(ledger):
        return CheckResult("durable-record", ENFORCE, False,
                           f"{ledger} is absent — no postflight was written for this session")
    untracked = [p for p in (ledger, STATE_BOARD) if not is_tracked(p)]
    if untracked:
        return CheckResult("durable-record", ENFORCE, False,
                           "the session's durable record is NOT TRACKED by git: "
                           + ", ".join(untracked)
                           + " — present on disk but absent from a fresh clone (gitignored or "
                             "never added); it must be committed before any lane reports clean")
    dirty = [p for p in uncommitted_paths(run=run) if p in (ledger, STATE_BOARD)]
    if dirty:
        return CheckResult("durable-record", ENFORCE, False,
                           "the session's durable record is UNCOMMITTED: " + ", ".join(dirty)
                           + f" — on disk is not durable; {ledger} and {STATE_BOARD} must be "
                             "committed before any lane reports clean")
    return CheckResult("durable-record", ENFORCE, True,
                       f"{ledger} tracked and committed; {STATE_BOARD} tracked and committed")


def check_working_tree(run=_subprocess_run) -> CheckResult:
    """Defect 3: the closeout asked David to confirm six uncommitted files when there
    were eight. The exact set is machine-readable; recollection is not."""
    paths = uncommitted_paths(run=run)
    if paths:
        return CheckResult("working-tree", ENFORCE, False,
                           f"{len(paths)} uncommitted path(s) — each must be named with its "
                           "park location and next gate in a `closed — parked` reply:\n  "
                           + "\n  ".join(paths))
    return CheckResult("working-tree", ENFORCE, True, "working tree clean (0 uncommitted paths)")


EPHEMERAL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"/private/tmp/\S+", "session-scoped /private/tmp locator"),
    (r"/var/folders/\S+", "per-session macOS temp locator"),
    (r"(?<![\w.])/tmp/\S+", "session-scoped /tmp locator"),
    (r"<session-scratchpad>\S*", "placeholder scratchpad locator"),
    (r"/Users/[A-Za-z0-9._-]+/\S+", "machine-bound absolute home path"),
)
def check_ephemeral_locators(lines: list[str]) -> CheckResult:
    """RISK-1 and the machine-bound reproducer. Two distinct 07-26 rescues: ~30 closeout
    artifacts existed only under /tmp, and the promoted evidence still CITED /tmp paths
    and hardcoded a home directory — a promoted document pointing at a dead path is not
    durable evidence, it is a pointer to nothing.

    Scoped to lines this session ADDS, so the committed historical archive (correctly
    full of such paths, as history) never trips the gate.

    NO WAIVERS (David, 2026-07-26, Option 2). The rule is simply: do not write a
    session-scoped or machine-bound locator into the closeout record. To discuss one,
    describe it — "a session-scoped temp path" — rather than reproducing it. The waiver
    system that used to sit here generated more defects than the check it guarded."""
    hits = sorted({f"{label}: {locator}"
                   for line in lines
                   for pattern, label in EPHEMERAL_PATTERNS
                   for locator in re.findall(pattern, line)})
    if hits:
        return CheckResult("ephemeral-locators", ENFORCE, False,
                           "closeout text cites storage that dies with the session — promote "
                           "the artifact into the repo, or describe the path instead of "
                           "reproducing it:\n  " + "\n  ".join(hits))
    return CheckResult("ephemeral-locators", ENFORCE, True,
                       f"no session-scoped or machine-bound locators in {len(lines)} added line(s)")

def _looks_like_repo_path(token: str) -> bool:
    """A backticked token is a repo citation only if it is rooted at a content root or
    is a root-level file. Backticks wrap far more prose than paths, so this must not
    over-reach: `bool`, `--base origin/main`, and `.venv/bin/python3.14` are not paths."""
    token = token.strip()
    if not token or any(t in token for t in _TEMPLATE_TOKENS):
        return False
    parts = token.split()
    if any(p.startswith("-") for p in parts) or any(c in token for c in "|;&><"):
        return False  # an invocation, not a citation: `scripts/x.py --base origin/main`
    if "/" in token:
        return token.split("/", 1)[0] in _CITED_ROOTS
    return token in _ROOT_FILES


def cited_paths(line: str) -> set[str]:
    """Repo paths cited on one line, from two grammars: backtick-delimited (which may
    contain spaces — the repo really has `docs/strategies/UI Research/`) and bare prose
    (rooted, no spaces). Whole whitespace-tokens containing template characters are
    dropped, so a glob like `…/2026-07-25-studio-009-*.png` never yields a prefix."""
    found: set[str] = set()
    for token in _BACKTICK_RE.findall(line):
        if _looks_like_repo_path(token):
            found.add(token.strip())
    for token in _BACKTICK_RE.sub(" ", line).split():
        if any(t in token for t in _TEMPLATE_TOKENS):
            continue
        found |= set(_REPO_PATH_RE.findall(token))
    # `file.py:76` and `file.py:58,1190-1193` are the repo's standard citation form —
    # governance, review verdicts, and every review packet use it. Resolving the whole
    # token as a path failed the gate on ordinary review prose, which is precisely the
    # false-positive class that gets a gate routed around rather than fixed.
    return {_LINE_SUFFIX_RE.sub("", path) for path in found}


def _ignored(path: str, run=_subprocess_run) -> bool:
    return run(["git", "check-ignore", "-q", path]).returncode == 0


# ------------------------------------------------------- citation extraction (REPORT)
#
# Content roots only. Agent-config dot-directories are listed explicitly rather than
# matched as `\.[a-z]+/`, because `.venv/bin/python3.14` is a command every doc quotes
# and is always gitignored — treating it as a citation would flag almost every closeout.
_CITED_ROOTS = ("docs", "scripts", "src", "tests", "app", "frontend",
                ".claude", ".github", ".gemini", ".agents", ".codex", ".cursor")
_ROOTS_ALT = "|".join(re.escape(r) for r in _CITED_ROOTS)
# Bare-prose form: a rooted path ending in an extension OR a trailing slash (directory).
_REPO_PATH_RE = re.compile(
    rf"(?<![\w/])((?:{_ROOTS_ALT})/[A-Za-z0-9._/-]*(?:\.[A-Za-z0-9]+|/))")
# Root-level files are an explicit ALLOWLIST, not a shape: a bare basename is
# indistinguishable from prose (`02-agent-operating-loop.md` does not live at the root).
_ROOT_FILES = frozenset({"AGENT_SYNC.md", "CLAUDE.md", "AGENTS.md", "GEMINI.md",
                         "PRODUCT.md", "DESIGN.md", "README.md", "pyproject.toml",
                         ".gitignore", ".pre-commit-config.yaml"})
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# Trailing `:76` / `:58,1190-1193` line-and-range suffix on a cited path.
_LINE_SUFFIX_RE = re.compile(r":\d+(?:[,-]\d+)*$")
# Only an EXPLICIT `commit <sha>` reference: the ledgers are full of SHA-256 artifact
# digests, and treating one as a commit is a false report on legitimate record prose.
_COMMIT_SHA_RE = re.compile(r"\bcommits?\s+`?([0-9a-f]{7,40})`?")
_TEMPLATE_TOKENS = ("YYYY", "MM-DD", "<", ">", "*", "{", "}", "\u2026")


def report_citations(lines: list[str], run=_subprocess_run, exists=_exists,
                     ignored=None) -> CheckResult:
    """Unresolved repo citations in the closeout record — REPORT, not ENFORCE.

    Demoted by David 2026-07-26 (Option 2). Enforcing this required deciding, in prose,
    which path-shaped strings were binding citations and which were examples. Four
    consecutive review rounds found defects not in the gate's purpose but in the waiver
    machinery built to make that distinction: over-waiving by substring, by dot-suffix,
    by directory prefix, by hex-inside-a-word, by marker bleed. The distinction is not
    decidable from prose, so this check now informs the reader instead of blocking.

    Defect 4 of the 2026-07-25 close (a spec citing a ruling that was not yet in the
    repo) is still surfaced here — a human reads it, rather than a regex adjudicating it.

    NOT built toward: Codex's structured-evidence design (enforce only machine-readable
    binding citations) is recorded as a target direction and is a future David decision.
    This demotion deliberately does not assume it."""
    is_ignored = ignored or (lambda p: _ignored(p, run=run))
    missing, hidden, bad_shas = set(), set(), set()
    for line in lines:
        for path in cited_paths(line):
            if not exists(path):
                missing.add(path)
            elif is_ignored(path):
                hidden.add(path)
        for sha in _COMMIT_SHA_RE.findall(line):
            if run(["git", "cat-file", "-e", f"{sha}^{{commit}}"]).returncode != 0:
                bad_shas.add(sha)
    listed = ([f"path does not resolve: {p}" for p in sorted(missing)]
              + [f"path is gitignored (absent from a fresh clone): {p}" for p in sorted(hidden)]
              + [f"commit does not resolve: {s}" for s in sorted(bad_shas)])
    if not listed:
        return CheckResult("citations", REPORT, None,
                           "every cited repo path and explicit `commit <sha>` reference resolves")
    return CheckResult("citations", REPORT, None,
                       "cited but not resolvable — AUDIT each: a genuine dangling citation is a "
                       "defect (the 07-25 close shipped one), an example or quoted probe input "
                       "is not:\n  " + "\n  ".join(listed))

# ------------------------------------------------------------------- added surface


SCAN_PREFIXES = ("docs/",)


def is_scanned(path: str) -> bool:
    """The closeout RECORD surface: the state board, ledgers, promoted evidence,
    specs/plans, and promoted reproducers under docs/. Deliberately NOT source or
    test code — those legitimately hold path literals (`tempfile.gettempdir()`, test
    fixtures) and are governed by ruff and the suite. Dogfooding this verifier on its
    own landing is what surfaced the distinction."""
    return path == STATE_BOARD or path.startswith(SCAN_PREFIXES)




def added_lines(base: str = "origin/main", run=_subprocess_run, read_text=None) -> list[str]:
    """Text this session ADDS to the closeout record: committed vs base, plus working
    tree, plus untracked files whole.

    EVERY added line is returned. Fenced code blocks were once excluded as "quoted
    material"; a fenced temp locator therefore escaped `ephemeral-locators` entirely — an
    undeclared exemption to a rule whose whole point is that it has none. A quoted probe
    input is exactly where a dead path hides.

    Diffs are taken PER FILE and content is read only AFTER the first `@@` hunk header,
    so no added line can ever be mistaken for diff metadata. Parsing a combined diff meant
    an added Markdown line beginning `++ ` rendered as `+++ ` and was read as a file
    header, which silently suppressed every following line and returned a PASS over ZERO
    scanned lines — an ENFORCE false pass driven by document content."""
    out: list[str] = []
    reader = read_text or (lambda p: (_REPO_ROOT / p).read_text(encoding="utf-8"))

    def collect(cmd: list[str]) -> None:
        r = run(cmd)
        if r.returncode != 0:
            raise RuntimeError(f"git failed ({r.returncode}): {' '.join(cmd)} :: "
                               f"{(r.stderr or '').strip()}")
        in_body = False
        for ln in (r.stdout or "").splitlines():
            if not in_body:
                # Everything before the first hunk header is metadata, by diff grammar.
                if ln.startswith("@@"):
                    in_body = True
                continue
            if ln.startswith("+"):
                out.append(ln[1:].strip())

    committed = set(_git(["git", "diff", "--name-only", f"{base}...HEAD"], run))
    worktree = set(_git(["git", "diff", "--name-only", "HEAD"], run))
    for path in sorted(p for p in committed if is_scanned(p)):
        collect(["git", "diff", "--unified=0", f"{base}...HEAD", "--", path])
    for path in sorted(p for p in worktree if is_scanned(p)):
        collect(["git", "diff", "--unified=0", "HEAD", "--", path])
    for path in _git(["git", "ls-files", "--others", "--exclude-standard"], run):
        if not is_scanned(path):
            continue
        try:  # a binary or vanished untracked path must not crash the gate
            out += [raw.strip() for raw in reader(path).splitlines() if raw.strip()]
        except (OSError, UnicodeDecodeError, ValueError):
            continue
    return [ln for ln in out if ln]


# ------------------------------------------------------------------- REPORT checks


def report_repo_facts(run=_subprocess_run) -> CheckResult:
    """Defect 2: the closeout order asserted HEAD, the QB files' committed status,
    what stayed uncommitted, and a reviewer's clearance — and was wrong on all four
    clauses. Repo state is a fact; paste THIS block instead of recollecting it."""
    head = (run(["git", "rev-parse", "HEAD"]).stdout or "").strip()
    origin = (run(["git", "rev-parse", "origin/main"]).stdout or "").strip()
    counts = (run(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"]).stdout
              or "").split()
    behind, ahead = (counts + ["?", "?"])[:2]
    paths = uncommitted_paths(run=run)
    body = (f"HEAD {head}\norigin/main {origin}\nbehind {behind} / ahead {ahead}\n"
            f"uncommitted paths: {len(paths)}"
            + ("\n  " + "\n  ".join(paths) if paths else " (none)"))
    return CheckResult("repo-facts", REPORT, None,
                       "machine-read state — a closeout may not assert repo state it has not "
                       "read; verify any assertion in a closeout ORDER against this block "
                       "before confirming it:\n" + body)


def report_pushed_ci(run=_subprocess_run) -> CheckResult:
    """The 07-26 LOW residual: the board omitted that pushed main was CI-red and that
    the fix existed only in a working tree. Local green is not pushed green."""
    # Bounded: an unbounded network call turns the gate into something people skip.
    # A timeout degrades to UNKNOWN (rc 124 from `_subprocess_run`), never a hang.
    r = run(["gh", "run", "list", "--branch", "main", "--limit", "1",
             "--json", "databaseId,conclusion,status,headSha"], timeout=_NETWORK_TIMEOUT_S)
    if r.returncode != 0:
        return CheckResult("pushed-ci", REPORT, None,
                           f"UNKNOWN — could not read GitHub CI ({(r.stderr or '').strip() or r.returncode}); "
                           "state the CI status of pushed HEAD explicitly, or state it as UNKNOWN")
    try:
        runs = json.loads(r.stdout or "[]")
    except json.JSONDecodeError as exc:
        return CheckResult("pushed-ci", REPORT, None,
                           f"UNKNOWN — malformed gh payload ({exc}); state CI status explicitly")
    if not runs:
        return CheckResult("pushed-ci", REPORT, None, "UNKNOWN — no CI run found for main")
    latest = runs[0]
    return CheckResult("pushed-ci", REPORT, None,
                       f"latest main run {latest.get('databaseId')} on {latest.get('headSha', '')[:7]}: "
                       f"status={latest.get('status')} conclusion={latest.get('conclusion')} — "
                       "a closeout that ships red CI must SAY so on the board")


def report_session_commits(today: str, run=_subprocess_run) -> CheckResult:
    """Codex's two mandatory post-commit divergence audits were parked and unstarted
    while the close read as done (02 §Closing the loop makes them mandatory)."""
    r = run(["git", "log", f"--since={today} 00:00", "--format=%h %s"])
    commits = _lines(r.stdout) if r.returncode == 0 else []
    if not commits:
        return CheckResult("session-commits", REPORT, None,
                           "no commits dated today — nothing to close the loop on")
    return CheckResult("session-commits", REPORT, None,
                       "commits dated today — each needs its independent post-commit divergence "
                       "audit state named (CLEAR, or OPEN with an owner) in the closeout:\n  "
                       + "\n  ".join(commits))


_NETWORK_TIMEOUT_S = 20   # gh is remote; bound it or the gate can hang
_PROBE_TIMEOUT_S = 10
_BACKGROUND_PATTERNS = ("pytest", "uvicorn", "vite", "npm run", "gh run watch")


def report_background(run=_subprocess_run) -> CheckResult:
    r = run(["pgrep", "-fl", "|".join(_BACKGROUND_PATTERNS)], timeout=_PROBE_TIMEOUT_S)
    if r.returncode not in (0, 1):  # 1 = no match, a real answer
        return CheckResult("background", REPORT, None,
                           f"UNKNOWN — process scan unavailable ({(r.stderr or '').strip() or r.returncode}); "
                           "state background ownership explicitly")
    found = _lines(r.stdout)
    body = ("\n  " + "\n  ".join(found)) if found else " none matched"
    return CheckResult("background", REPORT, None,
                       "long-running processes matching "
                       f"{'/'.join(_BACKGROUND_PATTERNS)}:{body}\n"
                       "For each: state whether THIS session created it. A pre-existing "
                       "process is not yours to stop, but it is yours to disclose.")


# -------------------------------------------------------------------------- REMIND


def remind_checklist() -> CheckResult:
    text = (
        "Human-judgment gates (02 §Cockpit Closeout Motion — not restated here):\n"
        "- CROSS-LANE closeout audit: the other binding lane verifies this lane's closeout "
        "claims. Self-evidence failed repeatedly on 2026-07-25 and independent review caught "
        "it every time; a lane may not audit its own close.\n"
        "- AUTHORITY disclosure: name any decision you took that was arguably David's or "
        "another lane's to make (a ruling conflict resolved unilaterally, scope taken beyond "
        "the word given, a contract widened).\n"
        "- UNVERIFIED-claim disclosure: name every load-bearing number or claim you used but "
        "did not independently check, with its provenance lane.\n"
        "- DEFERRED-work disclosure: name any authorized work you silently parked; filing it "
        "as a future ticket is still deferring it.\n"
        "- DELIVERY: a stranded `closed` is not a close (cockpit-messaging skill). When the "
        "wire is down, the repo IS the delivery channel — commit the evidence, do not "
        "hand-carry a path.\n"
        "- FLUSH vs TERMINAL CLOSE: a new David word after a flush reopens the session; "
        "re-flush and say so. Do not spend the word `closed` on a close that will reopen.\n"
        "- An ENFORCE failure here does NOT block closing. It blocks claiming CLEAN."
    )
    return CheckResult("remind", REMIND, None, text)


# ------------------------------------------------------------------------ assembly


def run_verification(today: str, base: str = "origin/main", run=_subprocess_run) -> list[CheckResult]:
    lines = added_lines(base=base, run=run)
    return [
        check_durable_record(today, run=run),
        check_working_tree(run=run),
        check_ephemeral_locators(lines),
        report_citations(lines, run=run),
        report_repo_facts(run=run),
        report_pushed_ci(run=run),
        report_session_commits(today, run=run),
        report_background(run=run),
        remind_checklist(),
    ]


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
    if exit_code(results) == 0:
        lines.append("\ncloseout verdict: this lane MAY report `closed — clean`")
    else:
        lines.append("\ncloseout verdict: MAY NOT claim clean — report `closed — parked` "
                     "(or `closeout-blocked`) naming every ENFORCE reason above. "
                     "A truthful parked close is a success, not a failure.")
    return "\n".join(lines)


def main(argv: list[str] | None = None, run=_subprocess_run) -> int:
    parser = argparse.ArgumentParser(description="Cockpit-closeout durability verifier.")
    parser.add_argument("--base", default="origin/main", help="ref to diff added lines against")
    parser.add_argument("--today", default=None, help="ISO date of the session (default: today)")
    args = parser.parse_args(argv)
    try:
        results = run_verification(args.today or _today(), base=args.base, run=run)
    except RuntimeError as exc:  # REMIND always prints, even on a git failure
        results = [CheckResult("surface-detection", ENFORCE, False, str(exc)), remind_checklist()]
    print(render(results))
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
