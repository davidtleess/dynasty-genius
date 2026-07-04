"""BUILD-1 Increment 2 RED: expand the tier-readiness registry.

This test file is intentionally scoped to registry + tripwire behavior for the
second graduation increment. It does not require gitignored producer artifacts
or change tier-readiness machinery.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes.system_tier_readiness_models import load_tier_readiness

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "app" / "config" / "tier_readiness.json"
OPENAPI_PATH = REPO_ROOT / "frontend" / "openapi.json"

EXPECTED_SURFACES = [
    "roster_capacity",
    "daily_what_changed",
    "model_trust_console",
    "trade_lab",
    "league_pulse",
]
EXPECTED_NEW_ROUTES = {
    "daily_what_changed": ["/api/league/what-changed"],
    "model_trust_console": [
        "/api/trust-surface/{position}",
        "/api/trust-surface/{position}/model-card",
    ],
    "league_pulse": ["/api/league/pulse"],
}
EXPECTED_TRUST_PRODUCERS = {
    "app/data/backtest/trust_surface/latest/backtest_result_QB.json",
    "app/data/backtest/trust_surface/latest/backtest_result_RB.json",
    "app/data/backtest/trust_surface/latest/backtest_result_TE.json",
    "app/data/backtest/trust_surface/latest/backtest_result_WR.json",
    "app/data/backtest/trust_surface/latest/model_card_source_QB.json",
    "app/data/backtest/trust_surface/latest/model_card_source_RB.json",
    "app/data/backtest/trust_surface/latest/model_card_source_TE.json",
    "app/data/backtest/trust_surface/latest/model_card_source_WR.json",
    "app/data/backtest/trust_surface/latest/manifest.json",
}


def test_registry_names_ratified_surfaces_and_routes_exist_in_openapi() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)
    openapi_paths = set(json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["paths"])

    assert [surface.surface_id for surface in registry.surfaces] == EXPECTED_SURFACES
    surfaces = {surface.surface_id: surface for surface in registry.surfaces}
    for surface_id, route_ids in EXPECTED_NEW_ROUTES.items():
        assert surfaces[surface_id].route_ids == route_ids
        assert set(route_ids).issubset(openapi_paths)


def test_increment2_evidence_exists_and_producers_remain_runtime_status_inputs() -> None:
    registry = load_tier_readiness(registry_path=REGISTRY_PATH, repo_root=REPO_ROOT)
    surfaces = {
        surface.surface_id: surface
        for surface in registry.surfaces
        if surface.surface_id in {"daily_what_changed", "model_trust_console"}
    }

    what_changed = surfaces["daily_what_changed"]
    assert what_changed.producer_artifacts == [
        "app/data/what_changed/what_changed_latest_report.json"
    ]
    trust = surfaces["model_trust_console"]
    assert set(trust.producer_artifacts) == EXPECTED_TRUST_PRODUCERS

    for surface in surfaces.values():
        evidence_paths = {
            evidence
            for component in surface.gate_components
            for evidence in component.evidence
        }
        assert set(surface.producer_artifacts).isdisjoint(evidence_paths)
        for evidence in evidence_paths:
            assert (REPO_ROOT / evidence).exists(), evidence


def test_increment2_what_changed_evidence_locks_semantic_tokens() -> None:
    wc_frontend = (
        REPO_ROOT / "frontend/src/what-changed/DailyWhatChanged.test.tsx"
    ).read_text(encoding="utf-8")
    wc_engine = (
        REPO_ROOT / "tests/contract/test_daily_what_changed_diff_engine.py"
    ).read_text(encoding="utf-8")
    wc_api = (REPO_ROOT / "tests/contract/test_daily_what_changed_api.py").read_text(
        encoding="utf-8"
    )

    assert "dynasty_value_score_delta: -0" in wc_frontend
    assert 'screen.getByText("-0")' in wc_frontend
    assert "semantic_output_hash" in wc_frontend
    assert "semantic_output_hash" in wc_engine
    assert "semantic_output_hash" in wc_api
    assert "player_name: null" in wc_frontend
    assert "model-key-fallback" in wc_frontend
    assert "comparison_window" in wc_frontend
    assert "comparison_window" in wc_engine


def test_increment2_trust_console_evidence_locks_semantic_tokens() -> None:
    modelcard = (
        REPO_ROOT / "tests/contract/test_harness_trust_w3_modelcard.py"
    ).read_text(encoding="utf-8")
    trust_v2 = (REPO_ROOT / "tests/contract/test_trust_surface_v2.py").read_text(
        encoding="utf-8"
    )
    publication = (
        REPO_ROOT / "tests/contract/test_trust_publication_audit.py"
    ).read_text(encoding="utf-8")
    provenance_footer = (
        REPO_ROOT / "frontend/src/trust/ProvenanceFooter.test.jsx"
    ).read_text(encoding="utf-8")

    assert "r2_oos" in modelcard
    assert "r2_oos_mean is None" in modelcard
    assert "kendall_tau_bca_ci95" in modelcard
    assert "spearman_rho_bca_ci95" in modelcard
    assert "model_card_available" in trust_v2
    assert "run_id" in publication
    assert "pinned_run_ids" in publication
    assert "test_t2_publication_audit_fails_on_model_card_provenance_mismatch" in (
        publication
    )
    assert "backtest_run_id.*QB" in publication
    assert "Model trust provenance" in provenance_footer


def test_increment2_null_ratification_reports_awaiting_david_ratification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface("daily_what_changed", ratified_date=None)
    _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry([surface]))
    client = _client_with_temp_registry(monkeypatch, registry_path, tmp_path)

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    surface_body = body["surfaces"][0]
    assert surface_body["surface_id"] == "daily_what_changed"
    assert surface_body["tier_status"] == "not_graduated"
    assert surface_body["basis"] == "awaiting_david_ratification"


def test_increment2_ratified_surfaces_report_limited_active_with_mif_dormant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surfaces = [
        _surface("daily_what_changed", ratified_date="2026-07-02"),
        _surface("model_trust_console", ratified_date="2026-07-02"),
    ]
    for surface in surfaces:
        _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry(surfaces))
    client = _client_with_temp_registry(monkeypatch, registry_path, tmp_path)

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "ok"
    readiness = {surface["surface_id"]: surface for surface in body["surfaces"]}
    for surface_id in ("daily_what_changed", "model_trust_console"):
        surface_body = readiness[surface_id]
        assert surface_body["tier_status"] == "diagnostic_grade_active_limited"
        assert surface_body["basis"] == "readiness_active_with_insufficient_data"
        assert surface_body["insufficient_data_count"] == 1
        assert surface_body["insufficient_data_components"] == ["mif_breaker"]
        mif = next(
            component
            for component in surface_body["components"]
            if component["component"] == "mif_breaker"
        )
        assert mif["component_status"] == "insufficient_data"


def _client_with_temp_registry(
    monkeypatch: pytest.MonkeyPatch,
    registry_path: Path,
    repo_root: Path,
) -> TestClient:
    from app.api.routes import system_tier_readiness

    monkeypatch.setattr(system_tier_readiness, "_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(system_tier_readiness, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(system_tier_readiness, "_MODEL_PROVENANCE_ADAPTER", lambda: "ok")
    monkeypatch.setattr(system_tier_readiness, "_CAPTURE_HEALTH_ADAPTER", lambda: "ok")
    from app.main import app

    return TestClient(app)


def _registry(surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    return {"registry_version": 1, "surfaces": surfaces}


def _surface(surface_id: str, *, ratified_date: str | None) -> dict[str, Any]:
    if surface_id == "daily_what_changed":
        route_ids = ["/api/league/what-changed"]
        producer_artifacts = ["app/data/what_changed/what_changed_latest_report.json"]
        evidence = {
            "audit_hygiene": [
                "tests/contract/test_daily_what_changed_api.py",
                "scripts/scan_league_opportunity_no_verdict.py",
            ],
            "deterministic_range_disclosure": [
                "frontend/src/what-changed/DailyWhatChanged.test.tsx",
                "tests/contract/test_daily_what_changed_diff_engine.py",
            ],
            "no_directive_copy": ["frontend/scripts/check-banned-language.mjs"],
        }
        display_name = "Daily What-Changed"
    elif surface_id == "model_trust_console":
        route_ids = [
            "/api/trust-surface/{position}",
            "/api/trust-surface/{position}/model-card",
        ]
        producer_artifacts = sorted(EXPECTED_TRUST_PRODUCERS)
        evidence = {
            "audit_hygiene": [
                "tests/contract/test_trust_surface_route.py",
                "tests/contract/test_trust_publication_audit.py",
            ],
            "deterministic_range_disclosure": [
                "tests/contract/test_harness_trust_w3_modelcard.py",
                "tests/contract/test_trust_surface_v2.py",
            ],
            "no_directive_copy": [
                "frontend/scripts/check-banned-language.mjs",
                "frontend/src/trust/ProvenanceFooter.test.jsx",
            ],
        }
        display_name = "Model Trust Console"
    else:
        raise AssertionError(f"unsupported fixture surface {surface_id}")

    components = [
        _component("audit_hygiene", evidence["audit_hygiene"]),
        _component("deterministic_range_disclosure", evidence["deterministic_range_disclosure"]),
        _component(
            "mif_breaker",
            [
                "src/dynasty_genius/outcome_loop/realized_outcome_scorer.py",
                "tests/unit/test_realized_outcome_scorer.py",
            ],
        ),
        _component("no_directive_copy", evidence["no_directive_copy"]),
    ]
    return {
        "surface_id": surface_id,
        "display_name": display_name,
        "declared_tier": "tier_1_candidate",
        "route_ids": route_ids,
        "producer_artifacts": producer_artifacts,
        "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
        "gate_components": components,
        "ratified_by": "David",
        "ratified_date": ratified_date,
    }


def _component(component: str, evidence: list[str]) -> dict[str, Any]:
    return {
        "component": component,
        "evidence": evidence,
        "expectation": f"{component} expectation",
        "optional": False,
    }


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _prepare_all_declared_files(repo_root: Path, surface: dict[str, Any]) -> None:
    paths = [
        evidence
        for component in surface["gate_components"]
        for evidence in component["evidence"]
    ]
    paths.extend(surface["producer_artifacts"])
    for rel_path in paths:
        path = repo_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
