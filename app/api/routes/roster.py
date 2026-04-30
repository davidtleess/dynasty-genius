from fastapi import APIRouter

from app.services.roster_auditor import run_audit

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("/audit")
async def audit_roster() -> list[dict]:
    return await run_audit()
