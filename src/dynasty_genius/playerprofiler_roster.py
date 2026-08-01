"""PlayerProfiler Weekly Roster Key — the identity spine for every other PP stream.

Layer 1. This is the smallest of David's PlayerProfiler downloads and the most important,
because it is the only one that hands us a player id we did not have to infer.

**The single fact that makes this stream worth ingesting first.** From 2023 onward the
export's ``player_id`` is a **GSIS id** (``00-0023459``) — the exact canonical key Dynasty
Genius already uses. For those seasons identity is not resolved, matched, or guessed: it is
*given*. Everywhere else in the PlayerProfiler ingest we are name-matching against a
governed crosswalk and holding conflicts; here, for half the archive, that whole class of
error does not exist.

**The seam, measured 2026-08-01 across all six files.** PlayerProfiler re-platformed
between the 2022 and 2023 seasons. Three things changed at once, in the same place, in
every one of the three downloads:

===========  ==============  =========================================================
Seasons      ``player_id``   Columns
===========  ==============  =========================================================
2020         PP-internal     ``week, team, jersey_number, name, player_id`` — team is a
                             FULL name ("Arizona Cardinals"), no position, no age/dob
2021-2022    PP-internal     ``player_id, name, week, team, number, position, age``
2023-2025    **GSIS**        ``player_id, name, week, team, number, position, dob``
===========  ==============  =========================================================

So this module has to hold two incompatible ideas at once, and the design turns on refusing
to blur them:

1. **Two id namespaces are never collapsed into one column.** ``source_player_id`` keeps
   whatever the vendor wrote and ``id_namespace`` says which universe it belongs to. A
   PP-internal ``JH-3675`` and a GSIS ``00-0023459`` are not comparable strings, and a
   single ``player_id`` column would silently invite joining them.

2. **A vendor-supplied id and an id we inferred are not the same evidence.** Both may end
   up in ``dg_player_id``, so ``identity_basis`` records which one it was:
   ``vendor_gsis`` (the vendor told us) outranks ``name_bridge`` (we matched a name across
   the seam). Without that column a name-matched guess would be indistinguishable from a
   fact, which is precisely the failure this whole ingest exists to avoid.

**The bridge.** Because a player active in 2022 is usually still active in 2023, the roster
key contains its own Rosetta stone: the same human appears once under each namespace. Match
on name (disambiguated by position) and the PP-internal id resolves to a GSIS id. Measured
over 3,290 PP-internal ids: **2,147 bridge · 11 ambiguous and HELD · 13 refused outright as
``source_id_collision`` · 1,119 never appear in 2023-2025**. That last group is not a
failure — those players left the league.

**The defect that governs the design: the internal id is not unique to a human.** It is
built from *initials plus a number*, so two players who share initials can share an id.
``AS-2100`` is Andre Smith the LB (Buffalo) *and* Andre Smith the OT (Baltimore), listed in
the same week. See ``find_colliding_source_ids``. A first cut of this module keyed rows on
``(season, week, player_id)`` and silently kept whichever row came last — deleting a real
player per collision, invisibly. The key now carries name and team, and colliding ids are
never bridged and never resolved.

**Why the season comes from the filename, and what is done about it.** Unlike the
data-analysis export, the roster key carries NO season column — only ``week``. There is no
content to read it off. Rather than trust the filename silently, ``verify_season_ordering``
checks that each file's roster overlaps its claimed neighbours more than distant seasons,
which is true of real consecutive NFL rosters and false of a mislabeled file. The filename
is an assumption; this makes it a *checked* assumption.
"""

from __future__ import annotations

import csv
import re
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
)

ROSTER_TABLE = "pp_roster_week"
BRIDGE_TABLE = "pp_identity_bridge"
ROSTER_STREAM = "roster_week"

#: A GSIS id, the canonical key. Anything else is PlayerProfiler's internal namespace.
_GSIS_RE = re.compile(r"^00-\d{7}$")

NAMESPACE_GSIS = "gsis"
NAMESPACE_PP_INTERNAL = "pp_internal"

#: How we came to believe a ``dg_player_id``. Ranked: the vendor telling us beats us
#: inferring it. Consumers that care about precision can filter on this.
BASIS_VENDOR_GSIS = "vendor_gsis"
BASIS_NAME_BRIDGE = "name_bridge"
BASIS_NONE = "none"

#: A source id that provably stands for more than one human. Distinct from `conflict`
#: (we could not choose between candidates) — here the ID ITSELF is the defect.
SOURCE_ID_COLLISION = "source_id_collision"

#: The three schema eras, keyed by the exact column SET the file carries. Detection is by
#: content, not by filename or by column count — two eras could share a count.
_ERAS: dict[str, frozenset[str]] = {
    "2020_launch": frozenset({"week", "team", "jersey_number", "name", "player_id"}),
    "2021_positioned": frozenset({"player_id", "name", "week", "team", "number",
                                  "position", "age"}),
    "2023_gsis": frozenset({"player_id", "name", "week", "team", "number",
                            "position", "dob"}),
}

#: The normalized row. Every era maps into this; fields an era does not carry stay NULL
#: rather than being invented or defaulted.
ROSTER_COLUMNS = (
    "row_key", "block", "season", "week", "source_player_id", "id_namespace",
    "dg_player_id", "identity_status", "identity_basis", "identity_candidates",
    "name", "team", "team_is_full_name", "number", "position", "dob", "age", "schema_era",
)

BRIDGE_COLUMNS = (
    "row_key", "block", "pp_player_id", "dg_player_id", "bridge_status",
    "candidates", "matched_name", "matched_position",
)

#: Consecutive NFL seasons share most of their players. Below this, a claimed adjacency is
#: not credible and the season labels are not trustworthy. Deliberately loose — it is a
#: tripwire for a mislabeled file, not a roster-churn metric.
_MIN_ADJACENT_OVERLAP = 0.35


class RosterKeyError(PlayerProfilerError):
    """The roster ingest refuses rather than storing an identity it cannot stand behind."""


@dataclass(frozen=True)
class RosterExport:
    path: Path
    season: str
    schema_era: str
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    id_namespace: str
    sha256: str


#: Values PlayerProfiler writes where an id is missing. They are NOT ids, and treating them
#: as one joins every unidentified player to every other. Measured: ``#N/A`` is shared by
#: Brandon Rusnak (Dallas) and CJ Goodwin (Jacksonville), among others.
_ID_NULL_SENTINELS = frozenset({"#n/a", "n/a", "na", "null", "none", "-", "0", ""})


def _is_null_id(value: str) -> bool:
    return value.strip().lower() in _ID_NULL_SENTINELS


def _season_from_filename(path: Path) -> str:
    match = re.match(r"(\d{4})", path.name)
    if not match:
        raise RosterKeyError(
            f"roster_key_unlabelled_file: {path.name} does not begin with a 4-digit season. "
            "The roster key carries no season column, so the filename is the only label — "
            "refusing to ingest a file whose season cannot be established at all."
        )
    return match.group(1)


def _detect_era(columns: Sequence[str]) -> str:
    got = frozenset(columns)
    for era, expected in _ERAS.items():
        if got == expected:
            return era
    raise RosterKeyError(
        f"roster_key_unknown_schema_era: columns {sorted(got)} match none of the three "
        f"known eras {sorted(_ERAS)}. PlayerProfiler re-platformed once already (2022->2023) "
        "and changed the id namespace when it did. Refusing to guess a mapping: an unknown "
        "era silently mapped onto a known one is how a whole season's ids become wrong."
    )


def _detect_namespace(rows: Sequence[Mapping[str, Any]]) -> str:
    """Namespace comes from the VALUES, not the era table.

    The era already implies a namespace, but implying is not checking. If a file ever
    arrives with 2023-era columns and 2022-era ids, the era table would confidently hand
    back the wrong namespace — so the values get the final say and a mixed file refuses.
    """
    ids = [str(r.get("player_id") or "").strip() for r in rows]
    # Sentinels are not ids and must not vote on which namespace the file is in — a single
    # "#N/A" in a GSIS file would otherwise trip the mixed-namespace refusal below.
    ids = [i for i in ids if i and not _is_null_id(i)]
    if not ids:
        raise RosterKeyError(
            "roster_key_no_usable_ids: every player_id is blank or a null sentinel "
            f"({sorted(_ID_NULL_SENTINELS)}). The file's id namespace cannot be "
            "established, so its rows cannot be stored under one."
        )
    gsis = sum(1 for i in ids if _GSIS_RE.match(i))
    if gsis == len(ids):
        return NAMESPACE_GSIS
    if gsis == 0:
        return NAMESPACE_PP_INTERNAL
    raise RosterKeyError(
        f"roster_key_mixed_id_namespace: {gsis} of {len(ids)} ids are GSIS-shaped and the "
        "rest are not. A file straddling both namespaces cannot be assigned one, and "
        "storing it would put non-comparable ids in the same column."
    )


def read_roster_export(path: Path) -> RosterExport:
    path = Path(path)
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    if not rows:
        raise RosterKeyError(f"roster_key_empty_export: {path}")
    era = _detect_era(columns)
    return RosterExport(
        path=path,
        season=_season_from_filename(path),
        schema_era=era,
        columns=columns,
        rows=rows,
        id_namespace=_detect_namespace(rows),
        sha256=_sha256(path),
    )


def discover_roster_exports(paths: Iterable[Path]) -> list[RosterExport]:
    exports = [read_roster_export(Path(p)) for p in paths]
    seen: dict[str, RosterExport] = {}
    for export in exports:
        prior = seen.get(export.season)
        if prior is not None and prior.sha256 != export.sha256:
            raise RosterKeyError(
                f"roster_key_conflicting_season_files: {export.season} arrived twice with "
                f"different contents ({prior.path.name} vs {export.path.name}). One of them "
                "is mislabeled or stale; refusing to pick."
            )
        seen[export.season] = export
    return sorted(seen.values(), key=lambda e: e.season)


def verify_season_ordering(exports: Sequence[RosterExport]) -> dict[str, Any]:
    """Check the filename-derived seasons against the rosters' own content.

    The roster key has no season column, so the filename is the only label available. That
    is a weak claim, and this makes it a checked one: real consecutive NFL rosters share
    most of their players, and that similarity decays with distance. A file whose roster
    looks nothing like its claimed neighbour is mislabeled.

    This deliberately does NOT try to re-derive the season — with no external anchor it
    cannot. It detects the failure it can actually detect: labels that are inconsistent
    with each other.
    """
    names = {
        e.season: {_norm_no_suffix(str(r.get("name") or "")) for r in e.rows} - {""}
        for e in exports
    }
    seasons = sorted(names)
    checks: list[dict[str, Any]] = []
    suspect: list[str] = []
    for left, right in zip(seasons, seasons[1:]):
        a, b = names[left], names[right]
        overlap = len(a & b) / max(1, min(len(a), len(b)))
        checks.append({"pair": f"{left}->{right}", "overlap": round(overlap, 4)})
        if overlap < _MIN_ADJACENT_OVERLAP:
            suspect.append(f"{left}->{right} ({overlap:.1%})")
    if suspect:
        raise RosterKeyError(
            f"roster_key_season_ordering_implausible: adjacent seasons {suspect} share far "
            f"fewer players than consecutive NFL rosters do (floor {_MIN_ADJACENT_OVERLAP:.0%}). "
            "The season labels come from filenames and these do not look consecutive — "
            "check for a mislabeled or duplicated download before ingesting."
        )
    # Non-adjacent pairs must not out-share adjacent ones; that would mean the ordering is
    # wrong even though every adjacent pair individually cleared the floor.
    inversions = []
    for i, season in enumerate(seasons):
        for j in range(i + 2, len(seasons)):
            far = len(names[season] & names[seasons[j]]) / max(1, min(len(names[season]), len(names[seasons[j]])))
            near = len(names[season] & names[seasons[i + 1]]) / max(1, min(len(names[season]), len(names[seasons[i + 1]])))
            if far > near:
                inversions.append(f"{season}~{seasons[j]} ({far:.1%}) > {season}~{seasons[i+1]} ({near:.1%})")
    return {
        "adjacent_overlap": checks,
        "distance_inversions": inversions,
        "ordering_consistent": not inversions,
        "note": (
            "Season labels are filename-derived and content-CHECKED, not content-derived. "
            "This proves the labels are mutually consistent; it cannot prove the whole set "
            "is not shifted by a constant."
        ),
    }


def find_colliding_source_ids(exports: Sequence[RosterExport]) -> dict[str, dict[str, Any]]:
    """Find PlayerProfiler internal ids that stand for MORE THAN ONE HUMAN.

    This is the defect that makes the internal id unsafe as an identity, and it is
    structural rather than accidental: the id is **initials plus a number**, so two players
    who share initials can share an id. Measured across the six roster files:

    - ``AS-2100`` is Andre Smith the **LB** (Buffalo) *and* Andre Smith the **OT** (Baltimore)
    - ``CJ-2150`` is Chris Jones the **CB** (Tennessee) *and* Chris Jones the **NT** (Kansas City)
    - ``KD-0111`` is Kalia Davis *and* Kellen Diesch — not even the same name
    - ``AW-1812`` (medical) is Andrew Wingard *and* ArDarius Washington

    Two tests, both of which one human cannot satisfy:

    1. the id appears twice in the SAME season+week on two different teams;
    2. the id appears under two different suffix-stripped names in the same week.

    Deliberately NOT treated as evidence: differing names across *seasons* (Matt/Matthew
    Judon, Mike/Michael Badgley, Robby Anderson -> Robbie Chosen after a legal name change)
    and position-label drift for one name. Those are the same human and 1,836 ids show the
    latter — flagging them would bury the 13 real collisions in noise.

    A colliding id is never bridged and never resolved. There is no correct single answer.
    """
    per_id: dict[str, dict[tuple[str, str], set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for export in exports:
        if export.id_namespace != NAMESPACE_PP_INTERNAL:
            continue
        for row in export.rows:
            pid = str(row.get("player_id") or "").strip()
            if not pid or _is_null_id(pid):
                continue
            week = str(row.get("week") or "").strip()
            per_id[pid][(export.season, week)].add((
                str(row.get("team") or "").strip(),
                _norm_no_suffix(str(row.get("name") or "")),
            ))

    collisions: dict[str, dict[str, Any]] = {}
    for pid, weeks in per_id.items():
        teams_clash = names_clash = False
        evidence: list[str] = []
        for (season, week), pairs in sorted(weeks.items()):
            teams = {t for t, _ in pairs if t}
            names = {n for _, n in pairs if n}
            if len(teams) > 1 or len(names) > 1:
                teams_clash |= len(teams) > 1
                names_clash |= len(names) > 1
                if len(evidence) < 3:
                    evidence.append(
                        f"{season} wk{week}: teams={sorted(teams)} names={sorted(names)}"
                    )
        if teams_clash or names_clash:
            all_names = sorted({n for pairs in weeks.values() for _, n in pairs if n})
            collisions[pid] = {
                "reason": "same_week_two_teams" if teams_clash else "same_week_two_names",
                "distinct_names": all_names,
                "evidence": evidence,
            }
    return collisions


def build_identity_bridge(exports: Sequence[RosterExport]) -> dict[str, Any]:
    """Resolve PlayerProfiler's internal ids to GSIS using the roster key's own overlap.

    A player active in 2022 is usually still active in 2023, so the same human appears once
    under each namespace. That makes this stream self-bridging — no external crosswalk, no
    fuzzy matching, no draft-year heuristics.

    Ambiguity is HELD. Where a name maps to more than one GSIS id, position narrows it; if
    it still does not resolve, the bridge records ``conflict`` with the candidates named and
    resolves nothing. A PP-internal id with no 2023+ appearance is ``no_modern_appearance``
    — a distinct outcome from a failure, because it usually means the player left the league.
    """
    gsis_names: dict[str, set[str]] = defaultdict(set)
    gsis_pos: dict[str, str] = {}
    pp_names: dict[str, set[str]] = defaultdict(set)
    pp_pos: dict[str, str] = {}

    collisions = find_colliding_source_ids(exports)

    for export in exports:
        target_names = gsis_names if export.id_namespace == NAMESPACE_GSIS else pp_names
        target_pos = gsis_pos if export.id_namespace == NAMESPACE_GSIS else pp_pos
        for row in export.rows:
            pid = str(row.get("player_id") or "").strip()
            name = _norm_no_suffix(str(row.get("name") or ""))
            if not pid or not name or _is_null_id(pid):
                continue
            target_names[pid].add(name)
            position = str(row.get("position") or "").strip()
            if position:
                target_pos.setdefault(pid, position)

    by_name: dict[str, set[str]] = defaultdict(set)
    for gid, names in gsis_names.items():
        for name in names:
            by_name[name].add(gid)

    records: list[dict[str, Any]] = []
    counts = {CANONICAL_RESOLVED: 0, CONFLICT: 0, "no_modern_appearance": 0,
              SOURCE_ID_COLLISION: 0}
    for pid, names in sorted(pp_names.items()):
        if pid in collisions:
            # The id stands for two humans. Bridging it to ONE canonical id would silently
            # merge two players' careers, and the merge would look perfectly clean
            # downstream. There is no right answer here, so there is no answer.
            counts[SOURCE_ID_COLLISION] += 1
            records.append({
                "row_key": f"bridge|{pid}", "block": "bridge", "pp_player_id": pid,
                "dg_player_id": None, "bridge_status": SOURCE_ID_COLLISION,
                "candidates": ",".join(collisions[pid]["distinct_names"]),
                "matched_name": None, "matched_position": None,
            })
            continue
        candidates: set[str] = set()
        for name in names:
            candidates |= by_name.get(name, set())
        if len(candidates) > 1 and pp_pos.get(pid):
            narrowed = {g for g in candidates if gsis_pos.get(g) == pp_pos[pid]}
            candidates = narrowed or candidates
        if len(candidates) == 1:
            status, resolved = CANONICAL_RESOLVED, next(iter(candidates))
        elif candidates:
            status, resolved = CONFLICT, None
        else:
            status, resolved = "no_modern_appearance", None
        counts[status] = counts.get(status, 0) + 1
        records.append({
            "row_key": f"bridge|{pid}",
            "block": "bridge",
            "pp_player_id": pid,
            "dg_player_id": resolved,
            "bridge_status": status,
            "candidates": ",".join(sorted(candidates)) if len(candidates) > 1 else None,
            "matched_name": sorted(names)[0] if names else None,
            "matched_position": pp_pos.get(pid),
        })

    total = len(pp_names)
    return {
        "records": records,
        "summary": {
            "pp_internal_ids": total,
            "gsis_ids": len(gsis_names),
            "resolved": counts[CANONICAL_RESOLVED],
            "conflict_held": counts[CONFLICT],
            "no_modern_appearance": counts["no_modern_appearance"],
            "source_id_collision_held": counts[SOURCE_ID_COLLISION],
            "colliding_ids": sorted(collisions),
            "resolved_share_of_bridgeable": (
                round(counts[CANONICAL_RESOLVED] / (total - counts["no_modern_appearance"]), 4)
                if total - counts["no_modern_appearance"] else None
            ),
            "note": (
                "A bridged id is INFERRED from a name match across the 2022/2023 "
                "re-platform seam. It is stored with identity_basis='name_bridge' so it can "
                "never be mistaken for a vendor-supplied GSIS id."
            ),
        },
    }


def _normalize_row(row: Mapping[str, Any], export: RosterExport, season: str) -> dict[str, Any]:
    """Map one era's row onto the common shape. Absent fields stay NULL, never defaulted."""
    era = export.schema_era
    pid = str(row.get("player_id") or "").strip()
    week = str(row.get("week") or "").strip()
    name = str(row.get("name") or "").strip()
    if era == "2020_launch":
        number, position, dob, age = row.get("jersey_number"), None, None, None
        team_is_full = "1"
    elif era == "2021_positioned":
        number, position, dob, age = row.get("number"), row.get("position"), None, row.get("age")
        team_is_full = "0"
    else:
        number, position, dob, age = row.get("number"), row.get("position"), row.get("dob"), None
        team_is_full = "0"
    return {
        # The key carries name and team, not just the id. A PP-internal id can stand for
        # two humans in the same week (initials-based ids collide), and keying on the id
        # alone made the second row overwrite the first — silently deleting a real player.
        "row_key": f"roster|{season}|{week}|{pid}|{_norm_no_suffix(name)}|{row.get('team') or ''}",
        "block": season,
        "season": season,
        "week": week,
        "source_player_id": pid,
        "id_namespace": export.id_namespace,
        "name": name,
        "team": str(row.get("team") or "").strip(),
        "team_is_full_name": team_is_full,
        "number": number,
        "position": position,
        "dob": dob,
        "age": age,
        "schema_era": era,
    }


def status_marker_path(root: Path = DEFAULT_ROOT) -> Path:
    return Path(root) / "playerprofiler_roster_status_latest.json"


def run_roster_key_ingest(
    *,
    export_paths: Sequence[Path],
    db_path: Path = DEFAULT_DB_PATH,
    root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    """Discover -> verify eras and season ordering -> bridge -> store -> marker."""
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"ppr-{''.join(ch for ch in started_at if ch.isalnum())}"
    marker = status_marker_path(root)
    base = {"schema_version": "playerprofiler_roster.v1", "run_id": run_id,
            "started_at": started_at, "export_count": len(export_paths)}
    _atomic_write_json(marker, {**base, "status": "running"})

    stage = "discover"
    try:
        if not export_paths:
            raise RosterKeyError(
                "roster_key_no_exports: zero files supplied. Refusing to record a "
                "successful run over no data."
            )
        exports = discover_roster_exports(export_paths)

        stage = "season_ordering"
        ordering = verify_season_ordering(exports)

        stage = "bridge"
        bridge = build_identity_bridge(exports)
        bridge_map = {
            r["pp_player_id"]: r["dg_player_id"]
            for r in bridge["records"] if r["dg_player_id"]
        }
        bridge_conflicts = {
            r["pp_player_id"]: r["candidates"]
            for r in bridge["records"] if r["bridge_status"] == CONFLICT
        }
        colliding = {
            r["pp_player_id"]: r["candidates"]
            for r in bridge["records"] if r["bridge_status"] == SOURCE_ID_COLLISION
        }

        stage = "store"
        store = PlayerProfilerStore(db_path, season_columns=(), medical_columns=())
        _ensure_roster_tables(store)

        by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for export in exports:
            for raw in export.rows:
                row = _normalize_row(raw, export, export.season)
                pid = row["source_player_id"]
                if pid and _is_null_id(pid):
                    # "#N/A" is not an id. Two different players carry it; joining on it
                    # would merge every unidentified player into one.
                    row.update({"dg_player_id": None, "identity_status": UNKNOWN,
                                "identity_basis": BASIS_NONE,
                                "identity_candidates": "null_id_sentinel"})
                elif pid in colliding:
                    row.update({"dg_player_id": None, "identity_status": CONFLICT,
                                "identity_basis": BASIS_NONE,
                                "identity_candidates": colliding[pid]})
                elif not pid:
                    row.update({"dg_player_id": None, "identity_status": UNKNOWN,
                                "identity_basis": BASIS_NONE, "identity_candidates": None})
                elif export.id_namespace == NAMESPACE_GSIS:
                    # The vendor gave us the canonical key outright. Strongest evidence here.
                    row.update({"dg_player_id": pid, "identity_status": CANONICAL_RESOLVED,
                                "identity_basis": BASIS_VENDOR_GSIS, "identity_candidates": None})
                elif pid in bridge_map:
                    row.update({"dg_player_id": bridge_map[pid],
                                "identity_status": CANONICAL_RESOLVED,
                                "identity_basis": BASIS_NAME_BRIDGE, "identity_candidates": None})
                elif pid in bridge_conflicts:
                    row.update({"dg_player_id": None, "identity_status": CONFLICT,
                                "identity_basis": BASIS_NONE,
                                "identity_candidates": bridge_conflicts[pid]})
                else:
                    row.update({"dg_player_id": None, "identity_status": UNKNOWN,
                                "identity_basis": BASIS_NONE, "identity_candidates": None})
                by_season[export.season].append(row)

        applied: dict[str, str] = {}
        for season, rows in sorted(by_season.items()):
            deduped = list({r["row_key"]: r for r in rows}.values())
            applied[f"{ROSTER_STREAM}:{season}"] = store.apply_block(
                table=ROSTER_TABLE, stream=ROSTER_STREAM, block=season, rows=deduped,
                columns=ROSTER_COLUMNS, coverage=_roster_coverage(deduped),
                ingested_at=started_at)
        applied[f"{ROSTER_STREAM}:bridge"] = store.apply_block(
            table=BRIDGE_TABLE, stream=ROSTER_STREAM, block="bridge",
            rows=bridge["records"], columns=BRIDGE_COLUMNS,
            coverage=bridge["summary"], ingested_at=started_at)

        all_rows = [r for rows in by_season.values() for r in rows]
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
        "seasons": {e.season: {"rows": len(e.rows), "era": e.schema_era,
                               "id_namespace": e.id_namespace} for e in exports},
        "rows": {"roster_week": len(all_rows), "identity_bridge": len(bridge["records"])},
        "applied": applied,
        "season_ordering": ordering,
        "identity_bridge": bridge["summary"],
        "coverage": _roster_coverage(all_rows),
        "provenance": {
            "source": "playerprofiler",
            "stream": "weekly_roster_key",
            "delivery": "manual subscriber export (no API)",
            "private": True,
        },
    }
    _atomic_write_json(marker, status)
    return status


def _ensure_roster_tables(store: PlayerProfilerStore) -> None:
    with store._connect() as conn:
        for table, cols in ((ROSTER_TABLE, ROSTER_COLUMNS), (BRIDGE_TABLE, BRIDGE_COLUMNS)):
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                + ", ".join(f'"{c}" TEXT' for c in cols)
                + ', PRIMARY KEY ("row_key"))'
            )


def _roster_coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Coverage split by BASIS, not just by status.

    A single 'canonical' count would blend ids the vendor handed us with ids we inferred
    across the re-platform seam. Those are different strengths of evidence and the split is
    the honest reporting unit.
    """
    by_basis: dict[str, int] = defaultdict(int)
    by_status: dict[str, int] = defaultdict(int)
    for row in rows:
        by_basis[str(row.get("identity_basis") or BASIS_NONE)] += 1
        by_status[str(row.get("identity_status") or UNKNOWN)] += 1
    total = len(rows)
    return {
        "rows_total": total,
        "by_identity_status": dict(sorted(by_status.items())),
        "by_identity_basis": dict(sorted(by_basis.items())),
        "vendor_supplied_share": (
            round(by_basis[BASIS_VENDOR_GSIS] / total, 4) if total else None
        ),
        "inferred_share": round(by_basis[BASIS_NAME_BRIDGE] / total, 4) if total else None,
    }
