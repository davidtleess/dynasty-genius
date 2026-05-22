"""Refresh the Phase 17 league-intelligence artifact chain."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PhaseStep:
    phase: str
    label: str
    script: str


PHASE_STEPS: tuple[PhaseStep, ...] = (
    PhaseStep("17.1", "Sleeper universe snapshot", "scripts/build_sleeper_universe_snapshot.py"),
    PhaseStep("17.2", "Full-universe PVO batch", "scripts/build_universe_pvo_batch.py"),
    PhaseStep("17.3", "Team value matrix", "scripts/build_team_value_matrix.py"),
    PhaseStep("17.4", "Market divergence overlay", "scripts/build_universe_market_divergence.py"),
    PhaseStep("17.5", "League opportunity map", "scripts/build_league_opportunity_map.py"),
)

Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _command_for(step: PhaseStep, python_executable: str) -> list[str]:
    return [python_executable, step.script]


def run_refresh(
    *,
    dry_run: bool = False,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    """Run the shipped Phase 17 builders in dependency order."""

    started_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for step in PHASE_STEPS:
        command = _command_for(step, python_executable)
        step_result = {
            "phase": step.phase,
            "label": step.label,
            "script": step.script,
            "command": command,
        }
        if dry_run:
            results.append({**step_result, "status": "planned"})
            continue

        print(f"[{step.phase}] {step.label}: running {step.script}")
        try:
            runner(command, cwd=ROOT, check=True)
        except subprocess.CalledProcessError as exc:
            results.append({**step_result, "status": "failed", "returncode": exc.returncode})
            print(f"[{step.phase}] {step.label}: failed with exit code {exc.returncode}", file=sys.stderr)
            raise SystemExit(exc.returncode) from exc
        results.append({**step_result, "status": "passed"})
        print(f"[{step.phase}] {step.label}: complete")

    status = "dry_run" if dry_run else "complete"
    return {
        "schema_version": "league_intelligence_refresh.v1",
        "status": status,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "steps": results,
        "decision_supported": False,
        "market_data_overlay_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Phase 17 league-intelligence artifacts in order.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps without executing builders.")
    args = parser.parse_args()

    result = run_refresh(dry_run=args.dry_run)
    for step in result["steps"]:
        if args.dry_run:
            print(f"[{step['phase']}] {step['label']}: planned {' '.join(step['command'])}")
    print(f"League intelligence refresh status: {result['status']}")


if __name__ == "__main__":
    main()
