"""F-feature-refresh — CLI for the source-hash-gated feature refresh runner.

Thin, cwd-independent wrapper over the runner. `--preflight` is a readiness-only
check (no assemble, no write, no runtime-dir creation); the full run regenerates a
CANDIDATE only (publish/scheduler are T2/T4) via the shared feature builder, gated on
the source content hash (honest `noop` when the upstream source is unchanged).

This script derives features only — it never trains or writes model artifacts.

    .venv/bin/python3.14 scripts/run_feature_refresh.py --preflight
    .venv/bin/python3.14 scripts/run_feature_refresh.py
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

# cwd-independent: put the repo root on sys.path BEFORE importing the package, so a
# standalone/launchd invocation from outside the repo does not crash on import.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.features.feature_assembly import (  # noqa: E402
    assemble_feature_candidate,
)
from src.dynasty_genius.features.feature_refresh_runner import (  # noqa: E402
    compute_source_hash,
    run_feature_refresh,
)

_DEFAULT_RUNTIME_DIR = ROOT / "app" / "data" / "features_runtime"
_DEFAULT_SEED = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"


def _load_source(seasons_window: list[int] | None) -> dict:
    """Lazily load the full upstream source frame set (nflreadpy) for the shared builder.

    Loads every frame `build_engine_b_features` consumes so the regenerated candidate is
    fully scoreable. Participation is only available from 2019 on, so it is scoped to the
    in-window seasons >= 2019. The real invocation is David-gated (T3 catch-up run).
    """
    import nflreadpy as nfl  # lazy: keep standalone import light + optional

    def _pd(frame):
        return frame.to_pandas() if hasattr(frame, "to_pandas") else frame

    part_seasons = [s for s in (seasons_window or []) if s >= 2019]
    return {
        "player_stats": _pd(nfl.load_player_stats(seasons=seasons_window)),
        "rosters": _pd(nfl.load_rosters(seasons=seasons_window)),
        "snap_counts": _pd(nfl.load_snap_counts(seasons=seasons_window)),
        "pbp": _pd(nfl.load_pbp(seasons=seasons_window)),
        "participation": _pd(nfl.load_participation(seasons=part_seasons)),
    }


def _package_version() -> str | None:
    """nflreadpy version if resolvable (part of the C4 source hash); None otherwise."""
    try:
        from importlib.metadata import version

        return version("nflreadpy")
    except Exception:
        return None


def _builder_config() -> dict:
    """Builder constants that change the candidate -> part of the C4 source hash.

    Any change to these thresholds alters the produced candidate, so they must be in the
    source hash or an identical-frame run would falsely noop after a constant change.
    """
    from scripts.assemble_engine_b_dataset import MIN_GAMES_THRESHOLD
    from src.dynasty_genius.models.engine_b_contract import (
        DUAL_THREAT_RUSHING_THRESHOLD,
    )

    return {
        "MIN_GAMES_THRESHOLD": MIN_GAMES_THRESHOLD,
        "DUAL_THREAT_RUSHING_THRESHOLD": DUAL_THREAT_RUSHING_THRESHOLD,
    }


def _te_artifact_hashes() -> dict:
    """Content hashes of the TE rubric/eligible artifacts the builder reads from disk.

    `build_engine_b_features` falls back to reading these committed artifacts when the
    frames lack `te_rubric`/`te_eligible`, so their bytes are a genuine source input (C4):
    changing them changes the candidate and MUST change the source hash (no false noop).
    """
    from scripts.assemble_engine_b_dataset import (
        TE_ARCHETYPE_RUBRIC_PATH,
        TE_ELIGIBLE_MANIFEST_PATH,
    )

    out: dict[str, str | None] = {}
    for label, path in (
        ("te_archetype_rubric", TE_ARCHETYPE_RUBRIC_PATH),
        ("te_eligible_manifest", TE_ELIGIBLE_MANIFEST_PATH),
    ):
        p = Path(path)
        out[label] = (
            hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        )
    return out


def _source_provenance(read_fns: dict, seasons_window: list[int]) -> dict:
    """Full C4 source-hash input set the CLI feeds to `compute_source_hash`.

    Covers every input the builder consumes that can change the candidate: the loader
    frames, the seasons window, the nflreadpy package version (if resolvable), the builder
    constants, and the on-disk TE rubric/eligible artifact byte-hashes. Wall-clock is
    intentionally excluded (C5 — the runner strips `generated_at`).
    """
    return {
        "loader_outputs": read_fns,
        "seasons_window": seasons_window,
        "package_version": _package_version(),
        "builder_config": _builder_config(),
        "te_rubric_artifacts": _te_artifact_hashes(),
        "identity_inputs": None,
    }


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

    # Full run: load the source frames, hash the source content, and delegate to the
    # source-hash-gated runner. The runner writes a CANDIDATE only (no publish, no model
    # writes in T1) and noops honestly when the source hash is unchanged.
    seasons_window = list(range(args.season_start, args.season_end + 1))
    read_fns = _load_source(seasons_window)
    source_hash = compute_source_hash(**_source_provenance(read_fns, seasons_window))
    result = run_feature_refresh(
        runtime_dir=args.runtime_dir,
        seed_path=args.seed_path,
        now_fn=lambda: datetime.now(timezone.utc),
        read_fns=read_fns,
        source_inputs={"source_hash": source_hash, "seasons_window": seasons_window},
        assemble_fn=assemble_feature_candidate,
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
