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
