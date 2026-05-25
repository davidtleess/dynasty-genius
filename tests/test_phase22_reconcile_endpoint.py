"""Phase 22 — POST /api/trade/reconcile endpoint tests (4 tests, W2).

RED  → endpoint does not exist; all 4 return 404.
GREEN → after route is wired in app/api/routes/trade.py.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import app.api.routes.trade as trade_route
from app.main import app

client = TestClient(app)

# ── Shared mock artifacts ─────────────────────────────────────────────────────

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


def _mock_pvo(player_ids: list[str], extra_ids: list[str] | None = None) -> dict:
    def _entry(pid: str) -> dict:
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
                "xvar_percentile_overall": 50.0,
                "dynasty_value_score": 50.0,
                "xvar": 15.0,
                "engine_path": "ENGINE_B",
            },
        }

    all_ids = list(player_ids) + list(extra_ids or [])
    return {"players": [_entry(pid) for pid in all_ids]}


def _mock_snapshot(player_ids: list[str]) -> dict:
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


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_reconcile_endpoint_balanced_trade(monkeypatch):
    """Happy path — 1-for-1 at capacity, no overflow, valid schema returned."""
    pids = [f"P{i}" for i in range(20)]
    monkeypatch.setattr(
        trade_route,
        "_load_reconcile_artifacts",
        lambda: (_mock_pvo(pids, ["P_new"]), _mock_snapshot(pids)),
    )

    payload = {
        "david_assets": [{"player_id": "P0", "xvar": 20.0, "position": "WR"}],
        "received_assets": [{"player_id": "P_new", "xvar": 25.0, "position": "WR"}],
    }
    resp = client.post("/api/trade/reconcile", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_supported"] is False
    assert data["roster_penalty"]["post_trade_overflow"] == 0
    assert data["roster_penalty"]["forced_cut_penalty_xvar"] == 0.0
    assert "base_evaluation" in data
    assert "adjusted_david_received_value" in data


def test_reconcile_endpoint_overflow_reduces_adjusted_value(monkeypatch):
    """1-for-2 at capacity → overflow=1; adjusted value is lower than base received value."""
    pids = [f"P{i}" for i in range(20)]
    monkeypatch.setattr(
        trade_route,
        "_load_reconcile_artifacts",
        lambda: (_mock_pvo(pids, ["PA", "PB"]), _mock_snapshot(pids)),
    )

    payload = {
        "david_assets": [{"player_id": "P0", "xvar": 30.0, "position": "WR"}],
        "received_assets": [
            {"player_id": "PA", "xvar": 15.0, "position": "WR"},
            {"player_id": "PB", "xvar": 12.0, "position": "WR"},
        ],
    }
    resp = client.post("/api/trade/reconcile", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["roster_penalty"]["post_trade_overflow"] == 1
    base_received = data["base_evaluation"]["side_b"]["side_value"]
    assert data["adjusted_david_received_value"] < base_received


def test_reconcile_endpoint_picks_only_deal_no_overflow(monkeypatch):
    """All assets are picks (is_prospect=True) → no roster slots consumed → overflow=0."""
    pids = [f"P{i}" for i in range(20)]
    monkeypatch.setattr(
        trade_route,
        "_load_reconcile_artifacts",
        lambda: (_mock_pvo(pids), _mock_snapshot(pids)),
    )

    payload = {
        "david_assets": [
            {"player_id": "pick_1_mid_WR", "xvar": 10.0, "position": "WR", "is_prospect": True}
        ],
        "received_assets": [
            {"player_id": "pick_2_early_RB", "xvar": 8.0, "position": "RB", "is_prospect": True},
            {"player_id": "pick_3_late_QB", "xvar": 5.0, "position": "QB", "is_prospect": True},
        ],
    }
    resp = client.post("/api/trade/reconcile", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["roster_penalty"]["post_trade_overflow"] == 0
    assert data["roster_penalty"]["forced_cut_penalty_xvar"] == 0.0


def test_reconcile_endpoint_decision_supported_false_throughout(monkeypatch):
    """Governance: recursive walk of full response JSON finds zero decision_supported=True."""
    pids = [f"P{i}" for i in range(20)]
    monkeypatch.setattr(
        trade_route,
        "_load_reconcile_artifacts",
        lambda: (_mock_pvo(pids, ["PA", "PB"]), _mock_snapshot(pids)),
    )

    # overflow=1 to exercise forced_cut_candidates in output
    payload = {
        "david_assets": [{"player_id": "P0", "xvar": 20.0, "position": "WR"}],
        "received_assets": [
            {"player_id": "PA", "xvar": 15.0, "position": "WR"},
            {"player_id": "PB", "xvar": 12.0, "position": "WR"},
        ],
    }
    resp = client.post("/api/trade/reconcile", json=payload)

    assert resp.status_code == 200

    def _count_ds_true(obj: object) -> int:
        if isinstance(obj, dict):
            here = 1 if obj.get("decision_supported") is True else 0
            return here + sum(_count_ds_true(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(_count_ds_true(item) for item in obj)
        return 0

    assert _count_ds_true(resp.json()) == 0
