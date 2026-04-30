from pydantic import BaseModel
from typing import Optional


class RosterSettings(BaseModel):
    wins: int
    losses: int
    ties: int = 0
    fpts: Optional[float] = None
    fpts_against: Optional[float] = None


class Roster(BaseModel):
    roster_id: int
    owner_id: str
    league_id: str
    players: list[str]
    starters: list[str]
    taxi: Optional[list[str]] = None
    ir: Optional[list[str]] = None       # mapped from Sleeper's "reserve" field
    settings: RosterSettings
