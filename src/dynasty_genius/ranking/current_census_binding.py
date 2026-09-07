"""Binding of the reviewed, dated current-player census into an audit (DG-178 plan T1, 2026-09-06).

The census is read from an explicit run directory — never a mutable 'latest' path — and the SAME
bytes are re-hashed: `census.csv` against `report.json["census_csv_sha256"]`, and the census's own
sources (nflverse roster, Sleeper eligibility, league snapshot) against the hashes it recorded;
the season and the league snapshot identity must match the audit's; Sleeper ids must be unique.
It is read as three separate populations that are never merged into one coverage figure:
league-owned players, listed unowned players by verified NFL status, and NFL records no Sleeper
row claims. A Sleeper id's NFL attachment is 'unverified' whenever no verified join exists —
an uncovered id, a contested or unknown member, or an id absent from the census.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

REQUIRED_FILES = ("census.csv", "uncovered.csv", "report.json")
VERIFIED_CLASSES = frozenset({"active", "injured_reserve", "pup", "nfi", "practice_squad", "exempt", "suspended", "cut", "retired"})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@dataclass(frozen=True)
class CensusBinding:
    run_dir: str
    run_id: str
    season: int
    census_csv_sha256: str
    report_sha256: str
    uncovered_csv_sha256: str
    members: int
    uncovered_count: int
    identity_checks: dict[str, bool]
    sources: dict[str, Any]
    denominator_note: str
    unmatched_nfl_records: int
    contested_nfl_records: int
    bridge_joined_rows: int = 0
    _rows: dict[str, dict[str, str]] = field(default_factory=dict, repr=False)
    _uncovered: dict[str, dict[str, str]] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, run_dir: Path | str, *, season: int, league_snapshot_sha256: str,
             snapshot_owned: Optional[Mapping[str, int]] = None) -> "CensusBinding":
        """Every consumed file is captured ONCE as bytes; its hash and its parse both come from
        that buffer, so nothing can change between the hash and the parse."""
        import io

        run = Path(run_dir)
        if "latest" in run.as_posix().lower() or run.is_symlink():
            raise ValueError(f"{run} is a mutable 'latest' path or a symlink; bind an explicit immutable run directory")
        missing = [f for f in REQUIRED_FILES if not (run / f).exists()]
        if missing:
            raise ValueError(f"census run {run} lacks {missing}")
        report_bytes = (run / "report.json").read_bytes()
        census_bytes = (run / "census.csv").read_bytes()
        uncovered_bytes = (run / "uncovered.csv").read_bytes()
        report = json.loads(report_bytes)
        checks: dict[str, bool] = {}
        census_sha = hashlib.sha256(census_bytes).hexdigest()
        checks["census_csv_sha256"] = str(report.get("census_csv_sha256") or "").lower() == census_sha
        if not checks["census_csv_sha256"]:
            raise ValueError("census.csv bytes do not match report.json census_csv_sha256")
        sources_in = report.get("sources") or {}
        sources: dict[str, Any] = {}
        for key in ("nflverse_roster", "sleeper_eligibility", "league_snapshot"):
            src = sources_in.get(key) or {}
            path = Path(str(src.get("path") or ""))
            data = path.read_bytes() if path.exists() else None
            ok = data is not None and bool(src.get("sha256")) and hashlib.sha256(data).hexdigest() == str(src["sha256"]).lower()
            checks[f"{key}_sha256"] = ok
            if not ok:
                raise ValueError(f"{key} source recorded by the census does not re-hash to its recorded sha256 (or is missing)")
            sources[key] = dict(src)
        # identity bridges are a LIST of files; every one is re-hashed and kept as provenance
        bridges = sources_in.get("identity_bridge") or []
        if isinstance(bridges, dict):
            bridges = [bridges]
        kept = []
        for src in bridges:
            path = Path(str(src.get("path") or ""))
            data = path.read_bytes() if path.exists() else None
            if data is None or not src.get("sha256") or hashlib.sha256(data).hexdigest() != str(src["sha256"]).lower():
                raise ValueError(f"identity_bridge source {path} is missing or does not re-hash to its recorded sha256")
            kept.append(dict(src))
        sources["identity_bridge"] = kept
        if str((sources_in.get("league_snapshot") or {}).get("sha256") or "").lower() != league_snapshot_sha256.lower():
            raise ValueError("the census was built on a different league snapshot than this audit")
        checks["league_snapshot_sha256"] = True
        checks["season"] = int(report.get("season", -1)) == int(season)
        if not checks["season"]:
            raise ValueError(f"census season {report.get('season')} is not the audit season {season}")
        rows: dict[str, dict[str, str]] = {}
        for rec in csv.DictReader(io.StringIO(census_bytes.decode("utf-8"))):
            sid = str(rec.get("sleeper_id") or "").strip()
            if not sid:
                raise ValueError("blank sleeper_id in census.csv")
            if sid in rows:
                raise ValueError(f"duplicate sleeper_id {sid} in census.csv")
            rows[sid] = rec
        unc: dict[str, dict[str, str]] = {}
        for rec in csv.DictReader(io.StringIO(uncovered_bytes.decode("utf-8"))):
            sid = str(rec.get("sleeper_id") or "").strip()
            if not sid:
                raise ValueError("blank sleeper_id in uncovered.csv")
            if sid in unc or sid in rows:
                raise ValueError(f"duplicate sleeper_id {sid} across census.csv and uncovered.csv")
            unc[sid] = rec
        checks["unique_sleeper_ids"] = True
        bridge_rows = sum(1 for r in rows.values() if str(r.get("join_basis") or "") == "gsis_id_via_bridge")
        if bridge_rows and not kept:
            raise ValueError(f"{bridge_rows} census rows were joined through an identity_bridge but the report records no "
                             "re-hashable identity_bridge source; provenance is required, fail closed")
        checks["identity_bridge_sha256"] = True
        counts = report.get("counts") or {}
        if int(counts.get("members", -1)) != len(rows):
            raise ValueError(f"report counts.members {counts.get('members')} does not equal the {len(rows)} census rows read")
        if "uncovered" in counts and int(counts.get("uncovered", -1)) != len(unc):
            raise ValueError(f"report counts.uncovered {counts.get('uncovered')} does not equal the {len(unc)} uncovered rows read")
        checks["counts_reconcile"] = True
        # Ownership is the verified SNAPSHOT's fact: every census row's league_owned / roster_id
        # must equal the snapshot's rosters, and every owned id must be present as owned.
        if snapshot_owned is not None:
            owned = {str(k): int(v) for k, v in snapshot_owned.items()}
            bad = []
            for sid, rec in rows.items():
                claimed = str(rec.get("league_owned") or "").strip().lower() == "true"
                rid = str(rec.get("roster_id") or "").strip()
                if claimed != (sid in owned) or (claimed and rid != str(owned.get(sid))):
                    bad.append((sid, rec.get("league_owned"), rid, owned.get(sid)))
            absent = sorted(sid for sid in owned if sid not in rows)
            if bad or absent:
                raise ValueError(f"census ownership does not reconcile with the verified snapshot: mismatched {bad[:5]}, "
                                 f"owned ids absent from the census {absent[:5]}")
            checks["ownership_reconciles"] = True
        return cls(run_dir=str(run), run_id=str(report.get("run") or run.parent.name), season=int(season),
                   census_csv_sha256=census_sha, report_sha256=hashlib.sha256(report_bytes).hexdigest(),
                   uncovered_csv_sha256=hashlib.sha256(uncovered_bytes).hexdigest(), members=len(rows), uncovered_count=len(unc),
                   identity_checks=checks, sources=sources,
                   denominator_note=str(report.get("denominator_note") or ""),
                   unmatched_nfl_records=int(counts.get("nfl_rows_unclaimed") or 0),
                   contested_nfl_records=int(counts.get("contested_nfl_records") or 0),
                   bridge_joined_rows=bridge_rows, _rows=rows, _uncovered=unc)

    def member(self, sleeper_id: str) -> Optional[dict[str, str]]:
        return self._rows.get(str(sleeper_id))

    def attachment(self, sleeper_id: str) -> dict[str, Any]:
        """The NFL attachment of a Sleeper id as the census can vouch for it. Fantasy ownership is
        a separate fact and never enters this verdict."""
        sid = str(sleeper_id)
        r = self._rows.get(sid)
        if r is None:
            u = self._uncovered.get(sid)
            if u is not None:
                flags = f"Sleeper lists {u.get('sleeper_status') or '?'} with {('team ' + u['sleeper_team']) if u.get('sleeper_team') else 'no team'}"
                return {"status": "unverified", "basis": "no verified join",
                        "note": f"{u.get('reason') or 'no verified join to the captured roster'}; {flags}"}
            return {"status": "unverified", "basis": "absent", "note": "not in the census: no captured record to verify"}
        cls = str(r.get("availability_class") or "")
        if cls in VERIFIED_CLASSES and not (r.get("identity_conflict") or "").strip():
            return {"status": cls, "basis": str(r.get("join_basis") or ""), "nfl_team": r.get("nfl_team") or None,
                    "note": f"verified join to the captured {self.season} roster ({r.get('nfl_status_raw') or cls})"}
        return {"status": "unverified", "basis": str(r.get("join_basis") or ""),
                "note": f"identity {cls}: {r.get('identity_conflict') or 'no verified NFL record'}"}

    def coverage(self, board: Mapping[str, bool], owned_ids: Iterable[str], positions: Iterable[str]) -> dict[str, Any]:
        """Populations reported separately, never merged: league-owned (every owned id counted,
        including ids absent from the census), listed unowned players with a VERIFIED NFL join
        by status, unowned members with NO verified join (contested / unknown), and NFL records
        no Sleeper row claims. `board` maps Sleeper id -> whether the board carries an estimate."""
        owned = {str(x) for x in owned_ids}
        pos_list = list(positions)
        lo_class: Counter = Counter()
        lo_with = lo_without = lo_in = lo_absent = 0
        for sid in owned:
            r = self._rows.get(sid)
            if r is None:
                lo_absent += 1
                lo_class["absent_from_census"] += 1
            else:
                lo_in += 1
                lo_class[str(r.get("availability_class") or "unknown")] += 1
            if board.get(sid):
                lo_with += 1
            else:
                lo_without += 1
        listed: dict[str, dict[str, dict[str, int]]] = {p: {} for p in pos_list}
        unverified: dict[str, dict[str, int]] = {}
        for sid, r in self._rows.items():
            if sid in owned:
                continue
            pos = str(r.get("league_position") or "?")
            if pos not in listed:
                continue
            cls = str(r.get("availability_class") or "unknown")
            verified = cls in VERIFIED_CLASSES and not (r.get("identity_conflict") or "").strip()
            key = "with_forecast" if board.get(sid) else "without_forecast"
            if verified:
                listed[pos].setdefault(cls, {"with_forecast": 0, "without_forecast": 0})[key] += 1
            else:
                unverified.setdefault(pos, {"with_forecast": 0, "without_forecast": 0})[key] += 1
        return {
            "league_owned": {"total": len(owned), "in_census": lo_in, "absent_from_census": lo_absent, "by_class": dict(lo_class),
                             "with_forecast": lo_with, "without_forecast": lo_without},
            "listed_unowned": {"by_position": {p: v for p, v in listed.items() if v},
                               "note": "unowned census members with a VERIFIED join to the captured roster, by NFL status"},
            "unverified_unowned": {"by_position": unverified,
                                   "note": "census members with no verified NFL join (contested or unknown identity); "
                                           "not counted as listed, shown separately"},
            "unmatched_nfl_records": {"count": self.unmatched_nfl_records,
                                      "note": "NFL skill rows no Sleeper row claims; kept separate, never added to a denominator"},
            "uncovered_sleeper_ids": self.uncovered_count,
            "contested_nfl_records": self.contested_nfl_records,
            "denominator_note": self.denominator_note,
        }

    def to_json(self) -> dict[str, Any]:
        return {"run_dir": self.run_dir, "run_id": self.run_id, "season": self.season,
                "census_csv_sha256": self.census_csv_sha256, "report_sha256": self.report_sha256,
                "uncovered_csv_sha256": self.uncovered_csv_sha256, "members": self.members,
                "uncovered": self.uncovered_count, "identity_checks": self.identity_checks, "sources": self.sources,
                "unmatched_nfl_records": self.unmatched_nfl_records, "contested_nfl_records": self.contested_nfl_records,
                "bridge_joined_rows": self.bridge_joined_rows, "denominator_note": self.denominator_note}
