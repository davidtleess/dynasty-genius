"""DG-177 annual runner — the pure helpers of scripts/experiments/dg177_annual_forecasts.py."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.dg177_annual_forecasts import (
    FORECAST_CUTOFF_RULE,
    build_manifest,
    final_forecasts,
)
from src.dynasty_genius.eval.annual_forecasts import QUANTITIES
from tests.test_dg177_annual_forecasts import FEATURES, _panel


def _with_inference_rows(df, inference_season=2025):
    """Add an inference partition: feature rows for the current season, both horizons censored."""
    rng = np.random.default_rng(9)
    extra = df[df.feature_season == 2023].copy()
    extra["feature_season"] = inference_season
    extra["ppg_t"] = extra["ppg_t"] + rng.normal(0, 1, len(extra))
    for j in (1, 2):
        extra[f"season_year{j}"] = inference_season + j
        extra[f"censored_year{j}"] = True
        extra[f"appeared_year{j}"] = pd.NA
        extra[f"games_year{j}"] = np.nan
        extra[f"points_year{j}"] = np.nan
    out = pd.concat([df, extra], ignore_index=True)
    for j in (1, 2):
        out[f"appeared_year{j}"] = out[f"appeared_year{j}"].astype("boolean")
    return out


def test_final_forecasts_score_the_inference_rows_from_closed_labels_only():
    df = _with_inference_rows(_panel(last_complete=2024))
    forecasts, fits = final_forecasts(
        df, {"WR": FEATURES}, horizons=(1, 2), inference_season=2025, last_complete_season=2024,
    )
    assert set(forecasts["feature_season"]) == {2025}
    assert len(forecasts) == int((df.feature_season == 2025).sum())
    for j in (1, 2):
        for q in QUANTITIES(j):
            assert q in forecasts.columns and np.isfinite(forecasts[q]).all()
        assert (forecasts[f"forecast_season_year{j}"] == 2025 + j).all()
        fit = fits["WR"][f"year{j}"]
        # a year-j label is closed only when feature_season + j <= last complete season
        assert max(fit["train_seasons"]) + j <= 2024
        assert fit["n_train_observed"] > 0
    assert set(forecasts["identity_status"]) == {"resolved"}


def test_final_forecasts_refuse_to_train_on_an_open_label():
    df = _with_inference_rows(_panel(last_complete=2024))
    # claim 2025 is complete while the frame says 2025 labels are censored: must not silently train
    with pytest.raises(ValueError):
        final_forecasts(df, {"WR": FEATURES}, horizons=(2,), inference_season=2025, last_complete_season=2025)


def test_manifest_types_every_term_the_contract_names():
    m = build_manifest(
        horizons=(1, 2), inference_season=2025, last_complete_season=2024, scope="REG",
        source={"weekly_stats_sha256": "abc", "nflreadpy": "0.1.5"}, git_head="deadbeef",
        features_by_position={"WR": FEATURES}, population="2025 feature rows",
    )
    assert m["forecast_cutoff"] == {"rule": FORECAST_CUTOFF_RULE, "feature_season": 2025,
                                    "information_through": "end of the 2025 NFL season including postseason"}
    assert m["label_window"] == {"year1": 1, "year2": 2}
    assert m["scoring_scope"] == {"scope": "REG", "scoring": "fantasy_points_ppr",
                                  "season_types": ["REG"]}
    assert m["exposure_definition"].startswith("games:")
    assert m["event"].startswith("appeared:")
    assert m["quantities"] == {"year1": QUANTITIES(1), "year2": QUANTITIES(2)}
    assert m["source"]["weekly_stats_sha256"] == "abc" and m["git_head"] == "deadbeef"
    assert m["horizons_supported"] == [1, 2] and m["longer_horizons"] == "unsupported: not measured"
    assert m["no_forecast_reason_for_absent_players"] == "no_feature_row"
