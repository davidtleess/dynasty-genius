from fastapi import APIRouter

from app.services.project_plan_loader import (
    PROJECT_PLAN_PATH,
    ProjectPlanResponse,
    load_project_plan,
)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get(
    "/project-plan",
    response_model=ProjectPlanResponse,
    include_in_schema=False,  # internal tooling: keep OpenAPI deterministic, no client churn
)
def get_project_plan() -> ProjectPlanResponse:
    # Fixed allowlisted source only; no request-supplied path. Fail-closed/degraded inside.
    return load_project_plan(PROJECT_PLAN_PATH)
