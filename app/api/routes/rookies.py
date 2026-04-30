from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rookie_evaluator import score_prospect, score_draft_class

router = APIRouter(prefix="/rookies", tags=["rookies"])


class ProspectRequest(BaseModel):
    name: str
    position: str
    pick: int
    round: int
    age: float


@router.post("/score")
def score_single(prospect: ProspectRequest) -> dict:
    try:
        result = score_prospect(
            position=prospect.position,
            pick=prospect.pick,
            round_num=prospect.round,
            age=prospect.age,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    result["name"] = prospect.name
    return result


@router.post("/score-class")
def score_class(prospects: list[ProspectRequest]) -> list[dict]:
    try:
        return score_draft_class([p.model_dump() for p in prospects])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
