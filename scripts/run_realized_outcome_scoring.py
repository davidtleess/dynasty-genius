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
import contextlib
import hashlib
import json
import math
import os
import sqlite3
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
from src.dynasty_genius.outcome_loop.realized_outcome_scorer import (  # noqa: E402
    ELIGIBLE_GAMES_MIN,
    SETTLEMENT_HORIZON_WEEKS,
    score,
)

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


def _schedule_shape_ok(schedule: Any) -> bool:
    """Structural validation of an external schedule envelope: dict root, PRESENT list
    ``games``, dict rows. A missing or null ``games`` is a malformed envelope — smoothing
    it to ``[]`` would make provider breakage indistinguishable from a genuinely empty
    off-season schedule (green-review R2-B1). Content-level facts (statuses, gamedays) are
    judged downstream; this guard only ensures the shape cannot crash or silently pass the
    health boundary."""
    if not isinstance(schedule, dict):
        return False
    if "games" not in schedule:
        return False
    games = schedule["games"]
    if not isinstance(games, list):
        return False
    return all(isinstance(game, dict) for game in games)


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
    frozen_players: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ingest finalized weeks 1..week into a THROWAWAY outcome store (system temp, auto-cleaned
    so the only persisted artifact is the scorecard), then build the scorer's ``outcomes`` input
    (per-gsis aggregate OutcomeRow + the weekly realized-util facts for MIF).

    ``frozen_players`` seeds the outcome universe from the frozen prediction cohort (v4/R2-B3):
    a frozen player with NO stat row still enters as an EXPLICIT zero-game outcome with
    ``player_status="status_unverified"`` and explicit unavailable weekly facts — retained in
    every cohort denominator, never floored (core delta), never fabricated into a specific
    absence status no governed source can distinguish today."""
    players: dict[str, Any] = {}
    weekly_util_by_gsis: dict[str, list[dict[str, Any]]] = {}
    gsis_ids: list[str] = []
    finalized_weeks: list[int] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        store = OutcomeForwardCaptureStore(Path(tmpdir) / "outcomes.db")
        for current in range(1, week + 1):
            week_schedule = schedule_loader(season, current)
            if week_status(season, current, schedule=week_schedule) != "finalized":
                continue
            finalized_weeks.append(current)
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
    for frozen in frozen_players or []:
        gsis = str(frozen.get("gsis_id") or "")
        if not gsis or gsis in players:
            continue
        players[gsis] = {
            "outcome": {
                "gsis_id": gsis,
                "season": season,
                "games_played": 0,
                "ppg_to_date": None,
                "player_status": "status_unverified",
            },
            "weekly_util": [
                _weekly_util_fact({}, season, current) for current in finalized_weeks
            ],
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
            for key in ("noop_reason", "failure_reason", "week_status", "gameday", "coverage"):
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

    def _failed(reason: str, **extra: Any) -> dict[str, Any]:
        return _terminal(
            {
                "status": "failed",
                "failure_reason": reason,
                "decision_supported": False,
                "git_commit_performed": False,
                **extra,
            }
        )

    try:
        loaded_predictions = prediction_loader(season, week)
    except MarkerWriteError:  # pragma: no cover — loaders never raise this
        raise
    except Exception as exc:
        return _failed(f"predictions_load_failed:{type(exc).__name__}")
    # Envelope normalization + shape validation (green-review R2-B2): the production
    # loader returns {rows, coverage}; injected legacy loaders may still return a bare
    # list (existing contracts pin that shape). A mapping envelope must CARRY a present
    # list ``rows`` and mapping ``coverage``, and every row must be a mapping — anything
    # else is a malformed envelope that fails CLOSED with a terminal marker, never a
    # healthy-looking noop and never a raw exception.
    if isinstance(loaded_predictions, dict):
        envelope_rows = loaded_predictions.get("rows")
        if "rows" not in loaded_predictions or not isinstance(envelope_rows, list):
            return _failed("prediction_envelope_invalid")
        if not isinstance(loaded_predictions.get("coverage"), dict):
            return _failed("prediction_envelope_invalid")
        predictions = list(envelope_rows)
        loader_coverage = dict(loaded_predictions["coverage"])
    elif isinstance(loaded_predictions, list):
        predictions = list(loaded_predictions)
        loader_coverage = {}
    else:
        return _failed("prediction_envelope_invalid")
    if not all(isinstance(row, dict) for row in predictions):
        return _failed("prediction_envelope_invalid")
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
    # G1 (green-review round 1): the loader's RETURNED shape is external data and must fail
    # CLOSED with a terminal marker — a malformed schedule must never escape as a raw
    # exception with the marker unwritten.
    if not _schedule_shape_ok(schedule):
        return _failed("schedule_shape_invalid")
    status = week_status(season, week, schedule=schedule)
    if status != "finalized":
        # Nonfinal-age law (framing v4 R2-B4): a target week with games on the schedule that
        # is STILL nonfinal >14 days past its last gameday is a stuck pipeline, not a quiet
        # off-season — on BOTH the scheduled and explicit paths. The bound reuses the
        # shipped freshness constant; zero games for the target week is the true off-season
        # and stays a healthy no-op (no age exists to measure). Unparseable or absent
        # gamedays make the age indeterminate and fail LOUD.
        target_games = [
            game
            for game in (schedule.get("games") or [])
            if game.get("season") == season and game.get("week") == week
        ]
        if target_games:
            gamedays = []
            for game in target_games:
                try:
                    gamedays.append(
                        datetime.strptime(str(game.get("gameday")), "%Y-%m-%d").date()
                    )
                except (TypeError, ValueError):
                    return _failed("nonfinal_age_indeterminate", week_status=status)
            latest = max(gamedays)
            if (now.date() - latest).days > target_max_age_days:
                return _failed(
                    "week_nonfinal_overdue", week_status=status, gameday=str(latest)
                )
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

    # Frozen-cohort resolution (coverage denominators + outcome-universe seeding, v4/W1):
    # every prediction resolves or is COUNTED by its resolution status — never dropped.
    identity_excluded_counts: dict[str, int] = {}
    resolved_gsis: list[str] = []
    for prediction in predictions:
        resolution = bridge.resolve(
            prediction.get("sleeper_id"), prediction.get("capture_date")
        )
        resolution_status = getattr(resolution, "resolution_status", None)
        gsis_id = getattr(resolution, "gsis_id", None)
        if resolution_status == "resolved" and gsis_id:
            resolved_gsis.append(str(gsis_id))
        else:
            key = str(resolution_status or "unresolved")
            identity_excluded_counts[key] = identity_excluded_counts.get(key, 0) + 1

    try:
        outcomes = _build_outcomes(
            season,
            week,
            schedule_loader=schedule_loader,
            stat_loader=stat_loader,
            util_loader=util_loader,
            frozen_players=[{"gsis_id": gsis_id} for gsis_id in resolved_gsis],
        )
    except Exception as exc:
        return _failed(f"outcome_build_failed:{type(exc).__name__}")

    try:
        scorecard = score(predictions, outcomes, bridge, as_of_week=week)
    except Exception as exc:
        return _failed(f"scoring_failed:{type(exc).__name__}")

    # Coverage denominators (v4/W1): grading nothing while reporting healthy is the trap
    # this build closes — zero graded is a FAILURE with a stated basis. Partial coverage is
    # disclosed as raw counts; no degraded band is invented (that threshold is David's).
    players_by_gsis = outcomes.get("players") or {}
    tracking_rows = scorecard.get("tracking_rows") or []
    graded_count = sum(
        1 for row in tracking_rows if row.get("realized_ppg_to_date") is not None
    )
    settled = week >= SETTLEMENT_HORIZON_WEEKS
    rank_eligible_count = 0
    for row in tracking_rows:
        if row.get("realized_ppg_to_date") is None:
            continue
        if settled:
            rank_eligible_count += 1
            continue
        entry = players_by_gsis.get(row.get("gsis_id")) or {}
        games_played = int((entry.get("outcome") or {}).get("games_played") or 0)
        if games_played >= ELIGIBLE_GAMES_MIN:
            rank_eligible_count += 1
    coverage = {
        "declared_count": loader_coverage.get("declared_count", len(predictions)),
        "eligible_count": loader_coverage.get("eligible_count", len(predictions)),
        "resolved_count": len(resolved_gsis),
        "outcome_present_count": sum(
            1 for gsis_id in dict.fromkeys(resolved_gsis) if gsis_id in players_by_gsis
        ),
        "graded_count": graded_count,
        "rank_eligible_count": rank_eligible_count,
        "prediction_excluded_counts": loader_coverage.get(
            "prediction_excluded_counts", {}
        ),
        "identity_excluded_counts": identity_excluded_counts,
    }
    if graded_count == 0:
        return _failed("zero_graded_predictions", coverage=coverage)

    # Stamp the successful run status onto the written artifact (the scorecard body is
    # the pure score() output; a written scorecard always reflects a completed run).
    artifact = {**scorecard, "status": "ok", "coverage": coverage}

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
        "coverage": coverage,
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
        # B21 law (Q2(c)): a populated score proves play was OBSERVED, never that play
        # ENDED — nflverse may publish interim scores. The score-derived default schedule
        # can therefore never certify finality; `week_status` finalizes only on "final",
        # which only a governed finality-evidence provider (David-gated) may assert.
        status = (
            "result_observed_unverified"
            if str(row.get("home_score")) not in {"", "None", "nan"}
            else "scheduled"
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


# Canonical nflverse usage store (snap counts). Realized snap share is the ONLY realized-util
# field wired this cycle: route participation has no local substrate, and WOPR's substrate is
# a third-party model output under a symbol-level consumer ban pending its own validation —
# both read `unavailable`, never imputed (framing v3 R2-B1/Q3).
NFLVERSE_USAGE_DB = ROOT / "app" / "data" / "nflverse_usage.db"


def _default_util_loader(season: int, week: int) -> list[dict[str, Any]]:
    """Realized snap share from ``player_snap_count`` (pfr-keyed → gsis via the pinned
    crosswalk). Unresolvable pfr ids are skipped — those players' MIF facts read
    ``unavailable``. Malformed, out-of-range, or duplicate snap rows fail LOUD."""
    if not NFLVERSE_USAGE_DB.exists():
        return []  # honest absence: every realized-util fact reads unavailable
    path = _resolve_ff_playerids_path()
    by_gsis, _by_sleeper = _load_ff_playerids(path)
    # G2 (green-review round 1): a PFR id claimed by MORE than one GSIS identity is
    # AMBIGUOUS and must never be assigned — last-write-wins would silently attach a
    # player's snaps to the wrong human (the real pinned crosswalk carries 3 such
    # collisions). Ambiguous ids are excluded deterministically; their snap rows then skip
    # below and those players' MIF facts read `unavailable` — per-field fail-closed, never
    # a wrong join and never a run-killing raise for a data state that legitimately exists.
    pfr_claims: dict[str, set[str]] = {}
    for gsis_id, mapping in by_gsis.items():
        pfr_id = mapping.get("pfr_id")
        if pfr_id:
            pfr_claims.setdefault(str(pfr_id), set()).add(
                str(mapping.get("gsis_id") or gsis_id)
            )
    pfr_to_gsis: dict[str, str] = {
        pfr_id: next(iter(claimants))
        for pfr_id, claimants in pfr_claims.items()
        if len(claimants) == 1
    }

    with contextlib.closing(
        sqlite3.connect(f"file:{NFLVERSE_USAGE_DB}?mode=ro", uri=True)
    ) as conn:
        snap_rows = conn.execute(
            """
            SELECT pfr_player_id, offense_pct
              FROM player_snap_count
             WHERE season = ? AND week = ?
            """,
            (str(season), str(week)),
        ).fetchall()

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for pfr_player_id, offense_pct in snap_rows:
        key = str(pfr_player_id)
        if key in seen:
            raise ValueError("snap_share_duplicate")
        seen.add(key)
        try:
            value = float(offense_pct)
        except (TypeError, ValueError) as exc:
            raise ValueError("snap_share_invalid") from exc
        if not math.isfinite(value):
            raise ValueError("snap_share_invalid")
        if value < 0.0 or value > 1.0:
            raise ValueError("snap_share_out_of_range")
        gsis_id = pfr_to_gsis.get(key)
        if gsis_id is None:
            continue
        rows.append(
            {
                "player_id": gsis_id,
                "season": season,
                "week": week,
                "snap_share_realized": value,
            }
        )
    return rows


PREDICTION_CAPTURE_DB = ROOT / "app" / "data" / "model_forward_capture.db"
FROZEN_PREDICTION_DECLARATION = (
    ROOT / "app" / "config" / "realized_outcome_frozen_predictions.json"
)


class FrozenPredictionSetUndeclared(RuntimeError):
    """No governed declaration says WHICH capture is the frozen set for this season.

    This RAISES rather than returning ``[]`` deliberately.  An empty return becomes
    ``noop:no_predictions_for_target``, and ``noop`` is a SUCCESS status on this artifact's
    ``auxiliary`` tier — so an undeclared freeze would report the loop healthy all season
    while grading nothing.  Not knowing which predictions are frozen is a failure to say so,
    not a quiet success.
    """


def _load_frozen_declaration(season: int) -> dict[str, Any]:
    """The frozen capture is DECLARED, never inferred.

    Selecting "the prediction for week N" from a daily capture history needs a season
    calendar, and calendar anchors are not governed here — `tests/contract/
    test_governed_cadence_inputs_red.py` records that they are underivable from what we hold
    and that the route is David's call.  Guessing one inside a loader would bury exactly the
    kind of silent assumption that contract exists to forbid, so the rule is read from a
    declaration that carries its own author and date.
    """
    if not FROZEN_PREDICTION_DECLARATION.exists():
        raise FrozenPredictionSetUndeclared(
            f"no declaration at {FROZEN_PREDICTION_DECLARATION.relative_to(ROOT)}"
        )
    try:
        declared = json.loads(
            FROZEN_PREDICTION_DECLARATION.read_text(),
            object_pairs_hook=_reject_duplicate_declaration_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenPredictionSetUndeclared(f"declaration unreadable: {exc}") from exc
    if not isinstance(declared, dict):
        raise FrozenPredictionSetUndeclared("declaration_root_not_object")
    seasons = declared.get("seasons")
    if seasons is not None and not isinstance(seasons, dict):
        raise FrozenPredictionSetUndeclared("declaration_seasons_not_object")
    entry = (seasons or {}).get(str(season))
    if entry is None:
        raise FrozenPredictionSetUndeclared(f"no declared frozen set for season {season}")
    if not isinstance(entry, dict):
        raise FrozenPredictionSetUndeclared("declaration_entry_not_object")
    for field in ("frozen_capture_date", "source", "declared_by", "declared_at"):
        if not entry.get(field):
            raise FrozenPredictionSetUndeclared(
                f"season {season} declaration missing '{field}'"
            )
    try:
        datetime.strptime(str(entry["frozen_capture_date"]), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise FrozenPredictionSetUndeclared("frozen_capture_date_invalid") from exc
    # G4 (green-review round 1): a declaration timestamp is a TIMESTAMP — date-only or
    # timezone-naive values are ambiguous provenance and fail named.
    declared_at_raw = str(entry["declared_at"])
    try:
        declared_at = datetime.fromisoformat(declared_at_raw)
    except (TypeError, ValueError) as exc:
        raise FrozenPredictionSetUndeclared("declared_at_invalid") from exc
    if "T" not in declared_at_raw or declared_at.tzinfo is None:
        raise FrozenPredictionSetUndeclared("declared_at_invalid")
    return entry


def _reject_duplicate_declaration_keys(pairs: list) -> dict[str, Any]:
    seen: set[str] = set()
    for key, _value in pairs:
        if key in seen:
            raise FrozenPredictionSetUndeclared("declaration_duplicate_json_key")
        seen.add(key)
    return dict(pairs)


_UTILIZATION_ROLES = frozenset({"model_input", "diagnostic_only"})


def _parse_prediction_utilization(raw: Any) -> dict[str, Any]:
    """Parse+validate a captured row's prediction-time utilization payload (fail loud —
    a captured row without a well-formed utilization is a capture defect, never `{}`)."""
    try:
        parsed = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("utilization_invalid_json") from exc
    if parsed is None:
        raise ValueError("utilization_invalid_json")
    if not isinstance(parsed, dict):
        raise ValueError("utilization_not_object")
    for field, entry in parsed.items():
        if not isinstance(entry, dict):
            raise ValueError("utilization_value_invalid")
        value = entry.get("value")
        if isinstance(value, bool) or not (
            value is None or isinstance(value, (int, float))
        ):
            raise ValueError("utilization_value_invalid")
        # G3 (green-review round 1): numeric edges fail LOUD — a NaN/Inf would otherwise
        # flow into eligible MIF as an ok-status fact, and a snap share outside [0, 1] is
        # not a share.
        if value is not None and not math.isfinite(value):
            raise ValueError("utilization_value_nonfinite")
        if (
            field == "snap_share"
            and value is not None
            and (value < 0.0 or value > 1.0)
        ):
            raise ValueError("utilization_snap_share_out_of_range")
        if entry.get("role") not in _UTILIZATION_ROLES:
            raise ValueError("utilization_role_invalid")
    return parsed


def _default_prediction_loader(season: int, week: int) -> dict[str, Any]:
    """Read the frozen prediction set as a ``{rows, coverage}`` envelope.

    ``model_forward_prediction_snapshot`` holds the values; ``model_forward_capture_joinable``
    holds the identity (`sleeper_id`, frozen `dg_player_id`) and `position`, on the same
    five-part key. The DENOMINATOR is every joinable (model-supported) row on the DECLARED
    capture — never the unfiltered snapshot universe and never a hardcoded count. Only rows
    the capture itself marked ``captured`` with a non-null ``projection_2y`` are eligible;
    every other model-supported row is COUNTED by status, never silently dropped — a
    ``capture_incomplete`` row is an absence of a prediction, never a prediction of nothing.
    Prediction-time utilization is parsed and validated (roles included) so MIF receives
    per-field facts, never a silent ``{}``.
    """
    del week  # the frozen set is per-season; the week selects OUTCOMES, not predictions
    entry = _load_frozen_declaration(season)
    if not PREDICTION_CAPTURE_DB.exists():
        raise FrozenPredictionSetUndeclared(
            f"declared frozen set but no capture store at "
            f"{PREDICTION_CAPTURE_DB.relative_to(ROOT)}"
        )
    with contextlib.closing(
        sqlite3.connect(f"file:{PREDICTION_CAPTURE_DB}?mode=ro", uri=True)
    ) as conn:
        conn.row_factory = sqlite3.Row
        joinable = conn.execute(
            """
            SELECT j.sleeper_id AS sleeper_id,
                   j.dg_player_id AS dg_player_id,
                   j.position AS position,
                   s.capture_date AS capture_date,
                   s.source AS source,
                   s.semantic_output_hash AS semantic_output_hash,
                   s.provenance_hash AS provenance_hash,
                   s.player_key AS player_key,
                   s.projection_2y AS projection_2y,
                   s.utilization AS utilization,
                   s.prediction_ppg_status AS prediction_ppg_status,
                   s.util_snapshot_status AS util_snapshot_status,
                   s.schema_version AS schema_version,
                   s.source_hash AS source_hash
              FROM model_forward_prediction_snapshot AS s
              JOIN model_forward_capture_joinable AS j
                ON j.capture_date = s.capture_date
               AND j.source = s.source
               AND j.semantic_output_hash = s.semantic_output_hash
               AND j.provenance_hash = s.provenance_hash
               AND j.player_key = s.player_key
             WHERE s.capture_date = ?
               AND s.source = ?
            """,
            (entry["frozen_capture_date"], entry["source"]),
        ).fetchall()

    status_counts: dict[str, int] = {}
    excluded_counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for raw in joinable:
        status = str(raw["prediction_ppg_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "captured" and raw["projection_2y"] is not None:
            rows.append(
                {
                    "sleeper_id": raw["sleeper_id"],
                    "dg_player_id": raw["dg_player_id"],
                    "position": raw["position"],
                    "capture_date": raw["capture_date"],
                    "source": raw["source"],
                    "semantic_output_hash": raw["semantic_output_hash"],
                    "provenance_hash": raw["provenance_hash"],
                    "player_key": raw["player_key"],
                    "projection_2y": raw["projection_2y"],
                    "utilization": _parse_prediction_utilization(raw["utilization"]),
                    "util_snapshot_status": raw["util_snapshot_status"],
                    "schema_version": raw["schema_version"],
                    "source_hash": raw["source_hash"],
                }
            )
        else:
            excluded_counts[status] = excluded_counts.get(status, 0) + 1
    if not rows:
        # A DECLARED capture that yields nothing is a broken declaration, not an off-season
        # quiet day: the declaration asserts this capture is the frozen set.
        raise FrozenPredictionSetUndeclared(
            f"declared frozen capture {entry['frozen_capture_date']}"
            f" ({entry['source']}) yielded zero captured predictions"
        )
    return {
        "rows": rows,
        "coverage": {
            "declared_capture_date": entry["frozen_capture_date"],
            "declared_count": len(joinable),
            "eligible_count": len(rows),
            "prediction_status_counts": status_counts,
            "prediction_excluded_counts": excluded_counts,
        },
    }


# Pinned sleeper→gsis crosswalk (Q1(c) conditional, W2 provenance rules). ``None`` resolves
# the canonical path lazily; tests inject a fixture path. The loader below DELEGATES to the
# hardened canonical reader — never a second hand-rolled crosswalk parser.
FF_PLAYERIDS_PATH: Path | None = None


def _resolve_ff_playerids_path() -> Path:
    if FF_PLAYERIDS_PATH is not None:
        return Path(FF_PLAYERIDS_PATH)
    from scripts.build_universe_pvo_batch import FF_PLAYERIDS_PATH as canonical_path

    return Path(canonical_path)


def _load_ff_playerids(path: Path):
    from scripts.build_universe_pvo_batch import _load_ff_playerids as canonical

    return canonical(path)


def _default_identity_snapshot_loader(season: int, week: int) -> list[dict[str, Any]]:
    """One governed point-in-time identity snapshot for the T2 bridge.

    Provenance stamps the crosswalk's own SOURCE pull timestamp (never scoring time), the
    file's SHA-256, and the mapping version; mappings are keyed by the FROZEN capture's
    ``dg_player_id`` (preserved, never fabricated). A frozen sleeper the crosswalk cannot
    resolve is simply omitted — the bridge then reports it unresolved and the scorer counts
    it, never guesses it.
    """
    del week  # identity follows the frozen per-season set
    entry = _load_frozen_declaration(season)
    if not PREDICTION_CAPTURE_DB.exists():
        raise FrozenPredictionSetUndeclared(
            f"declared frozen set but no capture store at "
            f"{PREDICTION_CAPTURE_DB.relative_to(ROOT)}"
        )
    with contextlib.closing(
        sqlite3.connect(f"file:{PREDICTION_CAPTURE_DB}?mode=ro", uri=True)
    ) as conn:
        pairs = conn.execute(
            """
            SELECT DISTINCT j.dg_player_id, j.sleeper_id
              FROM model_forward_capture_joinable AS j
              JOIN model_forward_prediction_snapshot AS s
                ON s.capture_date = j.capture_date
               AND s.source = j.source
               AND s.semantic_output_hash = j.semantic_output_hash
               AND s.provenance_hash = j.provenance_hash
               AND s.player_key = j.player_key
             WHERE s.capture_date = ?
               AND s.source = ?
               AND s.prediction_ppg_status = 'captured'
               AND s.projection_2y IS NOT NULL
            """,
            (entry["frozen_capture_date"], entry["source"]),
        ).fetchall()

    path = _resolve_ff_playerids_path()
    by_gsis, by_sleeper = _load_ff_playerids(path)
    if not by_gsis and not by_sleeper:
        raise ValueError("identity_crosswalk_empty")
    raw_bytes = path.read_bytes()
    try:
        metadata = (json.loads(raw_bytes.decode("utf-8")) or {}).get("metadata") or {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("identity_crosswalk_metadata_unreadable") from exc
    pull_timestamp = metadata.get("pull_timestamp")
    if not pull_timestamp:
        raise ValueError("identity_crosswalk_missing_pull_timestamp")

    mappings: dict[str, dict[str, Any]] = {}
    for dg_player_id, sleeper_id in pairs:
        mapping = by_sleeper.get(str(sleeper_id))
        if not mapping or not mapping.get("gsis_id"):
            continue  # unresolved: excluded and counted downstream, never guessed
        mappings[str(dg_player_id)] = {
            "sleeper_id": str(sleeper_id),
            "gsis_id": mapping["gsis_id"],
            "pfr_id": mapping.get("pfr_id"),
        }
    duplicate_count = max(
        int(getattr(by_gsis, "duplicate_count", 0) or 0),
        int(getattr(by_sleeper, "duplicate_count", 0) or 0),
    )
    return [
        {
            "timestamp": pull_timestamp,
            "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "mapping_version": path.stem,
            "duplicate_count": duplicate_count,
            "mappings": mappings,
        }
    ]


def _resolve_season_week(
    *,
    season_provider: Callable[[], Any] | None = None,
    week_provider: Callable[[], Any] | None = None,
) -> tuple[int, int]:
    """Resolve a CONCRETE (season, week) for an unattended/no-arg scheduled run — NEVER None.

    Target the LEAGUE YEAR, not the last played season (2026-08-18).

    This resolver used to return ``nfl.get_current_season()``, which is date-derived and
    stays on the COMPLETED season until the Thursday after Labor Day — so all summer it
    resolved 2025 wk 22. That was survivable while an unknown season merely produced an
    empty prediction set and a healthy ``noop:no_predictions_for_target``; it is not
    survivable since the 2026-08-13 frozen-set declaration, because ``_load_frozen
    _declaration`` RAISES for an undeclared season. The loop therefore reported
    ``predictions_load_failed:FrozenPredictionSetUndeclared`` every day of the pre-season
    while nothing was actually wrong. Both halves were behaving as designed; the target was
    the defect. We hold zero predictions for 2025 and never will — the declared frozen set
    is 2026-08-05, a 2026 prediction.

    ``roster=True`` is nflreadpy's league-year semantic (rolls at March 15), which is the
    right clock for a dynasty product: the asset year turns over long before Week 1. During
    the pre-season window — league year ahead of the last played season — the target week is
    1, the first week that can ever be graded. Once the played season catches up, the live
    week provider takes over and grading proceeds normally.

    Providers stay injectable so tests probe rollover cases without live nflreadpy, and
    ``week_provider`` stays fail-safe (CI/offline) so a no-arg run never crashes."""
    if season_provider is None or week_provider is None:
        import nflreadpy as nfl  # lazy: keep module import standalone-clean + fast

        def _league_year() -> int:
            return int(nfl.get_current_season(roster=True))

        def _week_for_league_year() -> int:
            # Pre-season: the league year has rolled but no game of it has been played, so
            # the live week provider still reports the PRIOR season's final week (22).
            # Week 1 is the only honest target; run_scoring's finality gate then no-ops it
            # until Week 1 actually finalizes.
            if _league_year() != int(nfl.get_current_season()):
                return 1
            return int(nfl.get_current_week())

        season_provider = season_provider or _league_year
        week_provider = week_provider or _week_for_league_year

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
