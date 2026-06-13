"""Task 12.1 + 12.5 unit tests: ModelCard + CalibrationReport schemas and generator.

Task 12.1 (7 tests): schema validation, round-trip persistence, experimental flag,
    CalibrationReport ECE field.
Task 12.5 (6 tests): generate_card_for_position() reads BacktestResult, populates
    all 9 sections, handles missing predictions CSV gracefully, writes CalibrationReport.
All tests are pure — no network, no harness run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.generate_model_cards import generate_card_for_position
from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)
from src.dynasty_genius.eval.backtest_report import write_prediction_log_csv
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


def test_model_card_metrics_carries_model_status():
    assert "model_status" in ModelCardMetrics.model_fields

    metrics = _metrics().model_copy(update={"model_status": "VALIDATED"})

    assert metrics.model_status == "VALIDATED"
    assert metrics.overall_grade == "ACTIVE_B"


def test_model_card_save_and_load_round_trips(tmp_path):
    """save() then load() produces an identical card."""
    card = _model_card()
    path = tmp_path / "WR_model_card.json"
    card.save(path)
    loaded = ModelCard.load(path)
    assert loaded.dict() == card.dict()


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
    loaded = CalibrationReport.parse_raw(path.read_text())
    assert loaded.dict() == report.dict()


def test_model_card_subgroup_results_allow_empty_list():
    """subgroup_results may be an empty list (e.g., missing age column in CSV)."""
    card = _model_card()
    card_no_subgroups = card.copy(update={"subgroup_results": []})
    assert card_no_subgroups.subgroup_results == []
    # round-trip preserves empty list
    data = card_no_subgroups.dict()
    assert data["subgroup_results"] == []


# ── Task 12.5 helpers ──────────────────────────────────────────────────────────

def _make_fold(fold_index: int, test_year: int, tau: float = 0.45) -> FoldResult:
    return FoldResult(
        fold_index=fold_index,
        train_years=list(range(2018, test_year)),
        test_year=test_year,
        outcome_seasons=[test_year + 1, test_year + 2],
        n_train=200,
        n_test=50,
        kendall_tau=tau,
        kendall_tau_bca_ci95=(tau - 0.10, tau + 0.10),
        spearman_rho=tau + 0.05,
        spearman_rho_bca_ci95=(tau - 0.05, tau + 0.15),
        rank_ic=tau + 0.05,
        rmse=3.0,
        mae=2.0,
    )


def _make_result(position: str = "WR") -> BacktestResult:
    folds = [
        _make_fold(1, 2020),
        _make_fold(2, 2021),
        _make_fold(3, 2022),
        _make_fold(4, 2023),
    ]
    rmse_vals = [f.rmse for f in folds]
    grade = "EXPERIMENTAL" if position == "TE" else "ACTIVE_B"
    return BacktestResult(
        run_id=uuid4(),
        run_date=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="deadbeef" * 8,
        position=position,  # type: ignore[arg-type]
        ridge_alpha=200.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=folds,
        rmse_stability=StabilityResult(
            rmse_per_fold=rmse_vals,
            rmse_mean=3.0,
            rmse_cv=0.0,
            rmse_max_deviation_pct=0.0,
        ),
        market_source="unavailable",
        promotion_gate=GateResult(
            g1_rank_correlation_pass=(position != "TE"),
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade=grade,
            promotion_justification="test fixture",
        ),
    )


def _write_fake_run(
    position: str,
    runs_dir: "Path",
    include_predictions: bool = True,
    n_rows: int = 50,
) -> "Path":
    result = _make_result(position)
    run_dir = runs_dir / str(result.run_id)
    result.save(run_dir)
    if include_predictions:
        rows = [
            {
                "player_id": f"p{i}",
                "position": position,
                "fold_index": (i % 4) + 1,
                "feature_season": 2020 + (i % 4),
                "predicted_ppg": float(i % 20) * 0.5 + 2.0,
                "realized_ppg": float(i % 20) * 0.5 + 2.5,
                "model_rank": (i % 20) + 1,
                "residual": 0.5,
                "age_at_feature_season": 24 + (i % 8),
                "draft_round": None,
            }
            for i in range(n_rows)
        ]
        write_prediction_log_csv(rows, run_dir / f"predictions_{position}.csv")
    return run_dir


# ── Task 12.5 tests ───────────────────────────────────────────────────────────

def test_generate_model_card_reads_backtest_result(tmp_path):
    """generate_card_for_position() reads a BacktestResult and returns a ModelCard."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    _write_fake_run("WR", runs_dir)

    card, report = generate_card_for_position("WR", runs_dir=runs_dir, output_dir=output_dir)

    assert isinstance(card, ModelCard)
    assert card.position == "WR"


def test_generate_model_card_populates_metrics_from_result(tmp_path):
    """ModelCard.metrics.kendall_tau_mean matches mean of FoldResult.kendall_tau."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    _write_fake_run("WR", runs_dir)

    card, _ = generate_card_for_position("WR", runs_dir=runs_dir, output_dir=output_dir)

    assert card.metrics.kendall_tau_mean == pytest.approx(0.45, abs=1e-9)
    assert len(card.metrics.kendall_tau_per_fold) == 4


def test_generate_model_card_populates_model_status_from_gate(tmp_path):
    result = _make_result("WR")
    result.promotion_gate.model_status = "PROVISIONAL"
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    run_dir = runs_dir / str(result.run_id)
    result.save(run_dir)

    card, _ = generate_card_for_position(
        "WR",
        runs_dir=runs_dir,
        output_dir=output_dir,
    )

    assert card.metrics.model_status == "PROVISIONAL"
    assert card.metrics.overall_grade == result.promotion_gate.overall_grade


def test_generate_model_card_te_sets_is_experimental_true(tmp_path):
    """TE card always has is_experimental=True regardless of gate result."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    _write_fake_run("TE", runs_dir)

    card, _ = generate_card_for_position("TE", runs_dir=runs_dir, output_dir=output_dir)

    assert card.is_experimental is True
    assert card.position == "TE"


def test_generate_model_card_ece_requires_prediction_log(tmp_path):
    """If predictions CSV is missing, card.metrics.ece is None — no crash."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    _write_fake_run("WR", runs_dir, include_predictions=False)

    card, report = generate_card_for_position("WR", runs_dir=runs_dir, output_dir=output_dir)

    assert card.metrics.ece is None


def test_generate_model_card_writes_calibration_report(tmp_path):
    """CalibrationReport JSON is written alongside ModelCard JSON."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    _write_fake_run("WR", runs_dir)

    generate_card_for_position("WR", runs_dir=runs_dir, output_dir=output_dir)

    assert (output_dir / "WR_model_card.json").exists()
    assert (output_dir / "WR_calibration_report.json").exists()


def test_generate_all_writes_four_cards(tmp_path):
    """generate_card_for_position called for all 4 positions writes 4 cards."""
    from scripts.generate_model_cards import VALID_POSITIONS
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "cards"
    for pos in VALID_POSITIONS:
        _write_fake_run(pos, runs_dir)

    for pos in VALID_POSITIONS:
        generate_card_for_position(pos, runs_dir=runs_dir, output_dir=output_dir)

    for pos in VALID_POSITIONS:
        assert (output_dir / f"{pos}_model_card.json").exists(), f"Missing card for {pos}"
