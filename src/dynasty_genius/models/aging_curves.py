"""Piecewise-linear aging curve reader for Engine B.

Loads resources/fitted_aging_curves_v1.json and provides a single function
aging_curve_value(position, age) that returns a relative value in [0.0, 1.0].

The curve form (from the JSON spec):
  - Ascent:  age <= peak_age → linear from base_value at entry_age to 1.0 at peak_age
  - Plateau: peak_age < age <= onset_of_decline_age → 1.0
  - Decline: age > onset_of_decline_age → 1.0 - decline_slope * (age - onset), floored at 0.0
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

AGING_CURVES_PATH = Path(__file__).resolve().parents[3] / "resources" / "fitted_aging_curves_v1.json"


@lru_cache(maxsize=1)
def load_aging_curves() -> dict:
    with AGING_CURVES_PATH.open() as f:
        return json.load(f)


def aging_curve_value(position: str, age: int | float) -> float:
    """Return relative PPG value in [0.0, 1.0] for a position at a given age.

    Raises KeyError if position is not in the curves JSON.
    """
    data = load_aging_curves()
    spec = data["positions"][position]  # KeyError if unknown position

    entry_age: float = spec["entry_age"]
    peak_age: float = spec["peak_age"]
    onset: float = spec["onset_of_decline_age"]
    base: float = spec["base_value"]
    ascent_slope: float = spec["ascent_slope_per_year"]
    decline_slope: float = spec["decline_slope_per_year"]

    age = float(age)

    if age <= peak_age:
        value = base + ascent_slope * (age - entry_age)
    elif age <= onset:
        value = 1.0
    else:
        value = 1.0 - decline_slope * (age - onset)

    return round(max(0.0, min(1.0, value)), 4)
