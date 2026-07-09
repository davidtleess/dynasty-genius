"""Dual Daily PIT Capture — FantasyCalc forward-capture store (T1, storage layer).

A dedicated, source-aware, append-only point-in-time store for the FantasyCalc
daily forward-capture (War Room roadmap #1, first brick). Storage/schema only —
the HTTP client, retry policy, scheduler, and capture-report writer live in T2/T3.

Design spec: docs/superpowers/specs/2026-06-24-dual-daily-pit-capture-fc-first-brick-design.md

Survivorship-complete by construction: EVERY returned row is persisted in the
raw sidecar (`fc_forward_capture_raw`, nullable `sleeper_id`); the Sleeper-keyed
resolved view (`fc_forward_capture_joinable`) holds only rows with a Sleeper id.
A no-`sleeperId` row is stored and counted, never dropped and never aborts the
archive. Snapshots are immutable (a changed value for an existing key conflicts),
and the namespace is source-aware (no legacy `fc_snapshots` INSERT-OR-REPLACE path).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

FC_SOURCE = "fc_native"

# Stored columns (the raw sidecar is the survivorship-complete record).
_COLUMNS = (
    "snapshot_date",
    "source",
    "settings_hash",
    "player_key",
    "sleeper_id",
    "player_name",
    "position",
    "value",
    "overall_rank",
    "position_rank",
    "trend_30day",
    "retrieved_at",
    "payload_hash",
    # Phase-0b: volatility is captured forward. `market_volatility_status` distinguishes
    # a value we stored, a value FantasyCalc never published, and a row that predates the
    # schema. A bare NULL cannot tell those apart, and a silent null is the defect.
    "market_volatility",
    "market_volatility_status",
)
_KEY_COLUMNS = ("snapshot_date", "source", "settings_hash", "player_key")
_REAL_COLUMNS = ("market_volatility",)
_INTEGER_COLUMNS = ("value", "overall_rank", "position_rank", "trend_30day")

# Phase-0b volatility fidelity enum. `structurally_unavailable` is reserved for rows
# written before the volatility schema landed; it can never be backfilled, because the
# immutable-snapshot rule rejects re-capturing an existing date with differing content.
VOLATILITY_STATUS_CAPTURED = "captured"
VOLATILITY_STATUS_SOURCE_OMITTED = "source_omitted"
VOLATILITY_STATUS_STRUCTURALLY_UNAVAILABLE = "structurally_unavailable"
VOLATILITY_STATUSES = frozenset(
    {
        VOLATILITY_STATUS_CAPTURED,
        VOLATILITY_STATUS_SOURCE_OMITTED,
        VOLATILITY_STATUS_STRUCTURALLY_UNAVAILABLE,
    }
)
# Immutable content signature = every stored field EXCEPT retrieved_at (the run
# timestamp may differ on a same-day re-run and must not, by itself, conflict).
# A changed value with a stale/identical payload_hash still conflicts (Codex).
_CONTENT_COLUMNS = tuple(c for c in _COLUMNS if c != "retrieved_at")


def _content_sig(entry: dict) -> tuple:
    """Immutable content signature for an entry (excludes `retrieved_at`)."""
    return tuple(entry.get(c) for c in _CONTENT_COLUMNS)


class FCForwardCaptureValidationError(Exception):
    """Fail-closed validation error (raised before any write)."""


class FCForwardCaptureConflictError(Exception):
    """An immutable snapshot would be mutated — the append is rejected."""


class FCForwardCaptureStore:
    """SQLite-backed dedicated FC forward-capture store."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── schema ────────────────────────────────────────────────────────────
    @staticmethod
    def _sql_type(column: str) -> str:
        if column in _INTEGER_COLUMNS:
            return "INTEGER"
        if column in _REAL_COLUMNS:
            return "REAL"
        return "TEXT"

    def _init_schema(self) -> None:
        cols = ",\n    ".join(f"{c} {self._sql_type(c)}" for c in _COLUMNS)
        pk = ", ".join(_KEY_COLUMNS)
        with sqlite3.connect(self.db_path) as conn:
            for table in ("fc_forward_capture_raw", "fc_forward_capture_joinable"):
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} (\n    {cols},\n    PRIMARY KEY ({pk})\n)"
                )
                self._migrate_add_missing_columns(conn, table)

    def _migrate_add_missing_columns(self, conn: sqlite3.Connection, table: str) -> None:
        """Additive-only migration for pre-Phase-0b stores.

        Existing rows keep NULL volatility. They are NOT `source_omitted` — nobody asked
        FantasyCalc for a value we then failed to get. Consumers must read a NULL status on
        a pre-migration row as `structurally_unavailable`; see `run_market_divergence_refresh`.
        Backfilling a value here is impossible by design: it would mutate an immutable snapshot.
        """
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column in _COLUMNS:
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {self._sql_type(column)}"
                )

    # ── source-family guard ───────────────────────────────────────────────
    def assert_single_source_family(self, source: str) -> None:
        """This is the FantasyCalc-native namespace; reject any other family."""
        if source != FC_SOURCE:
            raise FCForwardCaptureValidationError(
                f"FC forward-capture namespace accepts only {FC_SOURCE!r}, got {source!r}"
            )

    # ── append ────────────────────────────────────────────────────────────
    def append_entries(self, entries: list[dict]) -> dict[str, int]:
        """Append a day's capture. Survivorship-complete + immutable + idempotent.

        Returns counts of distinct entries processed: `raw_entries_written` (all)
        and `joinable_rows_written` (those with a Sleeper id). Re-appending an
        identical snapshot is a no-op that returns the same counts. Any validation
        failure or immutable-snapshot conflict raises BEFORE writing anything."""
        # 1. Validation pass — fail closed, no writes.
        for entry in entries:
            if not str(entry.get("player_key") or "").strip():
                raise FCForwardCaptureValidationError(
                    "entry missing a stable player_key (fail-closed before write)"
                )
            status = entry.get("market_volatility_status")
            if status not in VOLATILITY_STATUSES:
                raise FCForwardCaptureValidationError(
                    f"market_volatility_status must be one of {sorted(VOLATILITY_STATUSES)}, "
                    f"got {status!r} for player_key {entry.get('player_key')!r} "
                    "(fail-closed before write)"
                )
        sources = {e["source"] for e in entries}
        if len(sources) > 1:
            raise FCForwardCaptureValidationError(
                f"single source family required per series, got {sorted(sources)}"
            )
        if sources:
            # The batch's single source must be this FC namespace's family (Codex):
            # a pure non-fc_native batch is rejected, not just a mixed one.
            self.assert_single_source_family(next(iter(sources)))

        # 2. In-payload de-dup: identical duplicates collapse; differing ones fail.
        deduped: dict[str, dict] = {}
        for entry in entries:
            key = entry["player_key"]
            existing = deduped.get(key)
            if existing is None:
                deduped[key] = entry
            elif _content_sig(existing) != _content_sig(entry):
                raise FCForwardCaptureValidationError(
                    f"duplicate player_key {key!r} with differing content in one payload"
                )
            # else: byte-identical duplicate — collapse (already stored).

        ordered = list(deduped.values())

        # 3. Immutable-snapshot conflict check vs the store — still no writes.
        #    Compares the full content signature (not payload_hash alone), so a
        #    changed value with a stale/identical hash still conflicts.
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for entry in ordered:
                row = conn.execute(
                    f"SELECT {', '.join(_CONTENT_COLUMNS)} FROM fc_forward_capture_raw "
                    "WHERE snapshot_date=? AND source=? AND settings_hash=? AND player_key=?",
                    (entry["snapshot_date"], entry["source"], entry["settings_hash"], entry["player_key"]),
                ).fetchone()
                if row is not None and tuple(row[c] for c in _CONTENT_COLUMNS) != _content_sig(entry):
                    raise FCForwardCaptureConflictError(
                        f"immutable snapshot conflict for player_key {entry['player_key']!r} "
                        f"on {entry['snapshot_date']}"
                    )

            # 4. Write (all-or-nothing): new keys insert; identical keys are no-ops.
            raw_written = 0
            joinable_written = 0
            for entry in ordered:
                values = tuple(entry.get(c) for c in _COLUMNS)
                placeholders = ", ".join("?" for _ in _COLUMNS)
                cols = ", ".join(_COLUMNS)
                conn.execute(
                    f"INSERT OR IGNORE INTO fc_forward_capture_raw ({cols}) VALUES ({placeholders})",
                    values,
                )
                raw_written += 1
                if entry.get("sleeper_id") is not None:
                    conn.execute(
                        f"INSERT OR IGNORE INTO fc_forward_capture_joinable ({cols}) VALUES ({placeholders})",
                        values,
                    )
                    joinable_written += 1

        return {"raw_entries_written": raw_written, "joinable_rows_written": joinable_written}

    # ── reads ─────────────────────────────────────────────────────────────
    def _fetch(self, table: str, snapshot_date: str, source: str, settings_hash: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM {table} "
                "WHERE snapshot_date=? AND source=? AND settings_hash=? ORDER BY rowid",
                (snapshot_date, source, settings_hash),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_raw_entries(
        self, snapshot_date: str, source: str, settings_hash: str
    ) -> list[dict[str, Any]]:
        """Every captured row for the key (survivorship-complete; nullable sleeper_id)."""
        return self._fetch("fc_forward_capture_raw", snapshot_date, source, settings_hash)

    def get_joinable_entries(
        self, snapshot_date: str, source: str, settings_hash: str
    ) -> list[dict[str, Any]]:
        """The Sleeper-keyed resolved view (rows with a sleeper_id)."""
        return self._fetch("fc_forward_capture_joinable", snapshot_date, source, settings_hash)
