from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo

router = APIRouter(prefix="/rookies", tags=["rookies"])


class ProspectRequest(BaseModel):
    name: str
    position: str
    pick: int
    round: int
    age: float
    sleeper_id: Optional[str] = None
    draft_class: Optional[int] = None
    # TE Head A v3 college features — optional; when supplied, v3 scorer fires.
    # Absent = graceful fallback to v2 (pick/round/age only).
    final_college_age: Optional[float] = None
    te_ryptpa_final: Optional[float] = None
    te_yards_per_reception_career: Optional[float] = None


def _map_prospect_to_pvo(prospect: ProspectRequest):
    from src.dynasty_genius.adapters.prospect_identity_resolver import (
        resolve_prospect_sleeper_id,
    )
    draft_class = prospect.draft_class or date.today().year
    resolved_sid, _ = resolve_prospect_sleeper_id(
        prospect.name,
        prospect.position,
        draft_class,
        explicit_sleeper_id=prospect.sleeper_id,
    )
    identity = PlayerIdentity(
        dg_id=f"prospect_{prospect.position}_{prospect.pick}",
        full_name=prospect.name,
        position=prospect.position,
        nfl_team=None,
        sleeper_id=resolved_sid,
        verification_status="UNVERIFIED"
    )
    features = {
        "draft_capital": prospect.pick,
        "age_at_nfl_entry": prospect.age,
        "pick": prospect.pick,
        "round": prospect.round,
        "age": prospect.age,
        "final_college_age": prospect.final_college_age,
        "te_ryptpa_final": prospect.te_ryptpa_final,
        "te_yards_per_reception_career": prospect.te_yards_per_reception_career,
    }
    return assemble_pvo(identity, features, is_prospect=True)


@router.post("/score")
def score_single(prospect: ProspectRequest) -> dict:
    try:
        from src.dynasty_genius.services.market_overlay_service import (
            enrich_pvo_list_with_market_overlay,
        )
        pvo = _map_prospect_to_pvo(prospect)
        enrich_pvo_list_with_market_overlay([pvo])
        return pvo.dict()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/score-class")
def score_class(prospects: list[ProspectRequest]) -> list[dict]:
    try:
        from src.dynasty_genius.services.market_overlay_service import (
            enrich_pvo_list_with_market_overlay,
        )
        pvos = [_map_prospect_to_pvo(p) for p in prospects]
        pvos.sort(
            key=lambda x: (x.dynasty_value_score is not None, x.dynasty_value_score or -1.0),
            reverse=True,
        )
        enrich_pvo_list_with_market_overlay(pvos)
        return [p.dict() for p in pvos]
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
