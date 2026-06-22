"""Read-only S1 identity join + U4 match-rate gate (spec v4 §6, U4).

Resolves a curated mock prospect against the CONFIRMED S3 registry. STRICTLY
READ-ONLY: this module mints nothing and writes no registry/bridge state. Only a
:class:`ConfirmedProspectUuid` match feeds aggregation; fuzzy / ambiguous matches
surface to the human review queue and are NEVER auto-matched (common-name
collisions in particular). The optional alias-bridge target is resolved THROUGH
the registry and accepted only when it confirms.

The U4 match-rate gate operates over RAW pre-join ranked rows that preserve
unresolved entries, so a missing Top-N consensus prospect cannot silently bypass.

Import isolation (spec v4 U2): imports only the S3 identity substrate; never
Engine A/B, scoring, or ``backtest_mock_draft``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    MatchCandidate,
    NormalizedCollegeProspectRow,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    UnknownProspectUuid,
    compute_match_key,
    surface_review_candidates,
)

# Construction errors raised by ConfirmedProspectUuid for any non-confirmed target.
_UUID_WRAP_ERRORS = (
    UnknownProspectUuid,
    ProspectUuidNotConfirmed,
    ProspectUuidDeprecatedMerged,
)


@dataclass(frozen=True)
class IdentityResolution:
    """Outcome of resolving one curated row against the registry (read-only)."""

    confirmed_uuid: ConfirmedProspectUuid | None
    review_candidates: list[MatchCandidate] = field(default_factory=list)
    feeds_aggregation: bool = False


@dataclass(frozen=True)
class MatchRateGateResult:
    """U4 gate verdict over raw pre-join ranked rows."""

    should_abstain: bool
    reasons: list[str] = field(default_factory=list)


def _incoming_match_key(incoming: NormalizedCollegeProspectRow) -> str:
    return compute_match_key(
        normalized_name=incoming.normalized_name,
        position_group=incoming.position_group,
        draft_class=incoming.draft_class,
    )


def _try_confirm(
    uuid_str: str, registry: CollegeProspectRegistry
) -> ConfirmedProspectUuid | None:
    """Wrap ``uuid_str`` as a ConfirmedProspectUuid, or None if not confirmable."""
    try:
        return ConfirmedProspectUuid(uuid_str, registry=registry)
    except _UUID_WRAP_ERRORS:
        return None


def _resolve_alias(
    incoming: NormalizedCollegeProspectRow,
    registry: CollegeProspectRegistry,
    alias_bridge: CollegeAliasBridge,
) -> ConfirmedProspectUuid | None:
    """Read-only alias lookup: (match_key, source_record_id) -> confirmed target."""
    key = _incoming_match_key(incoming)
    for entry in alias_bridge.entries:
        if (
            entry.match_key == key
            and entry.source_record_id == incoming.source_record_id
        ):
            return _try_confirm(entry.target_prospect_uuid, registry)
    return None


def resolve_curated_row_identity(
    incoming: NormalizedCollegeProspectRow,
    *,
    registry: CollegeProspectRegistry,
    alias_bridge: CollegeAliasBridge,
) -> IdentityResolution:
    """Resolve a curated row to a confirmed prospect (read-only; mints nothing).

    Order: direct confirmed match_key (exactly one -> match; two or more ->
    common-name collision, review, no auto-match) -> read-only alias bridge ->
    fuzzy review queue. Only a confirmed match feeds aggregation.
    """
    key = _incoming_match_key(incoming)
    confirmed_with_key = [
        entry
        for entry in registry.entries.values()
        if entry.match_key == key and entry.verification_status == "confirmed"
    ]

    if len(confirmed_with_key) == 1:
        confirmed = _try_confirm(confirmed_with_key[0].prospect_uuid, registry)
        if confirmed is not None:
            return IdentityResolution(
                confirmed_uuid=confirmed, feeds_aggregation=True
            )
    elif len(confirmed_with_key) >= 2:
        # Common-name collision: never auto-match; surface every candidate.
        return IdentityResolution(
            confirmed_uuid=None,
            review_candidates=surface_review_candidates(incoming, registry.entries),
            feeds_aggregation=False,
        )

    alias_confirmed = _resolve_alias(incoming, registry, alias_bridge)
    if alias_confirmed is not None:
        return IdentityResolution(
            confirmed_uuid=alias_confirmed, feeds_aggregation=True
        )

    # Fuzzy fallback -> human review queue (never auto-match).
    return IdentityResolution(
        confirmed_uuid=None,
        review_candidates=surface_review_candidates(incoming, registry.entries),
        feeds_aggregation=False,
    )


def apply_match_rate_gate(
    ranked_rows: list[dict],
    *,
    top_n: int = 12,
    max_unresolved: float = 0.20,
) -> MatchRateGateResult:
    """U4 fail-closed gate over raw pre-join ranked rows.

    ``ranked_rows`` are the raw latest-eligible rows ranked by projected pick, each
    a mapping with ``raw_rank`` (1-based int) and ``resolved`` (bool) — INCLUDING
    unresolved entries. Abstain if the overall unresolved rate exceeds
    ``max_unresolved`` OR any unresolved row falls within the top ``top_n``.
    """
    total = len(ranked_rows)
    if total == 0:
        return MatchRateGateResult(
            should_abstain=True, reasons=["no_ranked_rows: empty consensus"]
        )

    # Fail-closed row-shape validation: a malformed raw row must abstain with an
    # explicit reason — never crash, and never let a wrong-type ``resolved`` value
    # silently count as resolved (which would bypass the integrity gate).
    for idx, row in enumerate(ranked_rows):
        if not isinstance(row, dict):
            return MatchRateGateResult(
                should_abstain=True,
                reasons=[f"malformed_ranked_row at index {idx}: not a mapping"],
            )
        rank = row.get("raw_rank")
        resolved = row.get("resolved")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            return MatchRateGateResult(
                should_abstain=True,
                reasons=[
                    f"malformed_ranked_row at index {idx}: "
                    f"raw_rank must be a positive int, got {rank!r}"
                ],
            )
        if not isinstance(resolved, bool):
            return MatchRateGateResult(
                should_abstain=True,
                reasons=[
                    f"malformed_ranked_row at index {idx}: "
                    f"resolved must be a bool, got {resolved!r}"
                ],
            )

    unresolved = [row for row in ranked_rows if not row["resolved"]]
    unresolved_rate = len(unresolved) / total
    reasons: list[str] = []

    if unresolved_rate > max_unresolved:
        reasons.append(
            f"unresolved_rate {unresolved_rate:.3f} exceeds "
            f"max_unresolved {max_unresolved}"
        )

    top_n_unresolved = sorted(
        row["raw_rank"] for row in unresolved if row["raw_rank"] <= top_n
    )
    if top_n_unresolved:
        reasons.append(f"top_{top_n}_unresolved at ranks {top_n_unresolved}")

    return MatchRateGateResult(should_abstain=bool(reasons), reasons=reasons)
