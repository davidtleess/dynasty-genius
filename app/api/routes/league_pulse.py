"""League Pulse Increment 1 — read-only decision-surface route.

`GET /api/league/pulse` reads the three pre-built Phase 17/18 `*_latest`
artifacts (no rebuild/refresh) and returns the typed, leak-proof
`LeaguePulseResponse`. Fail-closed: a missing artifact file or a systemic
assembler failure (`LeaguePulseDependencyError`) translates to 503.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.routes.league_pulse_assembler import (
    LeaguePulseDependencyError,
    assemble_league_pulse,
)
from app.api.routes.league_pulse_models import LeaguePulseResponse
from src.dynasty_genius.league_capture import load_production_league_set

_ROOT = Path(__file__).resolve().parents[3]
_VALUATION = _ROOT / "app" / "data" / "valuation"

router = APIRouter(prefix="/league", tags=["league-pulse"])


def _artifact_unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "league_pulse_artifact_unavailable", "message": message},
    )


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:  # FileNotFoundError → 503 artifact_unavailable
        return json.load(f)


_PINNED_LEAGUE_SET: ContextVar[Any] = ContextVar("league_pulse_pinned_set", default=None)


def _current_league_set() -> Any:
    """The request-pinned LeagueSet when inside the route, else a fresh resolution."""
    pinned = _PINNED_LEAGUE_SET.get()
    return pinned if pinned is not None else load_production_league_set()


def _load_team_posture() -> dict[str, Any]:
    return _load_json(_current_league_set().paths["team_posture.json"])


def _load_team_value_matrix() -> dict[str, Any]:
    return _load_json(_current_league_set().paths["team_value_matrix.json"])


def _load_league_opportunity() -> dict[str, Any]:
    return _load_json(_VALUATION / "league_opportunity_latest.json")


@router.get("/pulse", response_model=LeaguePulseResponse)
def league_pulse_surface() -> LeaguePulseResponse:
    """Read-only League Pulse over the Phase 17/18 artifacts (artifact-state)."""
    try:
        # Pin ONE resolution for the whole request: posture and matrix must come
        # from the same marker-pinned run (or the same seed set) — never mixed.
        pin_token = _PINNED_LEAGUE_SET.set(load_production_league_set())
        try:
            posture = _load_team_posture()
            value = _load_team_value_matrix()
        finally:
            _PINNED_LEAGUE_SET.reset(pin_token)
        opportunity = _load_league_opportunity()
    except FileNotFoundError as exc:
        raise _artifact_unavailable_503(str(exc)) from exc
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        # malformed/corrupt artifact (non-JSON, unreadable) → fail closed (not 500)
        raise _artifact_unavailable_503(f"malformed artifact: {exc}") from exc

    # Wrong root shape (loads but is not a JSON object) → fail closed.
    if not all(isinstance(a, dict) for a in (posture, value, opportunity)):
        raise _artifact_unavailable_503("artifact root is not a JSON object")

    try:
        return assemble_league_pulse(posture, value, opportunity)
    except LeaguePulseDependencyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "league_pulse_dependency_unavailable",
                "message": str(exc),
            },
        ) from exc
