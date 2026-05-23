"""Phase 16.3 College Feature Builder.

Joins PFF WR/RB export rows to Engine A training data, fetches CFBD team
pass attempts, computes RYPTPA, and extracts YPRR. Writes an enriched
training CSV and a manual_review CSV for unresolved rows.

Usage:
    .venv/bin/python3.14 scripts/build_college_features.py
    .venv/bin/python3.14 scripts/build_college_features.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.pff_wr_export import parse_pff_wr_season
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
    normalize_college_name,
)

MANIFEST_PATH = ROOT / "app/data/pff_exports/phase16_wr_manifest.json"
TRAINING_CSV = ROOT / "app/data/training/prospects_with_outcomes.csv"
OUTPUT_CSV = ROOT / "app/data/training/prospects_with_outcomes_phase16.csv"
REVIEW_CSV = ROOT / "app/data/pff_exports/phase16_wr_manual_review.csv"

_SUFFIX_PATTERN = re.compile(
    r"\b(jr\.?|sr\.?|ii|iii|iv)\s*$", re.IGNORECASE
)


def normalize_player_name(name: str) -> str:
    """Lowercase, strip accents, remove punctuation and name suffixes."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(ch for ch in name if unicodedata.category(ch) != "Mn")
    name = name.lower()
    name = _SUFFIX_PATTERN.sub("", name).strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def compute_ryptpa(
    receiving_yards: float | None,
    team_pass_attempts: float | None,
) -> float | None:
    """RYPTPA = receiving yards / team pass attempts."""
    if receiving_yards is None or team_pass_attempts is None:
        return None
    if team_pass_attempts <= 0:
        return None
    return receiving_yards / team_pass_attempts


def find_pff_match(
    pfr_name: str,
    college: str,
    pff_rows: list[dict],
) -> dict | None:
    """Find the best matching PFF row by normalized name + college."""
    norm_name = normalize_player_name(pfr_name)
    norm_college = normalize_college_name(college).lower()

    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        row_college = normalize_college_name(row.get("college", "")).lower()
        if row_name == norm_name and row_college == norm_college:
            return row

    # Relaxed: name match only (college name may differ slightly)
    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        if row_name == norm_name:
            return row

    return None


def build_college_season_year(
    draft_year: int,
    position: str,
    opt_out: bool = False,
) -> int | None:
    """College season year for the default (non-opt-out) case.

    Returns draft_year - 1 for standard entries. Returns None for opt-outs
    or other non-standard final-season cases — the feature builder treats
    None as a fallback signal to check adjacent season files.

    These files are full season snapshots, not draft-class-filtered exports.
    A player appears in whichever season(s) they actually played. The caller
    is responsible for resolving the correct file per player.
    """
    if opt_out:
        return None
    return draft_year - 1


def _load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Phase 16 WR manifest not found: {MANIFEST_PATH}\n"
            "Create app/data/pff_exports/phase16_wr_manifest.json first."
        )
    data = json.loads(MANIFEST_PATH.read_text())
    return data["exports"]


def _parse_all_seasons(manifest_entries: list[dict]) -> dict[int, list[dict]]:
    """Return {season_year: [pff_rows]} for all manifest entries."""
    seasons: dict[int, list[dict]] = {}
    seen_hashes: set[str] = set()
    for entry in manifest_entries:
        path = entry["path"]
        season = entry["season"]
        result = parse_pff_wr_season(path, season=season)
        if result.content_hash in seen_hashes:
            print(f"  [WARN] Duplicate content hash for season {season} — skipping")
            continue
        seen_hashes.add(result.content_hash)
        seasons[season] = result.rows
        print(f"  Loaded season {season}: {len(result.rows)} WR/RB rows")
    return seasons


def main(dry_run: bool = False) -> None:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("CFBD_API_KEY", "")

    print("Phase 16.3 College Feature Builder")
    print(f"  Training CSV: {TRAINING_CSV}")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  CFBD key present: {bool(api_key)}")

    manifest_entries = _load_manifest()
    pff_by_season = _parse_all_seasons(manifest_entries)

    with TRAINING_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        training_rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    new_fields = ["ryptpa", "source_ryptpa", "yprr_college", "source_yprr_college"]
    output_fields = fieldnames + [f for f in new_fields if f not in fieldnames]

    enriched: list[dict] = []
    review: list[dict] = []

    for row in training_rows:
        position = row.get("position", "").upper()
        if position not in ("WR", "RB"):
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        draft_year = int(row.get("season", 0))
        college_season = build_college_season_year(draft_year, position)
        pff_rows = pff_by_season.get(college_season, [])

        pff_match = find_pff_match(
            row.get("pfr_player_name", ""),
            row.get("college", ""),
            pff_rows,
        )

        if pff_match is None:
            review.append({
                "gsis_id": row.get("gsis_id"),
                "pfr_player_name": row.get("pfr_player_name"),
                "position": position,
                "draft_year": draft_year,
                "college": row.get("college"),
                "college_season": college_season,
                "reason": "no_pff_match",
            })
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        pff_yards = pff_match.get("yards")
        team_attempts = None
        if not dry_run and api_key:
            team_attempts = fetch_team_pass_attempts(
                pff_match.get("college", ""),
                college_season,
                api_key=api_key,
            )

        ryptpa = compute_ryptpa(pff_yards, team_attempts)
        yprr_col = pff_match.get("yprr")

        enriched.append({
            **row,
            "ryptpa": f"{ryptpa:.4f}" if ryptpa is not None else "",
            "source_ryptpa": "pff_yards_cfbd_attempts" if ryptpa is not None else "",
            "yprr_college": f"{yprr_col:.4f}" if yprr_col is not None else "",
            "source_yprr_college": "pff_premium_stats" if yprr_col is not None else "",
        })

    if not dry_run:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(enriched)
        print(f"\n  Written: {OUTPUT_CSV}")

        if review:
            with REVIEW_CSV.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(review[0].keys()))
                writer.writeheader()
                writer.writerows(review)
            print(f"  Manual review: {REVIEW_CSV} ({len(review)} rows)")

    wr_rb = [r for r in training_rows if r.get("position", "").upper() in ("WR", "RB")]
    resolved = len(wr_rb) - len(review)
    pct = resolved / len(wr_rb) * 100 if wr_rb else 0
    print(f"\n  Coverage: {resolved}/{len(wr_rb)} WR/RB rows resolved ({pct:.1f}%)")
    if pct < 80:
        print("  [WARN] Coverage below 80% — review manual_review.csv before bake-off")
    else:
        print("  [OK] Coverage ≥ 80% — proceed to bake-off")

    if dry_run:
        print("\n  [DRY RUN] No files written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
