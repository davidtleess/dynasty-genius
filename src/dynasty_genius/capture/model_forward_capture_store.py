"""Dual Daily PIT Capture — model-output forward-capture T1 store (storage layer).

A dedicated, append-only, point-in-time store for our own model outputs (PVO/DVS/
xVAR), parallel to (and isolated from) the FantasyCalc market store. Storage/schema
only: it does NOT read PVO artifacts, resolve provenance, compute semantic hashes,
refresh PVO, or write capture reports — those belong to T2+.

Vintage is defined by ``semantic_output_hash`` + ``provenance_hash`` (Codex 3-hash
model); the volatile ``artifact_sha256`` is deliberately NOT a schema/key column.

- ``model_forward_capture_raw``: survivorship-complete — every artifact row, including
  identity-unresolved and non-model (``PRE_MODEL``/``INACTIVE``/…) rows.
- ``model_forward_capture_joinable``: model-supported (``engine_path`` in
  {ENGINE_A, ENGINE_B, BLEND_AB}) AND Sleeper-keyed rows, for the future divergence join.

Design spec: docs/superpowers/specs/2026-06-24-model-output-forward-capture-brick-design.md
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

MODEL_PVO_SOURCE = "model_pvo"
MODEL_SUPPORTED_ENGINE_PATHS = frozenset({"ENGINE_A", "ENGINE_B", "BLEND_AB"})

_KEY_COLUMNS = (
    "capture_date",
    "source",
    "semantic_output_hash",
    "provenance_hash",
    "player_key",
)
_DATA_COLUMNS = (
    "sleeper_id",
    "dg_player_id",
    "player_name",
    "position",
    "engine_path",
    "dynasty_value_score",
    "dvs_pct",
    "xvar",
    "model_grade",
    "model_version",
    "artifact_vintage",
    "row_index",
    "semantic_row_hash",
    "payload_hash",
)
_ALL_COLUMNS = _KEY_COLUMNS + _DATA_COLUMNS
_COLUMN_DDL = {
    "row_index": "INTEGER",
    "dynasty_value_score": "REAL",
    "dvs_pct": "REAL",
    "xvar": "REAL",
}


class ModelForwardCaptureValidationError(ValueError):
    """A batch violates a fail-closed precondition (no write performed)."""


class ModelForwardCaptureConflictError(ValueError):
    """An immutable snapshot would be mutated (no write performed)."""


def _clean(value: object) -> Optional[str]:
    """Return a non-blank stripped string, or None for None/blank."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_model_player_key(
    row: dict,
    *,
    semantic_output_hash: str,
    row_index: int,
    semantic_row_hash: str,
) -> str:
    """Stable per-row key: sleeper -> dg -> unresolved (semantic hashes, never artifact).

    A Sleeper id is used only when present, non-blank, and not the pseudo-id ``'0'``.
    The unresolved fallback uses the STABLE ``semantic_output_hash``/``semantic_row_hash``
    (never the volatile ``artifact_sha256``), so an unresolved row keeps the same key
    across same-content re-runs.
    """
    identity_ids = row.get("identity_ids") or {}
    for candidate in (identity_ids.get("sleeper_id"), row.get("sleeper_player_id")):
        cleaned = _clean(candidate)
        if cleaned is not None and cleaned != "0":
            return f"sleeper:{cleaned}"
    dg = _clean(row.get("dg_player_id"))
    if dg is not None:
        return f"dg:{dg}"
    return f"unresolved:{semantic_output_hash}:{row_index}:{semantic_row_hash}"


def _is_joinable(entry: dict) -> bool:
    return (
        entry.get("engine_path") in MODEL_SUPPORTED_ENGINE_PATHS
        and str(entry.get("player_key", "")).startswith("sleeper:")
    )


def _create_table(conn: sqlite3.Connection, name: str) -> None:
    cols = ",\n    ".join(
        f"{c} {_COLUMN_DDL.get(c, 'TEXT')}" for c in _ALL_COLUMNS
    )
    pk = ", ".join(_KEY_COLUMNS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {name} (\n    {cols},\n    PRIMARY KEY ({pk})\n)")


class ModelForwardCaptureStore:
    """Append-only, immutable, survivorship-complete model-output PIT store."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            _create_table(conn, "model_forward_capture_raw")
            _create_table(conn, "model_forward_capture_joinable")

    def assert_single_source_family(self, source: str) -> None:
        """This is the model-output namespace; reject any other family."""
        if source != MODEL_PVO_SOURCE:
            raise ModelForwardCaptureValidationError(
                f"model-output namespace accepts only {MODEL_PVO_SOURCE!r}, got {source!r}"
            )

    def append_entries(self, entries: list[dict]) -> dict[str, int]:
        """Validate fail-closed, then append. Returns distinct raw/joinable counts.

        Idempotent on byte-identical re-append; a changed value at an existing key
        raises ``ModelForwardCaptureConflictError``; an in-batch duplicate player_key
        with differing content raises ``ModelForwardCaptureValidationError``.
        """
        # 1. every entry needs a stable player_key + a complete composite key
        # (SQLite composite PKs admit NULLs, so reject blank/None key fields fail-closed
        # before any write — otherwise the PIT immutability key is weakened).
        for entry in entries:
            if not _clean(entry.get("player_key")):
                raise ModelForwardCaptureValidationError(
                    "every entry needs a stable player_key"
                )
            for col in ("capture_date", "semantic_output_hash", "provenance_hash"):
                if not _clean(entry.get(col)):
                    raise ModelForwardCaptureValidationError(
                        f"every entry needs a complete composite key (missing/blank {col})"
                    )

        # 2. single source family, and it must be this namespace
        sources = {entry.get("source") for entry in entries}
        if len(sources) > 1:
            raise ModelForwardCaptureValidationError(
                "batch must be a single source family"
            )
        only_source = next(iter(sources)) if sources else None
        if only_source != MODEL_PVO_SOURCE:
            raise ModelForwardCaptureValidationError(
                f"model-output namespace accepts only {MODEL_PVO_SOURCE!r}, "
                f"got {only_source!r}"
            )

        # 3. collapse byte-identical in-batch duplicates; conflict on differing content
        distinct: dict[str, dict] = {}
        for entry in entries:
            key = entry["player_key"]
            signature = tuple(entry.get(col) for col in _ALL_COLUMNS)
            if key in distinct:
                if tuple(distinct[key].get(col) for col in _ALL_COLUMNS) != signature:
                    raise ModelForwardCaptureValidationError(
                        f"duplicate player_key with differing content: {key}"
                    )
                continue
            distinct[key] = entry

        # 4. conflict check vs existing immutable rows (before any write)
        with sqlite3.connect(self.db_path) as conn:
            for entry in distinct.values():
                row = conn.execute(
                    f"SELECT {', '.join(_DATA_COLUMNS)} FROM model_forward_capture_raw "
                    f"WHERE {' AND '.join(f'{c}=?' for c in _KEY_COLUMNS)}",
                    [entry.get(c) for c in _KEY_COLUMNS],
                ).fetchone()
                if row is not None:
                    existing = tuple(row)
                    incoming = tuple(entry.get(c) for c in _DATA_COLUMNS)
                    if existing != incoming:
                        raise ModelForwardCaptureConflictError(
                            f"immutable snapshot conflict for {entry['player_key']}"
                        )

            # 5. write (idempotent INSERT OR IGNORE)
            raw_written = 0
            joinable_written = 0
            placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
            cols = ", ".join(_ALL_COLUMNS)
            for entry in distinct.values():
                values = [entry.get(c) for c in _ALL_COLUMNS]
                conn.execute(
                    f"INSERT OR IGNORE INTO model_forward_capture_raw ({cols}) "
                    f"VALUES ({placeholders})",
                    values,
                )
                raw_written += 1
                if _is_joinable(entry):
                    conn.execute(
                        f"INSERT OR IGNORE INTO model_forward_capture_joinable ({cols}) "
                        f"VALUES ({placeholders})",
                        values,
                    )
                    joinable_written += 1
        return {"raw_rows_written": raw_written, "joinable_rows_written": joinable_written}

    def _get(
        self,
        table: str,
        capture_date: str,
        source: str,
        semantic_output_hash: str,
        provenance_hash: str,
    ) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_ALL_COLUMNS)} FROM {table} "
                "WHERE capture_date=? AND source=? AND semantic_output_hash=? "
                "AND provenance_hash=?",
                [capture_date, source, semantic_output_hash, provenance_hash],
            ).fetchall()
        return [dict(zip(_ALL_COLUMNS, row)) for row in rows]

    def get_raw_entries(
        self,
        capture_date: str,
        source: str,
        semantic_output_hash: str,
        provenance_hash: str,
    ) -> list[dict[str, Any]]:
        return self._get(
            "model_forward_capture_raw",
            capture_date,
            source,
            semantic_output_hash,
            provenance_hash,
        )

    def get_joinable_entries(
        self,
        capture_date: str,
        source: str,
        semantic_output_hash: str,
        provenance_hash: str,
    ) -> list[dict[str, Any]]:
        return self._get(
            "model_forward_capture_joinable",
            capture_date,
            source,
            semantic_output_hash,
            provenance_hash,
        )
