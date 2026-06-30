"""War Room #2 T3 RED: read-only What-Changed API over the latest report.

The API serves the pre-built T2 report. It must not rebuild the report, rerun the
diff engine, or touch frontend/UI code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


def _route_module():
    from app.api.routes import league_what_changed

    return league_what_changed


def _valid_report(*, overall_status: str = "degraded") -> dict[str, Any]:
    return {
        "schema_version": "war_room_2_what_changed_v1",
        "generated_at": "2026-06-24T13:17:30+00:00",
        "decision_supported": False,
        "overall_status": overall_status,
        "daily_diff": {
            "decision_supported": False,
            "overall_status": overall_status,
            "market": {
                "status": "ok",
                "decision_supported": False,
                "comparison_window": {
                    "from_date": "2026-06-23",
                    "to_date": "2026-06-24",
                },
                "roster_deltas": [
                    {
                        "sleeper_id": "9509",
                        "player_key": "sleeper:9509",
                        "player_name": "Bijan Robinson",
                        "position": "RB",
                        "value_delta": 250,
                        "value_delta_direction": "rose",
                        "overall_rank_delta": -2,
                        "overall_rank_delta_direction": "improved",
                        "position_rank_delta": -1,
                        "position_rank_delta_direction": "improved",
                    }
                ],
                "top_movers": [],
                "total_movers_count": 0,
                "entered": [],
                "exited": [],
                "market_source": "fantasycalc_overlay",
            },
            "model": {
                "status": "insufficient_history",
                "decision_supported": False,
                "comparison_window": {"status": "insufficient_history"},
                "deltas": [],
            },
        },
        "structural_context": {
            "status": "ok",
            "decision_supported": False,
            "current_not_delta": True,
            "sections": {
                "team_posture": _structural_section(
                    {
                        "david_roster_id": 1,
                        "david_team_name": "Woodbury Riders",
                        "david_posture": "REBUILDING",
                        "team_count": 12,
                    }
                ),
                "team_value": _structural_section(
                    {
                        "david_value_summary": {
                            "roster_id": 1,
                            "team_name": "Woodbury Riders",
                            "posture_label": "UNCLASSIFIED",
                            "depth_credit_xvar": 11.5,
                            "lineup_xvar": 88.25,
                            "starter_weighted_xvar": 72.0,
                            "top_n_xvar": 101.75,
                            "total_xvar_capped": 129.5,
                        }
                    }
                ),
                "league_opportunity": _structural_section(
                    {
                        "top_partner_rankings": [
                            {
                                "counterparty_roster_id": 2,
                                "counterparty_team_name": "League Mate",
                                "partner_score": 78.5,
                                "matched_positions": ["RB"],
                            }
                        ],
                        "top_cards": [
                            {
                                "card_id": "waiver-1",
                                "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                                "asset_name": "Noah Fant",
                                "roster_capacity_context": {
                                    "pool_status": "available",
                                    "candidate_count": 1,
                                    "hard_conflict_count": 0,
                                },
                            }
                        ],
                    }
                ),
                "drop_pressure": _structural_section(
                    {
                        "summary": {
                            "roster_id": 1,
                            "total_players": 30,
                            "total_capacity": 28,
                            "cuts_required": 2,
                        },
                        "top_candidates": [
                            {
                                "sleeper_player_id": "6786",
                                "player_name": "CeeDee Lamb",
                                "position": "WR",
                                "cut_priority": 1,
                                "dvs": 91.2,
                                "xvar_pct": 97.0,
                            }
                        ],
                    }
                ),
                "sleeper_snapshot": _structural_section(
                    {
                        "david_roster_id": 1,
                        "david_roster_player_count": 28,
                        "league_roster_count": 12,
                    }
                ),
            },
        },
    }


def _structural_section(extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "decision_supported": False,
        "current_not_delta": True,
        "source_path": "/tmp/artifact.json",
        "captured_at": "2026-06-23T13:17:30+00:00",
        "staleness_caveat": {
            "basis": "captured_at_vs_report_generated_at",
            "report_generated_at": "2026-06-24T13:17:30+00:00",
            "age_hours": 24.0,
            "is_stale": True,
        },
        **extra,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def test_what_changed_route_serves_prebuilt_degraded_report_read_only(
    tmp_path,
    monkeypatch,
) -> None:
    route = _route_module()
    report_path = _write_report(tmp_path / "what_changed_latest_report.json", _valid_report())
    monkeypatch.setattr(route, "_REPORT_PATH", report_path)

    def emitter_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("API must serve the pre-built report, not rerun T2")

    monkeypatch.setattr(route, "emit_daily_what_changed_report", emitter_must_not_run)
    from app.main import app

    response = TestClient(app).get("/api/league/what-changed")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["decision_supported"] is False
    assert body["daily_diff"]["market"]["decision_supported"] is False
    assert body["daily_diff"]["model"]["decision_supported"] is False
    assert body["structural_context"]["current_not_delta"] is True
    assert body["structural_context"]["sections"]["team_posture"]["staleness_caveat"][
        "is_stale"
    ] is True
    _assert_decision_supported_false_recursive(body)

    model_text = json.dumps(body["daily_diff"]["model"], sort_keys=True).lower()
    for market_key in ("market_overlay", "divergence", "fantasycalc", "fc_native"):
        assert market_key not in model_text


def test_what_changed_route_serves_valid_unavailable_report_as_honest_200(
    tmp_path,
    monkeypatch,
) -> None:
    route = _route_module()
    report_path = _write_report(
        tmp_path / "what_changed_latest_report.json",
        _valid_report(overall_status="unavailable"),
    )
    monkeypatch.setattr(route, "_REPORT_PATH", report_path)
    from app.main import app

    response = TestClient(app).get("/api/league/what-changed")

    assert response.status_code == 200
    assert response.json()["overall_status"] == "unavailable"


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json"), "malformed"),
        (lambda path: path.write_text(json.dumps(["not", "object"])), "root"),
        (
            lambda path: path.write_text(
                json.dumps({**_valid_report(), "schema_version": "wrong"})
            ),
            "schema_version",
        ),
    ],
)
def test_what_changed_route_fails_closed_on_unreadable_or_wrong_root_report(
    tmp_path,
    monkeypatch,
    writer,
    message_fragment: str,
) -> None:
    route = _route_module()
    report_path = tmp_path / "what_changed_latest_report.json"
    writer(report_path)
    monkeypatch.setattr(route, "_REPORT_PATH", report_path)
    from app.main import app

    response = TestClient(app).get("/api/league/what-changed")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "what_changed_report_unavailable"
    assert message_fragment in detail["message"]


def test_what_changed_dtos_are_extra_forbid_and_model_section_rejects_market_keys() -> None:
    from app.api.routes.league_what_changed_models import (
        WhatChangedModelSection,
        WhatChangedResponse,
    )

    with pytest.raises(ValidationError):
        WhatChangedResponse.model_validate({**_valid_report(), "unexpected": True})

    with pytest.raises(ValidationError):
        WhatChangedModelSection.model_validate(
            {
                **_valid_report()["daily_diff"]["model"],
                "market_overlay": {"must": "not validate"},
            }
        )

    with pytest.raises(ValidationError):
        WhatChangedModelSection.model_validate(
            {
                **_valid_report()["daily_diff"]["model"],
                "comparison_window": {
                    "status": "insufficient_history",
                    "market_overlay": {"nested": "must not validate"},
                },
            }
        )

    with pytest.raises(ValidationError):
        WhatChangedModelSection.model_validate(
            {
                **_valid_report()["daily_diff"]["model"],
                "comparison_window": {"status": "not_a_model_window_state"},
            }
        )

    with pytest.raises(ValidationError):
        WhatChangedModelSection.model_validate(
            {
                **_valid_report()["daily_diff"]["model"],
                "comparison_window": {
                    "from_date": "2026-06-23",
                    "to_date": "2026-06-24",
                    "from_vintage": {},
                    "to_vintage": {
                        "semantic_output_hash": "semantic-v2",
                        "provenance_hash": "provenance-v2",
                    },
                },
            }
        )

    with pytest.raises(ValidationError):
        WhatChangedModelSection.model_validate(
            {
                **_valid_report()["daily_diff"]["model"],
                "comparison_window": {
                    "status": "model_multi_vintage_ambiguous",
                    "from_date": "2026-06-23",
                    "to_date": "2026-06-24",
                    "ambiguous_dates": [],
                },
            }
        )


def test_what_changed_route_openapi_uses_typed_response_model() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/league/what-changed"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/WhatChangedResponse"
    }
    assert "WhatChangedResponse" in schema["components"]["schemas"]


def test_what_changed_openapi_snapshot_has_been_regenerated() -> None:
    from app.main import app

    repo_root = Path(__file__).resolve().parents[2]
    snapshot = repo_root / "frontend" / "openapi.json"
    canonical = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"

    assert snapshot.read_text(encoding="utf-8") == canonical
