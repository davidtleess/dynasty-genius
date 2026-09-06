#!/usr/bin/env python3.14
"""DG-168 — the dominance screen: where the market contradicts ITSELF.

Dynasty Nerds' two rules. Same production, longer career left -> mispriced. Same career
left, higher production -> mispriced. This looks for pairs the market prices ALIKE where
one player is ahead on BOTH of the things we measured.

WHY THIS AND NOT A RANKED BOARD. Every obstacle that has blocked publishing a board is a
question of MAGNITUDE — 80 rookies we cannot price at all, a replacement baseline four
separate discussions failed to settle, an order asserted between players separated by
0.02%. A dominance test asks only DIRECTION on two axes, so all of them stop mattering at
once rather than needing to be fixed one at a time.

AND IT IS THE ONLY SHAPE OF EDGE RULING 8 PERMITS. Market price is never a model input;
here it selects which pairs to look at and is never read by the value. A divergence from
the market is a hypothesis. The market contradicting itself on facts we measured is a
finding.

⛔ GATES. Both players priced — dominance is never inferred against a blank. A real
margin required on BOTH axes. Market values translated into his league first (DG-169):
untranslated, a quarterback or tight end reads ~2x overpriced and the screen would
manufacture its loudest findings on exactly the positions where the correction is largest.
"""
from __future__ import annotations
import json
from pathlib import Path

# DG-169, Bob, measured: his league / the market's format. RB is the only position the
# market prices correctly for him.
LEAGUE_TRANSLATION = {"TE": 1.96, "QB": 1.95, "WR": 1.45, "RB": 0.98}

# A pair must be priced this close to count as "the market says these are the same",
# and must differ by at least this much on each axis to count as dominance rather than
# noise. Both are stated here rather than buried, and both are choices.
SAME_PRICE_BAND = 0.10      # within 10% of each other after translation
MIN_PRODUCTION_EDGE = 0.15  # 15% more production per season
MIN_CAREER_EDGE = 0.15      # 15% more remaining startable value


def market_price(row: dict) -> float | None:
    """What the market ACTUALLY charges, in its own currency, untranslated.

    ⛔ Pair on THIS, not on a translated value. "The market prices these two the same"
    is a claim about the market, and translating first makes it a claim about our
    correction. Measured: the market charges 3403 for Kyren Williams and 1580 for Mark
    Andrews — 2.15x apart — and applying the tight-end factor moved them to within 8%,
    at which point the screen reported them as identically priced. That sentence would
    have been false, and it was the loudest finding on the board.
    """
    overlay = row.get("market_overlay") or {}
    value = overlay.get("market_value")
    if value is None:
        return None
    return float(value)


def format_explains(a: dict, b: dict) -> bool:
    """Does the format difference already account for the gap?

    The market prices for 0.5 PPR starting three receivers; his league is full PPR
    starting two, and DG-169 measured what that is worth by position. A player the
    market underprices FOR HIS FORMAT is not a market error — it is a format mismatch,
    and translating is how we tell them apart. A contradiction only counts if it
    SURVIVES the translation.
    """
    ta = a["market"] * LEAGUE_TRANSLATION.get(a["pos"], 1.0)
    tb = b["market"] * LEAGUE_TRANSLATION.get(b["pos"], 1.0)
    # if translation reverses or erases the price ordering, the format explains it
    return (a["market"] - b["market"]) * (ta - tb) <= 0 or abs(ta - tb) / max(ta, tb) < 0.02


def dominates(a: dict, b: dict) -> bool:
    """a beats b on BOTH axes by a real margin. Never true against a missing value."""
    if any(x is None for x in (a["production"], b["production"], a["career"], b["career"])):
        return False
    if b["production"] <= 0 or b["career"] <= 0:
        return False
    return (a["production"] >= b["production"] * (1 + MIN_PRODUCTION_EDGE)
            and a["career"] >= b["career"] * (1 + MIN_CAREER_EDGE))


def same_price(a: dict, b: dict) -> bool:
    lo, hi = sorted((a["market"], b["market"]))
    return lo > 0 and (hi - lo) / lo <= SAME_PRICE_BAND


def find_contradictions(players: list[dict]) -> list[dict]:
    """Pairs the market prices alike where one is ahead on both measured axes."""
    priced = [p for p in players
              if p["market"] is not None and p["production"] is not None and p["career"] is not None]
    out = []
    for i, a in enumerate(priced):
        for b in priced[i + 1:]:
            if not same_price(a, b):
                continue
            better, worse = (a, b) if dominates(a, b) else (b, a) if dominates(b, a) else (None, None)
            if better is None:
                continue
            if format_explains(better, worse):
                continue   # a format mismatch, not a market error
            out.append({"better": better, "worse": worse})
    return out


def sentence(pair: dict) -> str:
    """The output is a sentence, not a row. He reads sentences."""
    a, b = pair["better"], pair["worse"]
    return (f"The market prices {a['name']} and {b['name']} the same. "
            f"{a['name'].split()[-1]} produces more AND has more startable seasons left.")
