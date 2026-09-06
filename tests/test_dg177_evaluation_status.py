"""Codex review of 154635Z — a machine-readable per-horizon evaluation status.

"Supported" means the closed history was sufficient to evaluate; it never means validated.
An arm with zero evaluated policy folds says so in a field, not in prose. The bootstrap is
sampling uncertainty conditional on the fitted models. A better Brier score alone is not a
calibration proof, so the status carries reliability diagnostics computed from the graded
predictions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dynasty_genius.eval.evaluation_status import (
    BOOTSTRAP_MEANING,
    STATUS_EVALUATED,
    STATUS_NO_EVALUATED_FOLD,
    STATUS_UNSUPPORTED,
    calibration_diagnostics,
    evaluation_status,
)


def test_the_meaning_of_the_bootstrap_is_stated_once_and_correctly():
    assert "sampling uncertainty conditional on the fitted models" in BOOTSTRAP_MEANING
    assert "not model, selection or season uncertainty" in BOOTSTRAP_MEANING


def test_calibration_diagnostics_on_a_calibrated_and_a_miscalibrated_forecast():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.05, 0.95, 4000)
    y = (rng.uniform(size=4000) < p).astype(int)
    good = calibration_diagnostics(y, p)
    assert good["n"] == 4000 and good["ece"] < 0.03
    assert abs(good["reliability_slope"] - 1.0) < 0.15 and abs(good["reliability_intercept"]) < 0.15
    over = calibration_diagnostics(y, np.clip(p + 0.25, 0, 1))      # systematically too high
    assert over["ece"] > 0.15 and over["mean_predicted"] > over["observed_rate"] + 0.1
    assert over["reliability_intercept"] < -0.5


def test_calibration_diagnostics_refuse_a_degenerate_sample():
    out = calibration_diagnostics(np.array([1, 1, 1]), np.array([0.9, 0.8, 0.7]))
    assert out["status"] == "degenerate: one outcome class"
    assert np.isnan(out["reliability_slope"])


def _results():
    return {
        "historical": {
            "WR": {
                "year1": {"evidence": "policy", "evaluated_test_seasons": [2021, 2022, 2023], "folds": [
                    {"test_season": 2020, "forecast_season": 2021, "skipped_reason": "policy selection: no inner fold"},
                    {"test_season": 2021, "forecast_season": 2022, "skipped_reason": None},
                    {"test_season": 2022, "forecast_season": 2023, "skipped_reason": None},
                    {"test_season": 2023, "forecast_season": 2024, "skipped_reason": None},
                ], "pooled": {"policy": {"points_unconditional": {"delta_vs_baseline": {
                    "delta_r2": {"point": 0.03, "ci90": [0.013, 0.048]},
                    "delta_rmse": {"point": -2.1, "ci90": [-3.3, -0.9]}}}, "probability": {"brier": 0.119, "baseline_brier": 0.150}}}},
                "year2": {"evidence": "policy", "evaluated_test_seasons": [], "folds": [
                    {"test_season": 2022, "forecast_season": 2024, "skipped_reason": "policy selection: no inner fold"},
                    {"test_season": 2023, "forecast_season": 2025, "skipped_reason": "policy selection: no inner fold"},
                ], "pooled": {}},
                "year5": {"unsupported": True, "reason": "fewer than 6 closed seasons", "folds": []},
            }
        }
    }


def _predictions():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.2, 0.9, 300)
    return pd.DataFrame({
        "horizon": [1] * 300, "position": ["WR"] * 300, "forecast_season": rng.choice([2022, 2023, 2024], 300),
        "policy_p_appear_year1": p, "appeared_year1": (rng.uniform(size=300) < p).astype(int),
    })


def test_status_is_one_field_per_horizon_with_counts_and_diagnostics():
    out = evaluation_status(_results(), _predictions(), arm_key=None)
    wr = out["positions"]["WR"]
    assert wr["year1"]["status"] == STATUS_EVALUATED
    assert wr["year1"]["evaluated_folds"] == 3 and wr["year1"]["skipped_folds"] == 1
    assert wr["year1"]["forecast_seasons_graded"] == [2022, 2023, 2024]
    assert wr["year1"]["unconditional_points_delta_r2_vs_baseline"]["ci90"] == [0.013, 0.048]
    assert wr["year1"]["baseline_improvement"] == "within the reported 90% interval"
    assert wr["year1"]["calibration"]["n"] == 300 and "ece" in wr["year1"]["calibration"]
    assert wr["year2"]["status"] == STATUS_NO_EVALUATED_FOLD and wr["year2"]["evaluated_folds"] == 0
    assert wr["year2"]["baseline_improvement"] == "not graded: zero evaluated policy folds"
    assert wr["year5"]["status"] == STATUS_UNSUPPORTED
    assert out["meaning"]["supported"] == "closed history sufficient to evaluate; not validation"
    assert out["meaning"]["bootstrap"] == BOOTSTRAP_MEANING
    assert out["meaning"]["brier"].startswith("a better Brier score alone is not a calibration proof")


def test_an_inconclusive_interval_is_named_inconclusive():
    r = _results()
    r["historical"]["WR"]["year1"]["pooled"]["policy"]["points_unconditional"]["delta_vs_baseline"]["delta_r2"] = {"point": 0.015, "ci90": [-0.009, 0.041]}
    out = evaluation_status(r, _predictions(), arm_key=None)
    assert out["positions"]["WR"]["year1"]["baseline_improvement"] == "inconclusive: the 90% interval includes zero"
