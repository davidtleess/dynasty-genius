"""DG-021 — a row with no prior must say so.

114 served player cards carried ``dvs_engine="A"`` and the caveat "Engine A
prospect score used as prior", emitted from the exact branch that runs BECAUSE no
Engine A result was produced (the dead-window else-arm in ``pvo_assembler``), and
the player API served such rows as ``modeled`` with ``degradation=None`` beside a
null score. The product stated something about itself that was not true.

These tests pin the honest behavior:

  * no A and no B      -> ``dvs_engine`` is None, no prior caveat, and an explicit
                          no-score caveat instead
  * A genuinely used   -> the prior claim SURVIVES, because there it is true
  * route assembly     -> a scoreless no-prior row is never filed under ENGINE_A
  * the player API     -> a modeled row with a null score always carries a
                          degradation notice — never a blank beside a confident label
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes.players as players_route
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.universe_pvo_batch import _route_from_pvo

FALSE_CLAIM = "Engine A prospect score used as prior"
HONEST_CLAIM = "no dynasty value score available"


def _identity(position: str = "WR") -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_a_row_with_no_prior_never_claims_one() -> None:
    """Dead window, undrafted (no Engine A inputs), n too small to blend."""
    pvo = assemble_pvo(
        _identity(),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
            "games_t": 4,
            "feature_season": 2024,
            # no pick / round / age -> no Engine A result can exist
        },
    )
    assert pvo.dynasty_value_score is None
    assert pvo.dvs_engine is None, (
        "dvs_engine names the engine that produced the score; no engine produced "
        f"one, so 'A' is a false claim — got {pvo.dvs_engine!r}"
    )
    assert not any(FALSE_CLAIM in c for c in pvo.caveats), (
        f"a row with no prior must not claim one — caveats: {pvo.caveats}"
    )
    assert any(HONEST_CLAIM in c for c in pvo.caveats), (
        f"the absence of a score must be said outright — caveats: {pvo.caveats}"
    )


def test_the_true_prior_claim_survives_where_it_is_true() -> None:
    """n=0 with real Engine A inputs: the A-prior fallback is genuinely used."""
    pvo = assemble_pvo(
        _identity(),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
            "games_t": 0,
            "feature_season": 2024,
            "pick": 10.0,
            "round": 1.0,
            "age_at_nfl_entry": 22.0,  # DG-128 (2026-09-01): a veteran's `age` is his CURRENT age; Engine A reads the draft-season age from this key.
        },
    )
    assert pvo.dvs_engine == "A"
    assert pvo.dynasty_value_score is not None
    assert any(FALSE_CLAIM in c for c in pvo.caveats), (
        "where an Engine A prior IS used, saying so is the truth and must survive"
    )


def test_route_assembly_files_no_prior_scoreless_rows_honestly() -> None:
    """dvs_engine=None must never route to ENGINE_A on its own."""
    assert (
        _route_from_pvo(
            {"dvs_engine": None, "engine_used": "engine_b", "model_grade": "EXPERIMENTAL"}
        )
        == "ENGINE_B"
    )
    assert (
        _route_from_pvo({"dvs_engine": None, "engine_used": None, "model_grade": None})
        == "PRE_MODEL"
    )


# --- the serving surface -----------------------------------------------------


def _client(monkeypatch, pvo_artifact: dict[str, Any]) -> TestClient:
    monkeypatch.setattr(
        players_route, "_load_player_detail_artifacts", lambda: pvo_artifact, raising=False
    )
    monkeypatch.setattr(
        players_route,
        "_load_market_divergence_artifact",
        lambda: {"captured_at": "2026-08-25T00:00:00Z", "players": []},
        raising=False,
    )
    # DISCLOSED TEST CHANGE (DG-022 rebase, 2026-08-25): the route gained a
    # third artifact seam. Without this patch these tests silently read the
    # production capture DB — the same hermeticity rule the header states.
    monkeypatch.setattr(
        players_route,
        "_load_frozen_prediction_membership",
        lambda _sleeper_id, _rostered_ids: {
            "season": 2026,
            "frozen_capture_date": "2026-08-05",
            "status": "not_in_frozen_prediction_cohort",
            "basis": "not_present_in_frozen_universe",
            "message": "No model prediction was frozen for 2026 outcome evaluation.",
            "coverage": None,
            "decision_supported": False,
        },
        raising=False,
    )
    app = FastAPI()
    app.include_router(players_route.router, prefix="/api")
    return TestClient(app)


def _served_row(*, dynasty_value_score: float | None) -> dict[str, Any]:
    return {
        "sleeper_player_id": "9999",
        "player": {"full_name": "Fixture Player", "position": "WR", "team": "LVR", "age": 24.0},
        "valuation": {
            "engine_path": "ENGINE_B",
            "model_grade": "EXPERIMENTAL",
            "model_version": "fixture_model_v1",
            "dynasty_value_score": dynasty_value_score,
            "xvar": None,
            "xvar_percentile_position": None,
            "decision_supported": False,
        },
        "counter_argument": None,
        "top_drivers": [],
        "risk_flags": [],
        "caveats": [],
        "draft_class": 2022,
        "nfl_draft_pick": None,
        "nfl_draft_round": None,
        "projection_1y": None,
        "projection_2y": 9.1,
        "projection_3y": None,
        "identity_ids": {"sleeper_id": "9999"},
    }


def _artifact(row: dict[str, Any]) -> dict[str, Any]:
    return {"captured_at": "2026-08-25T00:00:00Z", "players": [row]}


def test_modeled_row_with_null_score_serves_a_degradation_notice(monkeypatch) -> None:
    client = _client(monkeypatch, _artifact(_served_row(dynasty_value_score=None)))
    body = client.get("/api/players/9999").json()
    assert body["model_status"] == "modeled"
    assert body["model"]["dynasty_value_score"] is None
    assert body["degradation"] is not None, (
        "a modeled row with no score must say so — a null score beside "
        "degradation=None is a blank beside a confident label"
    )
    assert "dynasty value score" in body["degradation"]["message"].lower()


def test_modeled_row_with_a_score_is_not_degraded(monkeypatch) -> None:
    client = _client(monkeypatch, _artifact(_served_row(dynasty_value_score=61.4)))
    body = client.get("/api/players/9999").json()
    assert body["model_status"] == "modeled"
    assert body["degradation"] is None
