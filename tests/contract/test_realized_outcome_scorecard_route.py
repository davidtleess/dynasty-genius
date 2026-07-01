"""RED: read-only Realized-Outcome scorecard API.

The scorecard artifact is gitignored and absent in the healthy off-season state.
These tests never depend on ``app/data/realized_outcome``; every file path is a
tmp_path monkeypatch. Missing artifact is an honest 200 inactive response, while
malformed present data fails closed.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _route_module():
    import app.api.routes.realized_outcome_scorecard as route

    return route


def _client_with_scorecard(monkeypatch: pytest.MonkeyPatch, path: Path) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_SCORECARD_PATH", path)
    from app.main import app

    return TestClient(app)


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def _valid_scorecard() -> dict[str, Any]:
    return {
        "status": "ok",
        "as_of_week": 3,
        "settlement_status": "unsettled",
        "maturity_pct": 8.82,
        "cohort_metrics": {
            "WR": {
                "spearman": {"value": None, "bca_ci": None},
                "kendall": {"value": None, "bca_ci": None},
                "ndcg": {"value": None},
                "precision_at_k": {
                    "value": None,
                    "k": None,
                    "truth_def": None,
                    "hits": None,
                },
                "status": "power_floor_not_met",
                "eligible_count": 1,
                "decision_supported": False,
            }
        },
        "tracking_rows": [
            {
                "gsis_id": "00-0001",
                "position": "WR",
                "predicted_ppg": 10.0,
                "realized_ppg_to_date": 11.0,
                "realized_vs_expected_delta": 1.0,
                "realized_outcome_status": "observed",
                "maturity_pct": 8.82,
                "settlement_status": "unsettled",
                "model_input_fidelity": {
                    "snap_share": {"status": "partial_window", "delta": None},
                    "target_share_nfl": {"status": "diagnostic_only", "delta": None},
                },
                "decision_supported": False,
            }
        ],
        "excluded_counts": {"identity_unresolved": 0},
        "decision_supported": False,
    }


def _write_scorecard(path: Path, body: dict[str, Any]) -> Path:
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_missing_scorecard_is_healthy_inactive_200_without_live_artifact_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scorecard_path = tmp_path / "missing_scorecard_latest.json"

    response = _client_with_scorecard(monkeypatch, scorecard_path).get(
        "/api/realized-outcome/scorecard"
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "inactive",
        "status_reason": "awaiting_first_finalized_week",
        "as_of_week": None,
        "settlement_status": "unsettled",
        "maturity_pct": None,
        "cohort_metrics": {},
        "tracking_rows": [],
        "excluded_counts": {},
        "decision_supported": False,
    }
    assert not scorecard_path.exists()


def test_scorecard_route_serves_typed_scorecard_without_player_verdict_language(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scorecard_path = _write_scorecard(
        tmp_path / "scorecard_latest.json", _valid_scorecard()
    )

    response = _client_with_scorecard(monkeypatch, scorecard_path).get(
        "/api/realized-outcome/scorecard"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["settlement_status"] == "unsettled"
    assert body["maturity_pct"] == 8.82
    assert body["cohort_metrics"]["WR"]["status"] == "power_floor_not_met"
    assert body["cohort_metrics"]["WR"]["eligible_count"] == 1
    assert body["tracking_rows"][0]["model_input_fidelity"]["snap_share"] == {
        "status": "partial_window",
        "delta": None,
    }
    assert body["tracking_rows"][0]["model_input_fidelity"]["target_share_nfl"] == {
        "status": "diagnostic_only",
        "delta": None,
    }
    assert _decision_supported_true_count(body) == 0
    text = json.dumps(body).lower()
    for forbidden in [
        "certificate",
        "verifier",
        "player verdict",
    ]:
        assert forbidden not in text
    assert re.search(r"\b(buy|sell|start|sit)\b", text) is None


@pytest.mark.parametrize(
    ("writer", "message_fragment"),
    [
        (lambda path: path.write_text("{not-json", encoding="utf-8"), "malformed"),
        (
            lambda path: path.write_text(json.dumps(["not", "object"]), encoding="utf-8"),
            "root",
        ),
    ],
)
def test_present_but_malformed_scorecard_fails_closed_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
    message_fragment: str,
) -> None:
    scorecard_path = tmp_path / "scorecard_latest.json"
    writer(scorecard_path)

    response = _client_with_scorecard(monkeypatch, scorecard_path).get(
        "/api/realized-outcome/scorecard"
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "realized_outcome_scorecard_unavailable"
    assert message_fragment in detail["message"].lower()
    assert detail["decision_supported"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.pop("decision_supported"),
        lambda body: body.__setitem__("maturity_pct", "NaN"),
        lambda body: body["cohort_metrics"]["WR"].__setitem__(
            "recommendation", "trust this player"
        ),
        lambda body: body["tracking_rows"][0].__setitem__("verdict", "start"),
    ],
)
def test_scorecard_schema_fails_closed_on_missing_non_finite_or_verdict_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation,
) -> None:
    body = deepcopy(_valid_scorecard())
    mutation(body)
    scorecard_path = _write_scorecard(tmp_path / "scorecard_latest.json", body)

    response = _client_with_scorecard(monkeypatch, scorecard_path).get(
        "/api/realized-outcome/scorecard"
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "realized_outcome_scorecard_unavailable"
    assert "schema" in detail["message"].lower() or "non-finite" in detail[
        "message"
    ].lower()
    assert detail["decision_supported"] is False


def test_realized_outcome_scorecard_openapi_uses_typed_response_and_structured_503() -> None:
    from app.main import app

    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/realized-outcome/scorecard"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RealizedOutcomeScorecardResponse"
    }
    assert operation["responses"]["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RealizedOutcomeScorecardErrorResponse"
    }
