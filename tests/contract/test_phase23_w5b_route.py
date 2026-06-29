"""Phase 23 W5b route wiring contract tests.

RED  -> app/api/routes/trade_market.py does not hydrate model assets or call the
        cross-lane producer after W4 yet.
GREEN -> the market route preserves W5a/W3/W4 behavior, then runs a separate
         hydrated model reconcile and appends only the W5b warning/caveats.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import app.api.routes.trade_market as trade_market_route
from app.main import app
from src.dynasty_genius.trade_lab.cross_lane_review import CrossLaneReviewResult
from src.dynasty_genius.trade_lab.market_reconciler import MarketRealismWarning

client = TestClient(app)

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


def _pvo_entry(pid: str, xvar: float | None, position: str = "WR") -> dict[str, Any]:
    return {
        "sleeper_player_id": pid,
        "player": {
            "full_name": f"Player {pid}",
            "position": position,
            "age": 24.0,
            "years_exp": 2,
            "sleeper_status": "Active",
        },
        "valuation": {
            "xvar_percentile_overall": 50.0,
            "dynasty_value_score": 50.0,
            "xvar": xvar,
            "engine_path": "ENGINE_B",
        },
    }


def _universe_pvo() -> dict[str, Any]:
    return {
        "players": [
            _pvo_entry("P0", 30.0),
            _pvo_entry("PA", 20.0),
            _pvo_entry("P1", 4.0),
            *[_pvo_entry(f"R{i}", 1.0) for i in range(18)],
        ]
    }


def _snapshot() -> dict[str, Any]:
    return {
        "league": {
            "roster_positions": _POSITIONS_20,
            "settings": _SETTINGS_NO_RESERVE,
        },
        "rosters": [
            {
                "roster_id": 1,
                "players": ["P0", "P1"] + [f"R{i}" for i in range(18)],
                "taxi": [],
                "reserve": [],
            }
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


def _fc_pick_row(key: str, value: int) -> dict[str, Any]:
    return {
        "player": {
            "name": key,
            "sleeperId": key,
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _fantasycalc_entries() -> list[dict[str, Any]]:
    return [
        _fc_player_row("P0", 9000),
        _fc_player_row("PA", 4000),
        _fc_player_row("P1", 1000),
        _fc_pick_row("DP_0_2", 3000),
        _fc_pick_row("FP_2027_2", 1200),
    ]


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
        ]
    }


def _payload_with_priced_picks() -> dict[str, Any]:
    return {
        "sent_assets": [
            {"asset_kind": "player", "player_id": "P0", "sleeper_id": "P0"},
        ],
        "received_assets": [
            {"asset_kind": "player", "player_id": "PA", "sleeper_id": "PA"},
            {
                "asset_kind": "future_pick",
                "year": 2026,
                "round": 1,
                "slot": 3,
                "quantity_id": "exact-2026-1.03",
            },
            {
                "asset_kind": "future_pick",
                "year": 2027,
                "round": 2,
                "quantity_id": "round-2027-2",
            },
        ],
        "current_draft_year": 2026,
        "format_key": "dynasty_sf_ppr",
    }


def _payload_with_bucket_pick() -> dict[str, Any]:
    payload = _payload_with_priced_picks()
    payload["received_assets"].append(
        {
            "asset_kind": "future_pick",
            "year": 2027,
            "round": 1,
            "bucket": "early",
            "quantity_id": "bucket-2027-early-1st",
        }
    )
    return payload


def _fake_roster_reconciliation(
    *,
    favors: str = "side_b",
    favors_status: str = "david",
    forced_cut_candidates: list[dict[str, Any]] | None = None,
    post_trade_overflow: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        base_evaluation=SimpleNamespace(
            side_a=SimpleNamespace(side_value=30.0),
        ),
        roster_penalty=SimpleNamespace(
            post_trade_total_players=20,
            post_trade_overflow=post_trade_overflow,
            forced_cut_candidates=forced_cut_candidates or [],
            forced_cut_penalty_xvar=0.0,
            penalty_caveats=[],
        ),
        adjusted_david_received_value=45.0,
        adjusted_favors=favors,
        adjusted_favors_status=favors_status,
    )


def _install_common_route_mocks(monkeypatch, events: list[str]) -> None:
    monkeypatch.setattr(
        trade_market_route,
        "_load_reconcile_artifacts",
        lambda: (_universe_pvo(), _snapshot()),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_fetch_fantasycalc_entries",
        lambda: (_fantasycalc_entries(), []),
    )
    monkeypatch.setattr(
        trade_market_route,
        "_load_market_divergence_artifact",
        lambda: _divergence_artifact(),
    )

    original_reconcile_market = trade_market_route.reconcile_trade_market

    def market_spy(*args, **kwargs):
        events.append("market")
        return original_reconcile_market(*args, **kwargs)

    monkeypatch.setattr(trade_market_route, "reconcile_trade_market", market_spy)

    original_attach_divergence = trade_market_route.attach_market_divergence_context

    def w3_spy(*args, **kwargs):
        events.append("w3")
        return original_attach_divergence(*args, **kwargs)

    monkeypatch.setattr(
        trade_market_route, "attach_market_divergence_context", w3_spy
    )

    def w4_spy(reconciliation, *, gamma, psi):
        events.append("w4")
        return reconciliation

    monkeypatch.setattr(
        trade_market_route, "attach_competitive_realism_warnings", w4_spy
    )


def _install_reconcile_spy(
    monkeypatch,
    events: list[str],
    calls: list[dict],
    *,
    cut_reconciliation: SimpleNamespace | None = None,
    hydrated_reconciliation: SimpleNamespace | None = None,
) -> None:
    def reconcile_spy(david_assets, received_assets, universe_pvo, sleeper_snapshot):
        label = "cut_reconcile" if not calls else "hydrated_reconcile"
        events.append(label)
        calls.append(
            {
                "label": label,
                "sent": list(david_assets),
                "received": list(received_assets),
            }
        )
        if label == "cut_reconcile" and cut_reconciliation is not None:
            return cut_reconciliation
        if label == "hydrated_reconcile" and hydrated_reconciliation is not None:
            return hydrated_reconciliation
        return _fake_roster_reconciliation()

    monkeypatch.setattr(trade_market_route, "reconcile_trade_roster", reconcile_spy)


def _install_pick_value_spies(monkeypatch, calls: list[dict]) -> None:
    def value_pick_spy(year: int, round_: int, **kwargs):
        calls.append({"year": year, "round": round_, **kwargs})
        if year == 2026 and round_ == 1 and kwargs.get("slot") == 3:
            return SimpleNamespace(xvar=7.0)
        if year == 2027 and round_ == 2 and kwargs.get("slot") is None:
            return SimpleNamespace(xvar=3.0)
        raise AssertionError(f"Unexpected value_pick call: {year=} {round_=} {kwargs=}")

    monkeypatch.setattr(trade_market_route, "value_pick", value_pick_spy, raising=False)

    import src.dynasty_genius.trade_lab.draft_pick_valuation as draft_pick_valuation

    monkeypatch.setattr(draft_pick_valuation, "value_pick", value_pick_spy)


def test_market_route_hydrates_model_assets_and_appends_cross_lane_warning(
    monkeypatch,
):
    events: list[str] = []
    reconcile_calls: list[dict] = []
    value_pick_calls: list[dict] = []
    producer_calls: list[dict] = []
    _install_common_route_mocks(monkeypatch, events)
    _install_reconcile_spy(monkeypatch, events, reconcile_calls)
    _install_pick_value_spies(monkeypatch, value_pick_calls)

    warning = MarketRealismWarning(
        warning_type="market_package_requires_manual_review",
        severity="advisory",
        message=(
            "Model favors David but Market favors Counterparty. The asset package "
            "is flagged for manual review."
        ),
        metrics={
            "model_delta_signed": 15.0,
            "adjusted_model_sent": 30.0,
            "adjusted_model_received": 45.0,
            "model_relative_delta": 15.0 / 45.0,
            "model_direction_code": 1.0,
            "market_delta_for_david": -800,
            "adjusted_market_sent": 9000,
            "adjusted_market_received": 8200,
            "market_relative_delta": 800 / 9000,
            "market_direction_code": -1.0,
            "parity_band": 0.10,
        },
        caveats=["market_realism_warning_only"],
    )

    def producer_spy(**kwargs):
        events.append("producer")
        producer_calls.append(kwargs)
        return CrossLaneReviewResult(warning=warning)

    monkeypatch.setattr(
        trade_market_route,
        "evaluate_cross_lane_manual_review",
        producer_spy,
        raising=False,
    )

    response = client.post("/api/trade/reconcile/market", json=_payload_with_priced_picks())

    assert response.status_code == 200
    data = response.json()
    assert [w["warning_type"] for w in data["realism_warnings"]] == [
        "market_package_requires_manual_review"
    ]
    assert [call["label"] for call in reconcile_calls] == [
        "cut_reconcile",
        "hydrated_reconcile",
    ]
    assert [asset.xvar for asset in reconcile_calls[0]["sent"]] == [None]
    assert [asset.xvar for asset in reconcile_calls[0]["received"]] == [None, None, None]
    assert [asset.xvar for asset in reconcile_calls[1]["sent"]] == [30.0]
    assert [asset.xvar for asset in reconcile_calls[1]["received"]] == [
        20.0,
        7.0,
        3.0,
    ]
    assert value_pick_calls == [
        {"year": 2026, "round": 1, "slot": 3, "curve": value_pick_calls[0]["curve"]},
        {"year": 2027, "round": 2, "curve": value_pick_calls[1]["curve"]},
    ]
    assert producer_calls == [
        {
            "model_favors_raw": "david",
            "model_coverage_complete": True,
            "model_delta_signed": 15.0,
            "adjusted_model_sent": 30.0,
            "adjusted_model_received": 45.0,
            "market_delta_for_david": data["market_delta_for_david"],
            "adjusted_market_sent": data["adjusted_market_sent"],
            "adjusted_market_received": data["adjusted_market_received"],
            "market_coverage_complete": True,
        }
    ]
    assert events.index("hydrated_reconcile") > events.index("w4")
    assert events.index("producer") > events.index("hydrated_reconcile")


def test_market_route_sources_model_favors_from_range_native_status(monkeypatch):
    events: list[str] = []
    reconcile_calls: list[dict] = []
    producer_calls: list[dict] = []
    value_pick_calls: list[dict] = []
    _install_common_route_mocks(monkeypatch, events)
    _install_reconcile_spy(
        monkeypatch,
        events,
        reconcile_calls,
        hydrated_reconciliation=_fake_roster_reconciliation(
            favors="side_b",
            favors_status="uncertain_range_crosses_parity",
        ),
    )
    _install_pick_value_spies(monkeypatch, value_pick_calls)

    def producer_spy(**kwargs):
        events.append("producer")
        producer_calls.append(kwargs)
        return CrossLaneReviewResult(warning=None, suppressed_reason=None)

    monkeypatch.setattr(
        trade_market_route,
        "evaluate_cross_lane_manual_review",
        producer_spy,
        raising=False,
    )

    response = client.post("/api/trade/reconcile/market", json=_payload_with_priced_picks())

    assert response.status_code == 200
    assert producer_calls[0]["model_favors_raw"] == "uncertain_range_crosses_parity"
    assert [call["label"] for call in reconcile_calls] == [
        "cut_reconcile",
        "hydrated_reconcile",
    ]


def test_market_route_bucket_pick_fails_closed_with_specific_caveats(monkeypatch):
    events: list[str] = []
    reconcile_calls: list[dict] = []
    producer_calls: list[dict] = []
    value_pick_calls: list[dict] = []
    _install_common_route_mocks(monkeypatch, events)
    _install_reconcile_spy(monkeypatch, events, reconcile_calls)
    _install_pick_value_spies(monkeypatch, value_pick_calls)

    def producer_spy(**kwargs):
        events.append("producer")
        producer_calls.append(kwargs)
        return CrossLaneReviewResult(
            warning=None,
            suppressed_reason=frozenset(
                {"model_coverage_incomplete", "market_coverage_incomplete"}
            ),
        )

    monkeypatch.setattr(
        trade_market_route,
        "evaluate_cross_lane_manual_review",
        producer_spy,
        raising=False,
    )

    response = client.post("/api/trade/reconcile/market", json=_payload_with_bucket_pick())

    assert response.status_code == 200
    data = response.json()
    assert data["realism_warnings"] == []
    assert "cross_lane_manual_review_suppressed_model_coverage_incomplete" in data[
        "caveats"
    ]
    assert "cross_lane_manual_review_suppressed_market_coverage_incomplete" in data[
        "caveats"
    ]
    assert producer_calls[0]["model_coverage_complete"] is False
    assert producer_calls[0]["market_coverage_complete"] is False
    assert [asset.xvar for asset in reconcile_calls[1]["received"]] == [
        20.0,
        7.0,
        3.0,
        None,
    ]
    assert len(value_pick_calls) == 2


def test_market_route_no_warning_preserves_market_w3_w4_fields(monkeypatch):
    events: list[str] = []
    reconcile_calls: list[dict] = []
    producer_calls: list[dict] = []
    value_pick_calls: list[dict] = []
    _install_common_route_mocks(monkeypatch, events)
    _install_reconcile_spy(monkeypatch, events, reconcile_calls)
    _install_pick_value_spies(monkeypatch, value_pick_calls)

    def producer_spy(**kwargs):
        events.append("producer")
        producer_calls.append(kwargs)
        return CrossLaneReviewResult(warning=None, suppressed_reason=None)

    monkeypatch.setattr(
        trade_market_route,
        "evaluate_cross_lane_manual_review",
        producer_spy,
        raising=False,
    )

    response = client.post("/api/trade/reconcile/market", json=_payload_with_priced_picks())

    assert response.status_code == 200
    data = response.json()
    assert data["realism_warnings"] == []
    assert data["market_sent_raw"] == 9000
    assert data["market_received_raw"] == 8200
    assert data["adjusted_market_sent"] == 9000
    assert data["adjusted_market_received"] == 8200
    assert data["market_delta_for_david"] == -800
    assert data["david_forced_cut_penalty"]["post_trade_overflow"] == 0
    assert data["david_forced_cut_penalty"]["penalty_market_value"] == 0
    assert data["counterparty_forced_cut_penalty"] is None
    assert data["sent_assets"][0]["divergence_context"]["signal_label"] == (
        "model_higher_than_market"
    )
    assert data["received_assets"][0]["divergence_context"]["signal_label"] == (
        "inside_band"
    )
    assert [call["label"] for call in reconcile_calls] == [
        "cut_reconcile",
        "hydrated_reconcile",
    ]
    assert events.index("hydrated_reconcile") > events.index("w4")
    assert events.index("producer") > events.index("hydrated_reconcile")
    assert producer_calls[0]["model_coverage_complete"] is True
    assert producer_calls[0]["market_coverage_complete"] is True


def test_market_route_forced_cut_gaps_fail_closed_with_specific_caveats(
    monkeypatch,
):
    events: list[str] = []
    reconcile_calls: list[dict] = []
    producer_calls: list[dict] = []
    value_pick_calls: list[dict] = []
    _install_common_route_mocks(monkeypatch, events)
    uncovered_cut = {
        "sleeper_player_id": "PX",
        "full_name": "Player PX",
        "position": "WR",
        "xvar_raw": None,
    }
    _install_reconcile_spy(
        monkeypatch,
        events,
        reconcile_calls,
        cut_reconciliation=_fake_roster_reconciliation(
            forced_cut_candidates=[uncovered_cut],
            post_trade_overflow=1,
        ),
        hydrated_reconciliation=_fake_roster_reconciliation(
            forced_cut_candidates=[uncovered_cut],
            post_trade_overflow=1,
        ),
    )
    _install_pick_value_spies(monkeypatch, value_pick_calls)

    def producer_spy(**kwargs):
        events.append("producer")
        producer_calls.append(kwargs)
        return CrossLaneReviewResult(
            warning=None,
            suppressed_reason=frozenset(
                {"model_coverage_incomplete", "market_coverage_incomplete"}
            ),
        )

    monkeypatch.setattr(
        trade_market_route,
        "evaluate_cross_lane_manual_review",
        producer_spy,
        raising=False,
    )

    response = client.post("/api/trade/reconcile/market", json=_payload_with_priced_picks())

    assert response.status_code == 200
    data = response.json()
    assert data["realism_warnings"] == []
    assert data["david_forced_cut_penalty"]["post_trade_overflow"] == 1
    assert data["david_forced_cut_penalty"]["unresolved_cut_count"] == 1
    assert "fantasycalc_uncovered" in data["coverage_gaps"]
    assert producer_calls == [
        {
            "model_favors_raw": "david",
            "model_coverage_complete": False,
            "model_delta_signed": 15.0,
            "adjusted_model_sent": 30.0,
            "adjusted_model_received": 45.0,
            "market_delta_for_david": data["market_delta_for_david"],
            "adjusted_market_sent": data["adjusted_market_sent"],
            "adjusted_market_received": data["adjusted_market_received"],
            "market_coverage_complete": False,
        }
    ]
    assert "cross_lane_manual_review_suppressed_model_coverage_incomplete" in data[
        "caveats"
    ]
    assert "cross_lane_manual_review_suppressed_market_coverage_incomplete" in data[
        "caveats"
    ]
    assert events.index("hydrated_reconcile") > events.index("w4")
    assert events.index("producer") > events.index("hydrated_reconcile")
