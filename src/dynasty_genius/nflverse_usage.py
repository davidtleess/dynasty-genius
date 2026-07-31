"""nflverse usage ingestion — Next Gen Stats and snap counts.

Layer 1. Two streams David named that we already had installed and had **never once called**:
``nflreadpy.load_nextgen_stats`` and ``nflreadpy.load_snap_counts``. Free, no credential, already
a daily dependency. Fetch, snapshot, resolve identity, store durably. Nothing downstream reads it
yet — no model input, no surface, no scoring.

Callable, never self-scheduling. A scheduler is a separate decision and a separate word.

**This module is deliberately the same shape as ``league_transactions.py``**, which was proven
against live data the same night: raw snapshot before parsing, canonical identity with a
never-rounded outcome, a content-addressed store whose idempotence is provable by bytes, a status
marker written before any fetch, and failures that name themselves. It is a repetition of a working
pattern, not a new framework — four stream specs and one capture function.

Shape facts measured from the live source (2026-07-30), each of which the code must survive:

- NGS keys on ``player_gsis_id``, which **is** our canonical id — so NGS needs no bridge.
- Snap counts key on ``pfr_player_id``, which does not, and needs the governed crosswalk's
  ``pfr_id -> gsis_id`` bridge (7,774 of 7,952 entries carry both).
- **That bridge is not clean.** Three PFR ids each map to two different players in the governed
  crosswalk (``CartKy01`` -> Kyle Carter *and* David Morgan; ``HarrAl00``; ``MillSt00``). A bridge
  that silently picks one would attach real snap counts to the wrong player. Those resolve to
  ``conflict`` and are counted separately — see ``IdentityIndex``.
- NGS ``week`` includes ``0``, which is the season aggregate rather than a real week. It is stored
  as-is and labelled, never mistaken for week one.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA_VERSION = "nflverse_usage.v2"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _REPO_ROOT / "app" / "data" / "nflverse_usage.db"
DEFAULT_RAW_ROOT = _REPO_ROOT / "app" / "data" / "nflverse_usage"
GOVERNED_CROSSWALK = (
    _REPO_ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json"
)

#: Identity outcomes. Four-valued, and the extra value is the point: a source id that maps to two
#: different players is NOT the same thing as one that maps to none, and neither is "resolved".
CANONICAL_RESOLVED = "canonical_resolved"
SOURCE_ONLY = "source_only"
CONFLICT = "conflict"
UNKNOWN = "unknown"


class UsageCaptureError(RuntimeError):
    """The capture refuses rather than publishing something untrustworthy."""


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityIndex:
    """Resolves a source player id to the Dynasty Genius canonical id.

    Our canonical id is the GSIS id, so a GSIS-keyed stream resolves by membership and a
    PFR-keyed stream resolves through the governed crosswalk's bridge.

    **Conflicts are held, not resolved.** ``pfr_conflicts`` carries every PFR id the crosswalk
    maps to more than one GSIS id. Resolving one by picking the first row would silently attach a
    real player's snaps to a different player, which is worse than not having the row at all.
    """

    gsis_ids: frozenset[str]
    pfr_to_gsis: Mapping[str, str]
    pfr_conflicts: Mapping[str, tuple[str, ...]]
    names_by_gsis: Mapping[str, str]

    @classmethod
    def from_governed_crosswalk(cls, path: Path = GOVERNED_CROSSWALK) -> "IdentityIndex":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = payload.get("entries") or []
        if not entries:
            raise UsageCaptureError(
                f"governed_crosswalk_empty: {path} carries no entries — refusing to resolve "
                "identity against an empty universe"
            )

        gsis: set[str] = set()
        names: dict[str, str] = {}
        by_pfr: dict[str, set[str]] = {}
        for row in entries:
            gsis_id = str(row.get("gsis_id") or "").strip()
            if not gsis_id:
                continue
            gsis.add(gsis_id)
            if row.get("name"):
                names[gsis_id] = str(row["name"])
            pfr_id = str(row.get("pfr_id") or "").strip()
            if pfr_id:
                by_pfr.setdefault(pfr_id, set()).add(gsis_id)

        bridge = {k: next(iter(v)) for k, v in by_pfr.items() if len(v) == 1}
        conflicts = {k: tuple(sorted(v)) for k, v in by_pfr.items() if len(v) > 1}
        return cls(
            gsis_ids=frozenset(gsis),
            pfr_to_gsis=bridge,
            pfr_conflicts=conflicts,
            names_by_gsis=names,
        )

    def resolve(self, source_id: Any, *, kind: str) -> tuple[str | None, str]:
        """Returns ``(dg_player_id, identity_status)``. Never raises, never guesses."""
        key = str(source_id or "").strip()
        if not key:
            return None, UNKNOWN

        if kind == "gsis":
            if key in self.gsis_ids:
                return key, CANONICAL_RESOLVED
            # A real GSIS id the governed universe does not carry: attributable, not canonical.
            return None, SOURCE_ONLY

        if kind == "pfr":
            if key in self.pfr_conflicts:
                return None, CONFLICT
            resolved = self.pfr_to_gsis.get(key)
            if resolved is not None:
                return resolved, CANONICAL_RESOLVED
            return None, SOURCE_ONLY

        raise UsageCaptureError(f"unknown identity kind: {kind!r}")


# ---------------------------------------------------------------------------
# Stream specifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamSpec:
    """One nflverse stream: how to load it, how to key it, what to keep."""

    name: str
    table: str
    identity_column: str
    identity_kind: str
    grain: tuple[str, ...]
    columns: tuple[str, ...]
    loader: Callable[..., Any]
    loader_kwargs: Mapping[str, Any]

    @property
    def stored_columns(self) -> tuple[str, ...]:
        return (*self.columns, "dg_player_id", "identity_status", "row_key", "season_ingested")


_NGS_SHARED = (
    "season",
    "season_type",
    "week",
    "player_gsis_id",
    "player_display_name",
    "player_position",
    "team_abbr",
)

NGS_PASSING = StreamSpec(
    name="ngs_passing",
    table="ngs_passing",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "avg_time_to_throw",
        "avg_completed_air_yards",
        "avg_intended_air_yards",
        "avg_air_yards_differential",
        "aggressiveness",
        "max_completed_air_distance",
        "avg_air_yards_to_sticks",
        "attempts",
        "pass_yards",
        "pass_touchdowns",
        "interceptions",
        "passer_rating",
        "completions",
        "completion_percentage",
        "expected_completion_percentage",
        "completion_percentage_above_expectation",
        "avg_air_distance",
        "max_air_distance",
    ),
    loader=None,  # bound at runtime; see build_streams
    loader_kwargs={"stat_type": "passing"},
)

NGS_RUSHING = StreamSpec(
    name="ngs_rushing",
    table="ngs_rushing",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "efficiency",
        "percent_attempts_gte_eight_defenders",
        "avg_time_to_los",
        "rush_attempts",
        "rush_yards",
        "avg_rush_yards",
        "rush_touchdowns",
        "expected_rush_yards",
        "rush_yards_over_expected",
        "rush_yards_over_expected_per_att",
        "rush_pct_over_expected",
    ),
    loader=None,
    loader_kwargs={"stat_type": "rushing"},
)

NGS_RECEIVING = StreamSpec(
    name="ngs_receiving",
    table="ngs_receiving",
    identity_column="player_gsis_id",
    identity_kind="gsis",
    grain=("season", "season_type", "week", "player_gsis_id"),
    columns=(
        *_NGS_SHARED,
        "avg_cushion",
        "avg_separation",
        "avg_intended_air_yards",
        "percent_share_of_intended_air_yards",
        "receptions",
        "targets",
        "catch_percentage",
        "yards",
        "rec_touchdowns",
        "avg_yac",
        "avg_expected_yac",
        "avg_yac_above_expectation",
    ),
    loader=None,
    # Explicit, not defaulted: nflreadpy's `stat_type` defaults to "passing", so an omitted
    # kwarg here silently loaded passing rows under a receiving label. The schema guard caught
    # it on the first live run — which is the guard doing exactly its job.
    loader_kwargs={"stat_type": "receiving"},
)

SNAP_COUNTS = StreamSpec(
    name="snap_counts",
    table="player_snap_count",
    identity_column="pfr_player_id",
    identity_kind="pfr",
    grain=("game_id", "pfr_player_id"),
    columns=(
        "game_id",
        "pfr_game_id",
        "season",
        "game_type",
        "week",
        "player",
        "pfr_player_id",
        "position",
        "team",
        "opponent",
        "offense_snaps",
        "offense_pct",
        "defense_snaps",
        "defense_pct",
        "st_snaps",
        "st_pct",
    ),
    loader=None,
    loader_kwargs={},
)


def build_streams() -> tuple[StreamSpec, ...]:
    """Bind the nflreadpy loaders. Imported lazily so the module stays importable offline."""
    import nflreadpy

    def _bind(spec: StreamSpec, loader: Callable[..., Any]) -> StreamSpec:
        return StreamSpec(
            name=spec.name,
            table=spec.table,
            identity_column=spec.identity_column,
            identity_kind=spec.identity_kind,
            grain=spec.grain,
            columns=spec.columns,
            loader=loader,
            loader_kwargs=spec.loader_kwargs,
        )

    return (
        _bind(NGS_PASSING, nflreadpy.load_nextgen_stats),
        _bind(NGS_RUSHING, nflreadpy.load_nextgen_stats),
        _bind(NGS_RECEIVING, nflreadpy.load_nextgen_stats),
        _bind(SNAP_COUNTS, nflreadpy.load_snap_counts),
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _row_key(spec: StreamSpec, row: Mapping[str, Any]) -> str:
    return "|".join(f"{col}={row.get(col)}" for col in spec.grain)


def normalize_rows(
    records: Sequence[Mapping[str, Any]],
    *,
    spec: StreamSpec,
    season: int,
    identity: IdentityIndex,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach canonical identity and key each row. Returns ``(rows, coverage)``.

    Missing source columns are a **hard** failure, not a silent null: nflverse adding or renaming a
    field must surface as a named refusal rather than a column of empties that looks like real
    absence of data.
    """
    if not records:
        return [], _coverage(spec, season, [], missing_columns=[])

    available = set(records[0].keys())
    missing = [col for col in spec.columns if col not in available]
    if missing:
        raise UsageCaptureError(
            f"nflverse_schema_drift: stream {spec.name} season {season} is missing "
            f"{missing} — the upstream shape changed; storing nulls would look like missing "
            "data rather than a changed contract"
        )

    rows: list[dict[str, Any]] = []
    for record in records:
        dg_player_id, status = identity.resolve(
            record.get(spec.identity_column), kind=spec.identity_kind
        )
        row = {col: record.get(col) for col in spec.columns}
        row["dg_player_id"] = dg_player_id
        row["identity_status"] = status
        row["row_key"] = _row_key(spec, record)
        row["season_ingested"] = str(season)
        rows.append(row)

    keys = [r["row_key"] for r in rows]
    if len(keys) != len(set(keys)):
        duplicates = sorted({k for k in keys if keys.count(k) > 1})[:5]
        raise UsageCaptureError(
            f"nflverse_grain_violation: stream {spec.name} season {season} has duplicate rows at "
            f"its declared grain {spec.grain}; examples {duplicates} — refusing to store a grain "
            "that silently drops rows"
        )

    return rows, _coverage(spec, season, rows, missing_columns=[])


def _coverage(
    spec: StreamSpec,
    season: int,
    rows: Sequence[Mapping[str, Any]],
    *,
    missing_columns: Sequence[str],
) -> dict[str, Any]:
    by_status = {
        status: [r for r in rows if r["identity_status"] == status]
        for status in (CANONICAL_RESOLVED, SOURCE_ONLY, CONFLICT, UNKNOWN)
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "stream": spec.name,
        "season": season,
        "rows_total": len(rows),
        # Four counts, never one. "Not canonically identified" is the sum of the last three and is
        # reported explicitly so no single zero can stand in for identity.
        "rows_canonical_resolved": len(by_status[CANONICAL_RESOLVED]),
        "rows_source_only": len(by_status[SOURCE_ONLY]),
        "rows_conflict": len(by_status[CONFLICT]),
        "rows_unknown": len(by_status[UNKNOWN]),
        "rows_not_canonically_identified": sum(
            len(by_status[s]) for s in (SOURCE_ONLY, CONFLICT, UNKNOWN)
        ),
        "source_only_ids": sorted(
            {str(r[spec.identity_column]) for r in by_status[SOURCE_ONLY]}
        )[:50],
        "conflict_ids": sorted({str(r[spec.identity_column]) for r in by_status[CONFLICT]}),
        "missing_columns": list(missing_columns),
    }


# ---------------------------------------------------------------------------
# Durable store
# ---------------------------------------------------------------------------

#: **A row here means a real successful capture.** That single invariant is the design, and it is
#: Codex's (TW30N integration review), taken over my own richer version because it needs no schema
#: change and cannot lie: a failed retry leaves the last-good row untouched and reports itself in
#: the run marker, and a ``failed`` row is written only when there is no prior success to preserve.
#: ``ingested_at`` on an ``ok`` row is therefore the last-good timestamp — staleness is readable
#: from the store alone without overloading ``status`` with attempt state.
_CAPTURE_COLUMNS = (
    "stream_season",
    "stream",
    "season",
    "status",
    "rows_total",
    "coverage_json",
    "failure_reason",
    "content_hash",
    "ingested_at",
)


def _rows_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = sorted(
        (json.dumps(row, sort_keys=True, default=str) for row in rows),
    )
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


class UsageStore:
    """Content-addressed, reconciling store, one table per stream.

    Idempotence is per ``(stream, season)`` and proven by content: if the season's rows hash to
    what is already stored, **nothing is written** — not a row, not a timestamp. If they differ,
    that season's rows are replaced wholesale, so a row withdrawn upstream cannot survive as a
    phantom.
    """

    def __init__(self, db_path: Path | str, specs: Sequence[StreamSpec]) -> None:
        self.db_path = Path(db_path)
        self.specs = {spec.name: spec for spec in specs}
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS nflverse_capture ("
                + ", ".join(f"{c} TEXT" for c in _CAPTURE_COLUMNS)
                + ", PRIMARY KEY (stream_season))"
            )
            self._assert_schema(conn, "nflverse_capture", _CAPTURE_COLUMNS)
            for spec in specs:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {spec.table} ("
                    + ", ".join(f"{c} TEXT" for c in spec.stored_columns)
                    + ", PRIMARY KEY (row_key))"
                )
                self._assert_schema(conn, spec.table, spec.stored_columns)

    @staticmethod
    def _assert_schema(
        conn: sqlite3.Connection, table: str, expected: Sequence[str]
    ) -> None:
        actual = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        missing = [column for column in expected if column not in actual]
        if missing:
            raise UsageCaptureError(
                f"nflverse_usage_schema_mismatch: {table} is missing {missing} — the store "
                f"predates {SCHEMA_VERSION}; rebuild it from the raw snapshots rather than "
                "writing mixed-schema rows"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def apply_season(
        self,
        spec: StreamSpec,
        *,
        season: int,
        rows: Sequence[Mapping[str, Any]],
        coverage: Mapping[str, Any],
        ingested_at: str,
    ) -> str:
        key = f"{spec.name}:{season}"
        digest = _rows_hash(rows)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT content_hash, status FROM nflverse_capture WHERE stream_season = ?",
                (key,),
            ).fetchone()
            # A `failed` row always carries content_hash NULL, so this branch can only be
            # reached from a real prior success — no recovery special-case is needed.
            if existing is not None and existing["content_hash"] == digest:
                return "unchanged"

            # Reconcile: this season's stored rows become exactly the rows we just fetched.
            conn.execute(
                f"DELETE FROM {spec.table} WHERE season_ingested = ?", (str(season),)
            )
            for row in rows:
                conn.execute(
                    f"INSERT OR REPLACE INTO {spec.table} "
                    f"({', '.join(spec.stored_columns)}) "
                    f"VALUES ({', '.join('?' for _ in spec.stored_columns)})",
                    [row.get(c) for c in spec.stored_columns],
                )
            conn.execute(
                f"INSERT OR REPLACE INTO nflverse_capture ({', '.join(_CAPTURE_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _CAPTURE_COLUMNS)})",
                [
                    key,
                    spec.name,
                    str(season),
                    "ok",
                    len(rows),
                    json.dumps(coverage, sort_keys=True, default=str),
                    None,  # failure_reason — an ok row never carries one
                    digest,
                    ingested_at,
                ],
            )
            return "inserted" if existing is None else "updated"

    def record_failure(
        self, stream: str, season: int, reason: str, ingested_at: str
    ) -> None:
        """Record a failed attempt **without ever disturbing a prior success.**

        My first version overwrote the whole row, wiping ``content_hash`` — so the next good run
        could no longer recognise unchanged content and would rewrite every row, forfeiting the
        idempotence this store exists to prove. Codex's fix, adopted here, is stronger than my
        replacement: rather than teaching the row to hold both states, a successful row is simply
        left alone and the failing attempt is reported by the run marker, which already names the
        stream, the season and the reason. A ``failed`` row is written **only** when there is no
        prior success — so the season is never silently absent, and a row is never a lie.
        """
        try:
            with self._connect() as conn:
                key = f"{stream}:{season}"
                prior = conn.execute(
                    "SELECT status FROM nflverse_capture WHERE stream_season = ?", (key,)
                ).fetchone()
                if prior is not None and prior["status"] == "ok":
                    # Last-good evidence stands. The marker carries this failure.
                    return
                conn.execute(
                    f"INSERT OR REPLACE INTO nflverse_capture ({', '.join(_CAPTURE_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _CAPTURE_COLUMNS)})",
                    [key, stream, str(season), "failed", None, "{}", reason, None, ingested_at],
                )
        except Exception:  # never mask the originating failure
            pass

    def row_count(self, table: str) -> int:
        with self._connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def captures(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM nflverse_capture ORDER BY stream, season DESC"
            ).fetchall()
        out = []
        for row in rows:
            record = dict(row)
            record["coverage"] = json.loads(record.pop("coverage_json") or "{}")
            out.append(record)
        return out

    def content_fingerprint(self) -> str:
        """Hash of every stored DATA row. Identical content, identical bytes.

        Deliberately excludes ``nflverse_capture``: that table is operational history — a
        failure and a later recovery genuinely happened and must move it. Folding it in would
        mean the data-idempotence proof could be broken by a run that changed no data at all.
        """
        chunks: list[str] = []
        with self._connect() as conn:
            for table in sorted(s.table for s in self.specs.values()):
                for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
                    chunks.append(json.dumps(tuple(row), default=str))
        return hashlib.sha256("\n".join(chunks).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Capture orchestration (callable; never self-scheduling)
# ---------------------------------------------------------------------------


def status_marker_path(raw_root: Path = DEFAULT_RAW_ROOT) -> Path:
    return Path(raw_root) / "nflverse_usage_status_latest.json"


def write_raw_snapshot(
    records: Sequence[Mapping[str, Any]],
    *,
    stream: str,
    season: int,
    captured_at: str,
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> Path:
    """Write the raw payload BEFORE parsing (`01` §Source Adapter Rules)."""
    raw_dir = Path(raw_root) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = "".join(ch for ch in captured_at if ch.isalnum())
    path = raw_dir / f"{stream}_{season}_{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "stream": stream,
                "season": season,
                "captured_at": captured_at,
                "rows": len(records),
                "records": list(records),
            },
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _to_records(frame: Any) -> list[dict[str, Any]]:
    """polars or pandas -> list of dicts, without importing either at module scope."""
    if hasattr(frame, "to_dicts"):
        return frame.to_dicts()
    if hasattr(frame, "to_dict"):
        return frame.to_dict(orient="records")
    raise UsageCaptureError(f"unsupported frame type from loader: {type(frame)!r}")


def run_usage_capture(
    *,
    seasons: Sequence[int],
    specs: Sequence[StreamSpec] | None = None,
    identity: IdentityIndex | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    fetch: Callable[[StreamSpec, int], Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Start marker -> per stream-season fetch -> raw snapshot -> normalize -> store -> marker.

    A start record is written before any fetch, so a run that dies mid-flight leaves
    ``status=running`` rather than the previous run's ``status=ok``. A stream-season that raises
    writes ``status=failed`` naming the stream, the season and the stage, then re-raises.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"nflverse-usage-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(raw_root)
    specs = tuple(specs if specs is not None else build_streams())
    seasons = [int(s) for s in seasons]

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "seasons": seasons,
        "streams": [spec.name for spec in specs],
    }
    _atomic_write_json(marker, {**base, "status": "running"})

    def _default_fetch(spec: StreamSpec, season: int) -> Sequence[Mapping[str, Any]]:
        return _to_records(spec.loader(seasons=[season], **dict(spec.loader_kwargs)))

    fetch = fetch or _default_fetch
    store: UsageStore | None = None
    results: list[dict[str, Any]] = []
    stream_name = season = None

    try:
        if identity is None:
            identity = IdentityIndex.from_governed_crosswalk()
        store = UsageStore(db_path, specs)

        for spec in specs:
            for season in seasons:
                stream_name = spec.name
                records = fetch(spec, season)
                raw_path = write_raw_snapshot(
                    records,
                    stream=spec.name,
                    season=season,
                    captured_at=started_at,
                    raw_root=raw_root,
                )
                rows, coverage = normalize_rows(
                    records, spec=spec, season=season, identity=identity
                )
                applied = store.apply_season(
                    spec,
                    season=season,
                    rows=rows,
                    coverage=coverage,
                    ingested_at=started_at,
                )
                results.append(
                    {
                        "stream": spec.name,
                        "season": season,
                        "applied": applied,
                        "raw_snapshot": str(raw_path),
                        "coverage": coverage,
                    }
                )
    except Exception as exc:
        if store is not None and stream_name is not None and season is not None:
            store.record_failure(
                stream_name, season, f"{type(exc).__name__}: {exc}", started_at
            )
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_stream": stream_name,
                "failed_season": season,
                "reason": f"{type(exc).__name__}: {exc}",
                "captured_before_failure": [
                    {"stream": r["stream"], "season": r["season"]} for r in results
                ],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise

    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "results": results,
        "totals": _totals(results),
        "rows_stored": {
            spec.table: store.row_count(spec.table) for spec in specs
        },
        "identity_bridge": {
            "gsis_universe": len(identity.gsis_ids),
            "pfr_bridge_pairs": len(identity.pfr_to_gsis),
            "pfr_conflicts_held": len(identity.pfr_conflicts),
            "pfr_conflict_ids": sorted(identity.pfr_conflicts),
        },
    }
    _atomic_write_json(marker, status)
    return status


def _totals(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Totals that cannot hide a stream-season. Same rule as the transaction chain."""
    blocks = [dict(r["coverage"]) for r in results]
    keys = (
        "rows_total",
        "rows_canonical_resolved",
        "rows_source_only",
        "rows_conflict",
        "rows_unknown",
        "rows_not_canonically_identified",
    )
    return {
        **{k: sum(int(b.get(k) or 0) for b in blocks) for k in keys},
        "stream_seasons": len(blocks),
        "stream_seasons_with_unresolved": sorted(
            f"{b['stream']}:{b['season']}"
            for b in blocks
            if int(b.get("rows_not_canonically_identified") or 0) > 0
        ),
        "by_stream_season": {f"{b['stream']}:{b['season']}": b for b in blocks},
    }


def load_governed_identity() -> IdentityIndex:
    return IdentityIndex.from_governed_crosswalk()
