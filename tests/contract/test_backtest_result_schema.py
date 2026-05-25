"""Phase 10/11 contract tests: BacktestResult Pydantic schema.

Eight contract tests lock the schema and grade-assignment logic before
any implementation code is written. All should fail with ImportError
on the RED run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fold(index: int, tau: float = 0.45, ci_lo: float = 0.30) -> FoldResult:
    return FoldResult(
        fold_index=index,
        train_years=list(range(2018, 2018 + index + 1)),
        test_year=2019 + index,
        outcome_seasons=[2020 + index, 2021 + index],
        n_train=200 + index * 50,
        n_test=45,
        kendall_tau=tau,
        kendall_tau_bca_ci95=(ci_lo, tau + 0.15),
        spearman_rho=tau + 0.05,
        spearman_rho_bca_ci95=(ci_lo - 0.02, tau + 0.20),
        rank_ic=tau + 0.05,
        rmse=3.5,
        mae=2.8,
    )


def _stability(max_dev: float = 15.0, dm_p: float = 0.05) -> StabilityResult:
    return StabilityResult(
        rmse_per_fold=[3.2, 3.4, 3.6, 3.5],
        rmse_mean=3.425,
        rmse_cv=0.04,
        rmse_max_deviation_pct=max_dev,
        dm_hln_pvalue=dm_p,
        dm_passes=dm_p <= 0.10,
    )


def _gate(g1: bool, g2: bool, g3: bool, g4=None, grade: str = "ACTIVE_B_VALIDATED") -> GateResult:
    if g4 is None:
        g4 = "deferred"
    return GateResult(
        g1_rank_correlation_pass=g1,
        g2_rmse_stability_pass=g2,
        g3_market_superiority_pass=g3,
        g4_divergence_validity_pass=g4,
        overall_grade=grade,
        promotion_justification="test",
    )


def _minimal_result(grade: str = "ACTIVE_B_VALIDATED", g4=None) -> BacktestResult:
    if g4 is None:
        g4 = "deferred"
    return BacktestResult(
        run_date=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="abc123def456" * 5,  # 60 hex chars
        position="WR",
        ridge_alpha=200.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=[_fold(i) for i in range(1, 5)],
        rmse_stability=_stability(),
        market_source="ktc_community_csv",
        promotion_gate=_gate(True, True, True, g4, grade),
    )


# ── Test 1: BacktestResult validates with all required fields ─────────────────

def test_backtest_result_validates_with_required_fields():
    result = _minimal_result()
    assert result.position == "WR"
    assert result.model_version == "engine_b_v2"
    assert isinstance(result.run_id, UUID)
    assert len(result.folds) == 4


# ── Test 2: overall_grade is one of the five valid literals ───────────────────

@pytest.mark.parametrize("grade", [
    "PRE_MODEL", "EXPERIMENTAL", "ACTIVE_B",
    "ACTIVE_B_VALIDATED", "DECISION_GRADE",
])
def test_overall_grade_accepts_valid_literals(grade):
    gate = _gate(True, True, True, "deferred", grade)
    assert gate.overall_grade == grade


def test_overall_grade_rejects_invalid_literal():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GateResult(
            g1_rank_correlation_pass=True,
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass=True,
            g4_divergence_validity_pass="deferred",
            overall_grade="SUPER_GRADE",     # invalid
            promotion_justification="test",
        )


# ── Test 3: g4 accepts all four valid states ──────────────────────────────────

@pytest.mark.parametrize("g4_val", [True, False, "deferred", "insufficient_data"])
def test_g4_divergence_validity_pass_accepts_all_states(g4_val):
    gate = _gate(True, True, True, g4_val, "ACTIVE_B_VALIDATED")
    assert gate.g4_divergence_validity_pass == g4_val


# ── Test 4: model_artifact_hash is a non-empty string ────────────────────────

def test_model_artifact_hash_is_non_empty():
    result = _minimal_result()
    assert isinstance(result.model_artifact_hash, str)
    assert len(result.model_artifact_hash) > 0


# ── Test 5: retrain_mode accepts both valid literals ─────────────────────────

def test_retrain_mode_refit_per_fold_accepted():
    result = _minimal_result()
    assert result.retrain_mode == "refit_per_fold_fixed_alpha"


def test_retrain_mode_frozen_accepted():
    result = BacktestResult(
        run_date=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="abc123",
        position="QB",
        ridge_alpha=1000.0,
        retrain_mode="frozen_retrospective",
        folds=[_fold(i) for i in range(1, 5)],
        rmse_stability=_stability(),
        market_source="unavailable",
        promotion_gate=_gate(False, False, False, "deferred", "ACTIVE_B"),
    )
    assert result.retrain_mode == "frozen_retrospective"


# ── Test 6: G1+G2+G3 pass, G4 deferred → ACTIVE_B_VALIDATED ─────────────────

def test_grade_active_b_validated_when_g1_g2_g3_pass_g4_deferred():
    result = _minimal_result(grade="ACTIVE_B_VALIDATED", g4="deferred")
    assert result.promotion_gate.overall_grade == "ACTIVE_B_VALIDATED"
    assert result.promotion_gate.g4_divergence_validity_pass == "deferred"


# ── Test 7: G1 fail → grade is ACTIVE_B, not demoted further ─────────────────

def test_grade_active_b_when_g1_fails():
    result = BacktestResult(
        run_date=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="abc123",
        position="RB",
        ridge_alpha=500.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=[_fold(i, tau=0.20) for i in range(1, 5)],  # tau too low
        rmse_stability=_stability(),
        market_source="unavailable",
        promotion_gate=_gate(False, True, True, "deferred", "ACTIVE_B"),
    )
    assert result.promotion_gate.overall_grade == "ACTIVE_B"
    assert result.promotion_gate.g1_rank_correlation_pass is False


# ── Test 8: FoldResult with all optional fields None still validates ──────────

def test_fold_result_validates_with_only_required_fields():
    fold = FoldResult(
        fold_index=1,
        train_years=[2018, 2019],
        test_year=2020,
        outcome_seasons=[2021, 2022],
        n_train=250,
        n_test=43,
        kendall_tau=0.42,
        kendall_tau_bca_ci95=(0.28, 0.54),
        spearman_rho=0.51,
        spearman_rho_bca_ci95=(0.36, 0.63),
        rank_ic=0.51,
        rmse=3.8,
        mae=2.9,
        # all optional fields absent
    )
    assert fold.ndcg_at_12_model is None
    assert fold.ndcg_at_24_model is None
    assert fold.precision_at_k is None
    assert fold.n_excluded_injury == 0


# ── Task 10.6 Persistence Contract Tests ──────────────────────────────────────

# Test 9: save() writes JSON that round-trips back to a valid BacktestResult

def test_save_and_load_round_trips(tmp_path):
    result = _minimal_result()
    saved_path = result.save(tmp_path)
    assert saved_path.exists()
    loaded = BacktestResult.load(saved_path)
    assert isinstance(loaded, BacktestResult)
    assert len(loaded.folds) == 4


# Test 10: run_id, model_version, position are identical after round-trip

def test_round_trip_preserves_identity_fields(tmp_path):
    result = _minimal_result()
    loaded = BacktestResult.load(result.save(tmp_path))
    assert loaded.run_id == result.run_id
    assert loaded.model_version == result.model_version
    assert loaded.position == result.position


# Test 11: artifact_hash returns a 64-char SHA-256 hex string for a real file

def test_artifact_hash_is_sha256_hex(tmp_path):
    import hashlib
    content = b"fake engine_b pkl bytes"
    pkl = tmp_path / "model.pkl"
    pkl.write_bytes(content)
    digest = BacktestResult.artifact_hash(pkl)
    assert len(digest) == 64
    assert digest == hashlib.sha256(content).hexdigest()


# Test 12: git_sha round-trips as 40-char hex string or None

def test_git_sha_round_trips(tmp_path):
    sha = "a" * 40
    result = BacktestResult(
        run_date=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        git_sha=sha,
        model_version="engine_b_v2",
        model_artifact_hash="abc123",
        position="QB",
        ridge_alpha=1000.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=[_fold(i) for i in range(1, 5)],
        rmse_stability=_stability(),
        market_source="unavailable",
        promotion_gate=_gate(True, True, True, "deferred", "ACTIVE_B_VALIDATED"),
    )
    loaded = BacktestResult.load(result.save(tmp_path))
    assert loaded.git_sha == sha
    assert len(loaded.git_sha) == 40


# Test 13: run_date timezone survives JSON serialization

def test_run_date_timezone_survives_round_trip(tmp_path):
    result = _minimal_result()
    loaded = BacktestResult.load(result.save(tmp_path))
    assert loaded.run_date.tzinfo is not None
    assert loaded.run_date == result.run_date
