"""Promoted generator for `tests/fixtures/ff_opportunity_2024_slice.json` (batch stream 2).

Same provenance discipline as the PFR generator (Codex R9/S6): derives its own repository root,
records upstream row count + sha256 + nflreadpy version, states its selection rule, and offers
`--check` that compares BOTH the fixture and its manifest against a fresh build.

SELECTION RULE:
  1. Every row of the two lowest-sorted `game_id` values in the season — this deliberately keeps
     BOTH row classes, because the residual rows are one per (game_id, posteam) and excluding
     them from the fixture would leave the exclusion/reconciliation path untested.
  2. IF the slice contains no player row whose GSIS id fails to resolve against the governed
     crosswalk, append the first such row found in the season, so the source_only path is
     exercised.

Run:
    .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-04/build_ff_opportunity_fixture_claude_v1.py
    .venv/bin/python3.14 ... --check
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

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "ff_opportunity_2024_slice.json"


def _nflreadpy_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


def build(season: int) -> tuple[list[dict], dict]:
    import nflreadpy as nr

    from dynasty_genius.nflverse_usage import load_governed_identity

    identity = load_governed_identity()
    frame = nr.load_ff_opportunity(seasons=[season])
    records = frame.to_dicts()
    upstream_hash = hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    games = sorted({r["game_id"] for r in records if r.get("game_id")})[:2]
    chosen = [r for r in records if r.get("game_id") in games]

    def is_player(row) -> bool:
        return bool(str(row.get("player_id") or "").strip())

    def unresolved(row) -> bool:
        return (
            is_player(row)
            and identity.resolve(row["player_id"], kind="gsis")[1] != "canonical_resolved"
        )

    appended = None
    if not any(unresolved(r) for r in chosen):
        extra = next((r for r in records if unresolved(r)), None)
        if extra is not None:
            chosen.append(extra)
            appended = extra["game_id"]

    players = [r for r in chosen if is_player(r)]
    residual = [r for r in chosen if not is_player(r)]

    manifest = {
        "season": season,
        "upstream_rows": len(records),
        "upstream_sha256": upstream_hash,
        "n_columns": len(records[0]) if records else 0,
        "base_games": games,
        "appended_unresolved_row_from_game": appended,
        "slice_rows": len(chosen),
        "player_rows": len(players),
        "residual_rows": len(residual),
        "residual_is_one_per_game_posteam": len(
            {(r["game_id"], r["posteam"]) for r in residual}
        )
        == len(residual),
        "identity_census_player_rows": dict(
            Counter(identity.resolve(r["player_id"], kind="gsis")[1] for r in players)
        ),
        "nflreadpy_version": _nflreadpy_version(),
    }
    return chosen, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rows, manifest = build(args.season)
    rendered = json.dumps(rows, indent=1, sort_keys=True, default=str)
    rendered_manifest = json.dumps(manifest, indent=2, sort_keys=True)
    manifest_path = args.out.with_name(args.out.stem + "_manifest.json")

    if args.check:
        failures = []
        for path, expected, label in (
            (args.out, rendered, "fixture"),
            (manifest_path, rendered_manifest, "manifest"),
        ):
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
    print(rendered_manifest)
    for path in (args.out, manifest_path):
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
