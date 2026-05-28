"""Subsystem 3 — Prospect Identity Substrate.

Single-module implementation per spec §1. Organized in labeled sections:

- Constants & versions
- Schema (Pydantic 2.x)
- Exceptions
- ConfirmedProspectUuid wrapper        (later task)
- Match-key & normalization            (later task)
- Matcher (discovery-only)             (later task)
- Registry I/O (per-file atomic)       (later task)
- Ambiguity-before-mint                (later task)
- Ingestion entry-point                (later task)
- Promotion entry-points               (later task)

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ======================================================================
# Constants & versions
# ======================================================================

MATCHER_ALGORITHM_VERSION: str = "cpr_matcher_v1.0.0"


# ======================================================================
# Schema (Pydantic 2.x)
# ======================================================================


class IdProvenance(BaseModel):
    """Per-ID source/method/timestamp provenance block (spec §2)."""

    model_config = ConfigDict(extra="forbid")

    cfbd_athlete_id: Optional[dict[str, Any]] = None
    cfb_player_id: Optional[dict[str, Any]] = None
    pfr_id: Optional[dict[str, Any]] = None
    gsis_id: Optional[dict[str, Any]] = None
    sleeper_id: Optional[dict[str, Any]] = None


class NormalizedCollegeProspectRow(BaseModel):
    """Locked source-shaped contract (spec §2). CFBD-shape forward-compatible."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str
    normalized_name: str
    full_name: str
    position: str
    position_group: str
    draft_class: int
    class_year: Optional[str] = None
    current_school: str
    prior_schools: list[str] = Field(default_factory=list)
    cfbd_athlete_id: Optional[str] = None
    cfb_player_id: Optional[str] = None
    pfr_id: Optional[str] = None
    gsis_id: Optional[str] = None
    sleeper_id: Optional[str] = None
    source: str
    source_record_id: str
    source_snapshot_id: str
    id_provenance: IdProvenance
    notes: Optional[str] = None


class StatusHistoryEntry(BaseModel):
    """Append-only summary of one state transition on a registry row (spec §4.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    decision: Literal["confirm", "reject", "defer", "merge_into", "split", "ingest"]
    after_status: Literal["provisional", "confirmed", "deprecated"]
    decided_at: str
    reviewer_id: str


class RegistryEntry(NormalizedCollegeProspectRow):
    """Registry row = source row + identity-substrate fields (spec §4.2)."""

    model_config = ConfigDict(extra="forbid")

    prospect_uuid: str
    verification_status: Literal["provisional", "confirmed", "deprecated"]
    match_key: str
    status_history: list[StatusHistoryEntry]
    merged_into_prospect_uuid: Optional[str] = None
    reviewer_id: str = "davidleess"
    reviewer_metadata: dict[str, Any] = Field(default_factory=dict)

    def replace_status_history(self, new_history: list[StatusHistoryEntry]) -> None:
        """Spec §4.5 contract 5: status_history is append-only.

        Destructive rewrites are forbidden. This method exists ONLY to be exercised
        by the append-only invariant test; it always raises. Real updates go through
        ``append_status_history``.
        """
        raise StatusHistoryAppendOnlyError(
            "status_history is append-only; use append_status_history()"
        )

    def append_status_history(self, entry: StatusHistoryEntry) -> None:
        """The only blessed mutator for status_history. Appends; never replaces or deletes."""
        self.status_history.append(entry)


# ======================================================================
# Exceptions
# ======================================================================


class StatusHistoryAppendOnlyError(RuntimeError):
    """Raised when a destructive rewrite of status_history is attempted."""


class UnknownProspectUuid(LookupError):
    """ConfirmedProspectUuid construction: no such uuid in registry."""


class ProspectUuidNotConfirmed(RuntimeError):
    """ConfirmedProspectUuid construction: row exists but verification_status != 'confirmed'."""


class ProspectUuidDeprecatedMerged(RuntimeError):
    """ConfirmedProspectUuid construction: row was merged into another; follow redirect explicitly."""


# ======================================================================
# Registry I/O (minimal v1 — atomic write layer arrives in Round 2 Task 6)
# ======================================================================


class CollegeProspectRegistry(BaseModel):
    """In-memory registry. Persisted via the atomic write layer in Round 2 Task 6."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: dict[str, RegistryEntry] = Field(default_factory=dict)

    def get(self, prospect_uuid: str) -> Optional[RegistryEntry]:
        return self.entries.get(prospect_uuid)


def load_registry(path: Path) -> CollegeProspectRegistry:
    """Spec §2 / §10.1: missing or empty file loads as a no-op empty registry."""
    if not path.exists():
        return CollegeProspectRegistry()
    raw = json.loads(path.read_text())
    metadata = raw.get("metadata", {})
    entry_list = raw.get("entries", [])
    entries: dict[str, RegistryEntry] = {}
    for raw_entry in entry_list:
        entry = RegistryEntry.model_validate(raw_entry)
        entries[entry.prospect_uuid] = entry
    return CollegeProspectRegistry(metadata=metadata, entries=entries)
