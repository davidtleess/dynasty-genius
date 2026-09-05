"""DG-159 — the three derivations, tested as arithmetic on their own.

``models/dvs_scale.py`` is the single place that turns a denominator into every other
scale constant: the cross-positional multiplier, the replacement baseline and the band
half-width. It has no state and no constants of its own, and that is what these tests
pin. Which constants come OUT of it for the shipped anchor is
``tests/contract/test_dg159_one_scale.py``; this file is about the functions.

The separation matters. Before the switch these same functions had to reproduce all
eight lambdas, all eight replacement baselines and the band sigmas from the ceilings
then in the code — that reproduction was the evidence that moving to one denominator
was a change of ONE input rather than a rewrite of thirty constants. It reproduced
seven of the eight families exactly. The one it could not reproduce was the replacement
points per game themselves, which turned out to exist only in inline comments citing an
artifact that does not contain them; they are now a derived, dated constant
(``REPLACEMENT_PPG``). That is the finding the reproduction pass was for, and the
reproduction is retired now that the constants it compared against are gone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dynasty_genius.models.dvs_scale import (
    derive_lambda,
    derive_replacement_dvs,
    derive_sigma,
)

POSITIONS = ("QB", "RB", "WR", "TE")


# ── the property the whole change rests on ──────────────────────────────────
@pytest.mark.parametrize("denominator", [9.4, 14.5, 16.7, 20.1, 20.3, 25.0])
def test_one_shared_denominator_makes_every_multiplier_exactly_one(denominator: float) -> None:
    """Under a single denominator the multiplier is 1.000 at every position on both
    engines, whatever the denominator is. A property of the derivation, not of the value
    David chose — which is why the switch could be reasoned about before he chose it."""
    assert derive_lambda(denominator, denominator) == 1.000


def test_the_multiplier_is_the_ratio_of_the_two_scales():
    """What it is for: converting a score expressed against one denominator into one
    expressed against another, so points above replacement can be compared across
    positions. Under four denominators that ratio was the work; under one it is 1."""
    assert derive_lambda(9.4, 14.5) == 0.648
    assert derive_lambda(20.1, 14.5) == 1.386


def test_replacement_is_the_points_a_game_expressed_on_the_scale():
    assert derive_replacement_dvs(8.41, 20.1) == 41.8
    assert derive_replacement_dvs(12.26, 20.1) == 61.0


def test_the_band_is_the_error_expressed_on_the_same_scale():
    """Sigma is stored in score points while the error it stands for is a fact in points
    per game — the member of the family most easily left behind when the scale moves."""
    assert derive_sigma(2.2223, 20.1) == 11.1
    assert derive_sigma(2.2223, 9.4) == 23.6


# ── a denominator that cannot be one refuses rather than returning a number ──
@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_a_non_positive_denominator_is_refused_by_every_derivation(bad: float) -> None:
    """Dividing by it would produce an infinity or a sign flip that reads as a score."""
    with pytest.raises(ValueError):
        derive_lambda(9.4, bad)
    with pytest.raises(ValueError):
        derive_replacement_dvs(8.41, bad)
    with pytest.raises(ValueError):
        derive_sigma(2.2223, bad)


# ── the module stays arithmetic ─────────────────────────────────────────────
def test_the_module_holds_no_denominator_of_its_own() -> None:
    """The value is a governed constant with a docstring explaining David's ruling
    (DVS_SCALE_ANCHOR_PPG in engine_b_contract.py). A second copy here would be a place
    for the two to drift apart silently, which is the whole failure this ticket exists
    to end.

    Read from the module's namespace rather than grepped from its text: prose is allowed
    to say which value shipped and why, and a test that cannot tell a sentence from a
    constant would either forbid the explanation or miss a constant spelled `20.10`.
    """
    import src.dynasty_genius.models.dvs_scale as scale

    documented_precisions = {"_LAMBDA_DECIMALS", "_SCORE_DECIMALS"}
    numeric = {
        name: value
        for name, value in vars(scale).items()
        if not name.startswith("__")
        and name not in documented_precisions
        and isinstance(value, (int, float, dict, list, tuple))
    }
    assert numeric == {}, (
        f"the scale module holds numbers of its own ({sorted(numeric)}); it derives from a "
        "denominator passed in, and the denominator itself lives in engine_b_contract.py"
    )
