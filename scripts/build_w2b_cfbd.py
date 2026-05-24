"""Phase 19 W2b — CFBD Player-Level Enrichment Pipeline.

Extends prospects_with_outcomes_v3.csv with position-specific Required
features that need season-by-season college stats from the CFBD API:

  WR: wr_dominator_final, wr_breakout_age, wr_market_share_yds,
      wr_yards_per_reception_career, ryptpa
  RB: rb_final_dominator, rb_school_sp_plus, rb_scrimmage_ypg, rb_rec_ypg
  TE: te_ryptpa_final, te_yards_per_reception_career

Era proxy features (derived from existing v3 columns — no API calls):
  final_college_age   = age_at_draft - 1  (proxy; see spec §3D)
  early_declare       = 1 if age_at_draft <= 21.0
  wr_early_declare    = same proxy, WR rows only
  covid_eligibility_flag = 1 if draft_year ∈ {2021, 2022} AND age_at_draft >= 23.0

Permanently stubbed (_missing=1 — not obtainable from CFBD player stats):
  wr_rec_tds_per_game_final — CFBD /stats/player/season never returns G (games)
  yprr_college              — requires PFF premium routes-run data absent from CFBD
  te_deep_yard_share        — requires PFF route data
  transfer_portal_flag      — CFBD portal only covers 2019+; cohort starts 2015

Games-proxy features (populated from CFBD /games endpoint team-game counts):
  rb_scrimmage_ypg, rb_rec_ypg — computed as yds / team_games when available

Data strategy:
  - Player stats fetched year-by-year (one call per year/category), not per-player.
  - Raw API responses cached as JSON under app/data/cfbd_cache/ (gitignored).
  - Team pass attempts (TE RYPTPA denominator) cached individually per (school, year).
  - Identity matching: normalize_player_name() + normalize_college_name() from
    the existing cfbd_receiving_adapter module.

API volume (approximate):
  14 years × 2 categories (receiving, rushing) + 14 SP+ calls ≈ 42 batch calls.
  Plus up to ~160 team-pass-attempts calls for TE RYPTPA — cached individually.

Does NOT change production model pkl files, latest.json, PVO scoring, or
market overlays. All generated artifacts remain gitignored.

Usage:
    .venv/bin/python3.14 scripts/build_w2b_cfbd.py
    .venv/bin/python3.14 scripts/build_w2b_cfbd.py --force-fetch  # bypass cache
    .venv/bin/python3.14 scripts/build_w2b_cfbd.py --allow-degraded  # tolerate API errors
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.cfbd_qb_adapter import (  # noqa: E402
    fetch_qb_college_stats,
)
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (  # noqa: E402
    fetch_team_pass_attempts,
    normalize_college_name,
)
from src.dynasty_genius.models.head_b_contract import (  # noqa: E402
    HEAD_B_PROHIBITED_COLUMNS,
    MARKET_PROHIBITED_COLUMNS,
    PFF_GRADE_PROHIBITED_COLUMNS,
)

# ── I/O paths ─────────────────────────────────────────────────────────────────

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
CACHE_DIR = ROOT / "app/data/cfbd_cache"

# ── Constants ─────────────────────────────────────────────────────────────────

CFBD_BASE = "https://api.collegefootballdata.com"

# College years to fetch: covers 2015–2025 draft classes (4-5 year careers)
COLLEGE_YEARS = list(range(2011, 2025))

# Dominator breakout threshold per Barnwell/TDN convention
DOMINATOR_BREAKOUT_THRESHOLD = 0.20

# Era proxy thresholds (simplified proxies; see spec §3D for rationale)
EARLY_DECLARE_AGE_THRESHOLD = 21.0      # age_at_draft <= this → early_declare=1
COVID_DRAFT_YEARS = frozenset({2021, 2022})  # cohorts that could have COVID eligibility
COVID_MIN_AGE = 23.0                    # age_at_draft >= this in COVID year → flag=1


# ── Name normalization ────────────────────────────────────────────────────────

def normalize_player_name(name: str) -> str:
    """Lowercase and strip all non-alpha characters for deterministic matching."""
    return re.sub(r"[^a-z]", "", name.lower())


def _norm_school_key(school: str) -> str:
    """Apply CFBD name map then lowercase for dict key."""
    return normalize_college_name(school).lower()


# ── API load / cache helpers ──────────────────────────────────────────────────

def _cfbd_api_key() -> str:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    return os.getenv("CFBD_API_KEY", "").strip()


def _load_json_cache(path: Path) -> Optional[list]:
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_json_cache(path: Path, data: list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _load_tpa_cache(cfbd_college: str, year: int) -> tuple[bool, Optional[float]]:
    """Load team pass attempts from local cache.

    Returns (cache_hit, value):
      (False, None)  — no cache file; caller should fetch from API
      (True, float)  — positive cache; use the stored value
      (True, None)   — negative cache; API returned nothing last time; skip re-fetch
    """
    safe_name = re.sub(r"[^a-z0-9]", "_", cfbd_college.lower())
    path = CACHE_DIR / f"tpa_{safe_name}_{year}.json"
    if not path.exists():
        return False, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        value = float(raw) if raw is not None else None
        return True, value
    except Exception:
        return False, None


def _save_tpa_cache(cfbd_college: str, year: int, value: Optional[float]) -> None:
    """Save team pass attempts to local cache. Writes null for negative caching."""
    safe_name = re.sub(r"[^a-z0-9]", "_", cfbd_college.lower())
    path = CACHE_DIR / f"tpa_{safe_name}_{year}.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _load_games_count_cache(cfbd_team: str, year: int) -> tuple[bool, Optional[int]]:
    """Load team games count from local cache.

    Returns (cache_hit, value):
      (False, None)  — no cache file; caller should fetch from API
      (True, int)    — positive cache; use the stored value
      (True, None)   — negative cache; API returned nothing last time; skip re-fetch
    """
    safe_name = re.sub(r"[^a-z0-9]", "_", cfbd_team.lower())
    path = CACHE_DIR / f"games_count_{safe_name}_{year}.json"
    if not path.exists():
        return False, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        value = int(raw) if raw is not None else None
        return True, value
    except Exception:
        return False, None


def _save_games_count_cache(cfbd_team: str, year: int, value: Optional[int]) -> None:
    """Save team games count to local cache. Writes null for negative caching."""
    safe_name = re.sub(r"[^a-z0-9]", "_", cfbd_team.lower())
    path = CACHE_DIR / f"games_count_{safe_name}_{year}.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def load_team_games_count(cfbd_team: str, year: int, api_key: str,
                          force_fetch: bool = False) -> Optional[int]:
    """Return regular-season game count for cfbd_team/year from CFBD /games endpoint.

    Returns an integer count, or None if the team/year has no data or the API fails.
    Results are cached individually (mirrors TPA cache pattern).
    """
    if not force_fetch:
        hit, cached = _load_games_count_cache(cfbd_team, year)
        if hit:
            return cached

    try:
        resp = httpx.get(
            f"{CFBD_BASE}/games",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"year": year, "team": cfbd_team, "seasonType": "regular"},
            timeout=30,
        )
        resp.raise_for_status()
        games = resp.json()
        count = len(games) if games else None
    except Exception:
        count = None

    _save_games_count_cache(cfbd_team, year, count)
    return count


def load_player_stats(year: int, category: str, api_key: str,
                      force_fetch: bool = False) -> list[dict]:
    """Load player season stats from local cache or CFBD API."""
    cache_path = CACHE_DIR / f"player_{category}_{year}.json"
    if not force_fetch:
        cached = _load_json_cache(cache_path)
        if cached is not None:
            return cached

    resp = httpx.get(
        f"{CFBD_BASE}/stats/player/season",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"year": year, "category": category, "seasonType": "regular"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _save_json_cache(cache_path, data)
    return data


def load_sp_ratings(year: int, api_key: str,
                    force_fetch: bool = False) -> list[dict]:
    """Load SP+ ratings from local cache or CFBD API."""
    cache_path = CACHE_DIR / f"sp_ratings_{year}.json"
    if not force_fetch:
        cached = _load_json_cache(cache_path)
        if cached is not None:
            return cached

    resp = httpx.get(
        f"{CFBD_BASE}/ratings/sp",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"year": year},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _save_json_cache(cache_path, data)
    return data


# ── Pivot functions ───────────────────────────────────────────────────────────

def pivot_receiving_stats(records: list[dict], year: int) -> dict[tuple, dict]:
    """Pivot CFBD receiving stat records into a keyed lookup.

    Key: (normalize_player_name, lowercase_school, year)
    Value: {'rec_yds', 'rec', 'rec_td', 'games'} — only keys present in records.

    Note: CFBD /stats/player/season returns LONG, REC, TD, YDS, YPR for
    receiving — 'G' (games) is not returned by this endpoint in practice.
    """
    stat_map = {"YDS": "rec_yds", "REC": "rec", "TD": "rec_td", "G": "games"}
    result: dict[tuple, dict] = {}
    for rec in records:
        name_key = normalize_player_name(rec.get("player", ""))
        school_key = _norm_school_key(rec.get("team", ""))
        stat_type = rec.get("statType", "")
        if stat_type not in stat_map:
            continue
        try:
            val = float(rec.get("stat", 0))
        except (ValueError, TypeError):
            continue
        key = (name_key, school_key, year)
        result.setdefault(key, {})[stat_map[stat_type]] = val
    return result


def pivot_rushing_stats(records: list[dict], year: int) -> dict[tuple, dict]:
    """Pivot CFBD rushing stat records into a keyed lookup.

    Key: (normalize_player_name, lowercase_school, year)
    Value: {'rush_yds', 'rush_att', 'rush_td', 'games'} — only keys present.

    Note: CFBD /stats/player/season returns CAR, LONG, TD, YDS, YPC for
    rushing — 'G' (games) is not returned by this endpoint in practice.
    """
    stat_map = {"YDS": "rush_yds", "CAR": "rush_att", "TD": "rush_td", "G": "games"}
    result: dict[tuple, dict] = {}
    for rec in records:
        name_key = normalize_player_name(rec.get("player", ""))
        school_key = _norm_school_key(rec.get("team", ""))
        stat_type = rec.get("statType", "")
        if stat_type not in stat_map:
            continue
        try:
            val = float(rec.get("stat", 0))
        except (ValueError, TypeError):
            continue
        key = (name_key, school_key, year)
        result.setdefault(key, {})[stat_map[stat_type]] = val
    return result


# ── Team aggregate lookups ────────────────────────────────────────────────────

def build_team_rec_lookup(rec_pivot: dict[tuple, dict]) -> dict[tuple, float]:
    """Sum player receiving yards by (lowercase_school, year)."""
    result: dict[tuple, float] = {}
    for (name, school, year), stats in rec_pivot.items():
        key = (school, year)
        result[key] = result.get(key, 0.0) + stats.get("rec_yds", 0.0)
    return result


def build_team_td_lookup(rec_pivot: dict[tuple, dict]) -> dict[tuple, float]:
    """Sum player receiving TDs by (lowercase_school, year)."""
    result: dict[tuple, float] = {}
    for (name, school, year), stats in rec_pivot.items():
        key = (school, year)
        result[key] = result.get(key, 0.0) + stats.get("rec_td", 0.0)
    return result


def build_team_rush_lookup(rush_pivot: dict[tuple, dict]) -> dict[tuple, float]:
    """Sum player rushing yards by (lowercase_school, year)."""
    result: dict[tuple, float] = {}
    for (name, school, year), stats in rush_pivot.items():
        key = (school, year)
        result[key] = result.get(key, 0.0) + stats.get("rush_yds", 0.0)
    return result


def build_sp_lookup(sp_records: list[dict], year: int) -> dict[tuple, float]:
    """Build (lowercase_school, year) → SP+ overall rating lookup."""
    result: dict[tuple, float] = {}
    for rec in sp_records:
        team = rec.get("team", "")
        school_key = _norm_school_key(team)
        try:
            rating = float(rec.get("rating", 0))
        except (ValueError, TypeError):
            continue
        result[(school_key, year)] = rating
    return result


# ── Shared helpers ────────────────────────────────────────────────────────────

def _get_player_seasons(
    name: str,
    college: str,
    draft_year: int,
    pivot: dict[tuple, dict],
) -> list[tuple[int, dict]]:
    """Return list of (year, stats_dict) for a player across their college years.

    Searches draft_year-5 through draft_year-1. Returns only years where the
    player has non-zero data in the pivot.
    """
    norm_name = normalize_player_name(name)
    norm_school = _norm_school_key(college)
    seasons = []
    for look_year in range(max(2011, draft_year - 5), draft_year):
        key = (norm_name, norm_school, look_year)
        stats = pivot.get(key)
        if stats and any(v > 0 for v in stats.values() if isinstance(v, (int, float))):
            seasons.append((look_year, stats))
    return seasons


def _age_in_season(age_at_draft: float, draft_year: int, season_year: int) -> float:
    """Approximate age during a past college season."""
    return round(age_at_draft - (draft_year - season_year), 1)


# ── WR feature computation ────────────────────────────────────────────────────

def compute_wr_cfbd_features(
    row: dict,
    rec_pivot: dict[tuple, dict],
    team_rec_lookup: dict[tuple, float],
    team_td_lookup: dict[tuple, float],
    team_pass_attempts_lookup: dict[tuple, float] | None = None,
) -> dict[str, str]:
    """Compute WR CFBD-derived features for a single row.

    wr_dominator_final: average of yard share and TD share in final season (spec §3A.1).
    wr_market_share_yds: yards share only in final season (spec §3A.3).
    ryptpa: rec_yds_final / team_pass_attempts (same formula as te_ryptpa_final; uses downstream contract name).
    wr_rec_tds_per_game_final: DARK — CFBD does not return games for this endpoint.
    yprr_college: DARK — requires PFF premium routes-run data absent from CFBD.
    """
    if team_pass_attempts_lookup is None:
        team_pass_attempts_lookup = {}
    result: dict[str, str] = {}
    _computed_cols = (
        "wr_dominator_final", "wr_breakout_age", "wr_market_share_yds",
        "wr_yards_per_reception_career", "ryptpa",
    )
    _dark_cols = ("wr_rec_tds_per_game_final", "yprr_college")

    # Dark features: always _missing=1 — games not available from CFBD player stats
    for col in _dark_cols:
        result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})

    try:
        draft_year = int(row.get("season", 0))
        age_at_draft = float(row.get("age_at_draft", "0") or 0)
    except (ValueError, TypeError):
        for col in _computed_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        return result

    name = row.get("pfr_player_name", "")
    college = row.get("college", "")
    seasons = _get_player_seasons(name, college, draft_year, rec_pivot)

    if not seasons:
        for col in _computed_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        return result

    norm_school = _norm_school_key(college)

    # Per-season dominator: average of yard share and TD share (spec §3A.1)
    annotated = []
    for year, stats in seasons:
        rec_yds = stats.get("rec_yds", 0.0)
        rec_td = stats.get("rec_td", 0.0)
        team_yds = team_rec_lookup.get((norm_school, year), 0.0)
        team_tds = team_td_lookup.get((norm_school, year), 0.0)

        yds_share = (rec_yds / team_yds) if team_yds > 0 else None
        td_share = (rec_td / team_tds) if team_tds > 0 else None

        if yds_share is not None and td_share is not None:
            dominator = round((yds_share + td_share) / 2, 4)
        elif yds_share is not None:
            dominator = round(yds_share, 4)  # fallback when team TDs unavailable
        else:
            dominator = None

        annotated.append({
            "year": year,
            "rec_yds": rec_yds,
            "rec": stats.get("rec", 0.0),
            "rec_td": rec_td,
            "dominator": dominator,
            "yds_share": yds_share,
            "age": _age_in_season(age_at_draft, draft_year, year),
        })

    final = annotated[-1]
    final_year = final["year"]
    final_team_yds = team_rec_lookup.get((norm_school, final_year), 0.0)

    # wr_dominator_final: avg(yds_share, td_share) in final season
    if final["dominator"] is not None:
        result.update({"wr_dominator_final": str(round(final["dominator"], 4)),
                       "wr_dominator_final_missing": "0",
                       "wr_dominator_final_source": "cfbd"})
    else:
        result.update({"wr_dominator_final": "", "wr_dominator_final_missing": "1",
                       "wr_dominator_final_source": ""})

    # wr_market_share_yds: yards share only in final season (spec §3A.3)
    if final["yds_share"] is not None:
        result.update({"wr_market_share_yds": str(round(final["yds_share"], 4)),
                       "wr_market_share_yds_missing": "0",
                       "wr_market_share_yds_source": "cfbd"})
    else:
        result.update({"wr_market_share_yds": "", "wr_market_share_yds_missing": "1",
                       "wr_market_share_yds_source": ""})

    # wr_breakout_age: first season where dominator >= threshold
    breakout_age: Optional[float] = None
    for s_data in annotated:
        if (s_data["dominator"] is not None
                and s_data["dominator"] >= DOMINATOR_BREAKOUT_THRESHOLD):
            breakout_age = s_data["age"]
            break
    if breakout_age is not None:
        result.update({"wr_breakout_age": str(breakout_age),
                       "wr_breakout_age_missing": "0",
                       "wr_breakout_age_source": "cfbd_proxy"})
    else:
        result.update({"wr_breakout_age": "", "wr_breakout_age_missing": "1",
                       "wr_breakout_age_source": ""})

    # wr_yards_per_reception_career: total career rec_yds / total career rec
    total_yds = sum(s["rec_yds"] for s in annotated)
    total_rec = sum(s["rec"] for s in annotated)
    if total_rec > 0:
        ypr = round(total_yds / total_rec, 2)
        result.update({"wr_yards_per_reception_career": str(ypr),
                       "wr_yards_per_reception_career_missing": "0",
                       "wr_yards_per_reception_career_source": "cfbd"})
    else:
        result.update({"wr_yards_per_reception_career": "",
                       "wr_yards_per_reception_career_missing": "1",
                       "wr_yards_per_reception_career_source": ""})

    # ryptpa: final_season_rec_yds / team_pass_attempts (same formula as te_ryptpa_final)
    cfbd_college = normalize_college_name(college)
    final_rec_yds = final["rec_yds"]
    tpa = team_pass_attempts_lookup.get((cfbd_college, final_year))
    if tpa and tpa > 0 and final_rec_yds > 0:
        ryptpa_val = round(final_rec_yds / tpa, 4)
        result.update({"ryptpa": str(ryptpa_val),
                       "ryptpa_missing": "0",
                       "ryptpa_source": "cfbd"})
    else:
        result.update({"ryptpa": "", "ryptpa_missing": "1",
                       "ryptpa_source": ""})

    return result


# ── RB feature computation ────────────────────────────────────────────────────

def compute_rb_cfbd_features(
    row: dict,
    rush_pivot: dict[tuple, dict],
    rec_pivot: dict[tuple, dict],
    team_rush_lookup: dict[tuple, float],
    team_rec_lookup: dict[tuple, float],
    sp_lookup: dict[tuple, float],
    team_games_lookup: dict[tuple, int] | None = None,
) -> dict[str, str]:
    """Compute RB CFBD-derived features for a single row.

    rb_final_dominator: (player_rush_yds + player_rec_yds) / (team_rush_yds + team_rec_yds)
      in the player's final college season (spec §3B.1 scrimmage formula).
    rb_scrimmage_ypg, rb_rec_ypg: computed from team_games_lookup when provided;
      dark (_missing=1) when lookup is absent or has no entry for this team/year.
    """
    if team_games_lookup is None:
        team_games_lookup = {}
    result: dict[str, str] = {}
    _computed_cols = ("rb_final_dominator", "rb_school_sp_plus")

    try:
        draft_year = int(row.get("season", 0))
    except (ValueError, TypeError):
        for col in _computed_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        return result

    name = row.get("pfr_player_name", "")
    college = row.get("college", "")
    norm_school = _norm_school_key(college)
    final_year = draft_year - 1

    rush_seasons = _get_player_seasons(name, college, draft_year, rush_pivot)
    rec_seasons = _get_player_seasons(name, college, draft_year, rec_pivot)

    # ── rb_final_dominator: scrimmage formula (spec §3B.1) ────────────────────
    final_rush = next((s for y, s in rush_seasons if y == final_year), None)
    player_rush_yds = 0.0
    player_rec_yds = 0.0

    if final_rush is not None:
        player_rush_yds = final_rush.get("rush_yds", 0.0)
        final_rec = next((s for y, s in rec_seasons if y == final_year), None)
        player_rec_yds = final_rec.get("rec_yds", 0.0) if final_rec else 0.0

        team_rush_yds = team_rush_lookup.get((norm_school, final_year), 0.0)
        team_rec_yds = team_rec_lookup.get((norm_school, final_year), 0.0)
        team_total = team_rush_yds + team_rec_yds
        player_total = player_rush_yds + player_rec_yds

        if team_total > 0:
            dom = round(player_total / team_total, 4)
            result.update({"rb_final_dominator": str(dom),
                           "rb_final_dominator_missing": "0",
                           "rb_final_dominator_source": "cfbd"})
        else:
            result.update({"rb_final_dominator": "", "rb_final_dominator_missing": "1",
                           "rb_final_dominator_source": ""})
    else:
        result.update({"rb_final_dominator": "", "rb_final_dominator_missing": "1",
                       "rb_final_dominator_source": ""})

    # ── rb_school_sp_plus ─────────────────────────────────────────────────────
    sp_rating = sp_lookup.get((norm_school, final_year))
    if sp_rating is not None:
        result.update({"rb_school_sp_plus": str(round(sp_rating, 2)),
                       "rb_school_sp_plus_missing": "0",
                       "rb_school_sp_plus_source": "cfbd_sp_plus"})
    else:
        result.update({"rb_school_sp_plus": "", "rb_school_sp_plus_missing": "1",
                       "rb_school_sp_plus_source": ""})

    # ── rb_yards_per_carry_final: rush_yds / rush_att (final season) ─────────
    rush_att = final_rush.get("rush_att", 0.0) if final_rush is not None else 0.0
    if final_rush is not None and rush_att >= 50.0:
        ypc = round(player_rush_yds / rush_att, 4)
        result.update({"rb_yards_per_carry_final": str(ypc),
                       "rb_yards_per_carry_final_missing": "0",
                       "rb_yards_per_carry_final_source": "cfbd"})
    else:
        src = "below_volume_gate" if 0 < rush_att < 50.0 else ""
        result.update({"rb_yards_per_carry_final": "",
                       "rb_yards_per_carry_final_missing": "1",
                       "rb_yards_per_carry_final_source": src})

    # ── rb_yards_per_reception_career: career rec_yds / career rec ───────────
    career_rec_yds = sum(s.get("rec_yds", 0.0) for _, s in rec_seasons)
    career_rec = sum(s.get("rec", 0.0) for _, s in rec_seasons)
    if career_rec >= 10.0:
        ypr = round(career_rec_yds / career_rec, 4)
        result.update({"rb_yards_per_reception_career": str(ypr),
                       "rb_yards_per_reception_career_missing": "0",
                       "rb_yards_per_reception_career_source": "cfbd"})
    else:
        src = "below_volume_gate" if 0 < career_rec < 10.0 else ""
        result.update({"rb_yards_per_reception_career": "",
                       "rb_yards_per_reception_career_missing": "1",
                       "rb_yards_per_reception_career_source": src})

    # ── rb_scrimmage_ypg: (rush_yds + rec_yds) / team_games ──────────────────
    games_count = team_games_lookup.get((norm_school, final_year))
    scrimmage_yds = player_rush_yds + player_rec_yds
    if games_count is not None and games_count > 0 and scrimmage_yds > 0:
        spg = round(scrimmage_yds / games_count, 2)
        result.update({"rb_scrimmage_ypg": str(spg),
                       "rb_scrimmage_ypg_missing": "0",
                       "rb_scrimmage_ypg_source": "cfbd_team_games_proxy"})
    else:
        result.update({"rb_scrimmage_ypg": "", "rb_scrimmage_ypg_missing": "1",
                       "rb_scrimmage_ypg_source": ""})

    # ── rb_rec_ypg: rec_yds / team_games ─────────────────────────────────────
    if games_count is not None and games_count > 0 and player_rec_yds > 0:
        rpg = round(player_rec_yds / games_count, 2)
        result.update({"rb_rec_ypg": str(rpg),
                       "rb_rec_ypg_missing": "0",
                       "rb_rec_ypg_source": "cfbd_team_games_proxy"})
    else:
        result.update({"rb_rec_ypg": "", "rb_rec_ypg_missing": "1",
                       "rb_rec_ypg_source": ""})

    return result


# ── TE feature computation ────────────────────────────────────────────────────

def compute_te_cfbd_features(
    row: dict,
    rec_pivot: dict[tuple, dict],
    team_pass_attempts_lookup: dict[tuple, float],
) -> dict[str, str]:
    """Compute TE CFBD-derived features for a single row."""
    result: dict[str, str] = {}
    _te_cols = ("te_ryptpa_final", "te_yards_per_reception_career")

    try:
        draft_year = int(row.get("season", 0))
    except (ValueError, TypeError):
        for col in _te_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        return result

    name = row.get("pfr_player_name", "")
    college = row.get("college", "")
    final_year = draft_year - 1

    rec_seasons = _get_player_seasons(name, college, draft_year, rec_pivot)

    # ── te_ryptpa_final ───────────────────────────────────────────────────────
    final_rec = next((s for y, s in rec_seasons if y == final_year), None)
    if final_rec:
        rec_yds = final_rec.get("rec_yds", 0.0)
        cfbd_college = normalize_college_name(college)
        tpa = team_pass_attempts_lookup.get((cfbd_college, final_year))
        if tpa and tpa > 0 and rec_yds > 0:
            ryptpa = round(rec_yds / tpa, 4)
            result.update({"te_ryptpa_final": str(ryptpa),
                           "te_ryptpa_final_missing": "0",
                           "te_ryptpa_final_source": "cfbd"})
        else:
            result.update({"te_ryptpa_final": "", "te_ryptpa_final_missing": "1",
                           "te_ryptpa_final_source": ""})
    else:
        result.update({"te_ryptpa_final": "", "te_ryptpa_final_missing": "1",
                       "te_ryptpa_final_source": ""})

    # ── te_yards_per_reception_career ─────────────────────────────────────────
    total_yds = sum(s.get("rec_yds", 0.0) for _, s in rec_seasons)
    total_rec = sum(s.get("rec", 0.0) for _, s in rec_seasons)
    if total_rec > 0:
        ypr = round(total_yds / total_rec, 2)
        result.update({"te_yards_per_reception_career": str(ypr),
                       "te_yards_per_reception_career_missing": "0",
                       "te_yards_per_reception_career_source": "cfbd"})
    else:
        result.update({"te_yards_per_reception_career": "",
                       "te_yards_per_reception_career_missing": "1",
                       "te_yards_per_reception_career_source": ""})

    return result


# ── QB feature computation (Phase 20 W3) ─────────────────────────────────────

def compute_qb_cfbd_features(
    row: dict,
    api_key: str,
    cache_dir: Path,
) -> dict[str, str]:
    """Compute QB CFBD features by calling fetch_qb_college_stats() per player.

    Caches the adapter result to avoid repeat API calls across rebuild runs.
    Volume gate: pass_attempts < 100 → all four features dark (_missing=1).
    """
    result: dict[str, str] = {}
    _qb_cols = (
        "qb_completion_pct_final",
        "qb_yards_per_attempt_final",
        "qb_td_int_ratio_final",
        "qb_sack_rate_final",
    )
    _feature_map = {
        "qb_completion_pct_final": "completion_pct",
        "qb_yards_per_attempt_final": "yards_per_attempt",
        "qb_td_int_ratio_final": "td_int_ratio",
        "qb_sack_rate_final": "sack_rate",
    }

    try:
        draft_year = int(row.get("season", 0))
    except (ValueError, TypeError):
        for col in _qb_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        return result

    name = row.get("pfr_player_name", "")
    final_year = draft_year - 1
    cache_key = f"qb_stats_{normalize_player_name(name)}_{final_year}.json"
    cache_path = cache_dir / cache_key

    if cache_path.exists():
        stats: dict = json.loads(cache_path.read_text())
    else:
        stats = fetch_qb_college_stats(name, final_year, api_key)
        cache_path.write_text(json.dumps(stats))

    pass_attempts = stats.get("pass_attempts")
    if pass_attempts is None or pass_attempts < 100:
        src = "below_volume_gate" if pass_attempts is not None and pass_attempts > 0 else ""
        for col in _qb_cols:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": src})
        return result

    for col, adapter_key in _feature_map.items():
        val = stats.get(adapter_key)
        if val is not None:
            result.update({col: str(round(float(val), 6)),
                           f"{col}_missing": "0",
                           f"{col}_source": "cfbd"})
        else:
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})

    return result


# ── Era proxy features (no API) ───────────────────────────────────────────────

def compute_era_proxy_features(row: dict) -> dict[str, str]:
    """Compute era-flag features from existing v3 CSV columns — no API call.

    Simplified proxy formulas (see spec §3D):
      final_college_age = age_at_draft - 1   (assumes final_college_season = draft_year - 1)
      early_declare     = 1 if age_at_draft <= 21.0
      covid_eligibility_flag = 1 if draft_year ∈ {2021, 2022} AND age_at_draft >= 23.0

    All values labeled proxy_age_at_draft to distinguish from CFBD-verified data.
    wr_early_declare is populated for WR rows only; other positions get stubs.
    """
    result: dict[str, str] = {}

    age_val = row.get("age_at_draft", "")
    age_missing = row.get("age_at_draft_missing", "1")
    position = row.get("position", "")

    try:
        draft_year = int(row.get("season", 0))
        age = float(age_val) if age_val and age_missing == "0" else None
    except (ValueError, TypeError):
        age = None
        draft_year = 0

    if age is None:
        for col in ("final_college_age", "early_declare", "covid_eligibility_flag"):
            result.update({col: "", f"{col}_missing": "1", f"{col}_source": ""})
        result.update({"wr_early_declare": "", "wr_early_declare_missing": "1",
                       "wr_early_declare_source": ""})
        return result

    # final_college_age: proxy assumes player's final season was draft_year - 1
    fca = round(age - 1.0, 1)
    result.update({"final_college_age": str(fca), "final_college_age_missing": "0",
                   "final_college_age_source": "proxy_age_at_draft"})

    # early_declare
    ed = "1" if age <= EARLY_DECLARE_AGE_THRESHOLD else "0"
    result.update({"early_declare": ed, "early_declare_missing": "0",
                   "early_declare_source": "proxy_age_at_draft"})

    # wr_early_declare (WR-specific; stubs for other positions)
    if position == "WR":
        result.update({"wr_early_declare": ed, "wr_early_declare_missing": "0",
                       "wr_early_declare_source": "proxy_age_at_draft"})
    else:
        result.update({"wr_early_declare": "", "wr_early_declare_missing": "1",
                       "wr_early_declare_source": ""})

    # covid_eligibility_flag: proxy for players who likely took NCAA COVID extra year
    if draft_year in COVID_DRAFT_YEARS and age >= COVID_MIN_AGE:
        result.update({"covid_eligibility_flag": "1", "covid_eligibility_flag_missing": "0",
                       "covid_eligibility_flag_source": "proxy_draft_year_age"})
    else:
        result.update({"covid_eligibility_flag": "0", "covid_eligibility_flag_missing": "0",
                       "covid_eligibility_flag_source": "proxy_draft_year_age"})

    return result


# ── Leakage governance guard ──────────────────────────────────────────────────

def _assert_no_leakage() -> None:
    """Verify at startup that no W2b output column violates leakage contracts."""
    w2b_output_cols = {
        "wr_dominator_final", "wr_breakout_age", "wr_market_share_yds",
        "wr_yards_per_reception_career", "ryptpa", "yprr_college", "wr_early_declare",
        "rb_final_dominator", "rb_school_sp_plus", "rb_scrimmage_ypg", "rb_rec_ypg",
        "rb_yards_per_carry_final", "rb_yards_per_reception_career",
        "te_ryptpa_final", "te_yards_per_reception_career",
        "qb_completion_pct_final", "qb_yards_per_attempt_final",
        "qb_td_int_ratio_final", "qb_sack_rate_final",
        "final_college_age", "early_declare", "covid_eligibility_flag",
    }
    for col in w2b_output_cols:
        assert col not in HEAD_B_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: W2b column '{col}' is in HEAD_B_PROHIBITED_COLUMNS"
        )
        assert col not in MARKET_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: W2b column '{col}' is in MARKET_PROHIBITED_COLUMNS"
        )
        assert col not in PFF_GRADE_PROHIBITED_COLUMNS, (
            f"GOVERNANCE: W2b column '{col}' is in PFF_GRADE_PROHIBITED_COLUMNS"
        )


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main(force_fetch: bool = False, allow_degraded: bool = False, include_rb_ypg: bool = False) -> None:
    _assert_no_leakage()

    if not V3_CSV.exists():
        raise FileNotFoundError(
            f"V3 CSV not found: {V3_CSV}\n"
            "Run W1 then W2 first (build_head_b_targets.py → build_w2_features.py)."
        )

    print("Phase 19 W2b — CFBD Player-Level Enrichment")
    print(f"  Input: {V3_CSV}")

    source_sha256 = hashlib.sha256(V3_CSV.read_bytes()).hexdigest()
    with V3_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"  Loaded {len(rows)} rows  sha256=...{source_sha256[-8:]}")

    api_key = _cfbd_api_key()
    if not api_key:
        raise RuntimeError(
            "CFBD_API_KEY not set. Load .env or set the variable before running W2b."
        )

    # ── Fetch / cache year-batched player stats ───────────────────────────────
    print(f"\n  Fetching player stats for years {COLLEGE_YEARS[0]}–{COLLEGE_YEARS[-1]}...")
    rec_pivot: dict[tuple, dict] = {}
    rush_pivot: dict[tuple, dict] = {}
    sp_lookup: dict[tuple, float] = {}

    fetch_errors: list[str] = []
    for year in COLLEGE_YEARS:
        try:
            rec_raw = load_player_stats(year, "receiving", api_key, force_fetch)
            rec_pivot.update(pivot_receiving_stats(rec_raw, year))
        except Exception as exc:
            fetch_errors.append(f"receiving/{year}: {exc}")

        try:
            rush_raw = load_player_stats(year, "rushing", api_key, force_fetch)
            rush_pivot.update(pivot_rushing_stats(rush_raw, year))
        except Exception as exc:
            fetch_errors.append(f"rushing/{year}: {exc}")

        try:
            sp_raw = load_sp_ratings(year, api_key, force_fetch)
            sp_lookup.update(build_sp_lookup(sp_raw, year))
        except Exception as exc:
            fetch_errors.append(f"sp/{year}: {exc}")

    cfbd_degraded = False
    if fetch_errors:
        msg = "\n  ".join(fetch_errors)
        if allow_degraded:
            print(f"  [WARN] {len(fetch_errors)} fetch error(s) — degraded output:\n  {msg}")
            cfbd_degraded = True
        else:
            raise RuntimeError(
                f"{len(fetch_errors)} CFBD fetch error(s). Pass --allow-degraded to "
                f"continue with partial data.\n{msg}"
            )

    team_rec_lookup = build_team_rec_lookup(rec_pivot)
    team_td_lookup = build_team_td_lookup(rec_pivot)
    team_rush_lookup = build_team_rush_lookup(rush_pivot)
    print(f"  Receiving pivot: {len(rec_pivot)} player-year entries")
    print(f"  Rushing pivot:   {len(rush_pivot)} player-year entries")
    print(f"  SP+ lookup:      {len(sp_lookup)} team-year entries")

    # ── Pre-fetch TE+WR team pass attempts (cached individually) ─────────────
    print("\n  Pre-fetching TE+WR team pass attempts...")
    tpa_lookup: dict[tuple, float] = {}
    tpa_position_rows = [(r.get("pfr_player_name", ""), r.get("college", ""),
                          int(r.get("season", 0)))
                         for r in rows if r.get("position") in ("TE", "WR")]
    unique_tpa_team_years = {
        (normalize_college_name(college), max(2011, draft_year - 1))
        for (_, college, draft_year) in tpa_position_rows
        if draft_year > 2011
    }
    for cfbd_college, year in sorted(unique_tpa_team_years):
        if not force_fetch:
            hit, cached_tpa = _load_tpa_cache(cfbd_college, year)
            if hit:
                if cached_tpa is not None:
                    tpa_lookup[(cfbd_college, year)] = cached_tpa
                continue  # skip API call for both positive and negative cache hits
        tpa = fetch_team_pass_attempts(cfbd_college, year, api_key)
        _save_tpa_cache(cfbd_college, year, tpa)  # cache None too (negative cache)
        if tpa is not None:
            tpa_lookup[(cfbd_college, year)] = tpa
    print(f"  Team pass attempts: {len(tpa_lookup)}/{len(unique_tpa_team_years)} pairs populated")

    # ── Pre-fetch RB team games count (legacy ypg path — gated behind --include-rb-ypg) ──
    games_lookup: dict[tuple, int] = {}
    if include_rb_ypg:
        print("\n  Pre-fetching RB team games count...")
        rb_rows = [(r.get("pfr_player_name", ""), r.get("college", ""),
                    int(r.get("season", 0)))
                   for r in rows if r.get("position") == "RB"]
        unique_rb_team_years = {
            (_norm_school_key(college), max(2011, draft_year - 1))
            for (_, college, draft_year) in rb_rows
            if draft_year > 2011
        }
        for team_key, year in sorted(unique_rb_team_years):
            if not force_fetch:
                hit, cached_games = _load_games_count_cache(team_key, year)
                if hit:
                    if cached_games is not None:
                        games_lookup[(team_key, year)] = cached_games
                    continue
            games = load_team_games_count(team_key, year, api_key, force_fetch)
            if games is not None:
                games_lookup[(team_key, year)] = games
        print(f"  Team games count:   {len(games_lookup)}/{len(unique_rb_team_years)} pairs populated")

    # ── Enrich rows ───────────────────────────────────────────────────────────
    print("\n  Enriching rows...")
    n_wr_hit = n_rb_hit = n_te_hit = n_qb_hit = 0
    position_counts: dict[str, int] = {}

    for row in rows:
        position = row.get("position", "")
        position_counts[position] = position_counts.get(position, 0) + 1

        # Era proxy features (all positions)
        row.update(compute_era_proxy_features(row))

        if position == "WR":
            feats = compute_wr_cfbd_features(
                row, rec_pivot, team_rec_lookup, team_td_lookup,
                team_pass_attempts_lookup=tpa_lookup,
            )
            if feats.get("wr_dominator_final_missing") == "0":
                n_wr_hit += 1
            row.update(feats)

        elif position == "RB":
            feats = compute_rb_cfbd_features(
                row, rush_pivot, rec_pivot, team_rush_lookup, team_rec_lookup, sp_lookup,
                team_games_lookup=games_lookup,
            )
            if feats.get("rb_final_dominator_missing") == "0":
                n_rb_hit += 1
            row.update(feats)

        elif position == "TE":
            feats = compute_te_cfbd_features(row, rec_pivot, tpa_lookup)
            if feats.get("te_ryptpa_final_missing") == "0":
                n_te_hit += 1
            row.update(feats)

        elif position == "QB":
            feats = compute_qb_cfbd_features(row, api_key, CACHE_DIR)
            if feats.get("qb_completion_pct_final_missing") == "0":
                n_qb_hit += 1
            row.update(feats)

    # ── Degraded provenance flag — always written ─────────────────────────────
    degraded_val = "1" if cfbd_degraded else "0"
    for row in rows:
        row["w2b_cfbd_degraded"] = degraded_val

    # ── Coverage summary ──────────────────────────────────────────────────────
    wr_total = position_counts.get("WR", 0)
    rb_total = position_counts.get("RB", 0)
    te_total = position_counts.get("TE", 0)
    qb_total = position_counts.get("QB", 0)
    if wr_total:
        print(f"\n  WR dominator_final populated: {n_wr_hit}/{wr_total} "
              f"({100 * n_wr_hit / wr_total:.1f}%)")
    if rb_total:
        print(f"  RB final_dominator populated:  {n_rb_hit}/{rb_total} "
              f"({100 * n_rb_hit / rb_total:.1f}%)")
    if te_total:
        print(f"  TE ryptpa_final populated:     {n_te_hit}/{te_total} "
              f"({100 * n_te_hit / te_total:.1f}%)")
    if qb_total:
        print(f"  QB completion_pct populated:   {n_qb_hit}/{qb_total} "
              f"({100 * n_qb_hit / qb_total:.1f}%)")
    print(f"  w2b_cfbd_degraded: {degraded_val}")

    # ── Write enriched CSV ────────────────────────────────────────────────────
    if rows:
        # Build fieldnames from union of all row keys (order: original columns first,
        # then any new columns added by enrichment for a subset of positions).
        seen: set[str] = set()
        fieldnames: list[str] = []
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    fieldnames.append(k)
                    seen.add(k)
        with V3_CSV.open("w", newline="", encoding="utf-8") as f:
            # restval="" fills missing keys for rows that lack position-specific columns
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
            writer.writeheader()
            writer.writerows(rows)
    new_sha256 = hashlib.sha256(V3_CSV.read_bytes()).hexdigest()
    print(f"\n  Written: {V3_CSV}")
    print(f"  Columns: {len(fieldnames) if rows else 0}")
    print(f"  New sha256=...{new_sha256[-8:]}")
    print("  promotion_decision: NOT_APPLICABLE (W2b data pipeline only)")


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description="Phase 19 W2b CFBD Enrichment")
    _parser.add_argument("--force-fetch", action="store_true",
                         help="Bypass local JSON cache and re-fetch from CFBD API.")
    _parser.add_argument("--allow-degraded", action="store_true",
                         help="Continue with partial data if some API calls fail.")
    _parser.add_argument("--include-rb-ypg", action="store_true",
                         help="Enable legacy RB scrimmage/rec YPG path (calls CFBD /games endpoint).")
    _args = _parser.parse_args()
    main(force_fetch=_args.force_fetch, allow_degraded=_args.allow_degraded,
         include_rb_ypg=_args.include_rb_ypg)
