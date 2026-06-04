import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.dynasty_genius.eval.backtest_artifact import BacktestResult
from src.dynasty_genius.eval.model_card import ModelCard

router = APIRouter(prefix="/trust-surface", tags=["trust-surface"])

RUNS_DIR = Path("app/data/backtest/runs")
MODEL_CARDS_DIR = Path("app/data/backtest/model_cards")

_VALID_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


class ModelReliability(BaseModel):
    """QB-only descriptive model-reliability stamp (measured uncertainty, no verdict)."""

    position: str
    r2_oos_mean: float | None = None
    spearman_rho_mean: float | None = None
    caveat: str


class TrustSurfaceResponse(BacktestResult):
    """Typed Trust Surface contract: the full BacktestResult plus the hoisted,
    consumer-facing fields. Non-breaking superset of the prior dict response, so the
    frontend Hey API codegen has a real OpenAPI schema (no untyped object)."""

    overall_grade: str
    experimental: bool
    model_card_available: bool
    model_reliability: ModelReliability | None = None


@router.get("/{position}", response_model=TrustSurfaceResponse)
async def get_trust_surface(position: str) -> JSONResponse:
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

    overall_grade = result.promotion_gate.overall_grade

    # W4: QB-only model-reliability stamp — a descriptive, measured-uncertainty
    # caveat (no buy/sell/roster-action, no verdict/tier/grade). The QB engine is
    # the least-validated; a divergence read should visibly carry that.
    model_reliability: ModelReliability | None = None
    if pos_upper == "QB":
        folds = result.folds
        _r2 = [f.r2_oos for f in folds if f.r2_oos is not None]
        r2_mean = (sum(_r2) / len(_r2)) if _r2 else None
        rho_mean = (
            sum(f.spearman_rho for f in folds) / len(folds) if folds else None
        )
        model_reliability = ModelReliability(
            position="QB",
            r2_oos_mean=r2_mean,
            spearman_rho_mean=rho_mean,
            caveat=(
                "QB magnitude predictions carry elevated uncertainty: OOS "
                f"R-squared={'n/a' if r2_mean is None else round(r2_mean, 3)}, "
                f"Spearman={'n/a' if rho_mean is None else round(rho_mean, 3)}."
            ),
        )

    response = TrustSurfaceResponse(
        **result.model_dump(),
        overall_grade=overall_grade,
        experimental=overall_grade == "EXPERIMENTAL",
        model_card_available=(
            MODEL_CARDS_DIR / f"{pos_upper}_model_card.json"
        ).exists(),
        model_reliability=model_reliability,
    )

    # response_model=TrustSurfaceResponse gives the typed OpenAPI schema; returning a
    # JSONResponse lets us preserve the exact prior response shape: the W4 contract
    # requires the QB-only model_reliability key ABSENT for non-QB (not present-as-null),
    # while a present model_reliability keeps its own nested nulls (all-null r2_oos_mean).
    payload = response.model_dump(mode="json")
    if response.model_reliability is None:
        payload.pop("model_reliability", None)
    return JSONResponse(content=payload)


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
