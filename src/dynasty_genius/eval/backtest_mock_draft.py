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
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

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


def resolve_draft_date(
    draft_year: int,
    *,
    override_date: Optional[str] = None,
    override_reason: Optional[str] = None,
) -> tuple[str, str]:
    """Spec §4.6: returns ``(draft_date, draft_date_source)``.

    Default: fetch from nflreadr. ``source = "nflreadr.draft_picks"``.

    Override: BOTH ``override_date`` AND ``override_reason`` MUST be supplied;
    if either is provided alone, raises ``ValueError`` (no silent override).
    When both are supplied, returns ``(override_date, "override:<reason>")``.
    """
    if override_date is not None or override_reason is not None:
        if override_date is None or override_reason is None:
            raise ValueError(
                "resolve_draft_date override requires BOTH override_date AND "
                "override_reason (spec §4.6; no silent override)"
            )
        return override_date, f"override:{override_reason}"

    import nflreadpy
    df = nflreadpy.load_draft_picks([draft_year])
    records = df.to_pandas().to_dict("records")
    if not records:
        raise ValueError(
            f"resolve_draft_date: nflreadr returned no rows for season {draft_year}"
        )
    return records[0]["draft_date"], "nflreadr.draft_picks"


def ingest_snapshots(
    snapshots_dir: Path,
    *,
    s3_registry: CollegeProspectRegistry,
    draft_date: Optional[str] = None,
    include_untrusted: bool = False,
    override_date: Optional[str] = None,
    override_reason: Optional[str] = None,
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
    # Resolve draft_date + source (spec §4.6, Task 7)
    if draft_date is not None:
        resolved_draft_date, resolved_source = draft_date, "explicit"
    elif override_date is not None or override_reason is not None:
        resolved_draft_date, resolved_source = resolve_draft_date(
            draft_year=0,  # unused for override branch
            override_date=override_date,
            override_reason=override_reason,
        )
    else:
        # Default: derive draft_year from first valid snapshot's metadata, fetch from nflreadr
        derived_year: Optional[int] = None
        for path in sorted(snapshots_dir.rglob("*.json"), key=lambda p: str(p)):
            try:
                meta_raw = json.loads(path.read_text()).get("metadata", {})
                derived_year = meta_raw.get("draft_year")
                if derived_year is not None:
                    break
            except Exception:
                continue
        if derived_year is None:
            resolved_draft_date, resolved_source = "9999-12-31", "no_snapshots"
        else:
            resolved_draft_date, resolved_source = resolve_draft_date(derived_year)

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
        "draft_date_used": resolved_draft_date,
        "draft_date_source": resolved_source,
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
        if snapshot.metadata.published_date >= resolved_draft_date:
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


# ======================================================================
# ProspectConsensus + abstention gates (spec §5.2, §5.3)
# ======================================================================

from datetime import date as _date  # noqa: E402  (grouped with [Task 8])
from statistics import median as _median  # noqa: E402
from statistics import quantiles as _quantiles  # noqa: E402


class ProspectConsensus(BaseModel):
    """Per-prospect consensus across normalized picks (spec §5.2).

    Abstention tiers per spec §5.3:
    - ``abstain``: n_sources < 3; no projection emitted (median/iqr/min/max = None)
    - ``round_tier_only``: 3-4 sources, OR >=5 sources with IQR > dispersion_threshold
    - ``exact_pick``: >=5 sources AND IQR <= dispersion_threshold (internal diagnostic only;
      per §5.3 must never reach David-facing surfaces)
    """

    model_config = ConfigDict(extra="forbid")

    prospect_uuid: str
    projected_pick_median: Optional[float] = None  # half-picks preserved (no truncation); spec §5.2 amended 2026-05-28
    projected_pick_iqr: Optional[float] = None
    projected_pick_min: Optional[int] = None
    projected_pick_max: Optional[int] = None
    n_sources: int
    n_unique_analysts: int
    snapshot_ids_used: list[str]
    staleness_days: Optional[float] = None
    abstention_tier: Literal["abstain", "round_tier_only", "exact_pick"]
    abstention_reason: Optional[str] = None


def _analyst_from_metadata_tuple_key(tuple_key: str) -> str:
    """Parse analyst from ``source_label|analyst|published_date|mock_version``
    (the canonical format produced by ``_metadata_tuple_key``)."""
    parts = tuple_key.split("|")
    return parts[1] if len(parts) >= 2 else ""


def _whole_day_staleness(draft_date: str, most_recent_published: str) -> float:
    """Whole calendar days between most-recent snapshot and draft_date,
    emitted as float per the §5.2 schema (whole-day integer value as float)."""
    delta = _date.fromisoformat(draft_date) - _date.fromisoformat(most_recent_published)
    return float(delta.days)


def aggregate_per_prospect(
    normalized_picks: list[NormalizedPick],
    draft_date: str,
    dispersion_threshold: float = 6,
) -> dict[str, ProspectConsensus]:
    """Group normalized picks by resolved prospect, compute consensus, apply §5.3 tiers.

    Returns ``{prospect_uuid: ProspectConsensus}``. Empty input → empty dict.
    """
    if not normalized_picks:
        return {}

    by_uuid: dict[str, list[NormalizedPick]] = {}
    for pick in normalized_picks:
        by_uuid.setdefault(pick.resolved_prospect_uuid, []).append(pick)

    result: dict[str, ProspectConsensus] = {}
    for uuid, picks in by_uuid.items():
        sources = {p.source_label for p in picks}
        analysts = {_analyst_from_metadata_tuple_key(p.metadata_tuple_key) for p in picks}
        snapshot_ids = sorted({p.snapshot_id for p in picks})
        n_sources = len(sources)
        n_unique_analysts = len(analysts)
        most_recent_published = max(p.published_date for p in picks)
        staleness = _whole_day_staleness(draft_date, most_recent_published)

        pick_nos = [p.pick_no for p in picks]
        median_val = float(_median(pick_nos))
        min_val = min(pick_nos)
        max_val = max(pick_nos)
        if len(pick_nos) >= 2:
            # IQR via statistics.quantiles default ('exclusive'); bump AGGREGATION_VERSION
            # if the method choice ever changes (replay outputs are sensitive to this).
            q1, _q2, q3 = _quantiles(pick_nos, n=4)
            iqr_val = float(q3 - q1)
        else:
            iqr_val = 0.0

        if n_sources < 3:
            tier: Literal["abstain", "round_tier_only", "exact_pick"] = "abstain"
            consensus = ProspectConsensus(
                prospect_uuid=uuid,
                projected_pick_median=None,
                projected_pick_iqr=None,
                projected_pick_min=None,
                projected_pick_max=None,
                n_sources=n_sources,
                n_unique_analysts=n_unique_analysts,
                snapshot_ids_used=snapshot_ids,
                staleness_days=staleness,
                abstention_tier=tier,
                abstention_reason=(
                    f"abstain: n_sources={n_sources} below minimum (>=3 required)"
                ),
            )
        elif n_sources < 5:
            tier = "round_tier_only"
            consensus = ProspectConsensus(
                prospect_uuid=uuid,
                projected_pick_median=median_val,
                projected_pick_iqr=iqr_val,
                projected_pick_min=min_val,
                projected_pick_max=max_val,
                n_sources=n_sources,
                n_unique_analysts=n_unique_analysts,
                snapshot_ids_used=snapshot_ids,
                staleness_days=staleness,
                abstention_tier=tier,
                abstention_reason=(
                    f"round_tier_only: n_sources={n_sources} in [3,4]; "
                    "exact-pick claim not permitted per spec §5.3"
                ),
            )
        else:
            if iqr_val <= dispersion_threshold:
                tier = "exact_pick"
                reason: Optional[str] = None
            else:
                tier = "round_tier_only"
                reason = (
                    f"round_tier_only: IQR={iqr_val:.2f} exceeds "
                    f"dispersion_threshold={dispersion_threshold}"
                )
            consensus = ProspectConsensus(
                prospect_uuid=uuid,
                projected_pick_median=median_val,
                projected_pick_iqr=iqr_val,
                projected_pick_min=min_val,
                projected_pick_max=max_val,
                n_sources=n_sources,
                n_unique_analysts=n_unique_analysts,
                snapshot_ids_used=snapshot_ids,
                staleness_days=staleness,
                abstention_tier=tier,
                abstention_reason=reason,
            )

        result[uuid] = consensus

    return result


# ======================================================================
# Bridge join + RealizedOutcome + JoinDiagnostics (spec §5.1 stage 3, §11.5)
# ======================================================================

from src.dynasty_genius.identity.prospect_nfl_bridge import (  # noqa: E402
    CollegeProspectBridge,
    NflTruthRow,
    ProspectNflBridgeEntry,
)

TEAM_CODE_NORMALIZATION_VERSION: str = "s4_team_norm_v1"

# Documented relocation/abbreviation equivalence classes. Each raw code maps to a
# single canonical token so a franchise's historical and current codes compare
# equal. Bump TEAM_CODE_NORMALIZATION_VERSION if these classes ever change.
_TEAM_CODE_EQUIVALENCE: dict[str, str] = {
    # Raiders — Oakland / Las Vegas
    "OAK": "LV", "LV": "LV", "LVR": "LV", "LAS": "LV",
    # Chargers — San Diego / Los Angeles
    "SD": "LAC", "SDG": "LAC", "LAC": "LAC",
    # Rams — St. Louis / Los Angeles
    "STL": "LAR", "LA": "LAR", "LAR": "LAR", "RAM": "LAR",
    # Washington
    "WAS": "WSH", "WSH": "WSH",
}


def normalize_team_code(raw_code: str) -> str:
    """Normalize an NFL team code to a canonical token (spec §11.5 #6).

    Strips surrounding whitespace, upper-cases, then collapses documented
    relocation/abbreviation equivalence classes (OAK/LVR, SDG/LAC, LAR/LA,
    WAS/WSH) so a franchise's historical and current codes compare equal.
    Unknown codes pass through normalized (strip + upper) but unmapped.
    """
    code = raw_code.strip().upper()
    return _TEAM_CODE_EQUIVALENCE.get(code, code)


class RealizedOutcome(BaseModel):
    """Realized NFL draft outcome joined to a prospect (spec §5.1 stage 3, §11.5).

    Pure-functional product of ``join_bridge_to_realized``. Carries the bridge's
    recorded draft capital plus a per-prospect ``warnings`` surface and the
    stale/unbridged flags. Runner-level concerns (review-queue writes, acceptance
    aggregation, metric skips) are Task 10/12; this object never touches the
    filesystem.
    """

    model_config = ConfigDict(extra="forbid")

    prospect_uuid: str
    gsis_id: Optional[str] = None
    pfr_id: Optional[str] = None
    draft_year: Optional[int] = None
    draft_pick_no: Optional[int] = None
    draft_round: Optional[int] = None
    nfl_team: Optional[str] = None
    udfa: bool = False
    unbridged_prospect: bool = False
    bridge_stale_warning: bool = False
    warnings: list[str] = Field(default_factory=list)
    evidence_full_name: Optional[str] = None
    evidence_position: Optional[str] = None
    evidence_college: Optional[str] = None


class JoinDiagnostics(BaseModel):
    """Run-level join diagnostics (spec §11.5).

    ``hard_block_reasons`` strings ARE the canonical ``acceptance_criteria_failed``
    tokens the Task 12 runner unions directly — there is no warning→failure
    mapping. ``warnings`` on each ``RealizedOutcome`` is the human-readable
    per-prospect surface; this payload is the machine-actionable runner gate.
    """

    model_config = ConfigDict(extra="forbid")

    hard_block_reasons: list[str] = Field(default_factory=list)
    review_queue_payload: list[dict] = Field(default_factory=list)
    duplicate_gsis_ids_detected: list[str] = Field(default_factory=list)
    wrong_year_truth_collisions: list[str] = Field(default_factory=list)
    evidence_incomplete_uuids: list[str] = Field(default_factory=list)


def join_bridge_to_realized(
    consensuses: list[ProspectConsensus],
    bridge: CollegeProspectBridge,
    nflreadr_current: list[NflTruthRow],
) -> tuple[list[tuple[ProspectConsensus, RealizedOutcome]], JoinDiagnostics]:
    """Join prospect consensus rows to realized NFL draft truth (§5.1 stage 3, §11.5).

    Pure function — performs NO filesystem writes. Returns the per-prospect
    ``(consensus, outcome)`` pairs plus a run-level ``JoinDiagnostics``.

    Fail-closed truth-lookup precedence (§11.5), per drafted bridge entry:
      1. duplicate ``gsis_id`` in truth  → hard block; refuse comparison.
      2. truth row absent                → stale warning (disappearance, not corrupt).
      3. truth ``draft_year`` mismatch   → hard block (wrong-year collision).
      4. single matching row             → evidence + pick/round/team divergence.
    Missing drafted-entry evidence is a hard block — the ``gsis_id``-only fallback
    is explicitly disabled. UDFA and unbridged prospects emit non-blocking flags.
    """
    diagnostics = JoinDiagnostics()

    # One decided bridge entry per prospect_uuid.
    entry_by_uuid: dict[str, ProspectNflBridgeEntry] = {
        e.prospect_uuid: e for e in bridge.entries
    }

    # gsis_id -> all truth rows carrying it. Duplicates are preserved at build
    # time so step 1 can fail closed rather than silently last-row-wins.
    truth_by_gsis: dict[str, list[NflTruthRow]] = {}
    for row in nflreadr_current:
        truth_by_gsis.setdefault(row.gsis_id, []).append(row)

    pairs: list[tuple[ProspectConsensus, RealizedOutcome]] = []
    for consensus in consensuses:
        uuid = consensus.prospect_uuid
        entry = entry_by_uuid.get(uuid)

        if entry is None:
            # Unbridged — flag only; coverage hard-block is Task 10/12 (§11.5 #5).
            pairs.append(
                (
                    consensus,
                    RealizedOutcome(
                        prospect_uuid=uuid,
                        unbridged_prospect=True,
                        warnings=["unbridged_prospect"],
                    ),
                )
            )
            continue

        if entry.udfa:
            # Explicit UDFA — verified absent from draft truth; clean outcome.
            pairs.append(
                (
                    consensus,
                    RealizedOutcome(
                        prospect_uuid=uuid,
                        draft_year=entry.draft_year,
                        udfa=True,
                    ),
                )
            )
            continue

        warnings: list[str] = []
        bridge_stale = False
        evidence_full_name: Optional[str] = None
        evidence_position: Optional[str] = None
        evidence_college: Optional[str] = None

        gsis_id = entry.gsis_id
        rows = truth_by_gsis.get(gsis_id, []) if gsis_id is not None else []

        if gsis_id is not None and len(rows) >= 2:
            # (1) Duplicate gsis_id — fail closed; refuse current-truth comparison.
            warnings.append("nflreadr_duplicate_gsis_id_warning")
            bridge_stale = True
            diagnostics.duplicate_gsis_ids_detected.append(gsis_id)
            diagnostics.hard_block_reasons.append("nflreadr_duplicate_gsis_id")
        elif gsis_id is None or not rows:
            # (2) Truth disappearance — stale, not a hard block.
            bridge_stale = True
            warnings.append("truth_row_missing")
        elif rows[0].draft_year != entry.draft_year:
            # (3) Wrong-year truth collision — hard conflict; queue for review.
            # A wrong-year mismatch is a major alignment failure, so the bridge's
            # recorded capital is stale vs current truth (consistent with the
            # duplicate-gsis_id branch).
            warnings.append("truth_row_wrong_year_warning")
            bridge_stale = True
            diagnostics.wrong_year_truth_collisions.append(gsis_id)
            diagnostics.hard_block_reasons.append("wrong_year_truth_collision")
            diagnostics.review_queue_payload.append(
                {
                    "prospect_uuid": uuid,
                    "gsis_id": gsis_id,
                    "reason": "wrong_year_truth_collision",
                    "bridge_draft_year": entry.draft_year,
                    "truth_draft_year": rows[0].draft_year,
                }
            )
        elif not entry.evidence_snapshot:
            # (4a) Missing evidence — refuse gsis_id-only fallback (§11.5 #4).
            warnings.append("evidence_snapshot_missing_warning")
            bridge_stale = True
            diagnostics.evidence_incomplete_uuids.append(uuid)
            diagnostics.hard_block_reasons.append("evidence_snapshot_missing")
        else:
            # (4b) Single matching row + evidence present → divergence comparison.
            evidence_full_name = entry.evidence_snapshot.get("full_name")
            evidence_position = entry.evidence_snapshot.get("position")
            evidence_college = entry.evidence_snapshot.get("college")

            truth = rows[0]
            if entry.draft_pick_no != truth.draft_pick_no:
                warnings.append("draft_pick_no_diverged")
                bridge_stale = True
            if entry.draft_round != truth.draft_round:
                warnings.append("draft_round_diverged")
                bridge_stale = True
            if (
                entry.nfl_team is not None
                and truth.nfl_team is not None
                and normalize_team_code(entry.nfl_team)
                != normalize_team_code(truth.nfl_team)
            ):
                warnings.append("nfl_team_diverged")
                bridge_stale = True

        pairs.append(
            (
                consensus,
                RealizedOutcome(
                    prospect_uuid=uuid,
                    gsis_id=entry.gsis_id,
                    pfr_id=entry.pfr_id,
                    draft_year=entry.draft_year,
                    draft_pick_no=entry.draft_pick_no,
                    draft_round=entry.draft_round,
                    nfl_team=entry.nfl_team,
                    udfa=False,
                    unbridged_prospect=False,
                    bridge_stale_warning=bridge_stale,
                    warnings=warnings,
                    evidence_full_name=evidence_full_name,
                    evidence_position=evidence_position,
                    evidence_college=evidence_college,
                ),
            )
        )

    return pairs, diagnostics


# ======================================================================
# Bridge-coverage gate + the 6 metrics (spec §5.4, §11.2)         (Task 10)
# ======================================================================

SKILL_POSITIONS: frozenset[str] = frozenset({"QB", "RB", "WR", "TE"})
DRAFT_PICK_MAX: int = 257  # projected_drafted predicate range [1, 257] (raw median; §5.4)
ROUND_BUCKET_ORDER: list[str] = [
    "R1-early",
    "R1-mid",
    "R1-late",
    "R2",
    "R3",
    "Day3",
    "UDFA",
]
ROUND_BUCKET_ROUNDING_POLICY: str = "round_half_up"


def evaluate_bridge_gates(coverage: dict) -> Optional[list[str]]:
    """§11.2 bridge-coverage hard-block helper.

    Returns ``None`` when all three coverage counts are clear; otherwise returns the
    canonical ``hard_block_reasons`` tokens (order-preserving) that the Task 12 runner
    unions verbatim into ``acceptance_criteria_failed`` (no mapping). When this returns
    non-None, the runner skips metric computation and the artifact ``metrics`` block is
    null.
    """
    reasons: list[str] = []
    if coverage.get("consensus_unbridged_count", 0):
        reasons.append("consensus_unbridged")
    if coverage.get("confirmed_class_unbridged_count", 0):
        reasons.append("confirmed_class_unbridged")
    if coverage.get("orphan_bridges_detected"):
        reasons.append("orphan_bridges_detected")
    return reasons or None


def _round_half_up(median: float) -> int:
    """Round-half-up to an int pick number per §5.4 (`math.floor(x + 0.5)`)."""
    return math.floor(median + 0.5)


def _bucket_from_pick(pick_no: int) -> str:
    """Map an int draft pick to its round bucket (§5.4 buckets table).

    Fail-closed: a pick number < 1 is corrupt data (no schema ge-constraint
    enforces it) and raises ValueError rather than silently classifying it as
    'R1-early'.
    """
    if pick_no < 1:
        raise ValueError(f"invalid draft pick number: {pick_no!r} (must be >= 1)")
    if pick_no <= 10:
        return "R1-early"
    if pick_no <= 21:
        return "R1-mid"
    if pick_no <= 32:
        return "R1-late"
    if pick_no <= 64:
        return "R2"
    if pick_no <= 105:
        return "R3"
    return "Day3"


def _realized_bucket(outcome: RealizedOutcome) -> str:
    """Round bucket for a realized outcome; UDFA / no realized pick → 'UDFA'."""
    if outcome.udfa or outcome.draft_pick_no is None:
        return "UDFA"
    return _bucket_from_pick(outcome.draft_pick_no)


def _is_projected_drafted(consensus: ProspectConsensus) -> bool:
    """Consensus emitted AND raw `projected_pick_median` in [1, 257] (§5.4).

    Predicate is applied to the raw float median (no rounding) per §5.4: a half-pick
    like 32.5 is inside the inclusive range and counts as projected_drafted.
    """
    median = consensus.projected_pick_median
    return median is not None and 1 <= median <= DRAFT_PICK_MAX


def compute_metrics(
    joined_outcomes: list[tuple[ProspectConsensus, RealizedOutcome]],
    n_prospects_total_in_class: int,
    bridge: CollegeProspectBridge,
) -> dict:
    """Compute the 6 §5.4 Backtest-A metrics + per-bucket breakdown + warnings.

    Pure function — no filesystem writes. Each metric enforces its spec §5.4 universe
    exactly. Returns ``{metric_version, metrics, warnings}``; the ``metrics`` block
    carries the 6 named metrics plus ``per_bucket_breakdown`` (every round bucket
    present, in canonical order).
    """
    warnings: list[str] = []

    # drafted-AND-projected-drafted intersection (UDFA excluded) — MAE + weighted error.
    abs_errors: list[float] = []
    weighted_num = 0.0
    weighted_den = 0.0
    for consensus, outcome in joined_outcomes:
        if (
            _is_projected_drafted(consensus)
            and not outcome.udfa
            and outcome.draft_pick_no is not None
        ):
            err = abs(consensus.projected_pick_median - outcome.draft_pick_no)
            weight = 1.0 / outcome.draft_pick_no
            abs_errors.append(err)
            weighted_num += err * weight
            weighted_den += weight
    overall_pick_mae = (sum(abs_errors) / len(abs_errors)) if abs_errors else None
    early_pick_weighted_error = (weighted_num / weighted_den) if weighted_den else None

    # round_bucket_accuracy — all non-abstain consensus prospects.
    scored_rows = [
        (c, o) for c, o in joined_outcomes if c.abstention_tier != "abstain"
    ]
    correct = 0
    for consensus, outcome in scored_rows:
        predicted = _bucket_from_pick(_round_half_up(consensus.projected_pick_median))
        if predicted == _realized_bucket(outcome):
            correct += 1
    round_bucket_accuracy = (correct / len(scored_rows)) if scored_rows else None

    # top_36_skill_recall — |projected_top_36 ∩ realized_top_36| / min(36, |realized|).
    realized_top_36: set[str] = set()
    for entry in bridge.entries:
        if entry.udfa or entry.draft_pick_no is None or entry.draft_pick_no > 36:
            continue
        position = (entry.evidence_snapshot or {}).get("position")
        if position in SKILL_POSITIONS:
            realized_top_36.add(entry.prospect_uuid)
    projected_top_36: set[str] = {
        c.prospect_uuid
        for c, _o in joined_outcomes
        if _is_projected_drafted(c) and _round_half_up(c.projected_pick_median) <= 36
    }
    realized_top_36_count = len(realized_top_36)
    if realized_top_36_count < 36:
        warnings.append("insufficient_truth_coverage")
    denominator = min(36, realized_top_36_count)
    top_36_skill_recall = (
        len(projected_top_36 & realized_top_36) / denominator if denominator else None
    )

    # udfa_false_positive_rate — false_positives / projected_drafted (abstain excluded).
    projected_drafted = [(c, o) for c, o in joined_outcomes if _is_projected_drafted(c)]
    false_positives = sum(1 for _c, o in projected_drafted if o.udfa)
    udfa_false_positive_rate = (
        (false_positives / len(projected_drafted)) if projected_drafted else None
    )

    # coverage_after_abstention — n_scored / n_prospects_total_in_class.
    n_scored = len(scored_rows)
    coverage_after_abstention = (
        (n_scored / n_prospects_total_in_class) if n_prospects_total_in_class else None
    )

    # per-bucket breakdown — every bucket present, canonical order; n_scored excludes abstain.
    per_bucket_breakdown: dict[str, dict] = {
        bucket: {"n_realized": 0, "n_scored": 0} for bucket in ROUND_BUCKET_ORDER
    }
    for consensus, outcome in joined_outcomes:
        bucket = _realized_bucket(outcome)
        per_bucket_breakdown[bucket]["n_realized"] += 1
        if consensus.abstention_tier != "abstain":
            per_bucket_breakdown[bucket]["n_scored"] += 1

    return {
        "metric_version": METRIC_VERSION,
        "metrics": {
            "overall_pick_mae": overall_pick_mae,
            "round_bucket_accuracy": round_bucket_accuracy,
            "top_36_skill_recall": top_36_skill_recall,
            "udfa_false_positive_rate": udfa_false_positive_rate,
            "coverage_after_abstention": coverage_after_abstention,
            "early_pick_weighted_error": early_pick_weighted_error,
            "per_bucket_breakdown": per_bucket_breakdown,
        },
        "warnings": warnings,
    }


# ======================================================================
# backtest_b_gate_status + synthetic hedge + two-tier (§5.5–§5.7)  (Task 11)
# ======================================================================

# Per-(round_bucket) v1 candidate thresholds (§5.5). R3/Day3 always abstain in v1.
B_GATE_BUCKET_THRESHOLDS: dict[str, dict] = {
    "R1-early": {"mae_max": 8.0, "coverage_min": 0.80},
    "R1-mid": {"mae_max": 12.0, "coverage_min": 0.70},
    "R1-late": {"mae_max": 12.0, "coverage_min": 0.70},
    "R2": {"mae_max": 18.0, "coverage_min": 0.60},
    "R3": {"gate_result": "always_abstain"},
    "Day3": {"gate_result": "always_abstain"},
}
# Two-tier bridge top-36 truth coverage (§5.7): v1 evidence-to-evaluate-A vs B's gate.
EVIDENCE_TO_EVALUATE_A_TOP_36_BRIDGE_COVERAGE: float = 0.90
B_GATE_REQUIRED_TRUTH_COVERAGE: float = 1.00


def evaluate_b_gate(
    metrics: dict,
    per_bucket_breakdown: dict,
    *,
    data_mode: str = "real",
    draft_date_source: str = "",
) -> dict:
    """Evaluate Backtest-B gate status per (round_bucket, position) — §5.5–§5.7.

    Pure function — no filesystem writes. ``per_bucket_breakdown`` is
    ``{round_bucket: {position: {"mae": float, "coverage": float}}}``.

    Robustness boundary: this function guards TYPE corruption only — a malformed
    bucket (non-dict), a malformed stat (non-dict), or a non-numeric mae/coverage
    all fail closed (recorded as ``fail`` with nulled stats, never crashing and
    never silently dropped/passed). SEMANTIC validation (coverage in [0, 1],
    mae >= 0, etc.) is the Task 12 producer's responsibility — it computes these
    metrics in-range by construction.

    NOTE — reserved/disconnected inputs (Task 12 owns the data-flow): the
    ``metrics`` parameter is reserved and unused in the v1 gate evaluator, and the
    ``per_bucket_breakdown`` shape this function consumes (per-(bucket, position)
    MAE/coverage) is NOT what ``compute_metrics`` emits (round-level
    ``{n_realized, n_scored}`` counts). The Task 12 runner MUST define/build the
    per-(bucket, position) MAE/coverage mapping and decide whether ``metrics`` is
    wired or formally dropped — do not assume ``compute_metrics`` output flows in
    directly.

    The synthetic safety hedge (§5.6) is applied BEFORE per-bucket evaluation:
    a synthetic ``data_mode`` OR an ``override:``-sourced draft date forces
    ``overall_status="always_abstain_synthetic_data"`` and every per-bucket
    ``gate_result="not_evaluable_synthetic"`` (mae/coverage nulled, schema shape
    preserved) — anti-false-confidence, regardless of metric values. R3/Day3 always
    abstain in v1. Two-tier thresholds (§5.7) are recorded for the future
    Backtest-B implementation but are not active gating in v1.
    """
    is_synthetic = (
        data_mode == "synthetic" or draft_date_source.startswith("override:")
    )

    per_bucket_results: dict[str, dict] = {}
    n_pass = 0
    n_evaluable = 0  # buckets with gate_result in {"pass","fail"}; abstains excluded
    for round_bucket, positions in per_bucket_breakdown.items():
        if not isinstance(positions, dict):
            # Bucket-level malformed structure → fail-closed; never silently
            # dropped (D8). Synthetic still abstains; real-mode counts as a fail
            # so a corrupt bucket can't masquerade as all_pass.
            key = f"{round_bucket}|__malformed__"
            if is_synthetic:
                per_bucket_results[key] = {
                    "gate_result": "not_evaluable_synthetic",
                    "mae": None,
                    "coverage": None,
                }
            else:
                per_bucket_results[key] = {
                    "gate_result": "fail",
                    "mae": None,
                    "coverage": None,
                }
                n_evaluable += 1
            continue
        for position, stats in positions.items():
            key = f"{round_bucket}|{position}"
            # Synthetic hedge is applied FIRST — never inspect per-bucket stat
            # VALUES on a synthetic/override run (anti-false-confidence; a malformed
            # or differently-shaped stats entry must still safely abstain, not crash).
            if is_synthetic:
                per_bucket_results[key] = {
                    "gate_result": "not_evaluable_synthetic",
                    "mae": None,
                    "coverage": None,
                }
                continue
            mae = stats.get("mae") if isinstance(stats, dict) else None
            coverage = stats.get("coverage") if isinstance(stats, dict) else None
            # Type-corruption guard (D9): a present-but-non-numeric mae/coverage
            # cannot be compared against a threshold — coerce to None so it routes
            # to the fail-closed path instead of raising. (Semantic range checks,
            # e.g. coverage in [0,1] / mae >= 0, are the Task 12 producer's job.)
            if not isinstance(mae, (int, float)) or isinstance(mae, bool):
                mae = None
            if not isinstance(coverage, (int, float)) or isinstance(coverage, bool):
                coverage = None
            threshold = B_GATE_BUCKET_THRESHOLDS.get(round_bucket, {})
            if threshold.get("gate_result") == "always_abstain":
                # Structural abstain (R3/Day3 in v1): excluded from the pass/fail
                # rollup, but surfaced here with its input mae/coverage retained.
                gate_result = "always_abstain"
                result_mae, result_coverage = mae, coverage
            elif "mae_max" in threshold and mae is not None and coverage is not None:
                if mae <= threshold["mae_max"] and coverage >= threshold["coverage_min"]:
                    gate_result = "pass"
                else:
                    gate_result = "fail"
                result_mae, result_coverage = mae, coverage
            else:
                # Fail-closed: malformed/incomplete stats or an unknown bucket can
                # NEVER pass; report "fail" with nulled mae/coverage (never silently
                # bypass a checkpoint, never crash).
                gate_result = "fail"
                result_mae, result_coverage = None, None
            per_bucket_results[key] = {
                "gate_result": gate_result,
                "mae": result_mae,
                "coverage": result_coverage,
            }
            if gate_result == "pass":
                n_pass += 1
            if gate_result in ("pass", "fail"):
                n_evaluable += 1

    # overall_status is computed over EVALUABLE buckets only — structural
    # always_abstain buckets do not count as failures (§5.9; anti-conflation).
    if is_synthetic:
        overall_status = "always_abstain_synthetic_data"
    elif not per_bucket_results:
        overall_status = "all_fail"  # empty input fails closed (nothing evaluated)
    elif n_evaluable == 0:
        overall_status = "always_abstain"  # >=1 bucket, all structurally abstained
    elif n_pass == n_evaluable:
        overall_status = "all_pass"
    elif n_pass == 0:
        overall_status = "all_fail"
    else:
        overall_status = "partial"

    return {
        "overall_status": overall_status,
        "per_bucket_results": per_bucket_results,
        "gate_version": GATE_VERSION,
        "thresholds": {
            "evidence_to_evaluate_a_top_36_bridge_coverage": (
                EVIDENCE_TO_EVALUATE_A_TOP_36_BRIDGE_COVERAGE
            ),
            "b_gate_required_truth_coverage": B_GATE_REQUIRED_TRUTH_COVERAGE,
            "bucket_thresholds": {
                bucket: dict(spec)
                for bucket, spec in B_GATE_BUCKET_THRESHOLDS.items()
            },
        },
    }


# ======================================================================
# Backtest-A runner + artifact writer + CLI support (§5.8–§5.9)   (Task 12)
# ======================================================================

MATCHER_ALGORITHM_VERSION: str = "cpr_matcher_v1.0.0"
METRIC_UNIVERSE: str = "tracked_confirmed_prospect_universe"
COHORT_SELECTION_BIAS_CAVEAT: str = (
    "Cohort selection-bias caveat: Backtest-A metrics are computed over the tracked "
    "confirmed prospect universe only (metric_universe="
    "tracked_confirmed_prospect_universe), NOT the full draft class. This is a "
    "cohort-selection bias — results are descriptive of the tracked cohort and must "
    "not be read as full-class predictive accuracy. Per the product constitution's "
    "'Truth over convenience' tenet, the harness reports only what it can verify "
    "rather than an attractive but unsupported full-class claim."
)


class BacktestAResult(BaseModel):
    """Backtest-A run artifact (spec §5.9).

    Pure data product of ``build_backtest_a_result``. ``metrics`` is null whenever a
    hard block fires (metric computation skipped).
    """

    model_config = ConfigDict(extra="forbid")

    metadata: dict
    coverage: dict
    metric_universe: str
    metrics: Optional[dict] = None
    abstention_summary: dict
    backtest_b_gate_status: dict
    warnings: list[str] = Field(default_factory=list)
    cohort_selection_bias_caveat: str
    acceptance_criteria_failed: list[str] = Field(default_factory=list)


class BacktestAInputError(RuntimeError):
    """Raised by ``run_backtest_a`` on missing/empty/malformed inputs (fail loud)."""


def build_b_gate_per_bucket_position_breakdown(
    joined_outcomes: list[tuple[ProspectConsensus, RealizedOutcome]],
) -> dict[str, dict[str, dict]]:
    """Build the per-(round_bucket, position) MAE/coverage structure that
    ``evaluate_b_gate`` consumes — resolving the documented compute_metrics↔
    evaluate_b_gate data-flow (§5.5; the D4 note).

    This is NOT the shape ``compute_metrics`` emits (round-level
    ``{n_realized, n_scored}`` counts). Groups joined outcomes by (realized round
    bucket, evidence position); per group: ``coverage`` = scored / total; ``mae`` =
    mean ``|projected_pick_median - realized_pick_no|`` over scored rows (None when
    no scored rows). Producer-side: finite numeric production is owned here, so
    evaluate_b_gate's type guard never has to.
    """
    groups: dict[tuple[str, str], list[tuple[ProspectConsensus, RealizedOutcome]]] = {}
    for consensus, outcome in joined_outcomes:
        bucket = _realized_bucket(outcome)
        position = outcome.evidence_position or "UNKNOWN"
        groups.setdefault((bucket, position), []).append((consensus, outcome))

    breakdown: dict[str, dict[str, dict]] = {}
    for (bucket, position), rows in groups.items():
        scored = [
            (c, o)
            for c, o in rows
            if c.abstention_tier != "abstain" and c.projected_pick_median is not None
        ]
        coverage = len(scored) / len(rows) if rows else 0.0
        errors = [
            abs(c.projected_pick_median - o.draft_pick_no)
            for c, o in scored
            if o.draft_pick_no is not None
        ]
        mae = sum(errors) / len(errors) if errors else None
        breakdown.setdefault(bucket, {})[position] = {"mae": mae, "coverage": coverage}
    return breakdown


def _abstention_summary(
    joined_outcomes: list[tuple[ProspectConsensus, RealizedOutcome]],
) -> dict[str, int]:
    summary = {"abstain": 0, "round_tier_only": 0, "exact_pick": 0}
    for consensus, _outcome in joined_outcomes:
        if consensus.abstention_tier in summary:
            summary[consensus.abstention_tier] += 1
    return summary


def build_backtest_a_result(
    *,
    run_id: str,
    draft_year: int,
    data_mode: str,
    draft_date: str,
    draft_date_source: str,
    snapshots_coverage: dict,
    bridge_coverage: dict,
    joined_outcomes: list[tuple[ProspectConsensus, RealizedOutcome]],
    join_diagnostics: JoinDiagnostics,
    bridge: CollegeProspectBridge,
    n_prospects_total_in_class: int,
    dispersion_threshold: float = 6,
    bridge_artifact_path: Optional[str] = None,
) -> BacktestAResult:
    """Assemble the Backtest-A artifact model (spec §5.9). Pure — no filesystem.

    ``acceptance_criteria_failed`` = ``JoinDiagnostics.hard_block_reasons`` +
    ``evaluate_bridge_gates(bridge_coverage)`` (canonical tokens, no mapping). When
    any hard block fires, ``metrics`` is null (metric computation skipped). The
    B-gate status is always computed from the per-(bucket, position) breakdown.
    """
    gate_reasons = evaluate_bridge_gates(bridge_coverage) or []
    acceptance_criteria_failed = list(join_diagnostics.hard_block_reasons) + list(
        gate_reasons
    )
    hard_block = bool(acceptance_criteria_failed)

    warnings: list[str] = list(snapshots_coverage.get("warnings", []))

    if hard_block:
        metrics_field: Optional[dict] = None
        metrics_for_gate: dict = {}
    else:
        metrics_result = compute_metrics(
            joined_outcomes, n_prospects_total_in_class, bridge
        )
        metrics_field = metrics_result["metrics"]
        metrics_for_gate = metrics_result
        for warning in metrics_result.get("warnings", []):
            if warning not in warnings:
                warnings.append(warning)

    breakdown = build_b_gate_per_bucket_position_breakdown(joined_outcomes)
    backtest_b_gate_status = evaluate_b_gate(
        metrics_for_gate,
        breakdown,
        data_mode=data_mode,
        draft_date_source=draft_date_source,
    )

    metadata = {
        "run_id": run_id,
        "draft_year": draft_year,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "matcher_algorithm_version": MATCHER_ALGORITHM_VERSION,
        "metric_version": METRIC_VERSION,
        "aggregation_version": AGGREGATION_VERSION,
        "gate_version": GATE_VERSION,
        "round_bucket_rounding_policy": ROUND_BUCKET_ROUNDING_POLICY,
        "team_code_normalization_version": TEAM_CODE_NORMALIZATION_VERSION,
        "within_source_aggregation_applied": False,
        "dispersion_threshold_used": dispersion_threshold,
        "bridge_artifact_path": bridge_artifact_path,
        "draft_date_used": draft_date,
        "draft_date_source": draft_date_source,
        "data_mode": data_mode,
    }

    return BacktestAResult(
        metadata=metadata,
        coverage={**snapshots_coverage, **bridge_coverage},
        metric_universe=METRIC_UNIVERSE,
        metrics=metrics_field,
        abstention_summary=_abstention_summary(joined_outcomes),
        backtest_b_gate_status=backtest_b_gate_status,
        warnings=warnings,
        cohort_selection_bias_caveat=COHORT_SELECTION_BIAS_CAVEAT,
        acceptance_criteria_failed=acceptance_criteria_failed,
    )


def _atomic_write_json(payload, path: Path) -> None:
    """Write JSON to ``path`` atomically (temp file + ``os.replace``)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def write_review_queue_from_join_diagnostics(
    diagnostics: JoinDiagnostics, queue_path: Path
) -> None:
    """Atomically write ``JoinDiagnostics.review_queue_payload`` to ``queue_path`` (§11.2)."""
    _atomic_write_json(diagnostics.review_queue_payload, Path(queue_path))


def write_backtest_a_artifact(result: BacktestAResult, *, output_root: Path) -> Path:
    """Write the artifact to ``<output_root>/<run_id>/backtest_a_result.json``.

    Creates the run directory and refuses a duplicate run_id (``FileExistsError``)
    so a completed run is never silently overwritten.
    """
    run_id = result.metadata["run_id"]
    artifact_path = Path(output_root) / run_id / "backtest_a_result.json"
    if artifact_path.exists():
        raise FileExistsError(
            f"backtest_a artifact already exists for run_id {run_id!r}: {artifact_path}"
        )
    _atomic_write_json(result.model_dump(mode="json"), artifact_path)
    return artifact_path


def _find_bridge_artifact(identity_dir: Path, draft_year: int) -> Optional[Path]:
    for candidate in (
        Path(identity_dir) / f"prospect_to_nfl_bridge_{draft_year}.json",
        Path(identity_dir) / "prospect_nfl_bridge.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_nflreadr_truth(draft_year: int, *, data_mode: str) -> list[NflTruthRow]:
    """Load realized NFL draft truth rows for the join (v1 SEAM).

    Returns an empty truth set in v1: the real nflreadr draft-pick → NflTruthRow
    mapping (column mapping + synthetic-vs-real sourcing) is a separate increment
    with its own RED contract. Because no truth is loaded, ``run_backtest_a`` FAILS
    CLOSED in real mode (surfaces ``nflreadr_truth_unavailable`` → metrics null) so
    no unverified metrics are ever presented as nflreadr-verified — never depending
    on guessed nflreadr columns. Out-of-scope-by-contract per the Task 12
    falsification matrix; owner: a follow-up truth-loader increment.
    """
    return []


def _compute_bridge_coverage(
    joined_outcomes: list[tuple[ProspectConsensus, RealizedOutcome]],
) -> dict:
    """Derive the §11.2 bridge-coverage counts from joined outcomes (v1 seam).

    ``consensus_unbridged_count`` is derived from per-outcome flags;
    ``confirmed_class_unbridged_count`` and ``orphan_bridges_detected`` require the
    S3 confirmed-class universe and are produced by the same follow-up increment as
    the truth loader (defaulted here).
    """
    return {
        "consensus_unbridged_count": sum(
            1 for _c, o in joined_outcomes if o.unbridged_prospect
        ),
        "confirmed_class_unbridged_count": 0,
        "orphan_bridges_detected": [],
    }


def run_backtest_a(
    *,
    snapshots_dir: Path,
    identity_dir: Path,
    draft_year: int,
    run_id: str,
    output_root: Path,
    override_draft_date: Optional[str] = None,
    override_reason: Optional[str] = None,
    include_untrusted: bool = False,
    dispersion_threshold: float = 6,
) -> BacktestAResult:
    """Orchestrate the Backtest-A pipeline and write the artifact (§5.9).

    Fail-loud input validation, in order: (1) override draft-date and reason must be
    supplied together (§5.6 audit trail); (2) the snapshots dir must exist and be
    non-empty; (3) the identity bridge artifact must be present; (4) each snapshot
    file must be valid JSON. Then ingest → aggregate → join → build → write. The
    nflreadr truth join uses the documented ``_load_nflreadr_truth`` v1 seam.
    """
    from src.dynasty_genius.identity.college_prospect_identity import load_registry
    from src.dynasty_genius.identity.prospect_nfl_bridge import load_bridge

    snapshots_dir = Path(snapshots_dir)
    identity_dir = Path(identity_dir)

    # (1) Override provenance: both-or-neither (loud, auditable; §5.6).
    if (override_draft_date is None) != (override_reason is None):
        raise BacktestAInputError(
            "override draft date and override reason must be provided together "
            "(both or neither) for a loud, auditable override"
        )

    # (2) Snapshots dir present and non-empty. Recursive discovery to match
    # ingest_snapshots' own recursive (rglob) discovery (F3).
    snapshot_files = (
        sorted(snapshots_dir.rglob("*.json")) if snapshots_dir.is_dir() else []
    )
    if not snapshot_files:
        raise BacktestAInputError(f"snapshots dir is missing or empty: {snapshots_dir}")

    # (3) Identity bridge artifact present.
    bridge_path = _find_bridge_artifact(identity_dir, draft_year)
    if bridge_path is None:
        raise BacktestAInputError(
            f"identity bridge artifact not found under {identity_dir}"
        )

    # (4) Each snapshot file must be valid JSON (fail loud before ingestion).
    for snapshot_file in snapshot_files:
        try:
            json.loads(snapshot_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BacktestAInputError(
                f"malformed snapshot JSON in {snapshot_file.name}: {exc}"
            ) from exc

    # (5) Orchestrate. An override draft date marks the run synthetic.
    data_mode = "synthetic" if override_draft_date is not None else "real"
    draft_date_source = (
        f"override:{override_reason}"
        if override_reason is not None
        else "nflreadr.draft_picks"
    )

    bridge = load_bridge(bridge_path)
    s3_registry = load_registry(identity_dir / "college_prospect_registry.json")
    normalized_picks, snapshots_coverage = ingest_snapshots(
        snapshots_dir,
        s3_registry=s3_registry,
        draft_date=override_draft_date,
        include_untrusted=include_untrusted,
        override_date=override_draft_date,
        override_reason=override_reason,
    )
    # Resolve the draft date from ingestion (real mode derives it from nflreadr)
    # before aggregation — never pass an empty string to date parsing (F2).
    resolved_draft_date = (
        override_draft_date or snapshots_coverage.get("draft_date_used") or ""
    )
    consensus_map = aggregate_per_prospect(
        normalized_picks,
        draft_date=resolved_draft_date,
        dispersion_threshold=dispersion_threshold,
    )
    truth_rows = _load_nflreadr_truth(draft_year, data_mode=data_mode)
    pairs, diagnostics = join_bridge_to_realized(
        list(consensus_map.values()), bridge, truth_rows
    )

    # Fail closed when real-mode nflreadr truth is unavailable (F1; anti-false-
    # confidence): without verified truth, metrics must not be presented as
    # nflreadr-verified. Surfaces a canonical token so metrics is nulled.
    if data_mode == "real" and not truth_rows:
        if "nflreadr_truth_unavailable" not in diagnostics.hard_block_reasons:
            diagnostics.hard_block_reasons.append("nflreadr_truth_unavailable")

    result = build_backtest_a_result(
        run_id=run_id,
        draft_year=draft_year,
        data_mode=data_mode,
        draft_date=resolved_draft_date,
        draft_date_source=draft_date_source,
        snapshots_coverage=snapshots_coverage,
        bridge_coverage=_compute_bridge_coverage(pairs),
        joined_outcomes=pairs,
        join_diagnostics=diagnostics,
        bridge=bridge,
        n_prospects_total_in_class=len(consensus_map),
        dispersion_threshold=dispersion_threshold,
        bridge_artifact_path=str(bridge_path),
    )

    if diagnostics.review_queue_payload:
        write_review_queue_from_join_diagnostics(
            diagnostics, Path(output_root) / run_id / "review_queue.json"
        )
    write_backtest_a_artifact(result, output_root=Path(output_root))
    return result
