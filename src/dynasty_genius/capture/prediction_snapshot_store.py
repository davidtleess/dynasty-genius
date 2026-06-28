"""Realized-Outcome Loop T1 — companion prediction-snapshot store.

A companion table on the SAME database as the model-output PIT capture
(``model_forward_capture.db``), keyed to the identical 5-column primary key. It holds
the raw model prediction (``projection_2y``) plus a prediction-time utilization
snapshot — the inputs a later realized-outcome scorer needs — WITHOUT touching the
core ``model_forward_capture_raw`` / ``_joinable`` schema or its immutability/vintage
signature (``_CONTENT_COLUMNS``). The core store stays byte-identical; everything new
lives here.

Append-only and immutable, mirroring ``ModelForwardCaptureStore``: a byte-identical
re-append is an idempotent no-op; a same-key append with differing content raises
(never an upsert/mutation). ``append_snapshot`` accepts an optional shared
``sqlite3.Connection`` so the capture driver can write the core row and this companion
row in ONE transaction (atomic — a companion failure rolls the core write back).

Rollout marker: an absent companion row for a captured core row is classified at the
STORE level via a one-time ``rollout_capture_date`` recorded when this table is first
created. A core row with no companion whose ``capture_date`` precedes the rollout reads
as ``missing_legacy_capture`` (it predates this feature); on/after the rollout it reads
as ``capture_incomplete`` (the companion write should have happened and didn't —
fail-closed). ``decision_supported`` semantics are descriptive only.

Design spec: docs/superpowers/specs/2026-06-27-realized-outcome-loop-design.md (Task 1).
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Optional

TABLE = "model_forward_prediction_snapshot"
META_TABLE = "model_forward_prediction_snapshot_meta"
CORE_RAW_TABLE = "model_forward_capture_raw"

PK_COLUMNS = (
    "capture_date",
    "source",
    "semantic_output_hash",
    "provenance_hash",
    "player_key",
)
CONTENT_COLUMNS = (
    "projection_2y",
    "utilization",
    "prediction_ppg_status",
    "util_snapshot_status",
    "schema_version",
    "source_hash",
)
_ALL_COLUMNS = PK_COLUMNS + CONTENT_COLUMNS
_COLUMN_DDL = {"projection_2y": "REAL", "schema_version": "INTEGER"}

# Canonical utilization fields and their default (position-AGNOSTIC) role. Present fields
# keep the role supplied by the driver (which computes the position-AWARE role from the
# Engine B contract); an ABSENT field is filled on read with this static default so every
# snapshot reads back the full 7-field shape.
#
# Static defaults are the *unconditional* truths only: `snap_share` is a model input for
# every position, so it defaults to `model_input`; the remaining fields are either never a
# model input (`route_participation`, `target_share_nfl`, `air_yards_share` — excluded from
# all position matrices) or only a model input for *some* positions (`weighted_opportunity`,
# `yprr`, `tprr` — WR/TE only). When the field is absent we have no position context, so the
# fail-safe default is `diagnostic_only` (never claim `model_input` without position evidence);
# the driver supplies the correct position-aware role whenever it captures a value.
CANONICAL_UTIL_FIELDS = (
    "snap_share",
    "route_participation",
    "target_share_nfl",
    "air_yards_share",
    "weighted_opportunity",
    "yprr",
    "tprr",
)
CANONICAL_ROLE = {
    "snap_share": "model_input",
    "route_participation": "diagnostic_only",
    "target_share_nfl": "diagnostic_only",
    "air_yards_share": "diagnostic_only",
    "weighted_opportunity": "diagnostic_only",
    "yprr": "diagnostic_only",
    "tprr": "diagnostic_only",
}


class PredictionSnapshotConflictError(ValueError):
    """A companion snapshot would be mutated (no write performed)."""


def _finite_or_none(value: object, *, field: str) -> Optional[float]:
    """Return a finite float (or None). Fail loud on wrong-type / non-finite."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a real number or None, got {value!r}")
    fvalue = float(value)
    if not math.isfinite(fvalue):
        raise ValueError(f"{field} must be finite, got {value!r}")
    return fvalue


def _canon_utilization(utilization: Any) -> str:
    """Validate util values fail-closed and return a canonical JSON string for storage."""
    util = utilization or {}
    if not isinstance(util, dict):
        raise TypeError(f"utilization must be a mapping, got {type(util)!r}")
    cleaned: dict[str, dict] = {}
    for field, obj in util.items():
        if not isinstance(obj, dict):
            raise TypeError(f"utilization[{field!r}] must be a mapping, got {obj!r}")
        value = _finite_or_none(obj.get("value"), field=f"utilization[{field!r}].value")
        role = obj.get("role")
        cleaned[field] = {"value": value, "role": role}
    return json.dumps(cleaned, sort_keys=True)


def _normalize_utilization(util_json: Optional[str]) -> dict[str, dict]:
    """Parse stored JSON and fill the full canonical field set (absent -> None + role)."""
    stored = json.loads(util_json) if util_json else {}
    out: dict[str, dict] = {}
    for field in CANONICAL_UTIL_FIELDS:
        if field in stored:
            out[field] = {
                "value": stored[field].get("value"),
                "role": stored[field].get("role"),
            }
        else:
            out[field] = {"value": None, "role": CANONICAL_ROLE[field]}
    return out


class PredictionSnapshotStore:
    """Append-only, immutable companion store for prediction snapshots."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        cols = ",\n    ".join(
            f"{c} {_COLUMN_DDL.get(c, 'TEXT')}" for c in _ALL_COLUMNS
        )
        pk = ", ".join(PK_COLUMNS)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {TABLE} (\n    {cols},\n    PRIMARY KEY ({pk})\n)"
            )
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {META_TABLE} "
                "(key TEXT PRIMARY KEY, value TEXT)"
            )
            # one-time rollout marker: the date this companion feature went live
            conn.execute(
                f"INSERT OR IGNORE INTO {META_TABLE} (key, value) VALUES "
                "('rollout_capture_date', ?)",
                [date.today().isoformat()],
            )

    # ── write ──
    def append_snapshot(self, row: dict[str, Any], *, conn: Optional[sqlite3.Connection] = None) -> None:
        """Validate fail-closed, then immutably append (idempotent; conflict -> raise).

        ``conn``: when provided, write on the caller's connection WITHOUT committing, so
        the driver can make the core + companion writes one atomic transaction. When None,
        open and commit an own connection.
        """
        for col in PK_COLUMNS:
            value = row.get(col)
            if value is None or str(value).strip() == "":
                raise ValueError(f"prediction snapshot needs a complete key (missing {col})")
        projection_2y = _finite_or_none(row.get("projection_2y"), field="projection_2y")
        util_json = _canon_utilization(row.get("utilization"))
        record = {
            **{c: row.get(c) for c in PK_COLUMNS},
            "projection_2y": projection_2y,
            "utilization": util_json,
            "prediction_ppg_status": row.get("prediction_ppg_status"),
            "util_snapshot_status": row.get("util_snapshot_status"),
            "schema_version": row.get("schema_version"),
            "source_hash": row.get("source_hash"),
        }
        if conn is not None:
            self._write(conn, record)
        else:
            with sqlite3.connect(self.db_path) as own:
                self._write(own, record)

    def _write(self, conn: sqlite3.Connection, record: dict[str, Any]) -> None:
        existing = conn.execute(
            f"SELECT {', '.join(CONTENT_COLUMNS)} FROM {TABLE} "
            f"WHERE {' AND '.join(f'{c}=?' for c in PK_COLUMNS)}",
            [record[c] for c in PK_COLUMNS],
        ).fetchone()
        if existing is not None:
            incoming = tuple(record[c] for c in CONTENT_COLUMNS)
            if tuple(existing) != incoming:
                raise PredictionSnapshotConflictError(
                    f"immutable prediction snapshot conflict for {record['player_key']}"
                )
            return  # idempotent no-op
        placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
        cols = ", ".join(_ALL_COLUMNS)
        conn.execute(
            f"INSERT OR IGNORE INTO {TABLE} ({cols}) VALUES ({placeholders})",
            [record[c] for c in _ALL_COLUMNS],
        )

    # ── read ──
    def _rollout_capture_date(self, conn: sqlite3.Connection) -> Optional[str]:
        row = conn.execute(
            f"SELECT value FROM {META_TABLE} WHERE key='rollout_capture_date'"
        ).fetchone()
        return row[0] if row else None

    def read_snapshot(self, pk: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Return the companion snapshot for ``pk``.

        - companion row present -> the stored snapshot (utilization normalized to the full
          canonical 7-field shape).
        - no companion row but the core capture row exists -> a synthesized record with
          ``projection_2y=None`` and a rollout-classified ``prediction_ppg_status``
          (``missing_legacy_capture`` before rollout / ``capture_incomplete`` on-after).
        - neither -> ``None``.
        """
        with sqlite3.connect(self.db_path) as conn:
            found = conn.execute(
                f"SELECT {', '.join(_ALL_COLUMNS)} FROM {TABLE} "
                f"WHERE {' AND '.join(f'{c}=?' for c in PK_COLUMNS)}",
                [pk[c] for c in PK_COLUMNS],
            ).fetchone()
            if found is not None:
                record = dict(zip(_ALL_COLUMNS, found))
                record["utilization"] = _normalize_utilization(record["utilization"])
                return record

            core = conn.execute(
                f"SELECT 1 FROM {CORE_RAW_TABLE} "
                f"WHERE {' AND '.join(f'{c}=?' for c in PK_COLUMNS)} LIMIT 1",
                [pk[c] for c in PK_COLUMNS],
            ).fetchone()
            if core is None:
                return None
            rollout = self._rollout_capture_date(conn)

        before_rollout = rollout is None or str(pk["capture_date"]) < str(rollout)
        status = "missing_legacy_capture" if before_rollout else "capture_incomplete"
        return {
            **{c: pk[c] for c in PK_COLUMNS},
            "projection_2y": None,
            "utilization": _normalize_utilization(None),
            "prediction_ppg_status": status,
            "util_snapshot_status": "unavailable",
            "schema_version": None,
            "source_hash": None,
        }
