from fastapi import APIRouter

from app.services.engine_b_service import score_inference_partition

router = APIRouter(prefix="/engine-b", tags=["engine-b"])


@router.get("/scores")
async def get_engine_b_scores() -> dict:
    """Return Engine B predictions for the current (2024) inference cohort."""
    scores = score_inference_partition()
    return {
        "status": "experimental",
        "scores": scores
    }
