"""League settings read from a Sleeper snapshot, never assumed (DG-178, DG-170).

Every structural number here — how many quarterbacks could start, how large the shared
flex pool is — is derived from ``league.roster_positions`` and the roster count in the
snapshot the caller names. Nothing carries a 12, a 24 or a 72 written down once; a league
with different slots gives different answers, and a slot name this module does not know is
refused rather than guessed.

Eligibility is Sleeper's definition of each slot NAME. That is the only place a fixed table
belongs: ``FLEX`` admits RB/WR/TE and ``WRRB_FLEX`` does not admit a tight end because that
is what the slot names mean on Sleeper, not because of anything about David's league. Which
names his league uses is read from the snapshot.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

# Sleeper slot name -> positions that may fill it. Non-starting slots admit nobody for the
# purpose of lineup capacity. Source: Sleeper league settings, roster_positions vocabulary.
SLEEPER_SLOT_ELIGIBILITY: dict[str, frozenset[str]] = {
    "QB": frozenset({"QB"}),
    "RB": frozenset({"RB"}),
    "WR": frozenset({"WR"}),
    "TE": frozenset({"TE"}),
    "K": frozenset({"K"}),
    "DEF": frozenset({"DEF"}),
    "FLEX": frozenset({"RB", "WR", "TE"}),
    "SUPER_FLEX": frozenset({"QB", "RB", "WR", "TE"}),
    "REC_FLEX": frozenset({"WR", "TE"}),
    "WRRB_FLEX": frozenset({"RB", "WR"}),
    "BN": frozenset(),
    "IR": frozenset(),
    "TAXI": frozenset(),
}
NON_STARTING_SLOTS: frozenset[str] = frozenset({"BN", "IR", "TAXI"})


class LeagueSettings(BaseModel):
    """The league facts the ranking contract declares and the lineup logic reads."""

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    season: Optional[str] = None
    teams: int = Field(..., ge=1)
    slots: dict[str, int]
    scoring: dict[str, float] = Field(default_factory=dict)
    full_ppr: bool
    te_premium: float
    taxi_slots: int = 0
    reserve_slots: int = 0
    snapshot_id: Optional[str] = None
    captured_at: Optional[str] = None

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any], snapshot_id: Optional[str] = None) -> "LeagueSettings":
        league = snapshot.get("league") or {}
        positions = list(league.get("roster_positions") or [])
        if not positions:
            raise ValueError("snapshot carries no league.roster_positions")
        unknown = sorted({p for p in positions if p not in SLEEPER_SLOT_ELIGIBILITY})
        if unknown:
            raise ValueError(
                f"unknown roster slot name(s) {unknown}: eligibility for a slot this module "
                "does not know cannot be guessed — add it with its Sleeper definition"
            )
        rosters = snapshot.get("rosters") or []
        teams = len(rosters)
        if teams < 1:
            raise ValueError("snapshot carries no rosters, so the team count is unknown")
        scoring = {k: float(v) for k, v in (league.get("scoring_settings") or {}).items()
                   if isinstance(v, (int, float))}
        settings = league.get("settings") or {}
        return cls(
            name=league.get("name"),
            season=str(league["season"]) if league.get("season") is not None else None,
            teams=teams,
            slots=dict(Counter(positions)),
            scoring=scoring,
            full_ppr=scoring.get("rec", 0.0) == 1.0,
            te_premium=float(scoring.get("bonus_rec_te", 0.0)),
            taxi_slots=int(settings.get("taxi_slots", 0) or 0),
            reserve_slots=int(settings.get("reserve_slots", 0) or 0),
            snapshot_id=snapshot_id,
            captured_at=snapshot.get("captured_at"),
        )

    @property
    def starting_slots(self) -> dict[str, int]:
        return {s: n for s, n in self.slots.items() if s not in NON_STARTING_SLOTS}

    def eligible_slots(self, position: str) -> set[str]:
        """The starting slots in THIS league that a player at ``position`` may fill."""
        pos = position.upper()
        return {s for s in self.starting_slots if pos in SLEEPER_SLOT_ELIGIBILITY[s]}

    def start_capacity(self, position: str) -> int:
        """Upper bound on how many of this position could start league-wide: every slot the
        position is eligible for, times teams. A bound by eligibility, not a replacement rule."""
        return self.teams * sum(self.slots[s] for s in self.eligible_slots(position))

    def pooled_start_capacity(self, positions: Iterable[str]) -> int:
        """Capacity for a group that competes for shared slots, counting each slot once."""
        shared: set[str] = set()
        for p in positions:
            shared |= self.eligible_slots(p)
        return self.teams * sum(self.slots[s] for s in shared)
