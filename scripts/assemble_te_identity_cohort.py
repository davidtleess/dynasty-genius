#!/usr/bin/env python3
"""Assemble the 2018-2025 drafted TE identity cohort and lookup fixtures.

Produces four files in --out-dir (all gitignored under _runs/):

  te_cohort_2018_2025.json       — IdentityAuditRow fixture for 116 drafted TEs
  ff_playerids_<YYYYMMDD>.json   — ff_playerids crosswalk keyed by gsis_id
  composite_registry.json        — (name, dob, pos, draft_year) → player_id  [empty first run]
  prospect_registry.json         — (name, college, pos, draft_year) → player_id [empty first run]

Denominator: nflverse load_draft_picks, position == 'TE', seasons 2018-2025.
Enrichment: nflreadpy.load_ff_playerids crosswalk (joined on gsis_id).
Sleeper supplement: /v1/players/nfl for any TEs missing sleeper_id after crosswalk join.

Usage:
  .venv/bin/python3.14 scripts/assemble_te_identity_cohort.py \\
      --out-dir app/data/identity/_runs \\
      [--skip-sleeper]   # skip Sleeper API call if already have ff_playerids coverage
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DRAFT_YEARS = list(range(2018, 2026))
COHORT_LABEL = "historical_te"


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_draft_picks_te() -> list[dict]:
    """Load drafted TEs 2018-2025 from nflverse (PFR-sourced). All have gsis_id."""
    import nflreadpy as nfl
    df = nfl.load_draft_picks(DRAFT_YEARS)
    te_df = df.filter(df["position"] == "TE")
    rows = []
    for row in te_df.iter_rows(named=True):
        rows.append({
            "name": row.get("pfr_player_name") or "",
            "draft_year": int(row["season"]),
            "draft_round": int(row["round"]) if row.get("round") else None,
            "draft_pick": int(row["pick"]) if row.get("pick") else None,
            "gsis_id": row.get("gsis_id") or None,
            "pfr_id": row.get("pfr_player_id") or None,
            "college": row.get("college") or None,
        })
    print(f"Draft picks: {len(rows)} TEs drafted 2018-2025")
    return rows


def load_ff_playerids_crosswalk() -> dict[str, dict]:
    """Load ff_playerids and index by gsis_id. Returns full crosswalk dict."""
    import nflreadpy as nfl
    df = nfl.load_ff_playerids()
    crosswalk: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        gsis = row.get("gsis_id")
        if gsis:
            crosswalk[str(gsis)] = {
                "gsis_id": str(gsis),
                "sleeper_id": str(row["sleeper_id"]) if row.get("sleeper_id") else None,
                "pff_id": str(row["pff_id"]) if row.get("pff_id") else None,
                "pfr_id": str(row["pfr_id"]) if row.get("pfr_id") else None,
                "espn_id": str(row["espn_id"]) if row.get("espn_id") else None,
                "yahoo_id": str(row["yahoo_id"]) if row.get("yahoo_id") else None,
                "sportradar_id": str(row["sportradar_id"]) if row.get("sportradar_id") else None,
                "fantasypros_id": str(row["fantasypros_id"]) if row.get("fantasypros_id") else None,
                "rotowire_id": str(row["rotowire_id"]) if row.get("rotowire_id") else None,
                "fantasy_data_id": str(row["fantasy_data_id"]) if row.get("fantasy_data_id") else None,
                "name": row.get("name") or None,
                "position": row.get("position") or None,
                "college": row.get("college") or None,
                "birthdate": row.get("birthdate") or None,
                "draft_year": int(row["draft_year"]) if row.get("draft_year") else None,
            }
    print(f"ff_playerids crosswalk: {len(crosswalk)} rows indexed by gsis_id")
    return crosswalk


def load_sleeper_players() -> dict[str, dict]:
    """Fetch Sleeper /v1/players/nfl and index by gsis_id.

    Used to supplement sleeper_id for TEs whose gsis_id is missing from ff_playerids.
    Returns dict keyed by gsis_id where not null.
    """
    import requests
    url = "https://api.sleeper.app/v1/players/nfl"
    print("Fetching Sleeper /v1/players/nfl …")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    by_gsis: dict[str, dict] = {}
    for sleeper_id, player in data.items():
        gsis = player.get("gsis_id")
        if gsis:
            by_gsis[str(gsis)] = {
                "sleeper_id": str(sleeper_id),
                "gsis_id": str(gsis),
                "full_name": player.get("full_name"),
                "position": player.get("position"),
                "college": player.get("college"),
                "birth_date": player.get("birth_date"),
                "espn_id": str(player["espn_id"]) if player.get("espn_id") else None,
                "sportradar_id": player.get("sportradar_id"),
            }
    print(f"Sleeper: {len(by_gsis)} players indexed by gsis_id")
    return by_gsis


# ---------------------------------------------------------------------------
# Cohort assembly
# ---------------------------------------------------------------------------

def assemble_cohort(
    draft_picks: list[dict],
    crosswalk: dict[str, dict],
    sleeper_by_gsis: dict[str, dict],
) -> list[dict]:
    """Build IdentityAuditRow dicts for every drafted TE."""
    entries = []
    no_crosswalk = 0
    for dp in draft_picks:
        gsis = dp.get("gsis_id")
        xwalk = crosswalk.get(gsis, {}) if gsis else {}
        sleeper = sleeper_by_gsis.get(gsis, {}) if gsis else {}

        # Prefer ff_playerids name if available (more standardized)
        name = xwalk.get("name") or sleeper.get("full_name") or dp["name"]
        college = xwalk.get("college") or sleeper.get("college") or dp.get("college")
        birthdate = xwalk.get("birthdate") or sleeper.get("birth_date")
        sleeper_id = xwalk.get("sleeper_id") or sleeper.get("sleeper_id")

        if not xwalk:
            no_crosswalk += 1

        entries.append({
            "cohort": COHORT_LABEL,
            "name": name,
            "position": "TE",
            "draft_year": dp["draft_year"],
            "college": college,
            "date_of_birth": birthdate,
            "player_id": None,
            "sleeper_id": sleeper_id,
            "gsis_id": gsis,
            "pff_id": xwalk.get("pff_id"),
            "pfr_id": dp.get("pfr_id") or xwalk.get("pfr_id"),
            "cfbref_id": None,
            "espn_id": xwalk.get("espn_id") or sleeper.get("espn_id"),
            "yahoo_id": xwalk.get("yahoo_id"),
            "sportradar_id": xwalk.get("sportradar_id") or sleeper.get("sportradar_id"),
            "fantasypros_id": xwalk.get("fantasypros_id"),
            "rotowire_id": xwalk.get("rotowire_id"),
            "fantasy_data_id": xwalk.get("fantasy_data_id"),
        })

    if no_crosswalk:
        print(f"Warning: {no_crosswalk} TEs had no ff_playerids match (Sleeper supplement applied where possible)")
    return entries


# ---------------------------------------------------------------------------
# Fixture writers
# ---------------------------------------------------------------------------

def write_cohort_fixture(entries: list[dict], path: Path, pull_timestamp: str) -> None:
    payload = {
        "metadata": {
            "description": "2018-2025 drafted TE identity cohort",
            "denominator": "nflverse load_draft_picks position==TE seasons 2018-2025",
            "pull_timestamp": pull_timestamp,
            "count": len(entries),
        },
        "entries": entries,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Written: {path} ({len(entries)} entries)")


def write_ff_playerids_fixture(crosswalk: dict[str, dict], path: Path, pull_timestamp: str) -> None:
    payload = {
        "metadata": {
            "source": "nflreadpy.load_ff_playerids",
            "pull_timestamp": pull_timestamp,
            "count": len(crosswalk),
        },
        "entries": list(crosswalk.values()),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Written: {path} ({len(crosswalk)} entries)")


def write_composite_registry(entries: list[dict], path: Path) -> None:
    """Composite name+DOB+pos+draft_year registry.

    Empty on first run — no DG canonical player_ids exist for historical TEs yet.
    Placeholder format; populate after identity gate passes and canonical IDs are assigned.
    """
    payload = {
        "metadata": {
            "description": "Composite deterministic key registry (Stage 5). Populate with canonical player_ids after identity gate passes.",
            "count": 0,
        },
        "entries": [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Written: {path} (empty — populate post-gate)")


def write_prospect_registry(entries: list[dict], path: Path) -> None:
    """Composite name+college+pos+draft_year registry.

    Empty on first run. Populate with canonical player_ids after identity gate passes.
    """
    payload = {
        "metadata": {
            "description": "Composite prospect key registry (Stage 6). Populate with canonical player_ids after identity gate passes.",
            "count": 0,
        },
        "entries": [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Written: {path} (empty — populate post-gate)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble 2018-2025 TE identity cohort fixtures.")
    parser.add_argument("--out-dir", type=Path, default=Path("app/data/identity/_runs"),
                        help="Output directory (gitignored)")
    parser.add_argument("--skip-sleeper", action="store_true",
                        help="Skip Sleeper API call (use if ff_playerids has full sleeper_id coverage)")
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pull_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = _utc_date()

    # 1. Load denominator
    draft_picks = load_draft_picks_te()

    # 2. Load crosswalk
    crosswalk = load_ff_playerids_crosswalk()

    # 3. Optionally supplement from Sleeper
    sleeper_by_gsis: dict[str, dict] = {}
    if not args.skip_sleeper:
        sleeper_by_gsis = load_sleeper_players()

    # 4. Assemble cohort
    entries = assemble_cohort(draft_picks, crosswalk, sleeper_by_gsis)

    # 5. Coverage summary before audit
    has_gsis = sum(1 for e in entries if e["gsis_id"])
    has_sleeper = sum(1 for e in entries if e["sleeper_id"])
    has_pff = sum(1 for e in entries if e["pff_id"])
    print(f"\nCohort pre-audit coverage:")
    print(f"  Total: {len(entries)}")
    print(f"  Has gsis_id:    {has_gsis} ({has_gsis/len(entries):.1%})")
    print(f"  Has sleeper_id: {has_sleeper} ({has_sleeper/len(entries):.1%})")
    print(f"  Has pff_id:     {has_pff} ({has_pff/len(entries):.1%})")

    # 6. Write fixtures
    cohort_path = args.out_dir / "te_cohort_2018_2025.json"
    ff_path = args.out_dir / f"ff_playerids_{date_str}.json"
    composite_path = args.out_dir / "composite_registry.json"
    prospect_path = args.out_dir / "prospect_registry.json"

    write_cohort_fixture(entries, cohort_path, pull_timestamp)
    write_ff_playerids_fixture(crosswalk, ff_path, pull_timestamp)
    write_composite_registry(entries, composite_path)
    write_prospect_registry(entries, prospect_path)

    print(f"\nNext step — run the identity audit:")
    print(f"  .venv/bin/python3.14 scripts/run_identity_audit.py \\")
    print(f"    --cohort {cohort_path} \\")
    print(f"    --ff-playerids {ff_path} \\")
    print(f"    --alias-bridge app/data/prospect_alias_bridge.json \\")
    print(f"    --composite-registry {composite_path} \\")
    print(f"    --prospect-registry {prospect_path} \\")
    print(f"    --out-dir {args.out_dir} \\")
    print(f"    --max-loss-rate 0.02 \\")
    print(f"    --run-id te_2018_2025_{date_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
