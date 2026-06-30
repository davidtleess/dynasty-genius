"""No-Verdict scanner for the league_opportunity + League Pulse surface (Phase 1 T1).

This is the *cordon* for the Phase 1 No-Verdict reconciliation. It scans source,
generated-client, OpenAPI, and visible-frontend surfaces for banned No-Verdict
vocabulary and fails closed on anything not pinned in an exact allowlist:

- recommendation language (``recommend`` stem, case-insensitive),
- tool-nominated targets (``tool_nominated`` stem, case-insensitive),
- action-order scores (``opportunity_score`` stem, case-insensitive),
- action-shaped CANDIDATE enums (ALL-CAPS identifiers containing ``CANDIDATE``),
- snake_case action-candidate fields (``drop_candidate``, ``waiver_candidate``, ...),
- action-verb + ``candidate`` label phrases (e.g. "Activation candidate").

The candidate distinction is deliberate: ``candidate`` as a tool-nominated *action*
(an enum card type, a visible action label, or a singular action-prefixed field) is
banned; ``candidate`` as a *descriptive pool noun* (``cut_candidates``,
``CapacityCandidate``, ``top_candidates``) is allowed.

Structural scanner failures fail loud, never silently: a path outside ``root`` yields a
``scanner_path_outside_root`` finding and an unreadable/missing surface file yields a
``scanner_file_unavailable`` finding (neither is allowlist-suppressible).

The known-debt allowlist is split into two exact (path + token + reason) buckets — never
a glob, so a newly introduced violation anywhere fails immediately even mid-migration:

- ``LEAGUE_PULSE_PHASE_1_DEBT`` was removed by Phase 1 (T2-T4), incl. What-Changed's
  *consumption* of renamed league_opportunity fields; the closeout asserts it is empty.
- ``WHAT_CHANGED_GOVERNANCE_DEBT`` held What-Changed's *own* model-ops tripwire field names,
  which the governance reconcile renamed to descriptive threshold-crossing language; that
  bucket is now empty too.

Both buckets are now empty, so the cordon is FULLY ENFORCING across the whole surface: any
newly introduced No-Verdict token fails immediately. ``KNOWN_DEBT_ALLOWLIST`` (their union)
is empty; :func:`allowlist_by_bucket` still reports per-bucket so the contract is explicit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# An identifier-ish token: a JSON key, Python/TS name, enum value, etc.
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Banned identifier stems (case-insensitive substring within a single identifier).
_RECOMMEND = re.compile(r"recommend", re.IGNORECASE)
_TOOL_NOMINATED = re.compile(r"tool_nominated", re.IGNORECASE)
_OPPORTUNITY_SCORE = re.compile(r"opportunity_score", re.IGNORECASE)

# An action verb immediately followed by "candidate" in a visible label/phrase.
_ACTION_CANDIDATE_PHRASE = re.compile(
    r"\b(?:activation|activate|drop|cut|add|start|sit|bench|trade|acquire|pickup|claim)"
    r"\s+candidate\b",
    re.IGNORECASE,
)

# Action terms that, paired with a *singular* "candidate" segment in a snake_case
# identifier, mark a tool-nominated action field (drop_candidate, waiver_candidate,
# cut_candidate_id, ...). The plural "candidates" and CamelCase class nouns
# (CapacityCandidate) are descriptive and never match this rule.
_ACTION_TERMS = frozenset(
    {
        "drop",
        "cut",
        "add",
        "start",
        "sit",
        "bench",
        "trade",
        "acquire",
        "pickup",
        "claim",
        "activate",
        "activation",
        "waiver",
        "nominate",
        "nominated",
        "select",
    }
)


@dataclass(frozen=True)
class AllowlistEntry:
    """One exact, pre-existing No-Verdict debt occurrence, pinned for removal."""

    path: str
    token: str
    reason: str


@dataclass(frozen=True)
class Finding:
    """A banned token detected at a path and not covered by the allowlist."""

    path: str
    token: str


def _is_action_candidate_enum(identifier: str) -> bool:
    """An ALL-CAPS identifier containing CANDIDATE is an action-shaped card type.

    ``WAIVER_CANDIDATE`` / ``TAXI_ACTIVATION_CANDIDATE`` -> banned.
    ``RosterCutCandidate`` / ``cut_candidates`` / ``top_candidates`` -> allowed.
    """
    return "CANDIDATE" in identifier and identifier == identifier.upper()


def _is_action_candidate_field(identifier: str) -> bool:
    """A snake_case identifier with a singular ``candidate`` segment + an action term.

    ``drop_candidate`` / ``cut_candidate_id`` / ``waiver_candidate`` -> banned.
    ``cut_candidates`` (plural) / ``CapacityCandidate`` (one camel token) -> allowed.
    """
    parts = [part.lower() for part in identifier.split("_") if part]
    if "candidate" not in parts:
        return False
    return any(part in _ACTION_TERMS for part in parts)


def _identifier_is_banned(identifier: str) -> bool:
    return bool(
        _RECOMMEND.search(identifier)
        or _TOOL_NOMINATED.search(identifier)
        or _OPPORTUNITY_SCORE.search(identifier)
        or _is_action_candidate_enum(identifier)
        or _is_action_candidate_field(identifier)
    )


def scan_text(text: str) -> set[str]:
    """Return the set of banned tokens (identifiers + action-candidate phrases) in text."""
    tokens: set[str] = {
        ident for ident in _IDENTIFIER.findall(text) if _identifier_is_banned(ident)
    }
    tokens.update(match.group(0) for match in _ACTION_CANDIDATE_PHRASE.finditer(text))
    return tokens


def scan_paths(
    paths: list[Path],
    *,
    root: Path | None = None,
    allowlist: list[AllowlistEntry] | None = None,
) -> list[Finding]:
    """Scan ``paths`` and return findings not suppressed by the exact allowlist.

    ``root`` (when given) is the base the reported/allowlist paths are relative to.
    A finding is suppressed only when an allowlist entry matches its (path, token)
    exactly.
    """
    if allowlist is None:
        allowlist = KNOWN_DEBT_ALLOWLIST
    allowed: set[tuple[str, str]] = {(entry.path, entry.token) for entry in allowlist}

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    def _add(rel: str, token: str, *, suppressible: bool) -> None:
        key = (rel, token)
        if key in seen:
            return
        # Structural scanner errors (out-of-root, unreadable) fail loud and are
        # never suppressed by the allowlist; banned-token findings are.
        if suppressible and key in allowed:
            return
        seen.add(key)
        findings.append(Finding(path=rel, token=token))

    for raw in paths:
        path = Path(raw)
        if root is not None:
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                _add(str(path), "scanner_path_outside_root", suppressible=False)
                continue
        else:
            rel = str(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, IsADirectoryError):
            _add(rel, "scanner_file_unavailable", suppressible=False)
            continue
        for token in sorted(scan_text(text)):
            _add(rel, token, suppressible=True)
    return findings


# No-Verdict debt allowlist, split into two exact (path + token + reason) buckets — never a
# glob, so a newly introduced violation anywhere fails immediately. BOTH buckets are now empty:
#
# LEAGUE_PULSE_PHASE_1_DEBT was emptied by Phase 1 (T2-T4): the producer/DTO/assembler renames
# (T2/T3), the backend What-Changed consumption (T4a), the FE client + visible render (T4b), and
# T4c's enforce/go-live (v1-compat shim deleted, header reworded, generated title-case residue
# reclassified out).
#
# WHAT_CHANGED_GOVERNANCE_DEBT held What-Changed's own model-ops seed-staleness tripwire field
# names, which the governance reconcile renamed to descriptive threshold-crossing language; the
# bucket is now empty too. The cordon is FULLY ENFORCING across the entire live surface.
LEAGUE_PULSE_PHASE_1_DEBT: list[AllowlistEntry] = []

WHAT_CHANGED_GOVERNANCE_DEBT: list[AllowlistEntry] = []

# Union of both buckets — the full known-debt the cordon allows on the live surface.
KNOWN_DEBT_ALLOWLIST: list[AllowlistEntry] = (
    LEAGUE_PULSE_PHASE_1_DEBT + WHAT_CHANGED_GOVERNANCE_DEBT
)


def allowlist_by_bucket() -> dict[str, list[AllowlistEntry]]:
    """Report known debt by bucket so the cordon never claims a false full-surface zero."""
    return {
        "LEAGUE_PULSE_PHASE_1_DEBT": list(LEAGUE_PULSE_PHASE_1_DEBT),
        "WHAT_CHANGED_GOVERNANCE_DEBT": list(WHAT_CHANGED_GOVERNANCE_DEBT),
    }
