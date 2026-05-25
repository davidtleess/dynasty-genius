"""Phase 23 W2 Trade Lab market reconciliation contract tests."""
from __future__ import annotations

import inspect

from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    MarketRosterPenalty,
    TradeMarketReconciliation,
    reconcile_trade_market,
)


def _fc_player_row(sleeper_id: str, value: int, name: str) -> dict:
    return {
        "player": {
            "name": name,
            "sleeperId": sleeper_id,
            "position": "WR",
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _cut(sleeper_id: str, name: str) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "full_name": name,
        "position": "WR",
        "decision_supported": False,
    }


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("decision_supported") is True else 0
        return count + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_w2_reconciler_accepts_phase22_forced_cuts_without_fetching_rosters():
    """W2 prices an already-selected Phase 22 cut set; it does not fetch/select cuts."""
    params = inspect.signature(reconcile_trade_market).parameters

    assert "david_roster_penalty" in params
    assert "fantasycalc_entries" in params
    assert "universe_pvo" not in params
    assert "sleeper_snapshot" not in params


def test_trade_market_reconciliation_decision_supported_false_recursive():
    """W2 market penalty/reconciliation schemas must lock decision_supported=False."""
    cut_ref = MarketAssetRef(asset_kind="player", sleeper_id="cut-1")
    cut_overlay = {
        "asset_ref": cut_ref,
        "label": "Cut Player",
        "source": "fantasycalc",
        "format_key": "dynasty_sf_ppr",
        "market_value": 700,
        "resolution": "player_sleeper_id",
        "coverage_gap": None,
        "caveats": ["market_overlay_display_only", "decision_supported_false"],
        "decision_supported": True,
    }
    penalty = MarketRosterPenalty(
        roster_id=1,
        post_trade_overflow=1,
        forced_cut_candidates=[cut_overlay],
        penalty_market_value=700,
        unresolved_cut_count=0,
        caveats=["market_overlay_display_only"],
        decision_supported=True,
    )
    reconciliation = TradeMarketReconciliation(
        market_source="fantasycalc",
        format_key="dynasty_sf_ppr",
        source_timestamp="2026-05-25T13:00:00Z",
        sent_assets=[],
        received_assets=[],
        market_sent_raw=0,
        market_received_raw=0,
        david_forced_cut_penalty=penalty,
        counterparty_forced_cut_penalty=None,
        adjusted_market_sent=0,
        adjusted_market_received=0,
        market_delta_for_david=0,
        coverage_gaps=[],
        caveats=["market_overlay_display_only"],
        decision_supported=True,
    )

    assert penalty.decision_supported is False
    assert reconciliation.decision_supported is False
    assert _decision_supported_true_count(reconciliation.model_dump()) == 0


def test_david_side_market_reconciliation_subtracts_selected_cut_values_only():
    """Section 8: adjusted received = raw received minus resolved selected cuts."""
    result = reconcile_trade_market(
        sent_assets=[
            MarketAssetRef(asset_kind="player", player_id="sent-1", sleeper_id="sent-1"),
        ],
        received_assets=[
            MarketAssetRef(asset_kind="player", player_id="received-1", sleeper_id="received-1"),
        ],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 2,
            "forced_cut_candidates": [
                _cut("cut-resolved", "Resolved Cut"),
                _cut("cut-unresolved", "Unresolved Cut"),
            ],
        },
        fantasycalc_entries=[
            _fc_player_row("sent-1", 1000, "Sent Player"),
            _fc_player_row("received-1", 5000, "Received Player"),
            _fc_player_row("cut-resolved", 700, "Resolved Cut"),
            _fc_player_row("not-selected-cut", 9000, "Not Selected Cut"),
        ],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
        source_timestamp="2026-05-25T13:00:00Z",
    )

    assert result.market_sent_raw == 1000
    assert result.market_received_raw == 5000
    assert result.david_forced_cut_penalty is not None
    assert result.david_forced_cut_penalty.penalty_market_value == 700
    assert result.david_forced_cut_penalty.unresolved_cut_count == 1
    assert [
        overlay.asset_ref.sleeper_id
        for overlay in result.david_forced_cut_penalty.forced_cut_candidates
    ] == ["cut-resolved", "cut-unresolved"]
    assert result.adjusted_market_sent == 1000
    assert result.adjusted_market_received == 4300
    assert result.market_delta_for_david == 3300
    assert "fantasycalc_uncovered" in result.coverage_gaps


def test_w2_counterparty_penalty_deferred_to_phase23_5():
    """W2 is single-sided only; counterparty market penalty remains deferred/null."""
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 0,
            "forced_cut_candidates": [],
        },
        fantasycalc_entries=[],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert result.david_forced_cut_penalty is not None
    assert result.david_forced_cut_penalty.penalty_market_value == 0
    assert result.counterparty_forced_cut_penalty is None
    assert result.adjusted_market_sent == 0
    assert result.adjusted_market_received == 0


def test_market_reconciliation_caveats_preserve_overlay_isolation():
    """Top-level W2 output carries required display-only market caveats."""
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 0,
            "forced_cut_candidates": [],
        },
        fantasycalc_entries=[],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert "market_overlay_display_only" in result.caveats
    assert "fantasycalc_raw_scale_not_xvar" in result.caveats
    assert "market_values_not_model_inputs" in result.caveats
    assert "decision_supported_false" in result.caveats
    assert result.decision_supported is False
