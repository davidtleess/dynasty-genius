"""Daily league snapshot capture entrypoint (F1 spec of record).

Thin re-export + CLI wrapper over ``src.dynasty_genius.league_capture``. The
contract (immutable per-run capture, marker-written-last, digest-verified
loading, seed fallback, identity floor) lives in the src module; this script is
the importable/schedulable surface the spec names.

The scheduled real run and any LaunchAgent install are David-gated (spec §5) —
this module intentionally ships with no side effects at import time and no
default invocation wiring beyond ``main()``.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.dynasty_genius.league_capture import (  # noqa: E402, F401 — re-exported contract
    ARTIFACTS,
    DEFAULT_CONFIG_PATH,
    SEED_FALLBACK_CAVEAT,
    TRACKED_SEED_PATHS,
    CaptureError,
    LeagueSet,
    assert_no_legacy_direct_readers,
    load_league_set,
    run_capture,
)

DEFAULT_RUNTIME_ROOT = _ROOT / "app" / "data" / "league_runtime"


def _production_fetch() -> dict:
    """Live Sleeper capture via the existing builder orchestration (Phase 17.1)."""
    import asyncio

    from scripts.build_sleeper_universe_snapshot import build_snapshot

    return asyncio.run(build_snapshot())


def _production_derive(snapshot: dict) -> dict:
    """The league derivation chain against the CURRENT PVO (never regenerated here).

    PVO has its own daily producer; this chain joins fresh league state onto it.
    """
    import json
    from datetime import datetime, timezone

    from src.dynasty_genius.pvo_source import resolve_pvo_source
    from src.dynasty_genius.roster_cut_engine import compute_roster_cut_candidates
    from src.dynasty_genius.sleeper_universe import build_coverage_report
    from src.dynasty_genius.team_posture import build_team_posture_artifact
    from src.dynasty_genius.team_value_matrix import build_team_value_matrix

    resolved = resolve_pvo_source(
        seed_paths={
            "pvo": _ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json",
            "coverage": _ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json",
        },
        runtime_dir=_ROOT / "app" / "data" / "valuation_runtime",
    )
    pvo = json.loads(Path(resolved.pvo_path).read_text(encoding="utf-8"))
    david_roster_id = int(snapshot.get("david_roster_id") or 1)

    coverage = build_coverage_report(snapshot)
    matrix = build_team_value_matrix(universe_pvo=pvo, league_snapshot=snapshot)
    posture = build_team_posture_artifact(matrix)
    cut = compute_roster_cut_candidates(pvo, snapshot, david_roster_id=david_roster_id)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "coverage.json": coverage,
        "team_posture.json": posture,
        "team_value_matrix.json": matrix,
        "roster_cut_report.json": {
            "captured_at": now,
            "decision_supported": False,
            "roster_cut_report": json.loads(cut.model_dump_json()),
        },
        "provenance.json": {
            "decision_supported": False,
            "sleeper_snapshot_captured_at": snapshot.get("captured_at"),
            "pvo_source_path": str(resolved.pvo_path),
            "derived_at": now,
        },
    }


def main() -> int:
    """Daily producer. Scheduling/real runs are David-gated (spec §5) — running
    this by hand IS the supervised real run and needs that word first."""
    import argparse
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(description="F1 daily league snapshot capture")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("league-%Y%m%dT%H%M%SZ"),
    )
    args = parser.parse_args()
    try:
        result = run_capture(
            fetch_league_state=_production_fetch,
            derive_chain=_production_derive,
            runtime_root=args.runtime_root,
            clock=lambda: datetime.now(timezone.utc),
            run_id=args.run_id,
        )
    except Exception as exc:  # named status marker already written by run_capture
        print(f"league capture FAILED: {exc}")
        return 1
    print(f"league capture ok: run {sorted(set(result.run_ids.values()))[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
