"""Surface 2 Trade Lab asset catalog contract tests.

RED: the pure asset catalog module does not exist yet.
GREEN: build_asset_catalog emits read-only, pre-shaped tradeable assets.
"""
from __future__ import annotations

from typing import Any

from src.dynasty_genius.trade_lab.asset_catalog import build_asset_catalog
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve
from src.dynasty_genius.trade_lab.evaluator import _PICK_CURVE_PATH

CURVE = load_curve(_PICK_CURVE_PATH)


def _pvo() -> dict[str, list[dict[str, Any]]]:
    # Real PVO shape: name/position nest under "player", xvar under "valuation";
    # sleeper_player_id + dvs_engine are top-level; roster info under "league_context".
    return {
        "players": [
            {
                "sleeper_player_id": "100",
                "dvs_engine": "B",
                "player": {"full_name": "Rostered Vet", "position": "WR"},
                "valuation": {"xvar": 22.5},
                "league_context": {
                    "rostered": True,
                    "roster_id": 1,
                    "owner_display_name": "Woodbury Riders",
                },
            },
            {
                "sleeper_player_id": "200",
                "dvs_engine": "A",
                "player": {"full_name": "Rostered Rookie", "position": "RB"},
                "valuation": {"xvar": 14.0},
                "league_context": {
                    "rostered": True,
                    "roster_id": 4,
                    "owner_display_name": "Free Kelly",
                },
            },
            {
                "sleeper_player_id": "250",
                "dvs_engine": "B",
                "player": {"full_name": "Rostered No Xvar", "position": "TE"},
                "valuation": {},
                "league_context": {
                    "rostered": True,
                    "roster_id": 2,
                    "owner_display_name": "No Value FC",
                },
            },
            {
                "sleeper_player_id": "300",
                "dvs_engine": "B",
                "player": {"full_name": "Free Agent", "position": "TE"},
                "valuation": {"xvar": 5.0},
                "league_context": {"rostered": False},
            },
        ]
    }


def _snapshot() -> dict[str, Any]:
    return {
        "captured_at": "2026-05-24T17:19:44Z",
        "future_picks": [
            {
                "season": 2027,
                "round": 1,
                "current_roster_id": 1,
                "original_roster_id": 5,
            },
            {
                "season": 2027,
                "round": 1,
                "current_roster_id": 1,
                "original_roster_id": 8,
            },
            {
                "season": None,
                "round": None,
                "current_roster_id": None,
                "original_roster_id": None,
            },
            {
                "season": "2027",
                "round": "1",
                "current_roster_id": 1,
                "original_roster_id": 9,
            },
            {
                "season": 2030,
                "round": 1,
                "current_roster_id": 1,
                "original_roster_id": 10,
            },
        ],
    }


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def test_short_query_returns_empty_no_serialization() -> None:
    out = build_asset_catalog("ab", _pvo(), _snapshot(), CURVE, limit=50)

    assert out.results == []


def test_blank_or_whitespace_query_returns_empty() -> None:
    assert build_asset_catalog("", _pvo(), _snapshot(), CURVE, limit=50).results == []
    assert build_asset_catalog("   ", _pvo(), _snapshot(), CURVE, limit=50).results == []


def test_unrostered_player_excluded() -> None:
    out = build_asset_catalog("free", _pvo(), _snapshot(), CURVE, limit=50)

    assert all(e.label != "Free Agent" for e in out.results)


def test_rostered_player_with_null_name_is_skipped_not_crashed() -> None:
    # GREEN-side regression (surfaced by the live-endpoint smoke): real PVO rows
    # can carry full_name=None (pseudo/unresolved players). Skip, do not crash.
    pvo = {
        "players": [
            {
                "sleeper_player_id": "0",
                "dvs_engine": None,
                "player": {"full_name": None, "position": None},
                "valuation": {},
                "league_context": {"rostered": True, "roster_id": 3},
            }
        ]
    }

    out = build_asset_catalog("any", pvo, _snapshot(), CURVE, limit=50)

    assert out.results == []


def test_rostered_rookie_is_player_not_prospect() -> None:
    out = build_asset_catalog("rookie", _pvo(), _snapshot(), CURVE, limit=50)

    e = next(e for e in out.results if e.label == "Rostered Rookie")
    assert e.model_payload.is_prospect is False
    assert e.market_ref.asset_kind == "player"


def test_rostered_player_missing_xvar_stays_selectable_with_none_xvar() -> None:
    out = build_asset_catalog("no xvar", _pvo(), _snapshot(), CURVE, limit=50)

    e = next(e for e in out.results if e.label == "Rostered No Xvar")
    assert e.kind == "player"
    assert e.model_payload.xvar is None
    assert e.model_payload.is_prospect is False


def test_future_pick_priced_and_prospect() -> None:
    out = build_asset_catalog("2027", _pvo(), _snapshot(), CURVE, limit=50)

    picks = [e for e in out.results if e.kind == "future_pick"]
    assert len(picks) == 2  # malformed, wrong-type, and out-of-range rows excluded
    assert all(p.model_payload.xvar is not None for p in picks)
    assert all(p.model_payload.is_prospect is True for p in picks)
    qids = {p.market_ref.quantity_id for p in picks}
    assert len(qids) == 2


def test_duplicate_same_round_picks_stay_distinct_by_quantity_id() -> None:
    out = build_asset_catalog("2027", _pvo(), _snapshot(), CURVE, limit=50)

    qids = sorted(
        e.market_ref.quantity_id for e in out.results if e.kind == "future_pick"
    )
    assert qids == [
        "pick:2027:r1:orig5:owner1",
        "pick:2027:r1:orig8:owner1",
    ]


def test_malformed_pick_row_excluded() -> None:
    out = build_asset_catalog("2027", _pvo(), _snapshot(), CURVE, limit=50)

    assert all(e.asset_id != "pick:None:rNone:origNone:ownerNone" for e in out.results)
    assert all(e.asset_id != "pick:2027:r1:orig9:owner1" for e in out.results)
    assert all(e.asset_id != "pick:2030:r1:orig10:owner1" for e in out.results)


def test_no_market_value_in_model_payload_and_decision_supported_locked() -> None:
    out = build_asset_catalog("rostered", _pvo(), _snapshot(), CURVE, limit=50)

    for e in out.results:
        assert not any("market" in str(k).lower() for k in e.model_payload.model_dump())
    assert out.decision_supported is False
    assert _decision_supported_true_count(out) == 0


def test_entry_carries_roster_owner_name() -> None:
    out = build_asset_catalog("vet", _pvo(), _snapshot(), CURVE, limit=50)

    e = next(e for e in out.results if e.label == "Rostered Vet")
    assert e.roster_owner_name == "Woodbury Riders"


def test_limit_clamped_for_negative_and_large_values() -> None:
    assert build_asset_catalog("ros", _pvo(), _snapshot(), CURVE, limit=-1).results == []
    big = build_asset_catalog("ros", _pvo(), _snapshot(), CURVE, limit=500)
    assert len(big.results) <= 100


def test_empty_universe_and_snapshot_returns_empty_with_caveat() -> None:
    out = build_asset_catalog(
        "anything",
        {"players": []},
        {"captured_at": "2026-05-24T17:19:44Z", "future_picks": []},
        CURVE,
        limit=50,
    )

    assert out.results == []
    assert out.decision_supported is False
