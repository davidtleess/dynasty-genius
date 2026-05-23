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

# Abbreviation → canonical CFBD name. Covers both:
#   (a) training CSV spellings (PFR names) → canonical
#   (b) PFF export ALL-CAPS team names → canonical
# Both sides of each (training_college, pff_college) pair must resolve to the
# same string for find_pff_match() to succeed.  Task 4.5: 81 aliases
# derived from the name_match_college_mismatch review rows.
_COLLEGE_NAME_MAP: dict[str, str] = {
    # ── Original entries ────────────────────────────────────────────────────
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
    # ── Task 4.5: PFF ALL-CAPS abbreviations → canonical ────────────────────
    # High-frequency pairs (training → PFF mismatch count)
    "N CAROLINA": "North Carolina",        # 9 rows
    "OLE MISS": "Mississippi",             # 7 rows
    "ARIZONA ST": "Arizona State",         # 6 rows  (training already mapped via "Arizona St.")
    "S CAROLINA": "South Carolina",        # 6 rows
    "OKLA STATE": "Oklahoma State",        # 5 rows  (training already mapped via "Oklahoma St.")
    "MIAMI FL": "Miami",                   # 5 rows
    "Miami (FL)": "Miami",                 # training form
    "FLORIDA ST": "Florida State",         # 5 rows  (training already mapped via "Florida St.")
    # Medium-frequency pairs
    "Central Florida": "UCF",             # 4 rows  (PFF uses "UCF")
    "BOISE ST": "Boise State",            # 4 rows
    "Boise St.": "Boise State",           # training form
    "OREGON ST": "Oregon State",          # 3 rows  (training already mapped via "Oregon St.")
    "MICH STATE": "Michigan State",       # 3 rows  (training already mapped via "Michigan St.")
    "COLO STATE": "Colorado State",       # 2 rows  (training already mapped via "Colorado St.")
    "SO MISS": "Southern Miss",           # 2 rows
    "NWESTERN": "Northwestern",           # 2 rows
    "BOSTON COL": "Boston College",       # 2 rows
    "Boston Col.": "Boston College",      # training form
    "LA LAFAYET": "Louisiana",            # 2 rows
    "W MICHIGAN": "Western Michigan",     # 2 rows
    "S ALABAMA": "South Alabama",         # 2 rows
    "Ala-Birmingham": "UAB",              # 2 rows  (PFF uses "UAB", already in map)
    # Low-frequency pairs (1 row each)
    "S DIEGO ST": "San Diego State",
    "San Diego St.": "San Diego State",
    "NEW MEX ST": "New Mexico State",
    "New Mexico St.": "New Mexico State",
    "LA TECH": "Louisiana Tech",
    "MIDDLE TN": "Middle Tennessee",
    "Middle Tenn. St.": "Middle Tennessee",
    "UMASS": "Massachusetts",             # training form is "Massachusetts" (passthrough)
    "W VIRGINIA": "West Virginia",
    "FRESNO ST": "Fresno State",
    "Fresno St.": "Fresno State",
    "DOMINION": "Old Dominion",
    "LA MONROE": "Louisiana Monroe",
    "La-Monroe": "Louisiana Monroe",
    "NC STATE": "NC State",
    "North Carolina St.": "NC State",
    "BOWL GREEN": "Bowling Green",
    "UTAH ST": "Utah State",
    "Utah St.": "Utah State",
    # Illinois → VANDERBILT omitted: identity risk (Ke'Shawn Vaughn transfer;
    # training CSV has wrong college — stays in manual review)
    "APP STATE": "Appalachian State",
    "Appalachian St.": "Appalachian State",
    "WASH STATE": "Washington State",     # training already mapped via "Washington St."
    "N TEXAS": "North Texas",
    "GA TECH": "Georgia Tech",
    "VA TECH": "Virginia Tech",
    "MISS STATE": "Mississippi State",    # training already mapped via "Mississippi St."
    "WAKE": "Wake Forest",
    "KANSAS ST": "Kansas State",          # training already mapped via "Kansas St."
    "C MICHIGAN": "Central Michigan",
    "W KENTUCKY": "Western Kentucky",
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
    url = f"{BASE_URL}/stats/season"
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
