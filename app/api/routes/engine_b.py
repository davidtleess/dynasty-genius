from fastapi import APIRouter, HTTPException

from app.services.engine_b_service import score_inference_partition
from src.dynasty_genius.features.inference_partition import InferencePartitionError

router = APIRouter(prefix="/engine-b", tags=["engine-b"])


@router.get("/scores")
async def get_engine_b_scores() -> dict:
    """Return Engine B predictions for the current (2024) inference cohort."""
    # DG-133: the cohort is the assembler's inference season, selected fail-closed. A
    # feature table that is empty, unreadable or not one-row-per-player is a dependency
    # outage — answered as a governed 503 carrying the bare token, never a partial list
    # and never a bare 500. (The docstring above is the OpenAPI description and is
    # pinned by frontend/openapi.json; explain here, not there.)
    try:
        scores = score_inference_partition()
    except InferencePartitionError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "engine_b_dependency_unavailable", "message": str(e)},
        )
    return {
        "status": "experimental",
        "scores": scores
    }
