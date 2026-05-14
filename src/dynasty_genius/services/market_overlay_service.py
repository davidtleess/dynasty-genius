"""Market overlay divergence engine.

Computes within-position percentile-rank divergence between Engine B
projections (projection_2y) and FantasyCalc market values, then assigns
a divergence_flag and position-specific caveats to each PVO.

Leakage rule: no field from MarketOverlay may enter Engine A or Engine B
training or inference. This module only writes to PVO.market_overlay.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.dynasty_genius.models.player_value_object import PlayerValueObject

# 10 percentile points ≈ one dynasty tier. Configurable — review after 2 months.
NOISE_BAND: float = 0.10

# 12-team Superflex PPR replacement baselines (from Phase 9 spec)
_VAR_REPLACEMENT_LEVEL: dict[str, int] = {
    "QB": 25,
    "RB": 33,
    "WR": 53,
    "TE": 13,
}

_ROOKIE_PEAK_WINDOW_START = (4, 1)   # April 1
_ROOKIE_PEAK_WINDOW_END   = (7, 1)   # July 1

_DIVERGENCE_FLAGS = frozenset({
    "aligned",
    "model_higher_than_market",
    "model_lower_than_market",
    "model_unreliable",
    "model_uninformative_rookie",
})


def pct_rank(values: list[float], x: float) -> float:
    """Percentile rank using mid-rank for ties: (less + 0.5*equal) / n."""
    n = len(values)
    if n < 2:
        return 0.5
    less = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return (less + 0.5 * equal) / n


def _classify_flag(delta: float, pvo: "PlayerValueObject") -> str:
    if pvo.model_grade == "EXPERIMENTAL" or pvo.position == "TE":
        return "model_unreliable"
    if abs(delta) < NOISE_BAND:
        return "aligned"
    return "model_higher_than_market" if delta > 0 else "model_lower_than_market"


def _is_rookie_peak_window() -> bool:
    today = date.today()
    start = _ROOKIE_PEAK_WINDOW_START
    end = _ROOKIE_PEAK_WINDOW_END
    m, d = today.month, today.day
    after_start = (m, d) >= start
    before_end  = (m, d) < end
    return after_start and before_end


def _attach_position_caveats(
    pvo: "PlayerValueObject",
    flag: str,
    delta: float,
) -> list[str]:
    caveats: list[str] = []
    pos = pvo.position or ""
    age = pvo.age or 0.0

    if pos == "TE":
        caveats += ["te_model_experimental_do_not_trade_on", "te_market_high_variance"]
    elif pos == "RB":
        if flag == "model_higher_than_market" and age >= 26:
            caveats.append("rb_cliff_watch")
        elif flag == "model_lower_than_market" and age <= 25:
            caveats.append("rb_youth_premium")

    if pvo.is_prospect:
        caveats.append("model_uninformative_rookie")
        if _is_rookie_peak_window():
            caveats.append("rookie_peak_value_window")

    return caveats


def compute_divergence(pvo_list: list["PlayerValueObject"], fc_response: list[dict]) -> None:
    """Mutates market_overlay on each PVO. No return value.

    Join key: pvo.sleeper_id → fc_entry["player"]["sleeperId"].
    Market percentile uses the full FC response as the cohort.
    Model percentile uses the PVOs in pvo_list that have a projection_2y.
    """
    from src.dynasty_genius.models.player_value_object import MarketOverlay

    fetch_ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build FC lookup and per-position market cohort from full response
    fc_by_sleeper: dict[str, dict] = {}
    fc_market_by_position: dict[str, list[float]] = defaultdict(list)
    for entry in fc_response:
        player = entry.get("player", {})
        sid = player.get("sleeperId")
        pos = player.get("position", "")
        val = entry.get("value")
        if sid:
            fc_by_sleeper[str(sid)] = entry
        if pos and val is not None:
            fc_market_by_position[pos].append(float(val))

    # Build per-position model cohort from pvo_list
    model_vals_by_position: dict[str, list[float]] = defaultdict(list)
    for pvo in pvo_list:
        if pvo.projection_2y is not None and pvo.position:
            model_vals_by_position[pvo.position].append(pvo.projection_2y)

    for pvo in pvo_list:
        sleeper_id = pvo.sleeper_id
        if not sleeper_id:
            continue

        fc_entry = fc_by_sleeper.get(str(sleeper_id))
        if fc_entry is None:
            continue  # no FC match — leave market_overlay as None

        overlay = MarketOverlay(
            source="fantasycalc",
            market_value=fc_entry.get("value"),
            trend_delta=fc_entry.get("trend30Day"),
            market_volatility=fc_entry.get("maybeMovingStandardDeviation"),
            position_rank=fc_entry.get("positionRank"),
            overall_rank=fc_entry.get("overallRank"),
            source_timestamp=fetch_ts,
            caveats=["source_timestamp_is_fetch_time_not_publish_time"],
        )
        pvo.market_overlay = overlay

        # Rookie / no-projection case
        if pvo.projection_2y is None:
            overlay.divergence_flag = "model_uninformative_rookie"
            overlay.caveats += _attach_position_caveats(pvo, "model_uninformative_rookie", 0.0)
            continue

        position = pvo.position or ""
        market_cohort = fc_market_by_position.get(position, [])
        model_cohort = model_vals_by_position.get(position, [])

        if not market_cohort or not model_cohort:
            continue

        m_pct = pct_rank(model_cohort, pvo.projection_2y)
        k_pct = pct_rank(market_cohort, float(overlay.market_value or 0))
        delta = round(m_pct - k_pct, 3)

        overlay.model_percentile = round(m_pct, 3)
        overlay.market_percentile = round(k_pct, 3)
        overlay.model_minus_market_delta = delta
        flag = _classify_flag(delta, pvo)
        overlay.divergence_flag = flag
        overlay.caveats += _attach_position_caveats(pvo, flag, delta)


def enrich_pvo_list_with_market_overlay(pvo_list: list["PlayerValueObject"]) -> None:
    """Fetch FC data (cached) and compute divergence. Mutates each PVO in place."""
    from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
    fc_data, _caveats = fetch_with_cache()
    if fc_data:
        compute_divergence(pvo_list, fc_data)


def compute_value_above_replacement(
    pvo_list: list["PlayerValueObject"],
) -> None:
    """Mutates pvo.value_above_replacement. Uses dynasty_value_score only — never market_value."""
    by_position: dict[str, list["PlayerValueObject"]] = defaultdict(list)
    for pvo in pvo_list:
        if pvo.position and pvo.dynasty_value_score is not None:
            by_position[pvo.position].append(pvo)

    for pos, pvos_at_pos in by_position.items():
        sorted_pvos = sorted(pvos_at_pos, key=lambda p: p.dynasty_value_score or 0, reverse=True)
        n = _VAR_REPLACEMENT_LEVEL.get(pos, len(sorted_pvos))
        # Replacement player is the Nth (0-indexed: n-1), or last if fewer than N
        idx = min(n - 1, len(sorted_pvos) - 1)
        replacement_score = sorted_pvos[idx].dynasty_value_score or 0.0
        for pvo in pvos_at_pos:
            pvo.value_above_replacement = round((pvo.dynasty_value_score or 0.0) - replacement_score, 3)

    # Players with no dynasty_value_score stay None (already default)
