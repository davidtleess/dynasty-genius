"""DG-017 falsifier experiment — unit tests for the decomposition and tuning helpers.

Report-only lane: these tests cover the pure logic of the experiment script
(scripts/experiments/dg017_scaled_refit_falsifier.py), not the deployed artifacts.
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.experiments.dg017_scaled_refit_falsifier import (
    family_of,
    family_shares,
    standardized_weights,
    tune_alpha_honestly,
)


class TestStandardizedWeights:
    def test_weight_is_abs_coef_times_sd(self):
        weights = standardized_weights(
            coefs=np.array([2.0, -0.5, 0.0]),
            feature_names=["a", "b", "c"],
            sds=np.array([3.0, 4.0, 5.0]),
        )
        assert weights == {"a": 6.0, "b": 2.0, "c": 0.0}

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            standardized_weights(
                coefs=np.array([1.0]),
                feature_names=["a", "b"],
                sds=np.array([1.0, 1.0]),
            )


class TestFamilyGrouping:
    def test_ppg_prefix_is_ppg_family(self):
        assert family_of("ppg_t") == "ppg"
        assert family_of("ppg_t_minus_1") == "ppg"
        assert family_of("ppg_t_minus_2_available") == "ppg"

    def test_age_and_usage_families(self):
        assert family_of("age") == "age"
        assert family_of("aging_curve_value") == "age"
        assert family_of("games_t") == "volume"
        assert family_of("snap_share") == "usage"
        assert family_of("tprr") == "usage"
        assert family_of("epa_per_dropback") == "usage"

    def test_family_shares_sum_to_one_and_ppg_share_correct(self):
        weights = {
            "ppg_t": 3.0,
            "ppg_t_minus_1": 1.0,
            "age": 0.5,
            "snap_share": 0.5,
        }
        shares = family_shares(weights)
        assert sum(shares.values()) == pytest.approx(1.0)
        assert shares["ppg"] == pytest.approx(0.8)
        assert shares["age"] == pytest.approx(0.1)
        assert shares["usage"] == pytest.approx(0.1)

    def test_all_zero_weights_give_zero_shares(self):
        shares = family_shares({"ppg_t": 0.0, "age": 0.0})
        assert shares["ppg"] == 0.0
        assert shares["age"] == 0.0


class TestHonestAlphaTuning:
    def test_selection_never_pinned_at_final_grid_boundary(self):
        rng = np.random.default_rng(42)
        n, p = 240, 6
        X = rng.normal(size=(n, p))
        y = X @ np.array([1.0, -0.5, 0.25, 0.0, 0.0, 0.0]) + rng.normal(
            scale=0.5, size=n
        )
        # A deliberately bad starting grid: every candidate is enormous, so the
        # honest tuner must widen downward until the optimum is interior.
        model, final_grid, widenings = tune_alpha_honestly(
            X, y, base_grid=[1e4, 1e5, 1e6], cv=5
        )
        assert widenings >= 1
        assert min(final_grid) < 1e4
        assert model.alpha_ != min(final_grid)
        assert model.alpha_ != max(final_grid)

    def test_interior_selection_widens_nothing(self):
        rng = np.random.default_rng(7)
        n, p = 240, 4
        X = rng.normal(size=(n, p))
        y = X @ np.array([1.0, 0.5, -0.5, 0.2]) + rng.normal(scale=1.0, size=n)
        grid = list(np.logspace(-3, 4, 15))
        model, final_grid, widenings = tune_alpha_honestly(X, y, base_grid=grid, cv=5)
        if model.alpha_ not in (min(final_grid), max(final_grid)):
            assert widenings == 0 or len(final_grid) > len(grid)
        assert model.alpha_ in final_grid
