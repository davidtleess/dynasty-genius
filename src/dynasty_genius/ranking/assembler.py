"""The assembler: weight and sum. Nothing else (DG-178).

Every term it receives is already unconditional and in one unit, so the only thing this
module is allowed to add is TIME PREFERENCE — the declared posture's discount ``d``:

    V(posture) = sum over h of d^h * ev_h

It never multiplies a probability by anything; that happened inside one adapter, inside one
declared event. It never infers the posture. It never drops a player: a term set it cannot
value comes back with its identity, ``value=None`` and the producer's stated reason, so a
blank on the board is always a sentence and never an absence.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict

from src.dynasty_genius.ranking.contract import (
    Posture,
    RankedValue,
    TargetSpec,
    TermSet,
)


def _comparability(used, board: Optional[TargetSpec]) -> tuple[str, Optional[str]]:
    """Readiness of a FULL term set against the board, from typed fields only."""
    if board is None:
        return "unclassified", "no board target declared; nothing can be called comparable"
    diffs: dict[str, set] = {}
    for t in used:
        for f in t.spec.mismatches(board):
            diffs.setdefault(f, set()).add(str(getattr(t.spec, f)))
    if not diffs:
        return "comparable", None
    note = "not comparable with the board target: " + "; ".join(
        f"{f} = {sorted(v)} vs {getattr(board, f)}" for f, v in sorted(diffs.items()))
    return "research_only", note


def compose_value(term_set: TermSet, posture: Posture, *, horizons: int,
                  board: Optional[TargetSpec] = None, comparable_only: bool = False) -> RankedValue:
    """One focal value for one player under one posture, or a stated reason for none.

    ``board`` is the typed target the board requires; readiness is decided against it on
    typed fields. With ``comparable_only`` a research-only term set keeps its identity and
    comes back with ``value=None`` and the mismatched fields as its reason.
    """
    used = [t for t in term_set.terms if t.h <= horizons]
    common = dict(
        player_id=term_set.player_id, position=term_set.position,
        full_name=term_set.full_name, sleeper_id=term_set.sleeper_id,
        posture=posture, producer=term_set.producer,
        replacement_ref=term_set.replacement_ref, forecast_date=term_set.forecast_date,
        served=term_set.served,
        conditioning_events=tuple(dict.fromkeys(t.conditioning_event for t in used)),
        unit=(used[0].unit if used else (board.unit if board else None)),
    )
    if term_set.coverage != "full":
        return RankedValue(value=None, coverage=term_set.coverage, reason=term_set.reason,
                           readiness="incomplete" if term_set.coverage == "partial" else "none",
                           horizons_used=len(used), **common)
    expected = list(range(horizons + 1))
    if [t.h for t in used] != expected:
        raise ValueError(
            f"{term_set.player_id}: producer {term_set.producer.name} claims full coverage "
            f"but supplies horizons {[t.h for t in term_set.terms]}, not h=0..{horizons}"
        )
    readiness, note = _comparability(used, board)
    if readiness == "comparable" and not term_set.producer.evidence_verified:
        readiness = "unverified"
        note = ("unverified: the producer's evidence identity could not be verified"
                + (f" ({term_set.producer.evidence_note})" if term_set.producer.evidence_note else ""))
    if comparable_only and readiness != "comparable":
        return RankedValue(value=None, coverage="full", readiness=readiness, comparability_note=note,
                           reason=note, horizons_used=len(used), **common)
    # Terms beyond the board horizon are not summed: a producer that reaches further than
    # the board is shown on the board's horizon, not refused for reaching.
    value = sum((posture.discount ** t.h) * t.ev_above_replacement for t in used)
    return RankedValue(value=float(value), coverage="full", readiness=readiness, comparability_note=note,
                       reason=term_set.reason, horizons_used=len(used), **common)


class RankingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    posture: Posture
    horizons: int
    forecast_date: Optional[date]
    board: Optional[TargetSpec] = None
    values: list[RankedValue]

    @property
    def counts(self) -> dict[str, int]:
        """Numerical coverage. NOT scientific comparability; see readiness_counts."""
        c = Counter(v.coverage for v in self.values)
        return {"full": c.get("full", 0), "partial": c.get("partial", 0), "none": c.get("none", 0)}

    @property
    def readiness_counts(self) -> dict[str, int]:
        c = Counter(v.readiness for v in self.values)
        keys = ("comparable", "unverified", "research_only", "incomplete", "none") + (("unclassified",) if c.get("unclassified") else ())
        return {k: c.get(k, 0) for k in keys}

    def ranked(self, comparable_only: bool = False) -> list[RankedValue]:
        """Highest value first, blanks last, input order preserved among ties. This is an
        ORDER for inspection; whether adjacent players are distinguishable is DG-172's
        question and is not answered here. With comparable_only, research-only values are
        left out rather than ranked beside comparable ones."""
        pool = [v for v in self.values if not comparable_only or v.readiness == "comparable"]
        return sorted(pool, key=lambda v: (v.value is None, -(v.value or 0.0)))


def assemble(term_sets: Iterable[TermSet], posture: Posture, *, horizons: int,
             board: Optional[TargetSpec] = None, comparable_only: bool = False) -> RankingResult:
    sets = list(term_sets)
    if len({t.player_id for t in sets}) != len(sets):
        dupes = [k for k, n in Counter(t.player_id for t in sets).items() if n > 1]
        raise ValueError(f"one term set per player: duplicates {dupes}")
    dates = {t.forecast_date for t in sets}
    if len(dates) > 1:
        raise ValueError(f"term sets on different forecast dates cannot share a board: {sorted(dates)}")
    # One replacement policy and one snapshot per board: a value against one bar rule is not
    # comparable with a value against another, however the terms are typed.
    refs = [t.replacement_ref for t in sets if t.replacement_ref is not None and t.coverage != "none"]
    policies = {r.policy for r in refs}
    snapshots = {r.snapshot_id for r in refs}
    if len(policies) > 1:
        raise ValueError(f"term sets with different replacement policies cannot share a board: {sorted(policies)}")
    if len(snapshots) > 1:
        raise ValueError(f"term sets with different replacement snapshots cannot share a board: {sorted(snapshots)}")
    return RankingResult(
        posture=posture, horizons=horizons, board=board,
        forecast_date=next(iter(dates)) if dates else None,
        values=[compose_value(t, posture, horizons=horizons, board=board, comparable_only=comparable_only)
                for t in sets],
    )
