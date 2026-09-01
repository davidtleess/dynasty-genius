"""A player who stops playing is an OUTCOME, not a missing row.

Why this file exists: `apply_inference_partition` computes the 2-year forward outcome
and then keeps only rows where that outcome is non-null. A player-season whose player
posted no games in either t+1 or t+2 gets `avg_ppg_t1_t2 = NaN` from `_calc_avg` and is
dropped by the `keep` mask. Measured on the production table, that silently deletes 638
of 2,880 training-eligible player-seasons, and the deletion is 9.3x concentrated in the
lowest snap-share decile.

That is not missing data. When a player posts zero games in both outcome seasons we have
OBSERVED something, and it is the single most informative observation a dynasty model can
have: the career ended, or the role did. Dropping those rows teaches the model only from
players who kept playing, which is why it has almost no examples of the low-opportunity
population it is asked to rank, and why the age curve it learns is too flat (the label
rate falls from 85.4% at age <=23 to 77.4% at 28-30, so attrition removes older players
preferentially).

These tests pin the distinction the current code conflates:

  * "he did not play"      — observed. Keep the row, record it, train on it.
  * "we cannot know yet"   — the inference season, and only that. Outcome stays null.

NAMING, deliberately narrow: the column is `outcome_returned`, not `played`. The upstream
assembler already drops seasons under MIN_GAMES_THRESHOLD=4, so a missing outcome row means
"did not post a QUALIFYING season", which is not the same claim as "took zero snaps". Naming
it for what is actually observed keeps a later hazard model from being trained on an event
defined by this pipeline's own filter and mistaking that for football.

The productive-capacity value stays NaN in BOTH cases on purpose. Zero-filling would
assert we measured a productive capacity of zero, when what we measured was no
opportunity to display capacity at all. The availability fact belongs in its own column
so a hurdle model can estimate P(plays) separately from E[points | plays].
"""
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.features.feature_assembly import (
    OUTCOME_COLUMN,
    apply_inference_partition,
)

WINDOW = list(range(2018, 2026))  # the production window: 2018..2025


def _survivor_and_washout() -> pd.DataFrame:
    """Two players, one complete training season each (2018).

    SURVIVOR plays 2018, 2019 and 2020 — a complete outcome window — and again in 2025,
    the inference season, so the "unobserved" case is exercised rather than vacuous.
    WASHOUT plays 2018 only; he never appears again, which is exactly what attrition
    looks like in this table (the outcome rows simply do not exist to join to).
    """
    rows = [
        {"player_id": "SURVIVOR", "feature_season": s, "ppg_t": 12.0, "games_t": 17}
        for s in (2018, 2019, 2020, 2025)
    ]
    rows.append(
        {"player_id": "WASHOUT", "feature_season": 2018, "ppg_t": 4.0, "games_t": 6}
    )
    return pd.DataFrame(rows)


def test_a_player_who_never_returns_is_kept_not_deleted() -> None:
    """The 638 deleted rows. His 2018 season has a complete window and a known fate."""
    out = apply_inference_partition(_survivor_and_washout(), seasons_window=WINDOW)
    washout = out[(out["player_id"] == "WASHOUT") & (out["feature_season"] == 2018)]
    assert not washout.empty, (
        "a player-season whose player never played again must survive the partition: "
        "his outcome is OBSERVED (he did not play), not missing"
    )


def test_the_washout_is_excluded_from_the_production_regression() -> None:
    """Kept and labelled is not the same as trainable, and conflating them breaks fits.

    `training_eligible` is what every existing consumer selects on before reading
    OUTCOME_COLUMN straight into a Ridge fit (train_engine_b.py:212,294,351,371;
    backtest_harness._build_fold_data). A washout has no production outcome BY
    DEFINITION, so admitting him there feeds NaN targets into a points regression — which
    is a different bug from the one being fixed, not a fix for it.

    His row is retained and labelled so an AVAILABILITY model can use him. That is the
    hurdle split: P(plays) is estimated from everyone with a complete window,
    E[points | plays] only from those who played.
    """
    out = apply_inference_partition(_survivor_and_washout(), seasons_window=WINDOW)
    washout = out[(out["player_id"] == "WASHOUT") & (out["feature_season"] == 2018)]
    assert not bool(washout["training_eligible"].iloc[0]), (
        "a player with no observed production must not enter the production regression"
    )
    survivor = out[(out["player_id"] == "SURVIVOR") & (out["feature_season"] == 2018)]
    assert bool(survivor["training_eligible"].iloc[0]), (
        "a player WITH an observed outcome must still train the production model"
    )


def test_attrition_is_recorded_in_its_own_column() -> None:
    """P(plays) is a separate estimand from E[points | plays]; it needs its own label."""
    out = apply_inference_partition(_survivor_and_washout(), seasons_window=WINDOW)
    assert "outcome_returned" in out.columns, (
        "the partition must publish whether a qualifying outcome season was observed, "
        "so a hurdle model can estimate availability separately from production"
    )
    washout = out[(out["player_id"] == "WASHOUT") & (out["feature_season"] == 2018)]
    survivor = out[(out["player_id"] == "SURVIVOR") & (out["feature_season"] == 2018)]
    assert not bool(washout["outcome_returned"].iloc[0])
    assert bool(survivor["outcome_returned"].iloc[0])


def test_a_washout_never_gets_a_fabricated_zero_ppg() -> None:
    """Zero-filling would claim we measured a productive capacity we never observed."""
    out = apply_inference_partition(_survivor_and_washout(), seasons_window=WINDOW)
    washout = out[(out["player_id"] == "WASHOUT") & (out["feature_season"] == 2018)]
    assert pd.isna(washout[OUTCOME_COLUMN].iloc[0]), (
        "he had no opportunity to display capacity; the points column must stay null "
        "and the availability fact must live in outcome_returned instead"
    )


def test_the_inference_season_cannot_claim_a_player_failed_to_return() -> None:
    """`False` and `unknown` are different facts, and only one of them is trainable.

    The inference season has no future in the table to join against, which is the same
    SHAPE as attrition and the opposite MEANING. If it were recorded as "did not return",
    a hurdle model would learn that every currently-active player washed out.
    """
    out = apply_inference_partition(_survivor_and_washout(), seasons_window=WINDOW)
    inf = out[out["feature_season"] == 2025]
    assert not inf.empty, "fixture must contain an inference-season row to be meaningful"
    assert inf["outcome_returned"].isna().all(), (
        "the inference season's return is unobserved, not negative; it must be null "
        "so it is excluded from an availability model rather than counted as a failure"
    )


def test_the_attrition_label_survives_schema_conformance() -> None:
    """Recovering the rows is worthless if the fact that identifies them is stripped.

    `_conform_to_engine_b_schema` selects EXACTLY `ENGINE_B_OUTPUT_COLUMNS`, so a column
    the partition computes but the contract omits is silently dropped on the way to the
    training table. That is what happened on the first assembler run after the partition
    fix: 643 rows came back and every one of them arrived without `outcome_returned`, so
    nothing downstream could tell a washout from a survivor — which is the entire point.
    """
    from scripts.assemble_engine_b_dataset import ENGINE_B_OUTPUT_COLUMNS

    assert "outcome_returned" in ENGINE_B_OUTPUT_COLUMNS, (
        "the availability label must be part of the published schema; without it the "
        "recovered player-seasons are indistinguishable from survivors and no hurdle "
        "model can be estimated from them"
    )
