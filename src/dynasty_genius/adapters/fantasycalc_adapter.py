"""FantasyCalc market overlay adapter.

Fetches dynasty SF PPR values from the FantasyCalc free API.
Caches to disk with a seasonal TTL. Three-stage degraded behaviour:
  1. Fresh cache → serve directly
  2. Expired cache + API failure → serve stale with caveat
  3. No cache + API failure → return empty list with market_data_unavailable caveat

Market values are post-scoring overlays only — never Engine A/B features.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

API_URL = (
    "https://api.fantasycalc.com/values/current"
    "?isDynasty=true&numQbs=2&numTeams=12&ppr=1"
)

CACHE_DIR = Path("app/cache/fantasycalc")
CACHE_FILE = CACHE_DIR / "market_values.json"

_BANNED_CACHE_FIELDS = frozenset({
    "combinedValue", "redraftValue", "redraftDynastyValueDifference"
})


def _sanitize_entries_for_cache(entries: list[dict]) -> list[dict]:
    """Strip banned fields from raw FC entries before disk write."""
    return [{k: v for k, v in entry.items() if k not in _BANNED_CACHE_FIELDS} for entry in entries]


def _current_ttl_hours() -> int:
    """Seasonal TTL: 6h in-season (Aug 16–Jan 15), 24h offseason."""
    today = date.today()
    m, d = today.month, today.day
    in_season = (
        (m == 8 and d >= 16)
        or m in (9, 10, 11, 12)
        or (m == 1 and d <= 15)
    )
    return 6 if in_season else 24


def _load_cache() -> dict | None:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
    except Exception:
        pass
    return None


def _save_cache(data: list[dict], ttl_hours: int) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ttl_hours": ttl_hours,
            "data": data,
        }))
    except Exception:
        pass


def fetch_with_cache() -> tuple[list[dict], list[str]]:
    """Returns (raw_fc_entries, caveats). Never raises."""
    ttl_hours = _current_ttl_hours()
    cached = _load_cache()

    if cached:
        try:
            fetched_at = datetime.strptime(cached["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
            if age_hours < ttl_hours:
                # Stage 1: fresh
                return cached["data"], ["source_timestamp_is_fetch_time_not_publish_time"]
        except Exception:
            pass

    # Cache miss or expired — attempt live fetch
    try:
        response = httpx.get(API_URL, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "players" in data:
            data = data["players"]
        if not isinstance(data, list):
            data = []
        _save_cache(_sanitize_entries_for_cache(data), ttl_hours)
        return data, ["source_timestamp_is_fetch_time_not_publish_time"]
    except Exception:
        pass

    if cached:
        # Stage 2: stale serve
        fetched_at_str = cached.get("fetched_at", "unknown")
        try:
            fetched_at = datetime.strptime(fetched_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            stale_h = int((datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600)
        except Exception:
            stale_h = -1
        return cached["data"], [
            "stale_market_data",
            f"fetched_at={fetched_at_str}",
            f"stale_for={stale_h}h",
            "source_timestamp_is_fetch_time_not_publish_time",
        ]

    # Stage 3: cold fail
    return [], ["market_data_unavailable"]


def fetch_fantasycalc_market_values() -> list[dict[str, Any]]:
    """Legacy entry point. Returns raw FC data (no caveats)."""
    data, _ = fetch_with_cache()
    return data


def normalize_fantasycalc_entry(raw_entry: dict[str, Any]) -> dict[str, Any]:
    """Normalise a single FC response entry into a flat dict for overlay construction."""
    player = raw_entry.get("player", {})
    return {
        "sleeper_id": player.get("sleeperId"),
        "mfl_id": player.get("mflId"),
        "full_name": player.get("name"),
        "position": player.get("position"),
        "age": player.get("maybeAge"),
        "nfl_team": player.get("maybeTeam"),
        "market_value": raw_entry.get("value"),
        "trend_delta": raw_entry.get("trend30Day"),
        "overall_rank": raw_entry.get("overallRank"),
        "position_rank": raw_entry.get("positionRank"),
        "market_volatility": raw_entry.get("maybeMovingStandardDeviation"),
        "fc_tier": raw_entry.get("maybeTier"),
        # Explicitly excluded: combinedValue, redraftValue, redraftDynastyValueDifference
    }
