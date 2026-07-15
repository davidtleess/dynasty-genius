"""Morning Tape — read-only API over the pre-built model-population artifact.

``GET /api/league/morning-tape`` serves the latest artifact written by the Morning
Tape producer. It does NOT rebuild the population or rerun the identity join — the
builder is imported only to document lineage (and is asserted never-called in the
contract test); the request path reads ``_ARTIFACT_PATH`` and nothing else.

Fail-closed (mirrors the League What-Changed route): a missing / malformed /
wrong-root / wrong-schema artifact → 503. An artifact that loads and conforms is
served as 200 with its own honest ``status`` (``degraded`` is valid loaded state,
not an error), so the descriptive caveats and receipts reach the client intact.

Frontend HOLD: backend route only, no UI in this increment.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

# ``build_model_population_artifact`` is imported to document producer lineage and
# to be the contract test's monkeypatch target; the request path serves the
# pre-built artifact and never invokes the builder (enforced by the contract test).
from app.services.morning_tape_artifact import (
    SCHEMA_VERSION,
    build_model_population_artifact,  # noqa: F401
)

_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_PATH = _ROOT / "app" / "data" / "morning_tape" / "morning_tape_latest.json"

router = APIRouter(prefix="/league", tags=["league-morning-tape"])


def _unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "morning_tape_artifact_unavailable", "message": message},
    )


@router.get("/morning-tape")
def morning_tape_surface() -> dict:
    """Read-only serve of the latest pre-built Morning Tape artifact (artifact-state)."""
    try:
        raw = _ARTIFACT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _unavailable_503(f"artifact file missing: {_ARTIFACT_PATH}") from exc
    except OSError as exc:
        raise _unavailable_503(f"artifact file unreadable: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _unavailable_503(f"malformed artifact JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise _unavailable_503("artifact root is not a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise _unavailable_503(
            f"unexpected schema_version: {data.get('schema_version')!r}"
        )

    # No-Verdict Line guard at the serve layer: never serve a verdict-bearing
    # artifact. The population is descriptive by construction; a persisted
    # ``decision_supported`` that is anything but an explicit False (artifact- or
    # player-level) is malformed or leaked verdict content — fail closed.
    if data.get("decision_supported") is not False:
        raise _unavailable_503(
            "artifact decision_supported is not False (verdict-bearing or malformed)"
        )
    players = data.get("players")
    if not isinstance(players, list):
        raise _unavailable_503("artifact players is not a list")
    for player in players:
        if not isinstance(player, dict):
            raise _unavailable_503("a player row is not an object")
        # Enforce the per-row No-Verdict disclosure exactly: every row must carry an
        # explicit ``decision_supported: false``. Missing (malformed) or anything but
        # False (verdict-bearing) fails closed — a single card can never render
        # without the disclaimer.
        if player.get("decision_supported") is not False:
            raise _unavailable_503(
                "a player row decision_supported is not an explicit False"
            )
        # The nested model bundle must also assert no-verdict exactly: a card that
        # reads model directly must never miss the disclaimer. Missing model, or a
        # model.decision_supported that is missing / None / non-bool / True, all fail
        # closed — only an explicit False passes.
        model = player.get("model")
        if not isinstance(model, dict) or model.get("decision_supported") is not False:
            raise _unavailable_503(
                "a player row model decision_supported is not an explicit False"
            )

    return data
