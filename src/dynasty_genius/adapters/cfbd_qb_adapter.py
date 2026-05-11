"""CFBD QB adapter.

Uses httpx directly against the College Football Data API for QB college stats.
The adapter is intentionally defensive: missing or partial data returns None
values rather than raising or fabricating signals.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.collegefootballdata.com"

QB_CFBD_FEATURES: list[str] = [
    "completion_pct",
    "yards_per_attempt",
    "td_int_ratio",
    "sack_rate",
    "all_purpose_yards",
    "passing_yards_share",
    "ppa",
    "wepa",
    "rushing_yards",
    "rushing_tds",
]


def _empty_result() -> dict[str, Any]:
    return {feature: None for feature in QB_CFBD_FEATURES}


def _auth_key(api_key: str | None) -> str:
    key = (api_key or os.getenv("CFBD_API_KEY") or "").strip()
    return key


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _request_json(endpoint: str, params: dict[str, Any], api_key: str) -> list[dict[str, Any]]:
    url = f"{BASE_URL}{endpoint}"
    try:
        response = httpx.get(url, headers=_headers(api_key), params=params)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _first_non_empty(values: list[Any]) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _first_stat(records: list[dict[str, Any]], field: str, stat_key: str) -> float | None:
    for row in records:
        if str(row.get(field, "")).strip().upper() == stat_key:
            value = row.get("stat")
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _team_stat(records: list[dict[str, Any]], stat_name: str) -> float | None:
    for row in records:
        if str(row.get("statName", "")).strip() == stat_name:
            value = row.get("statValue")
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _nested_ppa_value(records: list[dict[str, Any]]) -> float | None:
    if not records:
        return None
    average_ppa = records[0].get("averagePPA")
    if not isinstance(average_ppa, dict):
        return None
    value = average_ppa.get("all")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_wepa_value(records: list[dict[str, Any]]) -> float | None:
    if not records:
        return None
    value = records[0].get("wepa")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(sum(present))


def fetch_qb_college_stats(player_name: str, year: int, api_key: str) -> dict[str, Any]:
    """Fetch QB college stats from CFBD and normalize them into the contract shape."""
    key = _auth_key(api_key)
    if not key:
        return _empty_result()

    passing_records = _request_json(
        "/stats/player/season",
        {"year": year, "playerName": player_name, "category": "passing"},
        key,
    )
    rushing_records = _request_json(
        "/stats/player/season",
        {"year": year, "playerName": player_name, "category": "rushing"},
        key,
    )
    ppa_records = _request_json(
        "/ppa/players/season",
        {"year": year, "playerName": player_name},
        key,
    )
    wepa_records = _request_json(
        "/wepa/players/passing",
        {"year": year, "playerName": player_name},
        key,
    )

    team_name = _first_non_empty(
        [
            _first_non_empty([row.get("team") for row in passing_records]),
            _first_non_empty([row.get("team") for row in rushing_records]),
        ]
    )
    team_records = _request_json(
        "/stats/team/season",
        {"year": year, "team": team_name} if team_name else {"year": year},
        key,
    ) if team_name else []

    passing_yards = _first_stat(passing_records, "statType", "YDS")
    rushing_yards = _first_stat(rushing_records, "statType", "YDS")
    rushing_tds = _first_stat(rushing_records, "statType", "TD")
    completion_pct_raw = _first_stat(passing_records, "statType", "PCT")
    yards_per_attempt = _first_stat(passing_records, "statType", "YPA")
    passing_tds = _first_stat(passing_records, "statType", "TD")
    interceptions = _first_stat(passing_records, "statType", "INT")
    pass_attempts = _team_stat(team_records, "passAttempts")
    sacks_allowed = _team_stat(team_records, "sacksAllowed")
    net_passing_yards = _team_stat(team_records, "netPassingYards")

    completion_pct = completion_pct_raw / 100.0 if completion_pct_raw is not None else None
    td_int_ratio = None
    if passing_tds is not None and interceptions is not None:
        td_int_ratio = passing_tds / max(interceptions, 1.0)

    sack_rate = None
    if pass_attempts is not None and sacks_allowed is not None:
        denom = pass_attempts + sacks_allowed
        if denom > 0:
            sack_rate = sacks_allowed / denom

    passing_yards_share = None
    if passing_yards is not None and net_passing_yards not in (None, 0):
        passing_yards_share = passing_yards / net_passing_yards

    return {
        "completion_pct": completion_pct,
        "yards_per_attempt": yards_per_attempt,
        "td_int_ratio": td_int_ratio,
        "sack_rate": sack_rate,
        "all_purpose_yards": _sum_present(passing_yards, rushing_yards),
        "passing_yards_share": passing_yards_share,
        "ppa": _nested_ppa_value(ppa_records),
        "wepa": _first_wepa_value(wepa_records),
        "rushing_yards": rushing_yards,
        "rushing_tds": rushing_tds,
    }
