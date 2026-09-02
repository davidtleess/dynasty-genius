"""Phase 15 Bayesian blend contract tests - spec sections 5.8, 5.9, 5.10."""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import DVS_BLEND_K
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _mock_identity(position: str) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_blend_weight_monotonicity_wr():
    """5.8: WR k_pos=5 -> w_B at games=1 < games=4 < games=7."""
    k = DVS_BLEND_K["WR"]
    w1 = 1 / (1 + k)
    w4 = 4 / (4 + k)
    w7 = 7 / (7 + k)
    assert w1 < w4 < w7
    assert w1 == pytest.approx(1 / 6, rel=1e-3)
    assert w4 == pytest.approx(4 / 9, rel=1e-3)
    assert w7 == pytest.approx(7 / 12, rel=1e-3)


def test_blend_dvs_engine_when_both_present():
    """5.9: 1 <= games_t <= 7 with Engine A and B inputs -> dvs_engine='blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        "pick": 10.0,
        "round": 1.0,
        "age": 22.0,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "blend"
    assert pvo.dvs_blend_weight_b is not None
    expected_w = 4 / (4 + DVS_BLEND_K["WR"])
    assert pvo.dvs_blend_weight_b == pytest.approx(expected_w, rel=1e-3)


def test_blend_caveat_present_when_blend_fires():
    """5.9: Blend-specific caveat is in pvo.caveats when dvs_engine='blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        "pick": 10.0,
        "round": 1.0,
        "age": 22.0,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "blend"
    # DG-128 (2026-09-01): the blend caveat is a token now (its prose carried w_B=).
    assert any(c.startswith("engine_ab_blend_low_sample:") for c in pvo.caveats), (
        f"Expected blend caveat in caveats, got: {pvo.caveats}"
    )


def test_blend_single_engine_fallback():
    """5.10: Dead Window with no Engine A inputs -> dvs_engine != 'blend', honest caveat.

    DISCLOSED CONTRACT CHANGE (DG-021, 2026-08-25): this test previously asserted the
    caveat "Engine A prospect score used as prior" on a row constructed with NO Engine A
    inputs — it pinned a false self-description (spec 3.4/5.10 as originally written).
    A row with no prior now says so; the prior claim survives only where a prior exists
    (see test_dg021_no_prior_says_so.py, which pins both directions).
    """
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine != "blend"
    assert pvo.dynasty_value_score is None
    assert any("no dynasty value score available" in c for c in pvo.caveats), (
        f"Expected honest no-score caveat in caveats, got: {pvo.caveats}"
    )
    assert not any("Engine A prospect score used as prior" in c for c in pvo.caveats), (
        f"No Engine A result exists here; the prior claim is false: {pvo.caveats}"
    )


# ── DG-128: the blend's Engine B component pays the hurdle ──────────────────────────────
#
# Served value is P(plays) x E[points | plays] (test_availability_composition.py). The
# pure-B branch applied that hurdle from the day it landed; the blend branch did not — it
# normalised the raw projection, so a player at games_t=7 was served an availability-blind
# number while the same player at games_t=8 was discounted. The hurdle is applied to the
# B COMPONENT ONLY: the Engine A prior is a draft-capital model whose training outcomes
# already include the busts, so discounting it again would count attrition twice.


def _blend_fixture(availability_p: float | None) -> dict:
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        "pick": 10.0,
        "round": 1.0,
        "age": 22.0,
    }
    if availability_p is not None:
        features["availability_p"] = availability_p
    return features


def _expected_blend(position: str, games_t: int, dvs_a: float, projection: float,
                    availability_p: float | None) -> float:
    from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG
    from src.dynasty_genius.pvo_assembler import apply_availability

    adjusted = apply_availability(projection, availability_p)
    dvs_b = round(min(100.0, max(0.0, adjusted / ENGINE_B_P90_PPG[position] * 100.0)), 1)
    w_b = games_t / (games_t + DVS_BLEND_K[position])
    return round((1 - w_b) * dvs_a + w_b * dvs_b, 1)


def test_blend_b_component_pays_the_availability_hurdle():
    """DG-128: with availability_p supplied, the blended DVS uses the DISCOUNTED B component."""
    from src.dynasty_genius.scoring.engine_a import score_prospect

    identity = _mock_identity("WR")
    pvo = assemble_pvo(identity, _blend_fixture(availability_p=0.5))
    assert pvo.dvs_engine == "blend"

    dvs_a = score_prospect("WR", 10.0, 1.0, 22.0)["dynasty_value_score"]
    expected = _expected_blend("WR", 4, dvs_a, 12.0, availability_p=0.5)
    assert pvo.dynasty_value_score == pytest.approx(expected, abs=0.051), (
        f"blend served {pvo.dynasty_value_score}, expected {expected} with the B component "
        f"discounted by P(plays)=0.5"
    )
    # And it is a discount: the same row with no availability estimate serves MORE.
    undiscounted = assemble_pvo(identity, _blend_fixture(availability_p=None))
    assert pvo.dynasty_value_score < undiscounted.dynasty_value_score


def test_blend_without_availability_is_unchanged():
    """A missing availability estimate passes the B component through, exactly as pure-B does."""
    from src.dynasty_genius.scoring.engine_a import score_prospect

    identity = _mock_identity("WR")
    pvo = assemble_pvo(identity, _blend_fixture(availability_p=None))
    dvs_a = score_prospect("WR", 10.0, 1.0, 22.0)["dynasty_value_score"]
    expected = _expected_blend("WR", 4, dvs_a, 12.0, availability_p=None)
    assert pvo.dynasty_value_score == pytest.approx(expected, abs=0.051)
