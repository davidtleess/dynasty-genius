"""BUILD-1 T3 RED: tier-readiness live adapters and HTTP route.

These tests use temp registries, temp repo roots, and injected live-precondition
adapters only. They do not read the real tier-readiness registry, call sibling
system routes over HTTP, inspect real gitignored artifacts, or assert the T4 CI
tripwire / OpenAPI generation contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

BANNED_RESPONSE_RE = re.compile(
    r"\b(certified|validated|trusted|approved|safe|recommended|buy|sell|hold|start|sit)\b",
    re.IGNORECASE,
)


def _route_module():
    from app.api.routes import system_tier_readiness

    return system_tier_readiness


def _client_with_temp_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    registry_path: Path,
    repo_root: Path,
    model_provenance_status: str = "ok",
    capture_health_status: str = "ok",
) -> TestClient:
    route = _route_module()
    monkeypatch.setattr(route, "_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(route, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(route, "_MODEL_PROVENANCE_ADAPTER", lambda: model_provenance_status)
    monkeypatch.setattr(route, "_CAPTURE_HEALTH_ADAPTER", lambda: capture_health_status)
    from app.main import app

    return TestClient(app)


def _component(
    component: str,
    evidence: list[str],
    *,
    optional: bool = False,
) -> dict[str, Any]:
    return {
        "component": component,
        "evidence": evidence,
        "expectation": f"{component} expectation",
        "optional": optional,
    }


def _surface(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    surface = {
        "surface_id": "roster_capacity",
        "display_name": "Roster Capacity",
        "declared_tier": "tier_1_candidate",
        "route_ids": ["/api/roster/capacity"],
        "producer_artifacts": [
            "app/data/roster_capacity/roster_capacity_latest.json"
        ],
        "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
        "gate_components": [
            _component(
                "audit_hygiene",
                [
                    "tests/contract/test_roster_capacity_route.py",
                    "scripts/scan_league_opportunity_no_verdict.py",
                ],
            ),
            _component(
                "deterministic_range_disclosure",
                ["tests/contract/test_roster_capacity_route.py"],
            ),
            _component(
                "mif_breaker",
                ["src/dynasty_genius/realized_outcome/scorer.py"],
            ),
            _component(
                "no_directive_copy",
                ["frontend/scripts/check-banned-language.mjs"],
            ),
        ],
        "ratified_by": "David",
        "ratified_date": "2026-07-02",
    }
    if overrides:
        surface.update(overrides)
    return surface


def _trade_lab_surface(
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    surface = {
        "surface_id": "trade_lab",
        "display_name": "Trade Lab",
        "declared_tier": "tier_1_candidate",
        "route_ids": [
            "/api/trade/reconcile",
            "/api/trade/reconcile/market",
            "/api/trade/assets",
        ],
        "producer_artifacts": [
            "app/data/valuation/universe_pvo_latest.json",
            "app/data/league_snapshots/sleeper_universe_snapshot_latest.json",
        ],
        "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
        "gate_components": [
            _component(
                "audit_hygiene",
                [
                    "tests/contract/test_phase15_trade_lab.py",
                    "tests/contract/test_phase23_w5.py",
                    "tests/contract/test_phase23_w5b_route.py",
                ],
            ),
            _component(
                "deterministic_range_disclosure",
                [
                    "frontend/src/trade/TradeLabMitigation.test.jsx",
                    "frontend/src/trade/lanes.test.jsx",
                    "frontend/src/trade/forced_cut_range.test.jsx",
                ],
            )
            | {
                "expectation": (
                    "trade_lab_fe_mitigation_v1: exact mitigation copy, equal "
                    "model/market visual weight, separate result lanes, and "
                    "range-native no blended delta"
                )
            },
            _component(
                "mif_breaker",
                ["src/dynasty_genius/outcome_loop/realized_outcome_scorer.py"],
            ),
            _component(
                "no_directive_copy",
                [
                    "frontend/scripts/check-banned-language.mjs",
                    "frontend/src/trade/favors_guard.test.jsx",
                ],
            ),
        ],
        "ratified_by": "David",
        "ratified_date": "2026-07-04",
    }
    if overrides:
        surface.update(overrides)
    return surface


def _registry_body(surfaces: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "registry_version": 1,
        "surfaces": surfaces if surfaces is not None else [_surface()],
    }


def _write_json(path: Path, body: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _touch_repo_paths(repo_root: Path, paths: list[str]) -> None:
    for rel_path in paths:
        path = repo_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")


def _prepare_all_declared_files(repo_root: Path, surface: dict[str, Any]) -> None:
    evidence = [
        evidence_path
        for component in surface["gate_components"]
        for evidence_path in component["evidence"]
    ]
    _touch_repo_paths(repo_root, [*evidence, *surface["producer_artifacts"]])


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _assert_no_banned_response_language(value: Any) -> None:
    flattened = json.dumps(value, sort_keys=True)
    assert not BANNED_RESPONSE_RE.search(flattened)


def test_tier_readiness_route_reports_limited_active_with_injected_green_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface()
    _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "ok"
    assert body["registry_version"] == 1
    assert body["decision_supported"] is False
    _assert_decision_supported_false_recursive(body)
    _assert_no_banned_response_language(body)
    surface_body = body["surfaces"][0]
    assert surface_body["surface_id"] == "roster_capacity"
    assert surface_body["tier_status"] == "diagnostic_grade_active_limited"
    assert surface_body["basis"] == "readiness_active_with_insufficient_data"
    assert surface_body["insufficient_data_count"] == 1
    assert surface_body["insufficient_data_components"] == ["mif_breaker"]
    assert surface_body["all_components_evaluable"] is False
    assert surface_body["live_preconditions"] == {
        "model_provenance_ok": "ok",
        "capture_health_ok": "ok",
    }
    component_statuses = {
        component["component"]: component for component in surface_body["components"]
    }
    assert component_statuses["audit_hygiene"]["component_status"] == "pass"
    assert component_statuses["deterministic_range_disclosure"]["component_status"] == "pass"
    assert component_statuses["mif_breaker"]["component_status"] == "insufficient_data"
    assert component_statuses["no_directive_copy"]["component_status"] == "pass"


def test_missing_evidence_file_is_component_failure_with_path_named_in_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_evidence = "tests/contract/missing_roster_capacity_contract.py"
    surface = _surface(
        {
            "gate_components": [
                _component("audit_hygiene", [missing_evidence]),
                _component(
                    "deterministic_range_disclosure",
                    ["tests/contract/test_roster_capacity_route.py"],
                ),
                _component("mif_breaker", ["src/dynasty_genius/realized_outcome/scorer.py"]),
                _component("no_directive_copy", ["frontend/scripts/check-banned-language.mjs"]),
            ]
        }
    )
    _prepare_all_declared_files(
        tmp_path,
        _surface(
            {
                "producer_artifacts": surface["producer_artifacts"],
            }
        ),
    )
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    surface_body = body["surfaces"][0]
    assert surface_body["tier_status"] == "not_graduated"
    assert surface_body["basis"] == "component_failed:audit_hygiene"
    audit = next(
        component
        for component in surface_body["components"]
        if component["component"] == "audit_hygiene"
    )
    assert audit["component_status"] == "fail"
    assert f"evidence_missing:{missing_evidence}" in audit["basis"]


def test_live_precondition_adapter_degradation_is_200_preconditions_degraded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface()
    _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        model_provenance_status="degraded",
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    surface_body = body["surfaces"][0]
    assert surface_body["tier_status"] == "preconditions_degraded"
    assert surface_body["basis"] == "live_precondition_not_ok:model_provenance_ok=degraded"
    assert surface_body["live_preconditions"]["model_provenance_ok"] == "degraded"


def test_ci_shape_degraded_guards_are_runtime_status_not_config_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface()
    _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
        model_provenance_status="degraded",
        capture_health_status="degraded",
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    assert body["surfaces"][0]["tier_status"] == "preconditions_degraded"
    assert body["surfaces"][0]["live_preconditions"] == {
        "model_provenance_ok": "degraded",
        "capture_health_ok": "degraded",
    }


def test_missing_producer_artifact_is_runtime_downgrade_not_config_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_artifact = "app/data/roster_capacity/roster_capacity_latest.json"
    surface = _surface({"producer_artifacts": [missing_artifact]})
    evidence = [
        evidence_path
        for component in surface["gate_components"]
        for evidence_path in component["evidence"]
    ]
    _touch_repo_paths(tmp_path, evidence)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "degraded"
    surface_body = body["surfaces"][0]
    assert surface_body["tier_status"] == "not_graduated"
    assert surface_body["basis"] == f"producer_artifact_missing:{missing_artifact}"


@pytest.mark.parametrize(
    "writer",
    [
        lambda path: None,
        lambda path: path.write_text("{not-json", encoding="utf-8"),
        lambda path: path.write_text(
            json.dumps({"registry_version": 1, "surfaces": []}),
            encoding="utf-8",
        ),
    ],
)
def test_config_failures_return_sanitized_503_without_path_or_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer,
) -> None:
    registry_path = tmp_path / "tier_readiness.json"
    writer(registry_path)
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 503
    body = response.json()
    detail = body.get("detail", body)
    assert detail == {
        "error": "tier_readiness_unavailable",
        "message": "tier readiness configuration unavailable",
        "decision_supported": False,
    }
    serialized = json.dumps(body)
    assert str(tmp_path) not in serialized
    assert "traceback" not in serialized.lower()


def test_route_is_wired_in_app_main_and_uses_no_banned_response_vocabulary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _surface()
    _prepare_all_declared_files(tmp_path, surface)
    registry_path = _write_json(tmp_path / "tier_readiness.json", _registry_body([surface]))
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    _assert_no_banned_response_language(response.json())


def test_trade_lab_ratification_gate_and_single_precondition_degradation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trade_lab = _trade_lab_surface({"ratified_date": None})
    _prepare_all_declared_files(tmp_path, trade_lab)
    registry_path = _write_json(
        tmp_path / "tier_readiness.json", _registry_body([trade_lab])
    )
    client = _client_with_temp_registry(
        monkeypatch,
        registry_path=registry_path,
        repo_root=tmp_path,
    )

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    surface = response.json()["surfaces"][0]
    assert surface["surface_id"] == "trade_lab"
    assert surface["tier_status"] == "not_graduated"
    assert surface["basis"] == "awaiting_david_ratification"
    assert surface["live_preconditions"] == {
        "model_provenance_ok": "ok",
        "capture_health_ok": "ok",
    }

    stamped = _trade_lab_surface({"ratified_date": "2026-07-04"})
    _prepare_all_declared_files(tmp_path, stamped)
    _write_json(registry_path, _registry_body([stamped]))

    response = client.get("/api/system/tier-readiness")

    assert response.status_code == 200
    surface = response.json()["surfaces"][0]
    assert surface["tier_status"] == "diagnostic_grade_active_limited"
    assert surface["basis"] == "readiness_active_with_insufficient_data"
    assert surface["insufficient_data_components"] == ["mif_breaker"]

    for precondition in ("model_provenance_ok", "capture_health_ok"):
        degraded_client = _client_with_temp_registry(
            monkeypatch,
            registry_path=registry_path,
            repo_root=tmp_path,
            model_provenance_status="degraded"
            if precondition == "model_provenance_ok"
            else "ok",
            capture_health_status="degraded"
            if precondition == "capture_health_ok"
            else "ok",
        )
        degraded = degraded_client.get("/api/system/tier-readiness").json()[
            "surfaces"
        ][0]
        assert degraded["tier_status"] == "preconditions_degraded"
        assert degraded["basis"] == f"live_precondition_not_ok:{precondition}=degraded"
        assert degraded["live_preconditions"][precondition] == "degraded"
