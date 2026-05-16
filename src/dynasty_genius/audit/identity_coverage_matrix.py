"""Identity audit runner — Task 13.1.1.

Fixture-driven: all source lookup tables (ff_playerids crosswalk, sleeper
passthrough, alias bridge, composite registries) are injected as plain dicts.
No live API calls during the audit so results are reproducible and testable.

Resolution cascade (identity_contract.md §4):
  1. Direct ID join      — player_id already known
  2. ff_playerids        — gsis_id → crosswalk
  3. Sleeper passthrough — sleeper_id → gsis_id → crosswalk
  4. Alias bridge        — (norm_name, pos, draft_year) → sleeper_id
  5. Composite key       — (norm_name, dob, pos, draft_year) → player_id
  6. Composite prospect  — (norm_name, college, pos, draft_year) → player_id
  7. Review queue        — no deterministic resolution possible

Fuzzy matching is prohibited. Unresolved rows are counted in review_queue,
never silently dropped.
"""
from __future__ import annotations

import dataclasses
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

SOURCE_ID_FIELDS: tuple[str, ...] = (
    "player_id",
    "sleeper_id",
    "gsis_id",
    "pff_id",
    "pfr_id",
    "cfbref_id",
    "espn_id",
    "yahoo_id",
    "sportradar_id",
    "fantasypros_id",
    "rotowire_id",
    "fantasy_data_id",
)


class ResolutionStage(str, Enum):
    DIRECT_ID = "direct_id_join"
    FF_PLAYERIDS = "ff_playerids_crosswalk"
    SLEEPER_PASSTHROUGH = "sleeper_passthrough"
    ALIAS_BRIDGE = "prospect_alias_bridge"
    COMPOSITE_KEY = "composite_name_dob"
    COMPOSITE_PROSPECT = "composite_name_college"
    REVIEW_QUEUE = "review_queue"


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


@dataclasses.dataclass
class IdentityAuditRow:
    """A player record submitted to the coverage audit.

    cohort:  Segment label for coverage reporting.
             Common values: 'active_starter', 'active_depth',
             'rookie_2025', 'historical_te', 'historical_non_te'.
    """
    cohort: str
    name: str
    position: str
    draft_year: Optional[int] = None
    college: Optional[str] = None
    date_of_birth: Optional[str] = None
    player_id: Optional[str] = None
    sleeper_id: Optional[str] = None
    gsis_id: Optional[str] = None
    pff_id: Optional[str] = None
    pfr_id: Optional[str] = None
    cfbref_id: Optional[str] = None
    espn_id: Optional[str] = None
    yahoo_id: Optional[str] = None
    sportradar_id: Optional[str] = None
    fantasypros_id: Optional[str] = None
    rotowire_id: Optional[str] = None
    fantasy_data_id: Optional[str] = None


@dataclasses.dataclass
class AuditResult:
    """Resolution outcome for a single IdentityAuditRow."""
    input_row: IdentityAuditRow
    resolved: bool
    stage: ResolutionStage
    resolved_player_id: Optional[str]
    resolved_sleeper_id: Optional[str]
    resolved_gsis_id: Optional[str]
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.input_row.name,
            "position": self.input_row.position,
            "cohort": self.input_row.cohort,
            "resolved": self.resolved,
            "stage": self.stage.value,
            "resolved_player_id": self.resolved_player_id,
            "resolved_sleeper_id": self.resolved_sleeper_id,
            "resolved_gsis_id": self.resolved_gsis_id,
            "notes": self.notes,
        }


@dataclasses.dataclass(frozen=True)
class CohortCoverage:
    cohort: str
    total: int
    resolved: int
    review_queue: int

    @property
    def resolved_pct(self) -> float:
        return round(self.resolved / self.total, 4) if self.total else 0.0

    @property
    def loss_rate(self) -> float:
        return round(self.review_queue / self.total, 4) if self.total else 0.0

    def passes_gate(self, max_loss_rate: float) -> bool:
        return self.loss_rate <= max_loss_rate

    def as_dict(self) -> dict:
        return {
            "cohort": self.cohort,
            "total": self.total,
            "resolved": self.resolved,
            "review_queue": self.review_queue,
            "resolved_pct": self.resolved_pct,
            "loss_rate": self.loss_rate,
        }


@dataclasses.dataclass(frozen=True)
class DuplicateReport:
    """Non-null ID value present on more than one row — potential silent corruption."""
    field: str
    value: str
    player_names: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "player_names": list(self.player_names),
        }


@dataclasses.dataclass
class CoverageMatrix:
    run_id: str
    run_timestamp: str
    cohort_summary: list[CohortCoverage]
    duplicate_conflicts: list[DuplicateReport]
    total_input_rows: int
    total_output_rows: int

    @property
    def row_count_preserved(self) -> bool:
        return self.total_input_rows == self.total_output_rows

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_timestamp": self.run_timestamp,
            "row_count_preserved": self.row_count_preserved,
            "total_input_rows": self.total_input_rows,
            "total_output_rows": self.total_output_rows,
            "cohort_summary": [c.as_dict() for c in self.cohort_summary],
            "duplicate_conflicts": [d.as_dict() for d in self.duplicate_conflicts],
        }


def _resolve_row(
    row: IdentityAuditRow,
    *,
    ff_playerids: dict[str, dict],
    sleeper_passthrough: dict[str, dict],
    alias_bridge: dict[tuple, str],
    composite_registry: dict[tuple, str],
    prospect_registry: dict[tuple, str],
) -> AuditResult:
    norm = _normalize(row.name)
    pos = row.position.upper()

    # Stage 1: canonical player_id already present
    if row.player_id:
        return AuditResult(
            input_row=row,
            resolved=True,
            stage=ResolutionStage.DIRECT_ID,
            resolved_player_id=row.player_id,
            resolved_sleeper_id=row.sleeper_id,
            resolved_gsis_id=row.gsis_id,
        )

    # Stage 2: gsis_id → ff_playerids crosswalk
    if row.gsis_id and row.gsis_id in ff_playerids:
        xwalk = ff_playerids[row.gsis_id]
        return AuditResult(
            input_row=row,
            resolved=True,
            stage=ResolutionStage.FF_PLAYERIDS,
            resolved_player_id=xwalk.get("player_id"),
            resolved_sleeper_id=xwalk.get("sleeper_id") or row.sleeper_id,
            resolved_gsis_id=row.gsis_id,
        )

    # Stage 3: sleeper_id → sleeper passthrough → gsis_id → crosswalk
    if row.sleeper_id and row.sleeper_id in sleeper_passthrough:
        pt = sleeper_passthrough[row.sleeper_id]
        gsis = pt.get("gsis_id")
        if gsis and gsis in ff_playerids:
            xwalk = ff_playerids[gsis]
            return AuditResult(
                input_row=row,
                resolved=True,
                stage=ResolutionStage.SLEEPER_PASSTHROUGH,
                resolved_player_id=xwalk.get("player_id"),
                resolved_sleeper_id=row.sleeper_id,
                resolved_gsis_id=gsis,
            )
        # sleeper_id confirmed but gsis_id absent — 2022+ rookie propagation lag
        return AuditResult(
            input_row=row,
            resolved=True,
            stage=ResolutionStage.SLEEPER_PASSTHROUGH,
            resolved_player_id=None,
            resolved_sleeper_id=row.sleeper_id,
            resolved_gsis_id=None,
            notes="sleeper_id confirmed; gsis_id absent — probable 2022+ rookie propagation lag",
        )

    # Stage 4: prospect alias bridge — (norm_name, pos, draft_year) → sleeper_id
    if row.draft_year is not None:
        key4 = (norm, pos, row.draft_year)
        if key4 in alias_bridge:
            return AuditResult(
                input_row=row,
                resolved=True,
                stage=ResolutionStage.ALIAS_BRIDGE,
                resolved_player_id=None,
                resolved_sleeper_id=alias_bridge[key4],
                resolved_gsis_id=None,
            )

    # Stage 5: composite deterministic key — (norm_name, dob, pos, draft_year) → player_id
    if row.date_of_birth and row.draft_year is not None:
        key5 = (norm, row.date_of_birth, pos, row.draft_year)
        if key5 in composite_registry:
            return AuditResult(
                input_row=row,
                resolved=True,
                stage=ResolutionStage.COMPOSITE_KEY,
                resolved_player_id=composite_registry[key5],
                resolved_sleeper_id=row.sleeper_id,
                resolved_gsis_id=row.gsis_id,
            )

    # Stage 6: composite prospect key — (norm_name, college, pos, draft_year) → player_id
    if row.college and row.draft_year is not None:
        key6 = (norm, row.college.lower(), pos, row.draft_year)
        if key6 in prospect_registry:
            return AuditResult(
                input_row=row,
                resolved=True,
                stage=ResolutionStage.COMPOSITE_PROSPECT,
                resolved_player_id=prospect_registry[key6],
                resolved_sleeper_id=row.sleeper_id,
                resolved_gsis_id=row.gsis_id,
            )

    # Stage 7: review queue — no deterministic resolution
    return AuditResult(
        input_row=row,
        resolved=False,
        stage=ResolutionStage.REVIEW_QUEUE,
        resolved_player_id=None,
        resolved_sleeper_id=None,
        resolved_gsis_id=None,
    )


def _detect_duplicates(results: list[AuditResult]) -> list[DuplicateReport]:
    """Flag non-null ID values shared by more than one input row."""
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in results:
        row = r.input_row
        for field in SOURCE_ID_FIELDS:
            val = getattr(row, field, None)
            if val:
                seen[(field, val)].append(row.name)
    return [
        DuplicateReport(field=field, value=val, player_names=tuple(names))
        for (field, val), names in seen.items()
        if len(names) > 1
    ]


def run_audit(
    rows: list[IdentityAuditRow],
    *,
    ff_playerids: dict[str, dict] | None = None,
    sleeper_passthrough: dict[str, dict] | None = None,
    alias_bridge: dict[tuple, str] | None = None,
    composite_registry: dict[tuple, str] | None = None,
    prospect_registry: dict[tuple, str] | None = None,
    run_id: str | None = None,
) -> tuple[list[AuditResult], CoverageMatrix]:
    """Run the deterministic identity cascade over all rows.

    All lookup tables are injectable. Pass None to use empty tables.
    Returns (per-row results, coverage matrix).
    """
    ff_playerids = ff_playerids or {}
    sleeper_passthrough = sleeper_passthrough or {}
    alias_bridge = alias_bridge or {}
    composite_registry = composite_registry or {}
    prospect_registry = prospect_registry or {}
    run_id = run_id or uuid.uuid4().hex[:8]

    results: list[AuditResult] = [
        _resolve_row(
            row,
            ff_playerids=ff_playerids,
            sleeper_passthrough=sleeper_passthrough,
            alias_bridge=alias_bridge,
            composite_registry=composite_registry,
            prospect_registry=prospect_registry,
        )
        for row in rows
    ]

    # Aggregate by cohort
    cohort_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"resolved": 0, "review_queue": 0})
    for r in results:
        bucket = cohort_buckets[r.input_row.cohort]
        if r.resolved:
            bucket["resolved"] += 1
        else:
            bucket["review_queue"] += 1

    cohort_summary = [
        CohortCoverage(
            cohort=cohort,
            total=v["resolved"] + v["review_queue"],
            resolved=v["resolved"],
            review_queue=v["review_queue"],
        )
        for cohort, v in sorted(cohort_buckets.items())
    ]

    matrix = CoverageMatrix(
        run_id=run_id,
        run_timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        cohort_summary=cohort_summary,
        duplicate_conflicts=_detect_duplicates(results),
        total_input_rows=len(rows),
        total_output_rows=len(results),
    )

    return results, matrix
