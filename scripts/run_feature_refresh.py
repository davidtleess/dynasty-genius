"""F-feature-refresh — CLI for the source-hash-gated feature refresh runner (T1).

Thin, cwd-independent wrapper over the runner. T1 scope: `--preflight` is a
readiness-only check (no assemble, no write, no runtime-dir creation), and the
full run regenerates a CANDIDATE only (publish/scheduler are T2/T4).

This script derives features only — it never trains or writes model artifacts.

    .venv/bin/python3.14 scripts/run_feature_refresh.py --preflight
    .venv/bin/python3.14 scripts/run_feature_refresh.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# cwd-independent: put the repo root on sys.path BEFORE importing the package, so a
# standalone/launchd invocation from outside the repo does not crash on import.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DEFAULT_RUNTIME_DIR = ROOT / "app" / "data" / "features_runtime"
_DEFAULT_SEED = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"


def _load_source(seasons_window: list[int] | None) -> dict:
    """Lazily load the upstream source frames (nflreadpy). Validated at the T3 run."""
    import nflreadpy as nfl  # lazy: keep standalone import light + optional

    def _pd(frame):
        return frame.to_pandas() if hasattr(frame, "to_pandas") else frame

    stats = _pd(nfl.load_player_stats(seasons=seasons_window))
    rosters = _pd(nfl.load_rosters(seasons=seasons_window))
    return {"player_stats": stats, "rosters": rosters}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate the engine_b feature candidate (source-hash-gated)."
    )
    parser.add_argument("--runtime-dir", default=str(_DEFAULT_RUNTIME_DIR))
    parser.add_argument("--seed-path", default=str(_DEFAULT_SEED))
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="readiness-only check; never assembles, writes, or creates the runtime dir",
    )
    parser.add_argument("--season-start", type=int, default=2018)
    parser.add_argument("--season-end", type=int, default=datetime.now(timezone.utc).year)
    args = parser.parse_args(argv)

    if args.preflight:
        ready = bool(args.seed_path) and Path(args.seed_path).exists()
        print(f"preflight ready={ready} seed_path={args.seed_path}")
        return 0 if ready else 1

    # T1 GATE: the real run would produce only a schema-conformant SEAM (feature values
    # null until the full engineering lands in T1b). To avoid publishing a misleading
    # not-yet-scoreable artifact, the real run is gated BEFORE any source loading. T1b
    # removes this gate and wires `_load_source` → the full feature engineering.
    print("full feature engineering lands in T1b; real run gated until then")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
