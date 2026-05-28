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


# ======================================================================
# Match-key & normalization (spec §4.3 + §5.1)
# ======================================================================

import hashlib  # noqa: E402  (grouped with the matcher section it serves)
import re  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import jellyfish  # noqa: E402
from rapidfuzz import fuzz as _rf_fuzz  # noqa: E402

_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]")


def normalize_name(name: str) -> str:
    """Spec §5.1: identical to prospect_identity_resolver.normalize_name."""
    return _NORMALIZE_RE.sub("", name.lower()).strip()


def compute_match_key(*, normalized_name: str, position_group: str, draft_class: int) -> str:
    """Deterministic SHA-256 hash of (normalized_name, position_group, draft_class).

    Lookup/grouping key only — NEVER an identity key (spec §4.5 contract 6).
    """
    payload = f"{normalized_name}|{position_group.upper()}|{draft_class}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ======================================================================
# Matcher (discovery-only, fail-closed) — spec §5
# ======================================================================

MIN_CANDIDATE_SCORE: float = 0.80
LOW_CONFIDENCE_LOWER: float = 0.80
LOW_CONFIDENCE_UPPER: float = 0.88
AMBIGUOUS_NEAR_TIE_MARGIN: float = 0.05
CROSS_POSITION_THRESHOLD: float = 0.90
TOP_K_CANDIDATES: int = 3

POSITION_BONUS: float = 0.10
SCHOOL_BONUS: float = 0.05
JW_WEIGHT: float = 0.75
TOKEN_SET_WEIGHT: float = 0.25

# Position-group whitelist (offense-only v1; direction-insensitive) — spec §5.3
POSITION_GROUP_WHITELIST: frozenset[frozenset[str]] = frozenset({
    frozenset({"WR", "TE"}),
    frozenset({"WR", "RB"}),
    frozenset({"FB", "RB"}),
})

# Hard-block families (spec §5.3) — direction-insensitive
_OL_FAMILY: frozenset[str] = frozenset({"OL", "OT", "OG", "C"})
_SPECIAL_TEAMS: frozenset[str] = frozenset({"K", "P", "LS"})
_DEFENSIVE_GROUPS: frozenset[str] = frozenset({
    "DL", "DT", "DE", "EDGE", "OLB", "LB", "CB", "S", "DB",
})
_OFFENSIVE_SKILL: frozenset[str] = frozenset({"QB", "RB", "WR", "TE", "FB"})


def is_position_pair_whitelisted(a: str, b: str) -> bool:
    """Spec §5.3: direction-insensitive whitelist check."""
    return frozenset({a.upper(), b.upper()}) in POSITION_GROUP_WHITELIST


def is_position_pair_hard_blocked(a: str, b: str) -> bool:
    """Spec §5.3: direction-insensitive hard-block check.

    Hard-block rules:
    - QB ↔ anything else (never)
    - OL family (OL/OT/OG/C) ↔ anything except itself (never)
    - Special teams (K/P/LS) ↔ anything except themselves (never)
    - Defensive group ↔ offensive skill, either direction (never)
    """
    au = a.upper()
    bu = b.upper()
    if au == bu:
        return False
    if "QB" in {au, bu}:
        return True
    if au in _OL_FAMILY or bu in _OL_FAMILY:
        return True
    if au in _SPECIAL_TEAMS or bu in _SPECIAL_TEAMS:
        return True
    if (au in _DEFENSIVE_GROUPS and bu in _OFFENSIVE_SKILL) or (
        bu in _DEFENSIVE_GROUPS and au in _OFFENSIVE_SKILL
    ):
        return True
    return False


def POSITION_GROUP_HARD_BLOCKS() -> dict[str, frozenset[str]]:  # noqa: N802
    """Backstop accessor for callers that want the raw hard-block table.

    Computed on call from the source-of-truth frozensets above; returned dict is a
    fresh build and is not cached. Caller-name kept uppercase per spec naming.
    """
    blocks: dict[str, frozenset[str]] = {}
    universe = _OL_FAMILY | _SPECIAL_TEAMS | _DEFENSIVE_GROUPS | _OFFENSIVE_SKILL | {"QB"}
    for a in universe:
        bs = frozenset(b for b in universe if is_position_pair_hard_blocked(a, b))
        if bs:
            blocks[a] = bs
    return blocks


@dataclass(frozen=True)
class MatchCandidate:
    """Spec §5.7: review-queue audit-trail per candidate."""

    target_prospect_uuid: str
    match_score: float
    score_breakdown: dict[str, float]
    risk_flags: tuple[str, ...]
    raw_match_features: dict[str, Any]
    matcher_algorithm_version: str


def _name_base(incoming_name: str, existing_name: str) -> tuple[float, float, float]:
    jw = jellyfish.jaro_winkler_similarity(incoming_name, existing_name)
    token = _rf_fuzz.token_set_ratio(incoming_name, existing_name) / 100.0
    base = JW_WEIGHT * jw + TOKEN_SET_WEIGHT * token
    return jw, token, base


def score_candidate(
    incoming: NormalizedCollegeProspectRow,
    existing: RegistryEntry,
) -> MatchCandidate:
    """Compute a candidate score for incoming vs existing. Discovery-only."""
    jw, token, name_base = _name_base(incoming.normalized_name, existing.normalized_name)
    raw_features = {
        "prospect_name": incoming.full_name,
        "position": incoming.position,
        "school": incoming.current_school,
        "draft_class": incoming.draft_class,
    }

    if incoming.draft_class != existing.draft_class:
        breakdown = {
            "jw_score": jw,
            "token_set_score": token,
            "name_base": name_base,
            "position_bonus": 0.0,
            "school_bonus": 0.0,
            "final": 0.0,
        }
        return MatchCandidate(
            target_prospect_uuid=existing.prospect_uuid,
            match_score=0.0,
            score_breakdown=breakdown,
            risk_flags=("class_boundary_blocked",),
            raw_match_features=raw_features,
            matcher_algorithm_version=MATCHER_ALGORITHM_VERSION,
        )

    position_bonus = POSITION_BONUS if incoming.position_group == existing.position_group else 0.0
    school_bonus = 0.0
    if incoming.current_school and (
        incoming.current_school == existing.current_school
        or incoming.current_school in existing.prior_schools
        or existing.current_school in incoming.prior_schools
    ):
        school_bonus = SCHOOL_BONUS

    final = max(0.0, min(1.0, name_base + position_bonus + school_bonus))
    breakdown = {
        "jw_score": jw,
        "token_set_score": token,
        "name_base": name_base,
        "position_bonus": position_bonus,
        "school_bonus": school_bonus,
        "final": final,
    }
    return MatchCandidate(
        target_prospect_uuid=existing.prospect_uuid,
        match_score=final,
        score_breakdown=breakdown,
        risk_flags=(),
        raw_match_features=raw_features,
        matcher_algorithm_version=MATCHER_ALGORITHM_VERSION,
    )


def surface_review_candidates(
    incoming: NormalizedCollegeProspectRow,
    registry: dict[str, RegistryEntry],
) -> list[MatchCandidate]:
    """Spec §5.4: emit top-3 above MIN_CANDIDATE_SCORE; attach low_confidence /
    ambiguous_near_tie / common_name flags; apply whitelist + hard-block per spec §5.3.

    Cross-position whitelist transitions surface only at final_score >= CROSS_POSITION_THRESHOLD
    and carry cross_position_group + position_transition_allowed flags. Hard-blocked pairs
    are filtered out before scoring.
    """
    scored: list[MatchCandidate] = []
    for existing in registry.values():
        if is_position_pair_hard_blocked(incoming.position_group, existing.position_group):
            continue
        cand = score_candidate(incoming, existing)
        same_group = incoming.position_group.upper() == existing.position_group.upper()
        if not same_group:
            if not is_position_pair_whitelisted(
                incoming.position_group, existing.position_group
            ):
                continue
            if cand.match_score < CROSS_POSITION_THRESHOLD:
                continue
            cand = MatchCandidate(
                target_prospect_uuid=cand.target_prospect_uuid,
                match_score=cand.match_score,
                score_breakdown=cand.score_breakdown,
                risk_flags=cand.risk_flags
                + ("cross_position_group", "position_transition_allowed"),
                raw_match_features=cand.raw_match_features,
                matcher_algorithm_version=cand.matcher_algorithm_version,
            )
        scored.append(cand)

    above = sorted(
        (c for c in scored if c.match_score >= MIN_CANDIDATE_SCORE),
        key=lambda c: c.match_score,
        reverse=True,
    )
    top = above[:TOP_K_CANDIDATES]
    if not top:
        return []

    flagged: list[MatchCandidate] = []
    margin: Optional[float] = None
    if len(top) >= 2:
        margin = top[0].match_score - top[1].match_score
    for idx, cand in enumerate(top):
        flags = list(cand.risk_flags)
        if LOW_CONFIDENCE_LOWER <= cand.match_score < LOW_CONFIDENCE_UPPER:
            flags.append("low_confidence")
        if idx == 0 and margin is not None and margin <= AMBIGUOUS_NEAR_TIE_MARGIN:
            flags.append("ambiguous_near_tie")
            flags.append("common_name")
        flagged.append(
            MatchCandidate(
                target_prospect_uuid=cand.target_prospect_uuid,
                match_score=cand.match_score,
                score_breakdown=cand.score_breakdown,
                risk_flags=tuple(flags),
                raw_match_features=cand.raw_match_features,
                matcher_algorithm_version=cand.matcher_algorithm_version,
            )
        )
    return flagged
