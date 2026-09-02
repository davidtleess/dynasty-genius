"""DG-128: Engine A is a rookie model — for a veteran it reads his DRAFT-season age, never his current one.

Engine A (`score_prospect`) was trained on nflverse draft-pick rows whose `age` is the
prospect's age in his draft season (20–26; WR mean 22.1, coefficient −0.81 ppg per year).
A veteran's feature row carries `age` = his CURRENT age (21–45 in the runtime table),
because that is what Engine B and the PVO's `age` field mean by it. Feeding that key to
Engine A extrapolates a rookie model years outside anything it saw: on one WR fixture the
blend served 63.8 with current age 27 and 81.5 with draft age 22.

So the two meanings get two keys. Engine A reads `age_at_nfl_entry` for a veteran and
does NOT fall back to `age`; a veteran with draft capital but no draft-season age gets
no Engine A prior (and the DG-021 caveat says so) rather than a wrong one. Prospects
keep `age` — for a prospect the two are the same number, and the prospect cards set both.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import DVS_BLEND_K, ENGINE_B_P90_PPG
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.scoring.engine_a import score_prospect


def _wr(dg_id: str = "vet") -> PlayerIdentity:
    return PlayerIdentity(
        dg_id=dg_id,
        full_name="Veteran WR",
        position="WR",
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_a_veteran_with_only_his_current_age_gets_no_engine_a_prior() -> None:
    pvo = assemble_pvo(_wr(), {"pick": 5.0, "round": 1.0, "age": 27.0}, is_prospect=False)
    assert pvo.dynasty_value_score is None, (
        f"a rookie model was fed a 27-year-old's current age and served {pvo.dynasty_value_score}"
    )
    assert pvo.dvs_engine is None
    assert pvo.nfl_draft_pick == 5  # the draft capital itself is still carried


def test_engine_a_reads_the_draft_season_age_for_a_veteran() -> None:
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2025,
        "pick": 10.0,
        "round": 1.0,
        "age": 27.0,  # current age — Engine B's meaning
        "age_at_nfl_entry": 22.0,  # draft-season age — Engine A's meaning
    }
    pvo = assemble_pvo(_wr(), features, is_prospect=False)
    assert pvo.dvs_engine == "blend"

    dvs_a = score_prospect("WR", 10.0, 1.0, 22.0)["dynasty_value_score"]
    dvs_b = round(min(100.0, max(0.0, 12.0 / ENGINE_B_P90_PPG["WR"] * 100.0)), 1)
    w_b = 4 / (4 + DVS_BLEND_K["WR"])
    expected = round((1 - w_b) * dvs_a + w_b * dvs_b, 1)
    assert pvo.dynasty_value_score == pytest.approx(expected, abs=0.051), (
        f"blend served {pvo.dynasty_value_score}; with Engine A on draft age 22 it is {expected}"
    )
    # The PVO's own age field keeps the current age — that is what it has always meant.
    assert pvo.age == 27.0


def test_a_prospect_still_scores_on_age() -> None:
    """Prospect cards set both keys to the same number; `age` alone must keep working for them."""
    prospect = PlayerIdentity(
        dg_id="rookie", full_name="Rookie WR", position="WR",
        verification_status="VERIFIED_NFL_DRAFT",
    )
    pvo = assemble_pvo(prospect, {"pick": 10.0, "round": 1.0, "age": 21.0}, is_prospect=True)
    assert pvo.dvs_engine == "A"
    assert pvo.dynasty_value_score == pytest.approx(
        score_prospect("WR", 10.0, 1.0, 21.0)["dynasty_value_score"], abs=0.051
    )
