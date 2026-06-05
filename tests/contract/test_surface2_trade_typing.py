"""Surface 2 Trade Lab route typing contract tests.

RED: current trade routes expose loose dict request/response schemas.
GREEN: request and response models are declared without changing route behavior.
"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _operation(path: str) -> dict[str, Any]:
    return app.openapi()["paths"][path]["post"]


def _response_ref(path: str) -> str:
    response_schema = _operation(path)["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    return response_schema.get("$ref", "")


def _schema_props(name: str) -> dict[str, Any]:
    return app.openapi()["components"]["schemas"][name]["properties"]


def test_reconcile_declares_typed_response_schema() -> None:
    assert _response_ref("/api/trade/reconcile").endswith(
        "/TradeRosterReconciliation"
    )


def test_market_declares_typed_response_schema() -> None:
    assert _response_ref("/api/trade/reconcile/market").endswith(
        "/TradeMarketReconciliation"
    )


def test_evaluate_declares_typed_response_schema() -> None:
    assert _response_ref("/api/trade/evaluate").endswith("/TradeEvaluation")


def test_analyze_is_not_typed_with_a_trade_model() -> None:
    analyze_ref = _response_ref("/api/trade/analyze")
    assert not analyze_ref.endswith(
        (
            "/TradeEvaluation",
            "/TradeRosterReconciliation",
            "/TradeMarketReconciliation",
        )
    )


def test_evaluate_request_items_ref_trade_asset() -> None:
    props = _schema_props("TradeEvaluateRequest")
    assert props["side_a"]["items"]["$ref"].endswith("/TradeAsset")
    assert props["side_b"]["items"]["$ref"].endswith("/TradeAsset")


def test_reconcile_request_items_ref_trade_asset() -> None:
    props = _schema_props("TradeReconcileRequest")
    assert props["david_assets"]["items"]["$ref"].endswith("/TradeAsset")
    assert props["received_assets"]["items"]["$ref"].endswith("/TradeAsset")


def test_market_request_items_ref_market_asset_ref() -> None:
    props = _schema_props("MarketReconcileRequest")
    assert props["sent_assets"]["items"]["$ref"].endswith("/MarketAssetRef")
    assert props["received_assets"]["items"]["$ref"].endswith("/MarketAssetRef")


def test_evaluate_typed_request_still_returns_200() -> None:
    body = {
        "side_a": [{"player_id": "1", "xvar": 10.0, "position": "WR"}],
        "side_b": [{"player_id": "2", "xvar": 9.5, "position": "RB"}],
    }

    response = client.post("/api/trade/evaluate", json=body)

    assert response.status_code == 200
    assert response.json()["decision_supported"] is False


def test_request_typing_rejects_malformed_trade_asset_fields() -> None:
    body = {
        "side_a": [{"player_id": "1", "xvar": "not-a-number", "position": "WR"}],
        "side_b": [{"player_id": "2", "xvar": 9.5, "position": "RB"}],
    }

    response = client.post("/api/trade/evaluate", json=body)

    assert response.status_code == 422


def test_request_typing_rejects_missing_required_trade_asset_position() -> None:
    body = {
        "side_a": [{"player_id": "1", "xvar": 10.0}],
        "side_b": [{"player_id": "2", "xvar": 9.5, "position": "RB"}],
    }

    response = client.post("/api/trade/evaluate", json=body)

    assert response.status_code == 422
