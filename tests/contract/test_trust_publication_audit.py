from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)

POSITIONS = ("QB", "RB", "WR", "TE")


def _audit_module():
    try:
        from scripts.validate_trust_publication import (  # noqa: PLC0415
            TrustPublicationAuditError,
            validate_trust_publication_t1,
        )
    except ModuleNotFoundError as exc:
        pytest.fail(f"T1 publication audit module missing: {exc}")

    return TrustPublicationAuditError, validate_trust_publication_t1


def _audit_t2_module():
    try:
        from scripts.validate_trust_publication import (  # noqa: PLC0415
            TrustPublicationAuditError,
            validate_trust_publication_t2,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"T2 publication audit module missing: {exc}")

    return TrustPublicationAuditError, validate_trust_publication_t2


def _artifact(position: str) -> BacktestResult:
    return BacktestResult(
        run_id=uuid4(),
        run_date=datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc),
        git_sha="abcdef1",
        model_version="engine_b_v2",
        model_artifact_hash=f"{position.lower()}-hash",
        position=position,  # type: ignore[arg-type]
        ridge_alpha=500.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=[
            FoldResult(
                fold_index=1,
                train_years=[2018, 2019],
                test_year=2020,
                outcome_seasons=[2021, 2022],
                n_train=75,
                n_test=25,
                kendall_tau=0.1,
                kendall_tau_bca_ci95=(-0.1, 0.2),
                spearman_rho=0.2,
                spearman_rho_bca_ci95=(-0.05, 0.3),
                rank_ic=0.2,
                rmse=3.2,
                mae=2.4,
                r2_oos=0.1,
                primary_k=24,
                market_pool_n=25,
                ndcg_diff_primary_k=0.01,
                ndcg_diff_bca_ci95=(-0.03, 0.04),
                ndcg_at_12_model=0.82,
                ndcg_at_12_market=0.81,
                ndcg_at_24_model=0.79,
                ndcg_at_24_market=0.78,
                feature_coefficients={"age": -0.12, "prior_ppg": 0.45},
            )
        ],
        rmse_stability=StabilityResult(
            rmse_per_fold=[3.2],
            rmse_mean=3.2,
            rmse_cv=0.0,
            rmse_max_deviation_pct=0.0,
        ),
        market_source="fc_native",
        market_source_label="fantasycalc_native",
        market_snapshot_dates={2020: "2026-05-31"},
        promotion_gate=GateResult(
            g1_rank_correlation_pass=True,
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade="ACTIVE_B",
            promotion_justification="fixture",
        ),
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_publication(root: Path) -> dict[str, str]:
    pinned: dict[str, str] = {}
    manifest_positions: dict[str, dict[str, object]] = {}

    for position in POSITIONS:
        result = _artifact(position)
        result.save(root)
        pinned[position] = str(result.run_id)
        manifest_positions[position] = {
            "source_validation_note": "G3 validation run, decision support disabled.",
            "run_id": str(result.run_id),
            "run_date": result.run_date.isoformat(),
            "git_sha": result.git_sha,
            "model_version": result.model_version,
            "model_artifact_hash": result.model_artifact_hash,
            "market_source": result.market_source,
            "market_source_label": result.market_source_label,
            "publication_timestamp": "2026-06-10T00:00:00Z",
            "decision_supported": False,
        }

    _write_json(root / "manifest.json", {"positions": manifest_positions})
    return pinned


def _model_card_source_for(root: Path, position: str) -> dict[str, object]:
    artifact = _read_json(root / f"backtest_result_{position}.json")
    return {
        "position": position,
        "backtest_run_id": artifact["run_id"],
        "generated_at": "2026-06-10T00:00:00Z",
        "is_experimental": artifact["promotion_gate"]["overall_grade"] == "EXPERIMENTAL",
        "intended_use": f"{position} model trust context for validation review only.",
        "out_of_scope_uses": ["Roster-action recommendations"],
        "caveats": ["Edge remains unproven while confidence intervals include zero."],
        "known_failure_modes": ["Small validation cohorts can make rank metrics unstable."],
        "model_version": artifact["model_version"],
        "model_artifact_hash": artifact["model_artifact_hash"],
        "git_sha": artifact.get("git_sha"),
    }


def _write_model_card_sources(root: Path) -> None:
    for position in POSITIONS:
        _write_json(
            root / f"model_card_source_{position}.json",
            _model_card_source_for(root, position),
        )


def _assert_audit_fails(root: Path, pinned: dict[str, str], pattern: str) -> None:
    AuditError, validate_t1 = _audit_module()

    with pytest.raises(AuditError, match=pattern):
        validate_t1(root, pinned_run_ids=pinned)


def _assert_t2_audit_fails(root: Path, pinned: dict[str, str], pattern: str) -> None:
    AuditError, validate_t2 = _audit_t2_module()

    with pytest.raises(AuditError, match=pattern):
        validate_t2(root, pinned_run_ids=pinned)


def test_t1_publication_audit_accepts_well_formed_pinned_publication(tmp_path: Path) -> None:
    _, validate_t1 = _audit_module()
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)

    result = validate_t1(root, pinned_run_ids=pinned)

    assert result["status"] == "pass"
    assert result["positions"] == list(POSITIONS)
    assert result["allowed_files"] == [
        "backtest_result_QB.json",
        "backtest_result_RB.json",
        "backtest_result_TE.json",
        "backtest_result_WR.json",
        "manifest.json",
    ]


def test_t1_publication_audit_fails_when_position_artifact_missing(tmp_path: Path) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    (root / "backtest_result_TE.json").unlink()

    _assert_audit_fails(root, pinned, "missing.*TE")


def test_t1_publication_audit_fails_when_artifact_cannot_load(tmp_path: Path) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    (root / "backtest_result_QB.json").write_text("{bad-json", encoding="utf-8")

    _assert_audit_fails(root, pinned, "load.*QB")


def test_t1_publication_audit_fails_on_schema_invalid_artifact(tmp_path: Path) -> None:
    """JSON-valid but schema-invalid artifacts (missing required field) hard-stop."""
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    artifact = _read_json(root / "backtest_result_QB.json")
    del artifact["promotion_gate"]  # required BacktestResult field
    _write_json(root / "backtest_result_QB.json", artifact)

    _assert_audit_fails(root, pinned, "load.*QB")


def test_t1_publication_audit_fails_when_manifest_run_id_is_not_pinned(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    manifest = _read_json(root / "manifest.json")
    manifest["positions"]["RB"]["run_id"] = str(uuid4())
    _write_json(root / "manifest.json", manifest)

    _assert_audit_fails(root, pinned, "pinned.*RB")


@pytest.mark.parametrize("target", ["artifact", "manifest"])
def test_t1_publication_audit_fails_on_decision_supported_true(
    tmp_path: Path,
    target: str,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)

    if target == "artifact":
        artifact = _read_json(root / "backtest_result_WR.json")
        artifact["decision_supported"] = True
        _write_json(root / "backtest_result_WR.json", artifact)
    else:
        manifest = _read_json(root / "manifest.json")
        manifest["positions"]["WR"]["decision_supported"] = True
        _write_json(root / "manifest.json", manifest)

    _assert_audit_fails(root, pinned, "decision_supported.*WR")


def test_t1_publication_audit_allows_market_comparison_fields(
    tmp_path: Path,
) -> None:
    _, validate_t1 = _audit_module()
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)

    result = validate_t1(root, pinned_run_ids=pinned)

    assert result["status"] == "pass"


@pytest.mark.parametrize(
    ("field", "token"),
    [
        ("feature_coefficients", "ktc_signal"),
        ("model_feature_list", "fantasycalc_value"),
    ],
)
def test_t1_publication_audit_fails_on_market_derived_model_input_tokens(
    tmp_path: Path,
    field: str,
    token: str,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    artifact = _read_json(root / "backtest_result_QB.json")

    if field == "feature_coefficients":
        artifact["folds"][0]["feature_coefficients"][token] = 0.99
    else:
        artifact[field] = [token, "age"]

    _write_json(root / "backtest_result_QB.json", artifact)

    _assert_audit_fails(root, pinned, f"market-derived.*{token}")


def test_t1_publication_audit_fails_on_unallowlisted_tracked_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_json(root / "runs" / "raw_backtest_result_QB.json", {"leak": True})

    _assert_audit_fails(root, pinned, "unallowlisted.*raw_backtest_result_QB")


def test_t2_publication_audit_accepts_nine_file_published_substrate(
    tmp_path: Path,
) -> None:
    _, validate_t2 = _audit_t2_module()
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)

    result = validate_t2(root, pinned_run_ids=pinned)

    assert result["status"] == "pass"
    assert result["positions"] == list(POSITIONS)
    assert result["allowed_files"] == [
        "backtest_result_QB.json",
        "backtest_result_RB.json",
        "backtest_result_TE.json",
        "backtest_result_WR.json",
        "manifest.json",
        "model_card_source_QB.json",
        "model_card_source_RB.json",
        "model_card_source_TE.json",
        "model_card_source_WR.json",
    ]


@pytest.mark.parametrize(
    ("field", "bad_value", "pattern"),
    [
        ("position", "RB", "position.*QB"),
        ("backtest_run_id", "stale-run", "backtest_run_id.*QB"),
        ("model_version", "stale-version", "model_version.*QB"),
        ("model_artifact_hash", "stale-hash", "model_artifact_hash.*QB"),
        ("git_sha", "stale-sha", "git_sha.*QB"),
    ],
)
def test_t2_publication_audit_fails_on_model_card_provenance_mismatch(
    tmp_path: Path,
    field: str,
    bad_value: str,
    pattern: str,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)
    source = _read_json(root / "model_card_source_QB.json")
    source[field] = bad_value
    _write_json(root / "model_card_source_QB.json", source)

    _assert_t2_audit_fails(root, pinned, pattern)


@pytest.mark.parametrize(
    "leaked_key",
    ["metrics", "feature_list", "subgroup_results", "calibration", "ethical_considerations"],
)
def test_t2_publication_audit_fails_on_nine_section_model_card_leakage(
    tmp_path: Path,
    leaked_key: str,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)
    source = _read_json(root / "model_card_source_WR.json")
    source[leaked_key] = {"leak": True}
    _write_json(root / "model_card_source_WR.json", source)

    _assert_t2_audit_fails(root, pinned, f"curated.*{leaked_key}")


def test_t2_publication_audit_fails_on_model_card_decision_supported_true(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)
    source = _read_json(root / "model_card_source_TE.json")
    source["decision_supported"] = True
    _write_json(root / "model_card_source_TE.json", source)

    _assert_t2_audit_fails(root, pinned, "decision_supported.*TE")


def test_t2_publication_audit_fails_on_unallowlisted_file_after_sources(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)
    _write_json(root / "TE_model_card.json", {"old_shape": True})

    _assert_t2_audit_fails(root, pinned, "unallowlisted.*TE_model_card")


@pytest.mark.parametrize("missing_field", ["caveats", "intended_use", "model_version"])
def test_t2_publication_audit_fails_on_missing_required_source_field(
    tmp_path: Path,
    missing_field: str,
) -> None:
    """A model card source missing a required field hard-stops (no runtime KeyError)."""
    root = tmp_path / "trust_surface" / "latest"
    pinned = _write_publication(root)
    _write_model_card_sources(root)
    source = _read_json(root / "model_card_source_QB.json")
    del source[missing_field]
    _write_json(root / "model_card_source_QB.json", source)

    _assert_t2_audit_fails(root, pinned, f"{missing_field}.*QB")
