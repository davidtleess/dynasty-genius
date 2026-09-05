"""DG-128 (2026-09-01): every served score leaves the assembler with its band.

The band's FORM is pinned in test_dg128_dvs_band.py. This file pins that the assembler applies
it to the right basis with the right components: measured players get sigma_B, prior-only
players get sigma_A, and a blend gets the root-sum-square form over the components EXACTLY as
they entered the blend (B hurdle-adjusted and clamped). No score, no band.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius import pvo_assembler
from src.dynasty_genius.models.dvs_band import ENGINE_A_V3_HEAD, dvs_band
from src.dynasty_genius.models.engine_b_contract import (
    DVS_BLEND_K,
    ENGINE_B_MIN_GAMES_T,
    DVS_SCALE_ANCHOR_PPG,
)
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
    games_t, projection, availability_p = ENGINE_B_MIN_GAMES_T - 1, 12.0, 0.5
    pvo = assemble_pvo(
        _identity("WR"),
        {
            "engine_b_score": _b_score(projection),
            "games_t": games_t,
            "feature_season": 2025,
            "availability_p": availability_p,
            "pick": 10.0,
            "round": 1.0,
            # Engine A (v2) reads the prospect's age under `age`; a 22-year-old in his
            # first season, so the draft-season age and the current age coincide.
            "age": 22.0,
        },
    )
    assert pvo.dvs_engine == "blend"

    dvs_a = score_prospect("WR", 10.0, 1.0, 22.0)["dynasty_value_score"]
    adjusted = apply_availability(projection, availability_p)
    dvs_b = round(min(100.0, max(0.0, adjusted / DVS_SCALE_ANCHOR_PPG["WR"] * 100.0)), 1)
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


def test_a_te_prospect_scored_by_the_v3_head_ships_that_head_s_band(monkeypatch) -> None:
    # The assembler tries the v3 TE head first and falls back to the v2 ridge; whichever
    # produced the number is the one whose error the band must carry. The v3 head's is
    # wider (29.7 vs 23.6 DVS), so a v2 band on a v3 number would overstate its authority.
    def v3_scored(position: str, features: dict) -> dict:
        assert position == "TE"
        return {
            "dynasty_value_score": 80.0,
            "dvs_clamped": False,
            "engine_used": ENGINE_A_V3_HEAD,
            "model_version": "head_a_te_v3_ridge",
            "model_grade": "MODEL",
            "y24_ppg_raw": 7.28,
            "caveats": ["head_a_v3_college_features_used"],
        }

    monkeypatch.setattr(pvo_assembler, "score_prospect_v3", v3_scored)
    pvo = assemble_pvo(_identity("TE"), {"pick": 40.0, "round": 2.0, "age": 21.0}, is_prospect=True)
    assert pvo.dvs_engine == "A"
    assert pvo.engine_used == ENGINE_A_V3_HEAD
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == dvs_band(
        pvo.dynasty_value_score, "TE", engine="A", prior_head=ENGINE_A_V3_HEAD
    )
    assert (pvo.dvs_band_low, pvo.dvs_band_high) != dvs_band(pvo.dynasty_value_score, "TE", engine="A")


def test_no_score_means_no_band() -> None:
    pvo = assemble_pvo(_identity("WR"), {"engine_b_score": _b_score(12.0), "games_t": 3, "feature_season": 2025})
    assert pvo.dynasty_value_score is None
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == (None, None)


def test_the_blend_caveat_is_a_token_the_copy_dictionary_can_say() -> None:
    # Until DG-128 no blend row was ever served, so its caveat was never screened.
    # It carried "w_B=0.44", a raw key the render rule refuses on sight, and
    # "interpret with caution" — hedging David struck from the screen on 2026-08-29.
    # The caveat is a token now; the sentence lives in frontend/src/lib/copy.ts.
    pvo = assemble_pvo(
        _identity("WR"),
        {
            "engine_b_score": _b_score(12.0),
            "games_t": ENGINE_B_MIN_GAMES_T - 1,
            "feature_season": 2025,
            "pick": 10.0,
            "round": 1.0,
            # Engine A (v2) reads the prospect's age under `age`; a 22-year-old in his
            # first season, so the draft-season age and the current age coincide.
            "age": 22.0,
        },
    )
    assert pvo.dvs_engine == "blend"
    assert f"engine_ab_blend_low_sample:games={ENGINE_B_MIN_GAMES_T - 1}" in pvo.caveats
    assert not any("w_B" in caveat or "caution" in caveat for caveat in pvo.caveats)
