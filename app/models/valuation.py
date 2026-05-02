from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValuationEngine(str, Enum):
    ROOKIE_FORECAST = "rookie_forecast"
    ACTIVE_PLAYER_FORECAST = "active_player_forecast"


SOURCE_RANK_1_GROUND_TRUTH = 1
SOURCE_RANK_2_VALIDATED_ANALYST = 2
SOURCE_RANK_3_MARKET_SIGNAL = 3


class ConfidenceBand(BaseModel):
    low: float
    median: float
    high: float
    label: Optional[str] = None


class DynastyValuation(BaseModel):
    player_id: Optional[str] = None
    name: Optional[str] = None
    position: str
    engine: ValuationEngine
    model_version: Optional[str] = None
    source_rank: int = Field(
        default=SOURCE_RANK_1_GROUND_TRUTH,
        ge=1,
        le=3,
        description=(
            "Source hierarchy rank: 1=ground truth, 2=validated analyst, "
            "3=market signal."
        ),
    )

    dynasty_value_score: float = Field(
        ge=0.0,
        description="Unified comparable dynasty value scale shared by both engines.",
    )
    confidence_band: Optional[ConfidenceBand] = None
    projection_1y: float
    projection_2y: float
    projection_3y: float

    source_projection: Optional[dict[str, Any]] = None
    notes: list[str] = Field(default_factory=list)
