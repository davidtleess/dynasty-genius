from fastapi import APIRouter, HTTPException

from app.services.roster_auditor import RosterConfigError, run_audit_pvo

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("/audit")
async def audit_roster() -> dict:
    try:
        return await run_audit_pvo()
    except RosterConfigError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "roster_config_error",
                "message": str(e),
            },
        )
