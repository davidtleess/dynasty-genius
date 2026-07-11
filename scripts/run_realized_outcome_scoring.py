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
import os
import subprocess  # noqa: F401 — guarded seam: this tool must NEVER invoke git (tests patch subprocess.run to forbid)
import sys
import tempfile
from datetime import datetime, timezone
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

# Terminal status marker: written on EVERY terminal state (ok/noop/failed) so a scheduled
# run can never fail silently again. Execution state ONLY — never model performance.
DEFAULT_MARKER_PATH = (
    ROOT / "app" / "data" / "valuation_runtime" / "realized_outcome_scoring_status_latest.json"
)

# Scheduled-target freshness window (spec §2.2): the no-arg resolver path refuses a target
# whose last game is older than this — schedule-date-anchored, never calendar heuristics.
# Explicit --season/--week invocations bypass (a human-named target is intentional backfill).
SCHEDULED_TARGET_MAX_AGE_DAYS = 14


class MarkerWriteError(RuntimeError):
    """The terminal status marker could not be written — the run must fail LOUD."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _write_marker(marker_path: Path | str, payload: dict[str, Any]) -> None:
    try:
        path = Path(marker_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        raise MarkerWriteError(
            f"terminal status marker write failed at {marker_path}: {exc}"
        ) from exc


def _read_marker(marker_path: Path | str) -> Optional[dict[str, Any]]:
    """Absent/corrupt marker reads as None — it never blocks a run; this run's terminal
    state overwrites it (the marker is operational state, not compounding history)."""
    try:
        loaded = json.loads(Path(marker_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _latest_gameday(schedule: dict[str, Any], season: int, week: int):
    """Max parseable YYYY-MM-DD gameday among the target week's games; None when absent."""
    dates = []
    for game in schedule.get("games") or []:
        if game.get("season") == season and game.get("week") == week:
            try:
                dates.append(datetime.strptime(str(game.get("gameday")), "%Y-%m-%d").date())
            except (TypeError, ValueError):
                continue
    return max(dates) if dates else None

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
    marker_path: Path | str | None = None,
    enforce_target_freshness: bool = False,
    target_max_age_days: int = SCHEDULED_TARGET_MAX_AGE_DAYS,
    now_fn: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Score the frozen model's predictions vs realized outcomes for one finalized week.

    Gate order (spec 2026-07-11, each gate a marker-recorded terminal no-op/fail):
    1. predictions FIRST (local/cheap) — empty -> ``no_predictions_for_target``; an ok
       scorecard REQUIRES real frozen predictions by construction, and no network loader
       is touched before this gate.
    2. the marker is the target ledger — same (season, week) already ``ok`` (or already
       recorded ``already_scored``) -> ``already_scored``, never a summer of re-scores.
    3. finality on the injected schedule (existing law) -> ``week_not_finalized``.
    4. scheduled-target freshness (``enforce_target_freshness=True`` on the no-arg
       resolver path only) — target's last gameday older than ``target_max_age_days``
       -> ``stale_target``; unparseable gamedays fail LOUD (``target_freshness_indeterminate``).

    Every terminal state writes the status marker when ``marker_path`` is given; a marker
    write failure raises :class:`MarkerWriteError` (the run must fail loud, never silent).
    Writes only the scorecard + marker; never invokes git."""
    report_path = Path(report_path)
    now = (now_fn or _utc_now)()

    def _terminal(result: dict[str, Any]) -> dict[str, Any]:
        if marker_path is not None:
            marker = {
                "status": result["status"],
                "finished_at": now.isoformat(),
                "season": season,
                "week": week,
                "decision_supported": False,
            }
            for key in ("noop_reason", "failure_reason", "week_status"):
                if key in result:
                    marker[key] = result[key]
            _write_marker(marker_path, marker)
        return result

    def _noop(reason: str, **extra: Any) -> dict[str, Any]:
        return _terminal(
            {
                "status": "noop",
                "noop_reason": reason,
                "decision_supported": False,
                "git_commit_performed": False,
                **extra,
            }
        )

    def _failed(reason: str) -> dict[str, Any]:
        return _terminal(
            {
                "status": "failed",
                "failure_reason": reason,
                "decision_supported": False,
                "git_commit_performed": False,
            }
        )

    try:
        predictions = prediction_loader(season, week)
    except MarkerWriteError:  # pragma: no cover — loaders never raise this
        raise
    except Exception as exc:
        return _failed(f"predictions_load_failed:{type(exc).__name__}")
    if not predictions:
        return _noop("no_predictions_for_target")

    if marker_path is not None:
        prior = _read_marker(marker_path)
        if (
            prior is not None
            and prior.get("season") == season
            and prior.get("week") == week
            and (
                prior.get("status") == "ok"
                or prior.get("noop_reason") == "already_scored"
            )
        ):
            return _noop("already_scored")

    try:
        schedule = schedule_loader(season, week)
    except Exception as exc:
        return _failed(f"schedule_load_failed:{type(exc).__name__}")
    status = week_status(season, week, schedule=schedule)
    if status != "finalized":
        return _noop("week_not_finalized", week_status=status)

    if enforce_target_freshness:
        latest = _latest_gameday(schedule, season, week)
        if latest is None:
            return _failed("target_freshness_indeterminate")
        if (now.date() - latest).days > target_max_age_days:
            return _noop("stale_target")

    try:
        bridge = OutcomeIdentityBridge.from_identity_snapshots(
            identity_snapshot_loader(season, week)
        )
    except Exception as exc:
        return _failed(f"identity_bridge_failed:{type(exc).__name__}")
    try:
        outcomes = _build_outcomes(
            season,
            week,
            schedule_loader=schedule_loader,
            stat_loader=stat_loader,
            util_loader=util_loader,
        )
    except Exception as exc:
        return _failed(f"outcome_build_failed:{type(exc).__name__}")

    try:
        scorecard = score(predictions, outcomes, bridge, as_of_week=week)
        # Stamp the successful run status onto the written artifact (the scorecard body is
        # the pure score() output; a written scorecard always reflects a completed run).
        artifact = {**scorecard, "status": "ok"}
    except Exception as exc:
        return _failed(f"scoring_failed:{type(exc).__name__}")

    # Publish coupling (F16/F17): temp scorecard -> ok MARKER -> atomic publish. A marker
    # write failure leaves the report byte-unchanged (temp discarded, MarkerWriteError
    # propagates loud); a publish failure rewrites the marker to failed so the marker can
    # never vouch for a scorecard that was not actually published.
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_report = report_path.with_name(report_path.name + ".tmp")
        tmp_report.write_text(json.dumps(artifact, indent=2, sort_keys=True))
    except OSError as exc:
        return _failed(f"scorecard_write_failed:{type(exc).__name__}")
    result = {
        "status": "ok",
        "decision_supported": False,
        "git_commit_performed": False,
        "scorecard_path": str(report_path),
        "week_status": status,
    }
    try:
        _terminal(result)
    except MarkerWriteError:
        tmp_report.unlink(missing_ok=True)
        raise
    try:
        os.replace(tmp_report, report_path)
    except OSError as exc:
        tmp_report.unlink(missing_ok=True)
        return _failed(f"scorecard_publish_failed:{type(exc).__name__}")
    return result


# ── default production loaders (lazy nflreadpy / store-backed; validated at the David-gated
# first live finalized-week run — off-season they keep the dominant no-op path honest) ──
def _default_schedule_loader(season: int, week: int) -> dict[str, Any]:
    import nflreadpy as nfl  # lazy: keep module import standalone-clean + fast

    frame = nfl.load_schedules([season]).to_pandas()
    games = frame[frame["week"] == week]
    game_rows = []
    for _, row in games.iterrows():
        status = (
            "final" if str(row.get("home_score")) not in {"", "None", "nan"} else "scheduled"
        )
        game_rows.append(
            {
                "season": season,
                "week": week,
                "game_id": row.get("game_id"),
                "status": status,
                # gameday feeds the scheduled-target freshness guard (spec §2.2).
                "gameday": row.get("gameday"),
            }
        )
    return {
        "season": season,
        "week": week,
        "expected_game_count": len(games),
        "games": game_rows,
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


def _resolve_season_week(
    *,
    season_provider: Callable[[], Any] | None = None,
    week_provider: Callable[[], Any] | None = None,
) -> tuple[int, int]:
    """Resolve a CONCRETE (season, week) for an unattended/no-arg scheduled run — NEVER None.

    The resolver is deliberately DUMB: nflreadpy's date-derived values keep returning the
    COMPLETED season (e.g. 2025 week 22 in July 2026), so a resolved target is NOT evidence
    of live work. Honesty lives in ``run_scoring``'s gates: predictions-first, the marker
    target ledger, finality, and the scheduled-target freshness guard (spec 2026-07-11 —
    this replaces the disproven "off-season resolves past the played weeks" assumption).
    Providers are injectable so tests probe rollover cases without live nflreadpy.
    ``week_provider`` is wrapped fail-safe (CI/offline) so a no-arg run never crashes."""
    if season_provider is None or week_provider is None:
        import nflreadpy as nfl  # lazy: keep module import standalone-clean + fast

        season_provider = season_provider or nfl.get_current_season
        week_provider = week_provider or nfl.get_current_week

    season = int(season_provider())
    try:
        week = int(week_provider())
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
    parser.add_argument(
        "--marker-path",
        default=str(DEFAULT_MARKER_PATH),
        help="Gitignored terminal status marker path (execution state only).",
    )
    parser.add_argument("--season", type=int, default=None, help="Season to score.")
    parser.add_argument("--week", type=int, default=None, help="Latest finalized week to score.")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Report readiness without scoring or writing.",
    )
    return parser.parse_args(argv)


def main(
    argv: Optional[list[str]] = None,
    *,
    now_fn: Callable[[], datetime] | None = None,
) -> int:
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
    explicit_target = season is not None and week is not None
    if not explicit_target:
        # No-arg scheduled (LaunchAgent) run: resolve concrete values — never pass None onward.
        # The resolver may return a stale completed-season target; the freshness guard
        # (enforced ONLY on this path) refuses it. Explicit targets are intentional backfills.
        season, week = _resolve_season_week()

    try:
        result = run_scoring(
            season=season,
            week=week,
            report_path=report_path,
            marker_path=Path(args.marker_path),
            enforce_target_freshness=not explicit_target,
            now_fn=now_fn,
            schedule_loader=_default_schedule_loader,
            stat_loader=_default_stat_loader,
            util_loader=_default_util_loader,
            prediction_loader=_default_prediction_loader,
            identity_snapshot_loader=_default_identity_snapshot_loader,
        )
    except MarkerWriteError as exc:
        # The one sanctioned stderr-only path: the truth surface itself is unwritable.
        print(f"FATAL: status marker write failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, default=str))
    return 0 if result.get("status") in {"ok", "noop"} else 1


if __name__ == "__main__":
    sys.exit(main())
