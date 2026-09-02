from fastapi import APIRouter, HTTPException

from app.api.routes.dependency_unavailable_models import (
    RosterDependencyUnavailableResponse,
)
from app.api.routes.roster_audit_models import (
    RosterAuditResponse,
    RosterDependencyError,
    assemble_response,
)
from app.services.roster_auditor import RosterConfigError, run_audit_pvo
from src.dynasty_genius.features.inference_partition import InferencePartitionError

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get(
    "/audit",
    response_model=RosterAuditResponse,
    # DG-135: declare the 503 DG-133 added, in the shape the server actually sends.
    responses={503: {"model": RosterDependencyUnavailableResponse}},
)
async def audit_roster() -> RosterAuditResponse:
    try:
        audit = await run_audit_pvo()
    except RosterConfigError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "roster_config_error", "message": str(e)},
        )
    except InferencePartitionError as e:
        # DG-133: the Engine B feature table failed the partition contract (empty,
        # unreadable, a training row in the inference season, or a repeated player).
        # That is a dependency outage, not a request error — answer the same governed
        # 503 the envelope assembler uses, carrying the bare token.
        raise HTTPException(
            status_code=503,
            detail={"error": "roster_dependency_unavailable", "message": str(e)},
        )
    try:
        return assemble_response(audit)
    except RosterDependencyError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "roster_dependency_unavailable", "message": str(e)},
        )
