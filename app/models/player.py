from pydantic import BaseModel, computed_field
from typing import Optional

AGING_CLIFF = {"RB": 25, "WR": 27, "TE": 29, "QB": 32}


class Player(BaseModel):
    player_id: str
    first_name: str
    last_name: str
    position: str
    team: Optional[str] = None
    age: Optional[int] = None
    years_exp: Optional[int] = None
    college: Optional[str] = None
    draft_pick_round: Optional[int] = None
    draft_pick_number: Optional[int] = None
    entry_age: Optional[int] = None  # age at time of NFL entry, derived externally

    @computed_field
    @property
    def is_approaching_cliff(self) -> bool:
        if self.age is None or self.position not in AGING_CLIFF:
            return False
        return self.age >= AGING_CLIFF[self.position]
