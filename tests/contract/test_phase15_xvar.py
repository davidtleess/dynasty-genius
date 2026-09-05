"""Phase 15 xVAR contract tests - spec sections 5.1, 5.2, 5.4, 5.11.

SR-13 (DG-092) also lives here: the coupled-constant identity guard. The
"TE lambda should be 0.703" finding from an earlier SEASON-BRIEF.md is
RETRACTED (2026-08-20) — lambda[pos] = anchor[pos]/anchor['WR'] exactly for
all four positions, so a lambda-only edit CREATES a distortion rather than
removing one. DG-159 replaced four position denominators with one shared
anchor (20.1, David's ruling 2026-09-04), which makes every lambda 1.000 and
every replacement baseline a division by the same number; the identity itself
is unchanged. See the engine_b_contract.py module docstring.

Clamp measurement, preserved from dropped SR-17 (model_forward_capture.db,
capture_date 2026-08-20, engine_path ENGINE_B, dynasty_value_score >= 100):

    QB 0/37 · RB 5/99 · WR 6/163 · TE 11/89 at the DVS ceiling

Eleven of 89 TEs sit tied at the ceiling — the REAL TE defect is clamp
ORDERING at pvo_assembler.py:408-409 (``dvs_clamped_flag = dvs_raw > 100.0``
then ``round(min(100.0, max(0.0, dvs_raw)), 1)``), not a scaling defect a
lambda edit could fix.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    DVS_SCALE_ANCHOR_PPG,
    ENGINE_A_REPLACEMENT_DVS,
    ENGINE_B_REPLACEMENT_DVS,
    REPLACEMENT_PPG,
    XVAR_LAMBDA_ENGINE_A,
    XVAR_LAMBDA_ENGINE_B,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _mock_identity(position: str, is_prospect: bool = False) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        is_prospect=is_prospect,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_xvar_formula_wr():
    """5.1: xVAR = (DVS - replacement) x lambda, on the served number.

    DG-159: 14.5 points a game used to BE the receiver ceiling and so scored 100.
    On one denominator it scores 72.1, because 14.5 is not what the best football
    player produces — 20.1 is. The formula is unchanged; what a receiver at the top
    of his own position is worth on the shared scale is the thing that moved.
    """
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score == pytest.approx(72.1, abs=0.1)
    expected_xvar = round(
        (pvo.dynasty_value_score - ENGINE_B_REPLACEMENT_DVS["WR"])
        * XVAR_LAMBDA_ENGINE_B["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected_xvar, abs=0.1)
    assert pvo.xvar_anchor == "WR"


def test_xvar_formula_qb_higher_than_wr_at_same_dvs():
    """5.1: the quarterback at his position's ceiling outvalues the receiver at his.

    It used to be the lambda that carried this — a bigger multiplier on the same
    score. DG-159 removes the multiplier and the ordering survives, because it was
    never really about the multiplier: 20.1 points a game beats 14.5, and one
    denominator is what lets the two numbers say so directly.
    """
    wr_pvo = assemble_pvo(
        _mock_identity("WR"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
            "games_t": 10,
            "feature_season": 2024,
        },
    )
    qb_pvo = assemble_pvo(
        _mock_identity("QB"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 20.1, "engine": "test_v2"},
            "games_t": 10,
            "feature_season": 2024,
        },
    )
    assert qb_pvo.xvar is not None and wr_pvo.xvar is not None
    assert qb_pvo.xvar > wr_pvo.xvar


def test_a_prospect_and_a_veteran_are_now_on_the_same_cross_positional_unit():
    """5.2, rewritten by DG-159. This test used to assert the OPPOSITE — that a QB
    prospect must get Engine A's lambda (1.315) and not Engine B's (1.386) — and
    that difference was the defect, not the contract. The two engines divided by
    different ceilings, so a rookie and a veteran with the same points above
    replacement carried cross-positional values about 14% apart, and 80 of the 582
    scored players were on the wrong side of it.

    One denominator serves both engines, so the two constants are now equal by
    construction and the prospect's value is the veteran's arithmetic.
    """
    identity = _mock_identity("QB", is_prospect=True)
    pvo = assemble_pvo(identity, {"pick": 10.0, "round": 1.0, "age": 21.0})
    assert pvo.dvs_engine == "A"
    assert pvo.xvar is not None and pvo.dynasty_value_score is not None

    assert XVAR_LAMBDA_ENGINE_A["QB"] == XVAR_LAMBDA_ENGINE_B["QB"]
    assert ENGINE_A_REPLACEMENT_DVS["QB"] == ENGINE_B_REPLACEMENT_DVS["QB"]

    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["QB"])
        * XVAR_LAMBDA_ENGINE_A["QB"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.1)


def test_engine_a_lambda_applied_for_prospect():
    """5.2: WR prospect uses Engine A replacement and lambda."""
    identity = _mock_identity("WR", is_prospect=True)
    pvo = assemble_pvo(identity, {"pick": 5.0, "round": 1.0, "age": 21.0})
    assert pvo.dvs_engine == "A"
    assert pvo.xvar_anchor == "WR"
    assert pvo.xvar is not None and pvo.dynasty_value_score is not None
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["WR"])
        * XVAR_LAMBDA_ENGINE_A["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.1)


def test_xvar_ceiling_bound_when_clamped():
    """5.4: dvs_clamped=True -> xvar_ceiling_bound=True."""
    identity = _mock_identity("QB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 30.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_clamped is True
    assert pvo.xvar_ceiling_bound is True


# ── SR-13 (DG-092): coupled-constant identity guard ──────────────────────────

_XVAR_POSITIONS = ("QB", "RB", "WR", "TE")

# Replacement-level PPG (12-team Superflex Full PPR). Until DG-159 this test
# carried its own copy of the four numbers, because none existed in the code —
# they lived only in inline comments citing var_batch_20260516_190328.json, an
# artifact that does not contain them (it holds 13.47 / 8.59 / 8.65 / 9.76). A
# restated copy is exactly how a constant with no derivation survives: the test
# and the code agreed with each other and neither agreed with anything measured.
# They are now a derived, dated constant and this reads it.
_REPLACEMENT_PPG = REPLACEMENT_PPG


@pytest.mark.parametrize("pos", _XVAR_POSITIONS)
def test_sr13_lambda_is_exact_scale_ratio(pos: str) -> None:
    """SR-13: XVAR_LAMBDA_ENGINE_B[pos] == round(anchor[pos]/anchor['WR'], 3).

    The lambdas convert a position's own scale into the anchor's; they are not
    free parameters. Editing one alone creates a cross-positional distortion —
    exactly what the RETRACTED "TE should be 0.703" edit would have done.
    Under DG-159's single denominator the ratio is 1.000 everywhere, which is
    the identity holding rather than being switched off.
    """
    expected = round(DVS_SCALE_ANCHOR_PPG[pos] / DVS_SCALE_ANCHOR_PPG["WR"], 3)
    assert XVAR_LAMBDA_ENGINE_B[pos] == pytest.approx(expected, abs=0.001), (
        f"XVAR_LAMBDA_ENGINE_B[{pos!r}] = {XVAR_LAMBDA_ENGINE_B[pos]} but "
        f"anchor[{pos!r}]/anchor['WR'] = {expected}. The 'TE lambda should be "
        "0.703' finding is RETRACTED (2026-08-20; SR-13/DG-092) — do NOT edit "
        "one constant alone. DVS_SCALE_ANCHOR_PPG, XVAR_LAMBDA_ENGINE_B, "
        "REPLACEMENT_PPG and ENGINE_B_REPLACEMENT_DVS move together (new "
        "derivation + David approval) or not at all. See engine_b_contract.py's "
        "module docstring."
    )


@pytest.mark.parametrize("pos", _XVAR_POSITIONS)
def test_sr13_replacement_dvs_derives_from_replacement_ppg(pos: str) -> None:
    """SR-13: ENGINE_B_REPLACEMENT_DVS[pos] == round(repl_PPG/anchor[pos]*100, 1).

    Same coupled system as the lambda test: replacement DVS is replacement PPG
    normalized by the SAME denominator the lambda is built from and the score
    divides by. Moving the anchor without recomputing this (or vice versa)
    silently shifts every xVAR for the position.
    """
    expected = round(_REPLACEMENT_PPG[pos] / DVS_SCALE_ANCHOR_PPG[pos] * 100, 1)
    assert ENGINE_B_REPLACEMENT_DVS[pos] == pytest.approx(expected, abs=0.05), (
        f"ENGINE_B_REPLACEMENT_DVS[{pos!r}] = {ENGINE_B_REPLACEMENT_DVS[pos]} "
        f"but replacement_PPG/anchor*100 = {expected} "
        f"({_REPLACEMENT_PPG[pos]} / {DVS_SCALE_ANCHOR_PPG[pos]} * 100). These "
        "constants are one coupled system with DVS_SCALE_ANCHOR_PPG and "
        "XVAR_LAMBDA_ENGINE_B (SR-13/DG-092) — never move one alone. See "
        "engine_b_contract.py's module docstring."
    )


def test_te_xvar_computable_decision_supported_false():
    """5.11: TE has computable xVAR but decision_supported=False."""
    identity = _mock_identity("TE")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 9.0, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.xvar is not None
    assert pvo.decision_supported is False
    assert any("TE market superiority gate deferred" in caveat for caveat in pvo.caveats)
