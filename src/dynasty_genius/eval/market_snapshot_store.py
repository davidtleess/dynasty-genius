"""MarketSnapshotStore — SQLite-backed store for FantasyCalc dynasty value snapshots.

Supports both native daily snapshots (fc_native) and community CSV archive ingestion
(ktc_community_csv, dp_archive). The backtest harness queries this store to retrieve
market rankings aligned to fold snapshot dates.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("app/data/fc_snapshots.db")

_DDL = """
CREATE TABLE IF NOT EXISTS fc_snapshots (
    snapshot_date         TEXT NOT NULL,
    league_settings_hash  TEXT NOT NULL,
    sleeper_id            TEXT NOT NULL,
    value                 INTEGER NOT NULL,
    overall_rank          INTEGER,
    position_rank         INTEGER,
    position              TEXT,
    trend_30day           INTEGER,
    source                TEXT NOT NULL,
    inserted_at           TEXT NOT NULL,
    PRIMARY KEY (snapshot_date, league_settings_hash, sleeper_id)
);
CREATE INDEX IF NOT EXISTS idx_fc_snapshots_date
    ON fc_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_fc_snapshots_sleeper
    ON fc_snapshots(sleeper_id, snapshot_date);
"""


class MarketSnapshotImmutabilityError(RuntimeError):
    """Raised when an append would change an already-recorded snapshot row.

    Forward (fc_native) and point-in-time backfill snapshots are immutable: a
    changed value for an existing (snapshot_date, league_settings_hash, sleeper_id)
    is a corruption signal, not an overwrite.
    """


# Columns whose change for an existing PK constitutes an immutability violation.
_IMMUTABLE_COLS = (
    "value",
    "overall_rank",
    "position_rank",
    "position",
    "trend_30day",
    "source",
)


class MarketSnapshotStore:
    """SQLite-backed store for FantasyCalc snapshots (native + archive).

    Default path: app/data/fc_snapshots.db
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert_snapshots(self, rows: list[dict]) -> int:
        """Insert rows; conflict on primary key → REPLACE. Returns row count after upsert."""
        if not rows:
            return 0
        sql = """
            INSERT OR REPLACE INTO fc_snapshots
                (snapshot_date, league_settings_hash, sleeper_id, value,
                 overall_rank, position_rank, position, trend_30day,
                 source, inserted_at)
            VALUES
                (:snapshot_date, :league_settings_hash, :sleeper_id, :value,
                 :overall_rank, :position_rank, :position, :trend_30day,
                 :source, :inserted_at)
        """
        with self._connect() as conn:
            conn.executemany(sql, rows)
            conn.commit()
        return self._row_count_for_date(rows[0]["snapshot_date"])

    def append_snapshots(self, rows: list[dict]) -> int:
        """Append-only immutable write (W2a). Returns row count for the date.

        Identical same-key re-write is an idempotent no-op; a *changed* value for
        an existing (snapshot_date, league_settings_hash, sleeper_id) raises
        MarketSnapshotImmutabilityError — no silent overwrite (unlike
        upsert_snapshots, which is INSERT OR REPLACE). The whole batch is one
        transaction: a mid-batch conflict rolls back any rows already inserted in
        the same call, so a failed append leaves no partial write.
        """
        if not rows:
            return 0
        insert_sql = """
            INSERT INTO fc_snapshots
                (snapshot_date, league_settings_hash, sleeper_id, value,
                 overall_rank, position_rank, position, trend_30day,
                 source, inserted_at)
            VALUES
                (:snapshot_date, :league_settings_hash, :sleeper_id, :value,
                 :overall_rank, :position_rank, :position, :trend_30day,
                 :source, :inserted_at)
        """
        with self._connect() as conn:
            for r in rows:
                existing = conn.execute(
                    "SELECT value, overall_rank, position_rank, position, "
                    "trend_30day, source FROM fc_snapshots "
                    "WHERE snapshot_date = ? AND league_settings_hash = ? "
                    "AND sleeper_id = ?",
                    (r["snapshot_date"], r["league_settings_hash"], r["sleeper_id"]),
                ).fetchone()
                if existing is not None:
                    if any(existing[c] != r[c] for c in _IMMUTABLE_COLS):
                        raise MarketSnapshotImmutabilityError(
                            "immutable snapshot conflict at "
                            f"{r['snapshot_date']}/{r['sleeper_id']}"
                        )
                    continue  # identical → idempotent no-op
                conn.execute(insert_sql, r)
            conn.commit()
        return self._row_count_for_date(rows[0]["snapshot_date"])

    def _row_count_for_date(self, snapshot_date: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM fc_snapshots WHERE snapshot_date = ?",
                (snapshot_date,),
            )
            return cur.fetchone()[0]

    def get_snapshot(
        self,
        snapshot_date: str,
        position: Optional[str] = None,
    ) -> list[dict]:
        """Return rows for the given date (or nearest within ±7 days).

        Returns [] if no data within the ±7-day window.
        """
        target = date.fromisoformat(snapshot_date)
        actual_date = self._resolve_date(target)
        if actual_date is None:
            return []

        if actual_date != target:
            logger.warning(
                "No snapshot for %s; using nearest available date %s",
                snapshot_date,
                actual_date,
            )

        sql = "SELECT * FROM fc_snapshots WHERE snapshot_date = ?"
        params: list = [str(actual_date)]
        if position is not None:
            sql += " AND position = ?"
            params.append(position)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _resolve_date(self, target: date) -> Optional[date]:
        """Find the closest stored date within ±7 days of target. Returns None if none."""
        window_start = str(target - timedelta(days=7))
        window_end = str(target + timedelta(days=7))
        target_str = str(target)

        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT DISTINCT snapshot_date
                FROM fc_snapshots
                WHERE snapshot_date BETWEEN ? AND ?
                ORDER BY ABS(JULIANDAY(snapshot_date) - JULIANDAY(?))
                LIMIT 1
                """,
                (window_start, window_end, target_str),
            )
            row = cur.fetchone()

        if row is None:
            return None
        return date.fromisoformat(row[0])

    def get_ranked(self, snapshot_date: str, position: str) -> list[dict]:
        """Return rows for position on snapshot_date, sorted by overall_rank ascending."""
        actual_date = self._resolve_date(date.fromisoformat(snapshot_date))
        if actual_date is None:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM fc_snapshots
                WHERE snapshot_date = ? AND position = ?
                ORDER BY overall_rank ASC
                """,
                (str(actual_date), position),
            ).fetchall()
        return [dict(r) for r in rows]

    def has_snapshot(self, snapshot_date: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM fc_snapshots WHERE snapshot_date = ? LIMIT 1",
                (snapshot_date,),
            )
            return cur.fetchone() is not None

    def get_coverage(self) -> dict:
        """Return summary of what's in the store."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    MIN(snapshot_date) AS earliest_date,
                    MAX(snapshot_date) AS latest_date,
                    COUNT(DISTINCT snapshot_date) AS n_dates,
                    COUNT(*) AS n_rows
                FROM fc_snapshots
                """
            ).fetchone()
            sources = [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT source FROM fc_snapshots"
                ).fetchall()
            ]
        return {
            "earliest_date": row["earliest_date"],
            "latest_date": row["latest_date"],
            "n_dates": row["n_dates"],
            "n_rows": row["n_rows"],
            "sources": sources,
        }
