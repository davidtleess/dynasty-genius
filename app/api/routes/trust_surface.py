import json

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any

from src.dynasty_genius.eval.backtest_artifact import BacktestResult
from src.dynasty_genius.eval.model_card import ModelCard

router = APIRouter(prefix="/trust-surface", tags=["trust-surface"])

RUNS_DIR = Path("app/data/backtest/runs")
MODEL_CARDS_DIR = Path("app/data/backtest/model_cards")

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
    data = json.loads(result.json())
    data["overall_grade"] = result.promotion_gate.overall_grade
    data["experimental"] = result.promotion_gate.overall_grade == "EXPERIMENTAL"
    data["model_card_available"] = (
        MODEL_CARDS_DIR / f"{pos_upper}_model_card.json"
    ).exists()
    return data


@router.get("/{position}/model-card")
async def get_model_card(position: str) -> dict[str, Any]:
    """Return the generated ModelCard artifact for the position.

    Read-only file access. This endpoint does not run the backtest harness,
    generate cards, or compute metrics on demand.
    """
    pos_upper = position.upper()
    if pos_upper not in _VALID_POSITIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Invalid position: {position}. Must be one of {sorted(_VALID_POSITIONS)}.",
        )

    card_path = MODEL_CARDS_DIR / f"{pos_upper}_model_card.json"
    if not card_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No model card found for position {pos_upper}. "
                "Run scripts/generate_model_cards.py first."
            ),
        )

    return json.loads(ModelCard.load(card_path).json())
