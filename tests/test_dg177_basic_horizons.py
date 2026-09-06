"""Round 2, item 5 — years 1-5 on the basic cohort: unsupported cells are reported, never filled."""
from __future__ import annotations

import pytest

from scripts.experiments.dg177_basic_horizons import (
    HORIZONS,
    evaluable_horizons,
    horizon_support,
)


def test_horizons_are_one_to_five():
    assert HORIZONS == (1, 2, 3, 4, 5)


def test_support_counts_closed_training_seasons_per_horizon():
    seasons = list(range(2010, 2026))
    support = horizon_support(seasons, last_complete_season=2025, min_training_seasons=6)
    # a year-5 label closes at t+5 <= 2025 -> feature seasons 2010..2020: 11 closed seasons
    assert support[5]["closed_feature_seasons"] == list(range(2010, 2021))
    assert support[5]["supported"] is True
    assert support[1]["closed_feature_seasons"] == list(range(2010, 2025))


def test_a_horizon_with_too_few_closed_seasons_is_unsupported_not_filled():
    seasons = list(range(2018, 2026))
    support = horizon_support(seasons, last_complete_season=2025, min_training_seasons=6)
    assert support[5]["supported"] is False and "2018" in support[5]["reason"]
    assert evaluable_horizons(support) == [1, 2]      # 2018-2025 supports only 1-2 at that floor


def test_the_manifest_window_id_follows_the_label_source():
    from scripts.experiments.dg177_basic_horizons import WINDOW_IDS, window_id_for

    assert WINDOW_IDS == {"this_lane_REG_aggregation": "all_reg_weeks", "common_outcome_artifact": "championship_week17"}
    assert window_id_for("this_lane_REG_aggregation") == "all_reg_weeks"
    assert window_id_for("common_outcome_artifact") == "championship_week17"
    with pytest.raises(ValueError):
        window_id_for("something_else")


def test_outcome_binding_block_uses_the_ranking_lanes_exact_keys():
    from scripts.experiments.dg177_basic_horizons import outcome_binding

    attrs = {"target_identity": "t" * 64, "csv_sha256": "c" * 64, "manifest_sha256": "m" * 64,
             "scoring": "nflverse_default_ppr_championship_window_v1", "last_complete_season": 2025,
             "exposure": "unique stat_record weeks within the outcome window", "window_id": "championship_week17",
             "source_validation": {"coverage_status": "qualified_research_game_complete_identified_rows"}}
    block = outcome_binding(attrs)
    assert block["outcome"] == {"target_identity": "t" * 64, "outcomes_csv_sha256": "c" * 64, "manifest_sha256": "m" * 64,
                                "scoring_preset": "nflverse_default_ppr_championship_window_v1",
                                "coverage_status": "qualified_research_game_complete_identified_rows",
                                "last_complete_season": 2025}
    assert block["window_id"] == "championship_week17"
    assert block["scoring"] == "nflverse_default_ppr_championship_window_v1"
    assert block["exposure_definition"] == "unique stat_record weeks within the outcome window"


def test_embedded_and_final_manifest_disagreements_are_named_not_hidden():
    from scripts.experiments.dg177_basic_horizons import manifest_disagreements

    final = {"window_id": "championship_week17", "scoring": "nflverse_default_ppr_championship_window_v1",
             "outcome": {"target_identity": "t" * 64}, "scoring_scope": {"window_id": "championship_week17"},
             "outputs": {"a": "1"}, "outputs_sha256": {"a": "1"}, "evaluation_status": {"x": 1}}
    same = dict(final)
    assert manifest_disagreements(same, final) == []
    embedded = {**final, "window_id": "all_reg_weeks", "scoring_scope": {"window_id": "all_reg_weeks"}, "outcome": None}
    embedded.pop("outputs")  # outputs are known only after writing: not a disagreement
    embedded.pop("outputs_sha256")
    assert manifest_disagreements(embedded, final) == ["outcome", "scoring_scope", "window_id"]


def test_position_rule_note_states_the_actual_fallback_rule():
    from scripts.experiments.dg177_basic_horizons import POSITION_RULE_NOTE

    assert "recognized offensive stat-line position first" in POSITION_RULE_NOTE
    assert "unambiguous same-feature-season offensive roster role" in POSITION_RULE_NOTE
    assert "otherwise abstain" in POSITION_RULE_NOTE
    assert "excluded" not in POSITION_RULE_NOTE
