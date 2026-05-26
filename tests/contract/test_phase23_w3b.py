"""Phase 23.5 W3b counterparty forced-cut penalty contracts.

RED -> market endpoint has no counterparty status/penalty support.
GREEN -> optional counterparty penalty is computed only from RosterCutEngine
         selections and degrades to explicit unavailable/null states.
"""
from __future__ import annotations

import inspect
from typing import Any

from fastapi.testclient import TestClient

import app.api.routes.trade_market as trade_market_route
import src.dynasty_genius.trade_lab.market_reconciler as market_reconciler
from app.main import app

client = TestClient(app)

_POSITIONS_2 = ["QB", "RB"]
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
_REQUIRED_MARKET_CAVEATS = {
    "market_overlay_display_only",
    "fantasycalc_raw_scale_not_xvar",
    "market_values_not_model_inputs",
    "decision_supported_false",
    "source_timestamp_is_fetch_time_not_publish_time",
}


def _pvo_entry(
    sleeper_id: str,
    *,
    xvar_pct: float,
    xvar: float,
    position: str = "WR",
) -> dict[str, Any]:
    return {
        "sleeper_player_id": sleeper_id,
        "player": {
            "full_name": f"Player {sleeper_id}",
            "position": position,
            "age": 24.0,
            "years_exp": 2,
            "sleeper_status": "Active",
        },
        "valuation": {
            "xvar_percentile_overall": xvar_pct,
            "dynasty_value_score": 50.0,
            "xvar": xvar,
            "engine_path": "ENGINE_B",
        },
    }


def _universe_pvo(*, omit_ids: set[str] | None = None) -> dict[str, Any]:
    omit_ids = omit_ids or set()
    rows = [
        _pvo_entry("DAVID_A", xvar_pct=90.0, xvar=30.0),
        _pvo_entry("DAVID_B", xvar_pct=80.0, xvar=25.0),
        _pvo_entry("CP_SEND", xvar_pct=70.0, xvar=20.0),
        _pvo_entry("CP_MODEL_CUT", xvar_pct=1.0, xvar=1.0),
    ]
    return {"players": [row for row in rows if row["sleeper_player_id"] not in omit_ids]}


def _snapshot(*, counterparty_cut_id: str = "CP_MODEL_CUT") -> dict[str, Any]:
    return {
        "league": {
            "roster_positions": _POSITIONS_2,
            "settings": _SETTINGS_NO_RESERVE,
        },
        "rosters": [
            {
                "roster_id": 1,
                "players": ["DAVID_A", "DAVID_B"],
                "taxi": [],
                "reserve": [],
            },
            {
                "roster_id": 2,
                "players": ["CP_SEND", counterparty_cut_id],
                "taxi": [],
                "reserve": [],
            },
        ],
    }


def _fc_player_row(sleeper_id: str, value: int) -> dict[str, Any]:
    return {
        "player": {
            "name": f"Player {sleeper_id}",
            "sleeperId": sleeper_id,
            "position": "WR",
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _fc_entries() -> list[dict[str, Any]]:
    return [
        _fc_player_row("DAVID_A", 100),
        _fc_player_row("DAVID_B", 3000),
        _fc_player_row("CP_SEND", 5000),
        # This value is intentionally higher than DAVID_A. If implementation
        # market-sorts cut candidates, it will pick DAVID_A instead.
        _fc_player_row("CP_MODEL_CUT", 9000),
    ]


def _payload(*, counterparty_roster_id: int | None = 2) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sent_assets": [
            {"asset_kind": "player", "player_id": "DAVID_A", "sleeper_id": "DAVID_A"},
            {"asset_kind": "player", "player_id": "DAVID_B", "sleeper_id": "DAVID_B"},
        ],
        "received_assets": [
            {"asset_kind": "player", "player_id": "CP_SEND", "sleeper_id": "CP_SEND"},
        ],
        "current_draft_year": 2026,
        "format_key": "dynasty_sf_ppr",
    }
    if counterparty_roster_id is not None:
        payload["counterparty_roster_id"] = counterparty_roster_id
    return payload


def _install_market_route_mocks(
    monkeypatch,
    *,
    universe_pvo: dict[str, Any] | None = None,
    sleeper_snapshot: dict[str, Any] | None = None,
) -> None:
    monkeypatch.setattr(
        trade_market_route,
        "_load_reconcile_artifacts",
        lambda: (universe_pvo or _universe_pvo(), sleeper_snapshot or _snapshot()),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_fetch_fantasycalc_entries",
        lambda: (_fc_entries(), ["source_timestamp_is_fetch_time_not_publish_time"]),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_load_market_divergence_artifact",
        lambda: {"players": []},
    )


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def _assert_required_market_caveats(data: dict[str, Any]) -> None:
    assert _REQUIRED_MARKET_CAVEATS.issubset(set(data["caveats"]))


def test_counterparty_market_penalty_uses_roster_cut_engine_when_available(monkeypatch):
    """Full coverage selects counterparty cuts by model-native RosterCutEngine IDs."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["counterparty_market_penalty_status"] == "available"
    assert data["market_sent_raw"] == 3100
    assert data["market_received_raw"] == 5000
    assert data["adjusted_market_received"] == 5000
    assert data["adjusted_market_sent"] == 0
    assert data["market_delta_for_david"] == 5000

    penalty = data["counterparty_forced_cut_penalty"]
    assert penalty is not None
    assert penalty["roster_id"] == 2
    assert penalty["post_trade_overflow"] == 1
    assert penalty["penalty_market_value"] == 9000
    assert penalty["forced_cut_candidates"][0]["asset_ref"]["sleeper_id"] == (
        "CP_MODEL_CUT"
    )
    _assert_required_market_caveats(data)


def test_counterparty_penalty_has_no_market_sorted_fallback(monkeypatch):
    """FantasyCalc values must not decide the counterparty forced-cut set."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    penalty = response.json()["counterparty_forced_cut_penalty"]
    selected_ids = [
        overlay["asset_ref"]["sleeper_id"]
        for overlay in penalty["forced_cut_candidates"]
    ]
    assert selected_ids == ["CP_MODEL_CUT"]
    assert "DAVID_A" not in selected_ids


def test_unknown_counterparty_roster_returns_null_penalty_and_caveat(monkeypatch):
    """Unknown counterparty roster is unavailable, not a fabricated zero penalty."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload(counterparty_roster_id=99))

    assert response.status_code == 200
    data = response.json()
    assert data["counterparty_market_penalty_status"] == "unavailable"
    assert data["counterparty_forced_cut_penalty"] is None
    assert "counterparty_roster_unknown" in data["caveats"]
    assert data["adjusted_market_sent"] == data["market_sent_raw"]
    _assert_required_market_caveats(data)


def test_counterparty_penalty_unavailable_when_model_coverage_missing(monkeypatch):
    """Known roster with inadequate PVO coverage fails closed without FC fallback."""
    _install_market_route_mocks(
        monkeypatch,
        universe_pvo=_universe_pvo(omit_ids={"CP_MODEL_CUT"}),
    )

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["counterparty_market_penalty_status"] == "unavailable"
    assert data["counterparty_forced_cut_penalty"] is None
    assert "counterparty_coverage_inadequate" in data["caveats"]
    assert data["adjusted_market_sent"] == data["market_sent_raw"]
    assert data["market_delta_for_david"] == (
        data["adjusted_market_received"] - data["adjusted_market_sent"]
    )
    _assert_required_market_caveats(data)


def test_counterparty_not_requested_preserves_single_sided_market_math(monkeypatch):
    """Omitting counterparty_roster_id keeps the current David-side market behavior."""
    _install_market_route_mocks(monkeypatch)

    response = client.post(
        "/api/trade/reconcile/market",
        json=_payload(counterparty_roster_id=None),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["counterparty_market_penalty_status"] == "not_requested"
    assert data["counterparty_forced_cut_penalty"] is None
    assert "counterparty_roster_unknown" not in data["caveats"]
    assert "counterparty_coverage_inadequate" not in data["caveats"]
    assert data["market_sent_raw"] == 3100
    assert data["market_received_raw"] == 5000
    assert data["adjusted_market_sent"] == 3100
    assert data["adjusted_market_received"] == 5000
    assert data["market_delta_for_david"] == 1900
    _assert_required_market_caveats(data)


def test_counterparty_penalty_unavailable_when_selection_raises(monkeypatch):
    """Snapshot/RosterCutEngine failure for the counterparty fails closed (no 5xx).

    Locks the spec §385-386/505 clause: known roster but the post-trade snapshot
    cannot be built / RosterCutEngine cannot run -> status unavailable, null
    penalty, caveat — never a 5xx, never a market-sorted fallback.
    """
    _install_market_route_mocks(monkeypatch)

    real_reconcile = trade_market_route.reconcile_trade_roster

    def _raise_for_counterparty(
        david_assets, received_assets, universe_pvo, sleeper_snapshot, david_roster_id=1
    ):
        # The counterparty selection runs with david_roster_id=2; the David-side
        # call (roster 1) must still succeed.
        if david_roster_id == 2:
            raise ValueError("protected slot type in roster_positions")
        return real_reconcile(
            david_assets,
            received_assets,
            universe_pvo,
            sleeper_snapshot,
            david_roster_id=david_roster_id,
        )

    monkeypatch.setattr(
        trade_market_route, "reconcile_trade_roster", _raise_for_counterparty
    )

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["counterparty_market_penalty_status"] == "unavailable"
    assert data["counterparty_forced_cut_penalty"] is None
    assert "counterparty_coverage_inadequate" in data["caveats"]
    assert data["adjusted_market_sent"] == data["market_sent_raw"]
    _assert_required_market_caveats(data)


def test_counterparty_outputs_keep_decision_supported_false_recursive(monkeypatch):
    """New W3b output remains advisory-only throughout the serialized payload."""
    _install_market_route_mocks(monkeypatch)

    response = client.post("/api/trade/reconcile/market", json=_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["decision_supported"] is False
    assert _decision_supported_true_count(data) == 0
    assert data["counterparty_forced_cut_penalty"]["decision_supported"] is False


def test_market_reconciler_remains_price_only_and_model_blind():
    """Counterparty cut selection belongs in the endpoint, not market pricing code."""
    source = inspect.getsource(market_reconciler)

    assert "src.dynasty_genius.roster_cut_engine" not in source
    assert "compute_roster_cut_candidates" not in source
    assert "reconcile_trade_roster" not in source
