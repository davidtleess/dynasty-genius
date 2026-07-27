"""Contract tests for scripts/verify_closeout.py — the cockpit-closeout verifier.

Every ENFORCE check here maps to a defect the 2026-07-25/26 closeout actually had
to be rescued from; the mapping is named in each test's docstring so a future reader
can tell ceremony from a real gate.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "vco",
    Path(__file__).resolve().parents[1] / "scripts" / "verify_closeout.py",
)
vco = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = vco
_SPEC.loader.exec_module(vco)


class _R:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _runner(table, default=None):
    """Dispatch a fake `run` off a substring of the joined command."""

    def run(cmd, cwd=None, timeout=None):
        joined = " ".join(cmd)
        for key, result in table.items():
            if key in joined:
                return result
        if default is not None:
            return default
        raise AssertionError(f"unexpected command: {joined}")

    return run


# --------------------------------------------------------------------------- tiers


def test_tiers_and_checkresult_shape():
    assert (vco.ENFORCE, vco.REPORT, vco.REMIND) == ("ENFORCE", "REPORT", "REMIND")
    r = vco.CheckResult(name="x", tier=vco.ENFORCE, passed=False, detail="d")
    assert (r.name, r.tier, r.passed, r.detail) == ("x", "ENFORCE", False, "d")
    assert vco.CheckResult("y", vco.REPORT, None, "d").passed is None


def test_today_ledger_path_is_iso_dated():
    assert vco.today_ledger_path("2026-07-26") == "docs/agent-ledger/2026-07-26.md"


# ------------------------------------------------- C1 durable record (defect 1)


def test_durable_record_fails_when_ledger_is_untracked():
    """Defect 1: CLOSED declared while the postflight ledger existed only untracked."""
    run = _runner({
        "ls-files --others": _R(stdout="docs/agent-ledger/2026-07-26.md\n"),
        "diff --name-only": _R(stdout=""),
    })
    res = vco.check_durable_record("2026-07-26", run=run, exists=lambda p: True,
                                   tracked=lambda p: True)
    assert res.tier == vco.ENFORCE and res.passed is False
    assert "docs/agent-ledger/2026-07-26.md" in res.detail
    assert "uncommitted" in res.detail.lower()


def test_durable_record_fails_when_state_board_is_modified():
    """Defect 1 sibling: AGENT_SYNC.md flushed to disk but never committed."""
    run = _runner({
        "ls-files --others": _R(stdout=""),
        "diff --name-only --cached": _R(stdout=""),
        "diff --name-only": _R(stdout="AGENT_SYNC.md\n"),
    })
    res = vco.check_durable_record("2026-07-26", run=run, exists=lambda p: True,
                                   tracked=lambda p: True)
    assert res.passed is False and "AGENT_SYNC.md" in res.detail


def test_durable_record_fails_when_todays_ledger_absent_entirely():
    """A session that never wrote a postflight must not pass on an empty tree."""
    run = _runner({"ls-files --others": _R(stdout=""), "diff --name-only": _R(stdout="")})
    res = vco.check_durable_record("2026-07-26", run=run, exists=lambda p: False)
    assert res.passed is False and "absent" in res.detail.lower()


def test_durable_record_fails_when_the_ledger_is_present_but_untracked():
    """Codex r1 BLOCKER 1: a gitignored ledger is absent from `--others` AND from the
    diff, so absence-from-the-dirty-set was being read as `committed`. A false CLEAN
    on the exact surface the gate exists to protect."""
    run = _runner({"ls-files --others": _R(stdout=""), "diff --name-only": _R(stdout="")})
    res = vco.check_durable_record("2026-07-26", run=run, exists=lambda p: True,
                                   tracked=lambda p: False)
    assert res.passed is False
    assert "not tracked" in res.detail.lower()
    assert "docs/agent-ledger/2026-07-26.md" in res.detail


def test_durable_record_passes_only_when_tracked_committed_and_present():
    run = _runner({"ls-files --others": _R(stdout=""), "diff --name-only": _R(stdout="")})
    res = vco.check_durable_record("2026-07-26", run=run, exists=lambda p: True,
                                   tracked=lambda p: True)
    assert res.passed is True and "committed" in res.detail.lower()


# ---------------------------------------------- C2 working tree (defect 3: count)


def test_working_tree_reports_exact_paths_and_count():
    """Defect 3: the closeout asked to confirm six uncommitted files; there were eight."""
    run = _runner({
        "ls-files --others": _R(stdout="a.md\nb.md\n"),
        "diff --name-only --cached": _R(stdout="c.py\n"),
        "diff --name-only": _R(stdout="d.py\n"),
    })
    res = vco.check_working_tree(run=run)
    assert res.passed is False
    assert "4 uncommitted" in res.detail
    for path in ("a.md", "b.md", "c.py", "d.py"):
        assert path in res.detail


def test_working_tree_passes_on_empty_tree():
    run = _runner({"ls-files --others": _R(stdout=""), "diff --name-only": _R(stdout="")})
    assert vco.check_working_tree(run=run).passed is True


# ------------------------------------------------------------- added-line surface


def test_ephemeral_locators_flags_every_session_scoped_form():
    """RISK-1 + the machine-bound reproducer: evidence that dies with the session."""
    lines = [
        "verdict at /tmp/codex_d3d_green_r3_clear.md",
        "review at /private/tmp/codex_pick_plan_v1_review.txt",
        "cache under /var/folders/xy/T/probe.json",
        "plan at <session-scratchpad>/pick-valuation-plan-v2.md",
        "reproducer reads /Users/davidleess/frontend-studio/proposals/009-RELAY.md",
    ]
    res = vco.check_ephemeral_locators(lines)
    assert res.tier == vco.ENFORCE and res.passed is False
    for fragment in ("/tmp/codex_d3d", "/private/tmp/", "/var/folders/",
                     "<session-scratchpad>", "/Users/davidleess/"):
        assert fragment in res.detail


def test_a_gitignored_file_citation_is_reported():
    """The core defect: 02 nearly shipped citing a skill under gitignored `.agents/`,
    which resolves for the author and is absent from a fresh clone. Now SURFACED as a
    REPORT for human audit rather than enforced — the check informs, it does not judge."""
    run = _runner({}, default=_R())
    bad = vco.report_citations(["the procedure is `.agents/skills/cockpit-messaging/SKILL.md`"],
                               run=run, exists=lambda p: True, ignored=lambda p: True)
    assert bad.tier == vco.REPORT and bad.passed is None
    assert "gitignored" in bad.detail and ".agents/skills/cockpit-messaging/SKILL.md" in bad.detail


def test_ephemeral_locators_passes_on_durable_paths_only():
    lines = ["promoted to docs/validation/2026-07-25-studio-009-relay-verification.md"]
    assert vco.check_ephemeral_locators(lines).passed is True


def test_ephemeral_locators_passes_on_empty_surface():
    """No added lines is a real state (nothing written yet), not a failure."""
    assert vco.check_ephemeral_locators([]).passed is True


# ------------------------------------------- C4 dangling citations (defect 4)


def test_repo_facts_reports_machine_read_state_not_prose():
    """Defect 2: the closeout order asserted HEAD/ahead-behind and was wrong on all of it."""
    run = _runner({
        "rev-parse HEAD": _R(stdout="2102a2a\n"),
        "rev-parse origin/main": _R(stdout="59ba925\n"),
        "rev-list --left-right --count": _R(stdout="1\t3\n"),
        "ls-files --others": _R(stdout="x.md\n"),
        "diff --name-only": _R(stdout=""),
    })
    res = vco.report_repo_facts(run=run)
    assert res.tier == vco.REPORT and res.passed is None
    assert "2102a2a" in res.detail and "59ba925" in res.detail
    assert "behind 1" in res.detail and "ahead 3" in res.detail


# ------------------------------------------------------- C6 pushed CI (defect 5)


def test_pushed_ci_reports_conclusion_when_available():
    """The 07-26 residual: the board omitted that pushed main was CI-red."""
    run = _runner({"gh": _R(stdout='[{"databaseId":30202569707,"conclusion":"success",'
                                   '"headSha":"59ba925","status":"completed"}]')})
    res = vco.report_pushed_ci(run=run)
    assert res.tier == vco.REPORT
    assert "30202569707" in res.detail and "success" in res.detail


def test_pushed_ci_is_unknown_not_crash_when_gh_absent():
    run = _runner({"gh": _R(returncode=127, stderr="gh: not found")})
    assert "UNKNOWN" in vco.report_pushed_ci(run=run).detail


def test_pushed_ci_is_unknown_on_malformed_payload():
    run = _runner({"gh": _R(stdout="not json")})
    assert "UNKNOWN" in vco.report_pushed_ci(run=run).detail


# ------------------------------------------ C7 session commits (parked audits)


def test_session_commits_lists_todays_commits_for_audit_disclosure():
    """Codex's two required post-commit divergence audits were parked, undisclosed."""
    run = _runner({"log": _R(stdout="2102a2a docs(state): record closeout CI green\n"
                                    "59ba925 fix(closeout): restore CI reproducibility\n")})
    res = vco.report_session_commits("2026-07-26", run=run)
    assert "2102a2a" in res.detail and "59ba925" in res.detail
    assert "divergence audit" in res.detail.lower()


def test_session_commits_says_none_when_nothing_landed():
    run = _runner({"log": _R(stdout="")})
    assert "no commits" in vco.report_session_commits("2026-07-26", run=run).detail.lower()


# -------------------------------------------------------------- C8 background


def test_background_scan_is_unknown_when_tool_missing():
    run = _runner({}, default=_R(returncode=127, stderr="pgrep: not found"))
    assert "UNKNOWN" in vco.report_background(run=run).detail


# ------------------------------------------------------------------- assembly


def test_remind_names_the_gates_the_probe_had_to_uncover():
    text = vco.remind_checklist().detail.lower()
    for token in ("cross-lane", "authority", "unverified", "deferred", "delivery"):
        assert token in text


def test_exit_code_flips_only_on_enforce_failure():
    assert vco.exit_code([vco.CheckResult("a", vco.REPORT, None, "")]) == 0
    assert vco.exit_code([vco.CheckResult("a", vco.ENFORCE, True, "")]) == 0
    assert vco.exit_code([vco.CheckResult("a", vco.ENFORCE, False, "")]) == 1


def test_render_verdict_speaks_the_closeout_status_vocabulary():
    """The gate's output must name the status a lane may claim, not a bare PASS/FAIL."""
    clean = vco.render([vco.CheckResult("a", vco.ENFORCE, True, "ok")])
    assert "closed — clean" in clean
    dirty = vco.render([vco.CheckResult("a", vco.ENFORCE, False, "bad")])
    assert "MAY NOT" in dirty and "closed — parked" in dirty


def test_render_segregates_tiers():
    out = vco.render([
        vco.CheckResult("e", vco.ENFORCE, True, "ok"),
        vco.CheckResult("r", vco.REPORT, None, "facts"),
        vco.CheckResult("m", vco.REMIND, None, "judgement"),
    ])
    assert out.index("[ENFORCE]") < out.index("[REPORT]") < out.index("[REMIND]")


def test_main_fails_loud_on_git_error_but_still_prints_remind(capsys):
    def run(cmd, cwd=None, timeout=None):
        return _R(returncode=128, stderr="fatal: bad revision 'nope'")

    rc = vco.main(["--base", "nope"], run=run)
    out = capsys.readouterr().out
    assert rc == 1
    assert "[REMIND]" in out
    assert "bad revision" in out


def test_script_is_executable_end_to_end():
    """The verifier must actually run against this repo without crashing."""
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "verify_closeout.py")],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode in (0, 1), proc.stderr
    assert "closeout verdict:" in proc.stdout


# ------------------------------------------------------------------ surviving checks
#
# The waiver machinery these tests once guarded was DELETED (David, 2026-07-26, Option 2).
# What remains are the three ENFORCE checks — each a mechanical fact about the repo — and
# the REPORT blocks a human audits.


def test_file_line_citations_resolve_to_their_file():
    """`scripts/dg_delivery.py:76` is the repo's standard citation form — governance,
    review verdicts, and every packet use it. Treating the `:76` as part of the path made
    the gate fail on ordinary review prose, which is the false-positive class that gets a
    gate routed around. The line suffix is stripped before resolution."""
    run = _runner({}, default=_R())
    seen = {}

    def exists(p):
        seen[p] = True
        return p == "scripts/dg_delivery.py"

    res = vco.report_citations(
        ["defect at scripts/dg_delivery.py:76 and spec:53"], run=run, exists=exists,
        ignored=lambda p: False)
    assert "does not resolve" not in res.detail
    assert "scripts/dg_delivery.py" in seen and "scripts/dg_delivery.py:76" not in seen


def test_file_line_range_citations_also_resolve():
    run = _runner({}, default=_R())
    res = vco.report_citations(
        ["see src/dynasty_genius/mod.py:58,1190-1193"], run=run,
        exists=lambda p: p == "src/dynasty_genius/mod.py", ignored=lambda p: False)
    assert "does not resolve" not in res.detail


def test_a_genuinely_missing_file_with_a_line_suffix_is_reported():
    run = _runner({}, default=_R())
    res = vco.report_citations(["see docs/gone.md:12"], run=run, exists=lambda p: False)
    assert res.tier == vco.REPORT and "docs/gone.md" in res.detail


def _diff_runner(per_file, committed=(), worktree=(), untracked=()):
    """Fake `run` for the PER-FILE diff mechanism `added_lines` now uses."""
    def run(cmd, cwd=None, timeout=None):
        joined = " ".join(cmd)
        if "diff --name-only origin/main...HEAD" in joined:
            return _R(stdout="".join(f"{p}\n" for p in committed))
        if "diff --name-only HEAD" in joined:
            return _R(stdout="".join(f"{p}\n" for p in worktree))
        if "ls-files --others" in joined:
            return _R(stdout="".join(f"{p}\n" for p in untracked))
        for path, body in per_file.items():
            if joined.endswith(path):
                return _R(stdout=body)
        return _R(stdout="")
    return run


def _hunk(*added):
    return "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n" + "".join(
        f"+{a}\n" for a in added)


def test_added_lines_unions_committed_worktree_and_untracked():
    run = _diff_runner(
        {"docs/a.md": _hunk("committed add"), "AGENT_SYNC.md": _hunk("worktree add")},
        committed=["docs/a.md"], worktree=["AGENT_SYNC.md"], untracked=["docs/new.md"])
    lines = vco.added_lines(base="origin/main", run=run, read_text=lambda p: "untracked add\n")
    assert {"committed add", "worktree add", "untracked add"} <= set(lines)


def test_added_lines_survives_unreadable_untracked_file():
    """A binary or vanished untracked path must not crash the closeout gate."""
    def read_text(path):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")

    run = _diff_runner({}, untracked=["docs/validation/evidence/blob.bin"])
    assert vco.added_lines(base="origin/main", run=run, read_text=read_text) == []


def test_added_lines_scans_the_closeout_record_not_source_code():
    """The defect class is a closeout RECORD citing storage that dies with the session.
    Source and test code legitimately hold path literals and are governed by ruff and the
    suite, not by this gate."""
    run = _diff_runner(
        {"docs/a.md": _hunk("ledger line"), "tests/t.py": _hunk("fixture = '/tmp/x'")},
        committed=["docs/a.md", "tests/t.py"], untracked=["src/dynasty_genius/new.py"])
    lines = vco.added_lines(base="origin/main", run=run, read_text=lambda p: "source line\n")
    assert lines == ["ledger line"]


def test_content_cannot_be_mistaken_for_diff_metadata():
    """Codex: an added Markdown line beginning `++ ` renders as `+++ ` in a combined diff
    and was read as a file header, suppressing every following line — a PASS over ZERO
    scanned lines, an ENFORCE false pass driven by document content.

    Diffs are now taken PER FILE and content is read only after the first `@@`."""
    run = _diff_runner(
        {"docs/a.md": _hunk("++ evidence section", "/tmp/live-closeout-evidence.json")},
        committed=["docs/a.md"])
    lines = vco.added_lines(base="origin/main", run=run)
    assert "++ evidence section" in lines, "an added `++ ` line is content, not a header"
    assert "/tmp/live-closeout-evidence.json" in lines, "the following line must not be hidden"
    assert vco.check_ephemeral_locators(lines).passed is False


def test_fenced_content_is_scanned_no_undeclared_exemption():
    """Excluding fenced blocks as "quoted material" was an UNDECLARED EXEMPTION to a rule
    whose whole point is that it has none — a temp locator inside a fence escaped
    `ephemeral-locators` entirely. A quoted probe input is where a dead path hides."""
    run = _diff_runner(
        {"docs/a.md": _hunk("prose", "```text", "parked at /tmp/secret-packet.md", "```")},
        committed=["docs/a.md"])
    lines = vco.added_lines(base="origin/main", run=run)
    assert "parked at /tmp/secret-packet.md" in lines
    assert vco.check_ephemeral_locators(lines).passed is False
