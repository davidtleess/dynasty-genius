"""Realized-Outcome Loop T3 — outcome ingestion store + week-finalized gate.

An append-only, immutable store of weekly realized-outcome FACTS (one row per
``(season, week, gsis_id)``), mirroring the existing capture-store convention
(``fc_forward_capture_store`` / ``model_forward_capture_store``): a byte-identical
re-ingest is an idempotent no-op; a same-key ingest with differing content raises
(never an upsert). Season-to-date and rolling 3/5/8 aggregates are computed at
``read_outcomes`` time from the immutable weekly facts (Design A).

Finality is read from an INJECTED schedule, never inferred from the presence of stat
rows: a week ingests only when its schedule shows the expected number of games and
every game is ``final``. A non-finalized week no-ops (no partial-week ingest).

Survivorship-complete: a player who did not play (bye/injured/not_yet_played/departed)
is retained as an explicit zero-game fact, never dropped — it just does not inflate
``games_played`` or PPG. Realized utilization comes from a SEPARATE injected source and
is fail-closed: an absent field is ``{value: None, status: "unavailable"}``, never imputed.

``decision_supported`` semantics are descriptive only (this store records facts; the
scorer in T4 derives metrics). Realized fantasy production loads from
``nflreadpy.load_player_stats``; realized snap/route/target from ``load_snap_counts`` /
``load_participation`` (the producer/CLI wires those); finality from ``load_schedules``.
The store itself takes injected rows so it is testable without live data.

Design spec: docs/superpowers/specs/2026-06-27-realized-outcome-loop-design.md (§4.3).
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from statistics import fmean
from typing import Any, Optional

TABLE = "outcome_forward_capture_weekly"

KEY_COLUMNS = ("season", "week", "gsis_id")

# Per-field realized-utilization columns: a value + an explicit ok/unavailable status.
UTIL_FIELDS = (
    "snap_share_realized",
    "route_participation_realized",
    "target_share_nfl_realized",
)
_UTIL_STATUS_COLUMNS = tuple(f"{field}_status" for field in UTIL_FIELDS)

CONTENT_COLUMNS = (
    "fantasy_points_ppr",
    "player_status",
    "game_played",
    *UTIL_FIELDS,
    *_UTIL_STATUS_COLUMNS,
)
_ALL_COLUMNS = KEY_COLUMNS + CONTENT_COLUMNS

_COLUMN_DDL = {
    "season": "INTEGER",
    "week": "INTEGER",
    "game_played": "INTEGER",
    "fantasy_points_ppr": "REAL",
    **{field: "REAL" for field in UTIL_FIELDS},
}

ROLLING_WINDOWS = (3, 5, 8)

_FINAL = "final"


class OutcomeForwardCaptureConflictError(ValueError):
    """A weekly outcome fact would be mutated (no write performed)."""


class OutcomeForwardCaptureValidationError(ValueError):
    """A stat/util row is malformed or carries a non-finite value (fail-closed)."""


def _finite_or_none(value: Any, *, field: str) -> Optional[float]:
    """Finite float or None; fail loud on wrong-type / non-finite (never silently scored)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OutcomeForwardCaptureValidationError(
            f"{field} must be a real number or None, got {value!r}"
        )
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise OutcomeForwardCaptureValidationError(
            f"{field} must be finite, got {value!r}"
        )
    return fvalue


def week_status(season: int, week: int, *, schedule: dict[str, Any]) -> str:
    """Return ``"finalized"`` only when the INJECTED schedule shows the expected number of
    games for ``(season, week)`` and every one is ``final``. Anything else (missing game,
    postponed/non-final game, no games scheduled) is ``"not_finalized"``. Never inferred from
    stat rows."""
    expected = schedule.get("expected_game_count")
    if not isinstance(expected, int) or expected <= 0:
        return "not_finalized"
    games = [
        game
        for game in (schedule.get("games") or [])
        if game.get("season") == season and game.get("week") == week
    ]
    if len(games) != expected:
        return "not_finalized"
    if any(str(game.get("status") or "").lower() != _FINAL for game in games):
        return "not_finalized"
    return "finalized"


def _util_content_sig(util_row: dict[str, Any]) -> tuple:
    """The realized-util content that defines a util row's identity for in-payload dedupe."""
    return tuple(util_row.get(field) for field in UTIL_FIELDS)


def _util_field(util_row: dict[str, Any], field: str) -> tuple[Optional[float], str]:
    """A realized-util field: present -> (finite value, 'ok'); absent -> (None, 'unavailable')."""
    if field in util_row and util_row[field] is not None:
        return _finite_or_none(util_row[field], field=field), "ok"
    return None, "unavailable"


class OutcomeForwardCaptureStore:
    """Append-only immutable store of weekly realized-outcome facts."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        cols = ",\n    ".join(
            f"{c} {_COLUMN_DDL.get(c, 'TEXT')}" for c in _ALL_COLUMNS
        )
        pk = ", ".join(KEY_COLUMNS)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {TABLE} (\n    {cols},\n    PRIMARY KEY ({pk})\n)"
            )

    # ── write ──
    def ingest_week(
        self,
        season: int,
        week: int,
        *,
        stat_rows: list[dict[str, Any]],
        util_rows: list[dict[str, Any]],
        schedule: dict[str, Any],
    ) -> dict[str, Any]:
        """Ingest one week's facts IFF the injected schedule marks the week finalized.

        Non-finalized -> no-op (no partial-week ingest). Validation (malformed/non-finite)
        fails closed BEFORE any write. Re-ingesting identical content is idempotent; a
        same-key ingest with differing content raises (immutable)."""
        status = week_status(season, week, schedule=schedule)
        if status != "finalized":
            return {
                "week_status": status,
                "rows_written": 0,
                "noop_reason": "week_not_finalized",
            }

        util_by_player_id = self._validated_util_map(util_rows, season, week)
        facts = self._validated_facts(stat_rows, util_by_player_id, season, week)
        if not facts:
            return {
                "week_status": "finalized",
                "rows_written": 0,
                "noop_reason": "empty_week",
            }

        rows_written = self._write(facts)
        return {
            "week_status": "finalized",
            "rows_written": rows_written,
            "noop_reason": None,
        }

    def _assert_aligned(
        self, row: dict[str, Any], season: int, week: int, kind: str
    ) -> None:
        """A row's embedded season/week (when present) must match the ingest args — a
        misaligned row is a caller error and fails closed rather than being stored under the
        wrong key."""
        if row.get("season", season) != season or row.get("week", week) != week:
            raise OutcomeForwardCaptureValidationError(
                f"{kind} row season/week "
                f"{row.get('season')}/{row.get('week')} disagrees with ingest "
                f"{season}/{week}"
            )

    def _validated_util_map(
        self, util_rows: list[dict[str, Any]], season: int, week: int
    ) -> dict[str, dict[str, Any]]:
        """Index util rows by player_id, fail-closed: missing player_id or season/week
        misalignment rejects; a duplicate player with differing util content rejects, an
        identical duplicate collapses (mirrors the FC in-payload guard)."""
        indexed: dict[str, dict[str, Any]] = {}
        for util_row in util_rows:
            player_id = util_row.get("player_id")
            if player_id is None or str(player_id).strip() == "":
                raise OutcomeForwardCaptureValidationError("util row missing player_id")
            self._assert_aligned(util_row, season, week, "util")
            key = str(player_id)
            if key in indexed and _util_content_sig(indexed[key]) != _util_content_sig(
                util_row
            ):
                raise OutcomeForwardCaptureValidationError(
                    f"duplicate util rows for {key!r} with differing content in one payload"
                )
            indexed[key] = util_row  # identical duplicate collapses
        return indexed

    def _validated_facts(
        self,
        stat_rows: list[dict[str, Any]],
        util_by_player_id: dict[str, dict[str, Any]],
        season: int,
        week: int,
    ) -> list[dict[str, Any]]:
        """Build + dedupe weekly facts BEFORE any write: a duplicate ``(season, week,
        gsis_id)`` with differing content rejects; an identical duplicate collapses."""
        deduped: dict[tuple, dict[str, Any]] = {}
        for stat_row in stat_rows:
            fact = self._build_fact(season, week, stat_row, util_by_player_id)
            key = tuple(fact[c] for c in KEY_COLUMNS)
            if key in deduped and tuple(
                deduped[key][c] for c in CONTENT_COLUMNS
            ) != tuple(fact[c] for c in CONTENT_COLUMNS):
                raise OutcomeForwardCaptureValidationError(
                    f"duplicate stat rows for {key} with differing content in one payload"
                )
            deduped[key] = fact  # identical duplicate collapses
        return list(deduped.values())

    def _build_fact(
        self,
        season: int,
        week: int,
        stat_row: dict[str, Any],
        util_by_player_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        player_id = stat_row.get("player_id")
        if player_id is None or str(player_id).strip() == "":
            raise OutcomeForwardCaptureValidationError("stat row missing player_id")
        self._assert_aligned(stat_row, season, week, "stat")
        points = _finite_or_none(
            stat_row.get("fantasy_points_ppr"), field="fantasy_points_ppr"
        )
        game_played = bool(stat_row.get("game_played", points is not None))
        player_status = stat_row.get("player_status") or "active"

        util_row = util_by_player_id.get(str(player_id), {})
        fact: dict[str, Any] = {
            "season": season,
            "week": week,
            "gsis_id": str(player_id),
            "fantasy_points_ppr": points,
            "player_status": player_status,
            "game_played": 1 if game_played else 0,
        }
        for field in UTIL_FIELDS:
            value, field_status = _util_field(util_row, field)
            fact[field] = value
            fact[f"{field}_status"] = field_status
        return fact

    def _write(self, facts: list[dict[str, Any]]) -> int:
        rows_written = 0
        with sqlite3.connect(self.db_path) as conn:
            # Conflict pass first: a single differing fact aborts the whole ingest (no write).
            for fact in facts:
                existing = conn.execute(
                    f"SELECT {', '.join(CONTENT_COLUMNS)} FROM {TABLE} "
                    f"WHERE {' AND '.join(f'{c}=?' for c in KEY_COLUMNS)}",
                    [fact[c] for c in KEY_COLUMNS],
                ).fetchone()
                if existing is not None and tuple(existing) != tuple(
                    fact[c] for c in CONTENT_COLUMNS
                ):
                    raise OutcomeForwardCaptureConflictError(
                        f"immutable outcome conflict for "
                        f"{fact['season']}/{fact['week']}/{fact['gsis_id']}"
                    )
            # Write pass: INSERT OR IGNORE (identical re-ingest is a no-op).
            placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
            cols = ", ".join(_ALL_COLUMNS)
            for fact in facts:
                cur = conn.execute(
                    f"INSERT OR IGNORE INTO {TABLE} ({cols}) VALUES ({placeholders})",
                    [fact[c] for c in _ALL_COLUMNS],
                )
                rows_written += cur.rowcount
        return rows_written

    # ── read ──
    def read_outcomes(self, season: int, gsis_id: str) -> Optional[dict[str, Any]]:
        """Aggregate the immutable weekly facts for one player into an OutcomeRow.

        ``games_played``/PPG count only played weeks; realized-util reflects the latest
        ingested week (fail-closed per field). Returns None when the player has no facts.
        Rolling windows are order-independent (computed over week-ordered played facts)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_ALL_COLUMNS)} FROM {TABLE} "
                "WHERE season=? AND gsis_id=? ORDER BY week",
                [season, gsis_id],
            ).fetchall()
        if not rows:
            return None

        facts = [dict(zip(_ALL_COLUMNS, row)) for row in rows]
        played = [f for f in facts if f["game_played"] == 1]
        played_points = [
            f["fantasy_points_ppr"]
            for f in played
            if f["fantasy_points_ppr"] is not None
        ]
        games_played = len(played)
        ppg_to_date = fmean(played_points) if played_points else None

        outcome: dict[str, Any] = {
            "gsis_id": gsis_id,
            "season": season,
            "games_played": games_played,
            "ppg_to_date": ppg_to_date,
            "player_status": facts[-1]["player_status"],
        }
        for window in ROLLING_WINDOWS:
            recent = [p for p in played_points][-window:]
            outcome[f"ppg_rolling_{window}"] = fmean(recent) if recent else None

        latest = facts[-1]
        for field in UTIL_FIELDS:
            outcome[field] = {
                "value": latest[field],
                "status": latest[f"{field}_status"],
            }
        return outcome
