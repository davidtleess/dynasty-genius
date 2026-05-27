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
    "pick_value_floored_at_replacement",
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
        # Option-value floor: a busted pick is benched/cut -> contributes 0, never
        # negative. Slot expected value is the MEAN of these floored (priced) payoffs
        # (spec §4 Option A) — mean, not median, to preserve long-tail option value.
        priced = [max(0.0, v) for v in samples]
        slots[str(slot)] = {
            "expected_xvar": round(statistics.fmean(priced), 4),
            "mean_xvar": round(statistics.fmean(samples), 4),  # raw mean (audit)
            "n_years": len(samples),
            "p25": round(_pctl(samples, 25), 4),
            "p75": round(_pctl(samples, 75), 4),
            "mad": round(_mad(samples), 4),
            "low_sample_count": per_slot_lowflags[slot],
            "positions": dict(per_slot_positions[slot]),
            "raw_samples": [round(v, 4) for v in samples],
            "priced_samples": [round(v, 4) for v in priced],
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
    resolution: Literal[
        "board_exact_slot", "board_round",
        "exact_slot", "tier", "round_tier", "unresolved",
    ]
    valuation_regime: Literal["prospect_board", "historical_curve"] = "historical_curve"
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


def _value_pick_from_curve(
    year: int,
    round_: int,
    *,
    slot: Optional[int] = None,
    tier: Optional[str] = None,
    curve: dict,
    sf_qb_knob_active: bool = False,
) -> PickValue:
    """Regime B — price a pick against the historical slot curve. No position argument.

    Resolution order: exact ``slot`` -> explicit ``tier`` -> round-only generic tier
    (``round_{round_}_generic``, for reconstructed future picks that know only the
    round) -> ``unresolved``. (``valuation_regime`` defaults to ``historical_curve``.)
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


_ROUND_RANK_RANGES = {1: range(1, 13), 2: range(13, 25), 3: range(25, 37)}

_BOARD_PICK_CAVEATS = [
    "pick_value_board_class_specific",
    "pick_value_floored_at_replacement",
    "pick_value_board_model_output",
    "decision_supported_false",
]

_DEFAULT_CARDS_PATH = (
    Path(__file__).resolve().parents[3] / "resources" / "prospect_cards.json"
)


def load_prospect_board(
    draft_class: int, path: str | Path = _DEFAULT_CARDS_PATH
) -> dict[int, float]:
    """Parse prospect_cards.json into a ``{xvar_class_rank: xvar}`` board for one class.

    Model-blind: reads only the inference artifact (no scorer/Engine/market imports).
    Filters to the requested ``draft_class`` with a non-null rank and numeric ``xvar``.
    Raises ``ValueError`` on a duplicate rank (never silently picks one).
    """
    cards = json.loads(Path(path).read_text())
    board: dict[int, float] = {}
    for card in cards:
        if card.get("draft_class") != draft_class:
            continue
        rank = card.get("xvar_class_rank")
        xvar = card.get("xvar")
        if rank is None or isinstance(xvar, bool) or not isinstance(xvar, (int, float)):
            continue
        rank = int(rank)
        if rank in board:
            raise ValueError(
                f"duplicate xvar_class_rank {rank} in prospect board for class {draft_class}"
            )
        board[rank] = float(xvar)
    return board


def _value_pick_from_prospect_board(
    year: int,
    round_: int,
    *,
    slot: Optional[int],
    board: dict[int, float],
    sf_qb_knob_active: bool = False,
) -> PickValue:
    """Regime A — price a pick from the class's actual scored prospect board.

    Option-A parity with the curve: each prospect is floored at ``max(0, xvar)``.
    Exact slot N -> floored rank-N xVAR; round-only -> mean of floored over the round's
    rank range. Slots/ranks beyond the board are unresolved (never a curve fallback).
    """
    caveats = list(_BOARD_PICK_CAVEATS)
    if sf_qb_knob_active:
        caveats.append("sf_qb_ordering_assumption")

    if slot is not None:
        raw = board.get(int(slot))
        if raw is None:
            return PickValue(
                year=year, round_=round_, slot=slot, xvar=None,
                resolution="unresolved", valuation_regime="prospect_board",
                caveats=caveats + ["pick_value_board_slot_beyond_coverage"],
            )
        return PickValue(
            year=year, round_=round_, slot=slot, xvar=round(max(0.0, raw), 4),
            resolution="board_exact_slot", valuation_regime="prospect_board",
            caveats=caveats,
        )

    ranks = _ROUND_RANK_RANGES.get(int(round_))
    present = [board[r] for r in ranks if r in board] if ranks else []
    if not present:
        return PickValue(
            year=year, round_=round_, xvar=None, resolution="unresolved",
            valuation_regime="prospect_board",
            caveats=caveats + ["pick_value_board_slot_beyond_coverage"],
        )
    priced = [max(0.0, v) for v in present]
    if ranks is not None and len(present) < len(list(ranks)):
        caveats = caveats + ["pick_value_board_partial_round_coverage"]
    return PickValue(
        year=year, round_=round_, xvar=round(statistics.fmean(priced), 4),
        resolution="board_round", valuation_regime="prospect_board",
        caveats=caveats,
    )


def value_pick(
    year: int,
    round_: int,
    *,
    slot: Optional[int] = None,
    tier: Optional[str] = None,
    curve: dict,
    prospect_board: Optional[dict[int, float]] = None,
    sf_qb_knob_active: bool = False,
) -> PickValue:
    """Price a dynasty rookie pick in xVAR.

    Dispatches to the prospect-board path (Regime A) when a **non-empty** board is
    supplied for a slot/round-only pick; otherwise the historical-curve path (Regime B).
    A ``tier`` request always routes to the curve (board-tier mapping is undefined in
    v1). ``curve`` is required so the fallback is always deterministic.
    """
    if prospect_board and tier is None:
        return _value_pick_from_prospect_board(
            year, round_, slot=slot, board=prospect_board,
            sf_qb_knob_active=sf_qb_knob_active,
        )
    return _value_pick_from_curve(
        year, round_, slot=slot, tier=tier, curve=curve,
        sf_qb_knob_active=sf_qb_knob_active,
    )


def load_curve(path: str | Path) -> dict:
    """Read a versioned draft-pick value curve artifact from disk."""
    return json.loads(Path(path).read_text())
