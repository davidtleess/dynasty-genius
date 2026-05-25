"""Fixture validation tests — Phase 13.2 draft-capital bake-off.

These tests verify the fixture data itself is structurally sound and encodes
the behavioral properties the scenarios are meant to demonstrate. Codex's
Task 13.2.2 tests will import these same fixtures and assert LOOCV results.
"""
from __future__ import annotations

import math

import pytest

from src.dynasty_genius.eval.draft_class_loocv import (
    DraftClassEvaluationRow,
    DraftClassLOOCVError,
    build_loocv_folds,
    evaluate_candidate_loocv,
)
from tests.fixtures.draft_capital_bakeoff import (
    _MARKET_CONTAMINATED_SOURCE_FIELDS,
    _QB_CLIFF_PICKS,
    _QB_CLIFF_YEARS,
    all_candidates_qb_rows,
    candidate_scores_at_pick,
    market_contaminated_cohort,
    market_contaminated_row,
    qb_top15_cliff_rows,
    rb_day2_day3_drop_rows,
    single_class_rows,
    te_small_cohort_rows,
    wr_pick75_viability_rows,
)

# ---------------------------------------------------------------------------
# Scenario 1: QB top-15 cliff — fixture structure
# ---------------------------------------------------------------------------

class TestQBTop15CliffFixture:
    def test_row_count_correct(self):
        rows = qb_top15_cliff_rows()
        assert len(rows) == len(_QB_CLIFF_PICKS) * len(_QB_CLIFF_YEARS)

    def test_all_rows_are_qb(self):
        rows = qb_top15_cliff_rows()
        assert all(r.position == "QB" for r in rows)

    def test_covers_required_draft_classes(self):
        rows = qb_top15_cliff_rows()
        years = {r.draft_year for r in rows}
        assert years == set(_QB_CLIFF_YEARS)

    def test_bucketed_cliff_is_sharp_between_pick15_and_pick16(self):
        """Bucketed candidate must produce a large score gap at the tier boundary."""
        scores = candidate_scores_at_pick(15)
        scores_16 = candidate_scores_at_pick(16)
        cliff_bucketed = scores.position_bucketed - scores_16.position_bucketed
        cliff_log = scores.log_decay - scores_16.log_decay
        # Bucketed cliff must be at least 5x larger than log_decay's gradual drop
        assert cliff_bucketed > cliff_log * 5, (
            f"bucketed cliff={cliff_bucketed:.1f} must dwarf log_decay cliff={cliff_log:.1f}"
        )

    def test_log_decay_is_strictly_monotone(self):
        """Log_decay scores must strictly decrease as pick number increases."""
        picks = sorted(_QB_CLIFF_PICKS)
        rows = qb_top15_cliff_rows(candidate="log_decay")
        score_by_pick = {}
        for r in rows:
            pick = int(r.player_id.split("pick")[1].split("_")[0])
            score_by_pick[pick] = r.predicted_score
        for i in range(len(picks) - 1):
            assert score_by_pick[picks[i]] > score_by_pick[picks[i + 1]]

    def test_baseline_is_monotone_decreasing_in_pick(self):
        """Baseline scores must strictly decrease as pick increases (no step encoding)."""
        rows_2019 = [r for r in qb_top15_cliff_rows(candidate="current_engine_a_baseline")
                     if r.draft_year == 2019]
        pairs = sorted(
            [(int(r.player_id.split("pick")[1].split("_")[0]), r.predicted_score)
             for r in rows_2019]
        )
        for i in range(len(pairs) - 1):
            assert pairs[i][1] >= pairs[i + 1][1], (
                f"Baseline not monotone: pick {pairs[i][0]} score {pairs[i][1]} "
                f"vs pick {pairs[i+1][0]} score {pairs[i+1][1]}"
            )

    def test_realized_value_drops_at_pick16(self):
        """The fixture encodes a real cliff in realized value at pick 16."""
        rows_2019 = [r for r in qb_top15_cliff_rows() if r.draft_year == 2019]
        by_pick = {int(r.player_id.split("pick")[1].split("_")[0]): r.realized_value
                   for r in rows_2019}
        assert by_pick[15] > by_pick[16] * 1.5, (
            "Realized value cliff between pick 15 and 16 must be at least 50%"
        )


# ---------------------------------------------------------------------------
# Scenario 2: WR pick-75 viability
# ---------------------------------------------------------------------------

class TestWRPick75ViabilityFixture:
    def test_pick_74_and_76_in_different_bucketed_tiers(self):
        """position_bucketed assigns pick 74 to tier 2 and pick 76 to tier 3."""
        from tests.fixtures.draft_capital_bakeoff import _wr_bucketed_score
        assert _wr_bucketed_score(74) > _wr_bucketed_score(76)
        # The gap must be tier-sized (not just 2 points from log_decay drift)
        assert _wr_bucketed_score(74) - _wr_bucketed_score(76) > 30.0

    def test_pick_74_and_76_only_marginally_different_under_log_decay(self):
        """log_decay produces a smooth small difference between picks 74 and 76."""
        from tests.fixtures.draft_capital_bakeoff import _log_decay_score
        diff = abs(_log_decay_score(74) - _log_decay_score(76))
        assert diff < 3.0, f"log_decay diff at boundary should be small, got {diff:.2f}"

    def test_realized_value_cliff_at_76(self):
        """The fixture encodes a realized-value cliff between picks 74 and 76."""
        from tests.fixtures.draft_capital_bakeoff import _WR_VIABILITY_REALIZED
        assert _WR_VIABILITY_REALIZED[74] > _WR_VIABILITY_REALIZED[76] * 1.5

    def test_sufficient_draft_classes_for_loocv(self):
        rows = wr_pick75_viability_rows()
        years = {r.draft_year for r in rows}
        assert len(years) >= 2


# ---------------------------------------------------------------------------
# Scenario 3: RB Day-2 / Day-3 drop
# ---------------------------------------------------------------------------

class TestRBDay2Day3DropFixture:
    def test_bucketed_cliff_at_day3_boundary(self):
        """position_bucketed must score pick 65 dramatically lower than pick 64."""
        from tests.fixtures.draft_capital_bakeoff import _rb_bucketed_score
        cliff = _rb_bucketed_score(64) - _rb_bucketed_score(65)
        assert cliff > 30.0, f"Expected large Day-3 cliff, got {cliff}"

    def test_realized_value_collapses_at_day3(self):
        from tests.fixtures.draft_capital_bakeoff import _RB_DROP_REALIZED
        assert _RB_DROP_REALIZED[52] > _RB_DROP_REALIZED[65] * 2.0

    def test_all_required_candidates_available(self):
        for candidate in ["current_engine_a_baseline", "log_decay",
                          "position_bucketed", "position_isotonic_step"]:
            rows = rb_day2_day3_drop_rows(candidate=candidate)
            assert rows
            assert all(r.candidate_name == candidate for r in rows)

    def test_four_draft_classes_present(self):
        rows = rb_day2_day3_drop_rows()
        assert len({r.draft_year for r in rows}) == 4


# ---------------------------------------------------------------------------
# Scenario 4: TE small-cohort — null metric guard
# ---------------------------------------------------------------------------

class TestTESmallCohortFixture:
    def test_fewer_than_five_tes_per_fold_test_year(self):
        rows = te_small_cohort_rows()
        folds = build_loocv_folds(rows, candidate_name="position_bucketed", position="TE")
        for fold in folds:
            assert len(fold.test_rows) < 5, (
                f"Expected n < 5 per fold for TE small-cohort; got {len(fold.test_rows)}"
            )

    def test_loocv_returns_none_metrics_for_small_te_cohort(self):
        rows = te_small_cohort_rows()
        result = evaluate_candidate_loocv(rows, candidate_name="position_bucketed", position="TE")
        for fold in result.folds:
            assert fold.within_class_kendall_tau is None, (
                "LOOCV must return None for Kendall τ when test fold has < 5 rows"
            )
            assert fold.within_class_spearman_rho is None

    def test_mean_metrics_are_none_when_all_folds_null(self):
        rows = te_small_cohort_rows()
        result = evaluate_candidate_loocv(rows, candidate_name="position_bucketed", position="TE")
        assert result.mean_kendall_tau is None
        assert result.mean_spearman_rho is None

    def test_only_two_draft_classes(self):
        rows = te_small_cohort_rows()
        assert {r.draft_year for r in rows} == {2021, 2022}


# ---------------------------------------------------------------------------
# Scenario 5: All candidates — comparative score behavior
# ---------------------------------------------------------------------------

class TestAllCandidatesComparison:
    def test_all_four_candidates_present(self):
        rows = all_candidates_qb_rows()
        names = {r.candidate_name for r in rows}
        assert names == {
            "current_engine_a_baseline",
            "log_decay",
            "position_bucketed",
            "position_isotonic_step",
        }

    def test_step_candidates_score_pick1_higher_than_pick16_by_large_margin(self):
        """Step candidates must show a large pick-1 vs pick-16 spread."""
        for candidate in ("position_bucketed", "position_isotonic_step"):
            scores = all_candidates_qb_rows()
            year2019 = [r for r in scores if r.candidate_name == candidate and r.draft_year == 2019]
            by_pick = {int(r.player_id.split("pick")[1].split("_")[0]): r.predicted_score
                       for r in year2019}
            tier_gap = by_pick[1] - by_pick[16]
            assert tier_gap > 30.0, (
                f"{candidate}: pick-1 vs pick-16 gap {tier_gap:.1f} should exceed 30 points"
            )

    def test_log_decay_smooths_over_tier_boundary(self):
        """log_decay must show a smaller pick-15/16 gap than bucketed."""
        scores_15 = candidate_scores_at_pick(15)
        scores_16 = candidate_scores_at_pick(16)
        bucketed_cliff = scores_15.position_bucketed - scores_16.position_bucketed
        log_cliff = scores_15.log_decay - scores_16.log_decay
        assert bucketed_cliff > log_cliff * 5

    def test_baseline_and_log_decay_are_monotone_across_all_picks(self):
        all_picks = sorted(_QB_CLIFF_PICKS)
        for candidate in ("current_engine_a_baseline", "log_decay"):
            rows_2019 = [r for r in all_candidates_qb_rows()
                         if r.candidate_name == candidate and r.draft_year == 2019]
            by_pick = {int(r.player_id.split("pick")[1].split("_")[0]): r.predicted_score
                       for r in rows_2019}
            for i in range(len(all_picks) - 1):
                assert by_pick[all_picks[i]] > by_pick[all_picks[i + 1]], (
                    f"{candidate}: score at pick {all_picks[i]} must exceed pick {all_picks[i+1]}"
                )


# ---------------------------------------------------------------------------
# Scenario 6: Market-derived source field rejection
# ---------------------------------------------------------------------------

class TestMarketContaminatedRowRejection:
    @pytest.mark.parametrize("source_fields", _MARKET_CONTAMINATED_SOURCE_FIELDS)
    def test_single_contaminated_row_is_rejected_by_loocv(self, source_fields):
        """Any prohibited market field in source_fields must raise DraftClassLOOCVError."""
        clean = wr_pick75_viability_rows(candidate="position_bucketed")
        dirty_row = market_contaminated_row(source_fields=source_fields)
        # Replace one clean row with a dirty one to keep multi-class structure
        rows = clean[:-1] + [dirty_row]
        with pytest.raises(DraftClassLOOCVError, match="market"):
            build_loocv_folds(rows, candidate_name="position_bucketed", position="WR")

    def test_clean_cohort_does_not_raise(self):
        rows = wr_pick75_viability_rows(candidate="position_bucketed")
        folds = build_loocv_folds(rows, candidate_name="position_bucketed", position="WR")
        assert folds

    def test_contaminated_cohort_helper_contains_prohibited_field(self):
        rows = market_contaminated_cohort(source_fields=("ktc_value",))
        dirty = [r for r in rows if r.source_fields]
        assert dirty
        assert "ktc_value" in dirty[0].source_fields


# ---------------------------------------------------------------------------
# Scenario 7: Single draft class — LOOCV requires ≥ 2 classes
# ---------------------------------------------------------------------------

class TestInsufficientDraftClasses:
    def test_single_class_raises_loocv_error(self):
        rows = single_class_rows()
        assert {r.draft_year for r in rows} == {2022}
        with pytest.raises(DraftClassLOOCVError, match="at least two draft classes"):
            build_loocv_folds(rows, candidate_name="position_bucketed", position="WR")

    def test_two_classes_does_not_raise(self):
        year1 = single_class_rows()
        year2 = [
            DraftClassEvaluationRow(
                candidate_name=r.candidate_name,
                player_id=r.player_id.replace("2022", "2023"),
                position=r.position,
                draft_year=2023,
                predicted_score=r.predicted_score,
                realized_value=r.realized_value,
            )
            for r in year1
        ]
        folds = build_loocv_folds(year1 + year2, candidate_name="position_bucketed", position="WR")
        assert len(folds) == 2


# ---------------------------------------------------------------------------
# Fixture-level structural invariants
# ---------------------------------------------------------------------------

class TestFixtureStructuralInvariants:
    def test_all_player_ids_unique_within_candidate_and_year(self):
        for factory in [qb_top15_cliff_rows, wr_pick75_viability_rows, rb_day2_day3_drop_rows]:
            rows = factory()
            ids = [r.player_id for r in rows]
            assert len(ids) == len(set(ids)), f"Duplicate player_ids in {factory.__name__}"

    def test_no_market_fields_in_clean_fixtures(self):
        for factory in [qb_top15_cliff_rows, wr_pick75_viability_rows,
                        rb_day2_day3_drop_rows, te_small_cohort_rows]:
            for row in factory():
                assert row.source_fields == (), (
                    f"Clean fixture {factory.__name__} must not carry source_fields"
                )

    def test_all_predicted_scores_are_finite(self):
        for factory in [qb_top15_cliff_rows, wr_pick75_viability_rows,
                        rb_day2_day3_drop_rows, te_small_cohort_rows]:
            for row in factory():
                assert math.isfinite(row.predicted_score), (
                    f"NaN/Inf in predicted_score: {row}"
                )

    def test_all_realized_values_non_negative(self):
        for factory in [qb_top15_cliff_rows, wr_pick75_viability_rows,
                        rb_day2_day3_drop_rows, te_small_cohort_rows]:
            for row in factory():
                assert row.realized_value >= 0.0
