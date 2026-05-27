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

from datetime import datetime, timezone
from pathlib import Path

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
