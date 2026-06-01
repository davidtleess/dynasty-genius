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
