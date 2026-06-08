"""Surface-3 player detail endpoint (T4).

``GET /api/players/{sleeper_id}`` returns a curated, typed ``PlayerDetailResponse``
built from the universe PVO + market-divergence artifacts — never the raw PVO row.
Per-section honest degradation, market lane degrades independently, evidence text is
banned-vocabulary fail-closed (suppress + degrade), and ``decision_supported`` is
recursively False. Artifact loaders are named seams (monkeypatched in tests).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
UNIVERSE_PVO_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
MARKET_DIVERGENCE_PATH = (
    ROOT / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"
)
BANNED_VOCAB_PATH = ROOT / "frontend" / "src" / "shell" / "banned_vocabulary.json"

MODELED_ENGINE_PATHS = {"ENGINE_A", "ENGINE_B", "BLEND_AB"}

# The divergence artifact carries `signal` (direction) + `signal_status` (gate state,
# e.g. "gates_passed"). The DTO surfaces the descriptive DIRECTION, mapped from signal.
SIGNAL_TO_DIVERGENCE_STATUS = {
    "MODEL_HIGH_MARKET_LOW": "model_higher_than_market",
    "MODEL_LOW_MARKET_HIGH": "model_lower_than_market",
    "INSIDE_BAND": "inside_band",
}

router = APIRouter(prefix="/players", tags=["players"])


# --- Typed response contract ---------------------------------------------------
class PlayerIdentity(BaseModel):
    sleeper_id: str
    name: str | None
    position: str | None
    team: str | None
    age: float | None
    draft_class: int | None
    nfl_draft_pick: int | None
    nfl_draft_round: int | None


class PlayerModelLane(BaseModel):
    engine_path: str | None
    model_grade: str | None
    model_version: str | None
    dynasty_value_score: float | None
    xvar: float | None
    xvar_percentile_position: float | None
    projection_1y: float | None
    projection_2y: float | None
    projection_3y: float | None


class CounterArgumentField(BaseModel):
    text: str | None
    status: str
    caveats: list[str] = []


class EvidenceListField(BaseModel):
    items: list[str] = []
    caveats: list[str] = []


class PlayerEvidence(BaseModel):
    counter_argument: CounterArgumentField
    top_drivers: EvidenceListField
    risk_flags: EvidenceListField
    caveats: EvidenceListField


class PlayerMarketLane(BaseModel):
    status: str
    source: str | None
    market_value: float | None
    market_rank_overall: int | None
    market_rank_position: int | None
    source_timestamp: str | None
    caveats: list[str] = []


class DivergenceField(BaseModel):
    delta: float | None
    status: str


class DegradationField(BaseModel):
    message: str


class PlayerDetailResponse(BaseModel):
    sleeper_id: str
    identity: PlayerIdentity
    model_status: str
    model: PlayerModelLane | None
    evidence: PlayerEvidence | None
    market: PlayerMarketLane
    divergence: DivergenceField
    degradation: DegradationField | None
    source_timestamps: dict[str, str | None]
    caveats: list[str] = []
    decision_supported: Literal[False] = False


# --- Artifact loaders (named monkeypatch seams) --------------------------------
@lru_cache(maxsize=1)
def _load_player_detail_artifacts() -> dict[str, Any]:
    with open(UNIVERSE_PVO_PATH) as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_market_divergence_artifact() -> dict[str, Any]:
    with open(MARKET_DIVERGENCE_PATH) as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _banned_vocabulary() -> tuple[tuple[str, ...], tuple[str, ...]]:
    data = json.loads(BANNED_VOCAB_PATH.read_text())
    return (
        tuple(data.get("banned_standalone_words", [])),
        tuple(data.get("banned_phrases", [])),
    )


def _contains_banned(text: str) -> bool:
    standalone, phrases = _banned_vocabulary()
    lowered = text.lower()
    # Standalone words use word boundaries so 'robust' does not trip 'bust'.
    for word in standalone:
        if re.search(rf"\b{re.escape(word.lower())}\b", lowered):
            return True
    return any(phrase.lower() in lowered for phrase in phrases)


def _counter_argument_field(text: str | None) -> CounterArgumentField:
    if text is None:
        return CounterArgumentField(
            text=None, status="experimental", caveats=["counter_argument_unavailable"]
        )
    if _contains_banned(text):
        return CounterArgumentField(
            text=None, status="experimental", caveats=["evidence_suppressed_banned_term"]
        )
    return CounterArgumentField(text=text, status="available", caveats=[])


def _evidence_list_field(raw: list[str] | None) -> EvidenceListField:
    items = list(raw or [])
    clean = [item for item in items if not _contains_banned(item)]
    caveats = ["evidence_suppressed_banned_term"] if len(clean) != len(items) else []
    return EvidenceListField(items=clean, caveats=caveats)


def _find_row(artifact: dict[str, Any], sleeper_id: str) -> dict[str, Any] | None:
    for row in artifact.get("players") or []:
        if str(row.get("sleeper_player_id")) == sleeper_id:
            return row
    return None


def _market_and_divergence(
    divergence_artifact: dict[str, Any], sleeper_id: str
) -> tuple[PlayerMarketLane, DivergenceField]:
    div_row = _find_row(divergence_artifact, sleeper_id)
    overlay = (div_row or {}).get("market_overlay")
    if overlay:
        caveats = sorted({"market_overlay_static_caveat", *(overlay.get("caveats") or [])})
        market = PlayerMarketLane(
            status="available",
            source=overlay.get("source"),
            market_value=overlay.get("market_value"),
            market_rank_overall=overlay.get("overall_rank"),
            market_rank_position=overlay.get("position_rank"),
            source_timestamp=overlay.get("source_timestamp"),
            caveats=caveats,
        )
    else:
        market = PlayerMarketLane(
            status="unavailable",
            source=None,
            market_value=None,
            market_rank_overall=None,
            market_rank_position=None,
            source_timestamp=None,
            caveats=["market_overlay_unavailable"],
        )

    div_block = (div_row or {}).get("divergence")
    if div_block:
        signal = str(div_block.get("signal") or "").upper()
        divergence = DivergenceField(
            delta=div_block.get("model_minus_market_delta"),
            status=SIGNAL_TO_DIVERGENCE_STATUS.get(signal, "unavailable"),
        )
    else:
        divergence = DivergenceField(delta=None, status="unavailable")
    return market, divergence


@router.get("/{sleeper_id}", response_model=PlayerDetailResponse)
def get_player_detail(sleeper_id: str) -> PlayerDetailResponse:
    pvo = _load_player_detail_artifacts()
    row = _find_row(pvo, sleeper_id)
    if row is None:
        raise HTTPException(status_code=404, detail="player not found")

    player = row.get("player") or {}
    valuation = row.get("valuation") or {}
    engine_path = valuation.get("engine_path")
    modeled = engine_path in MODELED_ENGINE_PATHS

    identity = PlayerIdentity(
        sleeper_id=sleeper_id,
        name=player.get("full_name"),
        position=player.get("position"),
        team=player.get("team"),
        age=player.get("age"),
        draft_class=row.get("draft_class"),
        nfl_draft_pick=row.get("nfl_draft_pick"),
        nfl_draft_round=row.get("nfl_draft_round"),
    )

    divergence_artifact = _load_market_divergence_artifact()
    market, divergence = _market_and_divergence(divergence_artifact, sleeper_id)

    if modeled:
        model: PlayerModelLane | None = PlayerModelLane(
            engine_path=engine_path,
            model_grade=valuation.get("model_grade"),
            model_version=valuation.get("model_version"),
            dynasty_value_score=valuation.get("dynasty_value_score"),
            xvar=valuation.get("xvar"),
            xvar_percentile_position=valuation.get("xvar_percentile_position"),
            projection_1y=row.get("projection_1y"),
            projection_2y=row.get("projection_2y"),
            projection_3y=row.get("projection_3y"),
        )
        evidence: PlayerEvidence | None = PlayerEvidence(
            counter_argument=_counter_argument_field(row.get("counter_argument")),
            top_drivers=_evidence_list_field(row.get("top_drivers")),
            risk_flags=_evidence_list_field(row.get("risk_flags")),
            caveats=_evidence_list_field(row.get("caveats")),
        )
        model_status = "modeled"
        degradation: DegradationField | None = None
    else:
        model = None
        evidence = None
        model_status = "experimental"
        degradation = DegradationField(
            message="No active model score for this player category."
        )

    return PlayerDetailResponse(
        sleeper_id=sleeper_id,
        identity=identity,
        model_status=model_status,
        model=model,
        evidence=evidence,
        market=market,
        divergence=divergence,
        degradation=degradation,
        source_timestamps={
            "pvo": pvo.get("captured_at"),
            "market": divergence_artifact.get("captured_at"),
        },
        caveats=[],
        decision_supported=False,
    )
