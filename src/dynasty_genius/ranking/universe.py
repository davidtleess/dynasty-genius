"""The eligible fantasy universe, proven from two sources and never from scored rows (DG-178 round 2).

A player is in the universe if the artifact holds him as fantasy-relevant at a skill
position, OR any league roster holds him (a rostered player is eligible by the fact of being
rostered, whatever position string the artifact carries). Everything else the artifact
holds is listed as excluded with the cohort the artifact gave it.

What cannot be verified here: multi-position eligibility. The universe capture keeps only
Sleeper's single `position` string; Sleeper's `fantasy_positions` (Travis Hunter: WR and DB)
is not captured anywhere in shared data, so a rostered non-skill-position player is marked
as such with that note, not silently classed as a receiver or a corner. Closing that gap is
a capture change, recorded, not made here.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

SKILL = frozenset({"QB", "RB", "WR", "TE"})
MULTI_POSITION_NOTE = ("rostered at a non-skill position string; Sleeper fantasy_positions is not captured by the "
                       "universe pipeline, so multi-position eligibility cannot be verified here")


@dataclass
class UniverseRow:
    sleeper_id: str
    gsis_id: Optional[str]
    name: str
    position: str
    team: Optional[str]
    age: Optional[float]
    cohort: Optional[str]
    eligibility: str                      # fantasy_relevant | rostered_non_skill_position
    rostered: bool
    roster_id: Optional[int]
    on_taxi: bool = False
    on_reserve: bool = False
    multi_position_note: Optional[str] = None
    forecast_by: Optional[str] = None
    forecast_reason: Optional[str] = None
    nfl_draft_pick: Optional[int] = None
    draft_class: Optional[int] = None
    fantasy_positions: Optional[str] = None   # Sleeper's list, '|'-joined, when captured
    nfl_status: Optional[str] = None
    # producer -> the status that producer's reconciliation file gave this row
    reconciliation: dict = field(default_factory=dict)


@dataclass
class EligibleUniverse:
    rows: list[UniverseRow]
    excluded: dict[str, int] = field(default_factory=dict)
    note: str = MULTI_POSITION_NOTE

    def mark_forecast(self, gsis_ids: Iterable[str], *, producer: str,
                      picks: Optional[Iterable[tuple[str, int, int]]] = None) -> None:
        """Mark rows a producer forecasts: by gsis id, or by (position, draft class, pick) for
        rookie files, which carry no Sleeper id and whose artifact rows carry no gsis."""
        ids = {str(g) for g in gsis_ids}
        pick_keys = {(int(c), int(k)) for _, c, k in (picks or [])}  # position is an attribute, not a key
        for r in self.rows:
            if r.forecast_by is not None:
                continue
            if r.gsis_id and r.gsis_id in ids:
                r.forecast_by = producer
            elif (r.draft_class is not None and r.nfl_draft_pick is not None
                  and (r.draft_class, r.nfl_draft_pick) in pick_keys):
                r.forecast_by = producer

    def apply_reconciliation(self, path, *, producer: str) -> None:
        """Take a producer's per-row reconciliation (one status per sleeper id) as its own
        statement: fill a missing gsis from it, keep the status per producer, and write the
        stated reason when the row has no forecast."""
        by_sid: dict[str, dict] = {}
        with Path(path).open(newline="") as fh:
            for rec in csv.DictReader(fh):
                if rec.get("sleeper_id"):
                    by_sid[str(rec["sleeper_id"])] = rec
        for r in self.rows:
            rec = by_sid.get(r.sleeper_id)
            if rec is None:
                continue
            status = (rec.get("status") or "").strip()
            r.reconciliation[producer] = status
            if not r.gsis_id and rec.get("gsis_id"):
                r.gsis_id = str(rec["gsis_id"])
            if status == "forecast" and r.forecast_by is None:
                r.forecast_by = producer
            elif status and status != "forecast" and r.forecast_by is None:
                extra = f" (source position {rec['cohort_position']})" if rec.get("cohort_position") else ""
                r.forecast_reason = f"{producer}: {status}{extra}"

    def census(self) -> dict[str, Any]:
        by_pos: dict[str, dict[str, int]] = {}
        for r in self.rows:
            d = by_pos.setdefault(r.position, {"eligible": 0, "rostered": 0, "unrostered": 0, "forecast": 0, "unforecast": 0})
            d["eligible"] += 1
            d["rostered" if r.rostered else "unrostered"] += 1
            d["forecast" if r.forecast_by else "unforecast"] += 1
        return {"eligible": len(self.rows), "rostered": sum(1 for r in self.rows if r.rostered),
                "forecast": sum(1 for r in self.rows if r.forecast_by),
                "unforecast": sum(1 for r in self.rows if not r.forecast_by),
                "by_position": by_pos, "excluded": dict(self.excluded)}

    def write_csv(self, path: Path | str) -> Path:
        p = Path(path)
        cols = ["sleeper_id", "gsis_id", "name", "position", "eligibility", "rostered", "roster_id", "on_taxi",
                "on_reserve", "team", "age", "cohort", "nfl_draft_pick", "draft_class", "forecast_by",
                "forecast_reason", "multi_position_note", "fantasy_positions", "nfl_status", "reconciliation"]
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in self.rows:
                row = {c: getattr(r, c) for c in cols}
                row["reconciliation"] = ";".join(f"{k}={v}" for k, v in r.reconciliation.items())
                w.writerow(row)
        return p


def eligible_universe(player_rows: Iterable[Mapping[str, Any]], snapshot: Mapping[str, Any],
                      artifact_rows: Optional[Iterable[Mapping[str, Any]]] = None,
                      eligibility: Optional[Mapping[str, Mapping[str, str]]] = None) -> EligibleUniverse:
    """``player_rows`` is the snapshot's player list (it carries `cohort`; the served artifact
    does not). ``artifact_rows`` optionally enriches each row with the gsis-shaped dg id and
    the draft pick/class the artifact carries. ``eligibility`` (Sleeper fantasy_positions by
    Sleeper id) is the placement authority when supplied: a DB|WR is a WR here."""
    from src.dynasty_genius.ranking.served_rows import league_placement
    enrich: dict[str, Mapping[str, Any]] = {}
    for a in artifact_rows or []:
        if a.get("sleeper_player_id") is not None:
            enrich[str(a["sleeper_player_id"])] = a
    rosters = snapshot.get("rosters") or []
    roster_of: dict[str, int] = {}
    taxi: set[str] = set()
    reserve: set[str] = set()
    for r in rosters:
        for pid in r.get("players") or []:
            roster_of[str(pid)] = int(r["roster_id"])
        taxi |= {str(x) for x in (r.get("taxi") or [])}
        reserve |= {str(x) for x in (r.get("reserve") or [])}
    rows: list[UniverseRow] = []
    excluded: dict[str, int] = {}
    seen: set[str] = set()
    for a in player_rows:
        sid = a.get("sleeper_player_id")
        if sid is None:
            continue
        sid = str(sid)
        if sid in seen:
            raise ValueError(f"duplicate Sleeper id {sid} in the player list")
        seen.add(sid)
        player = a.get("player") or {}
        pos = str(player.get("position") or a.get("position") or "").upper()
        fps_text, nfl_status = None, None
        e = (eligibility or {}).get(sid)
        if e:
            fps = tuple(x.strip().upper() for x in str(e.get("fantasy_positions") or "").split("|") if x.strip())
            if fps:
                pos = league_placement(pos, fps)
                fps_text = "|".join(fps)
            nfl_status = str(e.get("status") or "").strip() or None
        cohort = a.get("cohort")
        rostered = sid in roster_of
        extra = enrich.get(sid, a)
        dg = extra.get("dg_player_id") or a.get("dg_player_id")
        gsis = str(dg) if dg and str(dg).startswith("00-") else None
        if not player.get("full_name") and a.get("full_name"):
            player = {**player, "full_name": a.get("full_name"), "team": a.get("team"), "age": a.get("age")}
        if cohort == "FANTASY_RELEVANT" and pos in SKILL:
            elig = "fantasy_relevant"
        elif rostered:
            elig = "rostered_non_skill_position" if pos not in SKILL else "rostered_skill_position"
        else:
            excluded[str(cohort)] = excluded.get(str(cohort), 0) + 1
            continue
        rows.append(UniverseRow(
            sleeper_id=sid, gsis_id=gsis, name=str(player.get("full_name") or ""), position=pos,
            team=player.get("team"), age=player.get("age"), cohort=cohort, eligibility=elig,
            rostered=rostered, roster_id=roster_of.get(sid), on_taxi=sid in taxi, on_reserve=sid in reserve,
            multi_position_note=MULTI_POSITION_NOTE if (rostered and pos not in SKILL) else None,
            nfl_draft_pick=int(extra["nfl_draft_pick"]) if extra.get("nfl_draft_pick") is not None else None,
            draft_class=int(extra["draft_class"]) if extra.get("draft_class") is not None else None,
            fantasy_positions=fps_text, nfl_status=nfl_status,
        ))
    missing = [sid for sid in roster_of if sid not in seen]
    for sid in missing:
        rows.append(UniverseRow(sleeper_id=sid, gsis_id=None, name="", position="?", team=None, age=None, cohort=None,
                                eligibility="rostered_absent_from_artifact", rostered=True, roster_id=roster_of[sid],
                                on_taxi=sid in taxi, on_reserve=sid in reserve))
    return EligibleUniverse(rows=rows, excluded=excluded)
