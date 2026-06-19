from fastapi import APIRouter, HTTPException

from app.api.routes.roster_audit_models import (
    RosterAuditResponse,
    RosterDependencyError,
    assemble_response,
)
from app.services.roster_auditor import RosterConfigError, run_audit_pvo

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("/audit", response_model=RosterAuditResponse)
async def audit_roster() -> RosterAuditResponse:
    try:
        audit = await run_audit_pvo()
    except RosterConfigError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "roster_config_error", "message": str(e)},
        )
    try:
        return assemble_response(audit)
    except RosterDependencyError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "roster_dependency_unavailable", "message": str(e)},
        )
