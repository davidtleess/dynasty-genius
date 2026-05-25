from pydantic import BaseModel

class League(BaseModel):
    league_id: str
    name: str
    season: str
    status: str
    total_rosters: int
    sport: str
    season_type: str
    roster_positions: list[str]
