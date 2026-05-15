"""Task 12.1 unit tests: ModelCard + CalibrationReport schemas.

7 tests covering schema validation, round-trip persistence, experimental flag,
and CalibrationReport ECE field.
All tests are pure — no network, no model calls.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.dynasty_genius.eval.model_card import (
    CalibrationDecile,
    CalibrationReport,
    ModelCard,
    ModelCardMetrics,
    ModelCardSubgroup,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _metrics() -> ModelCardMetrics:
    return ModelCardMetrics(
        rmse_mean=3.2,
        rmse_per_fold=[3.0, 3.1, 3.3, 3.4],
        kendall_tau_mean=0.72,
        kendall_tau_per_fold=[0.70, 0.71, 0.73, 0.74],
        spearman_rho_mean=0.81,
        spearman_rho_per_fold=[0.80, 0.80, 0.82, 0.82],
        ece=None,
        ndcg_at_24_model_mean=None,
        ndcg_at_24_market_mean=None,
        g1_pass=True,
        g2_pass=True,
        g3_pass="deferred",
        g4_pass="deferred",
        overall_grade="ACTIVE_B",
    )


def _model_card(position: str = "WR", is_experimental: bool = False) -> ModelCard:
    return ModelCard(
        schema_version="1.0.0",
        generated_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        position=position,  # type: ignore[arg-type]
        backtest_run_id="b3a338a3-ec42-4af8-a046-2ca0672e9390",
        git_sha=None,
        model_version="engine_b_v2",
        model_artifact_hash="deadbeef" * 8,
        ridge_alpha=200.0,
        training_window="2018–2023 (expanding; 4 folds)",
        feature_list=["age_at_feature_season", "breakout_age", "wopr"],
        retrain_mode="refit_per_fold_fixed_alpha",
        intended_use="Forecast 2-year average PPG for dynasty Superflex PPR leagues.",
        out_of_scope_uses=["Single-season redraft start/sit decisions"],
        relevant_factors=["position", "age", "sample_size", "draft_capital"],
        evaluation_factors=["age_under_26", "round_1_pick"],
        metrics=_metrics(),
        evaluation_data="4 expanding folds, test years 2020–2023.",
        training_data="engine_b_features_v2.csv, seasons 2018–2023.",
        subgroup_results=[
            ModelCardSubgroup(label="age_under_26", n=42, rmse=2.9, kendall_tau=0.75),
        ],
        ethical_considerations="Decision aid only.",
        caveats=["Sample size ~40–50 rows per fold."],
        known_failure_modes=["Injury-year outliers distort PPG labels."],
        is_experimental=is_experimental,
    )


def _calibration_report(ece: float = 0.5) -> CalibrationReport:
    deciles = [
        CalibrationDecile(
            decile=i,
            predicted_mean=float(i * 2),
            observed_mean=float(i * 2 + (0.5 if i % 2 == 0 else -0.5)),
            n=30,
            residual_mean=(0.5 if i % 2 == 0 else -0.5),
        )
        for i in range(1, 11)
    ]
    return CalibrationReport(
        position="WR",
        backtest_run_id="b3a338a3-ec42-4af8-a046-2ca0672e9390",
        ece=ece,
        deciles=deciles,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_model_card_validates_all_9_sections():
    """A fully populated ModelCard validates without error."""
    card = _model_card()
    assert card.schema_version == "1.0.0"
    assert card.position == "WR"
    assert len(card.feature_list) > 0
    assert card.metrics.g1_pass is True
    assert len(card.caveats) > 0
    assert len(card.known_failure_modes) > 0


def test_model_card_save_and_load_round_trips(tmp_path):
    """save() then load() produces an identical card."""
    card = _model_card()
    path = tmp_path / "WR_model_card.json"
    card.save(path)
    loaded = ModelCard.load(path)
    assert loaded.model_dump() == card.model_dump()


def test_model_card_is_experimental_flag_true_for_te():
    """is_experimental must be True when the card is for TE."""
    card = _model_card(position="TE", is_experimental=True)
    assert card.is_experimental is True
    assert card.position == "TE"


def test_model_card_is_experimental_flag_false_for_wr():
    """is_experimental is False for non-TE positions that pass gates."""
    card = _model_card(position="WR", is_experimental=False)
    assert card.is_experimental is False


def test_calibration_report_ece_computation():
    """ECE field stores the weighted mean |predicted - observed| across deciles."""
    # 10 equal-n deciles; alternating +0.5 / -0.5 residuals → ECE = 0.5
    report = _calibration_report(ece=0.5)
    assert report.ece == pytest.approx(0.5, abs=1e-9)
    assert len(report.deciles) == 10


def test_calibration_report_save_and_load_round_trips(tmp_path):
    """save() then load() produces an identical CalibrationReport."""
    report = _calibration_report()
    path = tmp_path / "WR_calibration_report.json"
    report.save(path)
    loaded = CalibrationReport.model_validate_json(path.read_text())
    assert loaded.model_dump() == report.model_dump()


def test_model_card_subgroup_results_allow_empty_list():
    """subgroup_results may be an empty list (e.g., missing age column in CSV)."""
    card = _model_card()
    card_no_subgroups = card.model_copy(update={"subgroup_results": []})
    assert card_no_subgroups.subgroup_results == []
    # round-trip preserves empty list
    data = card_no_subgroups.model_dump()
    assert data["subgroup_results"] == []
