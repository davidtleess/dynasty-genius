from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValuationEngine(str, Enum):
    ROOKIE_FORECAST = "rookie_forecast"
    ACTIVE_PLAYER_FORECAST = "active_player_forecast"


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
