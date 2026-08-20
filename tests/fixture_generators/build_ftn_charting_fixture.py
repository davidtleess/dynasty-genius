"""Promoted generator for `tests/fixtures/ftn_charting_2024_slice.json` (batch stream 3).

Same provenance discipline as the stream 1 and 2 generators (Codex R9/S6): own repo-root
derivation with a fail-loud check, upstream row count + sha256 + nflreadpy version recorded,
selection rule stated, and a `--check` mode comparing fixture AND manifest to a fresh build.

SELECTION RULE: every charted play of the two lowest-sorted `nflverse_game_id` values in the
season. No appended row — this stream has NO player identity, so there is no unresolved-identity
path to force. That absence is the stream's defining property, not an oversight.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not (REPO_ROOT / "src" / "dynasty_genius").is_dir():
    raise SystemExit(f"repo root derivation failed: {REPO_ROOT} has no src/dynasty_genius")
sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_OUT = REPO_ROOT / "tests" / "fixtures" / "ftn_charting_2024_slice.json"


def _nflreadpy_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("nflreadpy")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


def build(season: int) -> tuple[list[dict], dict]:
    import nflreadpy as nr

    frame = nr.load_ftn_charting(seasons=[season])
    records = frame.to_dicts()
    upstream_hash = hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    games = sorted({r["nflverse_game_id"] for r in records if r.get("nflverse_game_id")})[:2]
    chosen = [r for r in records if r.get("nflverse_game_id") in games]

    bool_cols = [c for c in (records[0] if records else {}) if c.startswith("is_")]
    manifest = {
        "season": season,
        "upstream_rows": len(records),
        "upstream_sha256": upstream_hash,
        "n_columns": len(records[0]) if records else 0,
        "base_games": games,
        "slice_rows": len(chosen),
        "grain_is_unique": len(
            {(r["nflverse_game_id"], r["nflverse_play_id"]) for r in chosen}
        )
        == len(chosen),
        # Named for what it asserts. An earlier draft called this `has_any_player_column`
        # while computing `not any(...)` — the value was right and the name said the opposite,
        # which in a provenance manifest is a reviewer trap.
        "has_no_player_column": not any(
            k in (records[0] if records else {})
            for k in ("gsis_id", "player_id", "pfr_player_id", "player", "player_name")
        ),
        "boolean_column_count": len(bool_cols),
        "boolean_null_counts": {
            c: sum(1 for r in chosen if r.get(c) is None)
            for c in bool_cols
            if any(r.get(c) is None for r in chosen)
        },
        "value_counts_is_motion": dict(
            Counter(str(r.get("is_motion")) for r in chosen)
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
