"""Helpers the roster audit relies on, tested on their own (DG-178 round 1).

Two rules. The denominator of any coverage statement is EVERY roster id, including the
ones the artifact does not know — an identity the pipeline lost is a missing forecast, not
a row to leave out of the count. And nothing is keyed by an id that could repeat: a
duplicate Sleeper id in the artifact or on a roster is refused, never overwritten.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from src.dynasty_genius.ranking.served_rows import SKILL_POSITIONS, ServedRow


@dataclass(frozen=True)
class RosterReconciliation:
    present_ids: list[str]
    absent_ids: list[str]
    outside_population: dict[str, str]  # sleeper id -> the artifact's position, when it is not a skill position

    @property
    def denominator(self) -> int:
        return len(self.present_ids) + len(self.absent_ids) + len(self.outside_population)


def rows_by_sleeper_id(rows: Iterable[ServedRow]) -> dict[str, ServedRow]:
    out: dict[str, ServedRow] = {}
    for r in rows:
        sid = str(r.sleeper_id)
        if sid in out:
            raise ValueError(f"duplicate Sleeper id {sid} in the artifact ({out[sid].full_name} / {r.full_name}); "
                             "a dictionary would keep the last one silently")
        out[sid] = r
    return out


def reconcile_roster(roster_ids: Sequence[str], rows: Iterable[ServedRow],
                     other_positions: Optional[Mapping[str, str]] = None) -> RosterReconciliation:
    """Every roster id lands in exactly one of: present (a skill row exists), outside the
    population (the artifact has him at a non-skill position), absent (no row at all)."""
    ids = [str(x) for x in roster_ids]
    dupes = sorted(k for k, n in Counter(ids).items() if n > 1)
    if dupes:
        raise ValueError(f"duplicate id(s) on the roster: {dupes}")
    by = rows_by_sleeper_id(rows)
    other = {str(k): v for k, v in (other_positions or {}).items()}
    return RosterReconciliation(
        present_ids=[i for i in ids if i in by],
        absent_ids=[i for i in ids if i not in by and i not in other],
        outside_population={i: other[i] for i in ids if i not in by and i in other},
    )


def replacement_pool_census(rows: Iterable[ServedRow], rostered_ids: set[str],
                            positions: Iterable[str] = SKILL_POSITIONS) -> dict[str, dict]:
    """Per position: how many unrostered players exist, how many could set the bar under the
    served-rate policy, and why the rest could not. The best SCORED available player is not
    automatically the best OBTAINABLE one: everyone in `excluded_unscored` is obtainable and
    unranked, and this census says how large that set is."""
    rostered = {str(x) for x in rostered_ids}
    rows = list(rows)
    out: dict[str, dict] = {}
    for pos in sorted(positions):
        unr = [r for r in rows if r.position == pos and str(r.sleeper_id) not in rostered]
        scored = [r for r in unr if r.served_rate_ppg is not None]
        eligible = [r for r in scored if not r.dvs_clamped and r.projection_2y is not None and r.projection_2y > 0]
        out[pos] = {
            "unrostered": len(unr),
            "scored": len(scored),
            "eligible": len(eligible),
            "excluded_unscored": len(unr) - len(scored),
            "excluded_clamped": sum(1 for r in scored if r.dvs_clamped),
            "excluded_no_projection": sum(1 for r in scored if not r.dvs_clamped
                                          and (r.projection_2y is None or r.projection_2y <= 0)),
            "eligible_ids": [str(r.sleeper_id) for r in sorted(eligible, key=lambda r: r.served_rate_ppg, reverse=True)],
        }
    return out
