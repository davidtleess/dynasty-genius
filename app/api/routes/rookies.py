from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.models.player_identity import PlayerIdentity

router = APIRouter(prefix="/rookies", tags=["rookies"])


class ProspectRequest(BaseModel):
    name: str
    position: str
    pick: int
    round: int
    age: float


def _map_prospect_to_pvo(prospect: ProspectRequest):
    identity = PlayerIdentity(
        dg_id=f"prospect_{prospect.position}_{prospect.pick}",
        full_name=prospect.name,
        position=prospect.position,
        nfl_team=None,
        verification_status="UNVERIFIED"
    )
    features = {
        "draft_capital": prospect.pick,
        "age_at_nfl_entry": prospect.age,
        "pick": prospect.pick,
        "round": prospect.round,
        "age": prospect.age,
    }
    return assemble_pvo(identity, features, is_prospect=True)


@router.post("/score")
def score_single(prospect: ProspectRequest) -> dict:
    try:
        pvo = _map_prospect_to_pvo(prospect)
        return pvo.model_dump()
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/score-class")
def score_class(prospects: list[ProspectRequest]) -> list[dict]:
    try:
        pvos = [_map_prospect_to_pvo(p) for p in prospects]
        # Sort by dynasty_value_score descending (None values last)
        pvos.sort(
            key=lambda x: (x.dynasty_value_score is not None, x.dynasty_value_score or -1.0),
            reverse=True
        )
        return [p.model_dump() for p in pvos]
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
