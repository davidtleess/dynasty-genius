from __future__ import annotations

import json

import pytest

from src.dynasty_genius.trade_lab.draft_pick_valuation import (
    PickValue,
    load_prospect_board,
    value_pick,
)

_CURVE = {
    "version": "v1",
    "board_size": 4,
    "slots": {"2": {"expected_xvar_smoothed": 25.0}},
    "tiers": {"early_1st": 27.5, "round_1_generic": 18.0},
}

_BOARD = {1: 30.0, 2: 12.0, 3: -5.0}


def _write_cards(tmp_path, rows: list[dict]) -> str:
    path = tmp_path / "cards.json"
    path.write_text(json.dumps(rows))
    return str(path)


def test_curve_path_sets_historical_curve_regime():
    pick_value = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)

    assert pick_value.valuation_regime == "historical_curve"


def test_pickvalue_supports_board_resolutions_and_regime():
    pick_value = PickValue(
        year=2027,
        round_=1,
        slot=2,
        xvar=5.0,
        resolution="board_exact_slot",
        valuation_regime="prospect_board",
        caveats=[],
    )

    assert pick_value.resolution == "board_exact_slot"
    assert pick_value.valuation_regime == "prospect_board"
    assert pick_value.decision_supported is False


def test_load_prospect_board_filters_class_rank_and_xvar(tmp_path):
    rows = [
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 30.0},
        {"draft_class": 2026, "xvar_class_rank": 2, "xvar": 12.0},
        {"draft_class": 2026, "xvar_class_rank": None, "xvar": 5.0},
        {"draft_class": 2027, "xvar_class_rank": 1, "xvar": 99.0},
        {"draft_class": 2026, "xvar_class_rank": 3, "xvar": None},
        {"draft_class": 2026, "xvar_class_rank": 4, "xvar": "bad"},
    ]

    board = load_prospect_board(2026, path=_write_cards(tmp_path, rows))

    assert board == {1: 30.0, 2: 12.0}


def test_load_prospect_board_raises_on_duplicate_rank(tmp_path):
    rows = [
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 30.0},
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 28.0},
    ]

    with pytest.raises(ValueError):
        load_prospect_board(2026, path=_write_cards(tmp_path, rows))


def test_board_exact_slot_uses_floored_rank_value():
    pick_value = value_pick(
        year=2026,
        round_=1,
        slot=3,
        curve=_CURVE,
        prospect_board=_BOARD,
    )

    assert pick_value.valuation_regime == "prospect_board"
    assert pick_value.resolution == "board_exact_slot"
    assert pick_value.xvar == 0.0
    assert "pick_value_board_class_specific" in pick_value.caveats
    assert "pick_value_historical_expected" not in pick_value.caveats


def test_board_round_only_is_mean_of_floored_over_range():
    pick_value = value_pick(
        year=2026,
        round_=1,
        curve=_CURVE,
        prospect_board=_BOARD,
    )

    assert pick_value.valuation_regime == "prospect_board"
    assert pick_value.resolution == "board_round"
    assert pick_value.xvar == 14.0
    assert "pick_value_board_partial_round_coverage" in pick_value.caveats


def test_board_exact_slot_beyond_board_is_unresolved_not_curve():
    pick_value = value_pick(
        year=2026,
        round_=1,
        slot=9,
        curve=_CURVE,
        prospect_board=_BOARD,
    )

    assert pick_value.valuation_regime == "prospect_board"
    assert pick_value.resolution == "unresolved"
    assert pick_value.xvar is None
    assert "pick_value_board_slot_beyond_coverage" in pick_value.caveats


def test_empty_board_falls_back_to_curve_bit_identical():
    with_empty = value_pick(
        year=2027,
        round_=1,
        slot=2,
        curve=_CURVE,
        prospect_board={},
    )
    curve_only = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)

    assert with_empty.model_dump() == curve_only.model_dump()
    assert with_empty.valuation_regime == "historical_curve"


def test_tier_with_board_routes_to_curve():
    pick_value = value_pick(
        year=2027,
        round_=1,
        tier="early_1st",
        curve=_CURVE,
        prospect_board=_BOARD,
    )

    assert pick_value.valuation_regime == "historical_curve"
    assert pick_value.resolution == "tier"
