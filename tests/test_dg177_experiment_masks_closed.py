"""Round 2, item 2 — the three remaining experiment harnesses use the shared closure rule.

Each keeps its skip semantics; each now refuses to learn from a label that was not known
at its test year. The proof in every case is the same: rewrite the labels of rows whose
window was still open at the forecast, and the fold must not move; rewrite rows the
closure admits, and it must.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dynasty_genius.eval import te_archetype_bakeoff as archetype
from src.dynasty_genius.eval import te_role_risk_experiment as role_risk
from src.dynasty_genius.models.engine_b_contract import OUTCOME_COLUMN
from src.dynasty_genius.models.label_closure import LABEL_WINDOW_SEASONS


def _te_frame(seasons=range(2018, 2024), n=12, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        for i in range(n):
            ppg = 4 + rng.normal(0, 2)
            rows.append({
                "player_id": f"te{i:02d}", "feature_season": s, "training_eligible": True, "position": "TE",
                "ppg_t": ppg, "games_t": 12, "age": 25 + i % 6, "route_participation": 0.6, "target_share_nfl": 0.12,
                "yprr": 1.4, "tprr": 0.18, "weighted_opportunity": 0.3, "snap_share": 0.6,
                OUTCOME_COLUMN: 0.8 * ppg + rng.normal(0, 1),
                "te_role_role_risk": i % 2, "te_role_blocking_specialist": 0,
                "archetype_a": float(i % 3 == 0), "archetype_b": float(i % 3 == 1),
            })
    return pd.DataFrame(rows)


class TestTeRoleRisk:
    def test_train_labels_are_closed_at_the_test_year(self):
        frame = _te_frame()
        fold = role_risk._evaluate_fold(frame, 2021, ["ppg_t", "games_t", "age"], ["te_role_role_risk"], 1.0)
        # closure: feature_season + 2 <= 2021 -> {2018, 2019} -> 24 rows, not 36
        assert fold["n_train"] == 2 * 12
        assert fold["n_test"] == 12

    def test_an_open_label_cannot_move_the_fold_but_a_closed_one_can(self):
        frame = _te_frame()
        base = role_risk._evaluate_fold(frame, 2021, ["ppg_t", "games_t", "age"], ["te_role_role_risk"], 1.0)
        open_rows = frame.copy()
        open_rows.loc[open_rows["feature_season"] == 2020, OUTCOME_COLUMN] += 100.0
        moved = role_risk._evaluate_fold(open_rows, 2021, ["ppg_t", "games_t", "age"], ["te_role_role_risk"], 1.0)
        assert moved["baseline_rmse"] == base["baseline_rmse"] and moved["candidate_rmse"] == base["candidate_rmse"]
        closed_rows = frame.copy()
        closed_rows.loc[closed_rows["feature_season"] == 2019, OUTCOME_COLUMN] += 100.0
        moved = role_risk._evaluate_fold(closed_rows, 2021, ["ppg_t", "games_t", "age"], ["te_role_role_risk"], 1.0)
        assert moved["baseline_rmse"] != base["baseline_rmse"]


class TestTeArchetypeBakeoff:
    def test_train_labels_are_closed_at_the_test_year(self):
        frame = _te_frame()
        out = archetype._evaluate_columns(frame, ["ppg_t", "games_t", "age", "archetype_a"], 2021)
        assert out["n_train"] == 2 * 12 and out["n_test"] == 12

    def test_an_open_label_cannot_move_the_fold_but_a_closed_one_can(self):
        frame = _te_frame()
        cols = ["ppg_t", "games_t", "age", "archetype_a"]
        base = archetype._evaluate_columns(frame, cols, 2021)
        open_rows = frame.copy()
        open_rows.loc[open_rows["feature_season"] == 2020, OUTCOME_COLUMN] += 100.0
        assert archetype._evaluate_columns(open_rows, cols, 2021)["rmse"] == base["rmse"]
        closed_rows = frame.copy()
        closed_rows.loc[closed_rows["feature_season"] == 2019, OUTCOME_COLUMN] += 100.0
        assert archetype._evaluate_columns(closed_rows, cols, 2021)["rmse"] != base["rmse"]


class TestQbV3WalkForward:
    """H1's label spans one season, so 'feature_season < test_year' already was closure;
    H2 and H3 were not. The fold builder now closes at the horizon it is given."""

    @staticmethod
    def _inputs(seasons=range(2016, 2023), n=10, seed=1):
        from src.dynasty_genius.features.qb_v3_candidate_matrix import (
            ENGINE_B_FEATURES_QB_V3_CANDIDATE,  # noqa: F401
        )
        from tests.contract.test_build4_qb_v3_walk_forward_t3 import (
            _candidate_frame,
            _eligibility_mask,
            _labels_for,
        )
        candidates = _candidate_frame(seasons=tuple(seasons))
        labels = _labels_for(candidates, horizons=(1, 2, 3))
        return candidates, labels, _eligibility_mask(candidates)

    def test_h1_keeps_its_split_and_h2_h3_close_at_their_horizon(self):
        import src.dynasty_genius.eval.qb_v3_walk_forward as wf
        from src.dynasty_genius.features.qb_v3_candidate_matrix import (
            ENGINE_B_FEATURES_QB_V3_CANDIDATE,
        )

        candidates, labels, mask = self._inputs()
        feats = list(ENGINE_B_FEATURES_QB_V3_CANDIDATE)
        seen = {}
        for horizon in (1, 2, 3):
            fold = wf.build_qb_v3_classification_fold_data(
                candidate_matrix=candidates, labels=labels, eligibility_mask=mask,
                feature_cols=feats, test_year=2021, horizon=horizon,
            )
            seen[horizon] = sorted(set(fold.train_metadata["feature_season"]))
        assert seen[1] == [2016, 2017, 2018, 2019, 2020]      # t + 1 <= 2021: the old split, unchanged
        assert seen[2] == [2016, 2017, 2018, 2019]            # t + 2 <= 2021
        assert seen[3] == [2016, 2017, 2018]                  # t + 3 <= 2021

    def test_an_open_h2_label_cannot_move_the_fold(self):
        import src.dynasty_genius.eval.qb_v3_walk_forward as wf
        from src.dynasty_genius.features.qb_v3_candidate_matrix import (
            ENGINE_B_FEATURES_QB_V3_CANDIDATE,
        )

        candidates, labels, mask = self._inputs()
        feats = list(ENGINE_B_FEATURES_QB_V3_CANDIDATE)
        build = lambda lab: wf.build_qb_v3_classification_fold_data(  # noqa: E731
            candidate_matrix=candidates, labels=lab, eligibility_mask=mask,
            feature_cols=feats, test_year=2021, horizon=2,
        )
        base = build(labels)
        flipped = labels.copy()
        open_rows = (flipped["horizon"] == 2) & (flipped["feature_season"] == 2020)
        flipped.loc[open_rows, "startable_role_occupancy"] = ~flipped.loc[open_rows, "startable_role_occupancy"].astype(bool)
        moved = build(flipped)
        pd.testing.assert_series_equal(moved.train_labels, base.train_labels)
        assert 2020 not in set(moved.train_metadata["feature_season"])


def test_window_constant_is_the_shared_one():
    assert LABEL_WINDOW_SEASONS == 2
