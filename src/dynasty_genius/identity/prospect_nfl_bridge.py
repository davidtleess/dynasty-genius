"""Subsystem 4 — Prospect ↔ NFL Bridge.

Cross-domain identity infrastructure: maps S3's pre-draft prospect_uuid
(opaque cpr_<uuid4>, confirmed only) to realized NFL gsis_id (from nflreadr
draft truth) at draft time. Manual-first review queue + promotion lifecycle;
per-file atomic writes; decision-log replay over genesis state per S3 §6.3.

Single-module implementation organized in labeled sections:
- Constants & versions
- Schema (Pydantic 2.x)
- Exceptions
- Validation (rules from spec §3.2)
- Atomic write helpers           (Task 2)
- Decision log + replay          (Task 2)
- Discovery / candidate matching (Task 3)
- Promotion lifecycle            (Task 4)

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
)

# ======================================================================
# Constants & versions
# ======================================================================

BRIDGE_SCHEMA_VERSION: str = "prospect_nfl_bridge_v1.0.0"
NFL_DOMAIN_MATCHER_VERSION: str = "cpr_nfl_bridge_matcher_v1.0.0"


# ======================================================================
# Schema (Pydantic 2.x)
# ======================================================================


class ProspectNflBridgeEntry(BaseModel):
    """Spec §3.1: cross-domain bridge entry mapping pre-draft prospect_uuid →
    realized NFL identity. Accepted-only artifact entries (`confirm` and `udfa`
    decisions); rejects/defers live only in the decision log + review queue."""

    model_config = ConfigDict(extra="forbid")

    # identity
    prospect_uuid: str
    gsis_id: Optional[str] = None
    pfr_id: Optional[str] = None

    # context
    draft_year: int
    draft_pick_no: Optional[int] = None
    draft_round: Optional[int] = None
    nfl_team: Optional[str] = None
    udfa: bool

    # provenance of the nflreadr snapshot used at decision time (spec §3.1 + §3.2 rule 5)
    nflreadr_source: str
    nflreadr_season: int
    draft_truth_content_hash: str
    nflreadr_fetched_at: str

    evidence_snapshot: Optional[dict[str, Any]] = None

    # decision audit (no nested status_history; that's S3 vocabulary)
    event_id: str
    decided_at: str
    reviewer_id: str
    decision: Literal["confirm", "udfa"]
    note: Optional[str] = None


# ======================================================================
# Exceptions
# ======================================================================


class BridgeValidationError(RuntimeError):
    """Raised when a bridge graph validation reveals an inconsistency."""


class BridgeEvidenceRequiredError(ValueError):
    """`udfa` promotion requires non-empty --evidence per spec §3.3."""


class BridgeConflictingDecisionError(RuntimeError):
    """Same prospect_uuid already has a different ACCEPTED decision in the log
    (procedural decisions reject/defer do not conflict with later accepted)."""


# ======================================================================
# Validation (rules from spec §3.2, per-entry shape checks)
# ======================================================================


def validate_bridge_entry(entry: ProspectNflBridgeEntry) -> list[str]:
    """Per-entry shape validation. Returns a list of human-readable errors
    (empty list = valid). Cross-entry invariants (1:1) are checked in
    ``validate_bridge_graph``; S3 confirmation + draft_year invariants are
    checked in ``validate_against_s3`` (Round 2 patch 1)."""
    errors: list[str] = []
    if entry.udfa:
        # spec §3.2 rule 4: udfa=True ⇒ 5 strict null fields
        for field in ("gsis_id", "pfr_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is not None:
                errors.append(
                    f"udfa=True requires {field}=None (spec §3.2 rule 4); got "
                    f"{getattr(entry, field)!r}"
                )
    else:
        # spec §3.2 rule 5: udfa=False ⇒ 4 required NFL fields
        for field in ("gsis_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is None:
                errors.append(
                    f"udfa=False requires {field} present (spec §3.2 rule 5); "
                    f"got None"
                )
        # pfr_id is nullable secondary; not required even when udfa=False
    return errors


def validate_against_s3(
    entry: ProspectNflBridgeEntry,
    *,
    s3_registry: CollegeProspectRegistry,
) -> list[str]:
    """Round 2 patch 1 (Codex plan review): spec §3.2 rules 1 + 2 require S3
    knowledge at bridge write time. Caller passes a loaded S3
    ``CollegeProspectRegistry``.

    Returns errors if:
    - ``prospect_uuid`` is not present in S3 (unknown)
    - ``prospect_uuid`` is in S3 but not ``verification_status="confirmed"``
    - bridge entry's ``draft_year`` != S3 row's ``draft_class``
    """
    errors: list[str] = []
    s3_row = s3_registry.entries.get(entry.prospect_uuid)
    if s3_row is None:
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} not in S3 registry (spec §3.2 rule 1)"
        )
        return errors  # can't check rule 2 without an S3 row
    if s3_row.verification_status != "confirmed":
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} has S3 status="
            f"{s3_row.verification_status!r} (not confirmed; spec §3.2 rule 1)"
        )
    if entry.draft_year != s3_row.draft_class:
        errors.append(
            f"bridge draft_year={entry.draft_year} != S3 row's draft_class="
            f"{s3_row.draft_class} (spec §3.2 rule 2)"
        )
    return errors
