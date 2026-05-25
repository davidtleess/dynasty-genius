"""Phase 23 W1 Trade Lab market resolver contract tests."""
from __future__ import annotations

import pytest

from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetOverlay,
    MarketAssetRef,
    resolve_market_asset,
    resolve_market_assets,
    resolve_pick_market_key,
)


def _fc_pick_row(key: str, value: int, name: str) -> dict:
    return {
        "player": {
            "name": name,
            "mflId": key,
            "sleeperId": key,
            "fleaflickerId": key,
            "position": "PICK",
        },
        "value": value,
        "trend30Day": 10,
        "maybeMovingStandardDeviation": None,
    }


def _fc_player_row(sleeper_id: str, value: int, name: str) -> dict:
    return {
        "player": {
            "name": name,
            "sleeperId": sleeper_id,
            "position": "WR",
        },
        "value": value,
        "trend30Day": -25,
        "maybeMovingStandardDeviation": 4.5,
    }


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("decision_supported") is True else 0
        return count + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_market_reconciliation_decision_supported_false_recursive():
    """W1 schemas must coerce/reject decision_supported=True at every market layer."""
    try:
        asset_ref = MarketAssetRef(
            asset_kind="future_pick",
            year=2027,
            round=1,
            quantity_id="pick-a",
            decision_supported=True,
        )
    except ValueError:
        asset_ref = MarketAssetRef(
            asset_kind="future_pick",
            year=2027,
            round=1,
            quantity_id="pick-a",
        )
    else:
        assert asset_ref.decision_supported is False

    try:
        overlay = MarketAssetOverlay(
            asset_ref=asset_ref,
            label="2027 Round 1 pick",
            source="fantasycalc",
            format_key="dynasty_sf_ppr",
            market_value=3450,
            resolution="pick_generic_year_round",
            coverage_gap=None,
            caveats=[
                "market_overlay_display_only",
                "fantasycalc_raw_scale_not_xvar",
                "generic_future_pick_market_value",
            ],
            decision_supported=True,
        )
    except ValueError:
        return

    assert overlay.decision_supported is False
    assert _decision_supported_true_count(overlay.model_dump()) == 0


def test_exact_pick_slot_resolves_dp_key():
    """A current-year exact rookie pick resolves to the 0-indexed FantasyCalc DP key."""
    asset_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2026,
        round=1,
        slot=1,
        quantity_id="2026-1.01",
    )

    resolution = resolve_pick_market_key(asset_ref, current_draft_year=2026)

    assert resolution.lookup_key == "DP_0_0"
    assert resolution.resolution == "pick_exact_slot"
    assert "generic_future_pick_market_value" not in resolution.caveats


def test_generic_future_pick_resolves_fp_key():
    """A generic future pick resolves to the FC year/round key with slot-spread caveat."""
    asset_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2027,
        round=1,
        quantity_id="2027-first",
    )

    resolution = resolve_pick_market_key(asset_ref, current_draft_year=2026)

    assert resolution.lookup_key == "FP_2027_1"
    assert resolution.resolution == "pick_generic_year_round"
    assert "generic_future_pick_market_value" in resolution.caveats
    assert any("slot-spread" in caveat for caveat in resolution.caveats)


def test_unresolved_pick_market_value_null():
    """An unresolvable or uncovered pick returns null value with explicit FC caveat."""
    asset_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2029,
        round=4,
        quantity_id="uncovered-2029-fourth",
    )

    overlay = resolve_market_asset(
        asset_ref,
        fantasycalc_entries=[],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert overlay.market_value is None
    assert overlay.resolution == "unresolved"
    assert overlay.coverage_gap == "fantasycalc_pick_unavailable"
    assert "fantasycalc_pick_unavailable" in overlay.caveats
    assert overlay.decision_supported is False


def test_bucket_pick_unresolved_without_slot():
    """Early/mid/late bucket picks do not map to generic FC year-round keys."""
    asset_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2027,
        round=1,
        bucket="early",
        quantity_id="2027-early-first",
    )

    resolution = resolve_pick_market_key(asset_ref, current_draft_year=2026)

    assert resolution.lookup_key is None
    assert resolution.resolution == "unresolved"
    assert "fantasycalc_bucket_pick_unavailable" in resolution.caveats


def test_duplicate_pick_assets_preserved():
    """Identical future picks remain separate overlay rows keyed by quantity_id."""
    first_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2027,
        round=1,
        quantity_id="future-first-1",
    )
    second_ref = MarketAssetRef(
        asset_kind="future_pick",
        year=2027,
        round=1,
        quantity_id="future-first-2",
    )

    overlays = resolve_market_assets(
        [first_ref, second_ref],
        fantasycalc_entries=[
            _fc_pick_row("FP_2027_1", 4100, "2027 Round 1 Pick"),
        ],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert len(overlays) == 2
    assert [overlay.asset_ref.quantity_id for overlay in overlays] == [
        "future-first-1",
        "future-first-2",
    ]
    assert [overlay.market_value for overlay in overlays] == [4100, 4100]
    assert overlays[0].asset_ref is not overlays[1].asset_ref
    assert all(overlay.decision_supported is False for overlay in overlays)


def test_player_sleeper_id_resolution_adds_required_caveats():
    """Player assets resolve by Sleeper ID and keep required display-only caveats."""
    asset_ref = MarketAssetRef(
        asset_kind="player",
        player_id="dg-player-1",
        sleeper_id="6794",
    )

    overlay = resolve_market_asset(
        asset_ref,
        fantasycalc_entries=[_fc_player_row("6794", 7147, "Justin Jefferson")],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )

    assert overlay.label == "Justin Jefferson"
    assert overlay.market_value == 7147
    assert overlay.resolution == "player_sleeper_id"
    assert overlay.coverage_gap is None
    assert overlay.trend_30d == -25
    assert overlay.market_volatility == 4.5
    assert "decision_supported_false" in overlay.caveats
    assert overlay.decision_supported is False
