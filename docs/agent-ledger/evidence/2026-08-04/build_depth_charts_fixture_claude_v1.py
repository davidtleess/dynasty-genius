"""Promoted generator for the depth-charts fixtures (batch stream 4).

Writes TWO slices, because this stream has two eras with different shapes AND different grains.
A single-era fixture would leave half the contract untested.

  tests/fixtures/depth_charts_weekly_2024_slice.json  — 15-column weekly era
  tests/fixtures/depth_charts_daily_2025_slice.json   — 12-column daily era

SELECTION RULE
  weekly: every row of the two lowest-sorted `club_code` values in the season, PLUS — if the
          slice contains no exact duplicate pair and no SBBYE row — the first of each found in
          the season, so the collapse and null-week paths are always exercised.
  daily:  every row of the single lowest-sorted `dt` (one daily snapshot) for the two
          lowest-sorted teams.

Same provenance discipline as streams 1-3: own repo-root derivation with a fail-loud check,
upstream rows + sha256 + nflreadpy version, and `--check` over fixtures AND manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if not (REPO_ROOT / "src" / "dynasty_genius").is_dir():
    raise SystemExit(f"repo root derivation failed: {REPO_ROOT} has no src/dynasty_genius")
sys.path.insert(0, str(REPO_ROOT / "src"))

FIXTURES = REPO_ROOT / "tests" / "fixtures"
WEEKLY_OUT = FIXTURES / "depth_charts_weekly_2024_slice.json"
DAILY_OUT = FIXTURES / "depth_charts_daily_2025_slice.json"


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


def _hash(records) -> str:
    return hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def build_weekly(season: int):
    import nflreadpy as nr

    records = nr.load_depth_charts(seasons=[season]).to_dicts()
    clubs = sorted({r["club_code"] for r in records})[:2]
    chosen = [r for r in records if r["club_code"] in clubs]

    def fingerprint(row):
        return tuple(sorted((k, repr(v)) for k, v in row.items()))

    counts = Counter(fingerprint(r) for r in chosen)
    appended = []
    if not any(c > 1 for c in counts.values()):
        all_counts = Counter(fingerprint(r) for r in records)
        dup_fp = next((fp for fp, c in all_counts.items() if c > 1), None)
        if dup_fp is not None:
            row = next(r for r in records if fingerprint(r) == dup_fp)
            chosen.extend([row, dict(row)])
            appended.append("exact_duplicate_pair")
    if not any(r.get("week") is None for r in chosen):
        sb = next((r for r in records if r.get("week") is None), None)
        if sb is not None:
            chosen.append(sb)
            appended.append("sbbye_null_week")

    counts = Counter(fingerprint(r) for r in chosen)
    manifest = {
        "era": "weekly",
        "season": season,
        "upstream_rows": len(records),
        "upstream_sha256": _hash(records),
        "n_columns": len(records[0]),
        "base_clubs": clubs,
        "appended_to_exercise": appended,
        "slice_rows": len(chosen),
        "exact_duplicate_rows": sum(c - 1 for c in counts.values() if c > 1),
        "null_week_rows": sum(1 for r in chosen if r.get("week") is None),
        "game_types": dict(Counter(str(r.get("game_type")) for r in chosen)),
        "nflreadpy_version": _version(),
    }
    return chosen, manifest


def build_daily(season: int):
    import nflreadpy as nr

    records = nr.load_depth_charts(seasons=[season]).to_dicts()
    day = sorted({r["dt"] for r in records})[0]
    teams = sorted({r["team"] for r in records})[:2]
    chosen = [r for r in records if r["dt"] == day and r["team"] in teams]
    manifest = {
        "era": "daily",
        "season": season,
        "upstream_rows": len(records),
        "upstream_sha256": _hash(records),
        "n_columns": len(records[0]),
        "snapshot_dt": str(day),
        "teams": teams,
        "slice_rows": len(chosen),
        "null_gsis_rows": sum(1 for r in chosen if not r.get("gsis_id")),
        "grain_is_unique": len(
            {
                (r["dt"], r["team"], r["espn_id"], r["pos_grp"], r["pos_slot"], r["pos_rank"])
                for r in chosen
            }
        )
        == len(chosen),
        "nflreadpy_version": _version(),
    }
    return chosen, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-season", type=int, default=2024)
    ap.add_argument("--daily-season", type=int, default=2025)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    targets = []
    for rows, manifest, out in (
        (*build_weekly(args.weekly_season), WEEKLY_OUT),
        (*build_daily(args.daily_season), DAILY_OUT),
    ):
        targets.append((out, json.dumps(rows, indent=1, sort_keys=True, default=str), "fixture"))
        targets.append(
            (
                out.with_name(out.stem + "_manifest.json"),
                json.dumps(manifest, indent=2, sort_keys=True),
                "manifest",
            )
        )

    if args.check:
        failures = [
            f"{'MISSING' if not p.exists() else 'DIVERGES'} {label}: {p}"
            for p, expected, label in targets
            if not p.exists() or p.read_text(encoding="utf-8") != expected
        ]
        for line in failures:
            print(line)
        print("ALL ARTIFACTS MATCH SOURCE" if not failures else "CHECK FAILED")
        return 0 if not failures else 1

    for path, content, _ in targets:
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
