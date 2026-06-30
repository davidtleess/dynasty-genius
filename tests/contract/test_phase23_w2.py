"""Phase 23 W2 Trade Lab market reconciliation contract tests."""
from __future__ import annotations

import inspect

from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    MarketRosterPenalty,
    TradeMarketReconciliation,
    reconcile_trade_market,
)


def _fc_player_row(
    sleeper_id: str, value: int, name: str, *, position: str = "WR"
) -> dict:
    return {
        "player": {
            "name": name,
            "sleeperId": sleeper_id,
            "position": position,
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _cut(sleeper_id: str, name: str, *, position: str = "WR") -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "full_name": name,
        "position": position,
        "decision_supported": False,
    }


def _snapshot(
    *,
    david_players: list[str] | None = None,
    counterparty_players: list[str] | None = None,
    player_universe: list[dict] | None = None,
    taxi: list[str] | None = None,
    reserve: list[str] | None = None,
    starters: list[str] | None = None,
) -> dict:
    return {
        "league": {
            "roster_positions": ["QB", "RB", "WR", "TE", "FLEX"],
            "settings": {"reserve_slots": 2, "taxi_slots": 2},
        },
        "rosters": [
            {
                "roster_id": 1,
                "players": list(david_players or ["sent-1", "received-1", "cut-a"]),
                "starters": list(starters or []),
                "taxi": list(taxi or []),
                "reserve": list(reserve or []),
            },
            {
                "roster_id": 2,
                "players": list(counterparty_players or ["cp-rostered"]),
                "starters": [],
                "taxi": [],
                "reserve": [],
            },
        ],
        "players": list(player_universe or []),
    }


def _snapshot_player(sleeper_id: str, *, position: str = "WR") -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "player": {
            "position": position,
        },
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
    assert "sleeper_snapshot" in params


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
    assert penalty.forced_cut_market_value_at_risk_range is None
    assert penalty.forced_cut_market_recovery_range is None
    assert penalty.market_penalty_status == "ok"


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
        sleeper_snapshot=_snapshot(),
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
        sleeper_snapshot=_snapshot(),
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
        sleeper_snapshot=_snapshot(),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert "market_overlay_display_only" in result.caveats
    assert "fantasycalc_raw_scale_not_xvar" in result.caveats
    assert "market_values_not_model_inputs" in result.caveats
    assert "decision_supported_false" in result.caveats
    assert result.decision_supported is False


def test_market_penalty_uses_fc_scale_depletion_without_selecting_cuts():
    """T4: FC values price model-selected cuts; they never select or reorder cuts."""
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 2,
            "forced_cut_candidates": [
                _cut("cut-a", "Selected Cut A", position="WR"),
                _cut("cut-b", "Selected Cut B", position="WR"),
            ],
        },
        fantasycalc_entries=[
            _fc_player_row("cut-a", 900, "Selected Cut A"),
            _fc_player_row("cut-b", 700, "Selected Cut B"),
            _fc_player_row("wire-1", 500, "Wire One"),
            _fc_player_row("wire-2", 300, "Wire Two"),
            _fc_player_row("wire-3", 100, "Wire Three"),
            # Rostered high-FC player must not replace the model-selected cuts.
            _fc_player_row("rostered-high-fc", 9999, "Rostered High FC"),
        ],
        sleeper_snapshot=_snapshot(
            david_players=["cut-a", "cut-b", "rostered-high-fc"],
            starters=["rostered-high-fc"],
        ),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    penalty = result.david_forced_cut_penalty
    assert penalty is not None
    assert [
        overlay.asset_ref.sleeper_id for overlay in penalty.forced_cut_candidates
    ] == ["cut-a", "cut-b"]
    assert penalty.penalty_market_value == 1600
    assert penalty.forced_cut_market_value_at_risk_range == (800.0, 1200.0)
    assert penalty.forced_cut_market_recovery_range == (400.0, 800.0)
    assert penalty.market_penalty_status == "ok"
    assert "fantasycalc_raw_scale_not_xvar" in penalty.caveats
    assert "market_overlay_display_only" in penalty.caveats


def test_market_pool_deficit_recovers_only_available_fc_values():
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 2,
            "forced_cut_candidates": [
                _cut("cut-a", "Selected Cut A", position="WR"),
                _cut("cut-b", "Selected Cut B", position="WR"),
            ],
        },
        fantasycalc_entries=[
            _fc_player_row("cut-a", 900, "Selected Cut A"),
            _fc_player_row("cut-b", 700, "Selected Cut B"),
            _fc_player_row("wire-1", 500, "Wire One"),
        ],
        sleeper_snapshot=_snapshot(david_players=["cut-a", "cut-b"]),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    penalty = result.david_forced_cut_penalty
    assert penalty is not None
    assert penalty.penalty_market_value == 1600
    assert penalty.forced_cut_market_value_at_risk_range == (1100.0, 1100.0)
    assert penalty.forced_cut_market_recovery_range == (500.0, 500.0)
    assert penalty.market_penalty_status == "ok"
    assert any("market_pool_deficit" in caveat for caveat in penalty.caveats)


def test_market_pool_unavailable_yields_uncertain_band_but_other_side_still_computes():
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 1,
            "forced_cut_candidates": [_cut("david-cut", "David Cut", position="WR")],
        },
        fantasycalc_entries=[
            _fc_player_row("david-cut", 600, "David Cut"),
            _fc_player_row("cp-cut", 1000, "Counterparty Cut"),
            _fc_player_row("rb-wire", 400, "RB Wire", position="RB"),
        ],
        sleeper_snapshot=_snapshot(
            david_players=["david-cut"],
            counterparty_players=["cp-cut"],
        ),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
        counterparty_roster_penalty={
            "roster_id": 2,
            "post_trade_overflow": 1,
            "forced_cut_candidates": [
                _cut("cp-cut", "Counterparty Cut", position="RB"),
            ],
        },
        counterparty_market_penalty_status="available",
    )

    david_penalty = result.david_forced_cut_penalty
    counterparty_penalty = result.counterparty_forced_cut_penalty
    assert david_penalty is not None
    assert counterparty_penalty is not None
    assert david_penalty.market_penalty_status == "uncertain_pool_unavailable"
    assert david_penalty.forced_cut_market_value_at_risk_range == (0.0, 600.0)
    assert david_penalty.forced_cut_market_recovery_range == (0.0, 600.0)
    assert "WR_market_pool_unavailable" in david_penalty.caveats
    assert counterparty_penalty.market_penalty_status == "ok"
    assert counterparty_penalty.forced_cut_market_value_at_risk_range == (600.0, 600.0)
    assert counterparty_penalty.forced_cut_market_recovery_range == (400.0, 400.0)


def test_market_pool_low_fc_coverage_yields_uncertain_band_with_caveat():
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 1,
            "forced_cut_candidates": [_cut("david-cut", "David Cut", position="WR")],
        },
        fantasycalc_entries=[
            _fc_player_row("david-cut", 600, "David Cut"),
            _fc_player_row("wire-valued", 400, "Wire Valued"),
        ],
        sleeper_snapshot=_snapshot(
            david_players=["david-cut"],
            player_universe=[
                _snapshot_player("david-cut", position="WR"),
                _snapshot_player("wire-valued", position="WR"),
                _snapshot_player("wire-missing-1", position="WR"),
                _snapshot_player("wire-missing-2", position="WR"),
            ],
        ),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    penalty = result.david_forced_cut_penalty
    assert penalty is not None
    assert penalty.market_penalty_status == "uncertain_pool_unavailable"
    assert penalty.forced_cut_market_value_at_risk_range == (0.0, 600.0)
    assert penalty.forced_cut_market_recovery_range == (0.0, 600.0)
    assert "WR_market_valuation_coverage_below_floor" in penalty.caveats


def test_market_penalty_blocked_keeps_ranges_none_on_unresolved_cut():
    result = reconcile_trade_market(
        sent_assets=[],
        received_assets=[],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 1,
            "forced_cut_candidates": [_cut("missing-cut", "Missing Cut", position="WR")],
        },
        fantasycalc_entries=[],
        sleeper_snapshot=_snapshot(david_players=["missing-cut"]),
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    penalty = result.david_forced_cut_penalty
    assert penalty is not None
    assert penalty.market_penalty_status == "blocked"
    assert penalty.penalty_market_value == 0
    assert penalty.forced_cut_market_value_at_risk_range is None
    assert penalty.forced_cut_market_recovery_range is None
