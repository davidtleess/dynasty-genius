from pydantic import BaseModel, Field
from typing import List, Optional

class DraftPick(BaseModel):
    year: int
    round: int
    original_owner: Optional[str] = None
    is_acquired: bool = False

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
