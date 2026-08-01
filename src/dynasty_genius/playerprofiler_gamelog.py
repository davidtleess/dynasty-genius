"""PlayerProfiler Advanced Gamelog — weekly player usage, 2020-2025.

Layer 1. 44,464 player-games. This is the stream with real modelling value: it is not *what*
a player produced but *how* he was used — routes run, snap share broken out by alignment
(slot / inline / out wide / backfield), hog rate, contested targets, drops, deep-ball
attempts, play-action and motion snaps, defenders in box.

It is also the messiest of the three PlayerProfiler downloads, and every design decision
below exists because of something measured on 2026-08-01 rather than assumed.

**1. Only 36 of 174 columns appear in all six seasons.** Most of the rest is not loss, it is
*renaming*: 2020 shipped ``pass_yards`` where 2021+ ships ``passing_yards``. The rename map
in ``COLUMN_RENAMES`` was verified numerically, not guessed from the spelling — each pair's
distribution was compared across the seam (QB passing yards: mean 207.6 in 2020 vs 193.1 in
2021). A rename that could not be reconciled is NOT in the map, and its columns stay
separate under their own names.

**2. The null token changed meaning at the same seam, and this is the dangerous one.**
2020 writes ``0``; 2021 onward writes the literal string ``NA`` — 435,537 of them in the
2021 file alone. Three renames looked broken until this was accounted for, and all three
reconciled once ``NA`` was read as zero:

===========================  ==================  ==================
Column                       2020 mean           2021 mean (NA→0)
===========================  ==================  ==================
``first_downs_rushing``      1.40                1.35
``zone_coverage_targets``    1.74                1.60
``big_hits_taken``           0.16                0.22
===========================  ==================  ==================

**3. But ``NA`` does NOT uniformly mean zero, so no blanket rule is applied.** Measured on
2021:

- ``snap_share`` is ``NA`` on 12 rows, all with zero snaps, and never with snaps > 0. There
  ``NA`` genuinely means "no opportunity".
- ``target_share`` and ``hog_rate`` are never ``NA``.
- ``yards_created_receiving`` is ``NA`` on 3,178 rows with zero receptions **and on 3,802
  rows that HAD receptions**. For that column "zero" and "not charted" are
  indistinguishable, and coercing it to 0 would invent 3,802 measurements.

So this module stores ``NA`` as SQL NULL and publishes a measured, per-column
classification (``classify_na_semantics``) that a consumer must consult before aggregating.
It never decides on the consumer's behalf.

**4. Nine coverage columns disappear after 2024** — ``routes_vs_man``, ``targets_vs_zone``,
``separation_at_target``, ``target_accuracy``, ``burns`` and friends. That is a blind window
with the same shape as the medical archive's: absent is not zero. See
``column_availability``.

**5. Two id namespaces**, at the same 2022/2023 seam as every other PlayerProfiler stream —
PP-internal ``AA-0025`` through 2022, GSIS from 2023. Identity resolves through the roster
key's bridge, and a ``source_id_collision`` id is never resolved.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .playerprofiler import (
    CANONICAL_RESOLVED,
    CONFLICT,
    DEFAULT_DB_PATH,
    DEFAULT_ROOT,
    UNKNOWN,
    PlayerProfilerError,
    PlayerProfilerStore,
    _atomic_write_json,
    _norm_no_suffix,
    _sha256,
    _slug,
)
from .playerprofiler_roster import (
    BASIS_NAME_BRIDGE,
    BASIS_NONE,
    BASIS_VENDOR_GSIS,
    BRIDGE_TABLE,
    NAMESPACE_GSIS,
    NAMESPACE_PP_INTERNAL,
    SOURCE_ID_COLLISION,
    _is_null_id,
)

GAMELOG_TABLE = "pp_gamelog_week"
GAMELOG_STREAM = "gamelog_week"
SCHEMA_VERSION = "playerprofiler_gamelog.v1"

_GSIS_RE = re.compile(r"^00-\d{7}$")

#: Null tokens seen in these files. ``NA`` is the 2021+ convention; 2020 wrote 0 instead.
_NULL_TOKENS = frozenset({"", "na", "n/a", "#n/a", "null", "-"})

#: 2020 column name -> the 2021+ name for the same measurement.
#:
#: EVERY pair here was checked numerically across the seam, not inferred from spelling. The
#: reconciliation for the three that initially looked divergent is in the module docstring;
#: all three were the NA-vs-0 change, not a different metric.
#:
#: DELIBERATELY ABSENT, because they could not be reconciled and guessing would silently
#: fuse two different measurements: ``carries_inside_10``/``carries_inside_5`` (2020) vs
#: ``carries_inside`` (2021+) — a two-into-one merge whose threshold is unstated; and
#: ``opportunity_share``/``juke_rate``/``average_cushion``/``routes_won*``, which have no
#: 2021+ counterpart at all and are simply 2020-only.
COLUMN_RENAMES: dict[str, str] = {
    "player_id": "player",
    "pass_yards": "passing_yards",
    "rush_yards": "rushing_yards",
    "pass_touchdowns": "passing_touchdowns",
    "rush_touchdowns": "rushing_touchdowns",
    "air_yards_passing": "air_yards_pass",
    "first_downs_passing": "passing_first_downs",
    "first_downs_receiving": "receiving_first_downs",
    "first_downs_rushing": "rushing_first_downs",
    "deep_ball_pass_attempts": "deep_ball_attempts",
    "deep_ball_pass_completions": "deep_ball_completions",
    "man_coverage_routes": "routes_vs_man",
    "man_coverage_targets": "targets_vs_man",
    "zone_coverage_routes": "routes_vs_zone",
    "zone_coverage_targets": "targets_vs_zone",
    "big_hits_taken": "big_hit",
}

#: Columns carrying identity/keying rather than measurement.
_KEY_COLUMNS = ("player", "name", "week", "season", "position", "team", "opponent")

NA_MEANS_NO_OPPORTUNITY = "na_means_no_opportunity"
NA_AMBIGUOUS = "na_ambiguous"
NA_NEVER_PRESENT = "na_never_present"
NA_UNCLASSIFIED = "na_unclassified"


class GamelogError(PlayerProfilerError):
    """Refuses rather than storing a measurement it cannot describe honestly."""


def _is_null(value: Any) -> bool:
    return str(value or "").strip().lower() in _NULL_TOKENS


@dataclass(frozen=True)
class GamelogExport:
    path: Path
    season: str
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    id_namespace: str
    sha256: str


def _canonical(column: str) -> str:
    """Map a source column onto the canonical (2021+) name."""
    return COLUMN_RENAMES.get(column, column)


def read_gamelog_export(path: Path) -> GamelogExport:
    path = Path(path)
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    if not rows:
        raise GamelogError(f"gamelog_empty_export: {path}")

    id_col = "player_id" if "player_id" in columns else "player"
    if id_col not in columns:
        raise GamelogError(
            f"gamelog_no_id_column: {path.name} has neither 'player_id' (2020) nor "
            "'player' (2021+). Without an id column every row would have to be name-matched."
        )
    ids = [str(r.get(id_col) or "").strip() for r in rows]
    ids = [i for i in ids if i and not _is_null_id(i)]
    if not ids:
        raise GamelogError(f"gamelog_no_usable_ids: every {id_col} in {path.name} is null")
    gsis = sum(1 for i in ids if _GSIS_RE.match(i))
    if gsis == len(ids):
        namespace = NAMESPACE_GSIS
    elif gsis == 0:
        namespace = NAMESPACE_PP_INTERNAL
    else:
        raise GamelogError(
            f"gamelog_mixed_id_namespace: {gsis} of {len(ids)} ids in {path.name} are "
            "GSIS-shaped and the rest are not; the file cannot be assigned one namespace."
        )

    # Season is in the 2020 file as a column and nowhere else; fall back to the filename and
    # cross-check whenever the column exists, rather than trusting either blindly.
    from_name = re.match(r"(\d{4})", path.name)
    if not from_name:
        raise GamelogError(f"gamelog_unlabelled_file: {path.name} has no leading season")
    season = from_name.group(1)
    in_file = {str(r.get("season") or "").strip() for r in rows if r.get("season")}
    if in_file and in_file != {season}:
        raise GamelogError(
            f"gamelog_season_label_mismatch: {path.name} is named {season} but its own "
            f"season column says {sorted(in_file)}. One of them is wrong; refusing to pick."
        )
    return GamelogExport(path, season, columns, rows, namespace, _sha256(path))


def discover_gamelog_exports(paths: Iterable[Path]) -> list[GamelogExport]:
    exports = [read_gamelog_export(Path(p)) for p in paths]
    seen: dict[str, GamelogExport] = {}
    for export in exports:
        prior = seen.get(export.season)
        if prior is not None and prior.sha256 != export.sha256:
            raise GamelogError(
                f"gamelog_conflicting_season_files: {export.season} arrived twice with "
                f"different contents ({prior.path.name} vs {export.path.name})."
            )
        seen[export.season] = export
    return sorted(seen.values(), key=lambda e: e.season)


def column_availability(exports: Sequence[GamelogExport]) -> dict[str, Any]:
    """Which seasons each canonical column actually exists in.

    Absence is not zero. Without this a consumer averaging ``routes_vs_man`` across
    2021-2025 would silently divide a four-season sum by five seasons — the 2025 file does
    not have the column at all.
    """
    seasons = [e.season for e in exports]
    present: dict[str, list[str]] = defaultdict(list)
    for export in exports:
        for column in export.columns:
            present[_canonical(column)].append(export.season)

    full, partial = [], {}
    for column, got in sorted(present.items()):
        if len(got) == len(seasons):
            full.append(column)
        else:
            partial[column] = {
                "present": sorted(got),
                "absent": sorted(set(seasons) - set(got)),
            }
    return {
        "seasons": seasons,
        "columns_in_every_season": sorted(full),
        "columns_with_gaps": partial,
        "note": (
            "A column absent in a season is NOT zero for that season. Any aggregate must "
            "restrict its denominator to the seasons listed in 'present'."
        ),
    }


def classify_na_semantics(
    exports: Sequence[GamelogExport],
    denominators: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Measure, per column, whether ``NA`` can be safely read as zero.

    The test is whether ``NA`` ever co-occurs with a NON-zero denominator. If it does not,
    ``NA`` marks an absence of opportunity and reads as zero. If it does, the column is using
    ``NA`` for both "none happened" and "not charted", those are indistinguishable, and any
    coercion to zero invents measurements that were never taken.

    Measured on 2021: ``snap_share`` is clean (12 NAs, all with zero snaps);
    ``yards_created_receiving`` is ambiguous (3,802 NAs on rows that HAD receptions).
    """
    denominators = dict(denominators or _DEFAULT_DENOMINATORS)
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"na_total": 0, "na_with_opportunity": 0, "rows": 0}
    )
    for export in exports:
        for row in export.rows:
            canon_row = {_canonical(k): v for k, v in row.items()}
            for column, value in canon_row.items():
                if column in _KEY_COLUMNS:
                    continue
                entry = stats[column]
                entry["rows"] += 1
                if not _is_null(value):
                    continue
                entry["na_total"] += 1
                denom = denominators.get(column)
                if denom is None:
                    continue
                raw = canon_row.get(denom)
                if _is_null(raw):
                    continue
                try:
                    if float(raw) > 0:
                        entry["na_with_opportunity"] += 1
                except (TypeError, ValueError):
                    continue

    out: dict[str, Any] = {}
    for column, entry in sorted(stats.items()):
        if entry["na_total"] == 0:
            verdict = NA_NEVER_PRESENT
        elif column not in denominators:
            verdict = NA_UNCLASSIFIED
        elif entry["na_with_opportunity"] == 0:
            verdict = NA_MEANS_NO_OPPORTUNITY
        else:
            verdict = NA_AMBIGUOUS
        out[column] = {
            "verdict": verdict,
            "na_rows": entry["na_total"],
            "na_with_nonzero_denominator": entry["na_with_opportunity"],
            "denominator": denominators.get(column),
        }
    return {
        "columns": out,
        "safe_to_zero_fill": sorted(
            c for c, v in out.items() if v["verdict"] == NA_MEANS_NO_OPPORTUNITY),
        "never_zero_fill": sorted(
            c for c, v in out.items() if v["verdict"] == NA_AMBIGUOUS),
        "unclassified": sorted(
            c for c, v in out.items() if v["verdict"] == NA_UNCLASSIFIED),
        "note": (
            "Columns in 'never_zero_fill' use NA for both 'none happened' and 'not "
            "charted'. 'unclassified' means no denominator was declared, so nothing was "
            "proven either way — treat as NOT safe."
        ),
    }


#: Denominator for each rate/derived column: the count that must be non-zero for the column
#: to have been measurable at all. Only columns listed here can be classified; everything
#: else stays ``na_unclassified``, which is deliberately conservative.
_DEFAULT_DENOMINATORS: dict[str, str] = {
    "snap_share": "snaps",
    "hog_rate": "routes_run",
    "target_share": "targets",
    "yards_created_receiving": "receptions",
    "yards_created_rushing": "carries",
    "routes_vs_man": "routes_run",
    "routes_vs_zone": "routes_run",
    "targets_vs_man": "targets",
    "targets_vs_zone": "targets",
    "yards_vs_man": "targets",
    "yards_vs_zone": "targets",
    "separation_at_target": "targets",
    "target_accuracy": "targets",
    "contested_catches": "contested_targets",
    "deep_ball_completions": "deep_ball_attempts",
    "red_zone_completions": "red_zone_passes",
    "qb_seconds_to_throw": "pass_attempts",
    "throws_under_duress": "pass_attempts",
    "catchable_targets": "targets",
    "drops": "targets",
    "evaded_tackles": "total_touches",
}


def status_marker_path(root: Path = DEFAULT_ROOT) -> Path:
    return Path(root) / "playerprofiler_gamelog_status_latest.json"


def _load_bridge(db_path: Path) -> tuple[dict[str, str], set[str]]:
    """Reuse the roster key's PP-internal -> GSIS bridge. Collisions come back separately."""
    resolved: dict[str, str] = {}
    colliding: set[str] = set()
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            f"SELECT pp_player_id, dg_player_id, bridge_status FROM {BRIDGE_TABLE}"
        ).fetchall()
    except sqlite3.OperationalError:
        return resolved, colliding
    for pid, dg, status in rows:
        if status == SOURCE_ID_COLLISION:
            colliding.add(pid)
        elif dg:
            resolved[pid] = dg
    return resolved, colliding


def run_gamelog_ingest(
    *,
    export_paths: Sequence[Path],
    db_path: Path = DEFAULT_DB_PATH,
    root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"ppg-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(root)
    base = {"schema_version": SCHEMA_VERSION, "run_id": run_id,
            "started_at": started_at, "export_count": len(export_paths)}
    _atomic_write_json(marker, {**base, "status": "running"})

    stage = "discover"
    try:
        if not export_paths:
            raise GamelogError(
                "gamelog_no_exports: zero files supplied. Refusing to record a successful "
                "run over no data."
            )
        exports = discover_gamelog_exports(export_paths)

        stage = "schema"
        availability = column_availability(exports)
        na_semantics = classify_na_semantics(exports)

        stage = "identity"
        bridge, colliding = _load_bridge(db_path)
        if not bridge:
            raise GamelogError(
                "gamelog_bridge_missing: the roster key's pp_identity_bridge is empty or "
                "absent. Run scripts/run_playerprofiler_roster_ingest.py first — without it "
                "every pre-2023 row would be unidentifiable, and the run would look healthy "
                "while resolving nothing."
            )

        stage = "store"
        columns = ["row_key", "block", "season", "week", "source_player_id", "id_namespace",
                   "dg_player_id", "identity_status", "identity_basis"]
        measured = sorted({
            _slug(_canonical(c)) for e in exports for c in e.columns
            if _canonical(c) not in ("player", "player_id")
        })
        columns += [c for c in measured if c not in columns]

        store = PlayerProfilerStore(db_path, season_columns=(), medical_columns=())
        with store._connect() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {GAMELOG_TABLE} ("
                + ", ".join(f'"{c}" TEXT' for c in columns)
                + ', PRIMARY KEY ("row_key"))'
            )

        by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for export in exports:
            id_col = "player_id" if "player_id" in export.columns else "player"
            for raw in export.rows:
                pid = str(raw.get(id_col) or "").strip()
                week = str(raw.get("week") or "").strip()
                name = str(raw.get("name") or "").strip()
                row: dict[str, Any] = {
                    _slug(_canonical(k)): (None if _is_null(v) else v)
                    for k, v in raw.items()
                }
                # NA becomes SQL NULL; the classification above tells a consumer whether
                # that NULL may be read as zero. Never decided here.
                # The key carries the OPPONENT as well as the week. Measured: Lynn Bowden
                # has two DIFFERENT 2020 week-14 games in the file (vs WAS and vs KC) — one
                # of the two week labels is wrong at source. Keying on week alone would
                # discard a real game; keying on opponent too keeps both and lets the
                # mislabeling be seen rather than silently resolved.
                # TEAM is in the key for a second, distinct reason: the colliding source ids
                # found in the roster key (DM-3050 = two David Moores, SB-9929 = two Spencer
                # Browns) appear here too, same week, same opponent, differing ONLY by team
                # — the vendor attributed one stat line to both players. Both rows are kept
                # and both are held as `conflict`; neither is resolved to a canonical id.
                opponent = str(raw.get("opponent") or "").strip()
                team = str(raw.get("team") or "").strip()
                row.update({
                    "row_key": (f"gamelog|{export.season}|{week}|{pid}|"
                                f"{_norm_no_suffix(name)}|{opponent}|{team}"),
                    "block": export.season,
                    "season": export.season,
                    "week": week,
                    "source_player_id": pid,
                    "id_namespace": export.id_namespace,
                })
                if not pid or _is_null_id(pid):
                    row.update({"dg_player_id": None, "identity_status": UNKNOWN,
                                "identity_basis": BASIS_NONE})
                elif export.id_namespace == NAMESPACE_GSIS:
                    row.update({"dg_player_id": pid, "identity_status": CANONICAL_RESOLVED,
                                "identity_basis": BASIS_VENDOR_GSIS})
                elif pid in colliding:
                    row.update({"dg_player_id": None, "identity_status": CONFLICT,
                                "identity_basis": BASIS_NONE})
                elif pid in bridge:
                    row.update({"dg_player_id": bridge[pid],
                                "identity_status": CANONICAL_RESOLVED,
                                "identity_basis": BASIS_NAME_BRIDGE})
                else:
                    row.update({"dg_player_id": None, "identity_status": UNKNOWN,
                                "identity_basis": BASIS_NONE})
                by_season[export.season].append(row)

        applied: dict[str, str] = {}
        exact_duplicates_by_season: dict[str, int] = {}
        stored_rows: list[dict[str, Any]] = []
        for season, rows in sorted(by_season.items()):
            # Collapse only rows that are BYTE-IDENTICAL; refuse on genuine disagreement.
            # Measured: the 2020 file ships each of Lynn Bowden's two week-14 games twice.
            # An exact duplicate carries no information and is safe to drop. Two rows that
            # share a key and DISAGREE are two different measurements, and picking one
            # silently is how a real player-game disappears.
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                grouped[row["row_key"]].append(row)
            conflicting = {
                key: len(group) for key, group in grouped.items()
                if len({tuple(sorted((k, str(v)) for k, v in g.items())) for g in group}) > 1
            }
            if conflicting:
                raise GamelogError(
                    f"gamelog_conflicting_duplicate_rows: season {season} has "
                    f"{len(conflicting)} key(s) whose rows DISAGREE, e.g. "
                    f"{sorted(conflicting)[:3]}. Two different measurements share one key; "
                    "silently keeping one would delete a real player-game — the exact defect "
                    "found in the roster key. Investigate before ingesting."
                )
            deduped = [group[0] for _, group in sorted(grouped.items())]
            exact_duplicates_by_season[season] = len(rows) - len(deduped)
            stored_rows.extend(deduped)
            applied[f"{GAMELOG_STREAM}:{season}"] = store.apply_block(
                table=GAMELOG_TABLE, stream=GAMELOG_STREAM, block=season, rows=deduped,
                columns=columns, coverage=_coverage(deduped), ingested_at=started_at)

        # Coverage is computed on what was actually STORED, never on the pre-dedup list.
        # In the roster key those two counts diverged and the marker over-reported by
        # exactly the number of rows dropped.
        all_rows = stored_rows
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
        "seasons": {e.season: {"rows": len(e.rows), "columns": len(e.columns),
                               "id_namespace": e.id_namespace} for e in exports},
        "rows": {"gamelog_week": len(all_rows)},
        "exact_duplicate_rows_dropped": {
            k: v for k, v in exact_duplicates_by_season.items() if v},
        "applied": applied,
        "column_availability": availability,
        "na_semantics": na_semantics,
        "coverage": _coverage(all_rows),
        "provenance": {"source": "playerprofiler", "stream": "advanced_gamelog",
                       "delivery": "manual subscriber export (no API)", "private": True},
    }
    _atomic_write_json(marker, status)
    return status


def _coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = defaultdict(int)
    by_basis: dict[str, int] = defaultdict(int)
    for row in rows:
        by_status[str(row.get("identity_status") or UNKNOWN)] += 1
        by_basis[str(row.get("identity_basis") or BASIS_NONE)] += 1
    total = len(rows)
    return {
        "rows_total": total,
        "by_identity_status": dict(sorted(by_status.items())),
        "by_identity_basis": dict(sorted(by_basis.items())),
        "vendor_supplied_share": (
            round(by_basis[BASIS_VENDOR_GSIS] / total, 4) if total else None),
    }
