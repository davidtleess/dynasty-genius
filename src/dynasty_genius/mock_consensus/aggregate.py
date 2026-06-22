"""S1 aggregation + analyst abstention policy + U4 gate application (spec v4 T4).

Integration task: wires the T1 canonical math, T2 curated rows, and T3 read-only
identity resolution into per-prospect consensus records under the S1 abstention
policy (spec §9). All policy lives HERE (the consumer), not in the canonical math
(U1): the ``disagreement_flag = iqr > 6`` threshold and the exact-pick eligibility
ladder are applied around the pure stats.

Abstention ladder (§9, over distinct curator-canonical analysts):
- ``n_unique_analysts < 3``           -> abstain (no record)
- ``3 <= n_unique_analysts <= 4``     -> round_tier_only (median surfaced, no exact)
- ``n_unique_analysts >= 5``          -> exact_pick ONLY when ``iqr <= 6`` AND
  ``staleness_days <= 30`` (U5); else round_tier_only with the pick median
  suppressed. Emitted exact picks carry a structural ``internal_diagnostic=True``
  (U6), never David-facing.

The U4 match-rate gate (T3) runs over the RAW pre-join eligible exact-pick rows
ranked by projected pick (preserving unresolved entries), so a missing Top-N
consensus prospect cannot silently bypass.

Import isolation (U2): imports only sibling mock_consensus modules + the S3
identity substrate; never Engine A/B, scoring, or backtest_mock_draft.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from statistics import median as _median

from src.dynasty_genius.identity.college_prospect_identity import normalize_name
from src.dynasty_genius.mock_consensus.consensus_math import (
    ConsensusObservation,
    compute_consensus_stats,
)
from src.dynasty_genius.mock_consensus.curated_input import CuratedMockRow
from src.dynasty_genius.mock_consensus.identity_join import (
    IdentityResolution,
    apply_match_rate_gate,
)

_MIN_ANALYSTS = 3
_EXACT_PICK_MIN_ANALYSTS = 5
_DISPERSION_THRESHOLD = 6  # S1 consumer policy (NOT in the canonical math, U1)
_MAX_STALENESS_DAYS = 30  # U5 (David ruling)


@dataclass(frozen=True)
class ConsensusRecord:
    """Per-prospect consensus output (overlay-only; exact pick internal-only)."""

    prospect_uuid: str
    n_unique_analysts: int
    n_sources: int
    projected_pick_median: float | None
    projected_pick_iqr: float | None
    projected_pick_mad: float | None
    projected_pick_min: int | None
    projected_pick_max: int | None
    disagreement_flag: bool
    staleness_days: int | None
    round_tier: str
    abstention_tier: str
    internal_diagnostic: bool
    raw_row_hashes_used: tuple[str, ...]


@dataclass(frozen=True)
class AggregateResult:
    """Outcome of aggregating a curated payload into consensus records."""

    should_abstain: bool
    records: list[ConsensusRecord] = field(default_factory=list)
    abstention_reasons: list[str] = field(default_factory=list)


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def round_tier_for_pick(pick: float | int | None) -> str:
    """Map a projected pick to its §8 round tier (12-team SF granularity at the top).

    ``None`` -> UDFA. Half-picks round half-up before bucketing (e.g. 4.5 -> 5 ->
    R1.mid; 8.5 -> 9 -> R1.late). R1.late spans the rest of NFL round 1 (picks
    9-32); R2/R3 are NFL rounds 2/3; Day3 is NFL rounds 4-7.
    """
    if pick is None:
        return "UDFA"
    p = _round_half_up(pick)
    if p <= 4:
        return "R1.early"
    if p <= 8:
        return "R1.mid"
    if p <= 32:
        return "R1.late"
    if p <= 64:
        return "R2"
    if p <= 96:
        return "R3"
    return "Day3"


def _round_only_tier(median_round: float) -> str:
    r = _round_half_up(median_round)
    if r <= 1:
        return "R1"
    if r == 2:
        return "R2"
    if r == 3:
        return "R3"
    return "Day3"


def _prospect_key(row: CuratedMockRow) -> tuple[str, str, int]:
    return (normalize_name(row.prospect_name_raw), row.position_raw, row.draft_class)


def _latest_per_analyst(
    pairs: list[tuple[CuratedMockRow, IdentityResolution]],
) -> list[tuple[CuratedMockRow, IdentityResolution]]:
    """Keep one latest-eligible row per (prospect, analyst).

    Deterministic tie-break: max of (published_date, source_snapshot_id,
    raw_row_hash) — §5.
    """
    best: dict[tuple[tuple[str, str, int], str], tuple[CuratedMockRow, IdentityResolution]] = {}
    for row, resolution in pairs:
        key = (_prospect_key(row), row.analyst)
        rank = (row.published_date, row.source_snapshot_id, row.raw_row_hash)
        current = best.get(key)
        if current is None:
            best[key] = (row, resolution)
            continue
        cur_row = current[0]
        cur_rank = (
            cur_row.published_date,
            cur_row.source_snapshot_id,
            cur_row.raw_row_hash,
        )
        if rank > cur_rank:
            best[key] = (row, resolution)
    return list(best.values())


def _staleness_days(rows: list[CuratedMockRow], as_of: str) -> int:
    as_of_date = date.fromisoformat(as_of)
    return max(
        (as_of_date - date.fromisoformat(row.published_date)).days for row in rows
    )


def _build_exact_record(
    uuid: str,
    group: list[CuratedMockRow],
    exact_rows: list[CuratedMockRow],
    as_of: str,
) -> tuple[ConsensusRecord | None, str | None]:
    """Build an exact-pick-class record, or (None, abstain_reason) on <3 analysts."""
    observations = [
        ConsensusObservation(
            pick_no=row.projected_pick,
            projected_round=row.projected_round,
            source_id=row.source_id,
            analyst=row.analyst,
            published_date=row.published_date,
        )
        for row in exact_rows
    ]
    stats = compute_consensus_stats(observations, as_of=as_of)
    disagreement_flag = stats.iqr > _DISPERSION_THRESHOLD
    n_analysts = stats.n_unique_analysts

    if n_analysts < _MIN_ANALYSTS:
        return None, (
            f"prospect {uuid}: n_unique_analysts={n_analysts} below minimum "
            f"(>= {_MIN_ANALYSTS} required)"
        )

    if n_analysts < _EXACT_PICK_MIN_ANALYSTS:
        tier, median, internal = "round_tier_only", stats.median, False
    elif not disagreement_flag and stats.staleness_days <= _MAX_STALENESS_DAYS:
        tier, median, internal = "exact_pick", stats.median, True
    else:
        # >=5 but exact-pick hard-blocked (dispersion or staleness): suppress pick.
        tier, median, internal = "round_tier_only", None, False

    record = ConsensusRecord(
        prospect_uuid=uuid,
        n_unique_analysts=n_analysts,
        n_sources=stats.n_sources,
        projected_pick_median=median,
        projected_pick_iqr=stats.iqr,
        projected_pick_mad=stats.mad,
        projected_pick_min=stats.min,
        projected_pick_max=stats.max,
        disagreement_flag=disagreement_flag,
        staleness_days=stats.staleness_days,
        round_tier=round_tier_for_pick(stats.median),
        abstention_tier=tier,
        internal_diagnostic=internal,
        raw_row_hashes_used=tuple(sorted(row.raw_row_hash for row in group)),
    )
    return record, None


def _build_round_or_udfa_record(
    uuid: str,
    group: list[CuratedMockRow],
    as_of: str,
) -> tuple[ConsensusRecord | None, str | None]:
    """Build a round_only / udfa record (never an exact pick)."""
    analysts = {row.analyst for row in group}
    n_analysts = len(analysts)
    if n_analysts < _MIN_ANALYSTS:
        return None, (
            f"prospect {uuid}: n_unique_analysts={n_analysts} below minimum "
            f"(>= {_MIN_ANALYSTS} required)"
        )

    round_rows = [r for r in group if r.projection_status == "round_only"]
    if round_rows:
        median_round = _median([r.projected_round for r in round_rows])
        round_tier = _round_only_tier(median_round)
    else:
        round_tier = "UDFA"

    record = ConsensusRecord(
        prospect_uuid=uuid,
        n_unique_analysts=n_analysts,
        n_sources=len({row.source_id for row in group}),
        projected_pick_median=None,
        projected_pick_iqr=None,
        projected_pick_mad=None,
        projected_pick_min=None,
        projected_pick_max=None,
        disagreement_flag=False,
        staleness_days=_staleness_days(group, as_of),
        round_tier=round_tier,
        abstention_tier="round_tier_only",
        internal_diagnostic=False,
        raw_row_hashes_used=tuple(sorted(row.raw_row_hash for row in group)),
    )
    return record, None


def aggregate_mock_consensus(
    rows: list[CuratedMockRow],
    identity_map: dict[str, IdentityResolution],
    *,
    as_of: str,
) -> AggregateResult:
    """Aggregate curated rows into per-prospect consensus records under §9 policy.

    ``identity_map`` maps ``raw_row_hash`` -> :class:`IdentityResolution` (T3). A
    row without an entry is treated as unresolved (fail-closed).
    """
    if not rows:
        return AggregateResult(
            should_abstain=True,
            records=[],
            abstention_reasons=["no_rows: empty payload"],
        )

    unresolved = IdentityResolution(confirmed_uuid=None, feeds_aggregation=False)
    pairs = [(row, identity_map.get(row.raw_row_hash, unresolved)) for row in rows]
    eligible = _latest_per_analyst(pairs)

    # U4 gate over RAW pre-join eligible exact-pick rows ranked by projected pick.
    exact_pairs = [
        (row, resolution)
        for row, resolution in eligible
        if row.projection_status == "exact_pick" and row.projected_pick is not None
    ]
    ranked = sorted(exact_pairs, key=lambda pr: (pr[0].projected_pick, pr[0].raw_row_hash))
    # The U4 gate ranks by projected pick, so it applies only when exact-pick rows
    # exist. All-round_only/UDFA payloads have no pick ranking to gate (and must
    # NOT trip T3's standalone empty-input fail-closed behavior).
    if ranked:
        gate = apply_match_rate_gate(
            [
                {"raw_rank": idx, "resolved": bool(resolution.feeds_aggregation)}
                for idx, (_row, resolution) in enumerate(ranked, start=1)
            ]
        )
        if gate.should_abstain:
            return AggregateResult(
                should_abstain=True, records=[], abstention_reasons=list(gate.reasons)
            )

    # Group resolved rows by confirmed prospect uuid.
    groups: dict[str, list[CuratedMockRow]] = {}
    for row, resolution in eligible:
        if not resolution.feeds_aggregation or resolution.confirmed_uuid is None:
            continue
        groups.setdefault(str(resolution.confirmed_uuid), []).append(row)

    records: list[ConsensusRecord] = []
    reasons: list[str] = []
    for uuid in sorted(groups):
        group = groups[uuid]
        exact_rows = [r for r in group if r.projection_status == "exact_pick"]
        if exact_rows:
            record, reason = _build_exact_record(uuid, group, exact_rows, as_of)
        else:
            record, reason = _build_round_or_udfa_record(uuid, group, as_of)
        if record is not None:
            records.append(record)
        if reason is not None:
            reasons.append(reason)

    return AggregateResult(
        should_abstain=not records,
        records=records,
        abstention_reasons=reasons,
    )
