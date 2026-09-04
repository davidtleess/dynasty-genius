"""DG-157 RED: the cross-positional value comes off the UNCAPPED score.

David's ruling, 2026-09-04 22:30:11Z (18:30 ET), verbatim and in full: "take decision one now.
then build before week 1". This is decision one.

The displayed score is clamped to 100, and the cross-positional value was then derived FROM the
clamped number. For a player above his position's ceiling that value is not his — it is the
ceiling's, so every clamped player at a position shares one identical figure (TE 2.85, RB 58.05,
WR 39.40, and 57.61 for the one clamped player on the other engine). Trey McBride and Colston
Loveland were both priced at 2.85 although the model separates them by 52% of a point per game.

Deriving it from the uncapped score restores exactly the identity the contract already
documents — ``(ppg − replacement_ppg) × 100 / P90[anchor]``, in which the position ceiling
cancels — and moves NO constant, so the DG-092 coupled-constant guard is untouched.

Pinned here:
  * no displayed score changes, on either engine;
  * a clamped player's cross-positional value becomes his own rather than his ceiling's;
  * an unclamped player's value does not move at all, because for him the raw and clamped
    scores are the same number;
  * the ceiling-bound disclosure still tells the truth about the DISPLAYED number, which is
    still clamped;
  * the coupled constants are untouched.

⚠ Recorded because the cards look identical: the cross-positional value is also a RANK, and on
the live artifact 103 of 502 players change place — the corrected ones plus 86 they leapfrog
whose own value does not move. That rank sorts cut advice. David was told before he ruled.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_P90_PPG,
    ENGINE_B_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_B,
)


def _uncapped_xvar(ppg: float, position: str) -> float:
    """The expected value, derived on the SAME basis the served pipeline uses.

    The uncapped score is rounded to one decimal before the multiplier, exactly as the
    displayed score has always been. That keeps clamped and unclamped players on one basis:
    an unclamped player's value has always come off a one-decimal score, and it would be a
    quiet inconsistency for the corrected players alone to be computed at full precision.
    """
    repl = ENGINE_B_REPLACEMENT_DVS[position]
    lam = XVAR_LAMBDA_ENGINE_B[position]
    uncapped = round(ppg / ENGINE_B_P90_PPG[position] * 100.0, 1)
    return round((uncapped - repl) * lam, 2)


# ── the Engine B scoring path ────────────────────────────────────────────────────────


def test_a_clamped_player_is_priced_at_his_own_number_not_his_ceilings(monkeypatch) -> None:
    """A tight end projecting 15.0 a game and one projecting 9.9 must not share a value."""
    from tests.contract import test_dg157_helpers as h

    high = h.assemble(position="TE", projection=15.035)
    low = h.assemble(position="TE", projection=9.908)

    assert high["dynasty_value_score"] == 100.0, "the DISPLAYED score is still clamped"
    assert low["dynasty_value_score"] == 100.0
    assert high["xvar"] != low["xvar"], "two clamped players must no longer share one value"
    assert high["xvar"] == pytest.approx(_uncapped_xvar(15.035, "TE"), abs=0.01)
    assert low["xvar"] == pytest.approx(_uncapped_xvar(9.908, "TE"), abs=0.01)


def test_an_unclamped_players_value_does_not_move(monkeypatch) -> None:
    """For a player under the ceiling the raw and clamped scores are the same number, so this
    change must be invisible to him."""
    from tests.contract import test_dg157_helpers as h

    row = h.assemble(position="TE", projection=8.0)

    assert row["dynasty_value_score"] < 100.0
    assert row["xvar"] == pytest.approx(_uncapped_xvar(8.0, "TE"), abs=0.01)


def test_the_displayed_score_is_still_clamped_and_still_says_so(monkeypatch) -> None:
    """The fix is to the cross-positional value only. The number on the card keeps its ceiling
    and keeps disclosing that it hit one."""
    from tests.contract import test_dg157_helpers as h

    row = h.assemble(position="TE", projection=15.035)

    assert row["dynasty_value_score"] == 100.0
    assert row["dvs_clamped"] is True
    assert row["xvar_ceiling_bound"] is True


def test_the_value_rises_monotonically_with_production_above_the_ceiling(monkeypatch) -> None:
    from tests.contract import test_dg157_helpers as h

    values = [h.assemble(position="RB", projection=p)["xvar"] for p in (16.0, 18.0, 20.0)]

    assert values == sorted(values)
    assert len(set(values)) == 3, "three different producers must get three different values"


# ── the coupled constants stay exactly where they are ────────────────────────────────


def test_no_constant_moves() -> None:
    """DG-092 guards these. This ticket must not touch them — the whole reason it is safe to
    land alone is that it changes a derivation, not a calibration."""
    assert ENGINE_B_P90_PPG == {"QB": 20.1, "RB": 15.7, "WR": 14.5, "TE": 9.4}
    assert ENGINE_B_REPLACEMENT_DVS == {"QB": 64.2, "RB": 46.4, "WR": 60.6, "TE": 95.6}
    assert XVAR_LAMBDA_ENGINE_B == {"QB": 1.386, "RB": 1.083, "WR": 1.000, "TE": 0.648}


def test_the_assembler_derives_the_value_from_the_uncapped_score() -> None:
    """Pin the wiring: the cross-positional line must not read the clamped score."""
    from pathlib import Path

    import src.dynasty_genius.pvo_assembler as assembler

    source = Path(assembler.__file__).read_text()
    xvar_line = [ln for ln in source.splitlines() if "xvar = round((" in ln]
    assert xvar_line, "the cross-positional computation moved; re-pin this test"
    assert "dynasty_value_score - _repl" not in xvar_line[0], (
        "the cross-positional value is still being derived from the CLAMPED score"
    )
