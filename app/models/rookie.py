from pydantic import BaseModel
from typing import Optional


class RookieProfile(BaseModel):
    # Base player fields
    player_id: str
    first_name: str
    last_name: str
    position: str
    team: Optional[str] = None
    age: Optional[int] = None
    years_exp: Optional[int] = None
    college: Optional[str] = None

    # NFL draft capital
    nfl_pick_round: Optional[int] = None
    nfl_pick_position: Optional[int] = None  # overall pick number

    # Evaluation metrics (populated from PlayerProfiler, PFF, RAS)
    dominator_rating: Optional[float] = None
    yprr: Optional[float] = None             # yards per route run (PFF)
    ras_score: Optional[float] = None        # Relative Athletic Score
    snap_pct_year1: Optional[float] = None   # year 1 snap share
    target_share: Optional[float] = None     # target share in final college season

    # Populated by rookie evaluator service
    dynasty_grade: Optional[str] = None      # e.g. "A", "B+", "C"
    needs_fit: Optional[bool] = None         # True if fits your roster needs
