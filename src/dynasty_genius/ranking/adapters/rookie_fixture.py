"""Rookie FIXTURE adapter — a labelled stand-in with the contract's shape, never a model (DG-178).

The rookie lane (DG-165) owes, per season h, P(qualifies at h | draft capital) and
E[ppg | qualifies at h]. That is the decomposition the assembler can take: the probability
and the conditional mean share one event and one season, so

    ev_h = P(qualifies at h) x max(0, E[ppg | qualifies at h] - R)

is the unconditional expectation above replacement at h. What it must NOT be is
P(ever qualifies) x a level-conditional retention path — "ever" has no clock, and the level
he reaches is the unknown.

Until that candidate exists, this builds a term set from explicit per-horizon inputs so the
assembler, the audit and the tests run end to end. Every term is stamped FIXTURE in its
event string and the producer is ``estimate_class="fixture"``. Nothing here is a forecast,
and nothing here may fill coverage on a board David reads.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from src.dynasty_genius.ranking.contract import (
    HorizonTerm,
    ProducerRef,
    ReplacementRef,
    ServedReference,
    TargetSpec,
    TermSet,
    annual_target,
    season_for_horizon,
)
from src.dynasty_genius.ranking.served_rows import ServedRow

PRODUCER_NAME = "rookie_fixture"
DEFAULT_HORIZONS = 5


def build_fixture_term_set(row: ServedRow, replacement: ReplacementRef,
                           per_horizon: Sequence[tuple[float, float]], *, forecast_date: date,
                           label: str, horizons: int = DEFAULT_HORIZONS,
                           spec: Optional[TargetSpec] = None, evidence_verified: bool = False) -> TermSet:
    """``per_horizon[h] = (P(qualifies at h), E[ppg | qualifies at h])`` for h = 0..horizons.
    ``spec`` defaults to the annual target so end-to-end tests can exercise the comparable
    path with a fixture that is stamped FIXTURE everywhere."""
    spec = spec or annual_target(forecast_date)
    served = ServedReference(dynasty_value_score=row.dynasty_value_score,
                             dvs_engine=row.dvs_engine, captured_at=row.captured_at)
    producer = ProducerRef(name=PRODUCER_NAME, version=f"fixture:{label}", estimate_class="fixture",
                           evidence_verified=evidence_verified,
                           evidence_note="fixture: evidence flag set by the test, not by any file")
    common = dict(player_id=row.player_id, position=row.position, forecast_date=forecast_date,
                  producer=producer, replacement_ref=replacement, full_name=row.full_name,
                  sleeper_id=row.sleeper_id, served=served)
    terms: list[HorizonTerm] = []
    for h, (p, e) in enumerate(per_horizon):
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"h={h}: {p!r} is not a probability")
        ev = p * max(0.0, float(e) - replacement.rate_ppg)
        terms.append(HorizonTerm(
            h=h, season=season_for_horizon(forecast_date, h), ev_above_replacement=ev,
            conditioning_event=(f"FIXTURE ({label}), not a model output: P(qualifies at h={h}) x "
                                f"max(0, E[ppg | qualifies at h={h}] - replacement)"),
            spec=spec,
        ))
    if len(terms) != horizons + 1:
        return TermSet(terms=terms, coverage="partial",
                       reason=f"fixture supplies {len(terms)} horizons, the board needs {horizons + 1}",
                       **common)
    return TermSet(terms=terms, coverage="full", reason=None, **common)
