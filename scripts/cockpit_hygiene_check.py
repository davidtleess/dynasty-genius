"""Cockpit working-tree hygiene tripwire — Gemini-controls Layer 3 (defense-in-depth).

Surfaces working-tree changes (including UNTRACKED files) that fall outside an
allowlist of expected-mutable paths, so an unexpected artifact (e.g. an out-of-lane
``scripts/run_2025_curation.py``) is caught. This is a DETECTION / surfacing gate,
not prevention, and is run manually by Claude/Codex at session boundaries and before
accepting any Gemini source-verification CLEAR. It does NOT attribute authorship; it
answers "is the tree in the expected state?".

Standalone by design — NOT folded into ``validate_governance.py`` (which may be
CI/pre-commit-wired, where an untracked-file scan would false-positive on in-flight
work). Spec: docs/superpowers/specs/2026-06-02-gemini-enforced-controls-design.md §5.

Note: this module is intentionally WITHOUT ``from __future__ import annotations``.
The contract tests load it via ``importlib.util.spec_from_file_location`` (the repo's
standard script-test pattern) without registering it in ``sys.modules``; under Python
3.14, a ``@dataclass`` with stringized (future) annotations triggers a ``sys.modules``
lookup that then fails. Eager annotations avoid that and are fully valid on 3.14.
"""
import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable

# Gemini lane re-scope (02-agent-operating-loop.md §Falsification #7): banned overreach
# declarations. The tripwire flags these ONLY inside Gemini-attributed ledger sections —
# a literal, case-insensitive substring flag, NOT an adjudicator of quoted/contextual use.
BANNED_GEMINI_DECLARATIONS = [
    "consensus lock",
    "team consensus",
    "unanimous",
    "Status: APPROVED",
    "Trust Consensus",
    "Governance CLEAR",
    "governance confirmed",
    "post-merge confirmation",
    "the loop is closed",
]

_GEMINI_ATTRIBUTION = "Gemini (Product Manager)"


def scan_gemini_ledger_violations(ledger_text: str) -> list[tuple[int, str, str]]:
    """Flag banned lane-overreach declarations inside Gemini-attributed ledger sections.

    A Gemini section runs from a header shaped ``## HH:MM ET - Gemini (Product Manager)``
    up to the next ``## `` header. Within those sections only, each banned-pattern hit
    yields a ``(1-based file line number, canonical banned pattern, original line text)``
    tuple. Match is literal + case-insensitive; this is a tripwire (it flags; it does not
    adjudicate quoted or contextual use). Lines outside Gemini sections are ignored.
    """
    violations: list[tuple[int, str, str]] = []
    in_gemini = False
    for line_no, line in enumerate(ledger_text.splitlines(), start=1):
        if line.startswith("## "):
            in_gemini = _GEMINI_ATTRIBUTION in line
            continue
        if not in_gemini:
            continue
        lowered = line.lower()
        for pattern in BANNED_GEMINI_DECLARATIONS:
            if pattern.lower() in lowered:
                violations.append((line_no, pattern, line))
    return violations


@dataclass(frozen=True)
class StatusEntry:
    """A single ``git status --porcelain`` change: status code + path."""

    status: str
    path: str


@dataclass(frozen=True)
class PartitionResult:
    """Working-tree changes split into allowlist-accounted vs anomalous."""

    accounted: list[StatusEntry]
    anomalous: list[StatusEntry]


def partition_status_lines(
    status_lines: list[str], allow_patterns: list[str]
) -> PartitionResult:
    """Split porcelain lines into accounted (matches an allow glob) vs anomalous.

    Input order is preserved within each group.
    """
    accounted: list[StatusEntry] = []
    anomalous: list[StatusEntry] = []
    for line in status_lines:
        if not line.strip():
            continue
        entry = StatusEntry(status=line[:2].strip(), path=line[3:])
        if any(fnmatch(entry.path, pattern) for pattern in allow_patterns):
            accounted.append(entry)
        else:
            anomalous.append(entry)
    return PartitionResult(accounted=accounted, anomalous=anomalous)


def default_allow_patterns(today: date) -> list[str]:
    """Expected-mutable paths for a normal cockpit session."""
    return [
        "AGENT_SYNC.md",
        f"docs/agent-ledger/{today.strftime('%Y-%m-%d')}.md",
        "docs/strategies/*.md",
        "app/data/backtest/subpopulation/*",
    ]


def format_anomalies(anomalous: list[StatusEntry]) -> str:
    """Render anomalous entries as ``<status> <path>`` lines."""
    return "\n".join(f"{entry.status} {entry.path}" for entry in anomalous)


def _git_status_porcelain() -> list[str]:
    """Return unquoted ``XY path`` records from ``git status --porcelain -z``.

    ``-z`` emits NUL-separated, verbatim (never quoted) paths — so space- and
    non-ASCII-containing paths survive intact for allowlist matching. For rename/copy
    records (status contains ``R``/``C``) git appends the source path as the next NUL
    field; that source field is skipped (only the destination record is surfaced).
    """
    completed = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        capture_output=True,
        text=False,
        check=True,
    )
    fields = completed.stdout.decode("utf-8").split("\x00")
    lines: list[str] = []
    skip_next = False
    for field in fields:
        if field == "":
            continue
        if skip_next:
            skip_next = False
            continue
        lines.append(field)
        if "R" in field[:2] or "C" in field[:2]:
            skip_next = True
    return lines


def main(
    argv: list[str] | None = None,
    *,
    status_lines_provider: Callable[[], list[str]] | None = None,
    today: date | None = None,
) -> int:
    """Exit 1 (printing anomalies to stderr) if any change escapes the allowlist; else 0."""
    parser = argparse.ArgumentParser(description="Cockpit working-tree hygiene tripwire.")
    parser.add_argument(
        "--allow",
        action="append",
        default=None,
        metavar="GLOB",
        help="Extra allowlist glob for a known in-flight batch (repeatable).",
    )
    parser.add_argument(
        "--gemini-ledger-scan",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help=(
            "Gemini-lane tripwire: scan a ledger (default today's "
            "docs/agent-ledger/<date>.md) for banned overreach declarations in "
            "Gemini-attributed sections; print path:line — pattern to stderr, exit 1 if any."
        ),
    )
    args = parser.parse_args(argv)

    if args.gemini_ledger_scan is not None:
        resolved_today = today or date.today()
        ledger_path = args.gemini_ledger_scan or (
            f"docs/agent-ledger/{resolved_today.strftime('%Y-%m-%d')}.md"
        )
        ledger_text = Path(ledger_path).read_text(encoding="utf-8")
        violations = scan_gemini_ledger_violations(ledger_text)
        for line_no, pattern, _line_text in violations:
            print(
                f"Gemini lane violation detected: {ledger_path}:{line_no} — {pattern}",
                file=sys.stderr,
            )
        return 1 if violations else 0

    provider = status_lines_provider or _git_status_porcelain
    resolved_today = today or date.today()
    patterns = default_allow_patterns(resolved_today) + (args.allow or [])

    result = partition_status_lines(provider(), patterns)
    if result.anomalous:
        print(format_anomalies(result.anomalous), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
