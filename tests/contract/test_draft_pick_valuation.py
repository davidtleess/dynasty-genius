from __future__ import annotations

import inspect
import json
import warnings
from pathlib import Path

import pandas as pd

from src.dynasty_genius.scoring.engine_a import ENGINE_A_P90_PPG
from src.dynasty_genius.trade_lab.draft_pick_valuation import (
    PickValue,
    apply_sf_qb_ordering,
    build_slot_curve,
    player_xvar_from_ppg,
    smooth_and_tier,
    value_pick,
)
from src.dynasty_genius.trade_lab.evaluator import TradeAsset, value_draft_pick


def test_engine_a_p90_public_constant_present():
    # Public, governed P90 used by the pick-value curve; no private _P90_PPG import.
    assert ENGINE_A_P90_PPG["WR"] == 12.7
    assert set(ENGINE_A_P90_PPG) == {"QB", "RB", "WR", "TE"}


def test_player_xvar_from_ppg_uses_position_constants():
    # WR: P90=12.7, replacement_DVS=69.2, lambda=1.0
    # DVS = min(100, 12.7/12.7*100) = 100.0; xVAR = (100-69.2)*1.0
    assert round(player_xvar_from_ppg(12.7, "WR"), 2) == 30.8


def test_player_xvar_from_ppg_clamps_dvs_at_100():
    assert player_xvar_from_ppg(50.0, "WR") == player_xvar_from_ppg(12.7, "WR")


def test_player_xvar_from_ppg_zero_ppg_is_negative_or_floor():
    # DVS=0 -> xVAR=(0-69.2)*1.0 = -69.2. Do not clamp sub-replacement here.
    assert round(player_xvar_from_ppg(0.0, "WR"), 1) == -69.2


def _fixture_df() -> pd.DataFrame:
    # Two mature years, three skill players each, known PPG, and low-sample flags.
    rows = []
    for year in (2015, 2016):
        for pick, pos, ppg, low in (
            (1, "QB", 16.7, 0),
            (2, "WR", 12.7, 0),
            (3, "RB", 7.3, 1),
        ):
            rows.append(
                {
                    "draft_year": year,
                    "pick": pick,
                    "position": pos,
                    "y24_ppg": ppg,
                    "low_sample_flag": low,
                }
            )
    return pd.DataFrame(rows)


def test_build_slot_curve_aggregates_xvar_per_slot():
    curve = build_slot_curve(_fixture_df(), mature_years=(2015, 2016), board_size=3)

    slot_one = curve["slots"]["1"]
    # QB 16.7 -> DVS 100 -> xVAR (100-77.3)*1.315 = 29.8505.
    assert round(slot_one["expected_xvar"], 2) == 29.85
    assert slot_one["n_years"] == 2
    assert slot_one["positions"] == {"QB": 2}
    assert curve["mature_years_used"] == [2015, 2016]


def test_build_slot_curve_counts_low_sample_flag_per_slot():
    curve = build_slot_curve(_fixture_df(), mature_years=(2015, 2016), board_size=3)

    assert curve["slots"]["3"]["low_sample_count"] == 2


def test_build_slot_curve_prices_picks_as_non_negative_option_value():
    df = pd.DataFrame(
        [
            {
                "draft_year": 2015,
                "pick": 1,
                "position": "WR",
                "y24_ppg": 12.7,
                "low_sample_flag": 0,
            },
            {
                "draft_year": 2016,
                "pick": 1,
                "position": "WR",
                "y24_ppg": 0.0,
                "low_sample_flag": 0,
            },
        ]
    )

    curve = build_slot_curve(df, mature_years=(2015, 2016), board_size=1)
    slot_one = curve["slots"]["1"]

    assert min(slot_one["raw_samples"]) < 0
    assert round(min(slot_one["raw_samples"]), 1) == -69.2
    assert slot_one["priced_samples"] == [30.8, 0.0]
    assert slot_one["expected_xvar"] == 15.4


def test_smooth_and_tier_clamps_monotonic_non_increasing():
    curve = {
        "board_size": 4,
        "slots": {
            "1": {"expected_xvar": 30.0},
            "2": {"expected_xvar": 25.0},
            "3": {"expected_xvar": 28.0},
            "4": {"expected_xvar": 10.0},
        },
    }

    out = smooth_and_tier(curve)
    smoothed = [
        out["slots"][str(slot)]["expected_xvar_smoothed"] for slot in range(1, 5)
    ]

    assert smoothed == sorted(smoothed, reverse=True)
    assert out["slots"]["3"]["expected_xvar_smoothed"] == 25.0


def test_tier_rollup_uses_member_slot_median_after_clamp():
    curve = {
        "board_size": 4,
        "slots": {
            "1": {"expected_xvar": 30.0},
            "2": {"expected_xvar": 25.0},
            "3": {"expected_xvar": 20.0},
            "4": {"expected_xvar": 10.0},
        },
        "tier_map": {
            "early_1st": [1, 2],
            "late_1st": [3, 4],
            "round_1_generic": [1, 2, 3, 4],
        },
    }

    out = smooth_and_tier(curve)

    assert out["tiers"]["early_1st"] == 27.5
    assert out["tiers"]["round_1_generic"] == 22.5


def test_sf_qb_ordering_promotes_qb_by_k_slots():
    board = [(5, "WR"), (8, "RB"), (40, "QB"), (12, "WR")]

    out = apply_sf_qb_ordering(board, k_slots=2, round_threshold_pick=64)

    assert [position for _, position in out][:1] == ["QB"]


def test_sf_qb_ordering_multiple_qbs_stable():
    board = [(5, "WR"), (40, "QB"), (8, "RB"), (50, "QB"), (12, "WR")]

    out = apply_sf_qb_ordering(board, k_slots=1, round_threshold_pick=64)
    positions = [position for _, position in out]
    qb_indexes = [index for index, position in enumerate(positions) if position == "QB"]

    assert positions[0] == "QB"
    assert qb_indexes[0] < qb_indexes[1]


_CURVE = {
    "version": "v1",
    "board_size": 4,
    "slots": {"2": {"expected_xvar_smoothed": 25.0}},
    "tiers": {"early_1st": 27.5, "round_1_generic": 18.0},
}


def test_value_pick_exact_slot():
    pick_value = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)

    assert isinstance(pick_value, PickValue)
    assert pick_value.xvar == 25.0
    assert pick_value.decision_supported is False
    assert "pick_value_historical_expected" in pick_value.caveats
    assert "pick_value_floored_at_replacement" in pick_value.caveats


def test_value_pick_tier():
    pick_value = value_pick(year=2027, round_=1, tier="early_1st", curve=_CURVE)

    assert pick_value.xvar == 27.5
    assert pick_value.resolution == "tier"


def test_value_pick_round_only_uses_round_generic_tier():
    pick_value = value_pick(year=2028, round_=1, curve=_CURVE)

    assert pick_value.resolution == "round_tier"
    assert pick_value.xvar == 18.0
    assert "generic_future_pick_round_only" in pick_value.caveats


def test_value_pick_requires_no_position():
    assert "position" not in inspect.signature(value_pick).parameters


def test_value_pick_decision_supported_locked():
    pick_value = PickValue(
        year=2027,
        round_=1,
        slot=2,
        xvar=25.0,
        resolution="exact_slot",
        caveats=[],
        decision_supported=True,
    )

    assert pick_value.decision_supported is False


def test_curve_artifact_built_and_shaped():
    path = Path("app/data/valuation/draft_pick_value_curve_v1.json")

    assert path.exists(), "run scripts/build_draft_pick_value_curve.py first"
    curve = json.loads(path.read_text())

    assert curve["version"] == "v1"
    assert curve["board_size"] == 36
    assert all(int(year) <= 2022 for year in curve["mature_years_used"])
    assert "1" in curve["slots"]
    assert "expected_xvar_smoothed" in curve["slots"]["1"]


def test_value_draft_pick_returns_tradeasset_curve_backed():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        wr_asset = value_draft_pick(round_=1, pick_bucket="mid", position="WR", age=21)
        rb_asset = value_draft_pick(round_=1, pick_bucket="mid", position="RB", age=21)

    assert any(issubclass(warning.category, DeprecationWarning) for warning in caught)
    assert isinstance(wr_asset, TradeAsset)
    assert wr_asset.is_prospect is True
    assert wr_asset.decision_supported is False
    assert wr_asset.dvs_engine == "pick_curve_v1"
    assert wr_asset.dvs is None
    assert wr_asset.xvar == rb_asset.xvar
