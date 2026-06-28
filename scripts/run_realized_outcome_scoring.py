"""Realized-Outcome Loop T5 — scorecard CLI producer (+ weekly LaunchAgent).

A thin, scheduler-safe wrapper that wires Tasks 1-4 into a single gitignored scorecard
artifact. It is READ-ONLY over the source stores/snapshots, writes ONLY the realized-outcome
scorecard (under ``app/data/realized_outcome/``), NEVER invokes git, and treats an
off-season / not-yet-finalized week as a healthy no-op (exit 0, no artifact mutation).

Off-season is the dominant path today: no finalized in-season week exists yet, and the T1
companion prediction-snapshot capture only begins once the live daily model-PVO-refresh runs
the companion code. So the default run no-ops until the 2026 season produces a finalized week.
``--preflight`` reports readiness without scoring or writing.

The scoring core ``run_scoring`` takes injected loaders so the full path is testable off-season
with fixtures (no live nflreadpy). The ``subprocess`` import is a guarded seam ONLY — this tool
must never invoke git; the contract test patches ``subprocess.run`` to forbid it.

Exit codes (unattended-scheduler alertability): ``ok``/``noop`` are healthy (exit 0); a blocked
or errored status exits non-zero.

Plan: docs/superpowers/plans/2026-06-27-realized-outcome-loop-v1.md (Task 5)
"""
from __future__ import annotations

import argparse
import json
import subprocess  # noqa: F401 — guarded seam: this tool must NEVER invoke git (tests patch subprocess.run to forbid)
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

# Standalone-run path bootstrap: when launchd/cron runs this file directly the repo root is
# not on sys.path, so the first-party `src` imports would crash. Resolve the root from this
# file's location (cwd-independent) before importing.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.outcome_forward_capture_store import (  # noqa: E402
    OutcomeForwardCaptureStore,
    week_status,
)
from src.dynasty_genius.identity.outcome_identity_bridge import (  # noqa: E402
    OutcomeIdentityBridge,
)
from src.dynasty_genius.outcome_loop.realized_outcome_scorer import score  # noqa: E402

# Default gitignored artifact location (mirrors the other capture bricks).
DEFAULT_REPORT_PATH = ROOT / "app" / "data" / "realized_outcome" / "scorecard_latest.json"

_REALIZED_UTIL_FIELDS = (
    "snap_share_realized",
    "route_participation_realized",
    "target_share_nfl_realized",
)


def _weekly_util_fact(util_row: dict[str, Any], season: int, week: int) -> dict[str, Any]:
    """Transform one raw realized-util row into the per-field {value,status} weekly fact the
    scorer's MIF rolling expects (present -> ok; absent -> unavailable, never imputed)."""
    fact: dict[str, Any] = {"season": season, "week": week}
    for field in _REALIZED_UTIL_FIELDS:
        if field in util_row and util_row[field] is not None:
            fact[field] = {"value": util_row[field], "status": "ok"}
        else:
            fact[field] = {"value": None, "status": "unavailable"}
    return fact


def _build_outcomes(
    season: int,
    week: int,
    *,
    schedule_loader: Callable[..., dict[str, Any]],
    stat_loader: Callable[..., list[dict[str, Any]]],
    util_loader: Callable[..., list[dict[str, Any]]],
) -> dict[str, Any]:
    """Ingest finalized weeks 1..week into a THROWAWAY outcome store (system temp, auto-cleaned
    so the only persisted artifact is the scorecard), then build the scorer's ``outcomes`` input
    (per-gsis aggregate OutcomeRow + the weekly realized-util facts for MIF)."""
    players: dict[str, Any] = {}
    weekly_util_by_gsis: dict[str, list[dict[str, Any]]] = {}
    gsis_ids: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        store = OutcomeForwardCaptureStore(Path(tmpdir) / "outcomes.db")
        for current in range(1, week + 1):
            week_schedule = schedule_loader(season, current)
            if week_status(season, current, schedule=week_schedule) != "finalized":
                continue
            stat_rows = stat_loader(season, current)
            util_rows = util_loader(season, current)
            store.ingest_week(
                season,
                current,
                stat_rows=stat_rows,
                util_rows=util_rows,
                schedule=week_schedule,
            )
            for stat_row in stat_rows:
                gsis = str(stat_row.get("player_id"))
                if gsis not in weekly_util_by_gsis:
                    weekly_util_by_gsis[gsis] = []
                    gsis_ids.append(gsis)
            for util_row in util_rows:
                gsis = str(util_row.get("player_id"))
                weekly_util_by_gsis.setdefault(gsis, [])
                weekly_util_by_gsis[gsis].append(
                    _weekly_util_fact(util_row, season, current)
                )
        for gsis in gsis_ids:
            outcome = store.read_outcomes(season, gsis)
            if outcome is None:
                continue
            players[gsis] = {
                "outcome": outcome,
                "weekly_util": weekly_util_by_gsis.get(gsis, []),
            }
    return {"players": players}


def run_scoring(
    season: int,
    week: int,
    report_path: Path | str,
    *,
    schedule_loader: Callable[..., dict[str, Any]],
    stat_loader: Callable[..., list[dict[str, Any]]],
    util_loader: Callable[..., list[dict[str, Any]]],
    prediction_loader: Callable[..., list[dict[str, Any]]],
    identity_snapshot_loader: Callable[..., list[dict[str, Any]]],
) -> dict[str, Any]:
    """Score the frozen model's predictions vs realized outcomes for one finalized week.

    Finality is gated on the queried week's INJECTED schedule FIRST — a not-finalized week is a
    healthy no-op that loads no source rows and mutates no artifact. Writes only the scorecard;
    never invokes git."""
    report_path = Path(report_path)
    schedule = schedule_loader(season, week)
    status = week_status(season, week, schedule=schedule)
    if status != "finalized":
        return {
            "status": "noop",
            "noop_reason": "week_not_finalized",
            "week_status": status,
            "decision_supported": False,
            "git_commit_performed": False,
        }

    predictions = prediction_loader(season, week)
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        identity_snapshot_loader(season, week)
    )
    outcomes = _build_outcomes(
        season,
        week,
        schedule_loader=schedule_loader,
        stat_loader=stat_loader,
        util_loader=util_loader,
    )
    scorecard = score(predictions, outcomes, bridge, as_of_week=week)

    # Stamp the successful run status onto the written artifact (the scorecard body is the
    # pure score() output; a written scorecard always reflects a completed run).
    artifact = {**scorecard, "status": "ok"}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(artifact, indent=2, sort_keys=True))
    return {
        "status": "ok",
        "decision_supported": False,
        "git_commit_performed": False,
        "scorecard_path": str(report_path),
        "week_status": status,
    }


# ── default production loaders (lazy nflreadpy / store-backed; validated at the David-gated
# first live finalized-week run — off-season they keep the dominant no-op path honest) ──
def _default_schedule_loader(season: int, week: int) -> dict[str, Any]:
    import nflreadpy as nfl  # lazy: keep module import standalone-clean + fast

    frame = nfl.load_schedules([season]).to_pandas()
    games = frame[frame["week"] == week]
    statuses = [
        "final" if str(row.get("home_score")) not in {"", "None", "nan"} else "scheduled"
        for _, row in games.iterrows()
    ]
    return {
        "season": season,
        "week": week,
        "expected_game_count": len(games),
        "games": [
            {"season": season, "week": week, "game_id": gid, "status": status}
            for gid, status in zip(games.get("game_id", []), statuses)
        ],
    }


def _default_stat_loader(season: int, week: int) -> list[dict[str, Any]]:
    import nflreadpy as nfl

    frame = nfl.load_player_stats([season]).to_pandas()
    rows = frame[(frame["week"] == week) & (frame["position"].isin(["QB", "RB", "WR", "TE"]))]
    return [
        {
            "player_id": row["player_id"],
            "season": season,
            "week": week,
            "fantasy_points_ppr": row.get("fantasy_points_ppr"),
            "player_status": "active",
            "game_played": True,
        }
        for _, row in rows.iterrows()
    ]


def _default_util_loader(season: int, week: int) -> list[dict[str, Any]]:
    # Realized snap/route/target loaders (load_snap_counts / load_participation) are wired +
    # validated at the David-gated first live finalized-week run; until then a week with no
    # realized-util source yields empty rows (MIF reads unavailable, never imputed).
    return []


def _default_prediction_loader(season: int, week: int) -> list[dict[str, Any]]:
    # Reads the T1 companion prediction snapshots captured by the live daily model-PVO-refresh;
    # wired + validated at go-live (no captured snapshots exist until the companion code runs).
    return []


def _default_identity_snapshot_loader(season: int, week: int) -> list[dict[str, Any]]:
    # Loads the governed identity snapshots (audit/identity_snapshot_generator) for the T2
    # bridge; wired + validated at go-live.
    return []


def _resolve_season_week() -> tuple[int, int]:
    """Resolve a CONCRETE (season, week) for an unattended/no-arg scheduled run — NEVER None,
    so ``run_scoring`` always receives real values and off-season deterministically no-ops.

    Uses nflreadpy's date-derived current season + week (cheap, no schedule download). Off-season
    the current week sits past the played weeks, so the week's finality gate yields the honest
    no-op. ``get_current_week`` is wrapped fail-safe (CI/offline) so a no-arg run never crashes.
    Validated at the David-gated first live finalized-week run."""
    import nflreadpy as nfl  # lazy: keep module import standalone-clean + fast

    season = int(nfl.get_current_season())
    try:
        week = int(nfl.get_current_week())
    except Exception:
        week = 1
    return season, week


def _parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Realized-Outcome Loop weekly scorecard producer (read-only; no-op off-season)."
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Gitignored scorecard artifact path.",
    )
    parser.add_argument("--season", type=int, default=None, help="Season to score.")
    parser.add_argument("--week", type=int, default=None, help="Latest finalized week to score.")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Report readiness without scoring or writing.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    report_path = Path(args.report_path)
    if args.preflight:
        print(
            json.dumps(
                {
                    "preflight": True,
                    "status": "ready",
                    "decision_supported": False,
                    "report_path": str(report_path),
                }
            )
        )
        return 0

    season, week = args.season, args.week
    if season is None or week is None:
        # No-arg scheduled (LaunchAgent) run: resolve concrete values — never pass None onward.
        season, week = _resolve_season_week()

    result = run_scoring(
        season=season,
        week=week,
        report_path=report_path,
        schedule_loader=_default_schedule_loader,
        stat_loader=_default_stat_loader,
        util_loader=_default_util_loader,
        prediction_loader=_default_prediction_loader,
        identity_snapshot_loader=_default_identity_snapshot_loader,
    )
    print(json.dumps(result, default=str))
    return 0 if result.get("status") in {"ok", "noop"} else 1


if __name__ == "__main__":
    sys.exit(main())
