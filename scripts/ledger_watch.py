#!/usr/bin/env python3
"""Ledger Watch — deterministic detection engine for the Dynasty Genius ledger channel.

David ruled 2026-08-19: *"we now use the ledger to communicate with tmux panes and
parallel sessions."* Three consultants run outside tmux, unreachable on the cockpit
wire; the repo is their only channel. A channel nobody reads is a drop box.

This is the detection layer. It observes and counts. It never judges, never votes,
never writes a ledger entry, and never touches a pane without --send.

DESIGN RULES, each one paid for by a measured failure:

  1. THE PARSE NEVER GATES THE REPORT. Measured 2026-08-19 against the real corpus:
     a strict "## HH:MM ET — Author: headline" regex matches 794 of 5,601 headings
     (14.2%). The other 85.8% — session closeouts, blocker notes, author-first
     headings, ASCII-hyphen separators, "Time Unknown" — would have been invisible.
     So EVERY heading is emitted, carrying its raw text; parsing is enrichment
     recorded as parsed=true|false, never a filter.

  2. NEWEST-FIRST, SO NO OFFSET CURSORS. Entries are prepended. Any byte or line
     offset cursor misses every new entry. Detection is a SIGNATURE SET difference.

  3. FOUR TREES, ROLLING WINDOW. The trunk plus every ~/dg-wt/*/ worktree. Measured:
     2026-08-18.md is 800d1389 in the trunk and f4a3b671 in all three worktrees —
     523 diff lines of real divergence on a file a "today only" rule never opens.
     A window also survives midnight, when the conversation is still in yesterday.

  4. wait NEVER ADVANCES A CURSOR. An agent turn can die between "cursor advanced"
     and "delta reached the reader". Off-wire there is no re-notification, so the
     delta would be consumed permanently. wait is strictly peek + a durable inbox
     drop; only an explicit `since` commits.

  5. ONE WRITER PER CURSOR FILE. A shared state document loses updates: a writer
     rewriting from a fresher view advances another reader's cursor past content it
     never saw. That converts over-reporting (safe) into under-reporting (not).

  6. THE WALL IS AN ALLOWLIST AFTER realpath, NEVER A SUBSTRING DENYLIST.
     TW29-WALL-35 (David, 2026-07-29): Studio is never read. A substring check on an
     unresolved path is defeated by a symlink named anything at all.

  7. A QUIET REPORT MUST PROVE IT LOOKED. Every run prints its census — trees walked,
     files stat'ed, files hashed. An empty glob from a rename must never be
     indistinguishable from a genuinely quiet channel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

HOME = Path.home()
TRUNK = HOME / "dynasty-genius-product"
WORKTREE_PARENT = HOME / "dg-wt"
LEDGER_REL = Path("docs/agent-ledger")

BASE = HOME / ".claude" / "dg-ledger-watch"
CURSOR_DIR = BASE / "cursors"      # one file per reader; exactly one writer each
INBOX_DIR = BASE / "inbox"         # durable drops, so a killed process loses nothing

DEFAULT_WINDOW = 7
BLOCK_LINES = 20                   # granularity for in-place-rewrite localisation
SCHEMA = 3   # bumped when signature identity dropped line numbers

SEATS = (
    "David", "Judge", "Tower", "Studio", "Claude Consultant", "Codex Consultant",
    "Gemini Consultant", "Claude", "Codex", "Gemini", "Ledger Watch",
)

# ------------------------------------------------------------------ grammar
# Enrichment only. Nothing below may cause a heading to go unreported.

HEADING_RE = re.compile(r"^(?P<hashes>\#{1,6})\s+(?P<text>.+?)\s*$")
TIME_RE = re.compile(r"^~?(?P<time>\d{1,2}[:.][\dxX]{2}[a-zA-Z]?)\s*(?P<tz>ET|PT|CT|MT|UTC|EDT|EST)?\b")
# Separator is ASCII hyphen far more often than em dash: 4,600 vs 2,014 (measured).
SEP_RE = re.compile(r"\s+[—–-]+\s+")
VOTES_SECTION_RE = re.compile(r"^\#{1,3}\s*(?:\N{BALLOT BOX WITH BALLOT}\s*)?Votes\b", re.I)
TALLY_SLOT_RE = re.compile(r"^(tally|result|outcome|summary)\b", re.I)
VOTE_LINE_RE = re.compile(
    r"^\s*(?P<q>Q\d+)\s*[:.]\s*(?P<raw>\*{0,2}[`_]?[A-Za-z]+[`_]?\*{0,2})\s*(?:[-–—]+\s*(?P<why>.+?))?\s*$"
)
ABSTAIN_RE = re.compile(r"\b(abstain|abstention|no vote|recuse)\b", re.I)
# A bare "Q4:" with no answer is the ballot template, not content. Reporting it as
# "grammar unmatched" tells a reader to go look at something that is not there, and
# blurs the line between a slot awaiting a vote and one holding an unreadable answer.
PLACEHOLDER_RE = re.compile(
    r"^\s*(?:[*_]?\(.*(?:append|left empty|your .*line|tbd|pending).*\)[*_]?|Q\d+\s*[:.]\s*)\s*$",
    re.I)
# An artifact can be retracted by its author. Measured 2026-08-19: a vote artifact was
# mislabeled, then marked SUPERSEDED by the lane that wrote it. Continuing to count a
# retracted vote is the same class of error the retraction exists to correct, so a
# supersede marker is honoured — the artifact is still REPORTED, never silently dropped,
# but its answers stop counting as a live vote.
SUPERSEDED_RE = re.compile(
    r"(^#{1,3}\s*SUPERSEDED\b|\bSUPERSEDED\b.*\bvote\b|\bmust not be counted\b|\\bsuperseded by\\b|\\bRETRACTED\\b)",
    re.I | re.M)
VOTER_FIELD_RE = re.compile(r"^\s*[*_]{0,2}Voter[*_]{0,2}\s*[:：]\s*[*_`]{0,2}(?P<voter>[^*_`\n]+)", re.I)
THREAD_RE = re.compile(r"\[w\#([A-Za-z0-9._-]+)\]")
ATTENTION_RE = re.compile(
    r"(BLOCKED|NOT CLEAR|\bSTOP\b|PLEASE REPLY|David's (?:call|ruling|word|decision)|"
    r"\bescalat\w+|\bawaiting\b|⛔|🚨)", re.I,
)
DATED_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


# ------------------------------------------------------------------ the wall

def allowed_roots() -> list[Path]:
    roots = []
    for r in (TRUNK, WORKTREE_PARENT):
        try:
            roots.append(r.resolve(strict=True))
        except OSError:
            pass
    return roots


def guard_path(p: Path) -> Path:
    """TW29-WALL-35. Resolve FIRST, then require the result inside an allowed root.

    An allowlist after resolution is a wall. A substring denylist on an unresolved
    path is a suggestion — a symlink named anything walks straight through it.
    """
    try:
        real = p.resolve(strict=False)
    except OSError as exc:
        raise PermissionError(f"unresolvable path {p}: {exc}") from exc
    for root in allowed_roots():
        try:
            real.relative_to(root)
            return real
        except ValueError:
            continue
    raise PermissionError(
        f"TW29-WALL-35: {p} resolves to {real}, outside every allowed ledger root. Refused."
    )


# ------------------------------------------------------------------ model

@dataclass
class Heading:
    raw: str
    depth: int
    line: int
    parsed: bool = False
    time: str = ""
    author: str = ""
    headline: str = ""
    threads: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)


@dataclass
class VoteSlot:
    voter: str
    state: str                      # empty | placeholder | filled | unparseable
    line: int = 0
    end_line: int = 0
    lines: list[str] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)       # Q1 -> raw, verbatim
    abstain: bool = False


@dataclass
class Parsed:
    headings: list[Heading] = field(default_factory=list)
    votes: list[VoteSlot] = field(default_factory=list)
    attention: list[tuple[int, str]] = field(default_factory=list)

    @property
    def entries(self) -> list[Heading]:
        return [h for h in self.headings if h.depth in (2, 3)]

    @property
    def unparsed(self) -> list[Heading]:
        return [h for h in self.headings if h.depth in (2, 3) and not h.parsed]


def _mentions(text: str) -> list[str]:
    return sorted({s for s in SEATS if re.search(rf"\b{re.escape(s)}\b", text)})


def _enrich(h: Heading) -> Heading:
    """Best-effort structure. Failure is recorded, never fatal, never a filter."""
    t = h.raw
    h.threads = THREAD_RE.findall(t)
    h.mentions = _mentions(t)
    tm = TIME_RE.match(t)
    if tm:
        h.time = tm.group("time")
        rest = t[tm.end():]
        rest = SEP_RE.sub(" ", rest, count=1).strip() if SEP_RE.match(rest) else rest.strip()
    else:
        rest = t
    # author: up to the first ':' or ' — ', whichever comes first; both shapes are real
    m = re.match(r"^(?P<author>.+?)\s*(?::\s*|\s+[—–-]+\s+)(?P<headline>.+)$", rest)
    if m:
        h.author, h.headline, h.parsed = m.group("author").strip(), m.group("headline").strip(), True
    elif rest:
        h.author, h.headline = rest.strip(), ""
        h.parsed = bool(h.time)      # "## 19:38 ET - Codex" is a real, headline-less entry
    return h


def parse_ledger(text: str) -> Parsed:
    out = Parsed()
    in_votes = False
    votes_depth = 0
    current: VoteSlot | None = None

    def close(end_line: int) -> None:
        nonlocal current
        if current is not None:
            current.end_line = end_line
            body = [ln for ln in current.lines if ln.strip()]
            if not body:
                current.state = "empty"
            elif all(PLACEHOLDER_RE.match(ln) for ln in body):
                current.state = "placeholder"
            elif current.answers or current.abstain:
                current.state = "filled"
            else:
                current.state = "unparseable"   # content present, grammar unmatched
            out.votes.append(current)
            current = None

    lines = text.splitlines()
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        hm = HEADING_RE.match(line)

        if hm:
            depth, text_ = len(hm.group("hashes")), hm.group("text").strip()
            if in_votes and current is not None and depth <= votes_depth + 1:
                close(i - 1)
            if VOTES_SECTION_RE.match(line):
                in_votes, votes_depth = True, depth
                out.headings.append(_enrich(Heading(raw=text_, depth=depth, line=i)))
                continue
            if in_votes and depth <= votes_depth:
                in_votes = False
            if in_votes and depth == votes_depth + 1:
                voter = text_.strip("*_` ").strip()
                if TALLY_SLOT_RE.match(voter):      # a tally is not a voter
                    out.headings.append(_enrich(Heading(raw=text_, depth=depth, line=i)))
                    continue
                current = VoteSlot(voter=voter, state="empty", line=i)
                continue
            out.headings.append(_enrich(Heading(raw=text_, depth=depth, line=i)))
            continue

        if current is not None and line.strip():
            current.lines.append(line.strip())
            vm = VOTE_LINE_RE.match(line)
            if vm:
                current.answers[vm.group("q").upper()] = vm.group("raw").strip()
            if ABSTAIN_RE.search(line):
                current.abstain = True

        if ATTENTION_RE.search(line):
            out.attention.append((i, line.strip()))

    close(len(lines))
    return out


def extract_votes(path: Path, text: str, parsed: Parsed | None) -> list[dict]:
    """Every vote a file carries, in either shape.

    Shape A: a slot under a ballot's ##Votes section.
    Shape B: a standalone evidence artifact with a "Voter:" field — which is exactly
    how a vote lands in a worktree the trunk cannot see. Both must be read.
    """
    found: list[dict] = []
    if parsed is not None:
        for v in parsed.votes:
            if v.state == "filled":
                found.append({"voter": v.voter, "answers": dict(v.answers), "abstain": v.abstain,
                              "source": f"{path.name}:{v.line}", "shape": "slot"})
        if found:
            return found
    voter = None
    for line in text.splitlines():
        m = VOTER_FIELD_RE.match(line)
        if m:
            voter = m.group("voter").strip()
            # a Voter: field may carry an explanatory clause; the name is the head of it
            voter = re.split(r"\s+[—–-]{1,2}\s+|\s*[;,]\s*", voter)[0].strip()
            break
    if voter is None:
        return found
    superseded = bool(SUPERSEDED_RE.search(text))
    answers: dict[str, str] = {}
    for n, line in enumerate(text.splitlines(), start=1):
        vm = VOTE_LINE_RE.match(line)
        if vm:
            answers[vm.group("q").upper()] = vm.group("raw").strip()
    if answers:
        found.append({"voter": voter, "answers": answers, "abstain": bool(ABSTAIN_RE.search(text)),
                      "source": path.name, "shape": "artifact", "superseded": superseded})
    return found


# ------------------------------------------------------------------ discovery

def ledger_roots() -> list[tuple[str, Path]]:
    """Enumerate every tree LIVE. New tickets appear without anyone announcing them."""
    roots: list[tuple[str, Path]] = []
    trunk = TRUNK / LEDGER_REL
    if trunk.is_dir():
        roots.append(("trunk", guard_path(trunk)))
    if WORKTREE_PARENT.is_dir():
        for wt in sorted(WORKTREE_PARENT.iterdir()):
            d = wt / LEDGER_REL
            if wt.is_dir() and d.is_dir():
                try:
                    roots.append((f"wt:{wt.name}", guard_path(d)))
                except PermissionError as exc:
                    print(f"REFUSED: {exc}", file=sys.stderr)
    return roots


def window_days(day: str, window: int) -> list[str]:
    d0 = date.fromisoformat(day)
    return [(d0 - timedelta(days=n)).isoformat() for n in range(window)]


def watched_files(root: Path, days: list[str]) -> list[Path]:
    files: list[Path] = []
    for d in days:
        f = root / f"{d}.md"
        if f.exists():
            files.append(f)
        ev = root / "evidence" / d
        if ev.is_dir():
            files.extend(sorted(p for p in ev.iterdir() if p.is_file() and not p.name.startswith(".")))
    return files


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def block_hashes(text: str) -> list[str]:
    """Coarse per-region hashes so an in-place REWRITE can be localised cheaply."""
    lines = text.splitlines()
    return [
        hashlib.sha256("\n".join(lines[i:i + BLOCK_LINES]).encode()).hexdigest()[:10]
        for i in range(0, max(len(lines), 1), BLOCK_LINES)
    ]


# ------------------------------------------------------------------ scan

def signatures(label: str, path: Path, is_evidence: bool) -> tuple[list[str], dict]:
    rel = f"{label}:{path.name}"
    detail: dict = {"path": str(path), "label": label, "votes": [], "parsed": None, "blocks": []}
    sigs: list[str] = []

    if is_evidence:
        sigs.append(f"evidence|{rel}")
        if path.suffix == ".md":
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                detail["votes"] = extract_votes(path, text, None)
                for v in detail["votes"]:
                    ans = " ".join(f"{q}={a}" for q, a in sorted(v["answers"].items()))
                    state = "superseded" if v.get("superseded") else "filled"
                    sigs.append(f"vote|{rel}|{v['voter']}|{state}|{ans}|{v['source']}")
            except OSError:
                pass
        return sigs, detail

    text = path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_ledger(text)
    detail["parsed"] = parsed
    detail["votes"] = extract_votes(path, text, parsed)
    detail["blocks"] = block_hashes(text)

    siglines: dict[str, int] = {}
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
    for ln, txt in parsed.attention:
        sig = f"attn|{rel}|{txt}"
        sigs.append(sig)
        siglines[sig] = ln
    detail["siglines"] = siglines
    return sigs, detail


def scan(day: str, window: int) -> dict:
    days = window_days(day, window)
    snap: dict = {"day": day, "days": days, "files": {}, "roots": [],
                  "census": {"trees": 0, "stat": 0, "hashed": 0, "refused": 0}}
    for label, root in ledger_roots():
        snap["roots"].append({"label": label, "path": str(root)})
        snap["census"]["trees"] += 1
        for path in watched_files(root, days):
            snap["census"]["stat"] += 1
            try:
                p = guard_path(path)
                is_ev = p.parent.name in days
                fday = p.parent.name if is_ev else p.stem
                sigs, detail = signatures(label, p, is_ev)
                st = p.stat()
                snap["census"]["hashed"] += 1
                snap["files"][str(p)] = {
                    "label": label, "name": p.name, "day": fday, "sha": sha256(p), "size": st.st_size,
                    "mtime": st.st_mtime, "sigs": sigs, "evidence": is_ev,
                    "blocks": detail["blocks"], "_detail": detail, "_votes": detail["votes"],
                    "_siglines": detail.get("siglines", {}),
                }
            except PermissionError as exc:
                snap["census"]["refused"] += 1
                print(f"REFUSED: {exc}", file=sys.stderr)
            except OSError as exc:
                print(f"UNREADABLE {path}: {exc}", file=sys.stderr)
    return snap


# ------------------------------------------------------------------ cursors

def cursor_file(reader: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", reader).strip("_") or "anon"
    return CURSOR_DIR / f"{safe}.json"


def load_cursor(reader: str) -> dict:
    p = cursor_file(reader)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"_corrupt": True}


def save_cursor(reader: str, snapshot: dict) -> None:
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA, "reader": reader,
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "day": snapshot["day"], "days": snapshot["days"],
        "trees": [r["label"] for r in snapshot["roots"]],
        "files": {p: {"sha": f["sha"], "sigs": f["sigs"], "blocks": f.get("blocks", []),
                          "day": f.get("day")}
                  for p, f in snapshot["files"].items()},
    }
    p = cursor_file(reader)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)   # atomic; one writer per reader, so no lost update


def drop_inbox(reader: str, body: str) -> Path:
    """Durable delivery. Notification to a process that may not exist is not delivery."""
    d = INBOX_DIR / (re.sub(r"[^A-Za-z0-9._-]+", "_", reader).strip("_") or "anon")
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')}.md"
    p.write_text(body + "\n", encoding="utf-8")
    return p


# ------------------------------------------------------------------ delta

def compute_delta(cursor: dict, snapshot: dict) -> dict:
    # A cursor written under a different signature grammar is not comparable. Saying so
    # is a cold start; silently diffing across grammars would invent deltas that never
    # happened and bury the real ones.
    cold = (not cursor or cursor.get("_corrupt") or "files" not in cursor
            or cursor.get("schema") != SCHEMA)
    prev = (cursor or {}).get("files", {})
    d = {"cold_start": bool(cold), "new_files": [], "added": [], "removed": [],
         "rewrites": [], "prose": [], "gone_files": [], "gone_trees": [], "widened": {}, "new_trees": {}}
    # Widening the window pulls in days the cursor never observed. Those files are not
    # new content and reporting them as new entries buries the real delta — measured
    # 2026-08-19, when a 1d cursor read against a 3d scan reported ~39 historical
    # entries as fresh. They are disclosed as newly-in-scope instead.
    prior_days = set((cursor or {}).get("days", []) or [])
    # A worktree appearing is a checkout of existing history, not new writing. Measured
    # 2026-08-19: DG-031 was created and the watcher reported ~40 historical entries as
    # fresh, burying the real delta. A new tree is disclosed once, like a widened window.
    prior_trees = set((cursor or {}).get("trees", []) or [])

    for path, cur in snapshot["files"].items():
        old = prev.get(path)
        if old is None:
            if prior_trees and cur["label"] not in prior_trees:
                d["new_trees"].setdefault(cur["label"], 0)
                d["new_trees"][cur["label"]] += 1
                continue
            if prior_days and cur.get("day") not in prior_days:
                d["widened"].setdefault(cur["day"], 0)
                d["widened"][cur["day"]] += 1
                continue
            d["new_files"].append(cur)
            if not cold:
                d["added"].extend((cur["label"], s) for s in cur["sigs"])
            continue
        if old.get("sha") == cur["sha"]:
            continue
        a, b = set(old.get("sigs", [])), set(cur["sigs"])
        d["added"].extend((cur["label"], s) for s in sorted(b - a))
        d["removed"].extend((cur["label"], s) for s in sorted(a - b))
        if b - a or a - b:
            continue        # structural delta already reported; the shift explains itself
        # Identical signature set, different bytes: something changed that the grammar
        # cannot see. Localise it by block so a human knows where to look.
        ob, nb = old.get("blocks", []), cur.get("blocks", [])
        changed = [i for i, (x, y) in enumerate(zip(ob, nb)) if x != y] if ob and nb else []
        if changed and len(ob) == len(nb):
            # Everything after an in-place insertion shifts, so only the FIRST divergent
            # block locates the edit; listing the shifted remainder as separate sites
            # overstates how much changed.
            d["rewrites"].append((cur, [changed[0] * BLOCK_LINES + 1]))
        else:
            d["prose"].append(cur)

    if not cold:
        for path in prev:
            if path not in snapshot["files"]:
                d["gone_files"].append(path)
        now_trees = {r["label"] for r in snapshot["roots"]}
        for t in cursor.get("trees", []):
            if t not in now_trees:
                d["gone_trees"].append(t)
    return d


def has_change(d: dict) -> bool:
    # "widened" is disclosure, never a change — it must not wake anyone.
    return bool(d["new_files"] or d["added"] or d["removed"] or d["rewrites"]
                or d["prose"] or d["gone_files"] or d["gone_trees"])


def divergence(snapshot: dict) -> list[tuple[str, list[tuple[str, str]]]]:
    """Same-named dated ledger file carrying different content across trees."""
    by: dict[str, list[tuple[str, str]]] = {}
    for f in snapshot["files"].values():
        if f["evidence"] or not DATED_FILE_RE.match(f["name"]):
            continue
        by.setdefault(f["name"], []).append((f["label"], f["sha"]))
    return [(n, sorted(v)) for n, v in sorted(by.items()) if len({s for _l, s in v}) > 1]


def evidence_gaps(snapshot: dict) -> list[tuple[str, list[str], list[str]]]:
    """Evidence artifacts a WORKTREE holds and the TRUNK does not.

    Only this direction is reported, and the asymmetry is deliberate. Trunk-only
    artifacts are normal — a worktree branched before they were written and is simply
    behind. The dangerous direction is the reverse: the trunk is the channel of record,
    so an artifact that exists only in a worktree is invisible to everyone reading the
    channel. Measured 2026-08-19: a Codex Consultant ballot vote sits in DG-021 alone.
    """
    by: dict[str, set[str]] = {}
    for f in snapshot["files"].values():
        if f["evidence"]:
            by.setdefault(f["name"], set()).add(f["label"])
    out = []
    for name, have in sorted(by.items()):
        if "trunk" not in have:
            out.append((name, sorted(have), ["trunk"]))
    return out


def vote_conflicts(snapshot: dict) -> list[str]:
    """One voter, one question, two answers. Reported — never resolved.

    Ledger Watch counts; it does not decide which of a voter's two answers is real.
    That belongs to the voter.
    """
    by: dict[str, dict[str, set[tuple[str, str]]]] = {}
    for f in snapshot["files"].values():
        for v in f.get("_votes", []):
            if v.get("superseded"):
                continue        # retracted by its author; counting it would re-create the error
            key = v["voter"].strip().lower()
            for q, a in v["answers"].items():
                norm = re.sub(r"[^a-z]", "", a.lower())
                by.setdefault(key, {}).setdefault(q, set()).add((norm, f"[{f['label']}] {v['source']}"))
    out = []
    for voter in sorted(by):
        for q in sorted(by[voter]):
            vals = by[voter][q]
            if len({c for c, _ in vals}) > 1:
                out.append(f"{voter} — {q} answered two ways: "
                           + "; ".join(f"{c!r} in {s}" for c, s in sorted(vals)))
    return out


# ------------------------------------------------------------------ render

def census_line(snapshot: dict) -> str:
    c = snapshot["census"]
    return (f"  [census] {c['trees']} trees walked · {c['stat']} files stat'ed · "
            f"{c['hashed']} hashed · {c['refused']} refused · window {len(snapshot['days'])}d "
            f"({snapshot['days'][-1]}..{snapshot['days'][0]})")


def sig_render(label: str, sig: str, line: int | None = None) -> str | None:
    kind, _, rest = sig.partition("|")
    p = rest.split("|")
    at = f":{line}" if line else ""
    if kind == "heading" and len(p) >= 3:
        flag = "" if p[1] == "P" else "  ⟨unparsed⟩"
        return f"  ENTRY     [{label}] {p[0].split(':',1)[-1]}{at}  {p[2][:96]}{flag}"
    if kind == "vote" and len(p) >= 4:
        if p[2] in ("empty", "placeholder"):
            return None
        if p[2] == "superseded":
            return f"  RETRACTED [{label}] {p[1]} → {p[3]} — marked superseded; NOT counted"
        tag = "VOTE" if p[2] == "filled" else "VOTE?"
        return f"  {tag:<9} [{label}] {p[1]} → {p[3] or '(no parseable answer)'}   @{p[0].split(':',1)[-1]}{at}"
    if kind == "evidence":
        return f"  EVIDENCE  [{label}] {p[0].split(':',1)[-1] if p else rest}"
    if kind == "attn" and len(p) >= 2:
        return f"  ATTENTION [{label}]{at} {p[1][:100]}"
    return f"  CHANGE    [{label}] {sig[:140]}"


def render_alerts(snapshot: dict, indent: str = "  ") -> list[str]:
    out: list[str] = []
    conf = vote_conflicts(snapshot)
    if conf:
        out += ["", f"{indent}🚨 VOTE CONFLICT — one voter, two answers (reported, never resolved):"]
        out += [f"{indent}    {c}" for c in conf]
    div = divergence(snapshot)
    if div:
        out += ["", f"{indent}🚨 LEDGER DIVERGENCE — same day, different content across trees:"]
        for name, pairs in div:
            for lbl, sha in pairs:
                out.append(f"{indent}    {name}  [{lbl:<12}] {sha[:12]}")
    gaps = evidence_gaps(snapshot)
    if gaps:
        out += ["", f"{indent}⚠ WORKTREE-ONLY EVIDENCE — the trunk channel cannot see these:"]
        for name, have, _missing in gaps:
            out.append(f"{indent}    {name}  (only in {', '.join(have)})")
    return out


def render_delta(delta: dict, snapshot: dict, reader: str) -> str:
    stamp = datetime.now().astimezone().strftime("%H:%M:%S")
    L: list[str] = []
    if delta["cold_start"]:
        L.append(f"[{stamp}] COLD START for '{reader}' — no usable checkpoint. "
                 f"What follows is CURRENT STATE, not a delta.")
        L.append("")
        L.append(render_status(snapshot))
        return "\n".join(L)

    widened = ""
    if delta.get("new_trees"):
        t = ", ".join(f"{k} ({n} files)" for k, n in sorted(delta["new_trees"].items()))
        widened += (f"\n  ⓘ NEW TREE now watched: {t}. Existing history checked out, "
                    f"not new writing — its future changes WILL be reported.")
    if delta.get("widened"):
        days = ", ".join(f"{d} ({n} files)" for d, n in sorted(delta["widened"].items()))
        widened = (f"\n  ⓘ SCOPE WIDENED — days now watched that your checkpoint never covered: "
                   f"{days}. Existing content, not new.")
    if not has_change(delta):
        return f"[{stamp}] No change since {reader}'s checkpoint.{widened}\n{census_line(snapshot)}"

    L.append(f"[{stamp}] LEDGER MOVED — delta for '{reader}':")
    order = {"heading": 0, "vote": 1, "attn": 2, "evidence": 3}
    lookup: dict[str, int] = {}
    for f in snapshot["files"].values():
        lookup.update(f.get("_siglines", {}))
    for label, sig in sorted(delta["added"], key=lambda x: order.get(x[1].split("|")[0], 9)):
        r = sig_render(label, sig, lookup.get(sig))
        if r:
            L.append(r)
    for f in delta["new_files"]:
        if not f["evidence"]:
            L.append(f"  NEW FILE  [{f['label']}] {f['name']} appeared ({f['size']}B)")
    for label, sig in delta["removed"]:
        L.append(f"  ⚠ REMOVED [{label}] {sig[:150]}")
    for f, starts in delta["rewrites"]:
        L.append(f"  ⚠ REWRITE [{f['label']}] {f['name']} edited IN PLACE at or after ~line "
                 f"{starts[0]} — not append-only; everything below it shifted")
    for f in delta["prose"]:
        L.append(f"  ~ PROSE   [{f['label']}] {f['name']} changed below heading level "
                 f"(sha {f['sha'][:8]}) — no structural delta")
    for p in delta["gone_files"]:
        L.append(f"  ⚠ GONE    file disappeared: {p}")
    for t in delta["gone_trees"]:
        L.append(f"  ⚠ TREE GONE  {t} is no longer present")
    if widened:
        L.append(widened.strip("\n"))
    L += render_alerts(snapshot)
    L.append("")
    L.append(census_line(snapshot))
    return "\n".join(L)


def render_status(snapshot: dict) -> str:
    L = [f"LEDGER STATUS — {snapshot['day']}  (window {len(snapshot['days'])}d)"]
    for r in snapshot["roots"]:
        L.append(f"    {r['label']:<16} {r['path']}")

    for _path, f in sorted(snapshot["files"].items()):
        parsed: Parsed | None = f["_detail"].get("parsed")
        if parsed is None:
            continue
        L.append("")
        L.append(f"  {f['label']} · {f['name']}  ({f['size']}B, sha {f['sha'][:8]})")
        ents = parsed.entries
        if ents:
            up = len(parsed.unparsed)
            L.append(f"    headings: {len(ents)}  ({len(ents)-up} parsed, {up} raw-only) — newest first")
            for h in ents[:14]:
                who = h.author or "(no author parsed)"
                tag = f"  [w#{','.join(h.threads)}]" if h.threads else ""
                mark = "" if h.parsed else "  ⟨unparsed⟩"
                L.append(f"      :{h.line:<5} {h.time or '--:--':<8} {who[:34]:<34} {h.headline[:44]}{tag}{mark}")
            if len(ents) > 14:
                L.append(f"      … {len(ents)-14} more")
        if parsed.votes:
            filled = [v for v in parsed.votes if v.state == "filled"]
            L.append(f"    ballot: {len(filled)} of {len(parsed.votes)} slots filled")
            for v in parsed.votes:
                if v.state == "filled":
                    ans = " ".join(f"{q}:{a}" for q, a in sorted(v.answers.items()))
                    L.append(f"      ✓ {v.voter:<20} {ans}{'  ABSTAIN' if v.abstain else ''}  @:{v.line}")
                elif v.state == "unparseable":
                    L.append(f"      ? {v.voter:<20} CONTENT PRESENT, GRAMMAR UNMATCHED @:{v.line} — read it yourself")
                else:
                    L.append(f"      ◻ {v.voter:<20} AWAITING ({v.state}) @:{v.line}")
            tally: dict[str, dict[str, int]] = {}
            for v in filled:
                for q, a in v.answers.items():
                    n = re.sub(r"[^a-z]", "", a.lower())
                    tally.setdefault(q, {}).setdefault(n, 0)
                    tally[q][n] += 1
            if tally:
                L.append("    arithmetic of filled slots only — not a ruling, not a tally of record:")
                for q in sorted(tally):
                    L.append(f"      {q}: " + ", ".join(f"{c}={n}" for c, n in sorted(tally[q].items())))
        if parsed.attention:
            L.append(f"    attention lines ({len(parsed.attention)}):")
            for ln, txt in parsed.attention[:8]:
                L.append(f"      :{ln} {txt[:96]}")

    ev = [f for f in snapshot["files"].values() if f["evidence"]]
    if ev:
        L.append("")
        L.append(f"  evidence artifacts ({len(ev)}):")
        for f in sorted(ev, key=lambda x: (x["name"], x["label"])):
            votes = f.get("_votes") or []
            if any(x.get("superseded") for x in votes):
                v = "  ← SUPERSEDED VOTE, not counted"
            elif votes:
                v = "  ← CARRIES A VOTE"
            else:
                v = ""
            L.append(f"    [{f['label']:<12}] {f['name']}  ({f['size']}B){v}")

    alerts = render_alerts(snapshot)
    if alerts:
        L += alerts
    else:
        L += ["", "  ✓ no divergence, no evidence gap, no vote conflict"]
    L.append("")
    L.append(census_line(snapshot))
    return "\n".join(L)


# ------------------------------------------------------------------ commands
# exit codes: 0 change/ok · 1 no change · 2 timeout · 3 refused/error

def cmd_status(args) -> int:
    snap = scan(args.day, args.window)
    print(render_status(snap))
    return 0


def cmd_delta(args, advance: bool) -> int:
    snap = scan(args.day, args.window)
    delta = compute_delta(load_cursor(args.as_reader), snap)
    body = render_delta(delta, snap, args.as_reader)
    print(body)
    if advance:
        save_cursor(args.as_reader, snap)
    return 0 if (has_change(delta) or delta["cold_start"]) else 1


def cmd_wait(args) -> int:
    """Block until the ledger moves. NEVER advances the cursor — see design rule 4."""
    snap = scan(args.day, args.window)
    cursor = load_cursor(args.as_reader)
    if not cursor or "files" not in cursor:
        save_cursor(args.as_reader, snap)      # establish a baseline, disclosed
        cursor = load_cursor(args.as_reader)
        print(f"[wait] cold start for '{args.as_reader}' — baseline checkpointed. "
              f"Now watching for the NEXT change.\n{census_line(snap)}", flush=True)

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        time.sleep(args.interval)
        try:
            snap = scan(args.day, args.window)
        except PermissionError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 3
        delta = compute_delta(cursor, snap)
        if has_change(delta):
            body = render_delta(delta, snap, args.as_reader)
            print(body, flush=True)
            drop = drop_inbox(args.as_reader, body)
            print(f"\n[wait] durable copy: {drop}", flush=True)
            print("[wait] cursor NOT advanced — run "
                  f"`scripts/ledger_watch.py since --as {args.as_reader}` to acknowledge.", flush=True)
            return 0
    print(f"[wait] TIMEOUT after {args.timeout}s — channel quiet for '{args.as_reader}'.\n"
          f"{census_line(snap)}", flush=True)
    return 2


def _verify_in_pane(pane: str, needle: str) -> bool:
    """Read the pane back and confirm the text is actually there.

    A send that returned 0 is not a send that arrived. Delivery is only claimed on
    evidence read back out of the target, never on the exit code of the write.
    """
    try:
        cap = subprocess.run(["tmux", "capture-pane", "-p", "-t", pane],
                             capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return cap.returncode == 0 and needle in cap.stdout


def cmd_broadcast(args) -> int:
    """One-line alert into the cockpit panes.

    Delivery state advances ONLY for panes whose transcript proves the message landed.
    Previously this advanced the cursor for every target regardless of whether the send
    succeeded, so a failed broadcast was recorded as delivered and — because the cursor
    had moved — was never re-reported. Silent permanent loss, flagged by Codex review
    2026-08-19.
    """
    snap = scan(args.day, args.window)
    delta = compute_delta(load_cursor("broadcast"), snap)
    if not has_change(delta) and not delta["cold_start"]:
        print("[broadcast] nothing new; not sending.")
        return 1
    counts: dict[str, int] = {}
    for _l, sig in delta["added"]:
        k = sig.split("|")[0]
        counts[k] = counts.get(k, 0) + 1
    summary = ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) or "changes"
    msg = f"LEDGER {snap['day']}: {summary}. Run scripts/ledger_watch.py since --as <you>"

    try:
        out = subprocess.run(
            ["tmux", "list-panes", "-a", "-F",
             "#{session_name}:#{window_index}.#{pane_index} #{pane_title}"],
            capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        print(f"[broadcast] tmux unavailable: {exc}")
        return 3
    if out.returncode != 0:
        print(f"[broadcast] tmux list-panes failed rc={out.returncode}; nothing sent.")
        return 3

    targets = []
    for line in out.stdout.splitlines():
        pane, _, title = line.partition(" ")
        if not pane.strip():
            continue
        if "studio" in title.lower():
            continue                                   # TW29-WALL-35
        targets.append((pane, title.strip()))

    if not args.send:
        for pane, title in targets:
            print(f"[broadcast] DRY RUN → {pane} {title}: {msg}")
        print("\n[broadcast] dry run. Re-run with --send to type into panes.")
        return 0

    verified, failed = [], []
    for pane, title in targets:
        try:
            r = subprocess.run(["tmux", "send-keys", "-t", pane, msg],
                               capture_output=True, text=True, timeout=10)
            ok = r.returncode == 0 and _verify_in_pane(pane, msg)
        except (FileNotFoundError, subprocess.SubprocessError):
            ok = False
        (verified if ok else failed).append((pane, title))
        print(f"[broadcast] {'VERIFIED' if ok else 'NOT VERIFIED'} → {pane} {title}")

    print(f"\n[broadcast] {len(verified)} verified, {len(failed)} unverified "
          f"of {len(targets)} targets.")
    if failed:
        # Delivery is all-or-nothing on purpose: advancing on a partial send would mark
        # this delta delivered to panes that never received it, and it would never be
        # re-reported.
        print("[broadcast] cursor NOT advanced — this delta will be re-offered next run.")
        return 1
    save_cursor("broadcast", snap)
    print("[broadcast] cursor advanced; every target verified by transcript.")
    return 0


def main(argv: list[str] | None = None) -> int:
    today = date.today().isoformat()
    p = argparse.ArgumentParser(
        prog="ledger_watch.py",
        description="Watch the Dynasty Genius ledger across every tree. Observes and counts; never judges.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--day", default=today, help=f"anchor day (default {today})")
    common.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"days back to watch, not just today (default {DEFAULT_WINDOW})")
    p.add_argument("--day", default=today, help=argparse.SUPPRESS)
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", parents=[common],
                   help="current picture across all trees").set_defaults(fn=cmd_status)
    for name, adv, h in (("since", True, "delta since your checkpoint, then advance it"),
                         ("peek", False, "delta since your checkpoint, WITHOUT advancing")):
        s = sub.add_parser(name, parents=[common], help=h)
        s.add_argument("--as", dest="as_reader", required=True, metavar="READER")
        s.set_defaults(fn=lambda a, _a=adv: cmd_delta(a, _a))
    s = sub.add_parser("wait", parents=[common], help="BLOCK until the ledger moves (never advances the cursor)")
    s.add_argument("--as", dest="as_reader", required=True, metavar="READER")
    s.add_argument("--timeout", type=int, default=900)
    s.add_argument("--interval", type=int, default=5)
    s.set_defaults(fn=cmd_wait)
    s = sub.add_parser("broadcast", parents=[common], help="one-line tmux alert (dry run unless --send)")
    s.add_argument("--send", action="store_true")
    s.set_defaults(fn=cmd_broadcast)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
