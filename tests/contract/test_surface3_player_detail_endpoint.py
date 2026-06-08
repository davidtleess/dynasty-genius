"""Surface-3 T4 — player detail endpoint contract tests.

RED: ``GET /api/players/{sleeper_id}`` is not implemented yet.
GREEN: endpoint returns a typed, degraded-safe PlayerDetailResponse from
fixture-monkeypatched artifacts, never production artifacts.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes.players as players_route
from app.main import app as main_app


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def _response_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys |= _response_keys(item)
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys |= _response_keys(item)
        return keys
    return set()


def _client(monkeypatch, *, pvo: dict[str, Any], divergence: dict[str, Any]) -> TestClient:
    monkeypatch.setattr(
        players_route,
        "_load_player_detail_artifacts",
        lambda: pvo,
        raising=False,
    )
    monkeypatch.setattr(
        players_route,
        "_load_market_divergence_artifact",
        lambda: divergence,
        raising=False,
    )
    app = FastAPI()
    app.include_router(players_route.router, prefix="/api")
    return TestClient(app)


def _pvo_row(
    sleeper_id: str = "13269",
    *,
    engine_path: str = "ENGINE_A",
    counter_argument: str | None = (
        "Premium valuation assumes continued high-level rushing or outlier passing efficiency."
    ),
    top_drivers: list[str] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    modeled = engine_path in {"ENGINE_A", "ENGINE_B", "BLEND_AB"}
    return {
        "schema_version": "universe_pvo_batch.v1",
        "sleeper_player_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "dvs_engine": "A" if engine_path == "ENGINE_A" else None,
        "player": {
            "full_name": "Fixture Player",
            "position": "QB",
            "team": "LVR",
            "age": 22.0,
            "years_exp": 0,
            "sleeper_status": "Active",
            "dg_status": engine_path,
        },
        "valuation": {
            "engine_path": engine_path,
            "valuation_status": "MODEL_SUPPORTED" if modeled else engine_path,
            "model_grade": "PROSPECT_D" if modeled else "PRE_MODEL",
            "model_version": "fixture_model_v1" if modeled else None,
            "dynasty_value_score": 85.14 if modeled else None,
            "xvar": 10.31 if modeled else None,
            "xvar_percentile_overall": 77.9 if modeled else None,
            "xvar_percentile_position": None,
            "decision_supported": False,
        },
        "counter_argument": counter_argument,
        "risk_flags": [],
        "top_drivers": top_drivers
        if top_drivers is not None
        else ["age_not_near_position_cliff"],
        "caveats": caveats if caveats is not None else ["NFL draft capital verified"],
        "draft_class": 2026,
        "nfl_draft_pick": 1,
        "nfl_draft_round": 1,
        "projection_1y": None,
        "projection_2y": None,
        "projection_3y": None,
        "market_overlay": {
            "source": "fantasycalc",
            "market_value": 4100,
            "overall_rank": 42,
            "position_rank": 8,
            "source_timestamp": "2026-05-24T17:19:52Z",
        },
        "lineage": {"sleeper_snapshot_hash": "sha256:test"},
        "pipeline_run_id": "must_not_leak",
        "identity_ids": {"sleeper_id": sleeper_id},
    }


def _pvo(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"captured_at": "2026-06-07T14:32:45Z", "players": list(rows)}


def _divergence(
    sleeper_id: str = "13269",
    *,
    delta: float | None = 0.27,
    signal: str = "MODEL_HIGH_MARKET_LOW",
) -> dict[str, Any]:
    # Mirrors the real universe_market_divergence artifact shape: market_overlay uses
    # `market_value`; divergence carries `signal` (direction) + `signal_status` (gate state).
    return {
        "captured_at": "2026-05-24T17:19:52Z",
        "players": [
            {
                "sleeper_player_id": sleeper_id,
                "market_overlay": {
                    "source": "fantasycalc",
                    "market_value": 4100,
                    "overall_rank": 42,
                    "position_rank": 8,
                    "source_timestamp": "2026-05-24T17:19:52Z",
                    "caveats": ["source_timestamp_is_fetch_time_not_publish_time"],
                },
                "divergence": {
                    "model_minus_market_delta": delta,
                    "signal": signal,
                    "signal_status": "gates_passed",
                    "decision_supported": False,
                },
            }
        ],
    }


def test_player_detail_named_loader_seams_exist() -> None:
    assert hasattr(players_route, "_load_player_detail_artifacts")
    assert hasattr(players_route, "_load_market_divergence_artifact")


def test_modeled_player_returns_full_shell_with_mapped_model_market_and_evidence(
    monkeypatch,
) -> None:
    client = _client(monkeypatch, pvo=_pvo(_pvo_row()), divergence=_divergence())

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    data = response.json()
    assert data["sleeper_id"] == "13269"
    assert data["decision_supported"] is False
    assert _decision_supported_true_count(data) == 0

    assert data["identity"] == {
        "sleeper_id": "13269",
        "name": "Fixture Player",
        "position": "QB",
        "team": "LVR",
        "age": 22.0,
        "draft_class": 2026,
        "nfl_draft_pick": 1,
        "nfl_draft_round": 1,
    }
    assert data["model_status"] == "modeled"
    assert data["model"]["engine_path"] == "ENGINE_A"
    assert data["model"]["model_grade"] == "PROSPECT_D"
    assert data["model"]["dynasty_value_score"] == 85.14
    assert data["model"]["xvar"] == 10.31
    assert data["model"]["projection_1y"] is None

    assert data["evidence"]["counter_argument"]["text"].startswith("Premium valuation")
    assert data["evidence"]["counter_argument"]["status"] == "available"
    assert data["evidence"]["top_drivers"]["items"] == ["age_not_near_position_cliff"]
    assert data["evidence"]["caveats"]["items"] == ["NFL draft capital verified"]

    assert data["market"]["status"] == "available"
    assert data["market"]["market_value"] == 4100  # maps from market_overlay.market_value
    assert data["market"]["market_rank_overall"] == 42
    assert data["market"]["market_rank_position"] == 8
    assert data["market"]["source"] == "fantasycalc"
    assert "market_overlay_static_caveat" in data["market"]["caveats"]
    assert data["divergence"]["delta"] == 0.27
    # status maps from divergence.signal (direction), NOT signal_status (gate state)
    assert data["divergence"]["status"] == "model_higher_than_market"


def test_response_never_leaks_raw_pvo_keys_or_banned_engine_a_fields(monkeypatch) -> None:
    client = _client(monkeypatch, pvo=_pvo(_pvo_row()), divergence=_divergence())

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    keys = _response_keys(response.json())
    assert "pipeline_run_id" not in keys
    assert "schema_version" not in keys
    assert "lineage" not in keys
    assert "identity_ids" not in keys
    assert "market_overlay" not in keys
    assert "confidence" not in keys
    assert "dynasty_tier" not in keys
    assert "bucket" not in keys


def test_non_modeled_player_returns_typed_degraded_response(monkeypatch) -> None:
    client = _client(
        monkeypatch,
        pvo=_pvo(_pvo_row("99999", engine_path="PRE_MODEL", counter_argument=None)),
        divergence=_divergence("99999", delta=None, signal="INSIDE_BAND"),
    )

    response = client.get("/api/players/99999")

    assert response.status_code == 200
    data = response.json()
    assert data["model_status"] in {"experimental", "unavailable"}
    assert data["model"] is None
    assert data["evidence"] is None
    assert data["decision_supported"] is False
    assert _decision_supported_true_count(data) == 0
    assert "No active model score" in data["degradation"]["message"]


def test_missing_market_degrades_market_lane_independently(monkeypatch) -> None:
    client = _client(monkeypatch, pvo=_pvo(_pvo_row()), divergence={"players": []})

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    data = response.json()
    assert data["model_status"] == "modeled"
    assert data["model"] is not None
    assert data["market"]["status"] == "unavailable"
    assert data["market"]["market_rank_overall"] is None
    assert data["market"]["market_rank_position"] is None
    assert "market_overlay_unavailable" in data["market"]["caveats"]
    assert data["divergence"]["status"] == "unavailable"
    assert data["divergence"]["delta"] is None


def test_banned_evidence_text_is_suppressed_and_degraded(monkeypatch) -> None:
    client = _client(
        monkeypatch,
        pvo=_pvo(
            _pvo_row(
                counter_argument="Elite valuation should never be emitted.",
                top_drivers=["age_not_near_position_cliff", "must draft immediately"],
                caveats=["robust projection context"],
            )
        ),
        divergence=_divergence(),
    )

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    data = response.json()
    rendered = str(data).lower()
    assert "elite valuation" not in rendered
    assert "must draft" not in rendered
    assert "robust projection context" in rendered
    assert data["evidence"]["counter_argument"]["text"] is None
    assert data["evidence"]["counter_argument"]["status"] == "experimental"
    assert "evidence_suppressed_banned_term" in data["evidence"]["counter_argument"]["caveats"]
    assert "must draft immediately" not in data["evidence"]["top_drivers"]["items"]
    assert "age_not_near_position_cliff" in data["evidence"]["top_drivers"]["items"]
    assert "evidence_suppressed_banned_term" in data["evidence"]["top_drivers"]["caveats"]


def test_main_app_mounts_player_detail_route_with_same_monkeypatched_seams(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        players_route,
        "_load_player_detail_artifacts",
        lambda: _pvo(_pvo_row()),
        raising=False,
    )
    monkeypatch.setattr(
        players_route,
        "_load_market_divergence_artifact",
        lambda: _divergence(),
        raising=False,
    )

    response = TestClient(main_app).get("/api/players/13269")

    assert response.status_code == 200
