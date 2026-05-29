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
    projected_pick_median: Optional[int] = None
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
        median_val = int(_median(pick_nos))
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
