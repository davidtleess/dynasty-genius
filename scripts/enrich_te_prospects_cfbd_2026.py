"""Enrich 2026 TE prospect cards with CFBD college stats.

Fetches receiving stats for the 2026 TE draft class and computes the three
features required by the Engine A v3 Ridge model:

    te_ryptpa_final              — final_season_rec_yds / team_pass_attempts
    te_yards_per_reception_career — career_rec_yds / career_rec
    final_college_age            — age - 1.0  (proxy; same convention as build_w2b_cfbd.py)

Also pre-scores each TE via score_prospect_v3() and writes the updated
dynasty_value_score back to the card.  This establishes the new v3 DVS as the
invariance baseline so that the subsequent refresh_prospect_cards.py run
passes the DVS-drift gate cleanly.

Reads:  resources/prospect_cards.json (22 TE rows)
Writes: resources/prospect_cards.json (three features + updated DVS)

After running:
    .venv/bin/python3.14 scripts/refresh_prospect_cards.py

API strategy:
    - Player stats fetched year-by-year via the existing cache pattern from
      build_w2b_cfbd.py.  2025 data is new; earlier years reuse cache.
    - School discovery: player's school is found by name-matching in the
      CFBD receiving data (identity file has no college field for 2026 class).
    - Team pass attempts fetched per (school, final_year) with individual cache.

Usage:
    .venv/bin/python3.14 scripts/enrich_te_prospects_cfbd_2026.py
    .venv/bin/python3.14 scripts/enrich_te_prospects_cfbd_2026.py --force-fetch
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.cfbd_receiving_adapter import (  # noqa: E402
    fetch_team_pass_attempts,
    normalize_college_name,
)
from src.dynasty_genius.scoring.engine_a import score_prospect_v3  # noqa: E402

CARDS_JSON = ROOT / "resources" / "prospect_cards.json"
CACHE_DIR = ROOT / "app" / "data" / "cfbd_cache"
CFBD_BASE = "https://api.collegefootballdata.com"

# 2026 draft class: career window is 2021-2025
DRAFT_YEAR = 2026
COLLEGE_YEARS = list(range(2021, 2026))  # 2021, 2022, 2023, 2024, 2025


# ── Name normalization (mirrors build_w2b_cfbd.py) ────────────────────────────

def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def _norm_school(school: str) -> str:
    return normalize_college_name(school).lower()


# ── Cache helpers (mirror build_w2b_cfbd.py) ─────────────────────────────────

def _cfbd_api_key() -> str:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    return os.getenv("CFBD_API_KEY", "").strip()


def _load_cache(path: Path) -> Optional[list]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _save_cache(path: Path, data: list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _load_tpa_cache(cfbd_college: str, year: int) -> tuple[bool, Optional[float]]:
    safe = re.sub(r"[^a-z0-9]", "_", cfbd_college.lower())
    path = CACHE_DIR / f"tpa_{safe}_{year}.json"
    if not path.exists():
        return False, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return True, float(raw) if raw is not None else None
    except Exception:
        return False, None


def _save_tpa_cache(cfbd_college: str, year: int, value: Optional[float]) -> None:
    safe = re.sub(r"[^a-z0-9]", "_", cfbd_college.lower())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"tpa_{safe}_{year}.json").write_text(json.dumps(value), encoding="utf-8")


# ── CFBD fetch helpers ────────────────────────────────────────────────────────

def _fetch_receiving(year: int, api_key: str, force: bool) -> list[dict]:
    path = CACHE_DIR / f"player_receiving_{year}.json"
    if not force:
        cached = _load_cache(path)
        if cached is not None:
            return cached
    resp = httpx.get(
        f"{CFBD_BASE}/stats/player/season",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"year": year, "category": "receiving", "seasonType": "regular"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _save_cache(path, data)
    return data


def _pivot_receiving(records: list[dict], year: int) -> dict[tuple, dict]:
    """(norm_name, norm_school, year) → {rec_yds, rec} — mirrors build_w2b_cfbd.py."""
    stat_map = {"YDS": "rec_yds", "REC": "rec"}
    result: dict[tuple, dict] = {}
    for rec in records:
        name_key = _norm_name(rec.get("player", ""))
        school_key = _norm_school(rec.get("team", ""))
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


# ── Player-season lookup ──────────────────────────────────────────────────────

def _player_seasons(
    name: str,
    pivot: dict[tuple, dict],
) -> list[tuple[int, str, dict]]:
    """Return [(year, cfbd_school, stats)] for all seasons the player appears.

    Searches all schools in the pivot so we can discover the player's college
    even though it's absent from the identity file.
    """
    norm = _norm_name(name)
    results = []
    for (n, school, yr), stats in pivot.items():
        if n == norm and any(v > 0 for v in stats.values() if isinstance(v, (int, float))):
            results.append((yr, school, stats))
    # sort by year ascending
    results.sort(key=lambda x: x[0])
    return results


def _get_cfbd_school_canonical(school_key: str, raw_pivot: dict) -> str:
    """Recover the un-normalised CFBD team name from the raw pivot records."""
    # The pivot uses normalised keys; we need the original name to call
    # normalize_college_name() correctly for the TPA fetch.
    # We stored only the normalised key, so we reconstruct via
    # normalize_college_name() of the lowercase school — good enough because
    # fetch_team_pass_attempts() calls normalize_college_name() internally.
    return school_key  # caller will pass this to normalize_college_name indirectly


# ── TPA fetch ─────────────────────────────────────────────────────────────────

def _get_tpa(raw_school: str, year: int, api_key: str, force: bool) -> Optional[float]:
    """Return team pass attempts for (raw_school, year), caching individually."""
    cfbd_name = normalize_college_name(raw_school)
    if not force:
        hit, cached = _load_tpa_cache(cfbd_name, year)
        if hit:
            return cached
    tpa = fetch_team_pass_attempts(raw_school, year, api_key)
    _save_tpa_cache(cfbd_name, year, tpa)
    return tpa


# ── Reverse-lookup: normalised school key → raw CFBD team name ───────────────

def _build_school_raw_map(records_by_year: dict[int, list[dict]]) -> dict[str, str]:
    """Build {norm_school_key → first-seen raw CFBD team name} across all years."""
    result: dict[str, str] = {}
    for records in records_by_year.values():
        for rec in records:
            raw = rec.get("team", "")
            key = _norm_school(raw)
            if key and key not in result:
                result[key] = raw
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main(force_fetch: bool = False) -> None:
    api_key = _cfbd_api_key()
    if not api_key:
        raise RuntimeError("CFBD_API_KEY not set. Load .env before running.")

    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    tes = [c for c in cards if c.get("position") == "TE" and c.get("draft_class") == 2026]
    if not tes:
        raise RuntimeError("No 2026 TE cards found in prospect_cards.json.")
    print(f"2026 TE prospects: {len(tes)}")

    # ── Fetch receiving stats for career window ───────────────────────────────
    print(f"\nFetching receiving stats for {COLLEGE_YEARS[0]}–{COLLEGE_YEARS[-1]}...")
    pivot: dict[tuple, dict] = {}
    records_by_year: dict[int, list[dict]] = {}
    for year in COLLEGE_YEARS:
        try:
            raw = _fetch_receiving(year, api_key, force_fetch)
            records_by_year[year] = raw
            pivot.update(_pivot_receiving(raw, year))
            cached_label = "" if force_fetch else " (cache)"
            print(f"  {year}: {len(raw)} stat records{cached_label}")
        except Exception as exc:
            print(f"  [WARN] {year}: fetch error — {exc}")
            records_by_year[year] = []

    school_raw_map = _build_school_raw_map(records_by_year)
    print(f"  Receiving pivot: {len(pivot)} player-year entries across {len(school_raw_map)} schools")

    # ── Enrich each TE ────────────────────────────────────────────────────────
    print("\nEnriching TE prospects...")

    results_table: list[dict] = []
    n_v3 = 0
    n_v3_partial = 0  # has career stats but no RYPTPA
    n_miss = 0        # no CFBD match at all

    for card in tes:
        name = card["full_name"]
        age = card.get("age")
        pick = card.get("nfl_draft_pick")
        round_ = card.get("nfl_draft_round")

        # final_college_age proxy — always computable if age is present
        fca: Optional[float] = round(float(age) - 1.0, 1) if age is not None else None

        seasons = _player_seasons(name, pivot)

        te_ryptpa: Optional[float] = None
        te_ypr: Optional[float] = None
        school_raw: Optional[str] = None
        final_year: Optional[int] = None

        if seasons:
            # Career stats
            total_yds = sum(s["rec_yds"] for _, _, s in seasons)
            total_rec = sum(s.get("rec", 0.0) for _, _, s in seasons)
            if total_rec > 0:
                te_ypr = round(total_yds / total_rec, 2)

            # Final season school → RYPTPA
            final_year, final_school_key, final_stats = seasons[-1]
            school_raw = school_raw_map.get(final_school_key)
            final_rec_yds = final_stats.get("rec_yds", 0.0)

            if school_raw and final_rec_yds > 0:
                tpa = _get_tpa(school_raw, final_year, api_key, force_fetch)
                if tpa and tpa > 0:
                    te_ryptpa = round(final_rec_yds / tpa, 4)

        # Write features to card
        card["final_college_age"] = fca
        card["te_ryptpa_final"] = te_ryptpa
        card["te_yards_per_reception_career"] = te_ypr

        # Pre-score via v3 if all features present
        v3_score_dict: Optional[dict] = None
        if pick is not None and round_ is not None and fca is not None and te_ryptpa is not None and te_ypr is not None:
            v3_features = {
                "nfl_pick": float(pick),
                "nfl_round": float(round_),
                "final_college_age": fca,
                "te_ryptpa_final": te_ryptpa,
                "te_yards_per_reception_career": te_ypr,
            }
            v3_score_dict = score_prospect_v3("TE", v3_features)

        if v3_score_dict is not None:
            card["dynasty_value_score"] = v3_score_dict["dynasty_value_score"]
            n_v3 += 1
            status = "v3"
        elif te_ypr is not None:
            n_v3_partial += 1
            status = "partial (no RYPTPA)"
        else:
            n_miss += 1
            status = "no match"

        results_table.append({
            "name": name,
            "pick": pick,
            "age": age,
            "fca": fca,
            "school": school_raw or "—",
            "final_year": final_year or "—",
            "te_ryptpa": te_ryptpa,
            "te_ypr": te_ypr,
            "dvs": card.get("dynasty_value_score"),
            "status": status,
        })

    # ── Write updated cards ───────────────────────────────────────────────────
    CARDS_JSON.write_text(json.dumps(cards, indent=2, default=str), encoding="utf-8")
    print(f"Written: {CARDS_JSON}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print()
    print(f"{'Name':<25} {'Pick':>4} {'School':<20} {'Yr':>4}  {'RYPTPA':>7}  {'YPR':>6}  {'DVS':>6}  Status")
    print("-" * 95)
    for r in results_table:
        ryptpa_str = f"{r['te_ryptpa']:.4f}" if r["te_ryptpa"] is not None else "—"
        ypr_str = f"{r['te_ypr']:.2f}" if r["te_ypr"] is not None else "—"
        dvs_str = f"{r['dvs']:.1f}" if r["dvs"] is not None else "—"
        school_str = str(r["school"])[:20]
        print(
            f"{r['name']:<25} {str(r['pick'] or '—'):>4} {school_str:<20} "
            f"{str(r['final_year']):>4}  {ryptpa_str:>7}  {ypr_str:>6}  {dvs_str:>6}  {r['status']}"
        )
    print()
    print(f"v3-ready (all features): {n_v3}/{len(tes)}")
    print(f"partial (career only, no RYPTPA): {n_v3_partial}/{len(tes)}")
    print(f"no CFBD match: {n_miss}/{len(tes)}")
    print()
    print("Next step: .venv/bin/python3.14 scripts/refresh_prospect_cards.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich 2026 TE prospects with CFBD stats")
    parser.add_argument("--force-fetch", action="store_true", help="Bypass local cache.")
    args = parser.parse_args()
    main(force_fetch=args.force_fetch)
