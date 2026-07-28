"""DG2-S0-01 — rebase the model/market divergence onto a common cohort.

The shipped divergence ranks a player's model value against the MODEL-backed population
and its market value against the MARKET-priced population, then subtracts the two
percentiles (`universe_market_divergence.py`). Those are different populations, so the
subtraction is not like-for-like: the 60th percentile of 300 model rows and the 60th
percentile of 500 market rows describe different positions in different fields.

This module defines the COMMON cohort — players carrying both a model-backed xVAR and a
market value, per position — and recomputes both percentiles against it, so the delta
compares like with like. It reports the current and rebased quantities side by side and
counts how many rows change noise-band classification.

Descriptive only. It reports quantities, counts, and populations; it issues no
recommendation and every row carries `decision_supported=False`
(00 §Descriptive Tools Issue No Verdicts). Market values are used only to rank the market
lane — they never touch the model value (00 §KTC And Market Data).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from src.dynasty_genius.services.market_overlay_service import NOISE_BAND, pct_rank
from src.dynasty_genius.universe_market_divergence import (
    MODEL_BACKED_ROUTES,
    MODEL_BACKED_STATUSES,
)

INCLUSION_RULE = "model_backed_and_market_priced"


class CohortMismatchError(RuntimeError):
    """Raised when a rebased run cannot be computed on a common cohort.

    The whole point of the ticket is that mismatched populations produce an
    uninterpretable delta, so this refuses BY NAME rather than falling back to them.
    """


@dataclass(frozen=True)
class CohortMember:
    """One player in the common cohort, with the populations it was drawn from."""

    sleeper_id: str
    position: str
    xvar: float
    market_value: float
    model_population: int
    market_population: int
    inclusion_rule: str = INCLUSION_RULE


def _model_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Model-backed rows keyed by sleeper id. A row that is not model-backed carries no
    comparable model value, so it cannot be ranked and is not a cohort candidate.

    Identity is the ROOT ``sleeper_player_id`` — the key production actually emits
    (12,201/12,201 live rows) and the one the shipped consumer reads
    (``universe_market_divergence.py:165``). A nested ``player.sleeper_id`` is read
    NOWHERE and emitted NOWHERE; this module briefly read it, which made every real
    comparison empty while a fixture suite built on the same invention stayed green.
    Position remains nested at ``player.position``, which is where production puts it.
    """
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        player = row.get("player") or {}
        valuation = row.get("valuation") or {}
        sleeper_id = row.get("sleeper_player_id")
        position = player.get("position")
        xvar = valuation.get("xvar")
        if sleeper_id is None or not position or xvar is None:
            continue
        if valuation.get("engine_path") not in MODEL_BACKED_ROUTES:
            continue
        if valuation.get("valuation_status") not in MODEL_BACKED_STATUSES:
            continue
        index[str(sleeper_id)] = {"position": str(position), "xvar": float(xvar)}
    return index


def _market_index(fc_response: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in fc_response:
        player = entry.get("player") or {}
        sleeper_id = player.get("sleeperId")
        position = player.get("position")
        value = entry.get("value")
        if sleeper_id is None or not position or value is None:
            continue
        index[str(sleeper_id)] = {"position": str(position), "market_value": float(value)}
    return index


def common_cohort(rows: list[dict[str, Any]],
                  fc_response: list[dict[str, Any]]) -> dict[str, list[CohortMember]]:
    """The common cohort per position, with its inclusion rule (AC1).

    A player is included when it carries BOTH a model-backed xVAR and a market value, and
    both sides agree on its position. Membership is per position because both percentiles
    are computed within position. Each member records the model and market population it
    was drawn from, so the exclusions are countable rather than silently dropped.
    """
    model = _model_index(rows)
    market = _market_index(fc_response)
    model_population: dict[str, int] = defaultdict(int)
    market_population: dict[str, int] = defaultdict(int)
    for entry in model.values():
        model_population[entry["position"]] += 1
    for entry in market.values():
        market_population[entry["position"]] += 1

    cohort: dict[str, list[CohortMember]] = defaultdict(list)
    for sleeper_id, model_entry in model.items():
        market_entry = market.get(sleeper_id)
        if market_entry is None:
            continue
        position = model_entry["position"]
        if market_entry["position"] != position:
            continue  # a position disagreement is not a like-for-like comparison
        cohort[position].append(CohortMember(
            sleeper_id=sleeper_id,
            position=position,
            xvar=model_entry["xvar"],
            market_value=market_entry["market_value"],
            model_population=model_population[position],
            market_population=market_population[position],
        ))
    for members in cohort.values():
        members.sort(key=lambda m: m.sleeper_id)
    return dict(cohort)


def _is_band_crossing(current_delta: float, rebased_delta: float) -> bool:
    """True when a row moves INTO or OUT OF the noise band.

    This is the ticket's registered phenomenon and the one its falsifier counts: a row
    whose model/market signal appears or disappears because the populations were rebased.
    """
    return (abs(current_delta) < NOISE_BAND) != (abs(rebased_delta) < NOISE_BAND)


def _is_direction_reversal(current_delta: float, rebased_delta: float) -> bool:
    """True when a row OUTSIDE the band on both sides flips sign.

    A distinct phenomenon from a band crossing: the signal never weakens into noise, it
    points the other way. Counting it inside the band-crossing figure is what produced
    133 where the registered contract counts 131 (Codex, 2026-07-27). Mutually exclusive
    with `_is_band_crossing` by construction — a row either changes its in-band status or,
    staying outside it on both sides, changes sign.
    """
    if abs(current_delta) < NOISE_BAND or abs(rebased_delta) < NOISE_BAND:
        return False
    return (current_delta > 0) != (rebased_delta > 0)


def _classify(delta: float) -> str:
    """The shipped noise-band classification, applied identically to both lanes so the
    reclassification count measures the rebase and nothing else."""
    if abs(delta) < NOISE_BAND:
        return "aligned"
    return "model_higher_than_market" if delta > 0 else "model_lower_than_market"


def build_rebased_divergence(rows: list[dict[str, Any]],
                             fc_response: list[dict[str, Any]],
                             *, snapshot_date: str) -> dict[str, Any]:
    """Current and rebased divergence for the same snapshot, side by side (AC2–AC4).

    `current_*` reproduces the shipped mismatched-population computation; `rebased_*`
    ranks both lanes against the common cohort. Refuses by name when no common cohort
    exists, rather than falling back to the populations the ticket exists to fix.
    """
    cohort = common_cohort(rows, fc_response)
    if not cohort:
        raise CohortMismatchError(
            "common_cohort_empty: no player carries both a model-backed xVAR and a "
            "market value, so no like-for-like comparison exists for "
            f"snapshot_date={snapshot_date}")

    model = _model_index(rows)
    market = _market_index(fc_response)
    # The shipped populations, reproduced exactly so `current_*` is a faithful baseline.
    current_model_cohorts: dict[str, list[float]] = defaultdict(list)
    current_market_cohorts: dict[str, list[float]] = defaultdict(list)
    for entry in model.values():
        current_model_cohorts[entry["position"]].append(entry["xvar"])
    for entry in market.values():
        current_market_cohorts[entry["position"]].append(entry["market_value"])

    positions_with_model = {e["position"] for e in model.values()}
    positions_without = sorted(positions_with_model - set(cohort))

    out_rows: list[dict[str, Any]] = []
    for position, members in sorted(cohort.items()):
        rebased_model = [m.xvar for m in members]
        rebased_market = [m.market_value for m in members]
        for member in members:
            current_delta = round(
                pct_rank(current_model_cohorts[position], member.xvar)
                - pct_rank(current_market_cohorts[position], member.market_value), 3)
            rebased_model_pct = round(pct_rank(rebased_model, member.xvar), 3)
            rebased_market_pct = round(pct_rank(rebased_market, member.market_value), 3)
            rebased_delta = round(rebased_model_pct - rebased_market_pct, 3)
            current_class = _classify(current_delta)
            rebased_class = _classify(rebased_delta)
            band_crossing = _is_band_crossing(current_delta, rebased_delta)
            direction_reversal = _is_direction_reversal(current_delta, rebased_delta)
            out_rows.append({
                "sleeper_id": member.sleeper_id,
                "position": position,
                "xvar": member.xvar,
                "current_delta": current_delta,
                "rebased_model_percentile": rebased_model_pct,
                "rebased_market_percentile": rebased_market_pct,
                "rebased_delta": rebased_delta,
                "current_classification": current_class,
                "rebased_classification": rebased_class,
                "band_crossing": band_crossing,
                "direction_reversal": direction_reversal,
                "classification_changed": band_crossing or direction_reversal,
                "decision_supported": False,
            })

    compared = len(out_rows)
    return {
        "snapshot_date": snapshot_date,
        "inclusion_rule": INCLUSION_RULE,
        "compared_rows": compared,
        "cohort_sizes": {p: len(m) for p, m in sorted(cohort.items())},
        "positions_without_common_cohort": positions_without,
        "current_mean_abs_delta": round(
            sum(abs(r["current_delta"]) for r in out_rows) / compared, 4) if compared else 0.0,
        "rebased_mean_abs_delta": round(
            sum(abs(r["rebased_delta"]) for r in out_rows) / compared, 4) if compared else 0.0,
        # Two distinct phenomena, separately named so neither is lost inside the other.
        # The union is reported too, and is exactly their sum (they are mutually exclusive).
        "band_crossing_count": sum(1 for r in out_rows if r["band_crossing"]),
        "direction_reversal_count": sum(1 for r in out_rows if r["direction_reversal"]),
        "classification_change_count": sum(1 for r in out_rows if r["classification_changed"]),
        "noise_band": NOISE_BAND,
        "rows": out_rows,
        "decision_supported": False,
    }
