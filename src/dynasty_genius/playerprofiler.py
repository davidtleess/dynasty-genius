"""PlayerProfiler ingestion — David's paid subscription, finally producing something.

Layer 1. Two streams from the same subscription, both delivered as manual subscriber
exports rather than an API:

- ``player_season``  — the Data Analysis report. 317 columns per player-season across
  QB/RB/WR/TE. Carries ``breakout_age``, ``speed_score`` and ``target_share``, the three
  fields ``SOURCE_REGISTRY`` has declared since it was written and never once received.
- ``medical_history`` — the injury archive, 2017-2023.

**Why this is a manual-export adapter and not a scraper.** The old
``scripts/probe_playerprofiler.py`` posted to an unauthenticated ``wp-admin/admin-ajax.php``
endpoint and returned 874 parse errors out of 874 players; that endpoint now answers HTTP
400 with body ``0``, i.e. the action is no longer registered. It never used David's
credentials at all, so it proved the shadow path was dead — NOT that the subscription was
unusable. The sanctioned path is the product's own export button, so this module ingests
files David downloads. No scripted login, no terms-of-service exposure, no account risk.

**The raw exports are private subscriber data.** They stay outside the repo, the manifest
recording them is gitignored, and this store is gitignored. Only derived features and
content hashes may ever travel.

Shape facts measured from the live exports (2026-07-31), each of which the code survives:

- The data-analysis export carries NO id of any kind — no GSIS, PFR, Sleeper, not even
  PlayerProfiler's own. Identity resolves on name, disambiguated by ``draft_year`` then
  ``college``. Measured across 5,476 player-seasons: 98.3% canonical, 8 conflicts HELD,
  83 unknown.
- The medical export DOES carry ``Player_ID`` — PlayerProfiler's internal key, shaped
  ``JH-4025`` (initials + number), 3,025 distinct over 9,768 rows. It is NOT usable as a
  join key and is deliberately not treated as one: the data-analysis export omits it
  entirely, so it cannot bridge the two streams; 18 rows carry the literal string
  ``#N/A``; and it is not even injective — ``AW-1812`` maps to three different player
  names. It is stored as an ordinary column for provenance and nothing depends on it.
  **The two streams join through the resolved canonical id, not through anything the
  vendor supplies.**
- The two streams cover DIFFERENT player universes. Medical covers all 53 roster spots;
  the crosswalk covers skill positions. Flat medical resolve is 82.4%, but 1,568 of the
  1,723 misses are linemen and defenders that were never in our universe. Over the
  modelled universe it is 98.1%, and the 155 remaining misses are true name collisions
  (``Mike Williams``, ``David Johnson``, ``Adrian Peterson``) which are HELD, never
  guessed. See ``_medical_universe_split``.
- There is NO season column in the medical files' filename-independent content; the
  ``Year`` column carries it, and one 2023 row carries a blank year.
- The medical schema DRIFTS across years, additively: 12 columns in 2017 growing to 17 by
  2023 (``Body Zone`` from 2019, ``Injured Reserve`` from 2020, ``O-D`` from 2021,
  ``Injury Detail`` and ``IR from Previous inj.`` in 2023). Additive drift is safe to
  union; a REMOVED column would not be, so the loader checks and refuses.
- The medical archive STOPS AT 2023. See ``MEDICAL_COVERAGE_END``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "playerprofiler.v1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _REPO_ROOT / "app" / "data" / "playerprofiler.db"
DEFAULT_ROOT = _REPO_ROOT / "app" / "data" / "playerprofiler"
GOVERNED_CROSSWALK = (
    _REPO_ROOT / "app" / "data" / "identity" / "_runs" / "ff_playerids_20260516.json"
)

#: The medical archive's last covered season. PlayerProfiler ships nothing past this
#: (David, 2026-07-31). Everything after it is a BLIND WINDOW, and the danger is that a
#: naive join renders "no record" identically to "was healthy" — which is not missing
#: data, it is a confident wrong answer. Any consumer must read
#: ``medical_blind_window()`` and carry the limit.
MEDICAL_COVERAGE_END = 2023

#: Identity outcomes. Four-valued; the extra value is the point — an id that matches two
#: different players is not the same thing as one that matches none, and neither is
#: "resolved".
CANONICAL_RESOLVED = "canonical_resolved"
SOURCE_ONLY = "source_only"
CONFLICT = "conflict"
UNKNOWN = "unknown"

PLAYER_SEASON_TABLE = "pp_player_season"
MEDICAL_TABLE = "pp_medical_history"

#: Columns present in EVERY medical year, 2017-2023. Drift beyond these is additive and
#: unioned; a missing core column is a contract break and refuses.
MEDICAL_CORE_COLUMNS = (
    "Player", "Player_ID", "Team", "Injury Description", "Body Part", "Severity",
    "Incident Date", "Year", "Games Missed", "Games On Injury Report", "Surgery",
    "Recovery Timetable",
)


class PlayerProfilerError(RuntimeError):
    """The ingest refuses rather than storing something untrustworthy."""


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _q(identifier: str) -> str:
    """Quote a column identifier for SQLite.

    The export carries columns like ``40_yard_dash`` and ``3_cone_drill``. SQLite rejects a
    bare identifier that starts with a digit, so every interpolated column name is quoted
    rather than renamed — keeping the stored column identical to the source column, which
    is what makes the store readable against the vendor's own documentation.
    """
    return '"' + identifier.replace('"', '""') + '"'


def _slug(value: str) -> str:
    """Column name -> safe SQLite identifier. 317 source columns, some with symbols."""
    out = re.sub(r"[^0-9a-zA-Z]+", "_", (value or "").strip()).strip("_").lower()
    return out or "col"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def _norm(value: str) -> str:
    return re.sub(r"[^a-z]", "", (value or "").lower())


def _norm_no_suffix(value: str) -> str:
    value = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", (value or "").lower())
    return re.sub(r"[^a-z]", "", value)


def _norm_college(value: str) -> str:
    value = (value or "").lower().replace("state", "st").replace("university", "").replace("&", "")
    return re.sub(r"[^a-z]", "", value)


@dataclass(frozen=True)
class NameIdentityIndex:
    """Name-based resolution to the canonical GSIS id, disambiguated then held.

    PlayerProfiler ships no id column, so this is the only join available. Name matching
    is exactly how one player's statistics get attached to another, so the design refuses
    to guess: an ambiguity that survives ``draft_year`` and ``college`` is returned as
    ``conflict`` with the candidates named, never resolved to whichever row sorted first.

    The suffix-insensitive pass exists because the two sources disagree about generational
    suffixes in BOTH directions — the export says ``Calvin Austin`` where the crosswalk says
    ``Calvin Austin III``, and ``Efton Chism III`` where the crosswalk says ``Efton Chism``.
    It runs only AFTER the exact pass, and its result is still disambiguated, so it can
    never promote an ambiguous match to a confident one.
    """

    by_exact: Mapping[str, tuple[dict[str, Any], ...]]
    by_no_suffix: Mapping[str, tuple[dict[str, Any], ...]]

    @classmethod
    def from_governed_crosswalk(cls, path: Path = GOVERNED_CROSSWALK) -> "NameIdentityIndex":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = payload.get("entries") or []
        if not entries:
            raise PlayerProfilerError(
                f"governed_crosswalk_empty: {path} carries no entries — refusing to "
                "resolve identity against an empty universe"
            )
        exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
        loose: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in entries:
            if not (row.get("gsis_id") or "").strip():
                continue
            exact[_norm(row.get("name"))].append(row)
            loose[_norm_no_suffix(row.get("name"))].append(row)
        return cls(
            by_exact={k: tuple(v) for k, v in exact.items()},
            by_no_suffix={k: tuple(v) for k, v in loose.items()},
        )

    def resolve(
        self, name: str, *, draft_year: str | None = None, college: str | None = None
    ) -> tuple[str | None, str, tuple[str, ...]]:
        """Returns ``(dg_player_id, identity_status, candidates)``. Never guesses."""
        for table, key in ((self.by_exact, _norm), (self.by_no_suffix, _norm_no_suffix)):
            found = table.get(key(name), ())
            if not found:
                continue
            if len(found) == 1:
                return found[0]["gsis_id"], CANONICAL_RESOLVED, ()
            narrowed = [
                row for row in found
                if str(row.get("draft_year") or "") == str(draft_year or "").strip()
            ] or list(found)
            if len(narrowed) == 1:
                return narrowed[0]["gsis_id"], CANONICAL_RESOLVED, ()
            wanted = _norm_college(college)
            narrowed2 = [
                row for row in narrowed if _norm_college(row.get("college")) == wanted
            ] or narrowed
            if len(narrowed2) == 1:
                return narrowed2[0]["gsis_id"], CANONICAL_RESOLVED, ()
            return None, CONFLICT, tuple(sorted(r["gsis_id"] for r in narrowed2))
        return None, UNKNOWN, ()


# ---------------------------------------------------------------------------
# Export discovery — season and position come from CONTENT, never the filename
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportFile:
    path: Path
    stream: str
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    blocks: tuple[tuple[str, str], ...]  # (position|"", season) pairs present
    sha256: str


def read_export(path: Path) -> ExportFile:
    """Read one subscriber export and identify what it contains FROM ITS CONTENT.

    Filenames are download-order artefacts (``data_analysis_report-… (17).csv``) and carry
    no reliable position or season. Trusting them is how a 2019 file gets ingested as 2021.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    if not rows:
        raise PlayerProfilerError(f"playerprofiler_empty_export: {path}")

    if "position" in columns and "season" in columns:
        stream = "player_season"
        blocks = tuple(sorted({(str(r.get("position") or ""), str(r.get("season") or "")) for r in rows}))
    elif "Player" in columns and "Injury Description" in columns:
        stream = "medical_history"
        blocks = tuple(sorted({("", str(r.get("Year") or "").strip()) for r in rows}))
    else:
        raise PlayerProfilerError(
            f"playerprofiler_unrecognised_export: {path} has neither the Data Analysis "
            f"(position+season) nor the medical (Player+Injury Description) shape"
        )
    return ExportFile(path, stream, columns, rows, blocks, _sha256(path))


def discover_exports(paths: Iterable[Path]) -> list[ExportFile]:
    return [read_export(Path(p)) for p in paths]


def check_medical_schema(exports: Sequence[ExportFile]) -> dict[str, Any]:
    """Medical drift is additive across years and safe to union — but only if it IS additive.

    A column that DISAPPEARS in a later year would silently become null for those rows and
    read as absence rather than as a contract change, so a missing core column refuses.
    """
    medical = [e for e in exports if e.stream == "medical_history"]
    missing: dict[str, list[str]] = {}
    for export in medical:
        gaps = [c for c in MEDICAL_CORE_COLUMNS if c not in export.columns]
        if gaps:
            missing[export.path.name] = gaps
    if missing:
        raise PlayerProfilerError(
            f"playerprofiler_medical_core_columns_missing: {missing} — the medical schema "
            "lost a core column rather than only gaining new ones; unioning would render "
            "the loss as missing data"
        )
    union: list[str] = []
    for export in medical:
        for column in export.columns:
            if column not in union:
                union.append(column)
    return {
        "files": len(medical),
        "core_columns": list(MEDICAL_CORE_COLUMNS),
        "union_columns": union,
        "additive_only": True,
    }


def check_player_season_schema(exports: Sequence[ExportFile]) -> dict[str, Any]:
    """Every Data Analysis export must carry an IDENTICAL column set.

    Unlike the medical archive, these are one report at one point in time; a divergent
    column set means the exports were not all taken from the same report and must not be
    stitched.
    """
    seasons = [e for e in exports if e.stream == "player_season"]
    signatures = {hashlib.sha256("|".join(e.columns).encode()).hexdigest(): e for e in seasons}
    if len(signatures) > 1:
        raise PlayerProfilerError(
            "playerprofiler_player_season_schema_divergent: "
            + str({e.path.name: len(e.columns) for e in signatures.values()})
        )
    return {"files": len(seasons), "columns": len(seasons[0].columns) if seasons else 0}


def check_no_duplicate_blocks(exports: Sequence[ExportFile]) -> dict[str, Any]:
    """A position-season delivered by two files is a double-count waiting to happen.

    Identical duplicates are benign (David downloaded RB 2025 three times) and are reported
    so the dedupe is visible; DIFFERING duplicates refuse, because silently keeping one
    would discard real data with no record of the choice.
    """
    owners: dict[tuple[str, str, str], list[ExportFile]] = defaultdict(list)
    for export in exports:
        for block in export.blocks:
            owners[(export.stream, *block)].append(export)

    def _block_rows(export: ExportFile, position: str, season: str) -> list[dict[str, Any]]:
        if export.stream == "player_season":
            return [r for r in export.rows
                    if str(r.get("position") or "") == position
                    and str(r.get("season") or "") == season]
        return [r for r in export.rows if str(r.get("Year") or "").strip() == season]

    benign: list[str] = []
    conflicting: dict[str, Any] = {}
    for (stream, position, season), files in owners.items():
        if len(files) < 2:
            continue
        label = ":".join(x for x in (stream, position, season) if x)
        # Compare the BLOCK's rows, not the whole file. A file can legitimately carry a
        # stray row from a neighbouring year — MedicalHistory_2023.csv holds exactly one
        # 2022-dated record — and a whole-file digest comparison called that a conflict
        # and refused real data. What matters is whether the two files DISAGREE about a
        # row, not whether they happen to differ elsewhere.
        maps: list[dict[str, str]] = []
        for export in files:
            rows = _block_rows(export, position, season)
            maps.append({
                json.dumps({k: v for k, v in r.items() if k in ("Player", "name", "Body Part",
                                                                "Incident Date", "position")},
                           sort_keys=True): json.dumps(r, sort_keys=True)
                for r in rows
            })
        disagreements = []
        for i in range(len(maps)):
            for j in range(i + 1, len(maps)):
                shared = set(maps[i]) & set(maps[j])
                bad = [k for k in shared if maps[i][k] != maps[j][k]]
                if bad:
                    disagreements.append({
                        "files": [files[i].path.name, files[j].path.name],
                        "rows_disagreeing": len(bad),
                    })
        if disagreements:
            conflicting[label] = disagreements
        else:
            benign.append(f"{label} ({'/'.join(str(len(m)) for m in maps)} rows)")
    if conflicting:
        raise PlayerProfilerError(
            f"playerprofiler_conflicting_duplicate_blocks: {conflicting} — the same "
            "position-season arrived from files with DIFFERENT contents"
        )
    return {"identical_duplicate_blocks": sorted(benign)}


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


_CAPTURE_COLUMNS = (
    "stream_key", "stream", "block", "status", "rows_total", "coverage_json",
    "failure_reason", "content_hash", "ingested_at",
)


class PlayerProfilerStore:
    """Content-addressed store, one table per stream.

    Same contract as the other layer-1 adapters: a row in ``pp_capture`` means a real
    successful ingest; identical content re-ingests to nothing; changed content replaces
    that block wholesale so a withdrawn row cannot survive as a phantom.
    """

    def __init__(self, db_path: Path | str, *, season_columns: Sequence[str],
                 medical_columns: Sequence[str]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.season_columns = tuple(season_columns)
        self.medical_columns = tuple(medical_columns)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pp_capture ("
                + ", ".join(f"{_q(c)} TEXT" for c in _CAPTURE_COLUMNS)
                + ", PRIMARY KEY (stream_key))"
            )
            for table, cols in (
                (PLAYER_SEASON_TABLE, self.season_columns),
                (MEDICAL_TABLE, self.medical_columns),
            ):
                if not cols:
                    continue
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} ("
                    + ", ".join(f"{_q(c)} TEXT" for c in cols)
                    + f", PRIMARY KEY ({_q('row_key')}))"
                )
                self._assert_schema(conn, table, cols)

    @staticmethod
    def _assert_schema(conn: sqlite3.Connection, table: str, expected: Sequence[str]) -> None:
        actual = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        gaps = [c for c in expected if c not in actual]
        if gaps:
            raise PlayerProfilerError(
                f"playerprofiler_schema_mismatch: {table} is missing {gaps[:6]}"
                f"{'…' if len(gaps) > 6 else ''} — the store predates {SCHEMA_VERSION}; "
                "rebuild it from the raw exports rather than writing mixed-schema rows"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def apply_block(
        self, *, table: str, stream: str, block: str, rows: Sequence[Mapping[str, Any]],
        columns: Sequence[str], coverage: Mapping[str, Any], ingested_at: str,
    ) -> str:
        key = f"{stream}:{block}"
        digest = hashlib.sha256(
            "\n".join(sorted(json.dumps(dict(r), sort_keys=True, default=str) for r in rows)).encode()
        ).hexdigest()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT content_hash FROM pp_capture WHERE stream_key = ?", (key,)
            ).fetchone()
            if existing is not None and existing["content_hash"] == digest:
                return "unchanged"
            conn.execute(f"DELETE FROM {table} WHERE block = ?", (block,))
            for row in rows:
                conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({', '.join(_q(c) for c in columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})",
                    [row.get(c) for c in columns],
                )
            conn.execute(
                f"INSERT OR REPLACE INTO pp_capture ({', '.join(_q(c) for c in _CAPTURE_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _CAPTURE_COLUMNS)})",
                [key, stream, block, "ok", len(rows),
                 json.dumps(coverage, sort_keys=True, default=str), None, digest, ingested_at],
            )
            return "inserted" if existing is None else "updated"

    def row_count(self, table: str) -> int:
        with self._connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def captures(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pp_capture ORDER BY stream, block").fetchall()
        out = []
        for row in rows:
            record = dict(row)
            record["coverage"] = json.loads(record.pop("coverage_json") or "{}")
            out.append(record)
        return out

    def content_fingerprint(self) -> str:
        chunks: list[str] = []
        with self._connect() as conn:
            for table in (PLAYER_SEASON_TABLE, MEDICAL_TABLE):
                try:
                    for row in conn.execute(f"SELECT * FROM {table} ORDER BY row_key"):
                        chunks.append(json.dumps(tuple(row), default=str))
                except sqlite3.OperationalError:
                    continue
        return hashlib.sha256("\n".join(chunks).encode()).hexdigest()


def medical_blind_window(as_of_year: int | None = None) -> dict[str, Any]:
    """The seasons the medical archive cannot see. Consumers MUST carry this.

    Absence of an injury record after ``MEDICAL_COVERAGE_END`` is NOT evidence of health —
    it is the absence of data, and joined naively the two are indistinguishable. Measured
    2026-07-31: of 244 WRs active in the 2025 export, 111 have no medical record at all,
    and for every one of them a 2024 or 2025 injury is invisible.
    """
    as_of_year = as_of_year or datetime.now(timezone.utc).year
    blind = [y for y in range(MEDICAL_COVERAGE_END + 1, as_of_year + 1)]
    return {
        "coverage_end_season": MEDICAL_COVERAGE_END,
        "blind_seasons": blind,
        "decision_supported": False,
        "use_boundary": (
            "Training and backtesting only. NOT decision-grade for current players: a "
            "player with no record after "
            f"{MEDICAL_COVERAGE_END} may be healthy or may have missed two seasons, and "
            "this data cannot tell them apart."
        ),
    }


# ---------------------------------------------------------------------------
# Ingest (callable; never self-scheduling)
# ---------------------------------------------------------------------------


def status_marker_path(root: Path = DEFAULT_ROOT) -> Path:
    return Path(root) / "playerprofiler_status_latest.json"


def _coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {s: 0 for s in (CANONICAL_RESOLVED, SOURCE_ONLY, CONFLICT, UNKNOWN)}
    for row in rows:
        counts[row.get("identity_status", UNKNOWN)] = counts.get(row.get("identity_status", UNKNOWN), 0) + 1
    unresolved = counts[SOURCE_ONLY] + counts[CONFLICT] + counts[UNKNOWN]
    return {
        "rows_total": len(rows),
        "rows_canonical_resolved": counts[CANONICAL_RESOLVED],
        "rows_source_only": counts[SOURCE_ONLY],
        "rows_conflict": counts[CONFLICT],
        "rows_unknown": counts[UNKNOWN],
        # Never a single count: "not canonically identified" is stated so no reader can
        # infer identity health from one reassuring zero.
        "rows_not_canonically_identified": unresolved,
        "unresolved_names": sorted({
            str(r.get("name") or r.get("player") or "")
            for r in rows if r.get("identity_status") != CANONICAL_RESOLVED
        })[:50],
    }


def _medical_universe_split(
    medical_rows: Sequence[Mapping[str, Any]],
    season_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Separate a real identity gap from rows that were never in our universe.

    The medical archive covers the WHOLE roster — centers, guards, safeties, long snappers.
    The governed crosswalk covers skill positions. So a flat medical resolve rate reads as
    catastrophic (82.4% on the live archive) when the overwhelming majority of the misses
    are players Dynasty Genius does not model and never will.

    Reporting one blended number would be the reassuring kind of wrong in both directions:
    it hides that the adapter is healthy, and it hides WHICH misses are real. So the split
    is explicit. ``in_universe_unresolved`` is the only number that indicts the adapter —
    those are skill players, present in the data-analysis export, whose medical rows failed
    to resolve. They are genuine name collisions (``Mike Williams``, ``David Johnson``,
    ``Adrian Peterson``) and they are HELD, not guessed.
    """
    skill = {_norm_no_suffix(str(r.get("name") or "")) for r in season_rows}
    skill.discard("")
    resolved = in_universe = out_of_universe = 0
    in_universe_names: set[str] = set()
    for row in medical_rows:
        if row.get("identity_status") == CANONICAL_RESOLVED:
            resolved += 1
            continue
        name = str(row.get("player") or row.get("name") or "")
        if _norm_no_suffix(name) in skill:
            in_universe += 1
            in_universe_names.add(name)
        else:
            out_of_universe += 1
    denom = resolved + in_universe
    return {
        "resolved": resolved,
        # Skill players we DO model whose medical rows did not resolve. The real gap.
        "in_universe_unresolved": in_universe,
        # Linemen / defenders / specialists the skill crosswalk never contained. Not a defect.
        "out_of_universe_unresolved": out_of_universe,
        "in_universe_unresolved_names": sorted(in_universe_names)[:50],
        "coverage_over_modelled_universe": round(resolved / denom, 4) if denom else None,
        "note": (
            "Flat medical coverage understates adapter health: the archive covers all 53 "
            "roster spots, the crosswalk covers skill positions. Judge the adapter on "
            "coverage_over_modelled_universe; judge the gap on in_universe_unresolved."
        ),
    }


def run_playerprofiler_ingest(
    *,
    export_paths: Sequence[Path],
    identity: NameIdentityIndex | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    """Discover -> verify schema -> resolve identity -> store -> marker.

    A start marker is written before anything is read, so a run that dies mid-flight leaves
    ``status=running`` rather than the previous run's ``ok``. Any failure writes
    ``status=failed`` with the stage named. Silence is never success.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"pp-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(root)
    base = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "started_at": started_at,
            "export_count": len(export_paths)}
    _atomic_write_json(marker, {**base, "status": "running"})

    stage = "discover"
    try:
        if not export_paths:
            # A zero-file run is indistinguishable from a healthy one if it reports `ok`:
            # same green marker, same absent error, just no data. That is precisely what a
            # renamed download folder or a changed export filename looks like, and it is
            # the failure mode most likely to go unnoticed for weeks. Refuse instead.
            raise PlayerProfilerError(
                "playerprofiler_no_exports: zero export files were supplied. Refusing to "
                "record a successful run over no data — check the download folder and the "
                "filename patterns before re-running."
            )
        exports = discover_exports(export_paths)
        stage = "schema"
        season_schema = check_player_season_schema(exports)
        medical_schema = check_medical_schema(exports)
        dupes = check_no_duplicate_blocks(exports)

        stage = "identity"
        identity = identity or NameIdentityIndex.from_governed_crosswalk()

        season_cols = ["row_key", "block", "dg_player_id", "identity_status", "identity_candidates"]
        src_season = [e for e in exports if e.stream == "player_season"]
        if src_season:
            season_cols += [_slug(c) for c in src_season[0].columns]
        medical_cols = ["row_key", "block", "dg_player_id", "identity_status", "identity_candidates"]
        medical_cols += [_slug(c) for c in medical_schema["union_columns"]]

        stage = "store"
        store = PlayerProfilerStore(db_path, season_columns=season_cols,
                                    medical_columns=medical_cols)

        by_block: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        seen: set[str] = set()
        for export in exports:
            for row in export.rows:
                if export.stream == "player_season":
                    block = f"{row.get('position')}-{row.get('season')}"
                    name = row.get("name")
                    dg, st, cands = identity.resolve(
                        name, draft_year=row.get("draft_year"), college=row.get("college"))
                    key = f"player_season|{block}|{_norm_no_suffix(name)}"
                else:
                    block = str(row.get("Year") or "").strip() or "unknown"
                    name = row.get("Player")
                    dg, st, cands = identity.resolve(name)
                    key = (f"medical|{block}|{_norm_no_suffix(name)}|"
                           f"{_slug(row.get('Body Part'))}|{_slug(row.get('Incident Date'))}")
                if key in seen:
                    continue
                seen.add(key)
                out = {_slug(k): v for k, v in row.items()}
                out.update({"row_key": key, "block": block, "dg_player_id": dg,
                            "identity_status": st,
                            "identity_candidates": ",".join(cands) if cands else None,
                            "name": name, "player": name})
                by_block[(export.stream, block)].append(out)

        applied: dict[str, str] = {}
        totals = {"player_season": 0, "medical_history": 0}
        for (stream, block), rows in sorted(by_block.items()):
            table = PLAYER_SEASON_TABLE if stream == "player_season" else MEDICAL_TABLE
            cols = season_cols if stream == "player_season" else medical_cols
            applied[f"{stream}:{block}"] = store.apply_block(
                table=table, stream=stream, block=block, rows=rows, columns=cols,
                coverage=_coverage(rows), ingested_at=started_at)
            totals[stream] += len(rows)

        all_rows = [r for rows in by_block.values() for r in rows]
        season_rows = [r for (stream, _), rows in by_block.items()
                       if stream == "player_season" for r in rows]
        medical_rows = [r for (stream, _), rows in by_block.items()
                        if stream == "medical_history" for r in rows]
    except Exception as exc:
        _atomic_write_json(marker, {**base, "status": "failed", "failed_stage": stage,
                                    "reason": f"{type(exc).__name__}: {exc}",
                                    "finished_at": datetime.now(timezone.utc).isoformat()})
        raise

    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "player_season_schema": season_schema,
        "medical_schema": {k: v for k, v in medical_schema.items() if k != "union_columns"},
        "duplicate_blocks": dupes,
        "rows": totals,
        "applied": applied,
        # Per-stream, never blended. The two streams cover different player universes, so a
        # single combined rate describes neither of them (see _medical_universe_split).
        "coverage": {
            "player_season": _coverage(season_rows),
            "medical_history": {
                **_coverage(medical_rows),
                "universe_split": _medical_universe_split(medical_rows, season_rows),
            },
            "all_rows_combined": {
                **_coverage(all_rows),
                "warning": (
                    "Do not read this as identity health. It blends two streams over "
                    "different player universes; read the per-stream figures instead."
                ),
            },
        },
        "medical_blind_window": medical_blind_window(),
        "provenance": {
            "source": "playerprofiler",
            "delivery": "manual subscriber export (no API; the shadow endpoint is dead)",
            "private": True,
            "note": "Raw exports stay outside the repo; only derived features may travel.",
        },
    }
    _atomic_write_json(marker, status)
    return status
