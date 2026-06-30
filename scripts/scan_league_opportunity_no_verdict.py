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

- ``LEAGUE_PULSE_PHASE_1_DEBT`` is removed by Phase 1 (T2-T4), incl. What-Changed's
  *consumption* of renamed league_opportunity fields; the T4 closeout asserts it is empty.
- ``WHAT_CHANGED_GOVERNANCE_DEBT`` is What-Changed's *own* independent tripwire language
  (``promote_recommended`` / ``recommendation_reasons``) — out of Phase 1 scope, tracked
  under a separate governance ticket, and reported (via :func:`allowlist_by_bucket`) but
  not counted toward the T4 empty assertion, so the cordon never claims a false zero.

``KNOWN_DEBT_ALLOWLIST`` is the union of both buckets.
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


# Pre-existing No-Verdict debt across the live Phase 1 surface, split into two buckets.
# Each entry is exact (path + token + reason) — never a glob — so a newly introduced
# violation anywhere fails immediately even while the surface is mid-migration.
#
# LEAGUE_PULSE_PHASE_1_DEBT is removed by Phase 1 tasks T2-T4 (incl. What-Changed's
# CONSUMPTION of renamed league_opportunity fields, which moves with the contract);
# the T4 closeout asserts this bucket is empty.
#
# WHAT_CHANGED_GOVERNANCE_DEBT is What-Changed's OWN independent recommendation-language
# (the model-ops seed-staleness tripwire promote_recommended + recommendation_reasons).
# It is out of Phase 1 scope, tracked under a separate governance ticket, and is REPORTED
# but NOT counted toward the T4 empty assertion (so we never claim a false generated-
# client zero).
# T4c closed out the League Pulse bucket. Earlier tasks cleared the producer/DTO/
# assembler (T2/T3), the backend What-Changed consumption (T4a), and the FE client +
# visible render (T4b). T4c then: (1) dropped the transitional v1-compat shim
# (league_pulse_v1_compat.py deleted, so its 4 legacy-token entries are gone),
# (2) reworded the LeaguePulseHeader honesty band to the neutral diagnostic-workspace
# copy (no "recommend" token), and (3) RECLASSIFIED the 4 residual capital
# Recommendation/Recommended generated entries into WHAT_CHANGED_GOVERNANCE_DEBT below
# — they are the title-case generated forms of What-Changed's promote_recommended /
# recommendation_reasons fields, not League Pulse residue. The bucket is therefore
# empty and the cordon is ENFORCING: any newly-introduced No-Verdict token on the
# League Pulse surface fails immediately.
LEAGUE_PULSE_PHASE_1_DEBT: list[AllowlistEntry] = []

WHAT_CHANGED_GOVERNANCE_DEBT: list[AllowlistEntry] = [
    AllowlistEntry(
        path='app/api/routes/league_what_changed_models.py',
        token='promote_recommended',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='app/api/routes/league_what_changed_models.py',
        token='recommendation_reasons',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/openapi.json',
        token='promote_recommended',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/openapi.json',
        token='recommendation_reasons',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/types.gen.ts',
        token='promote_recommended',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/types.gen.ts',
        token='recommendation_reasons',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/zod.gen.ts',
        token='promote_recommended',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/zod.gen.ts',
        token='recommendation_reasons',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    AllowlistEntry(
        path='src/dynasty_genius/what_changed/report.py',
        token='promote_recommended',
        reason='What-Changed independent recommendation-language tripwire; separate tracked governance ticket, NOT removed by Phase 1 (see follow-up)',
    ),
    # T4c reclassification: these capital Recommendation/Recommended generated tokens
    # are the title-case forms ("Promote Recommended" / "Recommendation Reasons") that
    # openapi-ts emits for the What-Changed promote_recommended / recommendation_reasons
    # fields above — NOT League Pulse residue. They move here with their owning fields
    # and are resolved by the same separate What-Changed governance ticket.
    AllowlistEntry(
        path='frontend/openapi.json',
        token='Recommendation',
        reason='generated title-case form of What-Changed recommendation_reasons; separate governance ticket, NOT removed by Phase 1',
    ),
    AllowlistEntry(
        path='frontend/openapi.json',
        token='Recommended',
        reason='generated title-case form of What-Changed promote_recommended; separate governance ticket, NOT removed by Phase 1',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/types.gen.ts',
        token='Recommendation',
        reason='generated title-case form of What-Changed recommendation_reasons; separate governance ticket, NOT removed by Phase 1',
    ),
    AllowlistEntry(
        path='frontend/src/lib/api/types.gen.ts',
        token='Recommended',
        reason='generated title-case form of What-Changed promote_recommended; separate governance ticket, NOT removed by Phase 1',
    ),
]

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
