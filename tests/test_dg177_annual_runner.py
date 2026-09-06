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
        features_by_arm={"recent_production_3col": {"WR": FEATURES}}, population="2025 feature rows",
        candidate_arm="recent_production_3col", candidate_rationale="why",
        comparator_export="annual_forecasts_served_features.csv",
    )
    assert m["candidate_arm"] == "recent_production_3col" and m["candidate_rationale"] == "why"
    assert m["exports"] == {"candidate": "annual_forecasts.csv",
                            "comparator": "annual_forecasts_served_features.csv"}
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


# ── round 2, item 1: the manifest's shape is asserted, not assumed ──

from scripts.experiments.dg177_annual_forecasts import (  # noqa: E402
    ManifestShapeError,
    validate_manifest,
)


def _good_manifest():
    return build_manifest(
        horizons=(1, 2), inference_season=2025, last_complete_season=2024, scope="REG",
        source={"weekly_stats_sha256": "a" * 64, "nflreadpy": "0.1.5"}, git_head="deadbeef",
        features_by_arm={"served_features": {"WR": ["age", "ppg_t"]}, "recent_production_3col": {"WR": FEATURES}},
        population="2025 feature rows",
        candidate_arm="recent_production_3col", candidate_rationale="why",
        comparator_export="annual_forecasts_served_features.csv",
        inputs={"training_csv_sha256": "b" * 64, "served_wr_pickle_sha256": "c" * 64},
        outputs={"annual_forecasts.csv": "d" * 64},
    )


def test_manifest_keeps_arms_and_positions_at_their_own_levels():
    m = _good_manifest()
    assert m["features_by_position"] == {"WR": FEATURES}                        # the candidate's, by POSITION
    assert m["features_by_arm"]["served_features"]["WR"] == ["age", "ppg_t"]   # every arm, by arm then position
    assert m["inputs"]["training_csv_sha256"] == "b" * 64 and m["outputs"]["annual_forecasts.csv"] == "d" * 64
    validate_manifest(m)   # no raise


def test_manifest_with_arm_names_at_the_position_level_is_refused():
    m = _good_manifest()
    m["features_by_position"] = m["features_by_arm"]        # the round-1 defect, reproduced
    with pytest.raises(ManifestShapeError, match="position"):
        validate_manifest(m)


def test_manifest_with_a_non_feature_leaf_or_unknown_arm_is_refused():
    m = _good_manifest()
    m["features_by_arm"]["served_features"]["WR"] = ["QB", "RB"]
    with pytest.raises(ManifestShapeError, match="feature"):
        validate_manifest(m)
    m = _good_manifest()
    m["features_by_arm"]["mystery_arm"] = {"WR": FEATURES}
    with pytest.raises(ManifestShapeError, match="arm"):
        validate_manifest(m)


def test_manifest_without_input_or_output_hashes_is_refused():
    m = _good_manifest()
    m["inputs"] = {}
    with pytest.raises(ManifestShapeError, match="input"):
        validate_manifest(m)
    m = _good_manifest()
    del m["outputs"]["annual_forecasts.csv"]
    with pytest.raises(ManifestShapeError, match="output"):
        validate_manifest(m)


# ── round 2, item 4: the exported candidate is the policy, and the manifest says so ──

from src.dynasty_genius.eval.annual_forecasts import (  # noqa: E402
    POLICY_SPACE,
    fit_policy,
)


def test_final_forecasts_can_use_the_policy_and_record_the_choice():
    df = _with_inference_rows(_panel(last_complete=2024))
    forecasts, fits = final_forecasts(
        df, {"WR": FEATURES}, horizons=(1,), inference_season=2025, last_complete_season=2024,
        fitter=fit_policy,
    )
    assert len(forecasts) == int((df.feature_season == 2025).sum())
    chosen = fits["WR"]["year1"]["policy_by_quantity"]
    assert set(chosen) == {"p_appear", "points_given_appear", "games_given_appear"}
    assert all(v in POLICY_SPACE for v in chosen.values())
    assert fits["WR"]["year1"]["final_fit_parity"] == "fit_policy is the function final scoring calls"


def test_manifest_carries_the_selection_policy_and_the_names_the_consumer_reads():
    m = build_manifest(
        horizons=(1,), inference_season=2025, last_complete_season=2024, scope="REG",
        source={"weekly_stats_sha256": "a" * 64}, git_head="deadbeef",
        features_by_arm={"recent_production_3col": {"WR": FEATURES}}, population="p",
        candidate_arm="recent_production_3col", candidate_rationale="why",
        comparator_export="annual_forecasts_served_features.csv",
        inputs={"training_csv_sha256": "b" * 64}, outputs={"annual_forecasts.csv": "d" * 64},
        selection_policy={"space": list(POLICY_SPACE), "chosen": {"WR": {"year1": {"p_appear": "candidate"}}}},
    )
    assert m["selection_policy"]["space"] == list(POLICY_SPACE)
    assert m["selection_policy"]["chosen"]["WR"]["year1"]["p_appear"] == "candidate"
    assert m["scoring_arm"] == "recent_production_3col"                 # alias the consumer reads
    assert m["outputs_sha256"] == m["outputs"]                          # alias the consumer reads
    validate_manifest(m)


def test_validate_manifest_accepts_a_declared_arm_set_and_refuses_one_outside_it():
    m = _good_manifest()
    m["features_by_arm"] = {"basic_cohort_3col_plus_lags": {"WR": FEATURES}}
    m["features_by_position"] = {"WR": FEATURES}
    m["candidate_arm"] = "basic_cohort_3col_plus_lags"
    with pytest.raises(ManifestShapeError, match="arm"):
        validate_manifest(m)                                             # not among the annual arms
    validate_manifest(m, known_arms={"basic_cohort_3col_plus_lags"})    # declared by its runner


def test_validate_manifest_lets_the_runner_declare_its_required_inputs():
    m = _good_manifest()
    m["inputs"] = {"weekly_stats_sha256": "e" * 64, "players_sha256": "f" * 64}
    with pytest.raises(ManifestShapeError, match="training_csv_sha256"):
        validate_manifest(m)
    validate_manifest(m, required_inputs=("weekly_stats_sha256", "players_sha256"))


def test_manifest_states_what_the_bootstrap_means_and_carries_an_evaluation_status_slot():
    from src.dynasty_genius.eval.evaluation_status import (
        BOOTSTRAP_MEANING,
        SUPPORTED_MEANING,
    )

    m = _good_manifest()
    assert m["intervals"] == "none exported; " + BOOTSTRAP_MEANING
    assert m["meaning"]["supported"] == SUPPORTED_MEANING
    assert m["evaluation_status"] == {}                      # filled by the runner from graded results


# ── Codex review of 155259Z: outputs must be real files, and the candidate export is whatever exports names ──

def test_validate_manifest_requires_the_named_candidate_export_not_a_fixed_filename(tmp_path):
    m = _good_manifest()
    m["exports"] = {"candidate": "basic_forecasts.csv", "comparator": "none"}
    m["outputs"] = {"basic_forecasts.csv": "d" * 64}
    validate_manifest(m)                                    # the named candidate export carries a hash
    m["outputs"] = {"annual_forecasts.csv": "d" * 64}       # a hash for a file the manifest does not export
    with pytest.raises(ManifestShapeError, match="basic_forecasts.csv"):
        validate_manifest(m)


def test_validate_manifest_with_a_run_dir_refuses_a_missing_file_or_a_wrong_hash(tmp_path):
    import hashlib
    payload = b"player_id,p_appear_year1\nA,0.5\n"
    (tmp_path / "annual_forecasts.csv").write_bytes(payload)
    m = _good_manifest()

    def set_outputs(values):
        m["outputs"] = values
        m["outputs_sha256"] = dict(values)          # builders write both; the validator holds them equal

    set_outputs({"annual_forecasts.csv": hashlib.sha256(payload).hexdigest()})
    validate_manifest(m, run_dir=tmp_path)                  # exists, hash matches
    set_outputs({"annual_forecasts.csv": "0" * 64})
    with pytest.raises(ManifestShapeError, match="hash"):
        validate_manifest(m, run_dir=tmp_path)
    set_outputs({"annual_forecasts.csv": hashlib.sha256(payload).hexdigest(), "ghost.csv": "1" * 64})
    with pytest.raises(ManifestShapeError, match="ghost.csv"):
        validate_manifest(m, run_dir=tmp_path)              # a fictitious entry is refused by name
    m["outputs_sha256"] = {"annual_forecasts.csv": "2" * 64}
    set_outputs({"annual_forecasts.csv": hashlib.sha256(payload).hexdigest()})
    m["outputs_sha256"] = {"annual_forecasts.csv": "2" * 64}
    with pytest.raises(ManifestShapeError, match="outputs_sha256"):
        validate_manifest(m, run_dir=tmp_path)              # the alias must not drift from outputs
