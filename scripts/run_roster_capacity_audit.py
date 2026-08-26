"""Read-only roster capacity audit producer — T4 CLI entrypoint.

Scheduler-safe wrapper over the pure T1-T3 simulator
(`simulate_capacity_scenarios`). Reads injected PVO/snapshot artifacts, writes
ONLY the gitignored latest scorecard artifact on success, NEVER invokes git, and
keeps producer metadata (`created_at`, `sleeper_snapshot_captured_at`) OUT of the
deterministic core model — the producer enriches the written artifact at write
time, not the model.

The producer emits its own `ProducerReport` (producer_status ok/blocked/
preflight_ready), distinct from the core `CapacityAuditResult.status`, so a
preflight run (which never scores) is representable. A blocked run writes no
artifact and does not overwrite a prior good `_latest`.

No API route, no scheduler plist in v1 (David-gated).

Plan: docs/superpowers/plans/2026-06-28-roster-capacity-simulator-v1.md (T4)
"""
from __future__ import annotations

import argparse
import json
import os

# Imported so the never-calls-git guard seam exists (tests patch
# `subprocess.run` to forbid it); the producer itself never shells out.
import subprocess  # noqa: F401
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Standalone-run path bootstrap: when launchd/cron runs this file directly the
# repo root is not on sys.path, so the first-party `src` import would crash at
# runtime. Resolve the repo root from this file's location (cwd-independent).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.league_capture import load_league_set_for_root  # noqa: E402
from src.dynasty_genius.pvo_source import resolve_pvo_source  # noqa: E402
from src.dynasty_genius.roster_capacity.models import ProducerReport  # noqa: E402
from src.dynasty_genius.roster_capacity.scenario_simulator import (  # noqa: E402
    simulate_capacity_scenarios,
)

SNAPSHOT_PATH = load_league_set_for_root(ROOT).paths["snapshot.json"]
PVO_SEED_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
PVO_SEED_COVERAGE_PATH = (
    ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)
PVO_RUNTIME_DIR = ROOT / "app" / "data" / "valuation_runtime"
DEFAULT_REPORT_PATH = (
    ROOT / "app" / "data" / "roster_capacity" / "roster_capacity_latest.json"
)
DEFAULT_STATUS_MARKER_PATH = (
    ROOT / "app" / "data" / "ops" / "roster_capacity_audit_status_latest.json"
)


def _now() -> str:
    """Wall-clock generation time (producer metadata; injectable seam)."""
    return datetime.now(timezone.utc).isoformat()


def _load_universe_pvo() -> dict[str, Any]:
    """Resolve the live PVO pair (verified runtime else committed seed)."""
    resolved = resolve_pvo_source(
        seed_paths={"pvo": PVO_SEED_PATH, "coverage": PVO_SEED_COVERAGE_PATH},
        runtime_dir=PVO_RUNTIME_DIR,
    )
    return json.loads(Path(resolved.pvo_path).read_text())


def _load_sleeper_snapshot() -> dict[str, Any]:
    return json.loads(SNAPSHOT_PATH.read_text())


def _write_status_marker(
    status_marker_path: Path | None,
    *,
    producer_status: str,
    finished_at: str,
    artifact_written: bool,
) -> None:
    """DG-039: the always-written attestation. The artifact keeps its
    preserve-last-good guarantee; THIS file is where a refused run becomes
    legible. Atomic so a reader never sees a half-written status."""
    if status_marker_path is None:
        return
    status_marker_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = status_marker_path.with_suffix(status_marker_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {
                "producer_status": producer_status,
                "finished_at": finished_at,
                "artifact_written": artifact_written,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, status_marker_path)


def run_audit(
    *,
    report_path: Path,
    universe_pvo_loader: Callable[[], dict[str, Any]],
    sleeper_snapshot_loader: Callable[[], dict[str, Any]],
    now_fn: Callable[[], str],
    status_marker_path: Path | None = None,
) -> dict[str, Any]:
    """Run one audit and, on success only, write the enriched artifact.

    Returns the `ProducerReport` as a dict. Fail-closed: missing/corrupt input
    yields a blocked report and writes no artifact (a prior good `_latest` is
    left untouched). The status marker (DG-039) is written on EVERY exit path,
    so a refused run is legible without the artifact losing preserve-last-good.
    """
    report_path = Path(report_path)

    try:
        universe_pvo = universe_pvo_loader()
        sleeper_snapshot = sleeper_snapshot_loader()
        result = simulate_capacity_scenarios(universe_pvo, sleeper_snapshot)
    except (OSError, ValueError, TypeError, KeyError):
        # Missing/unreadable/malformed input — fail closed with no scorecard and
        # no artifact. Distinct from a blocked CapacityAuditResult (corrupt
        # CONTENT), which still carries a scorecard below.
        _write_status_marker(
            status_marker_path,
            producer_status="blocked",
            finished_at=now_fn(),
            artifact_written=False,
        )
        return ProducerReport(producer_status="blocked", scorecard=None).model_dump()

    if result.status != "ok":
        _write_status_marker(
            status_marker_path,
            producer_status="blocked",
            finished_at=now_fn(),
            artifact_written=False,
        )
        return ProducerReport(
            producer_status="blocked", scorecard=result
        ).model_dump()

    snapshot_captured_at = (
        sleeper_snapshot.get("captured_at")
        if isinstance(sleeper_snapshot, dict)
        else None
    )
    artifact = {
        **result.model_dump(),
        "created_at": now_fn(),
        "sleeper_snapshot_captured_at": snapshot_captured_at,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")

    _write_status_marker(
        status_marker_path,
        producer_status="ok",
        finished_at=now_fn(),
        artifact_written=True,
    )
    return ProducerReport(producer_status="ok", scorecard=result).model_dump()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only roster capacity audit producer (PIT, descriptive)."
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Path for the gitignored scorecard artifact (JSON).",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Print a readiness report and exit; performs no load, score, or write.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.preflight:
        report = ProducerReport(producer_status="preflight_ready", scorecard=None)
        print(json.dumps(report.model_dump()))
        return 0

    report = run_audit(
        report_path=Path(args.report_path),
        universe_pvo_loader=_load_universe_pvo,
        sleeper_snapshot_loader=_load_sleeper_snapshot,
        now_fn=_now,
        status_marker_path=DEFAULT_STATUS_MARKER_PATH,
    )
    print(json.dumps(report))
    return 0 if report["producer_status"] in ("ok", "preflight_ready") else 1


if __name__ == "__main__":
    sys.exit(main())
