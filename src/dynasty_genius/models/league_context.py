import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class DraftPick(BaseModel):
    year: int
    round: int
    original_owner_id: Optional[int] = None  # roster_id of the original owner
    original_owner_name: Optional[str] = None
    is_acquired: bool = False

class LeagueMate(BaseModel):
    roster_id: int
    user_id: str
    display_name: str
    is_opponent: bool = True

class LeagueContext(BaseModel):
    """
    The "David's Context" model. 
    Defines the specific league state for scoring and decision logic.
    """
    league_id: str
    league_name: str
    season: str

    # David's Identity in the league
    david_user_id: str
    david_display_name: str
    david_roster_id: int

    # Scoring & Format
    is_superflex: bool = True
    is_ppr: bool = True
    te_premium: float = 0.0

    # Roster state
    my_players: List[str] = Field(default_factory=list, description="List of dg_ids on David's roster")
    my_future_picks: List[DraftPick] = Field(default_factory=list)

    # League state
    league_mates: List[LeagueMate] = Field(default_factory=list)

    @classmethod
    def load_from_json(cls, path: Path) -> "LeagueContext":
        if not path.exists():
            raise FileNotFoundError(f"League context not found at {path}")
        data = json.loads(path.read_text())
        return cls(**data)
