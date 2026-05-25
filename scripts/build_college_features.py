"""Phase 16.3 College Feature Builder.

Joins PFF WR/RB export rows to Engine A training data, fetches CFBD team
pass attempts, computes RYPTPA, and extracts YPRR. Writes an enriched
training CSV and a manual_review CSV for all unresolved or partially-resolved
rows (PFF identity misses, CFBD denominator gaps, non-standard final seasons).

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

from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
    normalize_college_name,
)
from src.dynasty_genius.adapters.pff_wr_export import parse_pff_wr_season

MANIFEST_PATH = ROOT / "app/data/pff_exports/phase16_wr_manifest.json"
TRAINING_CSV = ROOT / "app/data/training/prospects_with_outcomes.csv"
OUTPUT_CSV = ROOT / "app/data/training/prospects_with_outcomes_phase16.csv"
REVIEW_CSV = ROOT / "app/data/pff_exports/phase16_wr_manual_review.csv"

# Draft classes covered by the manifest (college seasons 2017-2023).
# Coverage gate (≥80%) applies only to these in-scope years.
MANIFEST_DRAFT_YEARS: frozenset[int] = frozenset(range(2018, 2025))

_SUFFIX_PATTERN = re.compile(
    r"\b(jr\.?|sr\.?|ii|iii|iv)\s*$", re.IGNORECASE
)

# Uniform schema for all manual review entries (PFF misses and CFBD gaps).
_REVIEW_FIELDS = [
    "gsis_id", "pfr_player_name", "position", "draft_year",
    "college", "college_season", "reason",
    "pff_college_found", "cfbd_college", "found_in_season",
]


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
    """Return the PFF row matching on both normalized name AND normalized college.

    Name-only matches are NOT resolved here — they indicate a college mismatch
    that must go to manual review. Use find_pff_name_mismatch() to detect them.
    """
    norm_name = normalize_player_name(pfr_name)
    norm_college = normalize_college_name(college).lower()

    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        row_college = normalize_college_name(row.get("college", "")).lower()
        if row_name == norm_name and row_college == norm_college:
            return row

    return None


def find_pff_name_mismatch(
    pfr_name: str,
    college: str,
    pff_rows: list[dict],
) -> dict | None:
    """Return the PFF row if name matches but college differs — identity risk.

    A non-None return means a same-name player exists in the PFF data under
    a different college. This must NOT auto-resolve; route to manual review
    with reason=name_match_college_mismatch.
    """
    norm_name = normalize_player_name(pfr_name)
    norm_college = normalize_college_name(college).lower()

    for row in pff_rows:
        row_name = normalize_player_name(row.get("player_name", ""))
        row_college = normalize_college_name(row.get("college", "")).lower()
        if row_name == norm_name and row_college != norm_college:
            return row

    return None


def find_pff_match_any_season(
    pfr_name: str,
    college: str,
    pff_by_season: dict[int, list[dict]],
    *,
    exclude_season: int | None = None,
) -> tuple[int, dict] | None:
    """Search all loaded seasons for a name+college match.

    Returns (season, pff_row) if found in any season other than
    exclude_season, or None if no match exists anywhere.

    Search order: prior seasons descending (nearest first), then later
    seasons ascending. This ensures that for non-standard final-season
    detection the best candidate season is returned — e.g. Ja'Marr Chase
    (exclude_season=2020) returns 2019, not 2018.

    A non-None return with exclude_season set indicates the player played in
    a non-standard final season — route to manual review rather than
    auto-resolving.
    """
    norm_name = normalize_player_name(pfr_name)
    norm_college = normalize_college_name(college).lower()

    pivot = exclude_season if exclude_season is not None else float("inf")
    prior = sorted((s for s in pff_by_season if s < pivot), reverse=True)
    later = sorted(s for s in pff_by_season if s > pivot)

    for season in prior + later:
        for row in pff_by_season[season]:
            row_name = normalize_player_name(row.get("player_name", ""))
            row_college = normalize_college_name(row.get("college", "")).lower()
            if row_name == norm_name and row_college == norm_college:
                return (season, row)

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


def _review_entry(
    row: dict,
    *,
    college_season: int | None,
    reason: str,
    pff_college_found: str = "",
    cfbd_college: str = "",
    found_in_season: str = "",
) -> dict:
    """Build a uniform review entry across all miss/gap types."""
    return {
        "gsis_id": row.get("gsis_id", ""),
        "pfr_player_name": row.get("pfr_player_name", ""),
        "position": row.get("position", "").upper(),
        "draft_year": row.get("season", ""),
        "college": row.get("college", ""),
        "college_season": college_season if college_season is not None else "",
        "reason": reason,
        "pff_college_found": pff_college_found,
        "cfbd_college": cfbd_college,
        "found_in_season": found_in_season,
    }


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
    review: list[dict] = []  # all review entries: PFF misses + CFBD gaps

    for row in training_rows:
        position = row.get("position", "").upper()
        if position not in ("WR", "RB"):
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        draft_year = int(row.get("season", 0))
        college_season = build_college_season_year(draft_year, position)
        pfr_name = row.get("pfr_player_name", "")
        college = row.get("college", "")
        pff_rows = pff_by_season.get(college_season, [])

        pff_match = find_pff_match(pfr_name, college, pff_rows)

        if pff_match is None:
            # Check: name matches in primary season but college differs
            name_miss = find_pff_name_mismatch(pfr_name, college, pff_rows)
            if name_miss:
                review.append(_review_entry(
                    row,
                    college_season=college_season,
                    reason="name_match_college_mismatch",
                    pff_college_found=name_miss.get("college", ""),
                ))
                enriched.append({**row, **{f: "" for f in new_fields}})
                continue

            # Check: player found in a different season (non-standard final season)
            any_season_result = find_pff_match_any_season(
                pfr_name, college, pff_by_season,
                exclude_season=college_season,
            )
            if any_season_result:
                alt_season, _ = any_season_result
                review.append(_review_entry(
                    row,
                    college_season=college_season,
                    reason="non_standard_final_season_requires_review",
                    found_in_season=str(alt_season),
                ))
                enriched.append({**row, **{f: "" for f in new_fields}})
                continue

            # No match anywhere
            review.append(_review_entry(
                row,
                college_season=college_season,
                reason="no_pff_match",
            ))
            enriched.append({**row, **{f: "" for f in new_fields}})
            continue

        # PFF match found — fetch CFBD denominator
        pff_yards = pff_match.get("yards")
        team_attempts = None
        cfbd_college = normalize_college_name(pff_match.get("college", ""))

        if not dry_run and api_key:
            team_attempts = fetch_team_pass_attempts(
                pff_match.get("college", ""),
                college_season,
                api_key=api_key,
            )
            if team_attempts is None:
                review.append(_review_entry(
                    row,
                    college_season=college_season,
                    reason="missing_cfbd_pass_attempts",
                    pff_college_found=pff_match.get("college", ""),
                    cfbd_college=cfbd_college,
                ))

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
                writer = csv.DictWriter(f, fieldnames=_REVIEW_FIELDS)
                writer.writeheader()
                writer.writerows(review)
            print(f"  Manual review: {REVIEW_CSV} ({len(review)} rows)")

    # Coverage reporting — gate applies to in-scope draft years only
    wr_rb = [r for r in training_rows if r.get("position", "").upper() in ("WR", "RB")]
    in_scope = [r for r in wr_rb if int(r.get("season", 0)) in MANIFEST_DRAFT_YEARS]

    # PFF identity misses (no enrichment): all review entries except cfbd gaps
    pff_miss_reasons = {
        "no_pff_match", "name_match_college_mismatch",
        "non_standard_final_season_requires_review",
    }
    pff_misses = [e for e in review if e["reason"] in pff_miss_reasons]
    cfbd_gaps = [e for e in review if e["reason"] == "missing_cfbd_pass_attempts"]

    in_scope_misses = sum(
        1 for e in pff_misses if int(e.get("draft_year", 0)) in MANIFEST_DRAFT_YEARS
    )
    in_scope_resolved = len(in_scope) - in_scope_misses
    in_scope_pct = in_scope_resolved / len(in_scope) * 100 if in_scope else 0

    overall_resolved = len(wr_rb) - len(pff_misses)
    overall_pct = overall_resolved / len(wr_rb) * 100 if wr_rb else 0

    print(f"\n  Coverage (all WR/RB, {len(wr_rb)} rows): "
          f"{overall_resolved} resolved ({overall_pct:.1f}%) "
          f"— includes out-of-scope draft classes")
    print(f"  Coverage (in-scope draft 2018-2024, {len(in_scope)} rows): "
          f"{in_scope_resolved} resolved ({in_scope_pct:.1f}%)")
    if cfbd_gaps:
        print(f"  CFBD denominator gaps: {len(cfbd_gaps)} matched rows with "
              f"yprr_college but no ryptpa (school name normalization gaps)")

    if in_scope_pct >= 80:
        print("  [OK] In-scope coverage ≥ 80% — proceed to bake-off")
    else:
        print("  [WARN] In-scope coverage below 80% — review manual_review.csv before bake-off")

    if dry_run:
        print("\n  [DRY RUN] No files written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
