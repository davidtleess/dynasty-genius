"""Realized-Outcome Loop T4 — pure realized-outcome scorer.

Joins captured predictions (T1 companion snapshots), point-in-time identity resolution
(T2 bridge), and realized weekly outcome facts (T3) into within-position RANK accuracy
metrics + a Model Input Fidelity (MIF) audit. Pure functions only — every input is
injected; no I/O, no store reads, no wall-clock.

Headline framing (spec §5): the loop LEADS with within-position rank accuracy and MIF (a
**utilization-deviation audit of the model's inputs**, NOT a player verdict). Every emitted
row and the scorecard root carry ``decision_supported=False``; market data never enters.

Honesty guards:
- **Power floor** — a cohort surfaces numeric rank metrics only with ≥10 rank-eligible
  players (matching ``compute_rank_correlation``'s built-in NaN-below-10 floor) AND maturity
  (a partial player needs ≥4 eligible games); otherwise ``status="power_floor_not_met"`` with
  no surfaced numbers. No maturity-weighting of rank metrics exists.
- **Survivorship-complete** — a disappeared (0-game) SETTLED player is never dropped; it is
  kept in its cohort with the position 5th-percentile realized outcome of the settled
  survivors (Gate-4 parity), computed here from the cohort itself (single source of truth).
- **MIF early gate** — a model-input field gets a 4-week realized-rolling delta only once the
  player has ≥4 eligible games; before that the field is ``partial_window`` with no value.
  Diagnostic-only fields are never scored.
- **Settled vs partial** — an in-season player is ``partial`` (maturity < 100); never
  ``settled`` before the 2-year horizon completes.

Metric-CI surface (spec §5.1): Spearman/Kendall carry BCa CIs; NDCG is a point estimate (NO
CI); precision@k is MODEL-ONLY (no market, no ``diff_wilson_ci95``).

Design spec: docs/superpowers/specs/2026-06-27-realized-outcome-loop-design.md (§5/§6).
"""
from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from src.dynasty_genius.eval.backtest_metrics import (
    compute_ndcg,
    compute_rank_correlation,
)

# Cohort surfaces numeric rank metrics only at/above this size (matches the rank fn's NaN<10).
POWER_FLOOR_MIN_COHORT = 10
# A partial player needs this many played games to be rank-eligible / MIF-eligible.
ELIGIBLE_GAMES_MIN = 4
# 2-year settlement horizon, in cumulative game-weeks (2 x 17-game seasons); GREEN-time calib.
SETTLEMENT_HORIZON_WEEKS = 34
# Disappeared-player survivorship penalty: the cohort's settled-survivor 5th percentile.
SURVIVORSHIP_PERCENTILE = 5.0
# Realized utilization rolling window for MIF (spec §5.2: 4 weeks, not 1-2 game-script noise).
MIF_ROLLING_WEEKS = 4
# Within-position top-k for NDCG / precision@k (capped at cohort size).
TOP_K = 12

# Prediction-time util field -> realized weekly-util field (T1 name -> T3 realized name).
_UTIL_FIELD_TO_REALIZED = {
    "snap_share": "snap_share_realized",
    "route_participation": "route_participation_realized",
    "target_share_nfl": "target_share_nfl_realized",
}


class RealizedOutcomeScoringValidationError(ValueError):
    """A non-finite/invalid prediction or outcome value (fail-closed; never silently scored)."""


def _finite(value: Any, *, field: str) -> Optional[float]:
    """Finite float or None; raise on wrong-type / non-finite (NaN/inf)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RealizedOutcomeScoringValidationError(
            f"{field} must be a real number or None, got {value!r}"
        )
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise RealizedOutcomeScoringValidationError(
            f"{field} must be finite, got {value!r}"
        )
    return fvalue


def _resolution_field(resolution: Any, field: str) -> Any:
    """Read a bridge-resolution field tolerantly: the production T2 bridge returns a
    ``BridgeResolution`` dataclass while injected test fakes return a plain dict."""
    if resolution is None:
        return None
    if isinstance(resolution, dict):
        return resolution.get(field)
    return getattr(resolution, field, None)


def compute_model_precision_at_k(
    model_top_k: set[str], realized_top_k: set[str], k: int
) -> dict[str, Any]:
    """Model-only precision@k (v1 excludes market): hit rate of the model's top-k against the
    realized top-k. Deliberately NO ``diff_wilson_ci95`` / market output."""
    hits = len(set(model_top_k) & set(realized_top_k))
    return {"model_hit_rate": (hits / k) if k else 0.0, "hits": hits, "k": k}


def _rolling_realized_util(
    weekly_util: list[dict[str, Any]], realized_field: str
) -> Optional[float]:
    """Mean of the last ``MIF_ROLLING_WEEKS`` weeks' realized value for one field, over weeks
    whose per-field status is ``ok``. Returns None when no usable value (fail-closed)."""
    ordered = sorted(weekly_util, key=lambda row: row.get("week", 0))
    values: list[float] = []
    for week_row in ordered[-MIF_ROLLING_WEEKS:]:
        field = week_row.get(realized_field) or {}
        if field.get("status") == "ok" and field.get("value") is not None:
            value = _finite(field.get("value"), field=realized_field)
            if value is not None:
                values.append(value)
    return float(np.mean(values)) if values else None


def _model_input_fidelity(
    prediction: dict[str, Any], weekly_util: list[dict[str, Any]], *, eligible: bool
) -> dict[str, dict[str, Any]]:
    """Per prediction-time util field: diagnostic_only -> not scored; model_input -> a 4-week
    realized-rolling delta once the player is eligible (≥4 games), else ``partial_window``."""
    mif: dict[str, dict[str, Any]] = {}
    utilization = prediction.get("utilization") or {}
    for field, snapshot in utilization.items():
        role = (snapshot or {}).get("role")
        if role != "model_input":
            mif[field] = {"status": "diagnostic_only"}
            continue
        if not eligible:
            mif[field] = {"status": "partial_window"}
            continue
        predicted_value = _finite((snapshot or {}).get("value"), field=field)
        realized_field = _UTIL_FIELD_TO_REALIZED.get(field)
        rolling = (
            _rolling_realized_util(weekly_util, realized_field)
            if realized_field
            else None
        )
        if rolling is None or predicted_value is None:
            mif[field] = {"status": "unavailable"}
        else:
            mif[field] = {"status": "ok", "delta": rolling - predicted_value}
    return mif


def _rank_of(values: list[float]) -> list[int]:
    """Dense competition ranks (1 = highest value); ties share the higher rank."""
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    ranks = [0] * len(values)
    for position, idx in enumerate(order, start=1):
        ranks[idx] = position
    return ranks


def _cohort_metric(eligible: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank metrics for one position's rank-eligible members, or a power-floor stub."""
    base = {
        "eligible_count": None,  # set by caller (cohort membership, not rank-eligible count)
        "spearman": {"value": None, "bca_ci": None},
        "kendall": {"value": None, "bca_ci": None},
        "ndcg": {"value": None},
        "precision_at_k": {"value": None, "k": None, "truth_def": None},
        "status": "power_floor_not_met",
    }
    if len(eligible) < POWER_FLOOR_MIN_COHORT:
        return base

    predicted = [m["predicted_ppg"] for m in eligible]
    realized = [m["realized_ppg"] for m in eligible]
    kendall_tau, kendall_ci, spearman_rho, spearman_ci = compute_rank_correlation(
        predicted, realized
    )
    if not math.isfinite(spearman_rho):  # defensive: built-in floor already gated above
        return base

    k = min(len(eligible), TOP_K)
    predicted_ranks = _rank_of(predicted)
    realized_ranks = _rank_of(realized)
    model_top_k = {m["gsis_id"] for m, r in zip(eligible, predicted_ranks) if r <= k}
    realized_top_k = {m["gsis_id"] for m, r in zip(eligible, realized_ranks) if r <= k}
    precision = compute_model_precision_at_k(model_top_k, realized_top_k, k)

    return {
        "eligible_count": None,
        "spearman": {"value": spearman_rho, "bca_ci": spearman_ci},
        "kendall": {"value": kendall_tau, "bca_ci": kendall_ci},
        "ndcg": {"value": compute_ndcg(predicted_ranks, realized, k)},
        "precision_at_k": {
            "value": precision["model_hit_rate"],
            "k": k,
            "truth_def": "realized_top_k_within_position",
            "hits": precision["hits"],
        },
        "status": "ok",
    }


def score(
    predictions: list[dict[str, Any]],
    outcomes: dict[str, Any],
    bridge: Any,
    as_of_week: int,
) -> dict[str, Any]:
    """Score the frozen model's predictions vs realized outcomes (pure; all inputs injected)."""
    players_outcomes = (outcomes or {}).get("players") or {}
    settled = as_of_week >= SETTLEMENT_HORIZON_WEEKS
    maturity_pct = min(100.0, (as_of_week / SETTLEMENT_HORIZON_WEEKS) * 100.0)
    settlement_status = "settled" if settled else "partial"

    excluded_counts: dict[str, int] = {}

    def _exclude(reason: str) -> None:
        excluded_counts[reason] = excluded_counts.get(reason, 0) + 1

    # ── pass 1: resolve identity, validate, build per-player records ──
    records: list[dict[str, Any]] = []
    for prediction in predictions:
        predicted_ppg = _finite(prediction.get("projection_2y"), field="projection_2y")
        resolution = bridge.resolve(
            prediction.get("sleeper_id"), prediction.get("capture_date")
        )
        if _resolution_field(resolution, "resolution_status") != "resolved":
            _exclude("identity_unresolved")
            continue
        gsis_id = _resolution_field(resolution, "gsis_id")
        entry = players_outcomes.get(gsis_id)
        if entry is None:
            _exclude("missing_outcome")
            records.append(
                {
                    "prediction": prediction,
                    "gsis_id": gsis_id,
                    "position": prediction.get("position"),
                    "predicted_ppg": predicted_ppg,
                    "has_outcome": False,
                    "games_played": 0,
                    "realized_ppg": None,
                    "outcome": {},
                    "weekly_util": [],
                }
            )
            continue
        outcome = entry.get("outcome") or {}
        records.append(
            {
                "prediction": prediction,
                "gsis_id": gsis_id,
                "position": prediction.get("position"),
                "predicted_ppg": predicted_ppg,
                "has_outcome": True,
                "games_played": int(outcome.get("games_played") or 0),
                "realized_ppg": _finite(outcome.get("ppg_to_date"), field="ppg_to_date"),
                "player_status": outcome.get("player_status"),
                "outcome": outcome,
                "weekly_util": entry.get("weekly_util") or [],
            }
        )

    # ── survivorship floor: position 5th-pct of SETTLED survivors' realized PPG ──
    survivor_ppgs: dict[str, list[float]] = {}
    if settled:
        for record in records:
            if (
                record["has_outcome"]
                and record["games_played"] >= 1
                and record["realized_ppg"] is not None
            ):
                survivor_ppgs.setdefault(record["position"], []).append(
                    record["realized_ppg"]
                )
    survivorship_floor: dict[str, Optional[float]] = {
        position: float(np.percentile(ppgs, SURVIVORSHIP_PERCENTILE))
        for position, ppgs in survivor_ppgs.items()
    }

    # ── pass 2: finalize realized value + eligibility + tracking rows ──
    tracking_rows: list[dict[str, Any]] = []
    # Cohort membership = resolved + has-outcome; a resolved player still registers its
    # position even with no outcome (the cohort then reads power_floor_not_met).
    cohort_members: dict[str, int] = {}
    rank_eligible: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        position = record["position"]
        cohort_members.setdefault(position, 0)
        realized = record["realized_ppg"]
        realized_outcome_status = "observed" if record["has_outcome"] else "missing_outcome"
        is_rank_eligible = False

        if record["has_outcome"]:
            cohort_members[position] += 1
            if settled and record["games_played"] == 0:
                floor = survivorship_floor.get(position)
                if floor is not None:
                    realized = floor
                    realized_outcome_status = "survivorship_floor_applied"
                    is_rank_eligible = True
                else:
                    realized_outcome_status = "survivorship_floor_unavailable"
            elif settled and realized is not None:
                is_rank_eligible = True
            elif (not settled) and record["games_played"] >= ELIGIBLE_GAMES_MIN and realized is not None:
                is_rank_eligible = True

        mif_eligible = record["games_played"] >= ELIGIBLE_GAMES_MIN
        delta = (
            realized - record["predicted_ppg"]
            if realized is not None and record["predicted_ppg"] is not None
            else None
        )
        tracking_rows.append(
            {
                "gsis_id": record["gsis_id"],
                "position": position,
                "predicted_ppg": record["predicted_ppg"],
                "realized_ppg_to_date": realized,
                "realized_vs_expected_delta": delta,
                "realized_outcome_status": realized_outcome_status,
                "maturity_pct": maturity_pct,
                "settlement_status": settlement_status,
                "model_input_fidelity": _model_input_fidelity(
                    record["prediction"], record["weekly_util"], eligible=mif_eligible
                ),
                "decision_supported": False,
            }
        )
        if is_rank_eligible:
            rank_eligible.setdefault(position, []).append(
                {"gsis_id": record["gsis_id"], "predicted_ppg": record["predicted_ppg"], "realized_ppg": realized}
            )

    # ── cohort metrics per position (every resolved position registers a cohort) ──
    cohort_metrics: dict[str, Any] = {}
    for position, member_count in cohort_members.items():
        metric = _cohort_metric(rank_eligible.get(position, []))
        metric["eligible_count"] = member_count
        metric["decision_supported"] = False
        cohort_metrics[position] = metric

    return {
        "as_of_week": as_of_week,
        "settlement_status": settlement_status,
        "tracking_rows": tracking_rows,
        "cohort_metrics": cohort_metrics,
        "excluded_counts": excluded_counts,
        "decision_supported": False,
    }
