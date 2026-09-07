"""Explicitly enabled local comparison; configured errors never fall back to old scores."""

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dynasty_genius.ranking.market_ranks import SourceError, load_market_ranks

router = APIRouter(prefix="/research")


class RankInterval(BaseModel):
    start: int
    end: int
    total: int


class RankComparison(BaseModel):
    direction: Literal["higher", "lower", "same", "overlap", "unavailable"]
    gap_min: int | None
    gap_max: int | None


class RankSeason(BaseModel):
    season: int
    advantage: float


class MarketRankPlayer(BaseModel):
    sleeper_id: str
    name: str
    position: str
    team: str | None
    on_roster: bool
    league_ownership: str
    taxi_or_reserve: bool | None
    model_value: float | None
    market_value: float | None
    our_rank: RankInterval | None
    market_rank: RankInterval | None
    model_rank_all: RankInterval | None
    market_rank_published: int | None
    comparison: RankComparison
    missing_reason: str | None
    model_zero_tie: bool
    seasons: list[RankSeason]
    reference_player: str | None


class MarketRankSource(BaseModel):
    report_run: str
    report_sha256: str
    market_sha256: str
    league_sha256: str
    forecast_date: str
    market_as_of: str
    ownership_as_of: str


class MarketRankBasis(BaseModel):
    years: list[int]
    season_weights: list[float]
    summary: str
    market_proxy_note: str
    scoring_note: str


class MarketRankCoverage(BaseModel):
    model_players: int
    market_players: int
    market_picks: int
    common_players: int
    total_players: int
    roster_players: int
    roster_common_players: int


class MarketRanksAvailable(BaseModel):
    status: Literal["available"]
    source: MarketRankSource
    basis: MarketRankBasis
    coverage: MarketRankCoverage
    rows: list[MarketRankPlayer]


class MarketRanksNotConfigured(BaseModel):
    status: Literal["not_configured"]


@router.get(
    "/market-ranks", response_model=MarketRanksAvailable | MarketRanksNotConfigured
)
def market_ranks():
    manifest = os.environ.get("DG_MARKET_RANKS_MANIFEST")
    if manifest is None:
        return {"status": "not_configured"}
    try:
        if not manifest or not Path(manifest).is_absolute():
            raise SourceError("Comparison manifest must be an absolute path")
        return load_market_ranks(Path(manifest))
    except SourceError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Us vs market is unavailable: {exc}. No older scores have been substituted.",
        ) from exc
