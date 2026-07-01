"""Slice A RED: read-only Roster Capacity API over the gitignored artifact.

The route must be CI-safe: every test serves temp files by monkeypatching the
route's artifact path and never depends on app/data/roster_capacity existing.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _route_module():
    import app.api.routes.roster_capacity as route

    return route


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def _valid_artifact() -> dict[str, Any]:
    return {
        "status": "ok",
        "capacity_health": {
            "total_players": 29,
            "total_capacity": 28,
            "total_capacity_cuts_required": 1,
            "active_slot_overflow": 2,
            "by_slot_class": {"active": 22, "reserve": 4, "taxi": 3},
            "reserve_unrestricted": False,
        },
        "candidates": [
            {
                "sleeper_player_id": "cut-1",
                "full_name": "Boundary Player",
                "position": "WR",
                "cut_priority": 1,
                "candidate_source": "capacity_ordered",
                "raw_xvar": 1.5,
                "dvs": 44.2,
                "xvar_pct": 12.0,
                "median_projection_2y": 5.1,
                "value_field_status": {
                    "xvar": "ok",
                    "dvs": "ok",
                    "projection_2y": "ok",
                    "position": "ok",
                    "model": "ok",
                },
            }
        ],
        "scenarios": [
            {
                "cut_set": ["cut-1"],
                "cumulative_value_at_risk": [-2.5, 4.75],
                "marginal_next_candidate_cost": [-0.5, 3.25],
                "per_position_depth_impact": {"WR": {"cuts": 1, "pool_size": 4}},
                "pool_deficits": {"WR": 0},
                "caveats": ["zero_crossing_range_preserved"],
            }
        ],
        "unrostered_pool_range": {
            "WR": {
                "status": "ok",
                "low": -1.25,
                "high": 4.5,
                "top_k_values": [4.5, 0.0, -1.25],
                "pool_size": 3,
                "caveats": [],
            }
        },
        "excluded_counts": {"unresolved_identity": 0},
        "caveats": [],
        "decision_supported": False,
        "created_at": "2026-06-30T12:00:00+00:00",
        "sleeper_snapshot_captured_at": "2026-06-30T11:00:00+00:00",
    }


def _write_artifact(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _client_with_artifact(monkeypatch: pytest.MonkeyPatch, path: Path) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_ARTIFACT_PATH", path)
    from app.main import app

    return TestClient(app)


def test_route_serves_temp_artifact_without_collapsing_ranges_or_nominating_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = _write_artifact(tmp_path / "roster_capacity_latest.json", _valid_artifact())
    response = _client_with_artifact(monkeypatch, artifact_path).get(
        "/api/roster/capacity"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["decision_supported"] is False
    assert body["created_at"] == "2026-06-30T12:00:00+00:00"
    assert body["sleeper_snapshot_captured_at"] == "2026-06-30T11:00:00+00:00"
    assert body["scenarios"][0]["cumulative_value_at_risk"] == [-2.5, 4.75]
    assert body["scenarios"][0]["marginal_next_candidate_cost"] == [-0.5, 3.25]
    assert "marginal_next_candidate" not in body["scenarios"][0]
    assert "marginal_next_candidate_player_id" not in body["scenarios"][0]
    assert "midpoint" not in json.dumps(body).lower()
    assert _decision_supported_true_count(body) == 0


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: None, "missing"),
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (lambda path: path.write_text(json.dumps(["not", "object"]), encoding="utf-8"), "root"),
    ],
)
def test_route_fails_closed_for_missing_malformed_or_wrong_root_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
    message_fragment: str,
) -> None:
    artifact_path = tmp_path / "roster_capacity_latest.json"
    writer(artifact_path)

    response = _client_with_artifact(monkeypatch, artifact_path).get(
        "/api/roster/capacity"
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "roster_capacity_artifact_unavailable"
    assert message_fragment in detail["message"]
    assert detail["decision_supported"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.pop("decision_supported"),
        lambda body: body["scenarios"][0].__setitem__("cumulative_value_at_risk", [0.0]),
        lambda body: body["unrostered_pool_range"]["WR"].__setitem__("low", "NaN"),
        lambda body: body["unrostered_pool_range"]["WR"].__setitem__("high", "Infinity"),
        lambda body: body.__setitem__("recommendation", "cut this player"),
        lambda body: body["scenarios"][0].__setitem__(
            "recommendation", "cut this player"
        ),
        lambda body: body["candidates"][0].__setitem__(
            "recommendation", "cut this player"
        ),
        lambda body: body["unrostered_pool_range"]["WR"].__setitem__(
            "recommendation", "pick this player"
        ),
    ],
)
def test_route_fails_closed_on_incomplete_non_finite_or_verdict_shaped_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation,
) -> None:
    body = _valid_artifact()
    mutation(body)
    artifact_path = _write_artifact(tmp_path / "roster_capacity_latest.json", body)

    response = _client_with_artifact(monkeypatch, artifact_path).get(
        "/api/roster/capacity"
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "roster_capacity_artifact_unavailable"
    assert "schema" in detail["message"].lower() or "non-finite" in detail["message"].lower()
    assert detail["decision_supported"] is False


@pytest.mark.parametrize("field", ["created_at", "sleeper_snapshot_captured_at"])
@pytest.mark.parametrize("unverifiable_value", ["not-a-timestamp", None])
def test_route_degrades_parseable_artifact_with_unverifiable_freshness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    unverifiable_value: str | None,
) -> None:
    body = _valid_artifact()
    body[field] = unverifiable_value
    artifact_path = _write_artifact(tmp_path / "roster_capacity_latest.json", body)

    response = _client_with_artifact(monkeypatch, artifact_path).get(
        "/api/roster/capacity"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_status"] == "degraded"
    assert payload["status"] == "ok"
    assert any("freshness_unverifiable" in caveat for caveat in payload["caveats"])
    assert payload["decision_supported"] is False


def test_route_reflects_blocked_scorecard_without_serving_stale_numbers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = deepcopy(_valid_artifact())
    body.update(
        {
            "status": "blocked",
            "capacity_health": None,
            "candidates": [],
            "scenarios": [],
            "unrostered_pool_range": {},
            "caveats": ["capacity_audit_blocked: malformed_snapshot"],
        }
    )
    artifact_path = _write_artifact(tmp_path / "roster_capacity_latest.json", body)

    response = _client_with_artifact(monkeypatch, artifact_path).get(
        "/api/roster/capacity"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["artifact_status"] == "blocked"
    assert payload["capacity_health"] is None
    assert payload["scenarios"] == []
    assert "capacity_audit_blocked: malformed_snapshot" in payload["caveats"]
    assert payload["decision_supported"] is False


def test_route_openapi_uses_typed_response_and_structured_503() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/roster/capacity"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RosterCapacityResponse"
    }
    error_schema = operation["responses"]["503"]["content"]["application/json"][
        "schema"
    ]
    assert error_schema == {"$ref": "#/components/schemas/RosterCapacityErrorResponse"}
