import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.dynasty_genius.eval.backtest_artifact import BacktestResult

router = APIRouter(prefix="/trust-surface", tags=["trust-surface"])

# Published trust substrate (Model Trust Console): the route reads the governed,
# tracked published path by default; the gitignored raw runs/ remain only as a local
# subdir fallback (never the CI / clean-clone path).
RUNS_DIR = Path("app/data/backtest/trust_surface/latest")
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


class ModelCardResponse(BaseModel):
    """Curated PUBLIC model-card contract — the 8 safety/identity fields only.

    Provenance fields (model_version / model_artifact_hash / git_sha) live on the
    audit-internal PublishedModelCardSource artifact and are deliberately NOT exposed
    here, so the public surface never leaks the 9-section ModelCard internals.
    """

    position: str
    backtest_run_id: str | None = None
    generated_at: str | None = None
    is_experimental: bool
    intended_use: str
    out_of_scope_uses: list[str]
    caveats: list[str]
    known_failure_modes: list[str]


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

    # Published path is FLAT (trust_surface/latest/backtest_result_{POS}.json). Fall back
    # to the legacy run-subdir glob only when no published flat file exists (local runs/).
    flat_path = RUNS_DIR / f"backtest_result_{pos_upper}.json"
    if flat_path.is_file():
        artifact_paths = [flat_path]
    else:
        artifact_paths = list(RUNS_DIR.glob(f"*/backtest_result_{pos_upper}.json"))

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
            RUNS_DIR / f"model_card_source_{pos_upper}.json"
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


@router.get("/{position}/model-card", response_model=ModelCardResponse)
async def get_model_card(position: str) -> ModelCardResponse:
    """Return the curated public ModelCardResponse for the position.

    Reads the published, provenance-aligned PublishedModelCardSource
    (``trust_surface/latest/model_card_source_{POS}.json``) and filters it to the 8
    curated public fields — provenance fields stay audit-internal. Read-only; no card
    generation or metric computation on demand.
    """
    pos_upper = position.upper()
    if pos_upper not in _VALID_POSITIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Invalid position: {position}. Must be one of {sorted(_VALID_POSITIONS)}.",
        )

    source_path = RUNS_DIR / f"model_card_source_{pos_upper}.json"
    if not source_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No model card found for position {pos_upper}",
        )

    source = json.loads(source_path.read_text(encoding="utf-8"))
    # Curated filter — the provenance fields (model_version/hash/git_sha) are dropped.
    return ModelCardResponse(
        position=source["position"],
        backtest_run_id=source.get("backtest_run_id"),
        generated_at=source.get("generated_at"),
        is_experimental=source["is_experimental"],
        intended_use=source["intended_use"],
        out_of_scope_uses=source["out_of_scope_uses"],
        caveats=source["caveats"],
        known_failure_modes=source["known_failure_modes"],
    )
