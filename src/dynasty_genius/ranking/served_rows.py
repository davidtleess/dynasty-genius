"""The served row, as the ranking code reads it (DG-178).

One flat record per player from ``universe_pvo_runtime.json`` carrying only what the
candidate composition needs: identity, the served score with the denominator it was divided
by and whether it was clamped, the conditional projection, and the artifact vintage. The
served rate — points a game as the product served them — is ``dvs / 100 x dvs_p90_ref``,
exact on an unclamped row and a LOWER BOUND on a clamped one (the memory rule: measuring the
live PVO artifact).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from pydantic import BaseModel, ConfigDict

SKILL_POSITIONS: frozenset[str] = frozenset({"QB", "RB", "WR", "TE"})


_GSIS = re.compile(r"^00-\d{7}$")


def _gsis_id(row: Mapping[str, Any]) -> Optional[str]:
    """identity_ids.gsis_id when present; otherwise the dg_player_id when it is gsis-shaped —
    which it is for every skill row in the served artifact while identity_ids.gsis_id is null."""
    explicit = (row.get("identity_ids") or {}).get("gsis_id")
    if explicit:
        return str(explicit)
    dg = str(row.get("dg_player_id") or "")
    return dg if _GSIS.match(dg) else None


class ServedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    player_id: str
    sleeper_id: Optional[str]
    full_name: str
    position: str
    age: Optional[float]
    dynasty_value_score: Optional[float]
    dvs_p90_ref: Optional[float]
    dvs_clamped: Optional[bool]
    dvs_engine: Optional[str]
    projection_2y: Optional[float]
    captured_at: Optional[str]
    nfl_draft_pick: Optional[int] = None
    draft_class: Optional[int] = None
    gsis_id: Optional[str] = None
    team: Optional[str] = None
    # Sleeper fantasy eligibility (lane 24974's capture): the positions David's league lets
    # him fill, his NFL roster status, and whether `position` was placed from it.
    fantasy_positions: Optional[tuple[str, ...]] = None
    nfl_status: Optional[str] = None
    placement_source: Optional[str] = None

    @property
    def served_rate_ppg(self) -> Optional[float]:
        """P x E in points a game, as served. None when there is no score or no denominator."""
        if self.dynasty_value_score is None or not self.dvs_p90_ref:
            return None
        return self.dynasty_value_score / 100.0 * self.dvs_p90_ref

    @classmethod
    def from_artifact_row(cls, row: Mapping[str, Any], captured_at: Optional[str]) -> "ServedRow":
        player = row.get("player") or {}
        valuation = row.get("valuation") or {}
        sid = row.get("sleeper_player_id")
        return cls(
            player_id=str(row.get("dg_player_id") or sid),
            sleeper_id=str(sid) if sid is not None else None,
            full_name=str(player.get("full_name") or ""),
            position=str(player.get("position") or "").upper(),
            age=player.get("age"),
            dynasty_value_score=valuation.get("dynasty_value_score"),
            dvs_p90_ref=valuation.get("dvs_p90_ref"),
            dvs_clamped=valuation.get("dvs_clamped"),
            dvs_engine=row.get("dvs_engine"),
            projection_2y=row.get("projection_2y"),
            captured_at=captured_at,
            nfl_draft_pick=int(row["nfl_draft_pick"]) if row.get("nfl_draft_pick") is not None else None,
            draft_class=int(row["draft_class"]) if row.get("draft_class") is not None else None,
            gsis_id=_gsis_id(row),
            team=player.get("team"),
        )


class ServedArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str
    captured_at: Optional[str]
    rows: list[ServedRow]
    total_rows: int
    # sleeper id -> position for every row OUTSIDE the loaded population, so a rostered
    # kicker or a two-way player the artifact lists as DB is a stated fact, not a lost id.
    other_positions: dict[str, str] = {}

    @classmethod
    def load(cls, path: Path | str, positions: frozenset[str] = SKILL_POSITIONS,
             eligibility: Optional[Mapping[str, Mapping[str, str]]] = None) -> "ServedArtifact":
        """``eligibility`` (Sleeper fantasy_positions by Sleeper id) places every row at its
        league position BEFORE the population filter, so a two-way player the artifact lists
        as DB joins the skill rows as a WR when David's league can start him there."""
        p = Path(path)
        raw_bytes = p.read_bytes()
        raw = json.loads(raw_bytes)
        captured_at = raw.get("captured_at")
        players = raw.get("players") or []
        rows, other = [], {}
        for r in players:
            pos = str((r.get("player") or {}).get("position") or "").upper()
            sid = str(r["sleeper_player_id"]) if r.get("sleeper_player_id") is not None else None
            e = (eligibility or {}).get(sid) if sid else None
            fps = tuple(x.strip().upper() for x in str((e or {}).get("fantasy_positions") or "").split("|") if x.strip())
            placed = league_placement(pos, fps) if fps else pos
            if placed in positions:
                row = ServedRow.from_artifact_row(r, captured_at)
                if e:
                    row = row.model_copy(update={"nfl_status": str(e.get("status") or "").strip() or None,
                                                 **({"fantasy_positions": fps, "position": placed,
                                                     "placement_source": "sleeper_fantasy_positions"} if fps else {})})
                rows.append(row)
            elif sid is not None:
                other[sid] = placed or "?"
        return cls(path=str(p), sha256=hashlib.sha256(raw_bytes).hexdigest(),
                   captured_at=captured_at, rows=rows, total_rows=len(players), other_positions=other)


def league_placement(position: str, fantasy_positions: tuple[str, ...]) -> str:
    """The league position a player is placed at: his artifact position when Sleeper lists
    it among his fantasy positions, else the first skill position Sleeper lists; unchanged
    when the field is missing or names no skill position. Never inferred from the NFL or
    draft position."""
    fps = tuple(str(x).upper() for x in fantasy_positions if str(x).strip())
    if not fps:
        return position
    # His own position stands only if David's league can START it; a DB|WR is a WR here.
    if position.upper() in fps and position.upper() in SKILL_POSITIONS:
        return position
    for fp in fps:
        if fp in SKILL_POSITIONS:
            return fp
    return position


def read_fantasy_eligibility(path: Path | str) -> dict[str, dict[str, str]]:
    """sleeper_eligibility.csv keyed by Sleeper id: fantasy_positions ('DB|WR'), status, team."""
    import csv

    out: dict[str, dict[str, str]] = {}
    with Path(path).open(newline="") as fh:
        for rec in csv.DictReader(fh):
            sid = str(rec.get("sleeper_id") or "").strip()
            if sid:
                out[sid] = {k: (v or "") for k, v in rec.items() if k}
    return out


def apply_fantasy_eligibility(rows: Iterable[ServedRow], eligibility: Mapping[str, Mapping[str, str]]) -> list[ServedRow]:
    """Place every row at its league position from Sleeper's fantasy_positions and carry the
    NFL status. A row absent from the capture, or with an empty field, is left as it was."""
    out = []
    for r in rows:
        e = eligibility.get(str(r.sleeper_id)) if r.sleeper_id is not None else None
        if not e:
            out.append(r)
            continue
        fps = tuple(x.strip().upper() for x in str(e.get("fantasy_positions") or "").split("|") if x.strip())
        status = str(e.get("status") or "").strip() or None
        update: dict = {"nfl_status": status}
        if fps:
            placed = league_placement(r.position, fps)
            update.update({"fantasy_positions": fps, "position": placed, "placement_source": "sleeper_fantasy_positions"})
        out.append(r.model_copy(update=update))
    return out


def apply_identity_bridge(rows: Iterable[ServedRow], sleeper_to_gsis: Mapping[str, str]) -> list[ServedRow]:
    """Fill a missing gsis id from a producer's stated Sleeper-to-gsis mapping (its
    reconciliation file). A row that already carries a gsis is never overwritten."""
    out = []
    for r in rows:
        if r.gsis_id is None and r.sleeper_id is not None and str(r.sleeper_id) in sleeper_to_gsis:
            g = str(sleeper_to_gsis[str(r.sleeper_id)]).strip()
            out.append(r.model_copy(update={"gsis_id": g}) if g else r)
        else:
            out.append(r)
    return out
