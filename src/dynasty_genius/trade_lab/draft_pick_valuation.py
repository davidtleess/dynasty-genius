"""Phase 24 — Dynasty rookie draft-pick valuation (historical slot curve).

Pure module: reads a versioned curve artifact and prices a pick in xVAR.
Model-blind beyond the curve artifact — no Engine A/B scoring, no PVO, no market.
The curve is built from realized rookie outcomes via the "first-36-skill-players-in-
NFL-draft-order = the FF rookie board" bridge; pick values are NFL-derived historical
expectations, not market-measured prices. Every output is ``decision_supported=False``.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_A_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_A,
)
from src.dynasty_genius.scoring.engine_a import ENGINE_A_P90_PPG

_SKILL = ("QB", "RB", "WR", "TE")

# Required caveat set on every pick value (§6 governance).
_BASE_PICK_CAVEATS = [
    "pick_value_historical_expected",
    "pick_value_thin_sample",
    "decision_supported_false",
]


# ── Per-player conversion ───────────────────────────────────────────────────


def player_xvar_from_ppg(y24_ppg: float, position: str) -> float:
    """Realized Year-2+3 PPG -> DVS (clamped 0-100) -> xVAR, using position constants.

    DVS = clamp(y24_ppg / P90_pos * 100, 0, 100);
    xVAR = (DVS - ENGINE_A_REPLACEMENT_DVS[pos]) * XVAR_LAMBDA_ENGINE_A[pos].
    Sub-replacement outcomes are intentionally NOT clamped (xVAR may be negative).
    """
    p90 = ENGINE_A_P90_PPG[position]
    dvs = max(0.0, min(100.0, y24_ppg / p90 * 100.0))
    return (dvs - ENGINE_A_REPLACEMENT_DVS[position]) * XVAR_LAMBDA_ENGINE_A[position]


def _pctl(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    idx = (len(xs) - 1) * q / 100.0
    lo, hi = int(idx), min(int(idx) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (idx - lo)


def _mad(xs: list[float]) -> float:
    med = statistics.median(xs)
    return statistics.median([abs(x - med) for x in xs])


# ── SF-QB ordering knob ─────────────────────────────────────────────────────


def _adjusted_order(
    picks_positions: list[tuple[int, str]], k_slots: int, round_threshold_pick: int
) -> list[int]:
    """Return original indices reordered by a stable adjusted-index sort.

    A qualifying QB gets key ``i - k_slots - 0.5`` so it edges just ahead of the
    incumbent at slot ``i-k``; the half-offset guarantees no ties with the integer
    keys of non-QBs, and multiple QBs keep their original relative order.
    """
    def _key(i: int) -> float:
        pick, pos = picks_positions[i]
        if pos == "QB" and pick <= round_threshold_pick:
            return i - k_slots - 0.5
        return float(i)

    return sorted(range(len(picks_positions)), key=_key)


def apply_sf_qb_ordering(
    board: list[tuple[int, str]], k_slots: int = 0, round_threshold_pick: int = 256
) -> list[tuple[int, str]]:
    """Promote qualifying QBs up by ``k_slots`` before slot aggregation.

    ``board`` is an ordered list of ``(pick, position)``. With ``k_slots <= 0`` the
    board is returned unchanged (SF-QB knob off — the v1 default).
    """
    if k_slots <= 0:
        return list(board)
    order = _adjusted_order(board, k_slots, round_threshold_pick)
    return [board[i] for i in order]


# ── Curve builder ───────────────────────────────────────────────────────────


def build_slot_curve(
    df,  # pandas DataFrame: draft_year, pick, position, y24_ppg, low_sample_flag
    mature_years: tuple[int, ...],
    board_size: int = 36,
    sf_qb_promote_slots: int = 0,
    round_threshold_pick: int = 256,
) -> dict:
    """Build the per-slot xVAR curve from mature classes via the 36-skill bridge."""
    per_slot_samples: dict[int, list[float]] = {k: [] for k in range(1, board_size + 1)}
    per_slot_positions: dict[int, Counter] = {k: Counter() for k in range(1, board_size + 1)}
    per_slot_lowflags: dict[int, int] = {k: 0 for k in range(1, board_size + 1)}
    years_used: list[int] = []

    for year in sorted(mature_years):
        cls = df[(df["draft_year"] == year) & (df["position"].isin(_SKILL))]
        cls = cls.sort_values("pick")
        board = cls.head(board_size)
        if board.empty:
            continue
        years_used.append(year)
        rows = [row for _, row in board.iterrows()]
        if sf_qb_promote_slots > 0:
            pp = [(int(r["pick"]), str(r["position"])) for r in rows]
            order = _adjusted_order(pp, sf_qb_promote_slots, round_threshold_pick)
            rows = [rows[i] for i in order]
        for slot, row in enumerate(rows, start=1):
            xv = player_xvar_from_ppg(float(row["y24_ppg"]), str(row["position"]))
            per_slot_samples[slot].append(xv)
            per_slot_positions[slot][str(row["position"])] += 1
            per_slot_lowflags[slot] += int(bool(row.get("low_sample_flag", 0)))

    slots: dict[str, dict] = {}
    for slot in range(1, board_size + 1):
        samples = per_slot_samples[slot]
        if not samples:
            continue
        slots[str(slot)] = {
            "expected_xvar": round(statistics.median(samples), 4),
            "mean_xvar": round(statistics.fmean(samples), 4),
            "n_years": len(samples),
            "p25": round(_pctl(samples, 25), 4),
            "p75": round(_pctl(samples, 75), 4),
            "mad": round(_mad(samples), 4),
            "low_sample_count": per_slot_lowflags[slot],
            "positions": dict(per_slot_positions[slot]),
            "raw_samples": [round(v, 4) for v in samples],
        }
    return {
        "version": "v1",
        "board_size": board_size,
        "mature_years_used": years_used,
        "slots": slots,
    }


def smooth_and_tier(curve: dict) -> dict:
    """Add a monotonic non-increasing clamp (running-min) per slot + tier rollups.

    ``expected_xvar_smoothed`` is a conservative clamp, NOT statistical smoothing: a
    slot-N pick must not be worth more than slot N-1. Tier value = median (locked for
    v1; not trimmed-mean) of its member slots' post-clamp values.
    """
    board = curve["board_size"]
    running = None
    for slot in range(1, board + 1):
        s = curve["slots"].get(str(slot))
        if s is None:
            continue
        val = s["expected_xvar"] if running is None else min(s["expected_xvar"], running)
        s["expected_xvar_smoothed"] = round(val, 4)
        running = val

    tier_map = curve.get("tier_map", {})
    tiers: dict[str, float] = {}
    for tier, slots in tier_map.items():
        vals = [
            curve["slots"][str(k)]["expected_xvar_smoothed"]
            for k in slots
            if str(k) in curve["slots"]
        ]
        if vals:
            tiers[tier] = round(statistics.median(vals), 4)
    curve["tiers"] = tiers
    return curve


# ── Public valuation API ────────────────────────────────────────────────────


class PickValue(BaseModel):
    year: int
    round_: int
    slot: Optional[int] = None
    tier: Optional[str] = None
    xvar: Optional[float]
    resolution: Literal["exact_slot", "tier", "round_tier", "unresolved"]
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


def value_pick(
    year: int,
    round_: int,
    *,
    slot: Optional[int] = None,
    tier: Optional[str] = None,
    curve: dict,
    sf_qb_knob_active: bool = False,
) -> PickValue:
    """Price a pick in xVAR against a loaded curve. No position argument.

    Resolution order: exact ``slot`` -> explicit ``tier`` -> round-only generic tier
    (``round_{round_}_generic``, for reconstructed future picks that know only the
    round) -> ``unresolved``.
    """
    caveats = list(_BASE_PICK_CAVEATS)
    if sf_qb_knob_active:
        caveats.append("sf_qb_ordering_assumption")

    if slot is not None:
        s = curve.get("slots", {}).get(str(slot))
        xv = s.get("expected_xvar_smoothed") if s else None
        return PickValue(
            year=year, round_=round_, slot=slot, xvar=xv,
            resolution="exact_slot" if xv is not None else "unresolved",
            caveats=caveats,
        )

    if tier is not None:
        xv = curve.get("tiers", {}).get(tier)
        return PickValue(
            year=year, round_=round_, tier=tier, xvar=xv,
            resolution="tier" if xv is not None else "unresolved",
            caveats=caveats,
        )

    # Round-only path: reconstructed future picks know only (year, round).
    round_tier = f"round_{round_}_generic"
    xv = curve.get("tiers", {}).get(round_tier)
    if xv is not None:
        return PickValue(
            year=year, round_=round_, tier=round_tier, xvar=xv,
            resolution="round_tier",
            caveats=caveats + ["generic_future_pick_round_only"],
        )
    return PickValue(
        year=year, round_=round_, xvar=None, resolution="unresolved", caveats=caveats
    )


def load_curve(path: str | Path) -> dict:
    """Read a versioned draft-pick value curve artifact from disk."""
    return json.loads(Path(path).read_text())
