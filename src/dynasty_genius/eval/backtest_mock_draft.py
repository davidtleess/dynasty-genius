"""Subsystem 4 — Backtest Mock Draft (manual-first harness).

Analytics infrastructure for testing whether NFL mock-draft consensus predicts
realized NFL draft capital. v1 lands Backtest A only; Backtest B is gated on
A clearance by round/position bucket and implemented as an always-abstain stub
per spec §6.1.

Single-module implementation organized in labeled sections:
- Constants & versions
- Snapshot schema (Pydantic 2.x)        (Task 5)
- Canonical content_hash + snapshot_id  (Task 5)
- Snapshot ingestion + coverage matrix  (Task 6)
- parse_status + draft_date sourcing    (Task 7)
- ProspectConsensus + abstention gates  (Task 8)
- Bridge join + RealizedOutcome         (Task 9)
- 6 metrics                             (Task 10)
- backtest_b_gate_status + synthetic    (Task 11)
- Artifact writer + run_backtest_a      (Task 12)
- B-shaped abstain library function     (Task 13)

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

# ======================================================================
# Constants & versions
# ======================================================================

METRIC_VERSION: str = "s4_metrics_v1"
AGGREGATION_VERSION: str = "s4_provisional_consensus_v1"
GATE_VERSION: str = "s4_b_gate_thresholds_v1"


# ======================================================================
# Snapshot schema (Pydantic 2.x) — spec §4.1
# ======================================================================


class MockSnapshotPick(BaseModel):
    """A single pick in a mock snapshot (spec §4.1)."""

    model_config = ConfigDict(extra="forbid")

    pick_no: int
    prospect_uuid: str
    note: Optional[str] = None


class MockSnapshotMetadata(BaseModel):
    """Sidecar metadata required on every snapshot (spec §4.1 + reconciliation §41)."""

    model_config = ConfigDict(extra="forbid")

    source_url: str
    source_label: str
    analyst: Optional[str] = None
    mock_version: str
    published_date: str
    fetched_at: str
    content_hash: str
    parser_version: str
    parse_status: Literal["complete", "partial", "untrusted"]
    draft_year: int


class MockSnapshot(BaseModel):
    """A complete mock snapshot (metadata + picks)."""

    model_config = ConfigDict(extra="forbid")

    metadata: MockSnapshotMetadata
    picks: list[MockSnapshotPick]


# ======================================================================
# Canonical content_hash + snapshot_id derivation (spec §4.1 + §4.4)
# ======================================================================


def compute_canonical_content_hash(picks: list[MockSnapshotPick]) -> str:
    """Deterministic SHA-256 of the picks payload, stable across:
    - input list order (sorts by pick_no ascending after duplicate detection)
    - field order within a pick (sort_keys=True per pick)

    Spec §4.1 + Codex round-2 note: sort by pick_no ascending after
    within-snapshot duplicate validation; serialize each pick with sort_keys=True;
    concatenate with newlines.

    NOTE: this function does NOT perform within-snapshot duplicate detection
    (that's part of ingestion validation in Task 6). Callers passing duplicates
    will get a hash that reflects whatever order they sorted into; for the
    canonical hash to be meaningful the caller must validate uniqueness first.
    """
    sorted_picks = sorted(picks, key=lambda p: p.pick_no)
    serialized = "".join(
        json.dumps(
            p.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        for p in sorted_picks
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def derive_snapshot_id(metadata: MockSnapshotMetadata) -> str:
    """Spec §4.4: derived snapshot_id = SHA-256 of pipe-joined
    (source_label || analyst || published_date || mock_version || content_hash).

    Reports reference snapshots by this ID — path-independent and stable
    across machine/path changes.
    """
    analyst = metadata.analyst or ""
    payload = (
        f"{metadata.source_label}|{analyst}|{metadata.published_date}"
        f"|{metadata.mock_version}|{metadata.content_hash}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ======================================================================
# Snapshot ingestion + coverage matrix (spec §4.3, §4.5)
# ======================================================================

from dataclasses import dataclass  # noqa: E402  (grouped with ingestion)
from pathlib import Path  # noqa: E402

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    CollegeProspectRegistry,
)


@dataclass(frozen=True)
class NormalizedPick:
    """A pick after ingestion + identity resolution. Carries both the
    ``original_prospect_uuid`` (as seen in the raw snapshot) and the
    ``resolved_prospect_uuid`` (after following any S3 redirects). Per spec
    §4.3 rule 3, ``redirect_applied`` is True only when the original differs
    from the resolved."""

    pick_no: int
    original_prospect_uuid: str
    resolved_prospect_uuid: str
    redirect_applied: bool
    snapshot_id: str
    metadata_tuple_key: str
    published_date: str
    source_label: str


def _metadata_tuple_key(metadata: MockSnapshotMetadata) -> str:
    """Same shape as Codex's expected ``"source_label|analyst|published_date|mock_version"``
    (no content_hash; that's the dimension we vary across collisions)."""
    analyst = metadata.analyst or ""
    return f"{metadata.source_label}|{analyst}|{metadata.published_date}|{metadata.mock_version}"


def _resolve_identity(
    prospect_uuid: str,
    s3_registry: CollegeProspectRegistry,
) -> tuple[Optional[str], bool]:
    """Returns (resolved_uuid_or_None, redirect_applied).
    - Unknown / provisional / deprecated-to-non-confirmed → (None, False)
    - Confirmed → (prospect_uuid, False)
    - Deprecated with confirmed survivor → (survivor_uuid, True)
    """
    entry = s3_registry.entries.get(prospect_uuid)
    if entry is None:
        return None, False
    if entry.verification_status == "confirmed":
        return prospect_uuid, False
    if (
        entry.verification_status == "deprecated"
        and entry.merged_into_prospect_uuid
    ):
        survivor = s3_registry.entries.get(entry.merged_into_prospect_uuid)
        if survivor is not None and survivor.verification_status == "confirmed":
            return survivor.prospect_uuid, True
        return None, False
    # provisional, deprecated-without-redirect, or anything else
    return None, False


_HIGH_REDIRECT_RATE_THRESHOLD: float = 0.05  # >5% of picks needed redirect (spec §4.3 rule 3)


def ingest_snapshots(
    snapshots_dir: Path,
    *,
    s3_registry: CollegeProspectRegistry,
    draft_date: str,
    include_untrusted: bool = False,
) -> tuple[list[NormalizedPick], dict]:
    """Spec §4.3 + §4.5: read all snapshots in ``snapshots_dir`` (recursive),
    apply ingestion validation, identity resolution, and emit a coverage matrix.

    Discovery: any ``*.json`` under ``snapshots_dir`` (recursive).
    Validation pipeline per snapshot:
      1. Pydantic schema (``extra="forbid"``); on failure → skip + count in total
      2. Within-snapshot duplicate pick_no → reject snapshot
      3. Within-snapshot duplicate prospect_uuid → reject snapshot
      4. Strict ``published_date < draft_date`` (leakage gate)
      5. ``parse_status``: ``untrusted`` excluded by default; ``partial`` flagged
      6. Cross-snapshot ``(metadata_tuple_key, content_hash)`` rule:
         - Same tuple + same hash → idempotent (second occurrence skipped)
         - Same tuple + different hash → REJECT later + warning
      7. Per-pick identity resolution via S3 registry; track ``redirect_applied``
         and ``unresolved_picks``

    Returns ``(normalized_picks, coverage_matrix)``.
    """
    coverage = {
        "snapshot_ids_used": [],
        "metadata_tuple_keys_used": [],
        "total_snapshots_found": 0,
        "leakage_excluded_snapshots": 0,
        "untrusted_excluded_snapshots": 0,
        "partial_snapshot_warnings": 0,
        "duplicate_pick_no_rejections": 0,
        "duplicate_prospect_uuid_rejections": 0,
        "content_hash_collisions": 0,
        "snapshots_used": 0,
        "total_picks": 0,
        "redirect_applied": 0,
        "high_redirect_rate_warning": False,
        "unresolved_picks": 0,
        "unresolved_picks_ratio": 0.0,
        "draft_date_used": draft_date,
        "draft_date_source": "explicit",
        "warnings": [],
    }
    normalized_picks: list[NormalizedPick] = []

    # Track which (tuple_key, content_hash) we've already accepted, and which
    # tuple_keys have any accepted hash (for collision detection).
    accepted_pair: set[tuple[str, str]] = set()
    accepted_tuple_keys: dict[str, str] = {}  # tuple_key → accepted content_hash

    # Discover all .json files recursively. Sort by file mtime (older first)
    # so the EARLIER-written snapshot wins under same-tuple-different-hash
    # collision (filesystem write order = ingestion priority). Path as tiebreaker.
    snapshot_paths = sorted(
        snapshots_dir.rglob("*.json"),
        key=lambda p: (p.stat().st_mtime_ns, str(p)),
    )
    for path in snapshot_paths:
        coverage["total_snapshots_found"] += 1

        # Stage 1: schema validation
        try:
            raw = json.loads(path.read_text())
            snapshot = MockSnapshot.model_validate(raw)
        except Exception:
            continue  # schema invalid: counted in total but not used

        # Stage 5: parse_status filter (untrusted)
        if snapshot.metadata.parse_status == "untrusted" and not include_untrusted:
            coverage["untrusted_excluded_snapshots"] += 1
            continue
        if snapshot.metadata.parse_status == "partial":
            coverage["partial_snapshot_warnings"] += 1

        # Stage 2: within-snapshot duplicate pick_no
        pick_nos = [p.pick_no for p in snapshot.picks]
        if len(pick_nos) != len(set(pick_nos)):
            coverage["duplicate_pick_no_rejections"] += 1
            continue

        # Stage 3: within-snapshot duplicate prospect_uuid
        pick_uuids = [p.prospect_uuid for p in snapshot.picks]
        if len(pick_uuids) != len(set(pick_uuids)):
            coverage["duplicate_prospect_uuid_rejections"] += 1
            continue

        # Stage 4: strict leakage gate
        if snapshot.metadata.published_date >= draft_date:
            coverage["leakage_excluded_snapshots"] += 1
            continue

        # Stage 6: cross-snapshot tuple-key + content_hash
        tuple_key = _metadata_tuple_key(snapshot.metadata)
        pair = (tuple_key, snapshot.metadata.content_hash)
        if pair in accepted_pair:
            # Idempotent re-occurrence; skip silently (still counted in total)
            continue
        if (
            tuple_key in accepted_tuple_keys
            and accepted_tuple_keys[tuple_key] != snapshot.metadata.content_hash
        ):
            # Collision: same tuple, different hash → reject this one
            coverage["content_hash_collisions"] += 1
            coverage["warnings"].append(
                f"content_hash_collision_warning: tuple_key={tuple_key} "
                f"already had hash={accepted_tuple_keys[tuple_key]}, "
                f"rejected new hash={snapshot.metadata.content_hash}"
            )
            continue

        # Snapshot accepted
        accepted_pair.add(pair)
        accepted_tuple_keys[tuple_key] = snapshot.metadata.content_hash
        coverage["snapshots_used"] += 1
        snapshot_id = derive_snapshot_id(snapshot.metadata)
        coverage["snapshot_ids_used"].append(snapshot_id)
        coverage["metadata_tuple_keys_used"].append(tuple_key)

        # Stage 7: per-pick identity resolution
        for pick in snapshot.picks:
            coverage["total_picks"] += 1
            resolved, redirect_applied = _resolve_identity(pick.prospect_uuid, s3_registry)
            if resolved is None:
                coverage["unresolved_picks"] += 1
                continue
            if redirect_applied:
                coverage["redirect_applied"] += 1
            normalized_picks.append(NormalizedPick(
                pick_no=pick.pick_no,
                original_prospect_uuid=pick.prospect_uuid,
                resolved_prospect_uuid=resolved,
                redirect_applied=redirect_applied,
                snapshot_id=snapshot_id,
                metadata_tuple_key=tuple_key,
                published_date=snapshot.metadata.published_date,
                source_label=snapshot.metadata.source_label,
            ))

    # Compute derived coverage fields
    if coverage["total_picks"] > 0:
        coverage["unresolved_picks_ratio"] = (
            coverage["unresolved_picks"] / coverage["total_picks"]
        )
        redirect_rate = coverage["redirect_applied"] / coverage["total_picks"]
        if redirect_rate > _HIGH_REDIRECT_RATE_THRESHOLD:
            coverage["high_redirect_rate_warning"] = True

    return normalized_picks, coverage
