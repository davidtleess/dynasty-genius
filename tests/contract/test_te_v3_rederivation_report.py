from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

REPORT_PATH = Path("docs/validation/2026-06-26-te-v3-rederivation-report.json")
EXPECTED_FEATURES = {
    "age",
    "aging_curve_value",
    "games_t",
    "ppg_t",
    "ppg_t_minus_1",
    "ppg_t_minus_1_available",
    "ppg_t_minus_2",
    "ppg_t_minus_2_available",
    "snap_share",
    "snap_share_t_minus_1",
    "snap_share_t_minus_1_available",
    "tprr",
    "weighted_opportunity",
    "yprr",
}


def _load_report() -> dict:
    assert REPORT_PATH.exists(), f"Missing re-derivation report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _assert_report_acceptable(report: dict) -> None:
    required = {
        "provenance",
        "gates",
        "metrics",
        "accuracy_vs_te_v2",
        "justification",
        "decision_supported",
        "caveats",
    }
    assert required <= set(report)
    assert report["decision_supported"] is False

    gates = report["gates"]
    assert gates["g1_rank_correlation_pass"] is True
    assert gates["g2_rmse_stability_pass"] is True
    assert gates["g2_rmse_max_deviation_pct"] <= 25.0
    assert gates["overall_grade"] == "ACTIVE_B"
    assert gates["g3_market_superiority_pass"] == "deferred"

    provenance = report["provenance"]
    assert provenance["position"] == "TE"
    assert provenance["model_version"] == "engine_b_v3_te_rederived_clean"
    assert provenance["seed_sha256"] and len(provenance["seed_sha256"]) == 64
    assert provenance["new_pkl_sha256"] and len(provenance["new_pkl_sha256"]) == 64
    assert provenance["new_manifest_sha256"] and len(provenance["new_manifest_sha256"]) == 64
    assert set(provenance["feature_set"]) == EXPECTED_FEATURES
    assert len(provenance["feature_set"]) == 14
    assert "te_role_is_risk_profile" not in provenance["feature_set"]

    metrics = report["metrics"]
    assert {"current_full", "rederived_14f_alpha100", "legacy_te_v2"} <= set(metrics)
    assert metrics["rederived_14f_alpha100"]["n_features"] == 14
    assert metrics["rederived_14f_alpha100"]["alpha"] == 100.0

    accuracy = report["accuracy_vs_te_v2"]
    assert accuracy["within_bca_noise"] is True
    rmse_ci = accuracy["rmse_delta_bca_ci95"]
    assert len(rmse_ci) == 2
    assert rmse_ci[0] <= 0.0 <= rmse_ci[1]
    assert accuracy["accuracy_lift_claimed"] is False

    justification = report["justification"]
    assert justification["basis"] == "g2_stability_only"
    assert justification["role_risk_dropped_as_contamination_artifact"] is True
    assert justification["accuracy_edge_beyond_noise"] is False

    caveats = set(report["caveats"])
    assert "local_only_model_artifact" in caveats
    assert "pvo_regen_deferred" in caveats
    assert "g3_market_superiority_deferred" in caveats


def test_te_v3_rederivation_report_schema_and_required_sections() -> None:
    _assert_report_acceptable(_load_report())


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("gates", "g1_rank_correlation_pass"), False),
        (("gates", "g2_rmse_stability_pass"), False),
        (("gates", "g2_rmse_max_deviation_pct"), 25.01),
        (("gates", "overall_grade"), "EXPERIMENTAL"),
        (("gates", "g3_market_superiority_pass"), True),
        (("decision_supported",), True),
        (("accuracy_vs_te_v2", "within_bca_noise"), False),
        (("accuracy_vs_te_v2", "accuracy_lift_claimed"), True),
        (("justification", "basis"), "accuracy_lift"),
    ],
)
def test_te_v3_rederivation_report_fails_closed_on_gate_or_honesty_drift(
    path: tuple[str, ...],
    bad_value: object,
) -> None:
    report = _load_report()
    mutated = copy.deepcopy(report)
    cursor = mutated
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = bad_value

    with pytest.raises(AssertionError):
        _assert_report_acceptable(mutated)
