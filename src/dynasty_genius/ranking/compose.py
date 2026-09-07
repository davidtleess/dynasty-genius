"""Route each served row to the producer that can speak for it (DG-178).

An Engine A row is a prospect with no conditional projection; the veteran adapter has
nothing to say about him and the rookie candidate, when one is supplied, does. Every other
row goes through the veteran adapter. Rows out always equal rows in: a position with no
replacement bar comes back as a stated blank, never an absence.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping, Optional

from src.dynasty_genius.ranking.adapters.annual_candidate import (
    AnnualCandidate,
    build_annual_term_set,
)
from src.dynasty_genius.ranking.adapters.rookie_candidate import (
    RookieCandidate,
    build_rookie_term_set,
)
from src.dynasty_genius.ranking.adapters.veteran_served import (
    PRODUCER_NAME,
    build_term_set,
)
from src.dynasty_genius.ranking.contract import (
    ProducerRef,
    ReplacementRef,
    ServedReference,
    TermSet,
)
from src.dynasty_genius.ranking.served_rows import ServedRow
from src.dynasty_genius.ranking.survival_cells import RetentionCells


def compose_term_sets(rows: Iterable[ServedRow], replacement: Mapping[str, ReplacementRef],
                      cells: RetentionCells, *, rookie_candidate: Optional[RookieCandidate],
                      forecast_date: date, horizons: int = 5) -> list[TermSet]:
    out: list[TermSet] = []
    for row in rows:
        ref = replacement.get(row.position)
        if ref is None:
            out.append(TermSet(
                player_id=row.player_id, position=row.position, forecast_date=forecast_date,
                full_name=row.full_name, sleeper_id=row.sleeper_id,
                producer=ProducerRef(name=PRODUCER_NAME, version=f"served:{row.captured_at}", estimate_class="candidate"),
                replacement_ref=None, terms=[], coverage="none",
                reason=f"no replacement bar for position {row.position}",
                served=ServedReference(dynasty_value_score=row.dynasty_value_score,
                                       dvs_engine=row.dvs_engine, captured_at=row.captured_at),
            ))
            continue
        if row.dvs_engine == "A" and rookie_candidate is not None:
            out.append(build_rookie_term_set(row, ref, rookie_candidate, draft_pick=row.nfl_draft_pick,
                                             forecast_date=forecast_date, horizons=horizons,
                                             draft_season=row.draft_class))
            continue
        out.append(build_term_set(row, ref, cells, forecast_date=forecast_date))
    return out


def compose_annual_term_sets(rows: Iterable[ServedRow], replacement: Mapping[str, list[ReplacementRef]],
                             candidate: AnnualCandidate, *, forecast_date: date,
                             horizons: Optional[int] = None) -> list[TermSet]:
    """The comparable path: every row through the annual-target producer. Rows the producer
    does not cover, and positions with no replacement, come back as stated absences. The
    research adapters are not consulted here."""
    out: list[TermSet] = []
    for row in rows:
        refs = replacement.get(row.position)
        if not refs:
            out.append(TermSet(
                player_id=row.player_id, position=row.position, forecast_date=forecast_date,
                full_name=row.full_name, sleeper_id=row.sleeper_id,
                producer=ProducerRef(name=candidate.model_version, version=f"csv:{candidate.csv_sha256[:12]}",
                                     estimate_class="candidate"),
                replacement_ref=None, terms=[], coverage="none",
                reason=f"no replacement bar for position {row.position} in {candidate.model_version}",
                served=ServedReference(dynasty_value_score=row.dynasty_value_score,
                                       dvs_engine=row.dvs_engine, captured_at=row.captured_at),
            ))
            continue
        out.append(build_annual_term_set(row, refs, candidate, forecast_date=forecast_date, horizons=horizons))
    return out


def absent_annual_term_sets(rows: Iterable[ServedRow], producers: list[str], *, forecast_date: date,
                            stated_reasons: Optional[Mapping[str, str]] = None) -> list[TermSet]:
    """Rows no annual producer forecasts: a stated absence naming the producers consulted and,
    when a producer's reconciliation stated WHY (by Sleeper id), that reason verbatim — never
    an invented one. Without a stated reason the absence says so."""
    names = ", ".join(producers) if producers else "none"
    out = []
    for row in rows:
        stated = (stated_reasons or {}).get(str(row.sleeper_id)) if row.sleeper_id is not None else None
        if stated:
            reason = f"not forecast by any annual producer ({names}); the producer's stated reason: {stated}"
        else:
            reason = (f"not forecast by any annual producer ({names}); no producer stated a reason for this player "
                      f"(typically no 2025 stat line for the veteran forecast and not a 2026 draftee)")
        out.append(TermSet(
            player_id=row.player_id, position=row.position, forecast_date=forecast_date,
            full_name=row.full_name, sleeper_id=row.sleeper_id,
            producer=ProducerRef(name="annual_target", version="no_producer", estimate_class="candidate"),
            replacement_ref=None, terms=[], coverage="none", reason=reason,
            served=ServedReference(dynasty_value_score=row.dynasty_value_score, dvs_engine=row.dvs_engine,
                                   captured_at=row.captured_at),
        ))
    return out
