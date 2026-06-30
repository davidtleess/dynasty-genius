"""League Pulse Increment 1 T3 route + mount contract tests."""

from __future__ import annotations

from importlib import import_module

from fastapi.testclient import TestClient


def _route_module():
    return import_module("app.api.routes.league_pulse")


def _posture_artifact() -> dict:
    return {
        "schema_version": "team_posture.v1",
        "captured_at": "2026-05-24T17:19:56Z",
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "David"},
                "posture": {
                    "label": "CONTENDER",
                    "score": 0.75,
                    "components": {"lineup": 0.8},
                    "caveats": ["phase18_heuristic_posture"],
                },
            },
            {
                "roster_id": 2,
                "owner": {"team_name": "Counterparty"},
                "posture": {
                    "label": "REBUILDING",
                    "score": -0.55,
                    "components": {"lineup": -0.5},
                    "caveats": [],
                },
            },
        ],
    }


def _team_value(roster_id: int, team_name: str) -> dict:
    return {
        "roster_id": roster_id,
        "owner": {"team_name": team_name},
        "team_value_views": {
            "starter_weighted_xvar": 42.0,
            "lineup_xvar": 38.0,
            "depth_credit_xvar": 4.0,
            "total_xvar_capped": 46.0,
            "top_n_xvar": 44.0,
            "market_overlay_total": 9999.0,
        },
        "age_profile": {"weighted_age": 25.3},
        "positional_summary": {"WR": {"z_score": 1.1}},
        "future_picks": {"owned_count": 4, "pick_value_status": "unvalued"},
        "players": [{"full_name": "Must Not Leak", "market_value": 123}],
    }


def _value_artifact() -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "captured_at": "2026-05-24T17:19:57Z",
        "teams": [_team_value(1, "David"), _team_value(2, "Counterparty")],
    }


def _opportunity_artifact() -> dict:
    return {
        "schema_version": "league_opportunity.v2",
        "captured_at": "2026-05-24T17:19:59Z",
        "perspective_roster_id": 1,
        "decision_supported": False,
        "card_section_counts": [],
        "partner_rankings": [
            {
                "counterparty_roster_id": 2,
                "counterparty_team_name": "Counterparty",
                "partner_score": 0.61,
                "matched_positions": ["WR"],
                "score_components": {"divergence_density_score": 0.3},
                "evidence": {"divergence_row_count": 2},
            }
        ],
        "cards": [
            {
                "card_id": "opp-roster",
                "card_type": "ROSTER_SURPLUS_DEFICIT_MATCH",
                "evidence_status": "evidence_complete",
                "sort_key": "positional_z_differential_desc",
                "sort_value": 2.2,
                "rationale": {
                    "primary": "POSITIONAL_SURPLUS_ON_COUNTERPARTY",
                    "secondary": ["PERSPECTIVE_POSITIONAL_DEFICIT"],
                    "evidence": {
                        "position": "WR",
                        "perspective_position_z": -1.0,
                        "counterparty_position_z": 1.2,
                        "perspective_surplus_label": "deficit",
                        "counterparty_surplus_label": "surplus",
                    },
                },
                "score_components": {
                    "fit_score": 0.5,
                    "divergence_score": 0.0,
                    "feasibility_score": 0.5,
                },
                "caveats": ["future_pick_values_deferred"],
            },
            {
                "card_id": "opp-waiver",
                "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                "evidence_status": "evidence_complete",
                "sort_key": "absolute_model_market_delta_desc",
                "sort_value": 0.4,
                "rationale": {
                    "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
                    "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
                    "evidence": {
                        "signal": "MODEL_HIGH_MARKET_LOW",
                        "evidence_status": "evidence_complete",
                        "model_minus_market_delta": 0.4,
                        "asset_xvar": 1.2,
                    },
                },
                "score_components": {
                    "fit_score": 0.4,
                    "divergence_score": 0.7,
                    "feasibility_score": 0.9,
                },
                "roster_capacity_candidates": {
                    "decision_supported": False,
                    "pool_status": "available",
                    "selection_rule": "descriptive_candidate_pool_no_tool_selection",
                    "narrowing_rule": "all_safe_candidates",
                    "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
                    "items": [
                        {
                            "sleeper_player_id": "drop-1",
                            "full_name": "Drop Candidate",
                            "position": "WR",
                            "value_status": "unvalued",
                            "xvar_pct": None,
                            "dvs": None,
                            "capacity_conflict_status": "hard_roster_rules_conflict",
                            "rule_conflict_label": "IR compliance violation",
                            "caveats": ["valuation_unavailable"],
                            "decision_supported": False,
                        }
                    ],
                    "caveats": [],
                },
                "caveats": ["waiver_status_from_sleeper_snapshot"],
            },
        ],
    }


def _patch_loaders(monkeypatch) -> object:
    route = _route_module()
    monkeypatch.setattr(route, "_load_team_posture", _posture_artifact)
    monkeypatch.setattr(route, "_load_team_value_matrix", _value_artifact)
    monkeypatch.setattr(route, "_load_league_opportunity", _opportunity_artifact)
    return route


def test_league_pulse_route_is_mounted_and_returns_degraded_response(
    monkeypatch,
) -> None:
    _patch_loaders(monkeypatch)
    from app.main import app

    response = TestClient(app).get("/api/league/pulse")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["decision_supported"] is False
    assert body["perspective_roster_id"] == 1
    assert body["captured_at"] == "2026-05-24T17:19:59Z"
    assert body["source_artifacts"]["team_posture"]["schema_version"] == "team_posture.v1"
    assert len(body["team_postures"]) == 2
    assert len(body["team_values"]) == 2
    assert len(body["partner_rankings"]) == 1
    assert len(body["model_native_cards"]) == 1
    assert len(body["market_overlay_cards"]) == 1
    assert "market_overlay_total" not in str(body)
    assert "Must Not Leak" not in str(body)


def test_league_pulse_dependency_error_translates_to_503(monkeypatch) -> None:
    route = _patch_loaders(monkeypatch)

    def fail(*_args: object) -> object:
        raise route.LeaguePulseDependencyError("schema_version mismatch")

    monkeypatch.setattr(route, "assemble_league_pulse", fail)
    from app.main import app

    response = TestClient(app).get("/api/league/pulse")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error": "league_pulse_dependency_unavailable",
        "message": "schema_version mismatch",
    }


def test_league_pulse_missing_artifact_file_translates_to_503(monkeypatch) -> None:
    route = _patch_loaders(monkeypatch)

    def missing() -> dict:
        raise FileNotFoundError("team_posture_latest.json")

    monkeypatch.setattr(route, "_load_team_posture", missing)
    from app.main import app

    response = TestClient(app).get("/api/league/pulse")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error": "league_pulse_artifact_unavailable",
        "message": "team_posture_latest.json",
    }


def test_league_pulse_malformed_json_translates_to_503(monkeypatch) -> None:
    import json

    route = _patch_loaders(monkeypatch)

    def malformed() -> dict:
        raise json.JSONDecodeError("Expecting value", "", 0)

    monkeypatch.setattr(route, "_load_team_posture", malformed)
    from app.main import app

    response = TestClient(app).get("/api/league/pulse")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "league_pulse_artifact_unavailable"


def test_league_pulse_wrong_root_type_translates_to_503(monkeypatch) -> None:
    route = _patch_loaders(monkeypatch)
    monkeypatch.setattr(route, "_load_team_value_matrix", lambda: ["not", "an", "object"])
    from app.main import app

    response = TestClient(app).get("/api/league/pulse")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "league_pulse_artifact_unavailable"


def test_league_pulse_route_openapi_uses_response_model(monkeypatch) -> None:
    _patch_loaders(monkeypatch)
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/league/pulse"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LeaguePulseResponse"
    }
