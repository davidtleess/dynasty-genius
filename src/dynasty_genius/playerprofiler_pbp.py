"""PlayerProfiler Advanced Play-by-Play — 280,868 charted plays, 2020-2025.

Layer 1. The deepest of David's PlayerProfiler downloads and the only one that describes a
single snap: who was on the field, what route each ran, who covered them, how much cushion
they were given, whether the throw was catchable, whether the QB was under duress.

**This is not one dataset. It is THREE**, and the whole module exists to keep them honest
about that. PlayerProfiler re-platformed twice, and each time it changed the vocabulary it
uses to describe *which player filled which role on a play*:

============  ============  =====================================================
Seasons       Columns       Receiver slots
============  ============  =====================================================
2020          134           ``wr1 wr2 slot1 slot2 wr5`` — **five**, and the SLOT
                            receiver is named as such
2021-2022     143           ``receiver1 receiver2 receiver5`` — **three**; there
                            is no receiver3 or receiver4 anywhere in the file
2023-2025      92           ``skill1..skill5`` — five slots, but **anonymous**:
                            the role is gone
============  ============  =====================================================

Read together those three rows are the finding. **2021 did not renumber the receivers, it
DROPPED two of them** — 2020's ``slot1``/``slot2`` are exactly the missing ``receiver3``/
``receiver4``, which is why the surviving indices are the discontinuous 1, 2 and 5. The
slot receiver, a position dynasty analysis cares about specifically, is unavailable from
2021 onward.

Then 2023 removed the role entirely. ``skill1`` is some skill player; the file does not say
whether he is a wide receiver, a tight end or a back. **That information is not recoverable
from this stream** — it has to be joined from the roster key, and a join is an inference,
not the vendor's word. So every slot row carries ``slot_role_known``, and it is False for
every 2023+ row. Anything that treats era-B slots as receivers is guessing.

**Structure.** Two tables rather than one wide one, because a play and a player-on-a-play
are different grains and 265 union columns in a single row would force every era's absent
columns to look like measurements:

- ``pp_pbp_play`` — one row per play, play-level context only.
- ``pp_pbp_slot`` — one row per (play, slot). This is what makes three incompatible
  vocabularies queryable in one shape without fusing them: ``slot_kind`` records what the
  VENDOR called it (``wr``/``slot``/``te``/``rb``/``receiver``/``skill``), never a
  normalisation we invented.

**What era B gained**, so the trade is stated in both directions: per-play ``coverage_type``,
weather (``forecast_temp``, ``forecast_wind``, ``conditions``), live score (``off_score``,
``def_score``), and ``evaded_tackle1..3`` in place of a scalar count. What it lost: per-
receiver coverage and defender, ``backfield_formation``, ``play_direction``, and the betting
lines that era A carried.

**Identity** follows the same 2022/2023 seam as every other PlayerProfiler stream —
PP-internal ids through 2022, GSIS from 2023 — and resolves through the roster key's bridge.
A ``source_id_collision`` id is never resolved.

**Idempotence is keyed on the SOURCE FILE digest**, not on a hash of the derived rows. At
~2.3M slot rows, hashing derived output per run costs more than the ingest itself, and the
input digest plus ``MAPPING_VERSION`` answers the same question: has anything that could
change the output changed? Bump ``MAPPING_VERSION`` when the mapping changes or a re-run
will correctly decide it has nothing to do.
"""

from __future__ import annotations

import csv
import json
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
    _atomic_write_json,
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

PLAY_TABLE = "pp_pbp_play"
SLOT_TABLE = "pp_pbp_slot"
PBP_STREAM = "pbp"
SCHEMA_VERSION = "playerprofiler_pbp.v1"

#: Bump when the era mappings or slot extraction change, or a re-run will read an unchanged
#: source file and correctly conclude there is nothing to do — with stale rows in the store.
MAPPING_VERSION = "2"

_GSIS_RE = re.compile(r"^00-\d{7}$")
_NULL_TOKENS = frozenset({"", "na", "n/a", "#n/a", "null", "-"})

ERA_2020 = "2020_named_roles"
ERA_2021 = "2021_receiver_slots"
ERA_2023 = "2023_anonymous_skill"

#: Slot families per era, as ``(vendor_slot_kind, index, id_column, {field: column})``.
#: Written out literally rather than derived from a regex so that the discontinuous receiver
#: indices (1, 2, 5) and the dropped slot receiver are VISIBLE in the source, not an
#: accident of pattern matching.
_SLOTS_2020: tuple[tuple[str, int, str, dict[str, str]], ...] = tuple(
    (kind, idx, key, {
        "route": f"{key}_route_run",
        "defender_id": f"defender_{key}",
        "cushion": f"cushion_{key}",
        "coverage": f"coverage_{key}",
    })
    for kind, idx, key in (
        ("wr", 1, "wr1"), ("wr", 2, "wr2"), ("wr", 5, "wr5"),
        ("slot", 1, "slot1"), ("slot", 2, "slot2"),
        ("te", 1, "te1"), ("te", 2, "te2"), ("te", 3, "te3"),
        ("rb", 1, "rb1"), ("rb", 2, "rb2"), ("rb", 3, "rb3"),
    )
)

_SLOTS_2021: tuple[tuple[str, int, str, dict[str, str]], ...] = tuple(
    (kind, idx, f"{prefix}_id", {
        "route": f"{prefix}_route",
        "motion": f"{prefix}_motion",
        "cushion": f"{prefix}_cushion_yards",
        "coverage": f"{prefix}_coverage",
        "defender_id": f"{prefix}_defender_id",
    })
    for kind, idx, prefix in (
        ("receiver", 1, "receiver1"), ("receiver", 2, "receiver2"),
        ("receiver", 5, "receiver5"),
        ("inline_te", 1, "inline_te1"), ("inline_te", 2, "inline_te2"),
        ("inline_te", 3, "inline_te3"),
        ("backfield_rb", 1, "backfield_rb1"), ("backfield_rb", 2, "backfield_rb2"),
        ("backfield_rb", 3, "backfield_rb3"),
    )
)

_SLOTS_2023: tuple[tuple[str, int, str, dict[str, str]], ...] = tuple(
    ("skill", idx, f"skill{idx}", {
        "route": f"skill{idx}_route",
        "motion": f"skill{idx}_motion",
        "cushion": f"skill{idx}_cushion",
    })
    for idx in range(1, 6)
)

_ERA_SLOTS = {ERA_2020: _SLOTS_2020, ERA_2021: _SLOTS_2021, ERA_2023: _SLOTS_2023}

#: Slot kinds whose ROLE the vendor states. ``skill`` does not — it is an anonymous slot.
_ROLE_BEARING_KINDS = frozenset({"wr", "slot", "te", "rb", "receiver", "inline_te",
                                 "backfield_rb"})

#: Columns that identify each era, checked as a subset so an added column does not break
#: detection while a REMOVED one still does.
_ERA_SIGNATURES: dict[str, frozenset[str]] = {
    ERA_2020: frozenset({"game_key", "nfl_play_id", "wr1", "slot1", "coverage_wr1"}),
    ERA_2021: frozenset({"playid", "receiver1_id", "backfield_rb1_id", "inline_te1_id"}),
    ERA_2023: frozenset({"playid", "gamekey_internal", "skill1", "skill1_route"}),
}

SLOT_COLUMNS = (
    "row_key", "block", "season", "week", "play_key", "schema_era",
    "slot_kind", "slot_index", "slot_role_known",
    "source_player_id", "id_namespace", "dg_player_id", "identity_status",
    "identity_basis", "route", "motion", "cushion", "coverage", "defender_id",
)


class PbpError(PlayerProfilerError):
    """Refuses rather than fusing three incompatible charting vocabularies."""


def _is_null(value: Any) -> bool:
    return str(value or "").strip().lower() in _NULL_TOKENS


@dataclass(frozen=True)
class PbpExport:
    path: Path
    season: str
    schema_era: str
    columns: tuple[str, ...]
    id_namespace: str
    sha256: str
    row_count: int


def _detect_era(columns: Sequence[str]) -> str:
    got = set(columns)
    for era, signature in _ERA_SIGNATURES.items():
        if signature <= got:
            return era
    raise PbpError(
        f"pbp_unknown_schema_era: columns match none of {sorted(_ERA_SIGNATURES)}. "
        "PlayerProfiler re-platformed this stream TWICE and changed which players it names "
        "on each play both times. Mapping an unrecognised era onto a known one would "
        "silently attach the wrong player to the wrong role on every play in the season."
    )


def _detect_namespace(sample: Sequence[Mapping[str, Any]], era: str) -> str:
    id_col = "qb" if era == ERA_2020 else "qb_id"
    ids = [str(r.get(id_col) or "").strip() for r in sample]
    ids = [i for i in ids if i and not _is_null_id(i)]
    if not ids:
        raise PbpError(f"pbp_no_usable_ids: every {id_col} in the sample is null")
    gsis = sum(1 for i in ids if _GSIS_RE.match(i))
    if gsis == len(ids):
        return NAMESPACE_GSIS
    if gsis == 0:
        return NAMESPACE_PP_INTERNAL
    raise PbpError(
        f"pbp_mixed_id_namespace: {gsis} of {len(ids)} sampled {id_col} values are "
        "GSIS-shaped and the rest are not."
    )


def read_pbp_header(path: Path) -> PbpExport:
    """Read the header and a sample only — these files are up to 30 MB each."""
    path = Path(path)
    match = re.match(r"(\d{4})", path.name)
    if not match:
        raise PbpError(f"pbp_unlabelled_file: {path.name} has no leading season")
    season = match.group(1)
    sample: list[dict[str, Any]] = []
    count = 0
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        for row in reader:
            count += 1
            if len(sample) < 500:
                sample.append(row)
    if not count:
        raise PbpError(f"pbp_empty_export: {path}")
    era = _detect_era(columns)

    in_file = {str(r.get("season") or "").strip() for r in sample if r.get("season")}
    if in_file and in_file != {season}:
        raise PbpError(
            f"pbp_season_label_mismatch: {path.name} is named {season} but its season "
            f"column says {sorted(in_file)}."
        )
    return PbpExport(path, season, era, columns,
                     _detect_namespace(sample, era), _sha256(path), count)


def discover_pbp_exports(paths: Iterable[Path]) -> list[PbpExport]:
    exports = [read_pbp_header(Path(p)) for p in paths]
    seen: dict[str, PbpExport] = {}
    for export in exports:
        prior = seen.get(export.season)
        if prior is not None and prior.sha256 != export.sha256:
            raise PbpError(
                f"pbp_conflicting_season_files: {export.season} arrived twice with "
                f"different contents ({prior.path.name} vs {export.path.name})."
            )
        seen[export.season] = export
    return sorted(seen.values(), key=lambda e: e.season)


def receiver_slot_coverage(exports: Sequence[PbpExport]) -> dict[str, Any]:
    """Record how many receiver positions each season actually charts, and their roles.

    The headline fact this exists to publish: 2020 charts five receiver positions and NAMES
    the slot receiver; 2021-2022 chart three (indices 1, 2 and 5 — the slot receiver is
    gone); 2023+ charts five but anonymously. A consumer counting "receivers on the play"
    across seasons without this would read a vendor coverage change as a real change in NFL
    personnel usage.
    """
    out: dict[str, Any] = {}
    for export in exports:
        slots = _ERA_SLOTS[export.schema_era]
        receiverish = [s for s in slots if s[0] in ("wr", "slot", "receiver", "skill")]
        out[export.season] = {
            "schema_era": export.schema_era,
            "receiver_slots_charted": len(receiverish),
            "slot_kinds": sorted({s[0] for s in slots}),
            "indices": sorted({f"{s[0]}{s[1]}" for s in receiverish}),
            "role_stated_by_vendor": export.schema_era != ERA_2023,
        }
    return {
        "by_season": out,
        "note": (
            "2021 did not renumber receivers, it DROPPED two of them: 2020's slot1/slot2 "
            "are the absent receiver3/receiver4, which is why surviving indices are 1, 2 "
            "and 5. From 2023 the role is not stated at all (skill1..skill5), so "
            "slot_role_known is False for every 2023+ row and any positional reading of "
            "those slots is an inference, not the vendor's word."
        ),
    }


def _load_bridge(db_path: Path) -> tuple[dict[str, str], set[str]]:
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


def status_marker_path(root: Path = DEFAULT_ROOT) -> Path:
    return Path(root) / "playerprofiler_pbp_status_latest.json"


def _play_key(row: Mapping[str, Any], export: PbpExport) -> str:
    """Identify a play.

    ``team_play_charted_order`` is part of the key in the 2020 era and only there. Measured:
    four 2020 plays are charted TWICE and the two chartings DISAGREE about who was on the
    field — different ``wr1``, different ``defender_wr1``, different cushion and coverage.
    Keying without it silently kept whichever charting was read first and discarded a real,
    differing observation. Keeping both lets the disagreement be seen and counted.
    """
    raw = row.get("playid") or row.get("nfl_play_id") or ""
    game = row.get("gamekey_internal") or row.get("gamekey") or row.get("game_key") or ""
    charted = str(row.get("team_play_charted_order") or "").strip()
    suffix = f"|c{charted}" if charted else ""
    return f"{export.season}|{game}|{raw}{suffix}"


def run_pbp_ingest(
    *,
    export_paths: Sequence[Path],
    db_path: Path = DEFAULT_DB_PATH,
    root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"ppp-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(root)
    base = {"schema_version": SCHEMA_VERSION, "mapping_version": MAPPING_VERSION,
            "run_id": run_id, "started_at": started_at,
            "export_count": len(export_paths)}
    _atomic_write_json(marker, {**base, "status": "running"})

    stage = "discover"
    try:
        if not export_paths:
            raise PbpError("pbp_no_exports: zero files supplied.")
        exports = discover_pbp_exports(export_paths)

        stage = "identity"
        bridge, colliding = _load_bridge(db_path)
        if not bridge:
            raise PbpError(
                "pbp_bridge_missing: the roster key's pp_identity_bridge is empty or "
                "absent. Run scripts/run_playerprofiler_roster_ingest.py first."
            )

        stage = "store"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pp_pbp_capture ("
            '"stream_key" TEXT PRIMARY KEY, "season" TEXT, "source_sha256" TEXT, '
            '"mapping_version" TEXT, "play_rows" INTEGER, "slot_rows" INTEGER, '
            '"coverage_json" TEXT, "ingested_at" TEXT)'
        )
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {SLOT_TABLE} ("
            + ", ".join(f'"{c}" TEXT' for c in SLOT_COLUMNS)
            + ', PRIMARY KEY ("row_key"))'
        )

        play_columns = ["play_key", "block", "season", "schema_era", "id_namespace"]
        seen_play_cols: list[str] = []
        for export in exports:
            slots = _ERA_SLOTS[export.schema_era]
            slot_owned = {s[2] for s in slots} | {
                col for _, _, _, fields in slots for col in fields.values()}
            for column in export.columns:
                slug = _slug(column)
                if column not in slot_owned and slug not in play_columns + seen_play_cols:
                    seen_play_cols.append(slug)
        play_columns += seen_play_cols
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {PLAY_TABLE} ("
            + ", ".join(f'"{c}" TEXT' for c in play_columns)
            + ', PRIMARY KEY ("play_key"))'
        )

        applied: dict[str, str] = {}
        totals = {"play": 0, "slot": 0}
        coverage_acc: dict[str, int] = defaultdict(int)
        for export in exports:
            key = f"{PBP_STREAM}:{export.season}"
            prior = conn.execute(
                "SELECT source_sha256, mapping_version, play_rows, slot_rows "
                "FROM pp_pbp_capture WHERE stream_key = ?", (key,)).fetchone()
            if prior and prior[0] == export.sha256 and prior[1] == MAPPING_VERSION:
                applied[key] = "unchanged"
                totals["play"] += int(prior[2] or 0)
                totals["slot"] += int(prior[3] or 0)
                continue

            play_rows, slot_rows, cov = _build_season_rows(
                export, bridge, colliding, play_columns)
            conn.execute(f"DELETE FROM {PLAY_TABLE} WHERE block = ?", (export.season,))
            conn.execute(f"DELETE FROM {SLOT_TABLE} WHERE block = ?", (export.season,))
            conn.executemany(
                f"INSERT OR REPLACE INTO {PLAY_TABLE} "
                f"({', '.join(chr(34)+c+chr(34) for c in play_columns)}) "
                f"VALUES ({', '.join('?' for _ in play_columns)})",
                [[r.get(c) for c in play_columns] for r in play_rows])
            conn.executemany(
                f"INSERT OR REPLACE INTO {SLOT_TABLE} "
                f"({', '.join(chr(34)+c+chr(34) for c in SLOT_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in SLOT_COLUMNS)})",
                [[r.get(c) for c in SLOT_COLUMNS] for r in slot_rows])
            conn.execute(
                "INSERT OR REPLACE INTO pp_pbp_capture VALUES (?,?,?,?,?,?,?,?)",
                (key, export.season, export.sha256, MAPPING_VERSION, len(play_rows),
                 len(slot_rows), json.dumps(cov, sort_keys=True), started_at))
            conn.commit()
            applied[key] = "inserted" if prior is None else "updated"
            totals["play"] += len(play_rows)
            totals["slot"] += len(slot_rows)
            for k, v in cov.items():
                coverage_acc[k] += v

        conn.commit()
    except Exception as exc:
        _atomic_write_json(marker, {**base, "status": "failed", "failed_stage": stage,
                                    "reason": f"{type(exc).__name__}: {exc}",
                                    "finished_at": datetime.now(timezone.utc).isoformat()})
        raise

    slot_total = sum(v for k, v in coverage_acc.items() if k.startswith("status_"))
    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "seasons": {e.season: {"plays": e.row_count, "columns": len(e.columns),
                               "schema_era": e.schema_era,
                               "id_namespace": e.id_namespace} for e in exports},
        "rows": {"pbp_play": totals["play"], "pbp_slot": totals["slot"]},
        "applied": applied,
        "receiver_slot_coverage": receiver_slot_coverage(exports),
        "slot_identity": {
            **{k: v for k, v in sorted(coverage_acc.items())},
            "rows_counted_this_run": slot_total,
            "note": ("Counts cover seasons INGESTED THIS RUN only; a season reported "
                     "'unchanged' contributes to rows but not to these counters."),
        },
        "provenance": {"source": "playerprofiler", "stream": "advanced_pbp",
                       "delivery": "manual subscriber export (no API)", "private": True},
    }
    _atomic_write_json(marker, status)
    return status


def _build_season_rows(
    export: PbpExport,
    bridge: Mapping[str, str],
    colliding: set[str],
    play_columns: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    slots = _ERA_SLOTS[export.schema_era]
    slot_owned = {s[2] for s in slots} | {
        col for _, _, _, fields in slots for col in fields.values()}
    play_rows: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    coverage: dict[str, int] = defaultdict(int)
    play_seen: dict[str, dict[str, Any]] = {}

    with export.path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for raw in csv.DictReader(handle):
            play_key = _play_key(raw, export)
            play = {_slug(k): (None if _is_null(v) else v)
                    for k, v in raw.items() if k not in slot_owned}
            play.update({"play_key": play_key, "block": export.season,
                         "season": export.season, "schema_era": export.schema_era,
                         "id_namespace": export.id_namespace})
            prior_play = play_seen.get(play_key)
            if prior_play is None:
                play_seen[play_key] = play
                play_rows.append(play)
            elif prior_play != play:
                # Two rows share a key and DISAGREE. Keeping one silently discards a real
                # observation — the defect already found in the roster key and the gamelog.
                raise PbpError(
                    f"pbp_conflicting_duplicate_play: season {export.season} play "
                    f"{play_key!r} appears more than once with DIFFERENT values. Silently "
                    "keeping one would delete a real charted observation. Investigate "
                    "before ingesting."
                )

            for kind, index, id_col, fields in slots:
                pid = str(raw.get(id_col) or "").strip()
                if _is_null(pid):
                    continue
                dg, status, basis = _resolve(pid, export.id_namespace, bridge, colliding)
                coverage[f"status_{status}"] += 1
                coverage[f"basis_{basis}"] += 1
                slot_rows.append({
                    "row_key": f"{play_key}|{kind}{index}",
                    "block": export.season,
                    "season": export.season,
                    "week": raw.get("week"),
                    "play_key": play_key,
                    "schema_era": export.schema_era,
                    "slot_kind": kind,
                    "slot_index": str(index),
                    # The single most important column here. False means the VENDOR did not
                    # say what this player's role was; any positional reading is inference.
                    "slot_role_known": "1" if kind in _ROLE_BEARING_KINDS else "0",
                    "source_player_id": pid,
                    "id_namespace": export.id_namespace,
                    "dg_player_id": dg,
                    "identity_status": status,
                    "identity_basis": basis,
                    **{f: (None if _is_null(raw.get(c)) else raw.get(c))
                       for f, c in fields.items()},
                })
    slot_keys = {r["row_key"] for r in slot_rows}
    if len(slot_keys) != len(slot_rows):
        raise PbpError(
            f"pbp_duplicate_slot_key: season {export.season} produced "
            f"{len(slot_rows) - len(slot_keys)} slot rows sharing a key; one player-on-a-"
            "play would be silently overwritten by another."
        )
    return play_rows, slot_rows, dict(coverage)


def _resolve(pid: str, namespace: str, bridge: Mapping[str, str],
             colliding: set[str]) -> tuple[str | None, str, str]:
    if _is_null_id(pid):
        return None, UNKNOWN, BASIS_NONE
    if namespace == NAMESPACE_GSIS:
        return pid, CANONICAL_RESOLVED, BASIS_VENDOR_GSIS
    if pid in colliding:
        return None, CONFLICT, BASIS_NONE
    if pid in bridge:
        return bridge[pid], CANONICAL_RESOLVED, BASIS_NAME_BRIDGE
    return None, UNKNOWN, BASIS_NONE
