"""Veteran adapter: served pieces + retention cells -> unconditional terms (DG-178).

This is the one place a probability meets a conditional mean, and it happens inside ONE
declared event, on ONE row:

    served_rate = P x E                 (dvs / 100 x dvs_p90_ref, exact when unclamped)
    P           = served_rate / E       (E = projection_2y, the conditional rate)
    ev_0        = P x (E - R)           (R = the replacement's served rate)
    ev_h        = ev_0 x R(h)           (h = 1..5; R(h) unconditional, survival inside)

Why the bar is INSIDE the bracket. Owning him and losing him means fielding the replacement,
not fielding nothing: E[lineup] = P x E + (1 - P) x R, so the value over not owning him is
P x (E - R). The served xVAR subtracts an undiscounted bar (P x E - R); that number is left
exactly as served and carried alongside, never overwritten.

What this adapter does NOT do. It does not invent P where the row cannot yield one (clamped:
a bound; Engine A: no projection). It does not borrow a neighbouring cell when the player's
cell is suppressed. It does not touch survival: the cells' ratios already contain it.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from src.dynasty_genius.models.availability import EVENT_DEFINITION
from src.dynasty_genius.ranking.contract import (
    HorizonTerm,
    ProducerRef,
    ReplacementRef,
    ServedReference,
    TargetSpec,
    TermSet,
    season_for_horizon,
)
from src.dynasty_genius.ranking.served_rows import ServedRow
from src.dynasty_genius.ranking.survival_cells import RetentionCells

PRODUCER_NAME = "veteran_served_plus_retention_cells"
_P_TOLERANCE = 1e-6

H0_EVENT = (
    "h=0: P(plays) x (E[ppg | plays] - replacement served rate). P recovered from the served "
    "row as served_rate / projection_2y; E is projection_2y (avg over t+1..t+2). Availability "
    "event: " + EVENT_DEFINITION + " The two-season window quantity is used as the h=0 estimate "
    "(overstates h=0 availability: P(t+1 or t+2) >= P(t+1))."
)


def _hx_event(key: tuple[str, str, str], n: int) -> str:
    return (
        f"h>=1: ev_0 x R(h). R(h) is UNCONDITIONAL given a qualifying season at h=0 "
        f"(cell {key[0]} {key[1]} {key[2]}, n={n}); survival is inside R and is not applied "
        "again. The return-after-non-qualification path is not modelled (biased low for low P). "
        "Age basis: the served whole-year age k was looked up as k + 0.5 because the cells were "
        "cut right-inclusive on exact age at September 1 (a served 23 is a true age in [23, 24), "
        "which the cells bin as 24-25)."
    )


def cell_lookup_age(served_age: Optional[float]) -> Optional[float]:
    """The exact-age proxy for a served whole-year age. Sleeper floors the true age; the cells
    were cut right-inclusive on exact age, so the whole interval [k, k+1) above the integer
    belongs to the band that contains k + 0.5. A served age that is already fractional (a
    caller that computed it from a birth date) is used as it is."""
    if served_age is None:
        return None
    a = float(served_age)
    return a + 0.5 if a == int(a) else a


def _h0_spec(cutoff: date) -> TargetSpec:
    """What the served composition actually is: all-games served ppg, the two-season-window
    qualifying event, a rate. A research approximation of the annual target, typed as such."""
    return TargetSpec(scope="ALL_GAMES", scoring="served_all_games_ppr", exposure="all_games",
                      event="two_season_window_qualifying", clock="two_season_window",
                      quantity="ppg_rate", labels_through=cutoff.year - 1)


def _hx_spec(cutoff: date) -> TargetSpec:
    """ev_0 x R(h): a season-total retention ratio from a bar-rank cohort applied to an
    all-games ppg margin. One season per term, but neither the event nor the unit is the
    annual target's."""
    return TargetSpec(scope="ALL_GAMES", scoring="served_all_games_ppr", exposure="all_games",
                      event="retention_ratio_bar_rank", clock="per_season",
                      quantity="ppg_rate", labels_through=cutoff.year - 1)


def _producer(row: ServedRow, cells: RetentionCells) -> ProducerRef:
    return ProducerRef(name=PRODUCER_NAME,
                       version=f"served:{row.captured_at};cells:{cells.source_sha256[:12]}",
                       estimate_class="candidate")


def build_term_set(row: ServedRow, replacement: ReplacementRef, cells: RetentionCells, *,
                   forecast_date: date) -> TermSet:
    served = ServedReference(dynasty_value_score=row.dynasty_value_score,
                             dvs_engine=row.dvs_engine, captured_at=row.captured_at)
    common = dict(player_id=row.player_id, position=row.position, forecast_date=forecast_date,
                  producer=_producer(row, cells), replacement_ref=replacement,
                  full_name=row.full_name, sleeper_id=row.sleeper_id, served=served)

    def blank(coverage: str, reason: str, terms: Optional[list[HorizonTerm]] = None) -> TermSet:
        return TermSet(terms=terms or [], coverage=coverage, reason=reason, **common)

    served_rate = row.served_rate_ppg
    if served_rate is None:
        return blank("none", "no served score on the row; nothing to compose")
    e = row.projection_2y
    if e is None:
        return blank("none", f"no conditional projection (E[ppg | plays]) on the row; "
                             f"dvs_engine={row.dvs_engine}. The veteran path cannot value him; "
                             "the rookie lane owes his terms")
    r = replacement.rate_ppg
    horizons = cells.horizons
    seasons = [season_for_horizon(forecast_date, h) for h in range(horizons + 1)]

    if e <= r:
        # P x (E - R) <= 0 for any P: worth 0.0 above replacement THIS season. That is all it
        # establishes. The cells are keyed on a positive margin and say nothing about his
        # seasons 1-5, so the future is a stated absence, not six measured zeros.
        h0 = HorizonTerm(h=0, season=seasons[0], ev_above_replacement=0.0, conditioning_event=H0_EVENT,
                         spec=_h0_spec(forecast_date))
        return blank("partial", f"below replacement: E[ppg | plays] {e:.3f} <= replacement {r:.3f}, "
                                "so 0.0 this season; seasons 1-5 unmodelled (the retention cells are "
                                "keyed on a positive margin)", [h0])

    if row.dvs_clamped:
        return blank("partial", "served value is clamped at the ceiling, so P(plays) recovered "
                                "from it is a bound, not an estimate")
    p = served_rate / e
    if p > 1.0 + _P_TOLERANCE or p < -_P_TOLERANCE:
        raise ValueError(f"{row.player_id}: served rate {served_rate:.4f} over projection {e:.4f} "
                         f"is {p:.4f}, not a probability — the producer is broken, not the player")
    p = min(1.0, max(0.0, p))
    ev0 = p * (e - r)
    h0 = HorizonTerm(h=0, season=seasons[0], ev_above_replacement=ev0, conditioning_event=H0_EVENT,
                     spec=_h0_spec(forecast_date))

    if replacement.conditional_rate_ppg is None or replacement.conditional_rate_ppg <= 0:
        return blank("partial", "replacement conditional rate unknown; the cell margin key "
                                "cannot be built", [h0])
    if row.age is None:
        return blank("partial", "age unknown; the retention cell cannot be found", [h0])
    margin = e / replacement.conditional_rate_ppg
    hit = cells.lookup(row.position, cell_lookup_age(row.age), margin)
    if hit.status != "cell":
        return blank("partial", f"retention cell {hit.status}: {hit.reason}", [h0])
    terms = [h0] + [
        HorizonTerm(h=h, season=seasons[h], ev_above_replacement=ev0 * hit.ratios[h - 1],
                    conditioning_event=_hx_event(hit.key, hit.n), spec=_hx_spec(forecast_date))
        for h in range(1, horizons + 1)
    ]
    return TermSet(terms=terms, coverage="full", reason=None, **common)
