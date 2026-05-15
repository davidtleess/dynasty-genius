from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any

from src.dynasty_genius.eval.backtest_artifact import BacktestResult

router = APIRouter(prefix="/trust-surface", tags=["trust-surface"])

RUNS_DIR = Path("app/data/backtest/runs")

_VALID_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


@router.get("/{position}")
async def get_trust_surface(position: str) -> dict[str, Any]:
    """Read-only Trust Surface endpoint.

    Returns the most recent BacktestResult artifact for the position as JSON.
    overall_grade is hoisted to the top level for quick consumer access.
    No recomputation — file read only.

    Returns 404 if no artifact exists for the position.
    """
    pos_upper = position.upper()
    if pos_upper not in _VALID_POSITIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Invalid position: {position}. Must be one of {sorted(_VALID_POSITIONS)}.",
        )

    pattern = f"*/backtest_result_{pos_upper}.json"
    artifact_paths = list(RUNS_DIR.glob(pattern))

    if not artifact_paths:
        raise HTTPException(
            status_code=404,
            detail=f"No backtest artifact found for position {pos_upper}",
        )

    artifacts: list[BacktestResult] = []
    for path in artifact_paths:
        try:
            artifacts.append(BacktestResult.load(path))
        except Exception:
            continue

    if not artifacts:
        raise HTTPException(
            status_code=404,
            detail=f"No valid backtest artifacts found for position {pos_upper}",
        )

    artifacts.sort(key=lambda x: x.run_date, reverse=True)
    result = artifacts[0]

    # Serialize to JSON-safe dict; hoist overall_grade for top-level access
    data = result.model_dump(mode="json")
    data["overall_grade"] = result.promotion_gate.overall_grade
    return data
