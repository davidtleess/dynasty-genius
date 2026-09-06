"""DG-173 — a third-party PROJECTION or RANKING is a market price.

David's ruling 2026-09-06, typed: "projection and price are very similar its a main
variable in price. you have to replace those points and or value."

The three contracts ban market columns BY EXACT NAME. Nothing in any of them names a
projection or a consensus ranking, so `sleeper_projection` passes today. This bans the
CLASS.

⛔ THE TRAP THIS TEST IS BUILT AGAINST. On 2026-09-05 a double-count check perturbed keys
that existed in ZERO of 168 cells and passed on the very defect it was named for. A ban on
columns nobody has yet is exactly that shape. So every prohibited name below is a column
that does NOT exist in the repo today, and the test is only meaningful because it was
watched going RED before the implementation landed.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_ALLOWED_FEATURES,
    is_market_derived_column,
    validate_no_prohibited_features,
)

# Plausible columns a future lane could add in good faith. NONE exist in the repo today.
PROJECTION_OR_RANKING = [
    "sleeper_projection", "espn_projection", "yahoo_projection",
    "fantasypros_ecr", "ecr", "consensus_rank", "expert_rank", "expert_consensus",
    "rotowire_projected_points", "numberfire_projection", "projected_points",
    "underdog_adp", "draftkings_salary_rank", "boris_chen_tier", "positional_tier",
    "ktc_superflex_value", "trade_value", "auction_value", "market_value",
    "dynastyprocess_value", "startup_adp", "rookie_adp", "ranking", "overall_ranking",
]

# Real columns that MUST keep passing. A ban that also blocks these is worse than no ban.
LEGITIMATE = sorted(ENGINE_B_ALLOWED_FEATURES) + [
    "aging_curve_value",          # ours: the fitted curve, the one real substring collision
    "ngs_avg_separation", "ngs_rush_yards_over_expected_per_att",
    "weighted_opportunity", "snap_share", "epa_per_dropback", "cpoe", "dakota",
    "player_id", "sleeper_player_id",   # identity, not a price
    "games_t", "ppg_t", "age", "team", "position",
]


@pytest.mark.parametrize("column", PROJECTION_OR_RANKING)
def test_projection_or_ranking_is_recognised_as_a_market_price(column: str) -> None:
    assert is_market_derived_column(column), (
        f"{column!r} is a third-party projection or ranking and must be treated as a "
        "market price (David's ruling 2026-09-06). It is not banned today."
    )


@pytest.mark.parametrize("column", LEGITIMATE)
def test_our_own_columns_are_not_swept_up(column: str) -> None:
    assert not is_market_derived_column(column), (
        f"{column!r} is one of ours and the class ban must not block it. A ban that "
        "false-positives on real features gets disabled, and then bans nothing."
    )


@pytest.mark.parametrize("column", PROJECTION_OR_RANKING)
def test_the_validator_actually_rejects_it(column: str) -> None:
    """The pattern existing is not enough — the gate every trainer calls must use it."""
    with pytest.raises(ValueError, match="rohibited|arket"):
        validate_no_prohibited_features(["age", "ppg_t", column])


def test_the_validator_still_accepts_a_clean_feature_list() -> None:
    validate_no_prohibited_features(["age", "ppg_t", "games_t", "aging_curve_value"])
