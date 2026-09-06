"""DG-177 runner — the pure helpers of scripts/experiments/dg177_veteran_candidate.py.

The script's I/O (read the CSV, the manifest, the warehouse; write the run) is glue;
what is tested here is that the arms are composed as the ticket says, that the served
feature lists come from the served pickles and nowhere else, that provenance names real
bytes, and that the report never hides a skipped fold or a losing arm.
"""
from __future__ import annotations

import hashlib
import json
import pickle

import pytest

from scripts.experiments.dg177_veteran_candidate import (
    ARM_DEPLOYED,
    ARM_DEPLOYED_OPP,
    ARM_PPG_ONLY,
    ARM_RECENT_3,
    ARM_RECENT_3_OPP,
    EXPLORATORY_ARMS,
    RECENT_PRODUCTION_FEATURES,
    build_arms,
    collect_provenance,
    render_report,
    served_feature_lists,
)
from src.dynasty_genius.eval.opportunity_features import (
    EXPLORATORY_XFP_FEATURES,
    RAW_OPPORTUNITY_FEATURES,
)


def test_recent_production_baseline_is_the_three_columns_dg162_named():
    assert RECENT_PRODUCTION_FEATURES == ["ppg_t", "games_t", "age"]


def test_served_feature_lists_come_from_the_manifest_pickles(tmp_path):
    run = tmp_path / "runs" / "r1"
    run.mkdir(parents=True)
    for pos, feats in {"QB": ["age", "ppg_t", "cpoe"], "RB": ["age", "ppg_t"]}.items():
        with open(run / f"{pos.lower()}_v2.pkl", "wb") as fh:
            pickle.dump({"features": feats, "version": f"engine_b_v2_{pos.lower()}"}, fh)
    manifest = tmp_path / "v2_manifest.json"
    manifest.write_text(json.dumps({
        "QB": "runs/r1/qb_v2.pkl", "RB": "runs/r1/rb_v2.pkl",
    }))
    served = served_feature_lists(manifest, root=tmp_path)
    assert served == {
        "QB": {"features": ["age", "ppg_t", "cpoe"], "version": "engine_b_v2_qb",
               "path": "runs/r1/qb_v2.pkl"},
        "RB": {"features": ["age", "ppg_t"], "version": "engine_b_v2_rb",
               "path": "runs/r1/rb_v2.pkl"},
    }


def test_arms_are_the_baselines_the_deployed_list_and_one_family():
    served = ["age", "ppg_t", "games_t", "snap_share", "aging_curve_value"]
    arms = build_arms(served)
    assert arms[ARM_PPG_ONLY] == ["ppg_t"]
    assert arms[ARM_RECENT_3] == ["ppg_t", "games_t", "age"]
    assert arms[ARM_DEPLOYED] == served
    assert arms[ARM_RECENT_3_OPP] == ["ppg_t", "games_t", "age", *RAW_OPPORTUNITY_FEATURES]
    assert arms[ARM_DEPLOYED_OPP] == [*served, *RAW_OPPORTUNITY_FEATURES]
    # the third-party expected-points columns only ever appear in arms named exploratory
    for name, feats in arms.items():
        if set(feats) & set(EXPLORATORY_XFP_FEATURES):
            assert name in EXPLORATORY_ARMS
    assert EXPLORATORY_ARMS and all(name in arms for name in EXPLORATORY_ARMS)


def test_the_served_list_is_not_mutated_by_arm_construction():
    served = ["age", "ppg_t"]
    build_arms(served)
    assert served == ["age", "ppg_t"]


def test_provenance_names_the_bytes(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"a,b\n1,2\n")
    prov = collect_provenance({"training_csv": f})
    entry = prov["files"]["training_csv"]
    assert entry["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert entry["bytes"] == 8
    assert entry["path"].endswith("data.csv")
    assert "modified_utc" in entry
    assert set(prov["versions"]) >= {"python", "scikit-learn", "pandas", "numpy"}


def test_provenance_refuses_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_provenance({"training_csv": tmp_path / "absent.csv"})


def test_report_shows_every_fold_including_skipped_and_every_arm_including_losers():
    results = {
        "config": {"rule": "labels_known_at_cutoff", "reference_arms": ["recent_production_3col"],
                   "arms": {"recent_production_3col": ["ppg_t"], "noise": ["x"]},
                   "test_seasons": [2020, 2021]},
        "positions": {
            "WR": {
                "k": 24,
                "evaluated_test_seasons": [2021],
                "folds": [
                    {"test_season": 2020, "train_seasons": [2018], "n_train": 40, "n_test": 40,
                     "n_train_players": 40, "n_test_players": 40,
                     "skipped_reason": "train rows 40 < minimum 60", "arms": {},
                     "deltas": {}},
                    {"test_season": 2021, "train_seasons": [2018, 2019], "n_train": 80,
                     "n_test": 40, "n_train_players": 40, "n_test_players": 40,
                     "skipped_reason": None,
                     "arms": {"recent_production_3col": {"n": 40, "rmse": 3.0, "mae": 2.0, "r2": 0.5,
                                                         "spearman": 0.7, "topk_overlap": 0.5, "k": 24},
                              "noise": {"n": 40, "rmse": 4.0, "mae": 3.0, "r2": 0.1,
                                        "spearman": 0.2, "topk_overlap": 0.2, "k": 24}},
                     "deltas": {"recent_production_3col": {"noise": {"delta_rmse": {"point": 1.0, "ci90": [0.5, 1.5]},
                                                       "delta_r2": {"point": -0.4, "ci90": [-0.6, -0.2]},
                                                       "delta_spearman": {"point": -0.5, "ci90": [-0.7, -0.3]},
                                                       "delta_topk_overlap": {"point": -0.3, "ci90": [-0.5, -0.1]},
                                                       "rows": 40, "clusters": 40, "draws": 10}}}},
                ],
                "pooled": {"recent_production_3col": {"n": 40, "rmse": 3.0, "mae": 2.0, "r2": 0.5,
                                                      "spearman": 0.7, "topk_overlap": 0.5, "k": 24},
                           "noise": {"n": 40, "rmse": 4.0, "mae": 3.0, "r2": 0.1,
                                     "spearman": 0.2, "topk_overlap": 0.2, "k": 24}},
                "deltas": {"recent_production_3col": {"noise": {"delta_rmse": {"point": 1.0, "ci90": [0.5, 1.5]},
                                                  "delta_r2": {"point": -0.4, "ci90": [-0.6, -0.2]},
                                                  "delta_spearman": {"point": -0.5, "ci90": [-0.7, -0.3]},
                                                  "delta_topk_overlap": {"point": -0.3, "ci90": [-0.5, -0.1]},
                                                  "rows": 40, "clusters": 40, "draws": 10}}},
            }
        },
    }
    md = render_report(results, provenance={"git_head": "abc1234", "files": {}, "versions": {}})
    assert "2020" in md and "skipped" in md and "train rows 40 < minimum 60" in md
    assert "noise" in md and "recent_production_3col" in md
    assert "abc1234" in md
    assert "+1.000" in md or "1.000" in md   # the losing delta is printed, not hidden
