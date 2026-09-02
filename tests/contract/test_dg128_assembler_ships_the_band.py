"""DG-128 (2026-09-01): every served score leaves the assembler with its band.

The band's FORM is pinned in test_dg128_dvs_band.py. This file pins that the assembler applies
it to the right basis with the right components: measured players get sigma_B, prior-only
players get sigma_A, and a blend gets the root-sum-square form over the components EXACTLY as
they entered the blend (B hurdle-adjusted and clamped). No score, no band.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.models.dvs_band import dvs_band
from src.dynasty_genius.models.engine_b_contract import DVS_BLEND_K, ENGINE_B_P90_PPG
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import apply_availability, assemble_pvo
from src.dynasty_genius.scoring.engine_a import score_prospect


def _identity(position: str = "WR") -> PlayerIdentity:
    return PlayerIdentity(
        dg_id=f"dg128-band-{position.lower()}",
        full_name="Band Fixture",
        position=position,
        birth_date="2000-01-01",
        nfl_team="NYJ",
        sleeper_id="1",
        verification_status="VERIFIED",
        identity_verified=True,
        age_verified=True,
    )


def _b_score(projection: float) -> dict:
    return {"predicted_avg_ppg_t1_t2": projection, "engine": "test_v2"}


def test_a_measured_player_ships_one_sigma_b_each_side() -> None:
    pvo = assemble_pvo(
        _identity("WR"),
        {"engine_b_score": _b_score(12.0), "games_t": 12, "feature_season": 2025, "availability_p": 0.9},
    )
    assert pvo.dvs_engine == "B"
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == dvs_band(pvo.dynasty_value_score, "WR", engine="B")
    assert pvo.dvs_band_low < pvo.dynasty_value_score < pvo.dvs_band_high


def test_a_blended_player_s_band_uses_the_components_as_they_entered_the_blend() -> None:
    games_t, projection, availability_p = 4, 12.0, 0.5
    pvo = assemble_pvo(
        _identity("WR"),
        {
            "engine_b_score": _b_score(projection),
            "games_t": games_t,
            "feature_season": 2025,
            "availability_p": availability_p,
            "pick": 10.0,
            "round": 1.0,
            "age_at_nfl_entry": 22.0,
        },
    )
    assert pvo.dvs_engine == "blend"

    dvs_a = score_prospect("WR", 10.0, 1.0, 22.0)["dynasty_value_score"]
    adjusted = apply_availability(projection, availability_p)
    dvs_b = round(min(100.0, max(0.0, adjusted / ENGINE_B_P90_PPG["WR"] * 100.0)), 1)
    w_b = games_t / (games_t + DVS_BLEND_K["WR"])
    expected = dvs_band(pvo.dynasty_value_score, "WR", engine="blend", w_b=w_b, dvs_a=dvs_a, dvs_b=dvs_b)
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == pytest.approx(expected, abs=0.051)

    # Wider than the same score would carry as a measured player: the prior's authority is lower.
    measured_low, measured_high = dvs_band(pvo.dynasty_value_score, "WR", engine="B")
    assert pvo.dvs_band_low < measured_low and pvo.dvs_band_high > measured_high


def test_a_prior_only_prospect_ships_sigma_a() -> None:
    pvo = assemble_pvo(_identity("RB"), {"pick": 40.0, "round": 2.0, "age": 21.0}, is_prospect=True)
    assert pvo.dvs_engine == "A"
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == dvs_band(pvo.dynasty_value_score, "RB", engine="A")


def test_no_score_means_no_band() -> None:
    pvo = assemble_pvo(_identity("WR"), {"engine_b_score": _b_score(12.0), "games_t": 3, "feature_season": 2025})
    assert pvo.dynasty_value_score is None
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == (None, None)
