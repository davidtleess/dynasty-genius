"""Section 5 — Roster Auditor Engine B integration tests.

Covers:
  - Cliff-contextualized trade signal (_cliff_trade_signal)
  - TE experimental caveat propagation from Engine B score
  - cliff_trade_signal field present on audit output
  - Market isolation: Engine B prediction dict contains no prohibited features
  - Engine B prediction attached to audit output when score provided
"""
from __future__ import annotations

import pytest

from app.services.roster_auditor import (
    _ABOVE_AVG_PPG_THRESHOLD,
    _cliff_trade_signal,
    audit_player,
)
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_PROHIBITED_FEATURES


# ── _cliff_trade_signal ────────────────────────────────────────────────────────

def test_past_cliff_always_sell_off():
    assert _cliff_trade_signal("past_cliff", 25.0, "QB") == "SELL_OFF"
    assert _cliff_trade_signal("past_cliff", None, "RB") == "SELL_OFF"
    assert _cliff_trade_signal("past_cliff", 0.0, "WR") == "SELL_OFF"


def test_no_projection_when_predicted_ppg_is_none():
    assert _cliff_trade_signal("no_age_signal", None, "WR") == "NO_PROJECTION"
    assert _cliff_trade_signal("approaching_cliff", None, "RB") == "NO_PROJECTION"
    assert _cliff_trade_signal("at_cliff", None, "TE") == "NO_PROJECTION"


def test_sell_high_when_approaching_cliff_and_above_avg():
    threshold = _ABOVE_AVG_PPG_THRESHOLD["RB"]
    assert _cliff_trade_signal("approaching_cliff", threshold + 1.0, "RB") == "SELL_HIGH_APPROACHING_CLIFF"
    assert _cliff_trade_signal("at_cliff", threshold + 1.0, "RB") == "SELL_HIGH_APPROACHING_CLIFF"


def test_monitor_when_approaching_cliff_and_below_avg():
    threshold = _ABOVE_AVG_PPG_THRESHOLD["WR"]
    assert _cliff_trade_signal("approaching_cliff", threshold - 1.0, "WR") == "MONITOR_APPROACHING_CLIFF"
    assert _cliff_trade_signal("at_cliff", threshold - 1.0, "WR") == "MONITOR_APPROACHING_CLIFF"


def test_championship_window_when_away_from_cliff_and_above_avg():
    threshold = _ABOVE_AVG_PPG_THRESHOLD["QB"]
    assert _cliff_trade_signal("no_age_signal", threshold + 2.0, "QB") == "CHAMPIONSHIP_WINDOW"


def test_hold_when_away_from_cliff_and_below_avg():
    threshold = _ABOVE_AVG_PPG_THRESHOLD["WR"]
    assert _cliff_trade_signal("no_age_signal", threshold - 2.0, "WR") == "HOLD"


def test_pm_example_rb_approaching_cliff_with_high_projection():
    """RB at 25 (age 25.5→int 25, cliff 26 → approaching) projected 16.5 PPG → SELL HIGH."""
    # 16.5 > 12.0 (RB threshold) and signal = approaching_cliff
    result = _cliff_trade_signal("approaching_cliff", 16.5, "RB")
    assert result == "SELL_HIGH_APPROACHING_CLIFF"


def test_threshold_boundary_is_inclusive():
    """Exactly at threshold is considered above average."""
    for pos, threshold in _ABOVE_AVG_PPG_THRESHOLD.items():
        result = _cliff_trade_signal("no_age_signal", threshold, pos)
        assert result == "CHAMPIONSHIP_WINDOW", f"{pos} at exact threshold should be CHAMPIONSHIP_WINDOW"


# ── audit_player integration ───────────────────────────────────────────────────

def test_audit_player_includes_cliff_trade_signal():
    player = {"player_id": "rb1", "full_name": "Young RB", "position": "RB", "team": "KC", "age": 23}
    result = audit_player(player)
    assert result is not None
    assert "cliff_trade_signal" in result


def test_audit_player_no_projection_when_no_engine_b_score():
    player = {"player_id": "wr1", "full_name": "WR Young", "position": "WR", "team": "SF", "age": 22}
    result = audit_player(player)
    assert result["cliff_trade_signal"] == "NO_PROJECTION"


def test_audit_player_trade_signal_uses_engine_b_ppg():
    """When Engine B score is provided, trade signal reflects the predicted PPG."""
    player = {"player_id": "rb1", "full_name": "Prime RB", "position": "RB", "team": "PHI", "age": 25}
    engine_b_score = {
        "predicted_avg_ppg_t1_t2": 17.5,
        "engine": "engine_b_v2_rb",
        "position": "RB",
        "experimental": False,
        "caveats": ["engine_b_not_decision_grade"],
    }
    result = audit_player(player, engine_b_score=engine_b_score)
    # age 25, RB cliff 26 → years_to_cliff = 1 → approaching_cliff
    # 17.5 > 12.0 (RB threshold) → SELL_HIGH_APPROACHING_CLIFF
    assert result["cliff_trade_signal"] == "SELL_HIGH_APPROACHING_CLIFF"


def test_audit_player_engine_b_prediction_attached():
    player = {"player_id": "wr2", "full_name": "WR2", "position": "WR", "team": "DET", "age": 24}
    engine_b_score = {
        "predicted_avg_ppg_t1_t2": 14.2,
        "engine": "engine_b_v2_wr",
        "position": "WR",
        "experimental": False,
        "caveats": ["engine_b_not_decision_grade"],
    }
    result = audit_player(player, engine_b_score=engine_b_score)
    assert result["engine_b_prediction"] == engine_b_score
    assert result["engine_b_prediction"]["predicted_avg_ppg_t1_t2"] == 14.2


# ── TE experimental caveat propagation ────────────────────────────────────────

def test_te_experimental_caveat_propagates_from_engine_b_score():
    player = {"player_id": "te1", "full_name": "TE Player", "position": "TE", "team": "KC", "age": 26}
    engine_b_score = {
        "predicted_avg_ppg_t1_t2": 9.1,
        "engine": "engine_b_v1",
        "position": "TE",
        "experimental": True,
        "caveats": ["engine_b_not_decision_grade", "engine_b_does_not_beat_baseline_for_this_position"],
    }
    result = audit_player(player, engine_b_score=engine_b_score)
    assert "engine_b_experimental_v1_fallback" in result["caveats"]


def test_non_te_score_does_not_add_experimental_caveat():
    for pos in ("QB", "RB", "WR"):
        player = {"player_id": f"{pos.lower()}1", "full_name": f"{pos} Player", "position": pos, "team": "KC", "age": 24}
        engine_b_score = {
            "predicted_avg_ppg_t1_t2": 15.0,
            "engine": f"engine_b_v2_{pos.lower()}",
            "position": pos,
            "experimental": False,
            "caveats": ["engine_b_not_decision_grade"],
        }
        result = audit_player(player, engine_b_score=engine_b_score)
        assert "engine_b_experimental_v1_fallback" not in result["caveats"], f"{pos} should not have experimental caveat"


def test_te_without_engine_b_score_does_not_add_experimental_caveat():
    """No score → no_usage_signal, not experimental_v1_fallback."""
    player = {"player_id": "te2", "full_name": "TE NoScore", "position": "TE", "team": "FA", "age": 27}
    result = audit_player(player)
    assert "engine_b_experimental_v1_fallback" not in result["caveats"]
    assert "no_usage_signal" in result["caveats"]


# ── Market isolation ───────────────────────────────────────────────────────────

def test_engine_b_prediction_contains_no_prohibited_market_features():
    """Engine B service output must never contain market-derived feature keys.

    This verifies the market-isolation boundary at the roster auditor level.
    KTC/ADP/FantasyCalc values must not appear inside engine_b_prediction.
    """
    player = {"player_id": "wr3", "full_name": "WR3", "position": "WR", "team": "LAR", "age": 25}
    engine_b_score = {
        "predicted_avg_ppg_t1_t2": 13.0,
        "engine": "engine_b_v2_wr",
        "position": "WR",
        "experimental": False,
        "feature_season": 2024,
        "decision_supported": False,
        "caveats": ["engine_b_not_decision_grade"],
    }
    result = audit_player(player, engine_b_score=engine_b_score)
    prediction = result["engine_b_prediction"]
    leaked = set(prediction.keys()) & ENGINE_B_PROHIBITED_FEATURES
    assert not leaked, f"Market features leaked into Engine B prediction: {leaked}"
