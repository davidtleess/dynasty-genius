"""Phase 16.2 CFBD receiving adapter — team pass attempts for RYPTPA.

Fetches team-level passing stats (pass attempts) for a given college team
and season year. Used as the RYPTPA denominator.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.collegefootballdata.com"

# Abbreviation → full CFBD name for common PFF export discrepancies
_COLLEGE_NAME_MAP: dict[str, str] = {
    "Florida St.": "Florida State",
    "Ohio St.": "Ohio State",
    "Michigan St.": "Michigan State",
    "Penn St.": "Penn State",
    "Mississippi St.": "Mississippi State",
    "Iowa St.": "Iowa State",
    "Kansas St.": "Kansas State",
    "Oklahoma St.": "Oklahoma State",
    "Washington St.": "Washington State",
    "Colorado St.": "Colorado State",
    "Oregon St.": "Oregon State",
    "Arizona St.": "Arizona State",
    "S JOSE ST": "San Jose State",
    "FAU": "Florida Atlantic",
    "FIU": "Florida International",
    "SMU": "SMU",
    "LSU": "LSU",
    "TCU": "TCU",
    "UCF": "UCF",
    "BYU": "BYU",
    "USF": "South Florida",
    "UTSA": "UTSA",
    "UTEP": "UTEP",
    "UAB": "UAB",
    "UMass": "Massachusetts",
    "UConn": "Connecticut",
    "UNT": "North Texas",
    "UNLV": "UNLV",
    "Hawaii": "Hawaii",
}


def normalize_college_name(name: str) -> str:
    """Map PFF college abbreviations to CFBD full names."""
    stripped = name.strip()
    return _COLLEGE_NAME_MAP.get(stripped, stripped)


def _auth_key(api_key: str | None) -> str:
    return (api_key or os.getenv("CFBD_API_KEY") or "").strip()


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


def fetch_team_pass_attempts(
    college_team: str,
    season: int,
    api_key: str | None = None,
) -> float | None:
    """Return pass attempts for a college team in a given season, or None.

    Args:
        college_team: PFF team_name string (will be normalized to CFBD name).
        season: College season year (e.g. 2022).
        api_key: CFBD API key. Falls back to CFBD_API_KEY env var.

    Returns:
        Float pass attempts or None if unavailable.
    """
    key = _auth_key(api_key)
    if not key:
        return None

    cfbd_name = normalize_college_name(college_team)
    url = f"{BASE_URL}/stats/team/season"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            params={"year": season, "team": cfbd_name},
        )
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            return None
        return _team_stat(records, "passAttempts")
    except Exception:
        return None
