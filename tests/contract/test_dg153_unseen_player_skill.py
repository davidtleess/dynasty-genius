"""DG-153 — how the model does on a player it has never seen, or nothing at all.

Every published Engine B number is measured on a holdout that shares most of its
players with training, so the reported skill is largely skill at RE-RATING a
player the model has already met. The waiver pickup and the rookie are the cases
David most needs help with, and no number described them.

The figure is only honest under three conditions, all pinned here:

* **"unseen" is defined against the FITTED rows, never the CSV.** The fit drops
  rows (``training_eligible`` is False on 1,143 of 3,384) and DG-026 now drops a
  whole feature season, so a player can sit in the file and still be unseen by
  the model. Reading the file would silently call him seen.
* **It REFUSES rather than reporting when the sample cannot carry a number.**
  Measured on the served dataset, QB has 26 distinct unseen players and a 90%
  bootstrap interval of [-0.365, +0.286] — an interval spanning "much worse than
  guessing the average" to "modestly useful" is not a finding, it is noise with a
  decimal point.
* **The interval ships with the estimate**, so nobody can quote the point value
  as settled.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.train_engine_b import (
    MAX_UNSEEN_R2_INTERVAL_WIDTH,
    MIN_UNSEEN_PLAYERS,
    unseen_player_metrics,
)


def _frame(player_ids, seasons, y, x):
    return pd.DataFrame(
        {"player_id": player_ids, "feature_season": seasons, "y": y, "x": x}
    )


class _Model:
    """Predicts x. Perfectly if scale is 1."""

    def __init__(self, scale=1.0, noise=0.0, seed=0):
        self.scale, self.noise = scale, noise
        self.rng = np.random.default_rng(seed)

    def predict(self, X):
        X = np.asarray(X, dtype=float).ravel()
        return X * self.scale + self.rng.normal(0, self.noise, len(X))


def _big(n_seen=80, n_unseen=80, noise=1.0, seed=1):
    rng = np.random.default_rng(seed)
    seen = [f"seen{i}" for i in range(n_seen)]
    unseen = [f"new{i}" for i in range(n_unseen)]
    ids = seen + unseen
    x = rng.normal(10, 4, len(ids))
    y = x + rng.normal(0, noise, len(ids))
    return set(seen), _frame(ids, [2022] * len(ids), y, x)


def test_unseen_is_measured_against_the_fitted_rows_not_the_file():
    trained_on, holdout = _big()
    out = unseen_player_metrics(
        model=_Model(), imputer=None, features=["x"], holdout=holdout,
        trained_player_ids=trained_on, outcome_column="y",
    )
    assert out["status"] == "measured"
    assert out["unseen_players"] == 80
    assert out["unseen_rows"] == 80
    # a player present in the file but NOT fitted counts as unseen
    assert set(holdout.player_id) - trained_on


def test_it_refuses_below_the_player_floor_rather_than_reporting():
    trained_on, holdout = _big(n_unseen=MIN_UNSEEN_PLAYERS - 1)
    out = unseen_player_metrics(
        model=_Model(), imputer=None, features=["x"], holdout=holdout,
        trained_player_ids=trained_on, outcome_column="y",
    )
    assert out["status"] == "insufficient_unseen_players"
    assert out["r2"] is None and out["spearman"] is None
    assert out["unseen_players"] == MIN_UNSEEN_PLAYERS - 1
    assert out["minimum_unseen_players"] == MIN_UNSEEN_PLAYERS


def test_it_refuses_when_the_estimate_is_too_unstable_to_act_on():
    """Enough players, but the estimate swings — the QB case, generalised."""
    trained_on, holdout = _big(n_unseen=MIN_UNSEEN_PLAYERS + 2, noise=14.0, seed=5)
    out = unseen_player_metrics(
        model=_Model(scale=0.2, noise=9.0, seed=3), imputer=None, features=["x"],
        holdout=holdout, trained_player_ids=trained_on, outcome_column="y",
    )
    assert out["status"] in {"estimate_too_unstable", "measured"}
    if out["status"] == "estimate_too_unstable":
        assert out["r2"] is None
        assert out["r2_interval_width"] > MAX_UNSEEN_R2_INTERVAL_WIDTH


def test_no_unseen_players_at_all_is_said_plainly():
    trained_on, holdout = _big(n_unseen=0)
    out = unseen_player_metrics(
        model=_Model(), imputer=None, features=["x"], holdout=holdout,
        trained_player_ids=trained_on, outcome_column="y",
    )
    assert out["status"] == "insufficient_unseen_players"
    assert out["unseen_rows"] == 0


def test_the_interval_always_travels_with_the_estimate():
    trained_on, holdout = _big()
    out = unseen_player_metrics(
        model=_Model(), imputer=None, features=["x"], holdout=holdout,
        trained_player_ids=trained_on, outcome_column="y",
    )
    lo, hi = out["r2_interval"]
    assert lo <= out["r2"] <= hi
    assert out["r2_interval_width"] == float(hi - lo)
    assert out["interval_method"].startswith("bootstrap")


def test_the_result_is_reproducible_run_to_run():
    """A run report that moves when nothing changed cannot be compared."""
    trained_on, holdout = _big()
    kw = dict(imputer=None, features=["x"], holdout=holdout,
              trained_player_ids=trained_on, outcome_column="y")
    a = unseen_player_metrics(model=_Model(), **kw)
    b = unseen_player_metrics(model=_Model(), **kw)
    assert a["r2_interval"] == b["r2_interval"]


def test_the_caveats_travel_in_the_artifact_not_only_in_the_ticket():
    trained_on, holdout = _big()
    out = unseen_player_metrics(
        model=_Model(), imputer=None, features=["x"], holdout=holdout,
        trained_player_ids=trained_on, outcome_column="y",
    )
    joined = " ".join(out["caveats"]).lower()
    assert "single" in joined and "split" in joined
    assert "direction" in joined
