"""Promoted generator for `tests/fixtures/pfr_advstats_2024_slice.json`.

Codex R9: the fixture was self-referential — it carried no generator, no source call, no version,
no selection rule, and no upstream hash, so "the fixture is real" rested on assertion alone. This
script is the missing provenance. It derives its own repository root, takes overridable arguments,
and records an upstream content hash so a reviewer can prove the committed slice came from the
source it claims.

SELECTION RULE, stated exactly (the previous prose said "two whole games per stat type", which was
FALSE for two of the four streams — see below):

  1. Take every row of the two lowest-sorted `game_id` values in the season, per stat type.
  2. IF that slice contains no row whose PFR id fails to resolve against the governed crosswalk,
     append the FIRST such row found anywhere in the season, so the unresolved-identity path is
     always exercised.
  3. Rule 2 is why `pfr_def` carries one row from a third game (`2024_01_PIT_ATL`) and `pfr_rec`
     one from `2024_02_CIN_KC`. `pfr_pass` and `pfr_rush` have no unresolved rows in 2024 at all,
     so they are exactly two games. The slice is therefore "two games, plus at most one appended
     unresolved row" — never uniformly "two whole games".

Run:
    .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-04/build_pfr_fixture_claude_v1.py
    .venv/bin/python3.14 ... --season 2024 --out tests/fixtures/pfr_advstats_2024_slice.json --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

# docs/agent-ledger/evidence/2026-08-04/<this file> -> four parents up is `docs`, five is the root.
REPO_ROOT = Path(__file__).resolve().parents[4]
if not (REPO_ROOT / "src" / "dynasty_genius").is_dir():  # fail loud, never silently import nothing
    raise SystemExit(f"repo root derivation failed: {REPO_ROOT} has no src/dynasty_genius")
sys.path.insert(0, str(REPO_ROOT / "src"))

STAT_TYPES = {"pfr_pass": "pass", "pfr_rush": "rush", "pfr_rec": "rec", "pfr_def": "def"}
DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "pfr_advstats_2024_slice.json"
DEFAULT_INJURY_OUT = REPO_ROOT / "tests" / "fixtures" / "nflverse_injuries_2024_seed.json"


def _nflreadpy_version() -> str:
    """Codex S6: the docstring claimed version provenance; nothing recorded it."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover - environment without the package
        return "unknown"


def build_injury_seed(season: int) -> tuple[list[dict], dict]:
    """A small REAL injuries slice, so the existing-table preservation gate covers all five
    live streams rather than three (Codex S2). Two teams of one week keeps it small; the era
    must match exactly, so no column is added or removed here.
    """
    import nflreadpy as nr

    frame = nr.load_injuries(seasons=[season])
    records = frame.to_dicts()
    upstream_hash = hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    week = min((r["week"] for r in records if r.get("week") is not None), default=None)
    teams = sorted({r["team"] for r in records if r.get("week") == week})[:2]
    chosen = [r for r in records if r.get("week") == week and r.get("team") in teams]

    manifest = {
        "season": season,
        "upstream_rows": len(records),
        "upstream_sha256": upstream_hash,
        "n_columns": len(records[0]) if records else 0,
        "columns": sorted(records[0]) if records else [],
        "selection_rule": f"every row of week {week} for teams {teams}",
        "slice_rows": len(chosen),
        "nflreadpy_version": _nflreadpy_version(),
    }
    return chosen, manifest


def build(season: int) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    import nflreadpy as nr

    from dynasty_genius.nflverse_usage import load_governed_identity

    identity = load_governed_identity()
    payload: dict[str, list[dict]] = {}
    manifest: dict[str, dict] = {}

    for name, stat_type in STAT_TYPES.items():
        frame = nr.load_pfr_advstats(seasons=[season], stat_type=stat_type)
        records = frame.to_dicts()
        upstream_hash = hashlib.sha256(
            json.dumps(records, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        games = sorted({r["game_id"] for r in records})[:2]
        chosen = [r for r in records if r["game_id"] in games]

        def unresolved(row) -> bool:
            return identity.resolve(row["pfr_player_id"], kind="pfr")[1] != "canonical_resolved"

        appended = None
        if not any(unresolved(r) for r in chosen):
            extra = next((r for r in records if unresolved(r)), None)
            if extra is not None:
                chosen.append(extra)
                appended = extra["game_id"]

        payload[name] = chosen
        manifest[name] = {
            "stat_type": stat_type,
            "season": season,
            "upstream_rows": len(records),
            "upstream_sha256": upstream_hash,
            "columns": sorted(records[0]) if records else [],
            "n_columns": len(records[0]) if records else 0,
            "base_games": games,
            "appended_unresolved_row_from_game": appended,
            "slice_rows": len(chosen),
            "slice_games": dict(Counter(r["game_id"] for r in chosen)),
            "identity_census": dict(
                Counter(
                    identity.resolve(r["pfr_player_id"], kind="pfr")[1] for r in chosen
                )
            ),
            "nflreadpy_version": _nflreadpy_version(),
        }

    return payload, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--injury-out", type=Path, default=DEFAULT_INJURY_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; fail if the committed fixture differs from a fresh build.",
    )
    args = parser.parse_args()

    payload, manifest = build(args.season)
    rendered = json.dumps(payload, indent=1, sort_keys=True, default=str)
    rendered_manifest = json.dumps(manifest, indent=2, sort_keys=True)

    injury_rows, injury_manifest = build_injury_seed(args.season)
    rendered_injury = json.dumps(injury_rows, indent=1, sort_keys=True, default=str)
    rendered_injury_manifest = json.dumps(injury_manifest, indent=2, sort_keys=True)

    manifest_path = args.out.with_name(args.out.stem + "_manifest.json")
    injury_manifest_path = args.injury_out.with_name(args.injury_out.stem + "_manifest.json")

    if args.check:
        # Codex S6: --check previously compared ONLY the fixture payload, so a stale or
        # fabricated manifest — wrong upstream hash, wrong selection metadata, wrong census —
        # still printed "FIXTURE MATCHES SOURCE". The manifest is provenance; unchecked
        # provenance is decoration.
        targets = [
            (args.out, rendered, "fixture"),
            (manifest_path, rendered_manifest, "fixture manifest"),
            (args.injury_out, rendered_injury, "injury seed"),
            (injury_manifest_path, rendered_injury_manifest, "injury seed manifest"),
        ]
        failures: list[str] = []
        for path, expected, label in targets:
            if not path.exists():
                failures.append(f"MISSING {label}: {path}")
            elif path.read_text(encoding="utf-8") != expected:
                failures.append(f"DIVERGES {label}: {path}")
        for line in failures:
            print(line)
        print("ALL ARTIFACTS MATCH SOURCE" if not failures else "CHECK FAILED")
        return 0 if not failures else 1

    args.out.write_text(rendered, encoding="utf-8")
    manifest_path.write_text(rendered_manifest, encoding="utf-8")
    args.injury_out.write_text(rendered_injury, encoding="utf-8")
    injury_manifest_path.write_text(rendered_injury_manifest, encoding="utf-8")
    print(rendered_manifest)
    print(rendered_injury_manifest)
    for path in (args.out, manifest_path, args.injury_out, injury_manifest_path):
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
