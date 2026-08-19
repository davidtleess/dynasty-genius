"""Ledger Watch detection contracts.

Every test here exists because a real failure was measured on the live corpus on
2026-08-19. They are contracts, not coverage: each one pins an invariant whose
violation means a real change to the channel goes unreported.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _module():
    path = Path("scripts/ledger_watch.py")
    spec = importlib.util.spec_from_file_location("ledger_watch", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ledger_watch"] = module   # py3.14 dataclasses resolves via sys.modules
    spec.loader.exec_module(module)
    return module


lw = _module()


# ----------------------------------------------------------- the parse never gates

REAL_HEADINGS = [
    # every one of these appears verbatim in the live corpus
    "## 09:0x ET — Claude (write lane): PREFLIGHT — R1 + R2 as a coordinated group",
    "## 23:08 ET - Gemini (Operations & Telemetry)",
    "## 19:38 ET - Codex",
    "## ~23:4x ET — Claude (write lane): THE REGISTERED QB-1 STUDY COMPLETED",
    "## ~22:xx ET - Codex — QB-1 D3-c framing challenge issued; Tower owns carry",
    "## Codex — independent model reverse-engineering science design",
    "## Time Unknown - Claude Code",
    "## Session (cont.)",
    "## TERMINAL CLOSEOUT — Codex (TW27G)",
]


@pytest.mark.parametrize("heading", REAL_HEADINGS)
def test_every_real_heading_is_reported(heading: str) -> None:
    """The parse is enrichment. A heading it cannot decompose is still REPORTED.

    Measured: a strict "HH:MM ET — Author: headline" regex matched 794 of 5,601
    headings. Gating the report on the parse hid 85.8% of the channel, and the hidden
    part is where session closeouts and blocker notes live.
    """
    parsed = lw.parse_ledger(heading + "\n\nbody\n")
    depth2 = [h for h in parsed.headings if h.depth == 2]
    assert len(depth2) == 1, f"heading dropped entirely: {heading!r}"
    assert depth2[0].raw == heading[3:], "raw text must survive verbatim for quoting"
    assert depth2[0].line == 1, "line number required — blockers are quoted with file and line"


def test_obfuscated_timestamps_parse() -> None:
    """Times in this ledger are deliberately fuzzed: 09:0x, 07:2x, ~23:4x, 09:xx."""
    for stamp in ("09:0x", "07:2x", "23:xx"):
        p = lw.parse_ledger(f"## {stamp} ET — Claude (crew lane): something\n")
        assert p.headings[0].time == stamp
        assert p.headings[0].parsed is True


def test_ascii_hyphen_separator_is_not_second_class() -> None:
    """Measured: 4,600 headings use ' - ', only 2,014 use an em dash."""
    p = lw.parse_ledger("## 19:38 ET - Codex\n")
    assert p.headings[0].author == "Codex"
    assert p.headings[0].parsed is True


# ----------------------------------------------------------- newest-first

def test_prepended_entry_is_detected() -> None:
    """The ledger is newest-first. An offset cursor would miss every new entry."""
    old = "# Day\n\n## 07:00 ET — Codex: first\n\nbody\n"
    new = "# Day\n\n## 09:00 ET — Claude: SECOND\n\nbody2\n\n## 07:00 ET — Codex: first\n\nbody\n"
    a = {s for s in _sigs(old)}
    b = {s for s in _sigs(new)}
    added = b - a
    assert any("SECOND" in s for s in added), "prepended entry must appear as an addition"


def _sigs(text: str) -> list[str]:
    p = lw.parse_ledger(text)
    return [f"heading|x|{h.line}|{'P' if h.parsed else 'U'}|{h.raw}"
            for h in p.headings if h.depth in (2, 3)]


# ----------------------------------------------------------- ballot integrity

BALLOT = """# Ballot

## Votes

### Codex (crew)

Q1: **a** — because.
Q2: **b** — because.

### Claude Consultant

*(append your three lines here)*

### Gemini Consultant

I have thoughts but no answer here.

### Tally — Claude (crew), after all four are in

*(left empty until the votes are cast)*
"""


def test_voter_name_survives_intact() -> None:
    p = lw.parse_ledger(BALLOT)
    names = [v.voter for v in p.votes]
    assert "Codex (crew)" in names, "structural characters must not be scrubbed from a seat name"


def test_tally_slot_is_not_a_voter() -> None:
    """Counting the tally heading as a voter inflates the denominator and the tie math."""
    p = lw.parse_ledger(BALLOT)
    assert all(not v.voter.lower().startswith("tally") for v in p.votes)
    assert len(p.votes) == 3


def test_slot_state_is_four_way_not_boolean() -> None:
    """Ambiguity is reported as ambiguity, never resolved into filled or empty."""
    p = lw.parse_ledger(BALLOT)
    state = {v.voter: v.state for v in p.votes}
    assert state["Codex (crew)"] == "filled"
    assert state["Claude Consultant"] == "placeholder"
    assert state["Gemini Consultant"] == "unparseable", "prose in a slot is neither a vote nor empty"


def test_answers_are_kept_verbatim() -> None:
    """Never normalize a voter's mark away — a deviation must stay visible."""
    p = lw.parse_ledger(BALLOT)
    codex = next(v for v in p.votes if v.voter == "Codex (crew)")
    assert codex.answers["Q1"] == "**a**"


def test_abstention_is_distinct_from_a_vote() -> None:
    p = lw.parse_ledger("## Votes\n\n### Tower\n\nQ1: abstain — not my seat.\n")
    slot = p.votes[0]
    assert slot.abstain is True


# ----------------------------------------------------------- the wall

def test_wall_refuses_symlink_into_studio(tmp_path: Path) -> None:
    """TW29-WALL-35. A substring denylist on an unresolved path is not a wall."""
    link = tmp_path / "innocent-name"
    link.symlink_to(Path.home() / "frontend-studio")
    with pytest.raises(PermissionError):
        lw.guard_path(link)


def test_wall_refuses_paths_outside_the_allowed_roots() -> None:
    with pytest.raises(PermissionError):
        lw.guard_path(Path("/etc/passwd"))


def test_wall_allows_the_real_ledger_roots() -> None:
    assert lw.guard_path(lw.TRUNK / lw.LEDGER_REL)


# ----------------------------------------------------------- conflicts & divergence

def _snap(files: dict[str, dict]) -> dict:
    return {"day": "2026-08-19", "days": ["2026-08-19"], "files": files,
            "roots": [{"label": "trunk", "path": "/t"}, {"label": "wt:DG-021", "path": "/w"}],
            "census": {"trees": 2, "stat": 2, "hashed": 2, "refused": 0}}


def test_one_voter_two_answers_is_reported_not_resolved() -> None:
    """Measured live: Codex Consultant answered Q3 'b' in the trunk and 'c' in DG-021."""
    snap = _snap({
        "/t/a.md": {"label": "trunk", "name": "2026-08-19.md", "sha": "1", "evidence": False,
                    "_votes": [{"voter": "Codex Consultant", "answers": {"Q3": "**b**"},
                                "abstain": False, "source": "2026-08-19.md:231", "shape": "slot"}]},
        "/w/b.md": {"label": "wt:DG-021", "name": "vote.md", "sha": "2", "evidence": True,
                    "_votes": [{"voter": "Codex Consultant", "answers": {"Q3": "**c**"},
                                "abstain": False, "source": "vote.md", "shape": "artifact"}]},
    })
    conflicts = lw.vote_conflicts(snap)
    assert len(conflicts) == 1
    assert "Q3" in conflicts[0]
    assert "'b'" in conflicts[0] and "'c'" in conflicts[0], "both answers quoted; neither chosen"


def test_worktree_only_evidence_is_flagged_but_trunk_only_is_not() -> None:
    """Trunk-only is a worktree being behind — normal. Worktree-only is invisible to the channel."""
    snap = _snap({
        "/t/x.md": {"label": "trunk", "name": "trunk_only.md", "sha": "1", "evidence": True, "_votes": []},
        "/w/y.md": {"label": "wt:DG-021", "name": "wt_only.md", "sha": "2", "evidence": True, "_votes": []},
    })
    names = [n for n, _have, _miss in lw.evidence_gaps(snap)]
    assert names == ["wt_only.md"]


def test_same_day_file_differing_across_trees_is_divergence() -> None:
    """Measured live: 2026-08-18.md is 800d1389 in the trunk, f4a3b671 in all worktrees."""
    snap = _snap({
        "/t/d.md": {"label": "trunk", "name": "2026-08-18.md", "sha": "800d", "evidence": False, "_votes": []},
        "/w/d.md": {"label": "wt:DG-021", "name": "2026-08-18.md", "sha": "f4a3", "evidence": False, "_votes": []},
    })
    assert lw.divergence(snap), "identical filename, different content, must be reported loudly"


# ----------------------------------------------------------- cursor safety

def test_wait_never_advances_the_cursor(monkeypatch, tmp_path: Path) -> None:
    """An agent turn can die between advancing and delivering. Off-wire there is no
    re-notification, so an advancing wait consumes the delta permanently."""
    monkeypatch.setattr(lw, "CURSOR_DIR", tmp_path / "cursors")
    monkeypatch.setattr(lw, "INBOX_DIR", tmp_path / "inbox")
    src = Path("scripts/ledger_watch.py").read_text()
    fn = src.split("def cmd_wait(")[1].split("def cmd_broadcast(")[0]
    assert "save_cursor" not in fn.split("deadline = time.monotonic()")[1], (
        "cmd_wait must not save a cursor after its baseline; only `since` may commit"
    )


def test_cursor_write_is_atomic_and_per_reader(monkeypatch, tmp_path: Path) -> None:
    """One writer per file. A shared document loses updates and can advance another
    reader past content it never saw — under-reporting, the one unacceptable failure."""
    monkeypatch.setattr(lw, "CURSOR_DIR", tmp_path)
    snap = _snap({"/t/a.md": {"label": "trunk", "name": "a.md", "sha": "1", "sigs": ["x"],
                              "blocks": [], "evidence": False, "_votes": []}})
    lw.save_cursor("Claude Consultant", snap)
    lw.save_cursor("Gemini Consultant", snap)
    files = sorted(p.name for p in tmp_path.glob("*.json"))
    assert files == ["Claude_Consultant.json", "Gemini_Consultant.json"]
    assert not list(tmp_path.glob("*.tmp")), "temp file must be renamed, never left behind"
    assert json.loads((tmp_path / "Claude_Consultant.json").read_text())["reader"] == "Claude Consultant"


def test_cold_start_is_disclosed_never_hidden() -> None:
    snap = _snap({})
    delta = lw.compute_delta({}, snap)
    assert delta["cold_start"] is True
    assert "COLD START" in lw.render_delta(delta, snap, "someone")


def test_corrupt_cursor_degrades_to_cold_start_not_to_silence() -> None:
    snap = _snap({})
    assert lw.compute_delta({"_corrupt": True}, snap)["cold_start"] is True


def test_quiet_report_proves_it_looked() -> None:
    """A rename that empties the glob must never be indistinguishable from a quiet day."""
    snap = _snap({})
    out = lw.render_delta(lw.compute_delta({"files": {}, "day": "2026-08-19"}, snap), snap, "r")
    assert "census" in out and "trees walked" in out


# ----------------------------------------------------------- line-shift immunity
# Measured 2026-08-19, live: appending one vote shifted every line below it, and
# because the line number was part of the signature, four untouched entries reported
# as REMOVED and the file was falsely flagged as an in-place REWRITE. In a
# newest-first ledger every single post shifts everything beneath it, so this would
# have fired on every legitimate append and destroyed the report's credibility.

def _file_record(text: str, name: str = "2026-08-19.md") -> dict:
    parsed = lw.parse_ledger(text)
    sigs, siglines = [], {}
    rel = f"trunk:{name}"
    for h in parsed.headings:
        if h.depth in (2, 3):
            sig = f"heading|{rel}|{'P' if h.parsed else 'U'}|{h.raw}"
            sigs.append(sig)
            siglines[sig] = h.line
    for v in parsed.votes:
        ans = " ".join(f"{q}={a}" for q, a in sorted(v.answers.items()))
        sig = f"vote|{rel}|{v.voter}|{v.state}|{ans}"
        sigs.append(sig)
        siglines[sig] = v.line
    return {"label": "trunk", "name": name, "sha": hashlib.sha256(text.encode()).hexdigest(),
            "sigs": sigs, "blocks": lw.block_hashes(text), "evidence": False,
            "_votes": [], "_siglines": siglines, "_detail": {"parsed": parsed}}


OLD = "# Day\n\n## 07:00 ET — Codex: first entry\n\nbody\n\n## 06:00 ET — Tower: older entry\n\nbody\n"
NEW = "# Day\n\n## 09:00 ET — Claude: brand new\n\nbody\n\n" + OLD.split("\n", 2)[2]


def test_prepending_does_not_report_untouched_entries_as_removed() -> None:
    cur = {"files": {"/t/a.md": {"sha": "old", "sigs": _file_record(OLD)["sigs"],
                                 "blocks": lw.block_hashes(OLD)}}, "day": "2026-08-19",
           "trees": ["trunk"]}
    snap = {"day": "2026-08-19", "days": ["2026-08-19"], "roots": [{"label": "trunk", "path": "/t"}],
            "census": {"trees": 1, "stat": 1, "hashed": 1, "refused": 0},
            "files": {"/t/a.md": _file_record(NEW)}}
    d = lw.compute_delta(cur, snap)
    assert d["removed"] == [], f"a pure prepend removed nothing, but reported: {d['removed']}"
    assert d["rewrites"] == [], "a prepend is append-only; it must not be flagged as a REWRITE"
    assert any("brand new" in s for _l, s in d["added"]), "the new entry must be reported"


def test_line_numbers_are_reported_but_are_not_identity() -> None:
    """The line must still reach the report — blockers are quoted with file and line —
    while never taking part in deciding whether something is new."""
    rec = _file_record(NEW)
    sig = next(s for s in rec["sigs"] if "brand new" in s)
    assert not any(part.isdigit() for part in sig.split("|")), "no line number inside the signature"
    assert rec["_siglines"][sig] == 3, "line still available for citation"
    assert ":3" in lw.sig_render("trunk", sig, rec["_siglines"][sig])


def test_cursor_from_an_older_grammar_is_a_cold_start_not_a_phantom_delta() -> None:
    """Changing the signature format must not manufacture a delta out of nothing."""
    snap = _snap({})
    stale = {"schema": lw.SCHEMA - 1, "files": {}, "day": "2026-08-19"}
    assert lw.compute_delta(stale, snap)["cold_start"] is True


def test_widening_the_window_is_disclosed_not_reported_as_new_content() -> None:
    """Measured live: a cursor saved at window 1d, read by a 3d watcher, reported ~39
    historical entries as fresh. Days the checkpoint never covered are existing
    content — disclosed once, and they must not wake a reader."""
    snap = _snap({"/t/old.md": {"label": "trunk", "name": "2026-08-17.md", "day": "2026-08-17",
                                "sha": "x", "sigs": ["heading|trunk:2026-08-17.md|P|ancient"],
                                "blocks": [], "evidence": False, "_votes": [], "_siglines": {}}})
    cursor = {"schema": lw.SCHEMA, "day": "2026-08-19", "days": ["2026-08-19"],
              "files": {}, "trees": ["trunk", "wt:DG-021"]}
    d = lw.compute_delta(cursor, snap)
    assert d["widened"] == {"2026-08-17": 1}
    assert d["added"] == [] and d["new_files"] == []
    assert lw.has_change(d) is False, "widening the window must not wake a reader"
    assert "SCOPE WIDENED" in lw.render_delta(d, snap, "r")


# ----------------------------------------------------------- retraction
# Measured 2026-08-19: a ballot artifact was written under the wrong voter name, the
# authoring lane marked it SUPERSEDED, and the watcher went on presenting it as a live
# vote — the same class of error the retraction existed to correct.

SUPERSEDED_ARTIFACT = """# SUPERSEDED — misattributed pre-channel-change vote

This artifact was authored by **Codex (crew)**. It was incorrectly labeled
`Codex Consultant`; it is **not** the outside Codex Consultant's ballot and must not be counted.

Voter: Codex crew — originally mislabeled; superseded by the shared-ledger slot

Q3: **c** — Given Q2(a), both tickets should wait.
"""


def test_superseded_artifact_is_reported_but_not_counted(tmp_path: Path) -> None:
    f = tmp_path / "vote.md"
    f.write_text(SUPERSEDED_ARTIFACT)
    votes = lw.extract_votes(f, SUPERSEDED_ARTIFACT, None)
    assert votes, "the artifact must still be REPORTED, never silently dropped"
    assert votes[0]["superseded"] is True
    assert votes[0]["voter"] == "Codex crew", "explanatory clause is not part of the voter's name"


def test_a_superseded_vote_cannot_create_a_conflict() -> None:
    """A retracted vote must not resurrect the conflict it was retracted to settle."""
    snap = _snap({
        "/t/a.md": {"label": "trunk", "name": "2026-08-19.md", "sha": "1", "evidence": False,
                    "_votes": [{"voter": "Codex Consultant", "answers": {"Q3": "**b**"},
                                "abstain": False, "source": "x:1", "shape": "slot"}]},
        "/w/b.md": {"label": "wt:DG-021", "name": "vote.md", "sha": "2", "evidence": True,
                    "_votes": [{"voter": "Codex Consultant", "answers": {"Q3": "**c**"},
                                "abstain": False, "source": "vote.md", "shape": "artifact",
                                "superseded": True}]},
    })
    assert lw.vote_conflicts(snap) == []


def test_rewrite_reports_one_edit_site_not_the_shifted_remainder() -> None:
    """An in-place insertion shifts every block after it; only the first locates the edit."""
    # Insert near the top AND drop the last line, so the line count — and therefore the
    # block count — is unchanged and every block below the edit genuinely shifts. That is
    # the shape that previously reported six separate "edit sites" for one edit.
    lines = [f"line {i}" for i in range(200)]
    old = "\n".join(lines)
    new = "\n".join(lines[:50] + ["INSERTED"] + lines[50:-1])
    assert len(old.splitlines()) == len(new.splitlines())
    cur = {"schema": lw.SCHEMA, "day": "2026-08-19", "days": ["2026-08-19"], "trees": ["trunk"],
           "files": {"/t/a.md": {"sha": "old", "sigs": [], "blocks": lw.block_hashes(old)}}}
    snap = _snap({"/t/a.md": {"label": "trunk", "name": "a.md", "day": "2026-08-19", "sha": "new",
                              "sigs": [], "blocks": lw.block_hashes(new), "evidence": False,
                              "_votes": [], "_siglines": {}}})
    d = lw.compute_delta(cur, snap)
    assert len(d["rewrites"]) == 1
    assert len(d["rewrites"][0][1]) == 1, "one edit site, not every shifted block"
