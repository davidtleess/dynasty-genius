"""DG-018 — the standing model-versus-market grade.

The realized-outcome loop grades the model against reality and says so in its own
docstring: "market data never enters" (``realized_outcome_scorer`` line 10). That is the
right design for what it measures and it structurally cannot answer the question DG-018
was filed for — *does the model beat free consensus pricing?* This module is the missing
half. It ranks the same players by the model and by the market, grades BOTH against the
SAME realized outcomes, and reports the paired difference with its interval.

Three rules are load-bearing, and each exists because this project has been burned:

1. **The denominator ships on the face of the card.** The paired difference is computed
   only on players both sides price. On the declared frozen set (2026-08-05) that is 304
   of 501 model predictions against 474 market rows — leaving 197 the model prices and the
   market does not, and 170 the reverse. Reporting the 304 without the 367 would be the
   trap. Those counts are required output, never a footnote. The asymmetry is also the
   most interesting thing on the card: what the market declines to price is where an edge
   would live if there is one.

2. **A null is a result.** If the interval contains zero, ``beats_market`` is ``None`` and
   the number is reported straddling zero. Nothing here may suppress a null, widen a
   cohort, or re-roll a seed toward a signal.

3. **Skill, not agreement.** Neither side is ever scored against the other. A model
   identical to the market scores a difference of exactly zero — agreeing with consensus
   earns nothing by itself.

Pure functions only: every input is injected, there is no I/O, no store read and no
wall-clock. ``decision_supported`` is False on the card root, as everywhere in this repo.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

from src.dynasty_genius.eval.backtest_metrics import (
    compute_ndcg_diff_bootstrap,
    compute_rank_correlation,
)

# A cohort surfaces numbers only at or above this size. Matches the realized-outcome
# scorer's floor and ``compute_rank_correlation``'s own NaN-below-10 behaviour, so the two
# scorecards cannot disagree about whether a position had enough players to speak.
POWER_FLOOR_MIN_COHORT = 10

# Within-position top-k for NDCG, capped at the cohort size by the metric itself.
TOP_K = 12

SCORED_POSITIONS = ("QB", "RB", "WR", "TE")


def _finite(value: Any) -> Optional[float]:
    """A usable float, or None. NaN and infinity are absences, not values."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _ranks_desc(values: list[float]) -> list[int]:
    """Competition ranks, 1 = best, ordering by value descending.

    Ties take the same rank, which is what ``compute_ndcg`` expects (it divides by
    ``log2(rank + 1)``, so ranks must start at 1 and never be zero or negative).
    """
    order = sorted(range(len(values)), key=lambda i: -values[i])
    ranks = [0] * len(values)
    previous: Optional[float] = None
    previous_rank = 0
    for position, index in enumerate(order, start=1):
        if previous is not None and values[index] == previous:
            ranks[index] = previous_rank
        else:
            ranks[index] = position
            previous_rank = position
            previous = values[index]
    return ranks


def _spearman(predicted: list[float], realized: list[float]) -> Optional[float]:
    """Spearman rho against realized outcomes, or None below the metric's own floor."""
    _tau, _tau_ci, rho, _rho_ci = compute_rank_correlation(predicted, realized)
    return rho if math.isfinite(rho) else None


def _index_by_player(rows: Iterable[dict[str, Any]], value_key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        player = row.get("sleeper_id")
        if player is None:
            continue
        out[str(player)] = {"row": row, "raw": row.get(value_key)}
    return out


def score_model_vs_market(
    *,
    model_predictions: list[dict[str, Any]],
    market_snapshot: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    top_k: int = TOP_K,
) -> dict[str, Any]:
    """Grade the model and the market against the same realized outcomes.

    ``model_predictions``: rows carrying ``sleeper_id``, ``position``, ``projection_2y``.
    ``market_snapshot``:   rows carrying ``sleeper_id``, ``position``, ``value`` (higher is
                           better — a price, not a rank).
    ``outcomes``:          ``{sleeper_id: {"ppg": float, "games_played": int}}``.

    Returns a card whose every position block carries its own paired count and the counts
    it could NOT pair, plus a card-level coverage roll-up over the same numbers.
    """
    model_by_player = _index_by_player(model_predictions, "projection_2y")
    market_by_player = _index_by_player(market_snapshot, "value")

    positions: dict[str, Any] = {}
    roll_up = {"paired_n": 0, "model_only_n": 0, "market_only_n": 0, "no_outcome_n": 0}

    seen_positions: list[str] = []
    for row in list(model_predictions) + list(market_snapshot):
        position = row.get("position")
        if position and position not in seen_positions:
            seen_positions.append(position)

    for position in seen_positions:
        model_ids = {p for p, v in model_by_player.items() if v["row"].get("position") == position}
        market_ids = {p for p, v in market_by_player.items() if v["row"].get("position") == position}

        excluded = {"nonfinite_prediction": 0, "nonfinite_market_value": 0}
        paired_players: list[str] = []
        model_values: list[float] = []
        market_values: list[float] = []
        realized: list[float] = []
        no_outcome = 0

        for player in sorted(model_ids & market_ids):
            outcome = outcomes.get(player)
            realized_ppg = _finite((outcome or {}).get("ppg"))
            if outcome is None or realized_ppg is None:
                no_outcome += 1
                continue
            predicted = _finite(model_by_player[player]["raw"])
            price = _finite(market_by_player[player]["raw"])
            # An absent number is an absence, never a zero and never a silent rank.
            if predicted is None:
                excluded["nonfinite_prediction"] += 1
                continue
            if price is None:
                excluded["nonfinite_market_value"] += 1
                continue
            paired_players.append(player)
            model_values.append(predicted)
            market_values.append(price)
            realized.append(realized_ppg)

        model_only_n = len(model_ids - market_ids)
        market_only_n = len(market_ids - model_ids)
        paired_n = len(paired_players)

        block: dict[str, Any] = {
            "paired_n": paired_n,
            "model_only_n": model_only_n,
            "market_only_n": market_only_n,
            "no_outcome_n": no_outcome,
            "excluded": excluded,
            "scored_on": "paired_only",
            "ndcg_diff": None,
            "ndcg_diff_ci95": None,
            "beats_market": None,
            "model": {"spearman": None, "ndcg": None},
            "market": {"spearman": None, "ndcg": None},
            "decision_supported": False,
        }

        roll_up["paired_n"] += paired_n
        roll_up["model_only_n"] += model_only_n
        roll_up["market_only_n"] += market_only_n
        roll_up["no_outcome_n"] += no_outcome

        if paired_n < POWER_FLOOR_MIN_COHORT:
            block["status"] = "power_floor_not_met"
            positions[position] = block
            continue

        k = min(top_k, paired_n)
        model_ranks = _ranks_desc(model_values)
        market_ranks = _ranks_desc(market_values)
        bootstrap = compute_ndcg_diff_bootstrap(model_ranks, market_ranks, realized, k)

        diff = bootstrap.get("ndcg_diff")
        ci = bootstrap.get("ndcg_diff_bca_ci95")
        block["status"] = "scored"
        block["ndcg_diff"] = diff
        # A list, not a tuple: the runner writes this card to disk and a re-read must equal
        # what was returned. JSON has no tuple, so a tuple here would make the artifact and
        # the return value differ — the sort of gap where a card drifts from its own record.
        block["ndcg_diff_ci95"] = [float(ci[0]), float(ci[1])] if ci is not None else None
        if bootstrap.get("caveat"):
            block["caveat"] = bootstrap["caveat"]
        block["model"] = {
            "spearman": _spearman(model_values, realized),
            "ndcg": _ndcg(model_ranks, realized, k),
        }
        block["market"] = {
            "spearman": _spearman(market_values, realized),
            "ndcg": _ndcg(market_ranks, realized, k),
        }
        # A verdict ONLY when the interval clears zero. An interval containing zero is a
        # null and is reported as one — never rounded into a win or a loss.
        if diff is not None and ci is not None:
            low, high = float(ci[0]), float(ci[1])
            if low > 0:
                block["beats_market"] = True
            elif high < 0:
                block["beats_market"] = False
            else:
                block["beats_market"] = None
        positions[position] = block

    return {
        "schema_version": "model_vs_market.v1",
        "positions": positions,
        "coverage": roll_up,
        "power_floor_min_cohort": POWER_FLOOR_MIN_COHORT,
        "decision_supported": False,
    }


def _ndcg(ranks: list[int], realized: list[float], k: int) -> Optional[float]:
    from src.dynasty_genius.eval.backtest_metrics import compute_ndcg

    value = compute_ndcg(ranks, realized, k)
    return value if math.isfinite(value) else None
