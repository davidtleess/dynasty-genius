"""Phase 23 W5a API integration contract tests.

RED  -> app/api/routes/trade_market.py and POST /api/trade/reconcile/market do not exist.
GREEN -> separate market route returns an enriched TradeMarketReconciliation
         without changing the model-native /api/trade/reconcile output.
"""
from __future__ import annotations

import json
from typing import Any

import app.api.routes.trade as trade_route
import app.api.routes.trade_market as trade_market_route
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BANNED_OUTPUT_TERMS = {
    "buy",
    "sell",
    "target",
    "block",
    "approve",
    "reject",
    "pass",
    "fail",
}

_POSITIONS_20 = ["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"] + ["BN"] * 14
_SETTINGS_NO_RESERVE = {
    "reserve_slots": 0,
    "reserve_allow_out": 0,
    "reserve_allow_doubtful": 0,
    "reserve_allow_sus": 0,
    "reserve_allow_na": 0,
    "reserve_allow_cov": 0,
    "reserve_allow_dnr": 0,
    "taxi_slots": 0,
    "taxi_years": 1,
    "taxi_allow_vets": 0,
    "taxi_deadline": 4,
}


def _mock_pvo(player_ids: list[str], extra_ids: list[str] | None = None) -> dict[str, Any]:
    def _entry(pid: str) -> dict[str, Any]:
        xvar_by_id = {
            "P0": 30.0,
            "P1": 4.0,
            "PA": 20.0,
            "PB": 10.0,
        }
        return {
            "sleeper_player_id": pid,
            "player": {
                "full_name": f"Player {pid}",
                "position": "WR",
                "age": 24.0,
                "years_exp": 2,
                "sleeper_status": "Active",
            },
            "valuation": {
                "xvar_percentile_overall": 5.0 if pid == "P1" else 50.0,
                "dynasty_value_score": 50.0,
                "xvar": xvar_by_id.get(pid, 15.0),
                "engine_path": "ENGINE_B",
            },
        }

    all_ids = list(player_ids) + list(extra_ids or [])
    return {"players": [_entry(pid) for pid in all_ids]}


def _mock_snapshot(player_ids: list[str]) -> dict[str, Any]:
    return {
        "league": {
            "roster_positions": _POSITIONS_20,
            "settings": _SETTINGS_NO_RESERVE,
        },
        "rosters": [
            {
                "roster_id": 1,
                "players": list(player_ids),
                "taxi": [],
                "reserve": [],
            }
        ],
    }


def _fc_player_row(sleeper_id: str, value: int, name: str | None = None) -> dict[str, Any]:
    return {
        "player": {
            "name": name or f"Player {sleeper_id}",
            "sleeperId": sleeper_id,
            "position": "WR",
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _divergence_artifact() -> dict[str, Any]:
    return {
        "players": [
            {
                "sleeper_player_id": "P0",
                "divergence": {
                    "signal_status": "gates_passed",
                    "model_minus_market_delta": 0.31,
                },
            },
            {
                "sleeper_player_id": "PA",
                "divergence": {
                    "signal_status": "inside_band",
                    "model_minus_market_delta": 0.04,
                },
            },
            {
                "sleeper_player_id": "PB",
                "divergence": {
                    "signal_status": "unavailable",
                    "model_minus_market_delta": None,
                },
            },
        ]
    }


def _payload() -> dict[str, Any]:
    return {
        "sent_assets": [
            {"asset_kind": "player", "player_id": "P0", "sleeper_id": "P0"},
        ],
        "received_assets": [
            {"asset_kind": "player", "player_id": "PA", "sleeper_id": "PA"},
            {"asset_kind": "player", "player_id": "PB", "sleeper_id": "PB"},
        ],
        "current_draft_year": 2026,
        "format_key": "dynasty_sf_ppr",
    }


def _install_market_route_mocks(
    monkeypatch,
    *,
    fantasycalc_caveats: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    pids = [f"P{i}" for i in range(20)]
    universe_pvo = _mock_pvo(pids, ["PA", "PB"])
    sleeper_snapshot = _mock_snapshot(pids)
    fc_entries = [
        _fc_player_row("P0", 7000),
        _fc_player_row("PA", 5200),
        _fc_player_row("PB", 1100),
        _fc_player_row("P1", 900),
    ]
    caveats = fantasycalc_caveats or ["source_timestamp_is_fetch_time_not_publish_time"]

    monkeypatch.setattr(
        trade_market_route,
        "_load_reconcile_artifacts",
        lambda: (universe_pvo, sleeper_snapshot),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_fetch_fantasycalc_entries",
        lambda: (fc_entries, caveats),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_load_market_divergence_artifact",
        lambda: _divergence_artifact(),
    )
    return universe_pvo, sleeper_snapshot


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def test_market_reconcile_route_is_separate_file_and_mounted(monkeypatch):
    """W5 must use a separate route module and expose POST /api/trade/reconcile/market."""
    assert trade_market_route.__file__ is not None
    assert trade_market_route.__file__.endswith("app/api/routes/trade_market.py")
    assert getattr(trade_market_route, "router", None) is not None

    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {
        "market_source",
        "sent_assets",
        "received_assets",
        "david_forced_cut_penalty",
        "realism_warnings",
        "caveats",
        "decision_supported",
    }
    assert data["decision_supported"] is False
    assert data["market_source"] == "fantasycalc"
    assert data["market_sent_raw"] == 7000
    assert data["market_received_raw"] == 6300
    assert data["david_forced_cut_penalty"]["post_trade_overflow"] == 1
    assert data["david_forced_cut_penalty"]["penalty_market_value"] == 900
    assert data["david_forced_cut_penalty"]["forced_cut_candidates"][0]["asset_ref"]["sleeper_id"] == "P1"
    assert data["sent_assets"][0]["divergence_context"]["signal_label"] == (
        "model_higher_than_market"
    )


def test_market_reconcile_stale_fantasycalc_returns_200_with_caveats(monkeypatch):
    """Stale FantasyCalc data degrades inside the payload, not as an endpoint failure."""
    _install_market_route_mocks(
        monkeypatch,
        fantasycalc_caveats=[
            "stale_market_data",
            "fetched_at=2026-05-20T00:00:00Z",
            "source_timestamp_is_fetch_time_not_publish_time",
        ],
    )

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert "stale_market_data" in data["caveats"]
    assert data["market_sent_raw"] == 7000
    assert data["market_received_raw"] == 6300


def test_market_reconcile_market_unavailable_returns_200_with_caveats(monkeypatch):
    """Cold FantasyCalc failure keeps the route usable but marks market coverage unavailable."""
    _install_market_route_mocks(
        monkeypatch,
        fantasycalc_caveats=["market_data_unavailable"],
    )
    monkeypatch.setattr(
        trade_market_route,
        "_fetch_fantasycalc_entries",
        lambda: ([], ["market_data_unavailable"]),
    )

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert "market_data_unavailable" in data["caveats"]
    assert data["market_sent_raw"] == 0
    assert data["market_received_raw"] == 0
    assert "fantasycalc_uncovered" in data["coverage_gaps"]


def test_market_reconcile_api_output_excludes_banned_language(monkeypatch):
    """The serialized API response must not leak UI/decision banned vocabulary."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    serialized = json.dumps(response.json(), sort_keys=True).lower()
    for banned in BANNED_OUTPUT_TERMS:
        assert banned not in serialized


def test_market_reconcile_decision_supported_false_on_all_market_rows(monkeypatch):
    """Market overlays, penalties, warnings, and the top-level envelope stay advisory-only."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert _decision_supported_true_count(data) == 0


def test_market_reconcile_does_not_change_native_reconcile_output(monkeypatch):
    """Calling the market endpoint must not alter the model-native reconciliation lane."""
    universe_pvo, sleeper_snapshot = _install_market_route_mocks(monkeypatch)
    monkeypatch.setattr(
        trade_route,
        "_load_reconcile_artifacts",
        lambda: (universe_pvo, sleeper_snapshot),
    )

    model_payload = {
        "david_assets": [{"player_id": "P0", "xvar": 30.0, "position": "WR"}],
        "received_assets": [
            {"player_id": "PA", "xvar": 20.0, "position": "WR"},
            {"player_id": "PB", "xvar": 10.0, "position": "WR"},
        ],
    }
    native_before = client.post("/api/trade/reconcile", json=model_payload)
    market_response = client.post("/api/trade/reconcile/market", json=_payload())
    native_after = client.post("/api/trade/reconcile", json=model_payload)

    assert native_before.status_code == 200
    assert market_response.status_code == 200
    assert native_after.status_code == 200
    assert native_after.json() == native_before.json()
    assert "market_source" not in native_after.json()
    assert "sent_assets" not in native_after.json()


def test_market_reconcile_missing_model_artifacts_returns_503(monkeypatch):
    """Model-native artifacts remain required because W5a self-computes Phase 22 cuts."""
    monkeypatch.setattr(
        trade_market_route,
        "_load_reconcile_artifacts",
        lambda: (_ for _ in ()).throw(
            HTTPException(status_code=503, detail="Required reconciler artifacts not found")
        ),
    )

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 503
    assert response.json()["detail"] == "Required reconciler artifacts not found"
