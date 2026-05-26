#!/usr/bin/env python3.14
"""Phase 24 — build the dynasty rookie draft-pick value curve artifact.

Reads `app/data/training/prospects_with_outcomes.csv` (mature classes 2015-2022),
builds the per-slot xVAR curve via the "first-36-skill-players-in-NFL-draft-order =
FF rookie board" bridge, applies the monotonic clamp + tier rollups, and writes a
versioned artifact. Values are NFL-derived historical expectations, not market prices.

Usage: .venv/bin/python3.14 scripts/build_draft_pick_value_curve.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402  (import after sys.path setup — scripts convention)

from src.dynasty_genius.trade_lab.draft_pick_valuation import (  # noqa: E402
    build_slot_curve,
    smooth_and_tier,
)

_CSV = _ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
_OUT = _ROOT / "app" / "data" / "valuation" / "draft_pick_value_curve_v1.json"

# Mature classes only: y24_ppg is realized Year-2+3 PPG, so recent classes are
# incomplete. 2015-2022 inclusive (Codex data-maturity gate).
_MATURE_YEARS = tuple(range(2015, 2023))
_BOARD_SIZE = 36
_SF_QB_PROMOTE_SLOTS = 0  # SF-QB knob off in v1 (manual calibration deferred)

_TIER_MAP = {
    "early_1st": [1, 2, 3, 4],
    "mid_1st": [5, 6, 7, 8],
    "late_1st": [9, 10, 11, 12],
    "early_2nd": [13, 14, 15, 16],
    "mid_2nd": [17, 18, 19, 20],
    "late_2nd": [21, 22, 23, 24],
    "early_3rd": [25, 26, 27, 28],
    "mid_3rd": [29, 30, 31, 32],
    "late_3rd": [33, 34, 35, 36],
    # Round-generic tiers for reconstructed future picks that know only the round.
    "round_1_generic": list(range(1, 13)),
    "round_2_generic": list(range(13, 25)),
    "round_3_generic": list(range(25, 37)),
}


def main() -> None:
    df = pd.read_csv(_CSV)
    df = df.rename(columns={"season": "draft_year"})
    df["y24_ppg"] = pd.to_numeric(df["y24_ppg"], errors="coerce").fillna(0.0)
    df["low_sample_flag"] = (
        pd.to_numeric(df.get("low_sample_flag", 0), errors="coerce").fillna(0).astype(int)
    )

    curve = build_slot_curve(
        df,
        mature_years=_MATURE_YEARS,
        board_size=_BOARD_SIZE,
        sf_qb_promote_slots=_SF_QB_PROMOTE_SLOTS,
    )
    curve["tier_map"] = _TIER_MAP
    curve = smooth_and_tier(curve)
    curve["source"] = {
        "csv": "app/data/training/prospects_with_outcomes.csv",
        "mature_years": list(_MATURE_YEARS),
        "board_size": _BOARD_SIZE,
        "sf_qb_promote_slots": _SF_QB_PROMOTE_SLOTS,
        "method": (
            "first-36-skill-NFL-order bridge; realized y24_ppg -> DVS -> xVAR; "
            "monotonic clamp; median tiers"
        ),
        "caveat": "NFL-derived historical expectation, not a market-measured price",
    }

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(curve, indent=2))

    total_low = sum(s["low_sample_count"] for s in curve["slots"].values())
    print(f"Wrote {_OUT.relative_to(_ROOT)}")
    print(f"  mature_years_used: {curve['mature_years_used']}")
    print(f"  slots populated:   {len(curve['slots'])}/{_BOARD_SIZE}")
    print(f"  total low_sample across slots: {total_low}")
    print(f"  tiers: {json.dumps(curve['tiers'])}")


if __name__ == "__main__":
    main()
