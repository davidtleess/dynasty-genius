"""Phase 15 xVAR contract tests - spec sections 5.1, 5.2, 5.4, 5.11.

SR-13 (DG-092) also lives here: the coupled-constant identity guard. The
"TE lambda should be 0.703" finding from an earlier SEASON-BRIEF.md is
RETRACTED (2026-08-20) — lambda[pos] = P90[pos]/P90['WR'] exactly for all
four positions, and the position P90 cancels in unclamped xVAR
(pvo_assembler.py:407), so a lambda-only edit CREATES an 8.4% TE distortion
where none exists. See the engine_b_contract.py module docstring.

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
    ENGINE_A_REPLACEMENT_DVS,
    ENGINE_B_P90_PPG,
    ENGINE_B_REPLACEMENT_DVS,
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
    """5.1: WR DVS=100, replacement=60.6, lambda=1.000 -> xVAR=39.4."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    expected_xvar = round(
        (100.0 - ENGINE_B_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_B["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected_xvar, abs=0.1)
    assert pvo.xvar_anchor == "WR"


def test_xvar_formula_qb_higher_than_wr_at_same_dvs():
    """5.1: QB lambda > WR lambda, so QB xVAR exceeds WR xVAR at same DVS."""
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


def test_engine_a_lambda_applied_for_qb_prospect():
    """5.2: QB prospect uses Engine A lambda (1.315), not Engine B lambda (1.386)."""
    identity = _mock_identity("QB", is_prospect=True)
    # DG-128 (2026-09-01): PlayerIdentity has no is_prospect field — the kwarg on _mock_identity was
    # silently ignored, so this 'prospect' test never marked a prospect. It passed only because Engine A
    # read `age` for everyone; now that a veteran's `age` is his current age, say prospect where meant.
    pvo = assemble_pvo(identity, {"pick": 10.0, "round": 1.0, "age": 21.0}, is_prospect=True)
    assert pvo.dvs_engine == "A"
    assert pvo.xvar is not None and pvo.dynasty_value_score is not None
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["QB"])
        * XVAR_LAMBDA_ENGINE_A["QB"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.1)
    # Confirm Engine B QB lambda was NOT applied.
    wrong = round(
        (pvo.dynasty_value_score - ENGINE_B_REPLACEMENT_DVS["QB"])
        * XVAR_LAMBDA_ENGINE_B["QB"],
        2,
    )
    assert pvo.xvar != pytest.approx(wrong, abs=0.01)


def test_engine_a_lambda_applied_for_prospect():
    """5.2: WR prospect uses Engine A replacement and lambda."""
    identity = _mock_identity("WR", is_prospect=True)
    pvo = assemble_pvo(identity, {"pick": 5.0, "round": 1.0, "age": 21.0}, is_prospect=True)  # DG-128: see above
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

# Replacement-level PPG (12-team Superflex Full PPR), Phase 14 calibration
# audit (var_batch_20260516_190328.json). Source of record: the inline
# comments on ENGINE_B_REPLACEMENT_DVS in
# src/dynasty_genius/models/engine_b_contract.py:111-115
# ("QB": 64.2,  # 12.91 / 20.1 ... "TE": 95.6,  # 8.99 / 9.4). No
# REPLACEMENT_PPG constant exists in the code; the same numerators also
# appear in the ENGINE_A_REPLACEMENT_DVS inline comments (same file, e.g.
# "QB": 77.3,  # 12.91 / 16.7 — Engine A side unguarded, out of SR-13 scope)
# and in the SR-13 section of docs/strategies/2026-08-20-dg-SEASON-BUILD-SPEC.md.
# Restated here so the coupled identity is executable. If a new calibration
# audit moves these, it moves the DVS values on the same line (BOTH engines'
# comments), and this test forces the Engine B pair to move together.
_REPLACEMENT_PPG: dict[str, float] = {
    "QB": 12.91,
    "RB": 7.29,
    "WR": 8.79,
    "TE": 8.99,
}


@pytest.mark.parametrize("pos", _XVAR_POSITIONS)
def test_sr13_lambda_is_exact_p90_ratio(pos: str) -> None:
    """SR-13: XVAR_LAMBDA_ENGINE_B[pos] == round(P90[pos]/P90['WR'], 3).

    The lambdas are P90 ratios, not free parameters. The position P90 cancels
    in unclamped xVAR (pvo_assembler.py:407), so editing the lambda alone
    creates a cross-positional distortion — that is exactly what the RETRACTED
    "TE should be 0.703" edit would have done (an 8.4% TE distortion where
    none exists).
    """
    expected = round(ENGINE_B_P90_PPG[pos] / ENGINE_B_P90_PPG["WR"], 3)
    assert XVAR_LAMBDA_ENGINE_B[pos] == pytest.approx(expected, abs=0.001), (
        f"XVAR_LAMBDA_ENGINE_B[{pos!r}] = {XVAR_LAMBDA_ENGINE_B[pos]} but "
        f"P90[{pos!r}]/P90['WR'] = {expected}. The 'TE lambda should be 0.703' "
        "finding is RETRACTED (2026-08-20; SR-13/DG-092) — do NOT edit one "
        "constant alone. ENGINE_B_P90_PPG, XVAR_LAMBDA_ENGINE_B, and "
        "ENGINE_B_REPLACEMENT_DVS move together (new diagnostic + David "
        "approval) or not at all. See engine_b_contract.py's module docstring."
    )


@pytest.mark.parametrize("pos", _XVAR_POSITIONS)
def test_sr13_replacement_dvs_derives_from_replacement_ppg(pos: str) -> None:
    """SR-13: ENGINE_B_REPLACEMENT_DVS[pos] == round(repl_PPG/P90[pos]*100, 1).

    Same coupled system as the lambda test: replacement DVS is replacement PPG
    normalized by the SAME position P90 the lambda is built from. Moving the
    P90 without recomputing this (or vice versa) silently shifts every xVAR
    for the position.
    """
    expected = round(_REPLACEMENT_PPG[pos] / ENGINE_B_P90_PPG[pos] * 100, 1)
    assert ENGINE_B_REPLACEMENT_DVS[pos] == pytest.approx(expected, abs=0.05), (
        f"ENGINE_B_REPLACEMENT_DVS[{pos!r}] = {ENGINE_B_REPLACEMENT_DVS[pos]} "
        f"but replacement_PPG/P90*100 = {expected} "
        f"({_REPLACEMENT_PPG[pos]} / {ENGINE_B_P90_PPG[pos]} * 100). These "
        "constants are one coupled system with ENGINE_B_P90_PPG and "
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
