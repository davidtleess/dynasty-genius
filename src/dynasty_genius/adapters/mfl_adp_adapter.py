"""MyFantasyLeague rookie ADP market overlay adapter.

Fetches real completed-draft dynasty rookie ADP from MFL's public export API and
joins it to MFL's player map (TYPE=players) for name/position. Mirrors
fantasycalc_adapter. Two independent cached fetches, each 3-stage degraded:
  1. Fresh cache (now - fetched_at < TTL) -> serve
  2. Expired/absent cache + fetch fails -> serve stale with caveat (if cache exists)
  3. No cache + fetch fails -> empty + unavailable caveat

Market values are post-scoring overlays only — never Engine A/B features.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

_BASE = "https://api.myfantasyleague.com"
# Params live-locked 2026-05-27 (ROOKIES=1; IS_KEEPER=Rookie Only is INVALID).
ADP_API_URL_TEMPLATE = (
    _BASE + "/{year}/export?TYPE=adp&PERIOD=RECENT&FCOUNT=12&IS_PPR=1"
    "&ROOKIES=1&IS_MOCK=No&JSON=1"
)
PLAYERS_API_URL_TEMPLATE = _BASE + "/{year}/export?TYPE=players&JSON=1"

CACHE_DIR = Path("app/cache/mfl_adp")
ADP_TTL_HOURS = 24
PLAYERS_TTL_HOURS = 168  # player map is near-static

_USER_AGENT = "dynasty-genius/0.1 (personal dynasty tool; contact david.t.leess@gmail.com)"
_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

_ADP_ALLOWED = ("id", "rank", "averagePick", "minPick", "maxPick", "draftSelPct", "draftsSelectedIn")
_PLAYERS_ALLOWED = ("id", "name", "position", "team")

INTRINSIC_CAVEATS = ["mfl_adp_format_blended_qb_count", "mfl_adp_te_premium_unfiltered"]


def _current_season() -> int:
    return datetime.now(timezone.utc).year


def _as_list(node) -> list[dict]:
    """MFL returns a bare object for single-row responses; normalize to a list."""
    if node is None:
        return []
    return node if isinstance(node, list) else [node]


def _adp_cache_file(season: int) -> Path:
    return CACHE_DIR / f"adp_{season}.json"


def _players_cache_file(season: int) -> Path:
    return CACHE_DIR / f"players_{season}.json"


def _sanitize_adp(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in _ADP_ALLOWED if k in r} for r in rows]


def _sanitize_players(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in _PLAYERS_ALLOWED if k in r} for r in rows]


def _cache_age_hours(fetched_at: str) -> float | None:
    """Local cache age from fetched_at — governs whether to attempt a refresh."""
    try:
        fetched = datetime.strptime(fetched_at, _TS_FMT).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _source_publish_age_hours(source_timestamp) -> float | None:
    """Publish age from MFL adp.timestamp (epoch seconds) — the market freshness signal."""
    if source_timestamp is None:
        return None
    try:
        published = datetime.fromtimestamp(int(source_timestamp), tz=timezone.utc)
        return (datetime.now(timezone.utc) - published).total_seconds() / 3600
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _freshness_caveats(source_timestamp) -> list[str]:
    """Disclose source publish age; flag when the source timestamp is unusable."""
    age = _source_publish_age_hours(source_timestamp)
    if age is None:
        return ["mfl_adp_timestamp_unavailable"]
    return [f"source_publish_age_h={int(age)}"]


def _load_cache(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def _save_cache(path: Path, data, ttl_hours: int, source_timestamp) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).strftime(_TS_FMT),
            "source_timestamp": source_timestamp,
            "ttl_hours": ttl_hours,
            "data": data,
        }))
    except Exception:
        pass


def _get_json(url: str) -> dict:
    resp = httpx.get(url, headers={"User-Agent": _USER_AGENT}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_adp_with_cache(season: int | None = None) -> tuple[list[dict], list[str]]:
    """(sanitized ADP rows, transient caveats). 3-stage degrade. Never raises."""
    season = season or _current_season()
    path = _adp_cache_file(season)
    cached = _load_cache(path)

    # Stage 1: fresh cache (fetched_at clock)
    if cached:
        age = _cache_age_hours(cached.get("fetched_at", ""))
        if age is not None and age < cached.get("ttl_hours", ADP_TTL_HOURS):
            return cached["data"], _freshness_caveats(cached.get("source_timestamp"))

    # Attempt live refresh
    try:
        payload = _get_json(ADP_API_URL_TEMPLATE.format(year=season)).get("adp", {})
        rows = _sanitize_adp(_as_list(payload.get("player")))
        source_ts = payload.get("timestamp")
        _save_cache(path, rows, ADP_TTL_HOURS, source_ts)
        return rows, _freshness_caveats(source_ts)
    except Exception:
        pass

    # Stage 2: stale serve (cache present but refresh failed)
    if cached:
        caveats = ["stale_market_data"]
        cache_age = _cache_age_hours(cached.get("fetched_at", ""))
        if cache_age is not None:
            caveats.append(f"cache_age_h={int(cache_age)}")
        caveats += _freshness_caveats(cached.get("source_timestamp"))
        return cached["data"], caveats

    # Stage 3: cold fail
    return [], ["market_data_unavailable"]


def _rows_to_player_map(rows: list[dict]) -> dict[str, dict]:
    return {r["id"]: {"name": r.get("name"), "position": r.get("position"), "team": r.get("team")}
            for r in rows if r.get("id") is not None}


def fetch_players_with_cache(season: int | None = None) -> tuple[dict[str, dict], list[str]]:
    """({mfl_id: {name,position,team}}, transient caveats). Independent 3-stage degrade. Never raises."""
    season = season or _current_season()
    path = _players_cache_file(season)
    cached = _load_cache(path)

    if cached:
        age = _cache_age_hours(cached.get("fetched_at", ""))
        if age is not None and age < cached.get("ttl_hours", PLAYERS_TTL_HOURS):
            return _rows_to_player_map(cached["data"]), []

    try:
        payload = _get_json(PLAYERS_API_URL_TEMPLATE.format(year=season)).get("players", {})
        rows = _sanitize_players(_as_list(payload.get("player")))
        _save_cache(path, rows, PLAYERS_TTL_HOURS, payload.get("timestamp"))
        return _rows_to_player_map(rows), []
    except Exception:
        pass

    if cached:
        return _rows_to_player_map(cached["data"]), ["stale_players_map"]

    return {}, ["mfl_players_map_unavailable"]
