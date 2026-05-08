"""Anti-drift guard for the rookie-forecast grader.

Pins three behaviors that protect the grader from out-promoting the planning
docs in docs/validation-gates.md before Step 0.5 ships the full composite
gate measurement script:

1. No position can be promoted to grade B from point-estimate metrics
   alone. The B branch in train_models._model_grade is gated until the
   composite gate components (RMSE stability across rolling holdouts, null
   coverage, caveat hygiene, bootstrap CI lower bounds) actually exist.
2. No position can be promoted to grade A either. validation-gates.md is
   explicit that A is "Currently unattainable; reserved for post-Phase-6
   calibration." A bypass would defeat the entire purpose of the guard.
3. While a position's holdout R² is negative, the statistical caveat
   `negative_r2_lower_bound` is surfaced additively alongside any
   domain-meaning caveats — never replaced.
"""

from app.data.pipeline.train_models import _model_grade, _position_caveats


def test_b_grade_blocked_until_composite_gates_land() -> None:
    # WR's 20260501T014544Z point-estimate metrics would have earned B
    # under the un-guarded grader (r2=0.408, spearman=0.729, top12=0.833,
    # holdout=35). The guard floors them at C until composite gates ship.
    grade = _model_grade(
        position="WR",
        r2=0.408,
        spearman=0.729,
        top_12_hit_rate=0.833,
        holdout_rows=35,
    )
    assert grade == "C", (
        "WR with point-estimate-only metrics must not earn B until Step 0.5 "
        "ships the composite gate measurement script."
    )


def test_a_grade_blocked_until_composite_gates_land() -> None:
    # Synthetic metrics that would clear the un-guarded A branch
    # (r2 >= ceiling*0.7, spearman >= 0.60, top12 >= 0.50, holdout >= 80).
    # validation-gates.md says A is "Currently unattainable; reserved for
    # post-Phase-6 calibration." — point-estimate metrics, no matter how
    # strong, must not promote past C until lower-bound criteria exist.
    grade = _model_grade(
        position="WR",
        r2=0.40,
        spearman=0.65,
        top_12_hit_rate=0.55,
        holdout_rows=120,
    )
    assert grade == "C", (
        "WR with point-estimate-only metrics must not earn A until Step 0.5 "
        "ships the composite gate measurement script (validation-gates.md "
        "reserves A for post-Phase-6 calibration)."
    )


def test_qb_negative_r2_caveat_surfaces_additively() -> None:
    # QB's 20260501T014544Z metrics include r2=-0.208. The guard adds
    # `negative_r2_lower_bound` while preserving the domain caveat
    # `qb_rookie_signal_inherently_low_ceiling` from POSITION_ALWAYS_CAVEATS
    # and the small-sample caveat `low_sample_holdout`.
    caveats = _position_caveats(position="QB", holdout_rows=10, r2=-0.208)
    assert "qb_rookie_signal_inherently_low_ceiling" in caveats
    assert "low_sample_holdout" in caveats
    assert "negative_r2_lower_bound" in caveats


def test_negative_r2_caveat_only_when_r2_negative() -> None:
    # WR with positive r2 must not pick up the negative_r2 caveat.
    caveats = _position_caveats(position="WR", holdout_rows=35, r2=0.408)
    assert "negative_r2_lower_bound" not in caveats


def test_te_caveats_preserve_low_sample_holdout() -> None:
    # TE caveat string must keep low_sample_holdout alongside the
    # additive te_population_per_class_small caveat.
    caveats = _position_caveats(position="TE", holdout_rows=11, r2=0.197)
    assert "te_population_per_class_small" in caveats
    assert "low_sample_holdout" in caveats


def test_qb_grade_remains_d_under_negative_r2() -> None:
    grade = _model_grade(
        position="QB",
        r2=-0.208,
        spearman=0.517,
        top_12_hit_rate=1.0,
        holdout_rows=10,
    )
    assert grade == "D"
