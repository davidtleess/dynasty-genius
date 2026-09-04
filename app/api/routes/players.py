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

from src.dynasty_genius.outcome_loop.frozen_prediction_membership import (
    resolve_frozen_prediction_membership,
)
from src.dynasty_genius.pvo_source import (
    PvoSourceNotReadyError,
    resolve_pvo_source,
)

ROOT = Path(__file__).resolve().parents[3]
# F-seed-split T4: read the PVO pair through resolve_pvo_source (verified runtime when
# published, else the committed seed); never the seed path directly. The committed seed
# is the absence fallback; a present-but-unverified runtime fails closed (503 below).
PVO_SEED_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
PVO_SEED_COVERAGE_PATH = (
    ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)
PVO_RUNTIME_DIR = ROOT / "app" / "data" / "valuation_runtime"
MARKET_DIVERGENCE_PATH = (
    ROOT / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"
)
BANNED_VOCAB_PATH = ROOT / "frontend" / "src" / "shell" / "banned_vocabulary.json"
FROZEN_PREDICTION_DECLARATION_PATH = (
    ROOT / "app" / "config" / "realized_outcome_frozen_predictions.json"
)
MODEL_FORWARD_CAPTURE_DB = ROOT / "app" / "data" / "model_forward_capture.db"
FROZEN_PREDICTION_SEASON = 2026

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


class PlayerLeagueOwnership(BaseModel):
    """Where the player stands in David's league (DG-145). Read from the row's
    ``league_context`` — the latest league roster capture — and dated by the
    artifact's ``source_snapshot_captured_at``, so the card can say how old the
    fact is instead of guessing. ``unknown`` means the capture did not vouch for
    him: a missing or non-boolean ``rostered`` flag, or an undated snapshot. It is
    never dressed up as a free agent. The word "FA" is the frontend's, minted once
    in copy.ts; this field carries the fact, not the label."""

    status: Literal["rostered", "free_agent", "unknown"]
    owner_display_name: str | None
    roster_id: int | None
    as_of: str | None


class PlayerModelLane(BaseModel):
    engine_path: str | None
    model_grade: str | None
    model_version: str | None
    dynasty_value_score: float | None
    # DG-128 (2026-09-01): the band ships with the number. dvs_engine is its BASIS —
    # measured (B), draft-capital prior (A), or blend — while engine_path stays the
    # lane; a prior-dominated estimate must not render like a measured one.
    dvs_engine: Literal["A", "B", "blend"] | None = None
    dvs_band_low: float | None = None
    dvs_band_high: float | None = None
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


class FrozenPredictionCoverage(BaseModel):
    current_rostered_skill_player_count: int
    current_rostered_skill_in_frozen_prediction_cohort_count: int
    current_rostered_skill_not_in_frozen_prediction_cohort_count: int


class FrozenPredictionField(BaseModel):
    season: int
    frozen_capture_date: str | None
    status: Literal[
        "included",
        "not_in_frozen_prediction_cohort",
        "prediction_capture_incomplete",
        "unavailable",
    ]
    basis: Literal[
        "model_supported_prediction_captured",
        "non_model_route_at_freeze",
        "not_present_in_frozen_universe",
        "prediction_capture_incomplete",
        "store_unavailable_or_ambiguous",
    ]
    message: str
    coverage: FrozenPredictionCoverage | None
    decision_supported: Literal[False] = False


class PlayerDetailResponse(BaseModel):
    sleeper_id: str
    identity: PlayerIdentity
    league_ownership: PlayerLeagueOwnership
    model_status: str
    model: PlayerModelLane | None
    evidence: PlayerEvidence | None
    market: PlayerMarketLane
    divergence: DivergenceField
    frozen_prediction: FrozenPredictionField
    degradation: DegradationField | None
    source_timestamps: dict[str, str | None]
    caveats: list[str] = []
    decision_supported: Literal[False] = False


# --- Artifact loaders (named monkeypatch seams) --------------------------------
# The PVO and market-divergence artifacts are rewritten by the daily 09:15/09:45
# jobs while the server stays up, so these two loaders read per request (H0-0b,
# finding F2). Only the static committed banned-vocabulary file is cached.
def _load_player_detail_artifacts() -> dict[str, Any]:
    try:
        resolved = resolve_pvo_source(
            seed_paths={"pvo": PVO_SEED_PATH, "coverage": PVO_SEED_COVERAGE_PATH},
            runtime_dir=PVO_RUNTIME_DIR,
        )
    except PvoSourceNotReadyError as exc:
        raise HTTPException(
            status_code=503, detail="PVO runtime present but unverified"
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="Required PVO artifact not found"
        ) from exc
    with open(resolved.pvo_path) as handle:
        return json.load(handle)


def _load_market_divergence_artifact() -> dict[str, Any]:
    with open(MARKET_DIVERGENCE_PATH) as handle:
        return json.load(handle)


def _load_frozen_prediction_membership(
    sleeper_id: str, current_rostered_skill_sleeper_ids: list[str]
) -> dict[str, Any]:
    return resolve_frozen_prediction_membership(
        sleeper_id,
        season=FROZEN_PREDICTION_SEASON,
        declaration_path=FROZEN_PREDICTION_DECLARATION_PATH,
        db_path=MODEL_FORWARD_CAPTURE_DB,
        current_rostered_skill_sleeper_ids=current_rostered_skill_sleeper_ids,
    )


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


def _current_rostered_skill_sleeper_ids(artifact: dict[str, Any]) -> list[str]:
    skill_positions = {"QB", "RB", "WR", "TE"}
    return [
        str(row.get("sleeper_player_id"))
        for row in artifact.get("players") or []
        if (row.get("league_context") or {}).get("rostered") is True
        and str((row.get("player") or {}).get("position") or "").upper()
        in skill_positions
        and row.get("sleeper_player_id") is not None
    ]


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


def _league_ownership(row: dict[str, Any], artifact: dict[str, Any]) -> PlayerLeagueOwnership:
    """The one rule for who owns him in David's league (DG-145).

    David, 2026-09-03 23:35 ET, on what "free agent" means: "nobody in the league
    owns." The row's ``league_context.rostered`` is that fact as of the league
    roster capture the artifact was built from; ``source_snapshot_captured_at``
    dates it. Without a boolean flag and a date there is no fact to serve, only
    ``unknown`` — never a free-agent claim the capture did not make.
    """
    as_of = artifact.get("source_snapshot_captured_at")
    as_of = as_of if isinstance(as_of, str) and as_of else None
    context = row.get("league_context")
    rostered = context.get("rostered") if isinstance(context, dict) else None
    if not isinstance(rostered, bool) or as_of is None:
        return PlayerLeagueOwnership(
            status="unknown", owner_display_name=None, roster_id=None, as_of=as_of
        )
    if not rostered:
        return PlayerLeagueOwnership(
            status="free_agent", owner_display_name=None, roster_id=None, as_of=as_of
        )
    owner = context.get("owner_display_name")
    roster_id = context.get("roster_id")
    return PlayerLeagueOwnership(
        status="rostered",
        owner_display_name=str(owner) if owner else None,
        roster_id=int(roster_id) if isinstance(roster_id, int) and not isinstance(roster_id, bool) else None,
        as_of=as_of,
    )


def _served_team_label(player: dict[str, Any]) -> str | None:
    """A player Sleeper lists as active but on no NFL roster is a free agent; say
    so, as the roster audit does (roster_auditor.get_my_roster), instead of serving
    a blank. Anyone else with no team (inactive, retired) keeps the blank — "FA"
    would be a claim the data does not make (DG-137)."""
    team = player.get("team")
    if team:
        return str(team)
    return "FA" if player.get("sleeper_status") == "Active" else None


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
        team=_served_team_label(player),
        age=player.get("age"),
        draft_class=row.get("draft_class"),
        nfl_draft_pick=row.get("nfl_draft_pick"),
        nfl_draft_round=row.get("nfl_draft_round"),
    )

    divergence_artifact = _load_market_divergence_artifact()
    market, divergence = _market_and_divergence(divergence_artifact, sleeper_id)
    frozen_prediction = FrozenPredictionField.model_validate(
        _load_frozen_prediction_membership(
            sleeper_id, _current_rostered_skill_sleeper_ids(pvo)
        )
    )

    if modeled:
        model: PlayerModelLane | None = PlayerModelLane(
            engine_path=engine_path,
            model_grade=valuation.get("model_grade"),
            model_version=valuation.get("model_version"),
            dynasty_value_score=valuation.get("dynasty_value_score"),
            dvs_engine=row.get("dvs_engine"),
            dvs_band_low=valuation.get("dvs_band_low"),
            dvs_band_high=valuation.get("dvs_band_high"),
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
        # A modeled lane with no score must say so (DG-021): a null score beside
        # degradation=None reads as a confident label over a blank.
        degradation: DegradationField | None = (
            DegradationField(
                message=(
                    "Model lane active without a dynasty value score — "
                    "insufficient professional season data for a reliable number."
                )
            )
            if valuation.get("dynasty_value_score") is None
            else None
        )
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
        league_ownership=_league_ownership(row, pvo),
        model_status=model_status,
        model=model,
        evidence=evidence,
        market=market,
        divergence=divergence,
        frozen_prediction=frozen_prediction,
        degradation=degradation,
        source_timestamps={
            "pvo": pvo.get("captured_at"),
            # The MARKET vintage, not the artifact's build clock. `captured_at` remains the
            # fallback only for pre-Phase-0b artifacts that carry no market vintage at all.
            "market": divergence_artifact.get("market_source_timestamp")
            or divergence_artifact.get("captured_at"),
        },
        caveats=[],
        decision_supported=False,
    )
