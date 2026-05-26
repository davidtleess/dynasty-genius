from __future__ import annotations

import inspect

import src.dynasty_genius.trade_lab.draft_pick_valuation as dpv

_BANNED_TOKENS = ("buy", "sell", "win", "loss", "verdict", "accept", "reject")


def test_pick_valuation_module_is_model_blind():
    source = inspect.getsource(dpv)

    for needle in ("fantasycalc", "mock", "adp", "WalkForwardDriver", "score_prospect"):
        assert needle not in source, f"{needle} must not appear in pick valuation"


def test_pick_value_outputs_carry_no_banned_language():
    pick_value = dpv.value_pick(
        year=2027,
        round_=1,
        slot=1,
        curve={"slots": {"1": {"expected_xvar_smoothed": 5.0}}},
    )
    blob = " ".join(pick_value.caveats).lower() + pick_value.resolution.lower()

    assert not any(token in blob for token in _BANNED_TOKENS)
    assert pick_value.decision_supported is False
