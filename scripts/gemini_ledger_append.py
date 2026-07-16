"""Constrained ledger-append command for the Gemini Operations & Telemetry seat — Gemini-controls Layer 2.

Gemini's native file-write tools are denied (spec §3); this is the ONLY path by
which Gemini may write the daily agent ledger. The target file is computed
internally (``docs/agent-ledger/<today>.md``) — there is NO path argument, so the
write cannot be redirected. Author attribution is hardcoded to "Gemini
(Operations & Telemetry)" (the David-ratified 2026-07-16 re-role) so the command
cannot impersonate Claude or Codex. Writes are append-only and fail closed if the
resolved target escapes ``docs/agent-ledger/`` (e.g. via a symlinked file or
directory).

Spec: docs/superpowers/specs/2026-06-02-gemini-enforced-controls-design.md §4;
re-role: docs/superpowers/specs/2026-07-16-gemini-ops-telemetry-rerole-02-amendment.md.

Usage (no path arg by design):
    .venv/bin/python3.14 scripts/gemini_ledger_append.py < entry_body.md
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_ATTRIBUTION = "Gemini (Operations & Telemetry)"
_LEDGER_TAIL = ("docs", "agent-ledger")
_ET = ZoneInfo("America/New_York")


def append_gemini_ledger_entry(*, body: str, ledger_dir: Path, now: datetime) -> Path:
    """Append a Gemini-attributed entry to ``<ledger_dir>/<today>.md``; return its path.

    Fail-closed: raises ``ValueError`` (writing nothing) if ``ledger_dir`` does not
    resolve to a real ``docs/agent-ledger`` directory, or if today's target file is a
    symlink / otherwise resolves outside that directory. Append-only — existing
    content is never truncated or overwritten.
    """
    ledger_dir = Path(ledger_dir)
    # Fail closed unless the supplied path IS a clean ``<root>/docs/agent-ledger`` with
    # no symlink in the ``docs`` or ``agent-ledger`` components (leaf, parent, or any
    # tail traversal). Resolving the root on both sides cancels "boring" ancestor
    # symlinks (e.g. macOS ``/var`` -> ``/private/var``); any symlink in the
    # docs/agent-ledger tail makes the fully-resolved path diverge from the literal
    # canonical path -> reject. No repo-root coupling: the root anchor is derived from
    # the supplied path itself (``ledger_dir.parent.parent``).
    resolved_dir = ledger_dir.resolve()
    canonical_dir = ledger_dir.parent.parent.resolve() / _LEDGER_TAIL[0] / _LEDGER_TAIL[1]
    if resolved_dir != canonical_dir:
        raise ValueError(
            f"ledger_dir {ledger_dir} (resolved {resolved_dir}) escapes docs/agent-ledger"
        )

    target = ledger_dir / f"{now.strftime('%Y-%m-%d')}.md"
    if target.is_symlink() or (target.exists() and target.resolve().parent != resolved_dir):
        raise ValueError(
            f"ledger target {target} escapes docs/agent-ledger via symlink"
        )

    entry = f"## {now.strftime('%H:%M')} ET - {_ATTRIBUTION}\n\n{body}\n"

    ledger_dir.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        existing = target.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        with target.open("a", encoding="utf-8") as handle:
            handle.write(separator + entry)
    else:
        target.write_text(entry, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    """Thin CLI glue: read the entry body from stdin; write today's ledger entry.

    Deliberately exposes NO path argument (spec §4) — ``ledger_dir`` is fixed to the
    repo ``docs/agent-ledger`` and the timestamp is the current Eastern Time.
    """
    if argv:
        print("usage: gemini_ledger_append.py (entry body on stdin; no arguments)", file=sys.stderr)
        return 2
    body = sys.stdin.read().rstrip("\n")
    if not body.strip():
        print("error: empty ledger entry body on stdin", file=sys.stderr)
        return 2
    ledger_dir = Path(__file__).resolve().parents[1] / "docs" / "agent-ledger"
    written = append_gemini_ledger_entry(body=body, ledger_dir=ledger_dir, now=datetime.now(_ET))
    print(str(written))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
