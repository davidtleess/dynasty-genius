import hashlib
import importlib.util
import json
from importlib import import_module
from pathlib import Path

import pytest

REPORT_HEADER = "DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim."


def _subpop_module():
    return import_module("src.dynasty_genius.eval.subpopulation_landscape")


def _subpop_cli_module():
    path = Path("scripts/run_subpopulation_landscape.py")
    spec = importlib.util.spec_from_file_location("run_subpopulation_landscape", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _rank_fixture(n: int) -> list[int]:
    return list(range(1, n + 1))


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _walk_strings(item)


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _walk_dicts(item)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_compute_slice_orientation_lock_lower_rank_is_better():
    module = _subpop_module()
    realized = _rank_fixture(30)
    model = _rank_fixture(30)
    consensus = list(reversed(realized))

    result = module.compute_slice(
        model,
        consensus,
        realized,
        primary_k=10,
        n_bootstrap=25,
        rng_seed=7,
    )

    assert result["n"] == 30
    assert result["rho_model"] == pytest.approx(1.0)
    assert result["rho_consensus"] == pytest.approx(-1.0)
    assert result["rho_diff"] > 0
    assert result["category"] == "model_leads_point_estimate"
    assert result["bca_ci95"][0] <= result["rho_diff"] <= result["bca_ci95"][1]
    assert isinstance(result["ci_includes_zero"], bool)
    assert 0.0 <= result["boot_p_value"] <= 1.0
    assert result["ndcg_xcheck"]["status"] == "available"


@pytest.mark.parametrize(
    ("rho_diff", "expected_category"),
    [
        (0.05, "model_leads_point_estimate"),
        (-0.05, "consensus_leads_point_estimate"),
        (0.049, "statistically_indistinguishable"),
        (-0.049, "statistically_indistinguishable"),
    ],
)
def test_compute_slice_category_uses_sign_and_neutral_band_not_ci(
    monkeypatch,
    rho_diff,
    expected_category,
):
    module = _subpop_module()

    def fake_rho_diff(*_args, **_kwargs):
        return {
            "rho_model": 0.4 + rho_diff,
            "rho_consensus": 0.4,
            "rho_diff": rho_diff,
            "bca_ci95": (-1.0, 1.0),
            "ci_includes_zero": True,
            "boot_p_value": 1.0,
        }

    monkeypatch.setattr(module, "_bootstrap_rho_diff", fake_rho_diff, raising=False)

    result = module.compute_slice(
        _rank_fixture(30),
        _rank_fixture(30),
        _rank_fixture(30),
        primary_k=10,
        n_bootstrap=25,
        rng_seed=7,
    )

    assert result["ci_includes_zero"] is True
    assert result["rho_diff"] == pytest.approx(rho_diff)
    assert result["category"] == expected_category


def test_compute_slice_spearman_available_when_ndcg_insufficient():
    module = _subpop_module()

    result = module.compute_slice(
        _rank_fixture(30),
        list(reversed(_rank_fixture(30))),
        _rank_fixture(30),
        primary_k=40,
        n_bootstrap=25,
        rng_seed=7,
    )

    assert result["n"] == 30
    assert result["category"] == "model_leads_point_estimate"
    assert result["rho_model"] == pytest.approx(1.0)
    assert result["ndcg_xcheck"]["status"] == "insufficient_n"
    assert result["ndcg_xcheck"]["model_ndcg"] is None
    assert result["ndcg_xcheck"]["consensus_ndcg"] is None


def test_compute_slice_ndcg_available_when_spearman_insufficient():
    module = _subpop_module()

    result = module.compute_slice(
        _rank_fixture(20),
        list(reversed(_rank_fixture(20))),
        _rank_fixture(20),
        primary_k=10,
        n_bootstrap=25,
        rng_seed=7,
    )

    assert result["n"] == 20
    assert result["category"] == "insufficient_n"
    assert result["rho_model"] is None
    assert result["rho_consensus"] is None
    assert result["rho_diff"] is None
    assert result["bca_ci95"] is None
    assert result["ci_includes_zero"] is None
    assert result["boot_p_value"] is None
    assert result["ndcg_xcheck"]["status"] == "available"
    assert result["ndcg_xcheck"]["model_ndcg"] is not None
    assert result["ndcg_xcheck"]["consensus_ndcg"] is not None


def test_compute_slice_is_deterministic_for_fixed_rng_seed():
    module = _subpop_module()
    realized = _rank_fixture(35)
    model = [1, 2, 4, 3, *range(5, 36)]
    consensus = [2, 1, 3, 5, 4, *range(6, 36)]

    first = module.compute_slice(
        model,
        consensus,
        realized,
        primary_k=10,
        n_bootstrap=50,
        rng_seed=123,
    )
    second = module.compute_slice(
        model,
        consensus,
        realized,
        primary_k=10,
        n_bootstrap=50,
        rng_seed=123,
    )

    assert first["bca_ci95"] == second["bca_ci95"]
    assert first["boot_p_value"] == second["boot_p_value"]


def test_aggregate_folds_uses_median_rho_diff_and_counts_evaluable_folds_only():
    module = _subpop_module()
    slice_folds = [
        {
            "fold": 2021,
            "category": "model_leads_point_estimate",
            "rho_diff": 0.50,
            "n": 40,
        },
        {
            "fold": 2022,
            "category": "insufficient_n",
            "rho_diff": None,
            "n": 12,
        },
        {
            "fold": 2023,
            "category": "consensus_leads_point_estimate",
            "rho_diff": -0.10,
            "n": 41,
        },
        {
            "fold": 2024,
            "category": "insufficient_n",
            "rho_diff": None,
            "n": 11,
        },
    ]

    aggregate = module.aggregate_folds(slice_folds)

    assert aggregate["median_rho_diff"] == pytest.approx(0.20)
    assert aggregate["folds_covered"] == 2
    assert aggregate["fold_rows"] == slice_folds


def test_aggregate_folds_preserves_fold_rows_without_pseudo_replication_primary():
    module = _subpop_module()
    slice_folds = [
        {"fold": 2021, "rho_diff": 0.70, "category": "model_leads_point_estimate"},
        {"fold": 2022, "rho_diff": -0.10, "category": "consensus_leads_point_estimate"},
    ]

    aggregate = module.aggregate_folds(slice_folds)

    assert aggregate["median_rho_diff"] == pytest.approx(0.30)
    assert aggregate["folds_covered"] == 2
    assert aggregate["fold_rows"] == slice_folds
    assert "pooled_rho_diff" not in aggregate
    if "secondary_pooled" in aggregate:
        assert "median_rho_diff" not in aggregate["secondary_pooled"]
        assert aggregate["secondary_pooled"].get("label") == "secondary"


@pytest.mark.parametrize("slice_folds", [[], [{"fold": 2021, "rho_diff": None}]])
def test_aggregate_folds_fail_closed_when_empty_or_all_insufficient(slice_folds):
    module = _subpop_module()

    aggregate = module.aggregate_folds(slice_folds)

    assert aggregate["median_rho_diff"] is None
    assert aggregate["folds_covered"] == 0
    assert aggregate["fold_rows"] == slice_folds


def test_apply_fdr_returns_new_records_with_global_bh_q_values_on_aggregates_only():
    module = _subpop_module()
    aggregate_tests = [
        {
            "axis": "aging_cliff_transition",
            "slice": "all",
            "position": "RB",
            "boot_p_value": 0.001,
            "fold_rows": [{"fold": 2021, "boot_p_value": 0.90}],
        },
        {
            "axis": "high_disagreement",
            "slice": "model_bullish",
            "position": "WR",
            "boot_p_value": 0.04,
            "fold_rows": [{"fold": 2021, "boot_p_value": 0.001}],
        },
        {
            "axis": "high_disagreement",
            "slice": "model_bearish",
            "position": "TE",
            "boot_p_value": 0.03,
            "fold_rows": [],
        },
        {
            "axis": "early_career",
            "slice": "eligible",
            "position": "QB",
            "boot_p_value": 0.20,
            "fold_rows": [],
        },
        {
            "axis": "early_career",
            "slice": "missing_draft_year",
            "position": "RB",
            "boot_p_value": None,
            "fold_rows": [],
        },
    ]

    adjusted = module.apply_fdr(aggregate_tests)

    assert adjusted is not aggregate_tests
    assert [record["q_value"] for record in adjusted[:-1]] == pytest.approx([
        0.004,
        0.05333333333333334,
        0.05333333333333334,
        0.20,
    ])
    assert adjusted[-1]["q_value"] is None
    assert [record["powered_followup_candidate"] for record in adjusted] == [
        True,
        True,
        True,
        False,
        False,
    ]
    assert all(
        record["powered_followup_label"] == "hypothesis_generating"
        for record in adjusted
    )
    assert all("q_value" not in record for record in aggregate_tests)
    assert all("powered_followup_candidate" not in record for record in aggregate_tests)


def test_apply_fdr_ignores_fold_level_p_values_and_leaves_fold_rows_untouched():
    module = _subpop_module()
    fold_rows = [
        {"fold": 2021, "boot_p_value": 0.001},
        {"fold": 2022, "boot_p_value": 0.002},
    ]
    aggregate_tests = [
        {
            "axis": "high_disagreement",
            "slice": "model_bullish",
            "position": "RB",
            "boot_p_value": 0.80,
            "fold_rows": fold_rows,
        },
        {
            "axis": "high_disagreement",
            "slice": "model_bearish",
            "position": "RB",
            "boot_p_value": 0.90,
            "fold_rows": [],
        },
    ]

    adjusted = module.apply_fdr(aggregate_tests)

    assert [record["q_value"] for record in adjusted] == pytest.approx([0.90, 0.90])
    assert [record["powered_followup_candidate"] for record in adjusted] == [
        False,
        False,
    ]
    assert adjusted[0]["fold_rows"] == fold_rows
    assert adjusted[0]["fold_rows"] is not fold_rows
    assert all("q_value" not in fold_row for fold_row in adjusted[0]["fold_rows"])
    assert all(
        "powered_followup_candidate" not in fold_row
        for fold_row in adjusted[0]["fold_rows"]
    )
    assert all("q_value" not in fold_row for fold_row in fold_rows)
    assert all("powered_followup_candidate" not in fold_row for fold_row in fold_rows)


def test_apply_fdr_fail_closed_for_empty_and_all_none_p_values():
    module = _subpop_module()

    assert module.apply_fdr([]) == []

    adjusted = module.apply_fdr([
        {
            "axis": "aging_cliff_transition",
            "slice": "all",
            "position": "RB",
            "boot_p_value": None,
            "fold_rows": [],
        },
        {
            "axis": "early_career",
            "slice": "eligible",
            "position": "WR",
            "boot_p_value": None,
            "fold_rows": [],
        },
    ])

    assert [record["q_value"] for record in adjusted] == [None, None]
    assert [record["powered_followup_candidate"] for record in adjusted] == [
        False,
        False,
    ]
    assert all(
        record["powered_followup_label"] == "hypothesis_generating"
        for record in adjusted
    )


@pytest.mark.parametrize(
    ("fold_rho_diffs", "expected_p"),
    [
        ([0.5, 0.4, 0.3, 0.2], 0.25),
        ([0.5, 0.4, 0.3], 0.50),
        ([0.5, 0.4], 0.50),
        ([0.6, 0.5, 0.4, 0.3, 0.2, 0.1], 0.125),
        ([0.5, 0.4, 0.3, -0.2], 0.25),
    ],
)
def test_aggregate_signflip_p_exact_reference_values(
    fold_rho_diffs,
    expected_p,
):
    module = _subpop_module()

    assert module.aggregate_signflip_p(fold_rho_diffs) == pytest.approx(expected_p)


def test_aggregate_signflip_p_fail_closed_empty_and_all_zero():
    module = _subpop_module()

    assert module.aggregate_signflip_p([]) is None
    assert module.aggregate_signflip_p([0.0, 0.0, 0.0, 0.0]) == pytest.approx(1.0)


def test_aggregate_signflip_p_includes_zero_effects_as_evaluable_folds():
    module = _subpop_module()

    # Zero fold effects remain in the observed median and in the 2^K sign-flip
    # enumeration; a zero's flipped sign is still zero.
    assert module.aggregate_signflip_p([0.5, 0.4, 0.0, 0.0]) == pytest.approx(0.50)


def test_aggregate_signflip_p_is_deterministic_without_rng(monkeypatch):
    module = _subpop_module()

    def fail_rng(*_args, **_kwargs):
        raise AssertionError("aggregate_signflip_p must be exact, not random")

    monkeypatch.setattr(module.np.random, "default_rng", fail_rng)

    first = module.aggregate_signflip_p([0.5, 0.4, 0.3, -0.2])
    second = module.aggregate_signflip_p([0.5, 0.4, 0.3, -0.2])
    assert first == second == pytest.approx(0.25)


def test_build_slice_ledger_balanced_bins_header_and_provenance():
    module = _subpop_module()
    aggregate_tests = [
        {
            "axis": "high_disagreement",
            "slice": "model_bullish",
            "position": "WR",
            "category": "model_leads_point_estimate",
            "n": 64,
            "folds_covered": 4,
            "median_rho_diff": 0.11,
            "q_value": 0.04,
            "powered_followup_candidate": True,
            "powered_followup_label": "hypothesis_generating",
            "fold_rows": [
                {
                    "fold": 2021,
                    "category": "model_leads_point_estimate",
                    "n": 32,
                }
            ],
        },
    ]
    draft_year_provenance = {
        "draft_year_source": "dynastyprocess_db_playerids",
        "db_season_snapshot": 2025,
        "draft_year_coverage_numerator": 98,
        "draft_year_coverage_denominator": 100,
        "excluded_missing_draft_year_count": 2,
        "invalid_negative_experience_count": 1,
        "per_position_disagreement_denominators": {"WR": 64, "RB": 0},
    }
    early_career_coverage = {
        "overall": {"covered": 98, "denominator": 100},
        "per_position_fold": [
            {"position": "WR", "fold": 2021, "covered": 32, "denominator": 32}
        ],
    }

    ledger = module.build_slice_ledger(
        aggregate_tests,
        draft_year_provenance=draft_year_provenance,
        early_career_coverage=early_career_coverage,
    )

    assert ledger["header"] == REPORT_HEADER
    assert set(ledger) == {"header", "axis_tables", "provenance"}
    assert ledger["provenance"] == {
        **draft_year_provenance,
        "early_career_coverage": early_career_coverage,
    }
    expected_bins = {
        "model_leads_point_estimate",
        "consensus_leads_point_estimate",
        "statistically_indistinguishable",
        "insufficient_n",
    }
    for axis in [
        "aging_cliff_transition",
        "high_disagreement",
        "early_career",
    ]:
        axis_table = ledger["axis_tables"][axis]
        assert axis_table["status"] == "available"
        bins = {row["category"] for row in axis_table["rows"]}
        assert bins == expected_bins
        assert all("n" in row and "folds_covered" in row for row in axis_table["rows"])

    high_disagreement_rows = {
        row["category"]: row
        for row in ledger["axis_tables"]["high_disagreement"]["rows"]
    }
    assert high_disagreement_rows["model_leads_point_estimate"]["n"] == 64
    assert high_disagreement_rows["model_leads_point_estimate"]["folds_covered"] == 4
    assert high_disagreement_rows["consensus_leads_point_estimate"]["n"] == 0
    assert high_disagreement_rows["consensus_leads_point_estimate"][
        "folds_covered"
    ] == 0


def test_build_slice_ledger_early_career_coverage_gate_fails_closed():
    module = _subpop_module()
    aggregate_tests = [
        {
            "axis": "early_career",
            "slice": "eligible",
            "position": "RB",
            "category": "model_leads_point_estimate",
            "n": 40,
            "folds_covered": 3,
            "median_rho_diff": 0.20,
            "fold_rows": [],
        }
    ]
    draft_year_provenance = {
        "draft_year_source": "dynastyprocess_db_playerids",
        "db_season_snapshot": 2025,
        "draft_year_coverage_numerator": 94,
        "draft_year_coverage_denominator": 100,
        "excluded_missing_draft_year_count": 6,
        "invalid_negative_experience_count": 0,
        "per_position_disagreement_denominators": {"RB": 40},
    }
    early_career_coverage = {
        "overall": {"covered": 94, "denominator": 100},
        "per_position_fold": [
            {"position": "RB", "fold": 2021, "covered": 38, "denominator": 40}
        ],
    }

    ledger = module.build_slice_ledger(
        aggregate_tests,
        draft_year_provenance=draft_year_provenance,
        early_career_coverage=early_career_coverage,
    )

    early_career = ledger["axis_tables"]["early_career"]
    assert early_career == {
        "status": "early_career_axis_unavailable",
        "coverage_counts": {
            "overall": {"covered": 94, "denominator": 100},
            "per_position_fold": [
                {"position": "RB", "fold": 2021, "covered": 38, "denominator": 40}
            ],
        },
        "rows": [],
    }


def test_build_slice_ledger_missing_or_invalid_draft_year_input_fails_closed():
    module = _subpop_module()

    ledger = module.build_slice_ledger(
        [],
        draft_year_provenance={
            "draft_year_source": None,
            "db_season_snapshot": None,
            "draft_year_coverage_numerator": 0,
            "draft_year_coverage_denominator": 0,
            "excluded_missing_draft_year_count": 0,
            "invalid_negative_experience_count": 0,
            "per_position_disagreement_denominators": {},
        },
        early_career_coverage=None,
        invalid_draft_year_error=module.InvalidDraftYearError("bad draft_year"),
    )

    assert ledger["axis_tables"]["early_career"]["status"] == (
        "early_career_axis_unavailable"
    )
    assert ledger["axis_tables"]["early_career"]["rows"] == []
    assert ledger["provenance"]["invalid_draft_year_error"] == "bad draft_year"


def test_build_slice_ledger_posture_guard_no_decision_or_edge_labels():
    module = _subpop_module()

    ledger = module.build_slice_ledger(
        [
            {
                "axis": "aging_cliff_transition",
                "slice": "all",
                "position": "RB",
                "category": "statistically_indistinguishable",
                "n": 30,
                "folds_covered": 2,
                "decision_supported": False,
                "fold_rows": [],
            }
        ],
        draft_year_provenance={
            "draft_year_source": "dynastyprocess_db_playerids",
            "db_season_snapshot": 2025,
            "draft_year_coverage_numerator": 30,
            "draft_year_coverage_denominator": 30,
            "excluded_missing_draft_year_count": 0,
            "invalid_negative_experience_count": 0,
            "per_position_disagreement_denominators": {"RB": 30},
        },
        early_career_coverage={
            "overall": {"covered": 30, "denominator": 30},
            "per_position_fold": [
                {"position": "RB", "fold": 2021, "covered": 30, "denominator": 30}
            ],
        },
    )

    assert ledger["header"] == REPORT_HEADER
    assert all(
        record.get("decision_supported") is not True for record in _walk_dicts(ledger)
    )
    banned = {"buy", "sell", "verdict", "grade", "tier", "recommendation"}
    strings = [text for text in _walk_strings(ledger) if text != REPORT_HEADER]
    assert not any(token in text.lower() for text in strings for token in banned)
    for axis_table in ledger["axis_tables"].values():
        for row in axis_table["rows"]:
            checked = [
                str(row.get("category", "")),
                str(row.get("slice", "")),
                str(row.get("recommendation", "")),
            ]
            assert not any("edge" in text.lower() for text in checked)


def test_build_slice_ledger_does_not_echo_dirty_aggregate_posture_fields():
    module = _subpop_module()

    ledger = module.build_slice_ledger(
        [
            {
                "axis": "aging_cliff_transition",
                "slice": "edge_buy_candidate",
                "position": "RB",
                "category": "buy_grade_edge",
                "n": 30,
                "folds_covered": 2,
                "decision_supported": True,
                "recommendation": "buy",
                "fold_rows": [
                    {
                        "decision_supported": True,
                        "recommendation": "sell",
                        "slice": "edge_followup",
                    }
                ],
            }
        ],
        draft_year_provenance={
            "draft_year_source": "dynastyprocess_db_playerids",
            "db_season_snapshot": 2025,
            "draft_year_coverage_numerator": 30,
            "draft_year_coverage_denominator": 30,
            "excluded_missing_draft_year_count": 0,
            "invalid_negative_experience_count": 0,
            "per_position_disagreement_denominators": {"RB": 30},
        },
        early_career_coverage={
            "overall": {"covered": 30, "denominator": 30},
            "per_position_fold": [
                {"position": "RB", "fold": 2021, "covered": 30, "denominator": 30}
            ],
        },
    )

    assert ledger["header"] == REPORT_HEADER
    assert all(
        record.get("decision_supported") is not True for record in _walk_dicts(ledger)
    )
    strings = [text for text in _walk_strings(ledger) if text != REPORT_HEADER]
    banned = {"buy", "sell", "verdict", "grade", "tier", "recommendation"}
    assert not any(token in text.lower() for text in strings for token in banned)
    for axis_table in ledger["axis_tables"].values():
        for row in axis_table["rows"]:
            checked = [
                str(row.get("category", "")),
                str(row.get("slice", "")),
                str(row.get("recommendation", "")),
            ]
            assert not any("edge" in text.lower() for text in checked)


def test_subpopulation_cli_loads_joins_writes_and_preserves_inputs(
    tmp_path,
    monkeypatch,
):
    cli = _subpop_cli_module()
    run_dir = tmp_path / "20260601T120000Z"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    market_path = run_dir / "market_comparison_WR.json"
    prediction_path = run_dir / "predictions_WR.csv"
    id_map_path = tmp_path / "db_playerids.csv"
    market_path.write_text(
        json.dumps([
            {
                "player_id": "00-001",
                "feature_season": 2024,
                "position": "WR",
                "model_rank": 8,
                "consensus_rank": 20,
                "realized_rank": 6,
            }
        ]),
        encoding="utf-8",
    )
    prediction_path.write_text(
        "player_id,feature_season,age_at_feature_season\n00-001,2024,24.5\n",
        encoding="utf-8",
    )
    id_map_path.write_text(
        "gsis_id,draft_year,db_season\n00-001,2022,2025\n",
        encoding="utf-8",
    )
    input_hashes = {
        path: _sha256(path) for path in [market_path, prediction_path, id_map_path]
    }
    captured = {}

    def fake_compute(enriched_rows, *, draft_year_provenance, run_id):
        captured["enriched_rows"] = enriched_rows
        captured["draft_year_provenance"] = draft_year_provenance
        captured["run_id"] = run_id
        return {
            "ledger": {
                "header": REPORT_HEADER,
                "axis_tables": {},
                "provenance": draft_year_provenance,
            },
            "aggregate_details": [
                {
                    "axis": "high_disagreement",
                    "slice": "model_bullish",
                    "position": "WR",
                    "category": "model_leads_point_estimate",
                    "q_value": 0.04,
                    "powered_followup_label": "hypothesis_generating",
                }
            ],
        }

    monkeypatch.setattr(cli, "_compute_landscape_payload", fake_compute)

    assert cli.main([
        "--run-dir",
        str(run_dir),
        "--id-map-csv",
        str(id_map_path),
        "--output-dir",
        str(output_dir),
    ]) == 0

    assert captured["run_id"] == "20260601T120000Z"
    assert captured["enriched_rows"] == [
        {
            "player_id": "00-001",
            "feature_season": 2024,
            "position": "WR",
            "model_rank": 8,
            "consensus_rank": 20,
            "realized_rank": 6,
            "age_at_feature_season": 24.5,
            "draft_year": 2022,
        }
    ]
    assert captured["draft_year_provenance"]["draft_year_source"] == (
        "dynastyprocess_db_playerids"
    )
    assert captured["draft_year_provenance"]["db_season_snapshot"] == 2025
    assert (output_dir / "subpopulation_landscape_latest.json").exists()
    assert (output_dir / "subpopulation_landscape_latest.md").exists()
    run_json = output_dir / "subpopulation_landscape_20260601T120000Z.json"
    run_md = output_dir / "subpopulation_landscape_20260601T120000Z.md"
    assert run_json.exists()
    assert run_md.exists()
    artifact = json.loads(run_json.read_text(encoding="utf-8"))
    assert artifact["run_id"] == "20260601T120000Z"
    assert artifact["ledger"]["header"] == REPORT_HEADER
    assert artifact["aggregate_details"][0]["powered_followup_label"] == (
        "hypothesis_generating"
    )
    assert {path: _sha256(path) for path in input_hashes} == input_hashes


def test_subpopulation_cli_missing_id_map_fails_closed_without_crash(
    tmp_path,
    monkeypatch,
):
    cli = _subpop_cli_module()
    run_dir = tmp_path / "run_missing_id"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (run_dir / "market_comparison_RB.json").write_text(
        json.dumps([
            {
                "player_id": "00-002",
                "feature_season": 2024,
                "position": "RB",
                "model_rank": 12,
                "consensus_rank": 24,
                "realized_rank": 10,
            }
        ]),
        encoding="utf-8",
    )
    (run_dir / "predictions_RB.csv").write_text(
        "player_id,feature_season,age_at_feature_season\n00-002,2024,23\n",
        encoding="utf-8",
    )

    def fake_compute(enriched_rows, *, draft_year_provenance, run_id):
        assert enriched_rows[0]["draft_year"] is None
        assert draft_year_provenance["draft_year_source"] is None
        return {
            "ledger": {
                "header": REPORT_HEADER,
                "axis_tables": {
                    "early_career": {
                        "status": "early_career_axis_unavailable",
                        "coverage_counts": None,
                        "rows": [],
                    }
                },
                "provenance": draft_year_provenance,
            },
            "aggregate_details": [],
        }

    monkeypatch.setattr(cli, "_compute_landscape_payload", fake_compute)

    assert cli.main([
        "--run-dir",
        str(run_dir),
        "--output-dir",
        str(output_dir),
    ]) == 0

    artifact = json.loads(
        (output_dir / "subpopulation_landscape_run_missing_id.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["ledger"]["axis_tables"]["early_career"]["status"] == (
        "early_career_axis_unavailable"
    )


def test_subpopulation_cli_refuses_differing_run_artifact_overwrite(
    tmp_path,
    monkeypatch,
):
    cli = _subpop_cli_module()
    run_dir = tmp_path / "run_collision"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (run_dir / "market_comparison_QB.json").write_text("[]", encoding="utf-8")
    (run_dir / "predictions_QB.csv").write_text(
        "player_id,feature_season,age_at_feature_season\n",
        encoding="utf-8",
    )
    existing = output_dir / "subpopulation_landscape_run_collision.json"
    existing.write_text('{"different": true}\n', encoding="utf-8")
    before = existing.read_text(encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "_compute_landscape_payload",
        lambda enriched_rows, *, draft_year_provenance, run_id: {
            "ledger": {
                "header": REPORT_HEADER,
                "axis_tables": {},
                "provenance": draft_year_provenance,
            },
            "aggregate_details": [],
        },
    )

    assert cli.main([
        "--run-dir",
        str(run_dir),
        "--output-dir",
        str(output_dir),
    ]) == 1
    assert existing.read_text(encoding="utf-8") == before
    assert not (output_dir / "subpopulation_landscape_latest.json").exists()


def test_subpopulation_cli_posture_guard_fails_loud_before_write(tmp_path, monkeypatch):
    cli = _subpop_cli_module()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    dirty_payload = {
        "ledger": {
            "header": REPORT_HEADER,
            "axis_tables": {},
            "provenance": {},
        },
        "aggregate_details": [
            {
                "axis": "aging_cliff_transition",
                "slice": "edge_buy_candidate",
                "position": "RB",
                "category": "buy_grade_edge",
                "decision_supported": True,
                "recommendation": "buy",
            }
        ],
    }

    with pytest.raises(ValueError, match="posture"):
        cli._write_outputs(
            dirty_payload,
            output_dir=output_dir,
            run_id="dirty_run",
        )

    assert list(output_dir.iterdir()) == []


def test_subpopulation_cli_reexec_under_repo_venv_guard(monkeypatch):
    cli = _subpop_cli_module()
    calls = []

    monkeypatch.setattr(cli.sys, "prefix", "/usr/bin")
    monkeypatch.setattr(cli.sys, "base_prefix", "/usr")
    monkeypatch.setenv("DYNASTY_SUBPOPULATION_REEXEC", "")

    def fake_execv(executable, argv):
        calls.append((executable, argv))
        raise RuntimeError("stop after exec")

    monkeypatch.setattr(cli.os, "execv", fake_execv)

    with pytest.raises(RuntimeError, match="stop after exec"):
        cli._reexec_under_venv()

    assert calls
    assert calls[0][0].endswith(".venv/bin/python3.14")
    assert calls[0][1][0].endswith(".venv/bin/python3.14")
