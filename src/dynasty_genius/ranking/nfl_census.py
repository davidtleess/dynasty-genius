"""The current-player census (DG-178, Week-17 queue, 2026-09-06).

WHO IS A CURRENT NFL PLAYER TODAY is decided by a DATED NFL roster source (nflverse
``roster_<season>.csv``, captured run-local with its hash), never by Sleeper's ``active`` /
``team`` flags — Ben Roethlisberger carries Active/PIT on Sleeper years after retiring. The
denominator is stated once, below, and every row says how it was joined:

* join by ``sleeper_id`` when the nflverse row carries one, else by ``gsis_id``; a row joined
  by Sleeper id whose gsis ids disagree is an IDENTITY CONFLICT (class unknown, never guessed);
* every player David's league owns is a member regardless of source flags (Tank Dell on IR
  stays), with class ``not_on_nfl_roster_<season>`` when no nflverse row claims him;
* Sleeper skill-eligible players on no NFL roster are UNCOVERED and listed in full with the
  reason, never dropped silently; nflverse rows no Sleeper player claims are listed too.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from src.dynasty_genius.ranking.served_rows import SKILL_POSITIONS, league_placement

NFL_ROSTER_COLUMNS = ("season", "team", "position", "status", "full_name", "gsis_id", "sleeper_id")


def load_nfl_roster(csv_path, manifest_path, *, season: int) -> list[dict[str, Any]]:
    """The captured roster, validated against its capture manifest before any use: the manifest
    must exist, its sha256 and row count must match the bytes read, every row must carry the
    requested season, and the join columns must be present. A 2025 row never becomes 2026."""
    import csv as _csv
    import hashlib
    import io
    import json
    from pathlib import Path as _P

    csv_p, man_p = _P(csv_path), _P(manifest_path)
    if not man_p.exists():
        raise ValueError(f"roster capture manifest {man_p} is missing; an unvalidated capture is not a census source")
    m = json.loads(man_p.read_text())
    raw = csv_p.read_bytes()
    if str(m.get("sha256") or "").lower() != hashlib.sha256(raw).hexdigest():
        raise ValueError("roster capture sha256 in the manifest does not match the bytes read")
    reader = _csv.DictReader(io.StringIO(raw.decode("utf-8")))
    missing = [c for c in NFL_ROSTER_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"roster capture lacks required columns {missing}")
    rows = list(reader)
    if int(m.get("rows", -1)) != len(rows):
        raise ValueError(f"roster capture manifest declares {m.get('rows')} rows; {len(rows)} read")
    if int(m.get("season", -1)) != season:
        raise ValueError(f"roster capture manifest is for season {m.get('season')}, not the requested {season}")
    bad = sorted({r.get("season") for r in rows if str(r.get("season")).strip() != str(season)})
    if bad:
        raise ValueError(f"roster capture carries rows for season(s) {bad}, not only the requested {season}")
    return rows


def merge_identity_bridges(sources: Iterable[tuple[str, Iterable[Mapping[str, Any]]]]) -> dict[str, str]:
    """Verified Sleeper-id -> gsis maps from several producer reconciliations, merged only where
    they agree: a Sleeper id mapped to two different gsis ids inside one file is a duplicate,
    across files a conflict; both are refused, never first-file-wins."""
    out: dict[str, str] = {}
    owner: dict[str, str] = {}
    for name, rows in sources:
        seen: dict[str, str] = {}
        for rec in rows:
            sid = str(rec.get("sleeper_id") or "").strip()
            g = str(rec.get("my_gsis_id") or rec.get("gsis_id") or "").strip()
            if not sid or not g.startswith("00-"):
                continue
            if sid in seen and seen[sid] != g:
                raise ValueError(f"duplicate Sleeper id {sid} maps to {seen[sid]} and {g} inside bridge {name}")
            seen[sid] = g
        for sid, g in seen.items():
            if sid in out and out[sid] != g:
                raise ValueError(f"identity bridge conflict for Sleeper id {sid}: {owner[sid]} says {out[sid]}, {name} says {g}")
            out[sid], owner[sid] = g, name
    return out

DENOMINATOR_DEFINITION = (
    "current-player census = every Sleeper player whose fantasy_positions include a position David's league can start "
    "(QB/RB/WR/TE) AND who appears on the dated nflverse roster file for the season (any listed status: ACT, RES, PUP, "
    "NON, DEV, EXE, SUS, CUT, RET), PLUS every player owned in David's league regardless of any source flag. Sleeper's "
    "active/status/team fields are recorded on each row and never define membership."
)

_STATUS = {"ACT": "active", "RES": "injured_reserve", "PUP": "pup", "NON": "nfi", "DEV": "practice_squad",
           "EXE": "exempt", "SUS": "suspended", "CUT": "cut", "RET": "retired"}


def classify_nfl_status(status: Optional[str]) -> str:
    s = (status or "").strip().upper()
    if not s:
        return "unknown"
    return _STATUS.get(s, f"other:{s}")


@dataclass(frozen=True)
class CensusRow:
    sleeper_id: str
    name: str
    league_position: str
    fantasy_positions: str
    sleeper_status: str
    sleeper_team: str
    sleeper_gsis_id: str
    nfl_team: Optional[str]
    nfl_position: Optional[str]
    nfl_status_raw: Optional[str]
    nfl_gsis_id: Optional[str]
    availability_class: str
    join_basis: str                 # sleeper_id | gsis_id | none
    identity_conflict: Optional[str]
    league_owned: bool
    roster_id: Optional[int]
    contested_nfl_gsis_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass(frozen=True)
class Uncovered:
    sleeper_id: str
    name: str
    league_position: str
    sleeper_status: str
    sleeper_team: str
    sleeper_gsis_id: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class Census:
    season: int
    rows: list[CensusRow]
    uncovered: list[Uncovered]
    nfl_rows_unclaimed: list[tuple]
    sources: dict[str, Any] = field(default_factory=dict)

    def report(self) -> dict[str, Any]:
        by_class = Counter(r.availability_class for r in self.rows)
        contested = {}
        for r in self.rows:
            if r.identity_conflict and "claimed by" in r.identity_conflict and r.contested_nfl_gsis_id:
                contested.setdefault(r.contested_nfl_gsis_id, []).append(r.sleeper_id)
        by_pos_class: dict[str, dict[str, int]] = {}
        for r in self.rows:
            by_pos_class.setdefault(r.league_position, {})
            by_pos_class[r.league_position][r.availability_class] = by_pos_class[r.league_position].get(r.availability_class, 0) + 1
        return {
            "season": self.season,
            "denominator": DENOMINATOR_DEFINITION,
            "sleeper_flags_are_membership": False,
            "sources": self.sources,
            "denominator_note": (f"members = players LISTED on the captured {self.season} roster file (any status, cut and retired "
                                 "included) OR owned in David's league; NOT a count of active NFL players — read active_nfl for that"),
            "counts": {
                "members": len(self.rows),
                "listed_or_owned": len(self.rows),
                "active_nfl": by_class.get("active", 0),
                "by_class": dict(by_class),
                "by_class_and_position": by_pos_class,
                "by_join_basis": dict(Counter(r.join_basis for r in self.rows)),
                "league_owned": sum(1 for r in self.rows if r.league_owned),
                "identity_conflicts": sum(1 for r in self.rows if r.identity_conflict),
                "uncovered": len(self.uncovered),
                "uncovered_by_reason": dict(Counter(u.reason for u in self.uncovered)),
                "uncovered_by_position": dict(Counter(u.league_position for u in self.uncovered)),
                "nfl_rows_unclaimed": len(self.nfl_rows_unclaimed),
                "nfl_rows_unclaimed_by_status": dict(Counter(str(t[3]) for t in self.nfl_rows_unclaimed)),
                "contested_nfl_records": len(contested),
                "owned_absent_from_sleeper_capture": sum(1 for r in self.rows if r.join_basis == "none" and r.league_position == "?"),
            },
            "contested_nfl_records": [{"nfl_gsis_id": g, "claimants": sorted(ids)} for g, ids in sorted(contested.items())],
            "identity_conflicts": [r.to_dict() for r in self.rows if r.identity_conflict],
            "uncovered": [u.to_dict() for u in self.uncovered],
            "nfl_rows_unclaimed": [list(t) for t in self.nfl_rows_unclaimed],
        }


def _fps(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(x.strip().upper() for x in str(row.get("fantasy_positions") or "").split("|") if x.strip())


def build_census(sleeper_rows: Iterable[Mapping[str, Any]], nfl_rows: Iterable[Mapping[str, Any]], *,
                 league_owned: Mapping[str, int], season: int,
                 sources: Optional[Mapping[str, Any]] = None,
                 identity_bridge: Optional[Mapping[str, str]] = None) -> Census:
    """``identity_bridge`` is a VERIFIED Sleeper-id -> gsis map from a producer's reconciliation
    (lane 24974's 80 rookies, lane 23481's veterans); it joins only when neither direct key
    does, the row says so (``gsis_id_via_bridge``), and a Sleeper gsis that disagrees with the
    bridge is a conflict, never resolved by preference."""
    nfl = list(nfl_rows)
    bridge = {str(k): str(v).strip() for k, v in (identity_bridge or {}).items() if str(v).strip()}
    # Source keys must be unique; a dictionary that overwrote a duplicate would pick a winner silently.
    for key in ("sleeper_id", "gsis_id"):
        seen: dict[str, int] = {}
        for r in nfl:
            v = str(r.get(key) or "").strip()
            if v:
                seen[v] = seen.get(v, 0) + 1
        dups = sorted(k for k, n in seen.items() if n > 1)
        if dups:
            raise ValueError(f"roster source {key} is not unique: {dups[:5]}")
    sleeper = list(sleeper_rows)
    sids = Counter(str(r.get("sleeper_id") or "").strip() for r in sleeper if str(r.get("sleeper_id") or "").strip())
    dup_sids = sorted(k for k, n in sids.items() if n > 1)
    if dup_sids:
        raise ValueError(f"Sleeper capture sleeper_id is not unique: {dup_sids[:5]}")
    by_sid = {str(r["sleeper_id"]).strip(): r for r in nfl if str(r.get("sleeper_id") or "").strip()}
    by_gsis = {str(r["gsis_id"]).strip(): r for r in nfl if str(r.get("gsis_id") or "").strip()}
    owned = {str(k): int(v) for k, v in league_owned.items()}
    no_join_class = f"no_verified_join_to_{season}_roster"

    # Pass 1: each Sleeper row's candidate NFL record, basis and any gsis conflict.
    staged: list[tuple[Mapping[str, Any], str, tuple[str, ...], str, Optional[Mapping[str, Any]], str, Optional[str]]] = []
    seen_sleeper: set[str] = set()
    for s in sleeper:
        sid = str(s.get("sleeper_id") or "").strip()
        if not sid:
            continue
        seen_sleeper.add(sid)
        fps = _fps(s)
        skill = any(p in SKILL_POSITIONS for p in fps)
        is_owned = sid in owned
        if not skill and not is_owned:
            continue
        pos = league_placement(str(s.get("position") or "").upper(), fps)
        sgsis = str(s.get("gsis_id") or "").strip()
        n = by_sid.get(sid)
        basis, conflict = "none", None
        if n is not None:
            basis = "sleeper_id"
            ngsis = str(n.get("gsis_id") or "").strip()
            if sgsis and ngsis and sgsis != ngsis:
                conflict = f"sleeper gsis {sgsis} != nflverse gsis {ngsis} on the sleeper_id join"
        elif sgsis and sgsis in by_gsis:
            n, basis = by_gsis[sgsis], "gsis_id"
        elif sid in bridge and bridge[sid] in by_gsis:
            n, basis = by_gsis[bridge[sid]], "gsis_id_via_bridge"
            if sgsis and sgsis != bridge[sid]:
                conflict = f"sleeper gsis {sgsis} != bridge gsis {bridge[sid]}"
        # A fallback join must not contradict the NFL row's own Sleeper id: a row that names a
        # different non-empty Sleeper id is incompatible regardless of how many rows claim it.
        if n is not None and basis in ("gsis_id", "gsis_id_via_bridge"):
            n_sid = str(n.get("sleeper_id") or "").strip()
            if n_sid and n_sid != sid:
                note = (f"nflverse row for gsis {str(n.get('gsis_id') or '')} names Sleeper id {n_sid}, not {sid}, on the "
                        f"{basis} join; incompatible source ids")
                conflict = f"{conflict}; {note}" if conflict else note
        staged.append((s, sid, fps, pos, n, basis, conflict))

    # Pass 2: an NFL record claimed by more than one Sleeper row is CONTESTED; neither source is
    # presumed right, every claimant is quarantined as unknown.
    claims: dict[int, list[str]] = {}
    for _, sid, _, _, n, _, _ in staged:
        if n is not None:
            claims.setdefault(id(n), []).append(sid)
    rows: list[CensusRow] = []
    uncovered: list[Uncovered] = []
    claimed: set[int] = set()
    for s, sid, fps, pos, n, basis, conflict in staged:
        sgsis = str(s.get("gsis_id") or "").strip()
        is_owned = sid in owned
        contested_gsis = None
        if n is not None and len(claims[id(n)]) > 1:
            others = sorted(x for x in claims[id(n)] if x != sid)
            contested_gsis = str(n.get("gsis_id") or "")
            note = (f"nflverse record {contested_gsis} ({n.get('full_name')}) claimed by {len(claims[id(n)])} Sleeper rows "
                    f"({', '.join(sorted(claims[id(n)]))}); this row via {basis}; others {', '.join(others)}")
            conflict = f"{conflict}; {note}" if conflict else note
            cls = "unknown"
            nfl_fields = (None, None, None, None)
        elif n is not None and conflict and "incompatible source ids" in conflict:
            cls = "unknown"
            nfl_fields = (None, None, None, None)  # the record is not his to carry
        elif n is not None:
            claimed.add(id(n))
            cls = "unknown" if conflict else classify_nfl_status(n.get("status"))
            nfl_fields = (n.get("team"), str(n.get("position") or "").upper(), n.get("status"), str(n.get("gsis_id") or ""))
        elif is_owned:
            cls = no_join_class
            nfl_fields = (None, None, None, None)
        else:
            uncovered.append(Uncovered(sid, str(s.get("full_name") or ""), pos, str(s.get("status") or ""),
                                       str(s.get("team") or ""), sgsis,
                                       f"no verified join to the captured {season} roster (Sleeper flags "
                                       f"{s.get('status') or '?'}/{s.get('team') or '-'} are not membership); "
                                       f"absence from the NFL is not proven"))
            continue
        rows.append(CensusRow(
            sleeper_id=sid, name=str(s.get("full_name") or ""), league_position=pos, fantasy_positions="|".join(fps),
            sleeper_status=str(s.get("status") or ""), sleeper_team=str(s.get("team") or ""), sleeper_gsis_id=sgsis,
            nfl_team=nfl_fields[0], nfl_position=nfl_fields[1], nfl_status_raw=nfl_fields[2], nfl_gsis_id=nfl_fields[3],
            availability_class=cls, join_basis=basis, identity_conflict=conflict,
            league_owned=is_owned, roster_id=owned.get(sid), contested_nfl_gsis_id=contested_gsis,
        ))
    # Every owned id is retained even when the Sleeper capture lacks it: an explicit unknown row.
    for sid, rid in sorted(owned.items()):
        if sid not in seen_sleeper:
            rows.append(CensusRow(
                sleeper_id=sid, name="", league_position="?", fantasy_positions="", sleeper_status="", sleeper_team="",
                sleeper_gsis_id="", nfl_team=None, nfl_position=None, nfl_status_raw=None, nfl_gsis_id=None,
                availability_class="unknown", join_basis="none",
                identity_conflict="owned Sleeper id absent from the Sleeper eligibility capture; identity and eligibility unknown",
                league_owned=True, roster_id=rid,
            ))
    unclaimed = [(r.get("full_name"), r.get("team"), r.get("position"), r.get("status"), r.get("gsis_id"))
                 for r in nfl if id(r) not in claimed and str(r.get("position") or "").upper() in SKILL_POSITIONS]
    return Census(season=season, rows=rows, uncovered=uncovered, nfl_rows_unclaimed=unclaimed, sources=dict(sources or {}))
