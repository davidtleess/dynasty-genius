"""FantasyCalc adapter.

Fetches market values from the FantasyCalc API.
Market values are physically separated from training artifacts.
"""
from __future__ import annotations

from typing import Any

import httpx

API_URL = "https://api.fantasycalc.com/values/current?isDynasty=true"

def fetch_fantasycalc_market_values() -> list[dict[str, Any]]:
    """Fetch current dynasty values from FantasyCalc."""
    try:
        response = httpx.get(API_URL, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # Expected shape is a list of players
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "players" in data:
            return data["players"]
        return []
    except Exception:
        return []

def normalize_fantasycalc_entry(raw_entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single raw entry into a decision-surface-ready card."""
    return {
        "full_name": raw_entry.get("name"),
        "fantasycalc_value": raw_entry.get("value"),
        "source_fantasycalc_value": "fantasycalc",
        "market_overlay": True
    }
