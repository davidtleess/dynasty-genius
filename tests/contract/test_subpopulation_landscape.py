from importlib import import_module

import pytest


def _subpop_module():
    return import_module("src.dynasty_genius.eval.subpopulation_landscape")


def test_subpopulation_landscape_exposes_pre_registered_constants():
    module = _subpop_module()

    assert module.NEUTRAL_BAND == 0.05
    assert module.DISAGREEMENT_MIN_SLOTS == 12
    assert module.EARLY_CAREER_MAX_EXP == 2
    assert module.SPEARMAN_MIN_N == 30
    assert module.COVERAGE_GATE == 0.95
    assert module.FDR_Q == 0.10
    assert module.AGING_THRESHOLDS == {
        "RB": 25,
        "WR": 27,
        "TE": 29,
        "QB": 32,
    }


def test_resolve_draft_year_maps_one_row_per_gsis_id():
    module = _subpop_module()

    draft_year_map, db_season_snapshot = module.resolve_draft_year([
        {"gsis_id": "00-001", "draft_year": "2021", "db_season": 2024},
        {"gsis_id": "00-002", "draft_year": 2022, "db_season": 2024},
    ])

    assert draft_year_map == {"00-001": 2021, "00-002": 2022}
    assert db_season_snapshot == 2024


def test_resolve_draft_year_latest_db_season_wins_deterministically():
    module = _subpop_module()

    draft_year_map, db_season_snapshot = module.resolve_draft_year([
        {"gsis_id": "00-001", "draft_year": None, "db_season": 2023},
        {"gsis_id": "00-001", "draft_year": 2021, "db_season": 2025},
        {"gsis_id": "00-002", "draft_year": 2022, "db_season": 2024},
    ])

    assert draft_year_map == {"00-001": 2021, "00-002": 2022}
    assert db_season_snapshot == 2025


def test_resolve_draft_year_conflicting_non_null_values_raise_value_error():
    module = _subpop_module()

    with pytest.raises(ValueError):
        module.resolve_draft_year([
            {"gsis_id": "00-001", "draft_year": 2020, "db_season": 2024},
            {"gsis_id": "00-001", "draft_year": 2021, "db_season": 2025},
        ])


def test_resolve_draft_year_allows_identical_and_null_vs_value_duplicates():
    module = _subpop_module()

    draft_year_map, db_season_snapshot = module.resolve_draft_year([
        {"gsis_id": "00-001", "draft_year": 2021, "db_season": 2023},
        {"gsis_id": "00-001", "draft_year": 2021, "db_season": 2025},
        {"gsis_id": "00-002", "draft_year": None, "db_season": 2024},
        {"gsis_id": "00-002", "draft_year": 2022, "db_season": 2025},
    ])

    assert draft_year_map == {"00-001": 2021, "00-002": 2022}
    assert db_season_snapshot == 2025


def test_resolve_draft_year_excludes_null_or_absent_draft_year_without_raising():
    module = _subpop_module()

    draft_year_map, db_season_snapshot = module.resolve_draft_year([
        {"gsis_id": "00-001", "draft_year": None, "db_season": 2024},
        {"gsis_id": "00-002", "db_season": 2025},
        {"gsis_id": "00-003", "draft_year": 2023, "db_season": 2025},
    ])

    assert draft_year_map == {"00-003": 2023}
    assert "00-001" not in draft_year_map
    assert "00-002" not in draft_year_map
    assert db_season_snapshot == 2025


@pytest.mark.parametrize("bad_draft_year", ["abc", 2020.5])
def test_resolve_draft_year_non_integer_values_raise_typed_error(bad_draft_year):
    module = _subpop_module()

    with pytest.raises(module.InvalidDraftYearError):
        module.resolve_draft_year([
            {
                "gsis_id": "00-001",
                "draft_year": bad_draft_year,
                "db_season": 2024,
            }
        ])


def test_invalid_draft_year_error_is_a_value_error():
    module = _subpop_module()

    assert issubclass(module.InvalidDraftYearError, ValueError)


@pytest.mark.parametrize(
    ("position", "threshold"),
    [("RB", 25), ("WR", 27), ("TE", 29), ("QB", 32)],
)
def test_tag_cohorts_flags_aging_cliff_boundaries(position, threshold):
    module = _subpop_module()

    tagged = module.tag_cohorts(
        [
            {
                "player_id": f"{position}_below",
                "position": position,
                "age_at_feature_season": threshold - 0.1,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
            {
                "player_id": f"{position}_at",
                "position": position,
                "age_at_feature_season": threshold,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
        ],
        {},
    )

    by_id = {row["player_id"]: row for row in tagged}
    assert by_id[f"{position}_below"]["aging_cliff_transition"] is False
    assert by_id[f"{position}_at"]["aging_cliff_transition"] is True


def test_tag_cohorts_flags_high_disagreement_direction_with_lower_rank_better():
    module = _subpop_module()

    tagged = module.tag_cohorts(
        [
            {
                "player_id": "model_bullish",
                "position": "WR",
                "age_at_feature_season": 24,
                "feature_season": 2024,
                "model_rank": 8,
                "consensus_rank": 20,
            },
            {
                "player_id": "model_bearish",
                "position": "WR",
                "age_at_feature_season": 24,
                "feature_season": 2024,
                "model_rank": 25,
                "consensus_rank": 13,
            },
            {
                "player_id": "inside_band",
                "position": "WR",
                "age_at_feature_season": 24,
                "feature_season": 2024,
                "model_rank": 20,
                "consensus_rank": 9,
            },
        ],
        {},
    )

    by_id = {row["player_id"]: row for row in tagged}
    assert by_id["model_bullish"]["high_disagreement"] is True
    assert by_id["model_bullish"]["disagreement_bucket"] == "model_bullish"
    assert by_id["model_bearish"]["high_disagreement"] is True
    assert by_id["model_bearish"]["disagreement_bucket"] == "model_bearish"
    assert by_id["inside_band"]["high_disagreement"] is False
    assert by_id["inside_band"]["disagreement_bucket"] is None


def test_tag_cohorts_flags_early_career_and_exclusions():
    module = _subpop_module()

    tagged = module.tag_cohorts(
        [
            {
                "player_id": "rookie_window",
                "position": "RB",
                "age_at_feature_season": 23,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
            {
                "player_id": "too_old_for_axis",
                "position": "RB",
                "age_at_feature_season": 25,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
            {
                "player_id": "negative_experience",
                "position": "RB",
                "age_at_feature_season": 22,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
            {
                "player_id": "missing_draft_year",
                "position": "RB",
                "age_at_feature_season": 22,
                "feature_season": 2024,
                "model_rank": 10,
                "consensus_rank": 10,
            },
            {
                "player_id": "null_experience",
                "position": "RB",
                "age_at_feature_season": 22,
                "feature_season": None,
                "model_rank": 10,
                "consensus_rank": 10,
            },
        ],
        {
            "rookie_window": 2022,
            "too_old_for_axis": 2021,
            "negative_experience": 2025,
            "null_experience": 2022,
        },
    )

    by_id = {row["player_id"]: row for row in tagged}
    assert by_id["rookie_window"]["early_career_eligible"] is True
    assert by_id["rookie_window"]["early_career_experience_year"] == 2
    assert by_id["rookie_window"]["cohort_exclusion_reasons"] == []
    assert by_id["too_old_for_axis"]["early_career_eligible"] is False
    assert by_id["too_old_for_axis"]["early_career_experience_year"] == 3
    assert by_id["too_old_for_axis"]["cohort_exclusion_reasons"] == []
    assert by_id["negative_experience"]["early_career_eligible"] is False
    assert by_id["negative_experience"]["early_career_experience_year"] == -1
    assert "invalid_negative_experience" in by_id["negative_experience"][
        "cohort_exclusion_reasons"
    ]
    assert by_id["missing_draft_year"]["early_career_eligible"] is False
    assert by_id["missing_draft_year"]["early_career_experience_year"] is None
    assert by_id["missing_draft_year"]["cohort_exclusion_reasons"] == []
    assert by_id["null_experience"]["early_career_eligible"] is False
    assert by_id["null_experience"]["early_career_experience_year"] is None
    assert "invalid_negative_experience" in by_id["null_experience"][
        "cohort_exclusion_reasons"
    ]


def test_tag_cohorts_never_mutates_rank_fields():
    module = _subpop_module()
    rows = [
        {
            "player_id": "rank_check",
            "position": "QB",
            "age_at_feature_season": 31,
            "feature_season": 2024,
            "model_rank": 5,
            "consensus_rank": 17,
        }
    ]

    tagged = module.tag_cohorts(rows, {})

    assert rows[0]["model_rank"] == 5
    assert rows[0]["consensus_rank"] == 17
    assert tagged[0]["model_rank"] == 5
    assert tagged[0]["consensus_rank"] == 17
    assert tagged[0] is not rows[0]
